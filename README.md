# Django Web应用：extract_web - 文件转换与处理平台

本项目是一个基于 Django 框架构建的 Web 应用程序，旨在提供一个用户友好的界面，用于多种文件格式之间的转换和处理。它是早期命令行脚本 `extract_text_from_images.py` 的功能扩展和Web化。

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
    - **PDF转文件** (开发中):
        - PDF 转 Word (.docx) (使用 `pdf2docx`)。
        - PDF 转 Excel (.xlsx) (使用 `pdfplumber`)。
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
    - 提供文件上传、清空列表、开始转换、合并输出等操作按钮。
    - 动态显示转换结果和下载链接。

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
│   │   └── ... (其他辅助模块)
│   ├── media/                    # 存放用户上传和转换后的文件 (通过 settings.MEDIA_ROOT 配置)
│   │   └── his_pic/              # 用户历史文件根目录
│   ├── db.sqlite3                # SQLite 数据库文件 (默认)
│   └── ... (其他 Django 项目文件)
├── requirements.txt              # Python 依赖包列表
└── README.md                     # 本说明文件
```

**注意**:
- `media/his_pic/` 目录及其子目录会在用户注册和文件上传/转换时自动创建。
- `extract_text_from_images.py` 和 `config.yaml` 是早期命令行版本的残留文件，与当前Web应用无关。

## 安装与运行

1.  **环境准备**:
    *   确保已安装 Python 3.7 或更高版本。
    *   建议使用虚拟环境 (如 venv 或 conda)。
    *   **Windows 用户**: 部分转换功能 (如 Excel/PPT 转 PDF) 依赖 LibreOffice。请确保已安装 LibreOffice 并且其 `soffice.exe` 所在路径已添加到系统的 `PATH` 环境变量中，或者在代码中硬编码其路径。
    *   **Linux 用户**: 同样需要 LibreOffice。可以通过包管理器安装 (例如 `sudo apt-get install libreoffice`)。

2.  **克隆项目或下载代码**。

3.  **安装依赖**:
    在项目根目录 (`extract_doc/`) 下打开终端，激活虚拟环境后执行：
    ```bash
    pip install -r requirements.txt
    ```
    **注意**: 如果在安装 `paddleocr` 时遇到问题，请参考其官方文档进行安装。`requirements.txt` 中的 `paddleocr` 可能不包含 `paddlepaddle` GPU/CPU 版本，您可能需要单独安装 `paddlepaddle` (例如 `pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple` 或 `pip install paddlepaddle-gpu ...`)。

4.  **数据库迁移**:
    进入 Django 项目目录 (`extract_doc/extract_web/`)，然后执行：
    ```bash
    python manage.py migrate
    ```

5.  **创建超级用户 (可选, 但建议)**:
    如果需要访问 Django Admin 后台或使用预设的管理员功能，请创建一个超级用户：
    ```bash
    python manage.py createsuperuser
    ```
    按照提示设置用户名、邮箱和密码。或者，代码中已尝试创建默认管理员 `admin` / `admin`，如果迁移后未自动创建，可手动创建。

6.  **运行开发服务器**:
    在 Django 项目目录 (`extract_doc/extract_web/`) 下执行：
    ```bash
    python manage.py runserver
    ```
    默认情况下，应用将在 `http://127.0.0.1:8000/` 上运行。

7.  **访问应用**:
    打开浏览器，访问上述地址。
    - 注册新用户或使用 `admin`/`admin` 登录 (如果创建成功)。

## 主要依赖库

- `Django`: Web 框架。
- `paddleocr`: 用于图片中的文字识别 (OCR)。
- `python-docx`: 创建和操作 Word (.docx) 文件。
- `Pillow`: 图像处理。
- `PyPDF2`: 合并 PDF 文件。
- `docx2pdf`: 将 Word 文件转换为 PDF。
- `reportlab`: 创建 PDF 文件 (用于 TXT 转 PDF)。
- `openpyxl`: 读写 Excel (.xlsx) 文件。
- `pdfplumber`: 从 PDF 中提取文本和表格。
- `pdf2docx`: 将 PDF 转换为 Word (.docx) 文件。
- `comtypes` (Windows): 用于通过 COM 接口与 Microsoft Office 应用程序交互 (目前 Excel 转 PDF 的 COM 方式已移除，但库仍可能在依赖中)。
- `LibreOffice`: 外部依赖，用于多种文档格式 (Word, Excel, PowerPoint) 到 PDF 的转换。

## 注意事项与已知问题

- **LibreOffice 依赖**: Word/Excel/PPT 转 PDF 的核心功能依赖于正确安装并配置好的 LibreOffice。确保 `soffice` 命令在系统路径中可用。
- **中文字体**: TXT 转 PDF 等功能使用了 `SimSun` (宋体) 作为中文字体。如果系统缺失该字体，可能导致中文显示为方框或乱码。
- **性能**: 大文件或大量文件的批量转换可能会比较耗时。
- **错误处理**: 部分复杂或损坏的文件可能导致转换失败。后端日志 (`extract_web/converter.log`) 会记录详细错误。
- **并发**: 当前开发服务器是单线程的，不适合高并发生产环境。生产部署时应使用 Gunicorn/uWSGI 等 WSGI 服务器。
- **Pylance/Linter 提示**: 开发过程中可能遇到 Pylance 等 linter 关于某些导入 (如 `docx2pdf`) 无法解析的提示。这通常是编辑器/IDE 的 Python 解释器配置问题，不一定影响 Django 应用的实际运行，只要库已正确安装在项目使用的虚拟环境中。

## 未来可能的增强

- 更全面的文件格式支持。
- 异步任务处理 (例如使用 Celery) 以优化长时间运行的转换任务。
- 更精细的管理员文件管理功能。
- 详细的转换任务队列和状态显示。
- 单元测试和集成测试。

