# Python 多客户端语音通信系统

一个基于 Python 的实时语音通信系统，支持多客户端连接，具有现代化的图形用户界面。

## 功能特点

- 🎙️ **实时语音通信** - 支持多客户端同时语音聊天
- 🖥️ **现代化GUI** - 基于 PyQt5 的直观用户界面
- 🔊 **高质量音频** - 48kHz 采样率，双声道音频传输
- 📊 **实时统计** - 显示连接状态、数据包统计和丢包率
- 🛡️ **稳定连接** - 内置抖动缓冲区和错误处理机制
- 🎯 **按住说话** - PTT（Push-to-Talk）模式，避免噪音干扰
- 🌐 **局域网支持** - 支持局域网内多设备连接

## 系统要求

- Python 3.7+
- Windows 10/11 (已测试)
- 支持音频输入/输出设备

## 依赖库

```bash
pip install pyqt5 pyaudio numpy
```

## 项目结构

```
Python-Voice-Chat/
├── client.py          # 客户端程序
├── server.py          # 服务器程序
├── dist/              # 打包后的可执行文件
│   ├── VoiceChatServer.exe
│   └── VoiceChatClient.exe
└── README.md
```

## 快速开始

### 方法一：运行 Python 源码

1. **克隆仓库**
   ```bash
   git clone https://github.com/IshadowshadowI/Python-Multi-client-voice-communication.git
   cd Python-Multi-client-voice-communication
   ```

2. **安装依赖**
   ```bash
   pip install pyqt5 pyaudio numpy
   ```

3. **启动服务器**
   ```bash
   python server.py
   ```

4. **启动客户端**
   ```bash
   python client.py
   ```

### 方法二：使用可执行文件

1. 下载 `dist` 文件夹中的可执行文件
2. 运行 `VoiceChatServer.exe` 启动服务器
3. 运行 `VoiceChatClient.exe` 启动客户端

## 使用说明

### 服务器端

1. 运行服务器程序后，它会自动监听端口 2000
2. 服务器会显示当前可用的 IP 地址
3. 服务器支持多个客户端同时连接
4. 实时显示连接统计信息

### 客户端

1. 启动客户端程序
2. 输入服务器 IP 地址（默认：192.168.137.1）
3. 输入端口号（默认：2000）
4. 点击"连接服务器"
5. 连接成功后，按住"按住说话"按钮进行语音通信

## 技术特性

### 音频处理
- **采样率**: 48kHz
- **声道**: 双声道立体声
- **格式**: 16位 PCM
- **缓冲区**: 1024 帧

### 网络优化
- TCP 连接，确保数据完整性
- 禁用 Nagle 算法，减少延迟
- 动态缓冲区管理
- 智能丢包处理

### 用户界面
- 现代化 Material Design 风格
- 实时连接状态显示
- 音频统计信息
- 操作日志记录

## 网络配置

### 局域网使用
1. 确保所有设备在同一局域网内
2. 服务器端防火墙允许端口 2000
3. 客户端输入服务器的局域网 IP

### 端口说明
- 默认端口：2000
- 协议：TCP
- 如需更改端口，请修改源码中的 `self.port` 变量

## 故障排除

### 常见问题

**1. 客户端无法连接服务器**
- 检查网络连接
- 确认服务器 IP 地址正确
- 检查防火墙设置

**2. 没有声音输出**
- 检查音频设备是否正常工作
- 确认系统音量设置
- 尝试重新连接

**3. 音频延迟过高**
- 检查网络延迟
- 减少其他网络应用的带宽占用
- 尝试有线连接

**4. 程序崩溃**
- 检查依赖库是否正确安装
- 查看错误日志
- 尝试重新安装依赖

## 开发说明

### 项目架构

```
┌─────────────────┐    TCP连接    ┌─────────────────┐
│   客户端 A      │◄──────────────►│                 │
├─────────────────┤               │                 │
│ - GUI界面       │               │     服务器       │
│ - 音频录制      │               │                 │
│ - 音频播放      │               │ - 连接管理      │
│ - 数据传输      │               │ - 数据转发      │
└─────────────────┘               │ - 统计信息      │
                                  │                 │
┌─────────────────┐               │                 │
│   客户端 B      │◄──────────────►│                 │
├─────────────────┤               └─────────────────┘
│ - GUI界面       │
│ - 音频录制      │
│ - 音频播放      │
│ - 数据传输      │
└─────────────────┘
```

### 核心模块

- **AudioClient**: 音频处理和网络通信
- **VoiceChatWindow**: 图形用户界面
- **Server**: 服务器连接管理和数据转发

## 打包说明

使用 PyInstaller 打包为独立可执行文件：

```bash
# 打包服务器
pyinstaller --noconfirm --onefile --name VoiceChatServer server.py

# 打包客户端
pyinstaller --noconfirm --onefile --windowed --name VoiceChatClient client.py
```

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 更新日志

### v1.0.0
- 基本语音通信功能
- PyQt5 图形界面
- 多客户端支持
- 实时统计显示

## 联系方式

- GitHub: [@IshadowshadowI](https://github.com/IshadowshadowI)
- 项目链接: [https://github.com/IshadowshadowI/Python-Multi-client-voice-communication](https://github.com/IshadowshadowI/Python-Multi-client-voice-communication)

## 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

⭐ 如果这个项目对您有帮助，请给个 Star 支持一下！
