#!/usr/bin/python3

import socket
import threading
import time
import queue
import sys

class Server:
    def __init__(self):
            # 使用0.0.0.0表示监听所有可用的网络接口，包括局域网
            self.ip = "0.0.0.0"
            # 可选：使用127.0.0.1仅监听本机连接
            # self.ip = "127.0.0.1"
            
            try:
                print("可用的IP地址:")
                hostname = socket.gethostname()
                ip_list = socket.gethostbyname_ex(hostname)[2]
                for i, ip in enumerate(ip_list):
                    print(f"{i+1}. {ip}")
                print(f"服务器将监听所有网络接口 (0.0.0.0)")
            except Exception as e:
                print(f"获取IP地址时出错: {e}")
                print("继续使用0.0.0.0作为监听地址")
            
            while 1:
                try:
                    self.port = 2000

                    self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    # 设置套接字选项，允许地址重用
                    self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    # 增加接收缓冲区大小
                    self.s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)  # 增加到128KB
                    self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)  # 增加到128KB
                    # 设置TCP_NODELAY选项，禁用Nagle算法
                    try:
                        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    except:
                        print("无法设置TCP_NODELAY，继续执行")
                    self.s.bind((self.ip, self.port))

                    break
                except Exception as e:
                    print(f"无法绑定到该端口: {e}")

            # 存储客户端连接
            self.connections = []
            # 为每个客户端创建一个队列字典，键为客户端socket，值为队列
            self.client_queues = {}
            # 添加锁以保护共享资源
            self.lock = threading.Lock()
            # 统计信息
            self.stats = {
                "total_packets": 0,
                "dropped_packets": 0
            }
            
            # 启动统计信息线程
            threading.Thread(target=self.print_stats, daemon=True).start()
            
            self.accept_connections()

    def print_stats(self):
        """定期打印服务器统计信息"""
        while True:
            time.sleep(10)  # 每10秒打印一次
            try:
                with self.lock:
                    total = self.stats["total_packets"]
                    dropped = self.stats["dropped_packets"]
                    if total > 0:
                        drop_rate = (dropped / total) * 100
                    else:
                        drop_rate = 0
                    
                    print(f"服务器统计: 总数据包: {total}, 丢弃: {dropped}, 丢包率: {drop_rate:.2f}%")
                    print(f"当前连接数: {len(self.connections)}")
                    # 重置统计
                    self.stats["total_packets"] = 0
                    self.stats["dropped_packets"] = 0
            except Exception as e:
                print(f"打印统计信息时出错: {e}")

    def accept_connections(self):
        self.s.listen(100)
        print('服务器运行在IP: '+self.ip)
        print('服务器运行在端口: '+str(self.port))        
        while True:
            try:
                c, addr = self.s.accept()
                # 设置客户端socket的缓冲区大小
                c.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)  # 增加到128KB
                c.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)  # 增加到128KB
                # 设置TCP_NODELAY选项，禁用Nagle算法
                try:
                    c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except:
                    pass
                # 设置TCP保活选项
                try:
                    c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except:
                    pass
                
                print(f"新连接来自: {addr[0]}:{addr[1]}")

                with self.lock:
                    self.connections.append(c)
                    # 增加队列大小到20，提供更多缓冲
                    self.client_queues[c] = queue.Queue(maxsize=20)

                # 为每个客户端创建接收和发送线程
                threading.Thread(target=self.handle_client_receive, args=(c, addr), daemon=True).start()
                threading.Thread(target=self.handle_client_send, args=(c,), daemon=True).start()
            except Exception as e:
                print(f"接受连接时出错: {e}")
    
    def handle_client_receive(self, c, addr):
        """处理从客户端接收数据"""
        buffer = bytearray()  # 用于存储不完整的数据包
        
        while True:
            try:
                # 增加接收缓冲区大小
                data = c.recv(4096)
                if not data:
                    break
                
                # 将数据添加到缓冲区
                buffer.extend(data)
                
                # 处理数据包
                # 在实际应用中，可能需要实现更复杂的数据包处理逻辑
                # 这里简单处理，直接使用接收到的数据
                
                # 将数据放入其他客户端的队列
                with self.lock:
                    self.stats["total_packets"] += 1
                    dropped = False
                    
                    for client in list(self.connections):  # 使用列表副本避免迭代时修改
                        if client != c and client in self.client_queues:
                            q = self.client_queues[client]
                            if q.full():
                                # 队列满，丢弃最旧的数据包
                                try:
                                    q.get_nowait()
                                    dropped = True
                                except queue.Empty:
                                    pass
                            # 添加新数据包到队列
                            try:
                                q.put(data)
                            except:
                                pass
                    
                    if dropped:
                        self.stats["dropped_packets"] += 1
                
                # 清空缓冲区，准备接收下一个数据包
                buffer.clear()
            
            except socket.error as e:
                print(f"接收数据错误: {e}")
                break
            except Exception as e:
                print(f"处理数据错误: {e}")
                break
        
        # 客户端断开连接
        self.remove_client(c, addr)
    
    def handle_client_send(self, c):
        """处理向客户端发送数据"""
        last_send_time = time.time()
        packet_count = 0
        
        while True:
            try:
                if c not in self.connections:
                    break
                    
                if c in self.client_queues:
                    try:
                        # 非阻塞方式获取数据，超时时间为0.005秒
                        data = self.client_queues[c].get(timeout=0.005)
                        c.sendall(data)
                        
                        # 控制发送速率
                        packet_count += 1
                        current_time = time.time()
                        if current_time - last_send_time > 1:  # 每秒重置
                            packet_count = 0
                            last_send_time = current_time
                        
                        # 动态调整休眠时间，根据发送的数据包数量
                        if packet_count > 30:  # 如果发送速率过高
                            time.sleep(0.002)  # 稍微休眠一下
                        else:
                            time.sleep(0.0005)  # 最小休眠
                            
                    except queue.Empty:
                        # 队列为空，继续下一次循环
                        time.sleep(0.001)  # 短暂休眠，减少CPU使用
                else:
                    # 如果客户端已被移除，退出循环
                    break
            except socket.error as e:
                print(f"发送数据错误: {e}")
                break
            except Exception as e:
                print(f"发送处理错误: {e}")
                break
                
        # 如果循环退出，确保客户端被移除
        if c in self.connections:
            self.remove_client(c, ('未知', 0))
    
    def remove_client(self, c, addr):
        """移除客户端连接"""
        with self.lock:
            if c in self.connections:
                self.connections.remove(c)
                if c in self.client_queues:
                    del self.client_queues[c]
                try:
                    c.close()
                except:
                    pass
                print(f"客户端断开连接: {addr[0]}:{addr[1]}")
                print(f"当前连接数: {len(self.connections)}")

if __name__ == "__main__":
    try:
        server = Server()
    except KeyboardInterrupt:
        print("服务器被用户中断")
    except Exception as e:
        print(f"服务器发生错误: {e}")
        import traceback
        traceback.print_exc()
