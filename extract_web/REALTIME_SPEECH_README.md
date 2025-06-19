# 实时语音识别功能说明 (Real-time Speech Recognition)

## 概述 (Overview)

本项目新增了基于阿里云DashScope API的实时语音识别功能，支持中英文混合识别，可实现低延迟的实时语音转文字。

This project now includes real-time speech recognition functionality based on Alibaba Cloud DashScope API, supporting Chinese-English mixed recognition with low latency speech-to-text conversion.

## 功能特性 (Features)

- ✅ **实时识别**: 低延迟语音转文字
- ✅ **多语言支持**: 中文、英文及混合识别  
- ✅ **WebSocket通信**: 基于WebSocket的实时数据传输
- ✅ **Django集成**: 完整集成到现有Django项目
- ✅ **前端界面**: 现代化的用户界面，支持麦克风录音
- ✅ **结果处理**: 实时显示识别结果和置信度

## 技术架构 (Technical Architecture)

```
前端 (Frontend)
├── HTML5 Web Audio API (麦克风录音)
├── WebSocket Client (实时通信)
└── Bootstrap UI (用户界面)

后端 (Backend)  
├── Django Views (HTTP API)
├── Django Channels (WebSocket处理)
├── Real-time Speech Processor (语音处理)
└── DashScope API (阿里云语音识别)
```

## 环境配置 (Environment Setup)

### 1. 安装依赖 (Install Dependencies)

```bash
pip install -r requirements.txt
```

新增的主要依赖包括:
- `websocket-client>=1.6.0`
- `channels>=4.0.0` 
- `channels-redis>=4.1.0`
- `dashscope==1.23.3`

### 2. 配置API密钥 (Configure API Key)

设置环境变量:
```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
```

或在Windows中:
```cmd
set DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

### 3. Redis配置 (Redis Configuration)

Django Channels需要Redis作为消息代理:
```bash
# 安装Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# 启动Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:latest
```

## 使用方法 (Usage)

### 1. 启动服务 (Start Services)

```bash
# 启动Django开发服务器
cd extract_web
python manage.py runserver

# 在新终端启动Channels Workers (如果需要)
python manage.py runworker
```

### 2. 访问界面 (Access Interface)

打开浏览器访问: `http://localhost:8000/converter/`

在转换器页面中，您会看到新增的"实时语音识别"功能区域。

### 3. 使用实时语音识别 (Use Real-time Speech Recognition)

1. **准备录音**: 点击"开始录音"按钮
2. **开始识别**: 允许浏览器访问麦克风
3. **实时查看**: 说话时实时查看识别结果
4. **停止录音**: 点击"停止录音"完成识别
5. **结果处理**: 查看最终识别文本和置信度

### 4. API接口 (API Endpoints)

#### HTTP API:
- `POST /converter/api/realtime-speech/start/` - 启动实时识别
- `POST /converter/api/realtime-speech/send-audio/<session_id>/` - 发送音频数据
- `GET /converter/api/realtime-speech/results/<session_id>/` - 获取识别结果
- `POST /converter/api/realtime-speech/stop/<session_id>/` - 停止识别

#### WebSocket API:
- `ws://localhost:8000/ws/realtime-speech/` - WebSocket连接地址

消息格式:
```json
// 启动识别
{
    "type": "start_recognition",
    "language_hints": ["zh", "en"],
    "vocabulary_id": "optional_custom_vocabulary"
}

// 发送音频数据
{
    "type": "audio_data", 
    "audio_data": "base64_encoded_audio_data"
}

// 停止识别
{
    "type": "stop_recognition"
}
```

## 测试功能 (Testing)

### 1. 基础测试 (Basic Test)

```bash
cd extract_web
python manage.py test_realtime_speech --duration 10 --language zh,en
```

### 2. 导入测试 (Import Test)

```bash
python -c "
from converter.realtime_speech_processor import create_realtime_recognizer
print('✅ Import successful')
"
```

### 3. API测试 (API Test)

使用curl测试HTTP API:
```bash
# 启动识别会话
curl -X POST http://localhost:8000/converter/api/realtime-speech/start/ \
  -H "Content-Type: application/json" \
  -d '{"language_hints": ["zh", "en"]}'
```

## 配置选项 (Configuration Options)

### 语音识别参数 (Speech Recognition Parameters)

```python
config = {
    "model": "paraformer-realtime-v1",           # 识别模型
    "language_hints": ["zh", "en"],              # 语言提示
    "audio_encoding": "pcm",                     # 音频编码格式
    "sample_rate": 16000,                        # 采样率
    "enable_intermediate_result": True,          # 启用中间结果
    "enable_punctuation_prediction": True,       # 启用标点预测
    "enable_inverse_text_normalization": True    # 启用逆文本标准化
}
```

### Django设置 (Django Settings)

在 `settings.py` 中添加:
```python
# Channels配置
ASGI_APPLICATION = 'project_core.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# 实时语音识别设置
REALTIME_SPEECH_CONFIG = {
    'MAX_AUDIO_DURATION': 300,  # 最大音频时长(秒)
    'AUDIO_CHUNK_SIZE': 1024,   # 音频块大小
    'SESSION_TIMEOUT': 3600,    # 会话超时时间(秒)
}
```

## 故障排除 (Troubleshooting)

### 常见问题 (Common Issues)

1. **API密钥错误**:
   ```
   Error: DASHSCOPE_API_KEY not found
   ```
   解决: 确保正确设置了环境变量 `DASHSCOPE_API_KEY`

2. **Redis连接失败**:
   ```
   Error: Redis connection failed
   ```
   解决: 确保Redis服务正在运行 (`redis-server`)

3. **麦克风权限被拒绝**:
   ```
   Error: NotAllowedError: Permission denied
   ```
   解决: 在浏览器中允许麦克风访问权限

4. **WebSocket连接失败**:
   ```
   Error: WebSocket connection failed
   ```
   解决: 检查Django Channels配置和ASGI应用设置

### 调试模式 (Debug Mode)

启用详细日志:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'converter.realtime_speech_processor': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'converter.realtime_speech_view': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## 性能优化 (Performance Optimization)

### 1. 音频处理优化
- 调整音频块大小 (`AUDIO_CHUNK_SIZE`)
- 优化采样率设置
- 启用音频压缩

### 2. 网络优化
- 使用WebSocket保持连接
- 实现音频数据缓冲
- 添加断线重连机制

### 3. 资源管理
- 定期清理过期会话
- 限制并发识别数量
- 监控内存使用情况

## 扩展功能 (Extended Features)

### 1. 自定义词汇表
支持添加专业术语词汇表以提高识别准确率

### 2. 多用户支持  
每个用户独立的识别会话管理

### 3. 历史记录
保存和查询历史识别记录

### 4. 音频文件上传
支持上传音频文件进行批量识别

## 技术支持 (Technical Support)

如有问题或建议，请联系开发团队或查看项目文档。

更多信息请参考:
- [DashScope API文档](https://help.aliyun.com/zh/dashscope/)
- [Django Channels文档](https://channels.readthedocs.io/)
- [Web Audio API文档](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) 