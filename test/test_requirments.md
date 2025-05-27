# 测试需求与用例规划

## 一、 测试环境与文件结构

### 1.1 目录结构

-   `test_data/`: 存放所有原始测试输入文件。
-   `test_script/`: 存放Python测试脚本 (例如使用 `unittest` 或 `pytest`)。
-   `test_output/`: 存放测试脚本运行后生成的转换结果文件，用于比对和验证。
-   `test_reports/`: (可选) 存放测试报告 (例如HTML格式的覆盖率报告或测试结果报告)。

### 1.2 测试数据命名规范

所有位于 `test_data/` 目录下的测试文件应遵循以下命名约定，以便清晰地表明其用途：

#  测试文件说明
1. 所有的test文件都在test_data目录下
2. 所有的test文件都以test_xxx开头
3. test_xxx.jpg是用作测试图片转xxx
4. test_txt.txt是用作测试txt转xxx
5. test_excel.xlsx是用作测试excel转xxx
6. test_pdf.pdf是用作测试pdf转xxx
7. test_ppt.pptx是用作测试ppt转xxx
8. test_word.docx是用作测试word转xxx
9. test_txt.pdf用作测试pdf转txt
10. test_ppt.pdf用作测试pdf转ppt
11. test_excel.pdf用作测试pdf转excel
12. test_word.pdf用作测试pdf转word

## 二、 测试范围与主要功能点

基于 `extract_web/GUI-Requirements.md` 中定义的功能，测试将覆盖以下主要转换路径：

### 2.1 图片转文件 (`imgToFile`)

-   **子功能：**
    -   图片 (`.jpg`, `.png`, `.bmp`) 转 Word (`.docx`)
    -   图片 (`.jpg`, `.png`, `.bmp`) 转 PDF (`.pdf`)
-   **测试维度：**
    -   单个文件转换。
    -   多个文件合并转换（合并到单一 `.docx` 或 `.pdf`）。
    -   不同图片格式的兼容性。
    -   内容提取的准确性（依赖OCR，此部分可能更多是集成测试或手动检查）。

### 2.2 文件转PDF (`fileToPdf`)

-   **子功能：**
    -   Word (`.doc`, `.docx`) 转 PDF
    -   Excel (`.xls`, `.xlsx`) 转 PDF
    -   PPT (`.ppt`, `.pptx`) 转 PDF
    -   TXT (`.txt`) 转 PDF
-   **测试维度：**
    -   单个文件转换。
    -   多个文件合并转换（合并到单一 `.pdf`）。
    -   不同Office文件版本的兼容性（如果可行）。
    -   格式保留程度（依赖LibreOffice）。

### 2.3 PDF转文件 (`pdfToFile`)

-   **子功能：**
    -   PDF 转 Word (`.docx`)
    -   PDF 转 Excel (`.xlsx`)
    -   PDF 转 PPT (`.pptx`)
    -   PDF 转 TXT (`.txt`)
-   **测试维度：**
    -   单个文件转换。
    -   多个文件合并转换（合并到单一 `.docx` 或 `.txt`；对于 `.xlsx` 和 `.pptx`，合并当前不支持，应测试其按单个文件转换的行为，即使勾选了合并）。
    -   内容提取的准确性（表格、文本、图片等）。
    -   对不同类型的PDF（例如，扫描版 vs. 原生版）的处理效果（当前主要基于文本提取）。

## 三、 测试用例设计原则

1.  **独立性**：每个测试用例应尽可能独立，不依赖于其他测试用例的执行结果。
2.  **可重复性**：测试用例在相同环境下应能重复执行并得到一致的结果。
3.  **覆盖率**：尽可能覆盖所有主要功能路径和重要的边界条件。
4.  **原子性**：每个测试用例聚焦于一个特定的功能点或场景。
5.  **命名清晰**：测试函数/方法名应清晰描述其测试目的。
6.  **断言明确**：每个测试用例应有明确的成功或失败的断言条件（例如，文件是否存在、文件内容是否符合预期、API响应是否正确）。
7.  **资源清理**：测试用例执行完毕后，应清理生成的临时文件或状态（如果适用，`test_output/` 中的文件通常保留用于检查）。

## 四、 Python测试用例编写计划

### 4.1 测试框架选择

-   建议使用 `pytest` 或 Python 内置的 `unittest` 框架。`pytest` 更简洁，插件丰富，推荐使用。

### 4.2 测试脚本结构

在 `test_script/` 目录下，可以按功能模块创建测试文件：

-   `test_img_to_file.py`
-   `test_file_to_pdf.py`
-   `test_pdf_to_file.py`
-   `test_views_api.py` (用于直接测试Django视图API的请求和响应)
-   `test_converters_ bezpośrednio.py` (可选，用于单元测试各个转换器模块的核心函数)

### 4.3 通用测试辅助函数

可以创建一个 `conftest.py` (如果使用 `pytest`) 或一个 `test_utils.py` 来存放通用的辅助函数，例如：

-   创建临时测试文件。
-   模拟文件上传。
-   调用Django测试客户端 (`django.test.Client`)。
-   比较文件内容（哈希值、特定文本等）。
-   清理 `test_output/` 目录。

### 4.4 示例测试用例骨架 (伪代码)

**`test_script/test_views_api.py` (使用Django Test Client 和 Pytest)**

```python
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from pathlib import Path

# Assume test_data_path is defined, pointing to test_data/
# Assume client is a Django test client fixture

def test_image_to_word_single_no_merge(client, test_data_path):
    # 1. 准备测试数据 (source_image.jpg)
    image_path = test_data_path / "source_image.jpg"
    with open(image_path, "rb") as f_img:
        image_file = SimpleUploadedFile(f_img.name, f_img.read(), content_type="image/jpeg")

    # 2. 构建请求数据
    url = reverse("converter:process_images") # 假设这是你的视图URL名
    data = {
        "main_tab": "imgToFile",
        "sub_tab": "imgToWord",
        "merge_output": "false",
        "output_format": "docx",
        "images": [image_file]
    }

    # 3. 发送POST请求
    # 需要登录用户，假设已有登录逻辑或fixture
    # client.login(username="testuser", password="password")
    response = client.post(url, data)

    # 4. 断言响应状态码
    assert response.status_code == 200
    response_data = response.json()

    # 5. 断言结果
    assert response_data["merge_output"] == False
    assert len(response_data["results"]) == 1
    result = response_data["results"][0]
    assert result["status"] == "success"
    assert result["original_name"] == "source_image.jpg"
    assert result["converted_name"].endswith(".docx")
    
    # 6. (可选) 验证转换后的文件是否存在于 test_output/ (或实际转换路径)
    #    并进行内容校验 (如果需要)
    #    注意：视图函数直接操作的是用户历史目录，测试时可能需要模拟或检查这些路径
```

## 五、 执行与报告

-   测试脚本应能通过命令行方便地执行 (例如 `pytest test_script/`)。
-   考虑集成覆盖率工具 (如 `coverage.py`) 生成代码覆盖率报告。
-   对于失败的测试用例，应提供清晰的错误信息，便于定位问题。

---
**注意**: 上述Python骨架仅为示例，实际实现时需要根据Django项目的用户认证、文件存储逻辑、视图的具体实现进行调整。
测试用户和其对应的历史文件目录结构也需要考虑在测试的setup和teardown中。
对于直接测试转换器模块的单元测试，会更侧重于函数的输入输出，mock掉外部依赖（如LibreOffice调用）。


# 运行 pytest:
打开您的项目根目录（包含 manage.py 和 test 文件夹的那个目录）的命令行终端。
执行 pytest 命令（或者 pytest -v 查看更详细的输出）。
确保您的 Django 设置 (DJANGO_SETTINGS_MODULE) 对 pytest 可见。
