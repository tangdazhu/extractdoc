# 图片文字提取工具

本项目是一个Python脚本，用于从指定目录中的图片（当前支持JPG格式）提取文字，并将提取的文字内容整理后保存到一个Word (.docx)文档中。同时，脚本运行过程中的信息和错误会记录到日志文件中。

## 功能特性

- **文字提取**：使用PaddleOCR进行图片中的文字识别，支持中文。
- **批量处理**：自动处理指定输入目录下的所有JPG图片。
- **自然排序**：对图片文件名进行自然排序（例如：1.jpg, 2.jpg, ..., 10.jpg），确保处理顺序符合预期。
- **Word文档输出**：将每张图片提取的文字作为一个独立部分（以图片文件名作为标题），添加到Word文档中，并在每张图片内容后添加分页符。
- **可配置性**：通过`config.yaml`文件配置图片输入目录、Word输出文件名和日志文件名。
- **日志记录**：记录脚本的运行信息、警告和错误到指定的日志文件，并同时输出到控制台。

## 项目结构

```
.
├── extract_text_from_images.py  # 主程序脚本
├── config.yaml                  # 配置文件
├── requirements.txt             # Python依赖包列表
├── his_pic/                     # 默认的图片输入目录 (示例)
│   └── example1.jpg
│   └── example2.jpg
├── app.log                      # 默认的日志输出文件 (程序运行后生成)
└── extracted_text.docx          # 默认的Word输出文件 (程序运行后生成)
└── README.md                    # 本说明文件
```

**注意**: `his_pic/` 目录需要您自行创建，并将待处理的图片放入其中，或者通过修改 `config.yaml` 中的 `input_directory` 指定其他图片目录。

## 安装依赖

在运行脚本之前，请确保已安装所需的Python库。可以通过以下命令使用`requirements.txt`文件安装所有依赖：

```bash
pip install -r requirements.txt
```

依赖库包括：
- `PyYAML`: 用于解析`config.yaml`配置文件。
- `paddleocr`: 用于OCR文字识别。
- `Pillow`: `paddleocr`的依赖库，用于图像处理。
- `python-docx`: 用于创建和编辑Word (.docx)文档。

## 配置文件 (`config.yaml`)

项目使用`config.yaml`文件进行配置。如果此文件不存在，脚本首次运行时会自动创建一个默认的配置文件。

默认配置如下：

```yaml
input_directory: "his_pic"       # 存放待识别图片的目录名称
output_filename: "extracted_text.docx" # 输出Word文档的文件名
log_file: "app.log"              # 日志文件的文件名
```

您可以根据需要修改这些配置项：
- `input_directory`: 指定存放JPG图片的文件夹路径。可以是相对路径（相对于脚本所在位置）或绝对路径。
- `output_filename`: 指定生成的Word文档的名称。
- `log_file`: 指定日志文件的名称。

## 运行方法

1.  **准备图片**：将需要提取文字的JPG图片放入`config.yaml`中`input_directory`所指定的目录（默认为`his_pic/`）。
2.  **配置检查** (可选)：根据需要修改`config.yaml`文件中的配置。
3.  **运行脚本**：在项目根目录下打开终端或命令行，执行以下命令：

    ```bash
    python extract_text_from_images.py
    ```

4.  **查看结果**：
    - 提取的文字内容会保存在`config.yaml`中`output_filename`所指定的Word文档中（默认为`extracted_text.docx`）。
    - 脚本的运行日志会保存在`config.yaml`中`log_file`所指定的日志文件中（默认为`app.log`），并同时在控制台输出。

## 注意事项

- **PaddleOCR模型下载**：首次运行PaddleOCR时，会自动下载所需的模型文件。请确保您的网络连接正常。如果下载速度较慢或失败，可能需要配置代理或手动下载模型。
- **图片格式**：当前脚本硬编码为处理`.jpg`文件。如果需要处理其他格式（如.png），需要修改`extract_text_from_images.py`脚本中`glob.glob(os.path.join(input_dir, \'*.jpg\'))`这一行。
- **错误处理**：脚本包含基本的错误处理机制。如果图片无法处理或发生其他错误，会在日志中记录详细信息。
- **中文字体**：Word文档默认使用`SimSun` (宋体) 字体，字号为11pt。如需更改，可以修改`extract_text_from_images.py`脚本中设置文档样式的相关代码。
- **升级到最新的 paddleocr 版本**：'pip install --upgrade paddleocr paddlepaddle'

