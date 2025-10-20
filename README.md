# Django Web应用：OmniAI Transform Studio - 智能文档转换工作室

---

## 📢 最新更新

**2025-10-20 重大更新：URL到PPT智能生成** 🎉
- ✨ **URL到PPT**: 从网络文章URL智能提取内容并生成专业PPT
- 🤖 **AI驱动**: 使用Qwen-Max模型智能分析文章结构
- 📊 **自动提炼**: 自动提取核心要点，生成3-8页精美幻灯片
- 🎨 **模板支持**: 支持商务风格和学术风格两种预定义模板
- 🌐 **多网站支持**: 优化支持微信公众号文章，兼容通用网页
- 📘 详细说明: [URL到PPT功能文档](docs/URL_TO_PPT_FEATURE.md)

**2025-10-20 配置管理统一**
- ✅ **配置统一**: 所有配置文件已合并到 `config/application.yaml`
- ✅ **配置管理器**: 新增统一配置管理器 `utils/config_manager.py`
- ✅ **向后兼容**: 旧代码无需修改，自动适配新配置
- ✅ **智能服务**: AI驱动的Word/PPT智能生成服务
- ✅ **测试完善**: 所有测试通过（10/10）
- 📘 详细说明: [配置管理完整指南](docs/CONFIG_COMPLETE_GUIDE.md)

**2025-06-21 新增功能：**
- 实时语音识别（流式同步）：前后端流式同步，兼容 DashScope WebSocket 接口，前端可实时显示临时（is_final: false）和最终（is_final: true）识别结果，支持中英文，详细日志辅助排查。

**2025-01-XX 更新：**
- 文件大小限制提升：单个文件上传限制从10MB提升至500MB，支持更大文件的处理。

---

本项目是一个基于 Django 框架构建的 Web 应用程序，旨在提供一个用户友好的界面，用于多种文件格式之间的转换和处理，并初步集成了视频内容提取功能。它是早期命令行脚本 `extract_text_from_images.py` 的功能扩展和Web化。

## 🌟 项目特色

- **🌐 URL到PPT智能生成** ⭐ NEW: 从网络文章URL一键生成专业PPT，AI智能提炼核心内容
- **🔄 多格式转换支持**: 支持图片、PDF、Word、Excel、PowerPoint、TXT等多种格式互转
- **🎞️ 视频帧提取**: 支持从视频中提取帧并保存为图片序列或PDF (初步集成)
- **⏱️ 处理时长反馈**: 所有转换和处理任务均显示处理耗时
- **🎯 智能转换策略**: 每种转换都提供多种方法，自动选择最佳方案或允许用户手动选择
- **📊 专业PDF表格提取**: 使用pdfplumber专门优化PDF中的表格数据提取
- **🔧 一键部署**: 提供自动安装脚本，简化环境配置和依赖安装
- **👥 多用户支持**: 完整的用户认证系统和个人文件管理
- **📱 现代化界面**: 响应式设计，支持拖拽上传，实时状态反馈
- **🔒 安全可靠**: 用户文件隔离存储，支持批量处理和历史记录管理
- **🗣️ 实时语音识别（流式同步）**: 支持通过 DashScope WebSocket 实现实时语音识别，前端可实时显示临时/最终识别结果，支持中英文，详细日志辅助排查。

## 主要功能

- **用户认证系统**:
    - 用户注册、登录、登出功能。
    - 管理员用户 (`admin/admin` 初始密码) 可以访问管理控制台。
- **管理控制台 (管理员专属)**:
    - 用户管理：查看、编辑、删除用户，重置用户密码。
    - 文件管理 (待实现)。
- **文件转换**:
    - **图片转文件**: 支持将上传的图片 (JPG, PNG等) 批量或单独转换为 Word (.docx) 或 PDF (.pdf) 文件。
        - 利用 PaddleOCR进行文字识别和表格检测。
        - 支持合并多个图片内容到一个输出文件。
        - *显示处理时长*
    - **文件转PDF**:
        - Word (.doc, .docx) 转 PDF。
        - Excel (.xls, .xlsx) 转 PDF (优先使用 LibreOffice, 其次 OpenPyXL 作为后备)。
        - PowerPoint (.ppt, .pptx) 转 PDF (使用 LibreOffice)。
        - TXT (.txt) 转 PDF (使用 `reportlab`)。
        - 支持合并多个输入文件到一个PDF。
        - *显示处理时长*
    - **PDF转文件**:
        - PDF 转 Word (.docx) - 支持多种转换方法：
          * 主要方法：`pdf2docx` (默认，效果好)
          * 备用方法：LibreOffice (Office转换方式)
        - PDF 转 Excel (.xlsx) - 专业表格提取：
          * 主要方法：`pdfplumber` (默认，专门优化PDF表格提取)
          * 备用方法：LibreOffice (在某些环境中可能不可用)
        - PDF 转 PowerPoint (.pptx) - 多种转换策略：
          * 主要方法：截图方式 (使用 `python-pptx` + `PyMuPDF`)
          * 备用方法：LibreOffice (Office转换方式)
        - PDF 转 TXT (.txt) - 文本提取：
          * 主要方法：`PyMuPDF` (默认，快速准确)
          * 备用方法：LibreOffice (已从界面移除)
        - 支持合并多个PDF到单个输出文件 (Word/TXT支持，Excel/PPT暂不支持合并)
        - *显示处理时长*
- **视频处理 (新增)**:
    - **视频帧提取**: 从上传的视频文件中提取图像帧。
        - 支持配置提取频率（间隔秒数、总帧数）。
        - 支持选择输出为图片序列 (JPG/PNG) 或合并为一个 PDF 文件。
        - 可选的图像去重功能，以减少相似帧。
        - 实时流式显示处理日志和进度。
        - *显示处理时长*
- **历史转换记录**:
    - 用户可以查看自己过去转换成功的文件列表。
    - 按日期组织转换记录。
    - 提供已转换文件的下载和删除功能。
- **动态文件处理与存储**:
    - 用户上传的文件和转换后的文件存储在服务器端的 `his_pic/<username>/<date>/` 目录下。
    - `uploads/` 子目录存放用户上传的原始文件。
    - `converted_files/` 子目录存放转换后的结果文件。
    - `.meta` 文件用于存储原始文件名信息，便于历史记录展示。
- **前端界面**:
    - 使用 HTML, CSS 和 JavaScript 构建交互式用户界面。
    - 主选项卡区分不同转换类型："图片转文件", "文件转PDF", "PDF转文件", "视频处理"。
    - 子选项卡用于选择具体的转换操作 (如 "图片转Word", "Excel转PDF", "视频帧提取")。
    - 智能转换方法选择：用户可以选择不同的转换方法 (如PDF转Word时选择pdf2docx或Office转换方式)。
    - 提供文件上传、清空列表、开始转换、合并输出等操作按钮。
    - 动态显示转换结果和下载链接。
    - 实时转换状态反馈（包括视频处理的流式日志）和错误处理提示。
    - 所有任务结果均显示处理时长。

## 项目结构 (简化版)

```
extract_doc/
├── extract_web/                  # Django 项目根目录
│   ├── manage.py                 # Django 项目管理脚本
│   ├── project_core/             # Django 项目核心配置 (settings.py, urls.py等)
│   ├── converter/                # Django 应用 (views, models, forms, converters)
│   │   ├── migrations/
│   │   ├── static/converter/css/ # CSS 样式
│   │   ├── templates/converter/  # HTML 模板
│   │   ├── services/             # 业务服务层
│   │   │   ├── smart_word_generator.py    # 智能Word生成器
│   │   │   ├── smart_ppt_generator.py     # 智能PPT生成器
│   │   │   ├── ai_document_analyzer.py    # AI文档分析器
│   │   │   ├── document_generation.py     # 文档生成服务
│   │   │   └── ... (其他服务)
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── pic_file_converter.py # 图片转文件逻辑
│   │   ├── excel_pdf_converter.py # Excel 转 PDF 逻辑
│   │   └── ... (其他转换器)
│   ├── media/                    # 存放用户上传和转换后的文件
│   │   └── his_pic/              # 用户历史文件根目录
│   └── db.sqlite3                # SQLite 数据库文件
├── config/                       # 配置文件目录
│   ├── application.yaml          # 统一配置文件 (新)
│   ├── templates/                # PPT模板文件
│   │   ├── business_template.pptx
│   │   └── academic_template.pptx
│   ├── create_ppt_templates.py   # 模板生成脚本
│   ├── patterns.py               # 正则表达式工具库
│   └── backup/                   # 旧配置文件备份
├── utils/                        # 工具函数模块
│   ├── __init__.py
│   ├── config_manager.py         # 统一配置管理器 (新)
│   ├── config.py                 # 配置加载（向后兼容层）
│   ├── logger.py                 # 日志工具
│   └── ... (其他工具)
├── docs/                         # 项目文档
│   ├── README.md                 # 文档目录
│   └── CONFIG_COMPLETE_GUIDE.md  # 配置管理完整指南
├── requirements.txt              # Python 依赖包列表
├── install_dependencies.py      # 自动安装脚本
├── test_config_migration.py     # 配置迁移测试脚本
├── test_config_compatibility.py # 配置兼容性测试脚本
├── extract_text_from_images.py  # 早期命令行脚本
├── VERSION.md                    # 版本历史和更新日志
└── README.md                     # 本说明文件
```

**重要更新 (2025-10-20)**:
- ✅ **配置统一**: 所有配置已统一到 `config/application.yaml`
- ✅ **配置管理器**: 新增 `utils/config_manager.py` 统一管理所有配置
- ✅ **向后兼容**: `utils/config.py` 作为兼容层，旧代码无需修改
- ✅ **智能服务**: 新增AI驱动的文档生成服务（Word、PPT）
- ✅ **测试完善**: 配置迁移和兼容性测试全部通过

**注意**:
- `config/application.yaml` 是唯一的配置文件，包含所有应用配置
- 旧配置文件已备份到 `config/backup/` 目录
- 详细配置说明请参考 `docs/CONFIG_COMPLETE_GUIDE.md`

## 安装与运行

### 快速安装 (推荐)

1. **克隆项目或下载代码**
2. **运行自动安装脚本**:
   ```bash
   python install_dependencies.py
   ```
   
   该脚本将自动：
   - 检查Python版本 (需要3.7+)
   - 安装所有Python依赖包
   - 检查LibreOffice安装状态
   - 执行Django数据库迁移
   - 创建默认管理员用户 (admin/admin)

3. **启动应用**:
   ```bash
   cd extract_web
       python manage.py runserver
    ```

## 🔧 故障排除

### 常见安装问题

#### 1. pip不可用或版本冲突
**问题**: `pip --version` 失败或出现"SRE module mismatch"错误
**解决方案**:
```bash
# 方法1: 使用python -m pip
python -m pip --version

# 方法2: 重新安装pip
python -m ensurepip --upgrade

# 方法3: 如果是LibreOffice冲突，临时移除PATH中的LibreOffice
```

#### 2. PaddleOCR安装失败
**问题**: paddleocr或paddlepaddle安装失败
**解决方案**:
```bash
# 使用国内镜像源
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
pip install paddleocr -i https://mirror.baidu.com/pypi/simple

# 或者使用CPU版本
pip install paddlepaddle==2.5.1 -i https://mirror.baidu.com/pypi/simple
```

#### 3. LibreOffice相关问题
**问题**: soffice命令不可用
**解决方案**:
- **Windows**: 确保LibreOffice安装路径在系统PATH中
- **Linux**: `sudo apt-get install libreoffice`
- **macOS**: `brew install --cask libreoffice`

#### 4. 数据库迁移失败
**问题**: Django迁移命令失败
**解决方案**:
```bash
cd extract_web
python manage.py makemigrations
python manage.py migrate --run-syncdb
```

#### 5. 端口占用问题
**问题**: 8000端口被占用
**解决方案**:
```bash
# 使用其他端口
python manage.py runserver 8080

# 或者找到并终止占用进程
netstat -ano | findstr :8000  # Windows
lsof -ti:8000 | xargs kill    # Linux/macOS
```

### 环境特定问题

#### Windows环境
- 确保Python安装时勾选了"Add Python to PATH"
- 如果使用Anaconda，建议在Anaconda Prompt中运行
- 某些杀毒软件可能阻止文件转换，需要添加白名单

#### Linux环境
- 可能需要安装额外的系统依赖：
  ```bash
  sudo apt-get update
  sudo apt-get install python3-dev python3-pip
  sudo apt-get install libreoffice
  ```

#### macOS环境
- 建议使用Homebrew安装依赖：
  ```bash
  brew install python
  brew install --cask libreoffice
  ```

4. **访问应用**: 在浏览器中打开 `http://127.0.0.1:8000/`

## 🚀 快速开始

### 基本使用流程

1. **注册/登录**: 
   - 访问应用首页，点击"注册"创建新账户
   - 或使用默认管理员账户：`admin/admin`

2. **选择转换类型**:
   - **图片转文件**: 上传JPG/PNG图片，转换为Word或PDF
   - **文件转PDF**: 将Word/Excel/PPT/TXT转换为PDF
   - **PDF转文件**: 将PDF转换为Word/Excel/PPT/TXT

3. **上传文件**:
   - 点击上传区域或拖拽文件到页面
   - 支持批量上传（最多10个文件，单个文件≤500MB）

4. **配置选项**:
   - 选择转换方法（如PDF转Word时选择pdf2docx或Office方式）
   - 决定是否合并多个文件为一个输出文件

5. **开始转换**:
   - 点击"开始转换"按钮
   - 等待转换完成，查看结果

6. **下载结果**:
   - 在转换结果表格中点击"下载"链接
   - 或在"历史转换记录"中管理所有转换文件

### 💡 使用技巧

- **PDF转Excel**: 推荐使用默认的pdfplumber方法，专门优化表格提取
- **图片转文字**: 确保图片清晰，文字对比度高，获得最佳OCR效果
- **批量转换**: 使用"合并为一个文件"选项可以将多个输入合并为单个输出
- **历史管理**: 定期清理历史文件以节省存储空间

### 手动安装

如果自动安装脚本遇到问题，可以按以下步骤手动安装：

1.  **环境准备**:
    *   确保已安装 Python 3.7 或更高版本。
    *   建议使用虚拟环境 (如 venv 或 conda)。

2.  **安装Python依赖**:
    ```bash
    pip install -r requirements.txt
    ```
    
    **注意**: 如果在安装 `paddleocr` 时遇到问题，请参考其官方文档进行安装。可能需要单独安装 `paddlepaddle`:
    ```bash
    pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
    ```

3.  **安装LibreOffice (可选但推荐)**:
    - **Windows**: 从 https://www.libreoffice.org/download/download/ 下载安装
    - **Linux**: `sudo apt-get install libreoffice`
    - **macOS**: `brew install --cask libreoffice`
    
    确保 `soffice` 命令在系统PATH中可用。

4.  **数据库迁移**:
    ```bash
    cd extract_web
    python manage.py migrate
    ```

5.  **创建超级用户**:
    ```bash
    python manage.py createsuperuser
    ```
    或使用默认的 `admin/admin` 账户。

6.  **运行开发服务器**:
    ```bash
    python manage.py runserver
    ```

# OCR and Table Extraction Script

This project is a Python script for extracting text and tables from images using OCR.

## Project Structure

```
extract_doc/
├── config/
│   ├── __init__.py
│   ├── patterns.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── layout_analyzer.py
│   ├── ocr_engine.py
│   ├── table_detector.py
│   └── text_processor.py
├── exporters/
│   ├── __init__.py
│   ├── base_exporter.py
│   ├── docx_exporter.py
│   └── pdf_exporter.py
├── handlers/
│   ├── __init__.py
│   ├── image_specific.py
│   └── special_tables.py
├── models/                 # Contains OCR/detection models
│   ├── det_model_ch/
│   ├── layout_model/
│   ├── rec_model_ch/
│   └── table_model_ch/
├── output/                 # Default output directory for extracted files
├── processors/
│   ├── __init__.py
│   ├── content_merger.py
│   ├── table_processor.py
│   └── text_formatter.py
├── test/
│   ├── test_data/          # Sample images for testing
│   └── test_output/        # Output from test runs
├── utils/
│   ├── __init__.py
│   ├── config.py
│   ├── coordinate_utils.py
│   ├── text_utils.py
│   └── validation.py
├── app.log                 # Log file
├── bilibili_downloader.py
├── comprehensive_diagnosis.py
├── config.yaml             # Configuration file for the script
├── correct_function.py
├── extract_text_from_images_original.py # Original monolithic script
├── extract_text_from_images.py          # Main modular script
├── extract_video_snapshots.py
├── extracted_text.docx
├── install_dependencies.py
├── PROJECT_REBRANDING.md
├── pytest.ini
├── README.md
├── REFACTORING_COMPLETION_REPORT.md
├── REFACTORING_PLAN.md
├── REFACTORING_VIEWS.md
├── requirements.txt
├── run_extraction.bat
├── start_project.bat
└── VERSION.md
```

## Usage

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure**:
    - Modify `config.yaml` to set paths for models, input/output directories, etc.
3.  **Run the script**:
    ```bash
    python extract_text_from_images.py <image_path_or_directory>
    ```

## Key Modules

-   `extract_text_from_images.py`: Main script to orchestrate the OCR process.
-   `core/ocr_engine.py`: Handles the OCR operations using PaddleOCR.
-   `core/table_detector.py`: Detects tables in the image.
-   `core/layout_analyzer.py`: Analyzes the layout of the document.
-   `core/text_processor.py`: Processes the extracted text.
-   `processors/table_processor.py`: Processes detected tables.
-   `exporters/docx_exporter.py`: Exports the extracted content to a DOCX file.
-   `utils/`: Contains utility functions for configuration, text manipulation, etc.
-   `config/`: Contains configuration settings and patterns.

## Logging

The script logs its operations to `app.log`. This includes detailed information about the extraction process, errors, and warnings.

## 注意事项与已知问题

### 🔧 环境依赖
- **LibreOffice 依赖**: Office文档转换的备用方法依赖LibreOffice。虽然不是必需的，但建议安装以获得更好的兼容性。
- **中文字体**: TXT转PDF功能使用`SimSun`(宋体)。如系统缺失该字体，可能导致中文显示异常。
- **Python版本**: 需要Python 3.7+，推荐使用Python 3.8或更高版本。

### ⚡ 性能考虑
- **文件大小**: 建议单个文件不超过500MB，批量处理不超过10个文件。
- **转换时间**: PDF转换可能需要较长时间，特别是包含复杂图表的文件。
- **并发限制**: 开发服务器为单线程，生产环境建议使用Gunicorn/uWSGI。

### 🐛 已知问题
- **LibreOffice PDF转Excel**: 在某些环境中可能不可用，已默认使用pdfplumber方法。
- **复杂PDF**: 包含复杂布局或加密的PDF可能转换效果不佳。
- **OCR准确性**: 图片转文字的准确性取决于图片质量和PaddleOCR模型。

### 📝 开发注意
- **日志记录**: 详细错误信息记录在`extract_web/converter.log`中。
- **调试模式**: 开发时建议开启Django的DEBUG模式以获得详细错误信息。
- **虚拟环境**: 强烈建议使用虚拟环境以避免依赖冲突。

## 🚀 未来发展规划

### 📈 功能增强
- **更多格式支持**: 
  - 图片格式：WebP、TIFF、SVG等
  - 文档格式：RTF、ODT、Pages等
  - 压缩包：ZIP、RAR内文件批量转换
- **高级转换选项**:
  - PDF转换质量设置 (DPI、压缩率)
  - OCR语言选择和精度调优
  - 批量重命名和文件组织

### ⚡ 性能优化
- **异步任务处理**: 使用Celery+Redis实现后台任务队列 (尤其适用于耗时较长的视频处理和复杂文档转换)
- **进度跟踪**: 实时显示转换进度和预估完成时间 (视频处理已初步实现流式进度)
- **缓存机制**: 智能缓存常用转换结果
- **并发处理**: 支持多文件并行转换

### 🛠️ 技术改进
- **容器化部署**: Docker支持，一键部署
- **API接口**: RESTful API，支持第三方集成
- **云存储**: 支持阿里云OSS、AWS S3等云存储
- **微服务架构**: 转换服务独立部署

### 🧪 质量保证
- **完整测试覆盖**: 单元测试、集成测试、端到端测试
- **性能监控**: 转换成功率、响应时间监控
- **错误恢复**: 自动重试和错误恢复机制
- **安全加固**: 文件类型验证、病毒扫描

### 📱 用户体验
- **移动端优化**: 响应式设计改进
- **批量操作**: 文件夹上传、批量下载
- **转换模板**: 预设转换配置和批量应用
- **分享功能**: 转换结果分享和协作

