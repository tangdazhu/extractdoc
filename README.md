# Django Web应用：extract_web - 文件转换与处理平台

本项目是一个基于 Django 框架构建的 Web 应用程序，旨在提供一个用户友好的界面，用于多种文件格式之间的转换和处理。它是早期命令行脚本 `extract_text_from_images.py` 的功能扩展和Web化。

## 🌟 项目特色

- **🔄 多格式转换支持**: 支持图片、PDF、Word、Excel、PowerPoint、TXT等多种格式互转
- **🎯 智能转换策略**: 每种转换都提供多种方法，自动选择最佳方案或允许用户手动选择
- **📊 专业PDF表格提取**: 使用pdfplumber专门优化PDF中的表格数据提取
- **🔧 一键部署**: 提供自动安装脚本，简化环境配置和依赖安装
- **👥 多用户支持**: 完整的用户认证系统和个人文件管理
- **📱 现代化界面**: 响应式设计，支持拖拽上传，实时状态反馈
- **🔒 安全可靠**: 用户文件隔离存储，支持批量处理和历史记录管理

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
    - **文件转PDF**:
        - Word (.doc, .docx) 转 PDF。
        - Excel (.xls, .xlsx) 转 PDF (优先使用 LibreOffice, 其次 OpenPyXL 作为后备)。
        - PowerPoint (.ppt, .pptx) 转 PDF (使用 LibreOffice)。
        - TXT (.txt) 转 PDF (使用 `reportlab`)。
        - 支持合并多个输入文件到一个PDF。
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
    - 主选项卡区分不同转换类型："图片转文件", "文件转PDF", "PDF转文件"。
    - 子选项卡用于选择具体的转换操作 (如 "图片转Word", "Excel转PDF")。
    - 智能转换方法选择：用户可以选择不同的转换方法 (如PDF转Word时选择pdf2docx或Office转换方式)。
    - 提供文件上传、清空列表、开始转换、合并输出等操作按钮。
    - 动态显示转换结果和下载链接。
    - 实时转换状态反馈和错误处理提示。

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
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── pic_file_converter.py # 图片转文件逻辑
│   │   ├── excel_pdf_converter.py # Excel 转 PDF 逻辑
│   │   ├── ppt_pdf_converter.py  # PPT 转 PDF 逻辑
│   │   ├── txt_to_pdf_converter.py # TXT 转 PDF 逻辑
│   │   ├── pdf_to_excel_converter.py # PDF 转 Excel 逻辑
│   │   ├── pdf_to_word_converter.py  # PDF 转 Word 逻辑
│   │   ├── pdf_to_ppt_converter.py   # PDF 转 PPT 逻辑
│   │   ├── pdf_to_txt_converter.py   # PDF 转 TXT 逻辑
│   │   ├── word_to_pdf_converter.py  # Word 转 PDF 逻辑
│   │   ├── libreoffice_converter.py  # LibreOffice 通用转换器
│   │   └── ... (其他辅助模块)
│   ├── media/                    # 存放用户上传和转换后的文件 (通过 settings.MEDIA_ROOT 配置)
│   │   └── his_pic/              # 用户历史文件根目录
│   ├── db.sqlite3                # SQLite 数据库文件 (默认)
│   └── ... (其他 Django 项目文件)
├── requirements.txt              # Python 依赖包列表
├── install_dependencies.py      # 自动安装脚本
├── utils.py                      # 工具函数 (配置加载、日志设置)
├── extract_text_from_images.py  # 早期命令行脚本 (已集成到Web应用)
├── VERSION.md                    # 版本历史和更新日志
└── README.md                     # 本说明文件
```

**注意**:
- `media/his_pic/` 目录及其子目录会在用户注册和文件上传/转换时自动创建。
- `extract_text_from_images.py` 是早期命令行脚本，现已集成到Web应用中。
- `install_dependencies.py` 是新增的自动安装脚本，简化项目部署流程。

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
   - 支持批量上传（最多10个文件，单个文件≤10MB）

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

## 主要依赖库

### 核心框架
- `Django==5.2.1`: Web框架

### OCR和图像处理
- `paddleocr==2.7.3`: OCR文字识别
- `pillow==10.3.0`: 图像处理
- `numpy==1.26.4`: 数值计算支持
- `beautifulsoup4==4.12.3`: HTML解析

### PDF处理
- `PyMuPDF>=1.23.0`: PDF文本提取和操作 (fitz)
- `pdfplumber>=0.10.0`: PDF表格提取 (PDF→Excel主要方法)
- `pdf2docx>=0.5.0`: PDF转Word
- `PyPDF2==3.0.1`: PDF合并和分割

### Office文档处理
- `python-docx==1.1.2`: Word文档生成和操作
- `python-pptx>=0.6.21`: PowerPoint演示文稿创建
- `openpyxl==3.1.5`: Excel文件读写
- `docx2pdf==0.1.8`: Word转PDF (需要Office或LibreOffice)
- `comtypes==1.4.11`: Windows COM接口 (仅Windows)

### PDF生成和报告
- `reportlab==4.4.1`: PDF生成 (TXT→PDF)

### 配置和解析
- `PyYAML==6.0.1`: YAML配置文件解析

### 测试依赖 (开发环境)
- `pytest>=7.4.0`: 测试框架
- `pytest-django>=4.5.2`: Django测试集成

### 外部依赖
- `LibreOffice`: Office文档转换 (可选，需单独安装)
- `Microsoft Office`: Windows原生Office支持 (可选)

## 注意事项与已知问题

### 🔧 环境依赖
- **LibreOffice 依赖**: Office文档转换的备用方法依赖LibreOffice。虽然不是必需的，但建议安装以获得更好的兼容性。
- **中文字体**: TXT转PDF功能使用`SimSun`(宋体)。如系统缺失该字体，可能导致中文显示异常。
- **Python版本**: 需要Python 3.7+，推荐使用Python 3.8或更高版本。

### ⚡ 性能考虑
- **文件大小**: 建议单个文件不超过10MB，批量处理不超过10个文件。
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
- **异步任务处理**: 使用Celery+Redis实现后台任务队列
- **进度跟踪**: 实时显示转换进度和预估完成时间
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

