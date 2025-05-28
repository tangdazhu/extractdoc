# 版本历史

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