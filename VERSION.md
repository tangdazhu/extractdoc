# 版本历史

## v2.1.0 (2025-05-31)

### ✨ 新增功能
- **视频处理模块 (初步集成)**:
  - 新增"视频处理"主选项卡。
  - 实现"视频帧提取"功能，可将视频帧提取为图片序列或合并为一个PDF文件。
  - 支持配置提取频率、输出格式（图片/PDF）以及可选的图像去重阈值。
  - 视频处理过程采用流式响应，在前端实时显示处理日志和进度。
- **处理时长显示**: 
  - 所有文件转换（图片转文件、文件转PDF、PDF转文件）和视频处理任务，均在前端结果区域显示总处理时长，单位为秒。

### 🔧 技术改进
- **视图函数更新**: `img_to_file_view`, `file_to_pdf_view`, `pdf_to_file_view` 和 `process_video_extraction_view` (及其辅助函数 `stream_video_processing_response`) 已更新，实现处理开始和结束时间的记录，计算处理时长，并将时长包含在返回给前端的JSON数据中。
- **前端模板更新** (`index.html`):
  - `handleConversionResponse` (针对文档转换) 和 `displayVideoExtractionResults` (针对视频处理) JavaScript函数已更新，用于解析并显示后端返回的 `duration_seconds`。
- **响应格式化**: 更新了 `response_formatters.py` 中的 `format_json_response` 以支持包含 `duration_seconds`。

### 🐛 问题修复
- 解决了视频处理过程中，因 `extract_video_snapshots.py` 脚本内部错误 (AttributeError: 'VideoManager' object has no attribute 'is_started') 导致的卡死问题。
- 修正了部分视图函数中 `format_json_response` 调用参数不匹配的问题。
- 修复了 `img_to_file_view` 中 `file_results` 未在所有分支正确传递导致JSON响应不含结果的问题。

### 📚 文档更新
- `GUI-Requirements.md` 已更新，包含视频处理模块的需求和处理时长显示。
- `README.md` 将同步更新项目特色和功能列表。

---

## v2.0.0 (2025-01-27)

### 🎉 重大更新
- **完整的PDF转文件功能**: 支持PDF转Word、Excel、PowerPoint、TXT
- **智能转换策略**: 每种转换提供多种方法，自动选择最佳方案
- **一键安装脚本**: 新增`install_dependencies.py`自动化安装流程

### ✨ 新增功能
- **PDF转Excel**: 使用pdfplumber专门优化表格提取
- **PDF转PPT**: 支持截图方式和LibreOffice方式
- **PDF转TXT**: 使用PyMuPDF快速文本提取
- **转换方法选择**: 用户可在界面上选择不同转换方法
- **批量合并**: 支持多个PDF合并为单个Word/TXT文件

### 🔧 技术改进
- **依赖管理**: 重新组织requirements.txt，按功能分类
- **错误处理**: 改进LibreOffice不可用时的降级处理
- **用户界面**: 移除不稳定的LibreOffice选项，优化用户体验
- **日志系统**: 增强错误日志和调试信息

### 📚 文档更新
- **README.md**: 全面更新安装说明和使用指南
- **故障排除**: 新增详细的问题解决方案
- **快速开始**: 添加使用流程和技巧说明

### 🐛 问题修复
- 修复PDF转Excel时的KeyError问题
- 修复重复文件生成问题
- 修复AttributeError错误
- 改进LibreOffice转换的错误提示

---

## v1.0.0 (2024年初)

### 🚀 初始版本
- **基础转换功能**: 图片转文件、文件转PDF
- **用户系统**: 注册、登录、管理控制台
- **历史记录**: 转换文件的历史管理
- **OCR功能**: 基于PaddleOCR的图片文字识别

### 📋 支持的转换
- 图片 → Word/PDF
- Word/Excel/PPT/TXT → PDF
- 基础的PDF转Word功能

### 🛠️ 技术栈
- Django 5.2.1 Web框架
- PaddleOCR 文字识别
- LibreOffice 文档转换
- SQLite 数据库 