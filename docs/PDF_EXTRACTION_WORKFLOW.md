# PDF提取工作流程

## 三个工具的角色

| 工具 | 角色 | 使用时机 | 速度 | 准确率 |
|------|------|---------|------|--------|
| **pdfplumber** | 主力 | 总是使用 | 快(0.1秒/页) | 高(标准PDF 95%) |
| **PyMuPDF (fitz)** | 图片提取 | 总是使用 | 快(0.05秒/页) | 高(99%) |
| **paddleocr** | Fallback | 检测到问题时 | 慢(2-5秒/页) | 中(85%) |

## 完整工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                     PDF文件输入                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段1: pdfplumber 提取 (主力)                                │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 1. 提取文本: page.extract_text()                            │
│    - 获取每页的纯文本内容                                    │
│    - 速度: ~0.05秒/页                                       │
│                                                             │
│ 2. 提取表格: page.extract_tables()                          │
│    - 策略1: lines (基于表格线)                              │
│    - 策略2: text (基于文本位置,如果策略1失败)                │
│    - 速度: ~0.05秒/页                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段2: 智能修复 (pdfplumber结果)                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 1. 分离表头和数据                                            │
│    - 检测第一行是否包含换行符                                │
│    - 分离: "版本\n0.1" → 表头="版本", 数据="0.1"            │
│                                                             │
│ 2. 跨行合并                                                  │
│    - 检测: 某行只有"LLM"                                     │
│    - 合并: "LLM" + 下一行内容 → "增加 LLM 模型..."          │
│                                                             │
│ 3. 智能重组                                                  │
│    - 检测: "LLM\n首次发布..."                               │
│    - 重组: "首次发布: LLM 基础..."                          │
│                                                             │
│ 4. 清理换行符                                                │
│    - 将单元格内的换行符替换为空格                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段3: 问题检测                                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 检测1: 重复行                                                │
│   - 相邻行的内容列是否相同                                   │
│   - 示例: 第3行和第4行都是"增加 LLM 模型..."                │
│                                                             │
│ 检测2: 空表格                                                │
│   - 表格是否为空或只有表头                                   │
│                                                             │
│ 检测3: 列数异常                                              │
│   - 某些行的列数明显少于其他行                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    有问题? (重复/空/异常)
                            ↓
                    ┌───────┴───────┐
                   是               否
                    ↓                ↓
┌─────────────────────────────┐  使用pdfplumber结果
│ 阶段4: paddleocr Fallback   │       ↓
│ ━━━━━━━━━━━━━━━━━━━━━━━━━ │       跳到阶段5
│ 1. 页面转图片               │
│    - 使用PyMuPDF渲染        │
│    - 2倍缩放提高清晰度      │
│                             │
│ 2. OCR识别                  │
│    - paddleocr.ocr()        │
│    - 返回: 文字+坐标+置信度 │
│                             │
│ 3. 过滤页眉页脚             │
│    - 过滤顶部5%的内容       │
│    - 过滤底部5%的内容       │
│                             │
│ 4. 按Y坐标分组为行          │
│    - 容差: 10像素           │
│                             │
│ 5. 按X坐标排序为列          │
│    - 每行内从左到右排序     │
│                             │
│ 速度: ~2-5秒/页             │
└─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段5: 表格规范化                                            │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 1. 找出最大列数                                              │
│    max_cols = max(len(row) for row in table)                │
│                                                             │
│ 2. 补齐所有行                                                │
│    if len(row) < max_cols:                                  │
│        row += [''] * (max_cols - len(row))                  │
│                                                             │
│ 确保: 所有行的列数一致,避免渲染时索引越界                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段6: PyMuPDF 提取图片                                      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ 1. 遍历所有页面                                              │
│    for page in pdf_document:                                │
│        image_list = page.get_images(full=True)              │
│                                                             │
│ 2. 提取图片(基于xref)                                        │
│    - xref是PDF中图片的唯一标识                               │
│    - 跳过已提取的xref(去重)                                  │
│                                                             │
│ 3. 过滤小图片                                                │
│    - 宽度或高度 < 200px → 跳过                              │
│    - 宽高比 > 10 → 跳过(横幅/分隔线)                        │
│                                                             │
│ 4. 保存图片                                                  │
│    - 保存到临时目录                                          │
│    - 记录: 页码、路径、尺寸、xref                            │
│                                                             │
│ 速度: ~0.05秒/页                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    返回结果                                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│ {                                                           │
│   "text": "全文文本",                                        │
│   "tables": [                                               │
│     {"page": 2, "data": [["版本","内容",...], ...]},       │
│   ],                                                        │
│   "images": [                                               │
│     {"page": 5, "path": "page5_img1.jpeg", ...},           │
│   ]                                                         │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## 使用场景决策树

### 场景1: 标准PDF (文本层完整)

**特征**:
- PDF是从Word/PPT等生成的
- 文本可以被选中和复制
- 表格结构规范

**使用工具**:
```
✅ pdfplumber (文本+表格)
✅ PyMuPDF (图片)
❌ paddleocr (不需要)
```

**流程**:
```
pdfplumber提取 → 智能修复 → 检测(无问题) → PyMuPDF提取图片 → 完成
```

**速度**: ~0.15秒/页

---

### 场景2: 复杂表格PDF

**特征**:
- 表格有合并单元格
- 表格线不规范
- 文字位置偏移

**使用工具**:
```
✅ pdfplumber (文本+表格,可能失败)
✅ PyMuPDF (图片)
✅ paddleocr (fallback)
```

**流程**:
```
pdfplumber提取 → 智能修复 → 检测(有问题!) → paddleocr重新提取 → 规范化 → PyMuPDF提取图片 → 完成
```

**速度**: ~2-5秒/页 (因为触发OCR)

---

### 场景3: 扫描件PDF

**特征**:
- PDF是扫描的图片
- 文本无法被选中
- 没有文本层

**使用工具**:
```
❌ pdfplumber (提取不到内容)
✅ PyMuPDF (图片)
✅ paddleocr (必须)
```

**流程**:
```
pdfplumber提取 → 检测(空表格!) → paddleocr提取 → 规范化 → PyMuPDF提取图片 → 完成
```

**速度**: ~2-5秒/页

---

### 场景4: 纯图片PDF

**特征**:
- PDF只包含图片,没有文字
- 例如:海报、设计稿

**使用工具**:
```
❌ pdfplumber (没有文字)
✅ PyMuPDF (图片)
❌ paddleocr (不需要)
```

**流程**:
```
pdfplumber提取(空) → PyMuPDF提取图片 → 完成
```

**速度**: ~0.05秒/页

## 代码位置

### 主流程
- **文件**: `document_generation.py`
- **函数**: `_extract_pdf_multimodal()`
- **行数**: 第110-440行

### 关键代码段

#### 1. pdfplumber提取 (第128-167行)
```python
import pdfplumber

with pdfplumber.open(str(pdf_path)) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        # 提取文本
        page_text = page.extract_text()
        
        # 提取表格
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            # ... 参数配置
        })
```

#### 2. 智能修复 (第176-300行)
```python
# 分离表头和数据
if '\n' in str(cell):
    parts = str(cell).split('\n', 1)
    header_part = parts[0]
    data_part = parts[1] if len(parts) > 1 else ''

# 跨行合并
if str(row[1]).strip() == 'LLM':
    # 从下一行合并内容
    row[1] = f"增加 LLM {next_row[1]}"
```

#### 3. 问题检测 (第304-315行)
```python
# 检测重复行
has_duplicate = False
for i in range(1, len(processed_table) - 1):
    if processed_table[i][1] == processed_table[i+1][1]:
        has_duplicate = True
        break
```

#### 4. OCR fallback (第317-328行)
```python
if has_duplicate:
    ocr_extractor = get_ocr_extractor()
    ocr_table = ocr_extractor.extract_table_from_page(pdf_path, page_num)
    if ocr_table:
        processed_table = ocr_table
```

#### 5. PyMuPDF提取图片 (第373-435行)
```python
import fitz

pdf_document = fitz.open(str(pdf_path))
extracted_xrefs = set()

for page_num in range(len(pdf_document)):
    page = pdf_document[page_num]
    image_list = page.get_images(full=True)
    
    for img in image_list:
        xref = img[0]
        if xref in extracted_xrefs:
            continue
        
        # 提取图片
        base_image = pdf_document.extract_image(xref)
        extracted_xrefs.add(xref)
```

## 性能对比

### 5页PDF文档

| 场景 | pdfplumber | PyMuPDF | paddleocr | 总耗时 |
|------|-----------|---------|-----------|--------|
| **标准PDF** | 0.5秒 | 0.25秒 | 0秒(不触发) | **0.75秒** |
| **复杂表格** | 0.5秒 | 0.25秒 | 10秒(2页触发) | **10.75秒** |
| **扫描件** | 0.5秒 | 0.25秒 | 25秒(全部触发) | **25.75秒** |

### 优化建议

1. **并行处理**: 图片提取可以与表格提取并行
2. **缓存OCR结果**: 避免重复识别同一页
3. **GPU加速**: paddleocr使用GPU可提速3-5倍
4. **智能跳过**: 如果文本层为空,直接使用OCR

## 配置选项

### config.yaml

```yaml
pdf_extraction:
  # 是否启用OCR fallback
  enable_ocr_fallback: true
  
  # OCR触发条件
  ocr_trigger_on_duplicate: true  # 检测到重复行
  ocr_trigger_on_empty: true      # 表格为空
  
  # OCR引擎配置
  ocr_engine:
    use_gpu: false  # GPU加速
    lang: 'ch'      # 语言
    use_angle_cls: true  # 旋转识别
  
  # 页眉页脚过滤
  header_margin: 0.05  # 顶部5%
  footer_margin: 0.05  # 底部5%
  
  # 图片过滤
  min_image_size: 200  # 最小宽高
  max_aspect_ratio: 10  # 最大宽高比
```

## 调试技巧

### 1. 查看pdfplumber提取结果

```python
# 在日志中查找
DEBUG 页面2原始表格所有行:
DEBUG   第0行: ['版本\n0.1', '内容\nLLM\n首次发布...', ...]
```

### 2. 查看OCR触发

```python
# 在日志中查找
WARNING 页面2检测到重复内容,尝试使用OCR重新提取
INFO OCR重新提取成功,行数: pdfplumber=5, OCR=5
```

### 3. 查看图片去重

```python
# 在日志中查找
DEBUG 跳过重复图片: xref=173 (页面 5)
```

### 4. 查看最终统计

```python
# 在日志中查找
INFO PDF 多模态提取完成: 文本 1056 字符, 表格 5 个, 图片 10 张
```

## 常见问题

### Q1: 什么时候只用pdfplumber和PyMuPDF?

**A**: 当PDF满足以下条件时:
- ✅ 文本层完整(可以选中复制)
- ✅ 表格结构规范
- ✅ 没有重复行或错位

**判断方法**: 看日志中是否有`OCR重新提取`

### Q2: 什么时候需要paddleocr?

**A**: 当出现以下情况时:
- ❌ 表格内容重复
- ❌ 表格为空但PDF中有表格
- ❌ 扫描件PDF
- ❌ 文字错位严重

**判断方法**: 看日志中是否有`检测到重复内容,尝试使用OCR重新提取`

### Q3: 为什么不总是用OCR?

**A**: 因为OCR:
- 速度慢(慢20-50倍)
- 准确率不如pdfplumber(对标准PDF)
- 消耗更多CPU/GPU资源

**策略**: 先用快速的pdfplumber,失败了再用慢速的OCR

### Q4: 可以禁用OCR吗?

**A**: 可以,在`config.yaml`中设置:
```yaml
pdf_extraction:
  enable_ocr_fallback: false
```

但这样复杂表格可能提取错误。

## 相关文档

- **`OCR_INTEGRATION.md`** - OCR集成详细说明
- **`PDF_TABLE_EXTRACTION_LIMITATION.md`** - pdfplumber的限制
- **`OCR_AND_IMAGE_EXTRACTION_FIX.md`** - 最新的修复
- **`TABLE_STRUCTURE_NORMALIZATION.md`** - 表格规范化

## 总结

### 三者关系

```
pdfplumber (主力,快速) 
    ↓ 失败
paddleocr (fallback,慢速但准确)
    ↓ 并行
PyMuPDF (图片提取,总是使用)
```

### 使用原则

1. **总是使用**: pdfplumber + PyMuPDF
2. **按需使用**: paddleocr (检测到问题时)
3. **性能优先**: 能用pdfplumber就不用OCR
4. **准确率优先**: 宁可慢一点,也要用OCR修复错误
