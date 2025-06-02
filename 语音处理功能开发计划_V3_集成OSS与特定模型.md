**阶段二：核心后端逻辑 - 语音识别 (ASR)**

再梳理1.  **ASR API集成：**
    *   [x] 目标模型已确定: `Paraformer-v2`。
    *   [x] 已确认并实现使用 `dashscope.audio.asr.Transcription` 类（非 `FileTranscriber`）接受用户提供的OSS URL，并与 `Paraformer-v2` 模型正常工作 (已在 `speech_processor.py` 中初步实现)。

2.  **设计ASR的Django View (`asr_views.py` 或在现有 `views.py` 中新增)：**
    *   [ ] 创建一个新的URL endpoint (例如 `/api/speech-to-text/`)。
    *   [ ] 该接口应能接收用户提交的音频文件的OSS URL。
    *   [ ] 后端调用 `speech_processor.transcribe_audio_dashscope(audio_file_url='<user_provided_oss_url>')` (该函数内部使用 `dashscope.audio.asr.Transcription`)。

**主要变化和风险点：**

*   **OSS URL的提供**: 当前计划依赖用户预先将文件上传到OSS并提供URL。前端需要有相应输入字段。
*   **Paraformer-v2模型支持**: 确保 `dashscope.audio.asr.Transcription` 与 `Paraformer-v2` 结合使用时，所有预期的特性（如m4a格式、方言）均符合预期。
*   **应用自行管理OSS上传 (未来)**: 如果未来需要应用处理文件上传到OSS的流程，则需要完成 `oss2` SDK的集成、配置和相关上传逻辑的开发。

**下一步：**

1.  **首要任务：** 搭建ASR功能的后端API endpoint。该接口将接收用户提供的OSS URL，并使用 `Paraformer-v2` 模型通过 `speech_processor.transcribe_audio_dashscope` (内部调用 `dashscope.audio.asr.Transcription`) 进行识别。
2.  随后，搭建声音克隆功能的后端API endpoint。 