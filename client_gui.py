#!/usr/bin/python3

import socket
import threading
import pyaudio
import time
import queue
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QHBoxLayout, QTextEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

class AudioClient(QThread):
    status_signal = pyqtSignal(str)
    stats_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.sending_audio = False  # 控制是否发送音频
        self.s = None
        self.p = None
        self.playing_stream = None
        self.recording_stream = None
        
        # 音频参数
        self.chunk_size = 1024
        self.audio_format = pyaudio.paInt16
        self.channels = 2
        self.rate = 48000
        
        # 创建音频队列
        self.audio_queue = queue.Queue(maxsize=20)
        
        # 创建抖动缓冲区
        self.jitter_buffer_size = 3
        self.jitter_buffer = []
        
        # 统计信息
        self.stats = {
            "packets_received": 0,
            "packets_dropped": 0,
            "start_time": time.time()
        }

    def connect_to_server(self, ip, port):
        """连接到服务器"""
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
            self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            self.s.connect((ip, port))
            
            # 初始化音频设备
            self.p = pyaudio.PyAudio()
            
            self.playing_stream = self.p.open(format=self.audio_format, 
                                            channels=self.channels, 
                                            rate=self.rate, 
                                            output=True,
                                            frames_per_buffer=self.chunk_size)
            self.recording_stream = self.p.open(format=self.audio_format, 
                                            channels=self.channels, 
                                            rate=self.rate, 
                                            input=True,
                                            frames_per_buffer=self.chunk_size)
            
            self.running = True
            self.status_signal.emit("已连接到服务器")
            return True
        except Exception as e:
            self.status_signal.emit(f"连接失败: {e}")
            return False

    def run(self):
        """启动音频处理线程"""
        if not self.running:
            return
            
        # 启动接收线程
        receive_thread = threading.Thread(target=self.receive_server_data)
        receive_thread.daemon = True
        receive_thread.start()
        
        # 启动播放线程
        play_thread = threading.Thread(target=self.play_audio)
        play_thread.daemon = True
        play_thread.start()
        
        # 启动发送线程
        send_thread = threading.Thread(target=self.send_data_to_server)
        send_thread.daemon = True
        send_thread.start()
        
        # 启动统计线程
        stats_thread = threading.Thread(target=self.print_stats)
        stats_thread.daemon = True
        stats_thread.start()

    def print_stats(self):
        """定期打印统计信息"""
        while self.running:
            time.sleep(5)  # 每5秒更新一次
            elapsed = time.time() - self.stats["start_time"]
            received = self.stats["packets_received"]
            dropped = self.stats["packets_dropped"]
            
            if received > 0:
                drop_rate = (dropped / (received + dropped)) * 100
                packets_per_second = received / elapsed
            else:
                drop_rate = 0
                packets_per_second = 0
                
            stats_text = f"接收: {received}, 丢弃: {dropped}, 丢包率: {drop_rate:.1f}%, 速率: {packets_per_second:.1f}/s"
            self.stats_signal.emit(stats_text)
            
            # 重置统计
            self.stats["packets_received"] = 0
            self.stats["packets_dropped"] = 0
            self.stats["start_time"] = time.time()

    def receive_server_data(self):
        """从服务器接收音频数据并放入队列"""
        buffer = bytearray()
        
        while self.running:
            try:
                data = self.s.recv(4096)
                if not data:
                    continue
                
                buffer.extend(data)
                
                if self.audio_queue.full():
                    try:
                        self.audio_queue.get_nowait()
                        self.stats["packets_dropped"] += 1
                    except queue.Empty:
                        pass
                
                self.audio_queue.put(data)
                self.stats["packets_received"] += 1
                
                buffer = bytearray()
                
            except socket.error as e:
                if self.running:
                    self.status_signal.emit(f"接收数据错误: {e}")
                break
            except Exception as e:
                if self.running:
                    self.status_signal.emit(f"处理接收数据时出错: {e}")
                break

    def play_audio(self):
        """从队列中获取音频数据并播放"""
        # 初始化抖动缓冲区
        while self.running and len(self.jitter_buffer) < self.jitter_buffer_size:
            try:
                data = self.audio_queue.get(timeout=0.5)
                self.jitter_buffer.append(data)
            except queue.Empty:
                if len(self.jitter_buffer) == 0:
                    silence = b'\x00' * self.chunk_size * 2
                    self.jitter_buffer.append(silence)
                time.sleep(0.01)
        
        while self.running:
            try:
                if self.jitter_buffer:
                    data_to_play = self.jitter_buffer.pop(0)
                    try:
                        self.playing_stream.write(data_to_play)
                    except Exception as e:
                        pass
                
                try:
                    new_data = self.audio_queue.get(timeout=0.01)
                    self.jitter_buffer.append(new_data)
                except queue.Empty:
                    if len(self.jitter_buffer) < 1:
                        silence = b'\x00' * self.chunk_size * 2
                        self.jitter_buffer.append(silence)
                
                while len(self.jitter_buffer) > self.jitter_buffer_size + 2:
                    self.jitter_buffer.pop(0)
                    self.stats["packets_dropped"] += 1
                    
            except Exception as e:
                if self.running:
                    pass
                time.sleep(0.01)

    def send_data_to_server(self):
        """录制并发送音频数据到服务器"""
        while self.running:
            try:
                # 只有在sending_audio为True时才发送音频
                if self.sending_audio:
                    data = self.recording_stream.read(self.chunk_size, exception_on_overflow=False)
                    self.s.sendall(data)
                else:
                    # 如果不发送音频，只是休眠以降低CPU占用
                    time.sleep(0.01)
            except (socket.error, BrokenPipeError):
                if self.running:
                    self.status_signal.emit("连接中断")
                self.running = False
                break
            except Exception as e:
                if self.running:
                    self.status_signal.emit(f"发送时出错: {e}")
                break

    def start_sending(self):
        """开始发送音频"""
        self.sending_audio = True

    def stop_sending(self):
        """停止发送音频"""
        self.sending_audio = False

    def cleanup(self):
        """清理资源"""
        self.running = False
        time.sleep(0.2)
        
        if hasattr(self, 'playing_stream') and self.playing_stream:
            try:
                self.playing_stream.stop_stream()
                self.playing_stream.close()
            except:
                pass
        
        if hasattr(self, 'recording_stream') and self.recording_stream:
            try:
                self.recording_stream.stop_stream()
                self.recording_stream.close()
            except:
                pass
        
        if hasattr(self, 'p') and self.p:
            try:
                self.p.terminate()
            except:
                pass
        
        if hasattr(self, 's') and self.s:
            try:
                self.s.close()
            except:
                pass


class VoiceChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.audio_client = AudioClient()
        self.connected = False
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('语音聊天客户端')
        self.setGeometry(100, 100, 400, 600)
        
        # 创建布局
        layout = QVBoxLayout()
        
        # 连接区域
        connect_layout = QVBoxLayout()
        
        # IP输入
        ip_layout = QHBoxLayout()
        ip_label = QLabel('服务器IP:')
        self.ip_input = QLineEdit('192.168.137.1')
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_input)
        
        # 端口输入
        port_layout = QHBoxLayout()
        port_label = QLabel('端口:')
        self.port_input = QLineEdit('2000')
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_input)
        
        # 连接按钮
        self.connect_btn = QPushButton('连接服务器')
        self.connect_btn.clicked.connect(self.connect_to_server)
        
        connect_layout.addLayout(ip_layout)
        connect_layout.addLayout(port_layout)
        connect_layout.addWidget(self.connect_btn)
        
        # 状态显示
        self.status_label = QLabel('未连接')
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        
        # 按住说话按钮
        self.talk_btn = QPushButton('按住说话')
        self.talk_btn.setEnabled(False)
        self.talk_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 绑定按钮事件
        self.talk_btn.pressed.connect(self.start_talking)
        self.talk_btn.released.connect(self.stop_talking)
        
        # 统计信息显示
        self.stats_label = QLabel('统计信息: 等待连接...')
        self.stats_label.setStyleSheet("color: blue; font-size: 10px;")
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("程序启动...")
        
        # 添加到主布局
        layout.addLayout(connect_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.talk_btn)
        layout.addWidget(self.stats_label)
        layout.addWidget(QLabel('日志:'))
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # 连接信号
        self.audio_client.status_signal.connect(self.update_status)
        self.audio_client.stats_signal.connect(self.update_stats)
        
    def connect_to_server(self):
        """连接到服务器"""
        if self.connected:
            # 断开连接
            self.audio_client.cleanup()
            self.connected = False
            self.connect_btn.setText('连接服务器')
            self.talk_btn.setEnabled(False)
            self.status_label.setText('已断开连接')
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.log_text.append("已断开连接")
            return
            
        # 获取连接参数
        ip = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            self.update_status("端口号必须是数字")
            return
            
        if not ip:
            self.update_status("请输入服务器IP地址")
            return
            
        # 尝试连接
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText('连接中...')
        self.log_text.append(f"正在连接到 {ip}:{port}...")
        
        # 在后台线程中连接
        def connect():
            success = self.audio_client.connect_to_server(ip, port)
            if success:
                self.connected = True
                self.audio_client.start()
                self.connect_btn.setText('断开连接')
                self.talk_btn.setEnabled(True)
            else:
                self.connect_btn.setText('连接服务器')
            self.connect_btn.setEnabled(True)
            
        threading.Thread(target=connect, daemon=True).start()
        
    def start_talking(self):
        """开始说话"""
        if self.connected:
            self.audio_client.start_sending()
            self.talk_btn.setText('正在发送语音...')
            self.talk_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 10px;
                }
            """)
            
    def stop_talking(self):
        """停止说话"""
        if self.connected:
            self.audio_client.stop_sending()
            self.talk_btn.setText('按住说话')
            self.talk_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 20px;
                    font-size: 18px;
                    font-weight: bold;
                    border-radius: 10px;
                }
                QPushButton:pressed {
                    background-color: #45a049;
                }
            """)
            
    def update_status(self, message):
        """更新状态显示"""
        self.status_label.setText(message)
        self.log_text.append(f"{time.strftime('%H:%M:%S')} - {message}")
        
        if "已连接" in message:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        elif "失败" in message or "错误" in message:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
    def update_stats(self, stats):
        """更新统计信息"""
        self.stats_label.setText(f"统计信息: {stats}")
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.connected:
            self.audio_client.cleanup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyleSheet("""
        QWidget {
            font-family: Arial, sans-serif;
        }
        QLineEdit {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        QPushButton {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 3px;
            background-color: #f0f0f0;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
    """)
    
    window = VoiceChatWindow()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
