# 图片文字与表格智能提取工具

本项目是一个Python脚本，用于从指定目录中的图片（当前支持JPG格式）智能提取文字和表格，并将内容整理后保存到Word (.docx)文档中。脚本运行过程中的信息和错误会记录到日志文件中。

## 功能特性

- **多种表格图片智能还原**：支持多个特殊表格图片（如6.jpg、7.jpg等）的定制还原，所有特殊表格图片的处理逻辑通过 `special_table_handlers` 注册表统一管理，易于扩展和维护。
- **通用表格自动还原**：非特殊图片自动检测表格并还原为Word表格，无需手动指定。
- **普通文本处理**：非表格图片全部以普通段落方式输出，不会被错误地放入表格。
- **自动分割表格与正文**：自动区分表格区域和正文区域，正文内容不会被误放入表格。
- **批量处理**：自动处理指定输入目录下的所有JPG图片，按自然顺序排序。
- **Word文档输出**：每张图片内容作为独立部分（以图片文件名为标题）输出到Word文档，图片间自动分页。
- **可配置性**：通过`config.yaml`文件配置图片输入目录、Word输出文件名和日志文件名。
- **日志记录**：详细记录运行信息、警告和错误到日志文件，并同步输出到控制台。

## 项目结构

```
.
├── extract_text_from_images.py  # 主程序脚本
├── config.yaml                  # 配置文件
├── requirements.txt             # Python依赖包列表
├── his_pic/                     # 默认图片输入目录
│   └── 1.jpg
│   └── 6.jpg
├── app.log                      # 日志输出文件（程序运行后生成）
└── extracted_text.docx          # Word输出文件（程序运行后生成）
└── README.md                    # 本说明文件
```

**注意**: `his_pic/` 目录需自行创建，并将待处理图片放入其中，或通过修改 `config.yaml` 的 `input_directory` 指定其他目录。

## 安装依赖

请先安装Python 3.7及以上版本。然后在项目根目录下执行：

```bash
pip install -r requirements.txt
```

依赖库包括：
- `PyYAML`：解析配置文件
- `paddleocr`：OCR文字识别
- `Pillow`：图像处理
- `python-docx`：Word文档生成
- `beautifulsoup4`：HTML表格解析辅助
- `numpy`：数值计算辅助

## 配置文件（config.yaml）

默认配置如下：

```yaml
input_directory: "his_pic"       # 图片目录
output_filename: "extracted_text.docx" # 输出Word文件名
log_file: "app.log"              # 日志文件名
```

可根据需要修改：
- `input_directory`：图片文件夹路径（相对或绝对路径）
- `output_filename`：生成的Word文档名称
- `log_file`：日志文件名称

## 运行方法

1.  准备图片：将需要识别的JPG图片放入`input_directory`指定目录（默认`his_pic/`）。
2.  配置检查：如有需要，修改`config.yaml`。
3.  运行脚本：

    ```bash
    python extract_text_from_images.py
    ```

4.  查看结果：
    - 提取内容保存在`output_filename`指定的Word文档中。
    - 日志保存在`log_file`指定的日志文件中，并同步输出到控制台。

## 特殊表格图片的定制还原与扩展

- 所有特殊表格图片的处理逻辑通过 `special_table_handlers` 字典注册，key为图片文件名，value为处理函数。
- 例如，6.jpg 的特殊还原逻辑已封装为 `handle_table_6jpg`，未来只需实现新的处理函数并注册到 `special_table_handlers` 即可。
- 主循环自动分发，无需写一堆 if-else，结构清晰，易于维护和扩展。
- 非特殊图片自动走通用表格还原逻辑，无需手动干预。

**添加新特殊表格图片的步骤：**
1. 在脚本中实现新的处理函数（如 `handle_table_7jpg`）。
2. 在 `special_table_handlers` 字典中注册：`"7.jpg": handle_table_7jpg`。
3. 无需修改主循环，其会自动分发。

## 注意事项

- **首次运行PaddleOCR会自动下载模型文件，请确保网络畅通。**
- **仅处理JPG图片，如需支持PNG等格式请修改脚本中的glob匹配规则。**
- **Word文档默认使用宋体（SimSun）11号字体，可在脚本中自定义。**
- **如需升级PaddleOCR，可执行：**

```bash
pip install --upgrade paddleocr paddlepaddle
```

- **如遇图片表格结构复杂或识别不理想，可适当调整特殊表格处理函数或优化图片质量。**

