# 多来源文章自动总结与PPT生成系统技术方案

## 1. 需求概述
- **输入**：
  - 用户上传的本地文档（PDF、DOCX、TXT、PPT 等）
  - **多个网络文章链接**（支持动态添加，每个URL独立提取与缓存）
- **输出**：
  - 多层次文本结果：全文总结、精简摘要、关键要点列表。
  - 自动生成结构化 PPT：包含标题页、目录页、重点内容页、结论页等。
- **目标**：在现有依赖基础上扩展能力，接入阿里云通义千问（Qwen），提供稳定、安全、可扩展的报告生成服务。

### 1.1 多URL支持能力（v2.0新增）

**前端交互增强**：
- 网络文章URL输入框右侧提供"+"按钮，用户可动态添加多个URL输入框
- 每个输入框独立校验，支持删除（至少保留1个）
- 提交时收集所有URL为数组：`["url1", "url2", "url3"]`

**后端处理流程**：
1. **独立缓存**：每个URL使用独立缓存键（`md5(url)_content`），遵守配置的过期策略
2. **并行提取**：使用 `WebContentExtractor` 并行处理各URL，保留各自章节结构与图片
3. **智能合并**：
   - 章节标题去重（基于文本相似度）
   - 内容段落去重（哈希或语义向量）
   - 图片去重（URL或内容哈希）
4. **来源标注**：为每个章节添加来源URL标记
5. **统一生成**：合并后的内容生成单一PPT，包含多来源引用页

## 2. 技术栈约束
- 依赖文件：[requirements.txt](cci:7://file:///d:/Python-Learning/extract_doc/requirements.txt:0:0-0:0) 中已有 OCR、文档解析、PPT 处理等基础能力。
- 大模型选择：统一对接阿里云通义千问（Qwen），不再引入其它第三方大模型。

## 3. 系统架构设计
- **表现层**：Django 模板 + 静态资源，提供上传、配置与结果展示。
- **服务层**：Django/DRF 实现任务编排，必要时引入 FastAPI 子服务封装千问调用。
- **模型层**：通义千问 API 负责摘要、重点提炼与 PPT 文本生成。
- **数据层**：PostgreSQL 存储任务与元数据；对象存储（MinIO/S3）保存原文与生成 PPT。
- **基础设施**：Celery + Redis 异步任务；日志写入项目 `logs/` 目录；监控采用 Prometheus + Grafana。

### 3.1 核心数据流
1. 获取文档（上传或抓取）→ 文本抽取与预处理。
2. 调用千问生成摘要、要点、结论。
3. 依据模板生成 PPT。
4. 持久化结果并通知用户。

## 4. 功能模块设计

### 4.1 内容采集模块

**本地上传**：
- Django 表单校验文件类型、大小
- 支持 PDF、DOCX、TXT、PPT 等多种格式

**网络抓取（支持多URL）**：
- **输入**：前端提交URL列表 `source_urls: ["url1", "url2", ...]`
- **并行提取**：
  - 后端使用 `concurrent.futures.ThreadPoolExecutor` 或 `asyncio` 并行调用 `WebContentExtractor.extract_from_url()`
  - 每个URL独立处理，互不影响
- **独立缓存策略**：
  - 缓存键格式：`md5(url)_content`、`md5(url)_images`
  - 缓存位置：`cache/web_content/`（配置路径：`config.get("paths.cache_dir")`）
  - 过期策略：遵守 `config.get("web_extraction.cache_expiry_hours", 24)` 配置
  - 缓存命中时直接返回，未命中时重新提取并缓存
- **提取工具**：
  - 优先使用 `requests` + `BeautifulSoup` 提取静态内容
  - 按需启用 `Playwright` 渲染动态页面（头条、知乎等）
  - 遵守 `robots.txt` 规则与访问频率限制

**OCR处理**：
- `paddleocr` + `paddlepaddle` + `opencv-python-headless` 处理扫描件
- 支持图片中的文字识别与表格提取

### 4.2 文本预处理
- **格式转换**：
  - `PyMuPDF`、`pdfplumber`：PDF → 文本。
  - `python-docx`：DOCX → 文本。
  - `openpyxl`：Excel → CSV/文本。
  - `python-pptx`：PPT → 文本。
- **清洗与结构化**：统一编码、去除噪声、段落分割、章节识别。

### 4.3 语义分析与生成

**单文档处理**：
- **摘要生成**：分段调用千问，合并为全文总结
- **关键词与重点**：结合本地 TF-IDF/KeyBERT 预筛选，再由千问 refine

**多URL文档整合**：

1. **独立提取阶段**：
   - 各URL分别调用 `WebContentExtractor.extract_from_url(url)`
   - 每个URL返回独立的数据结构：
     ```python
     {
       "url": "https://example.com/article1",
       "title": "文章标题",
       "sections": [
         {"title": "章节1", "content": ["要点1", "要点2"], "level": 2},
         {"title": "章节2", "content": ["要点3"], "level": 2}
       ],
       "images": [{"url": "img1.jpg", "alt": "图片说明"}],
       "extract_time": "2025-10-23 16:00:00"
     }
     ```

2. **内容去重与合并**：
   - **章节标题去重**：
     - 使用编辑距离（Levenshtein Distance）计算标题相似度
     - 相似度阈值：`config.get("text_processing.title_similarity_threshold", 0.85)`
     - 相似标题合并为同一章节，保留最长或最完整的标题
   - **内容段落去重**：
     - 对每个段落计算 MD5 哈希或使用语义向量（sentence-transformers）
     - 哈希相同或余弦相似度 > 0.9 的段落视为重复
     - 保留首次出现的段落，记录来源URL
   - **图片去重**：
     - 优先基于图片URL去重
     - 对于不同URL但内容相同的图片，计算图片内容哈希（pHash）
     - 保留第一个出现的图片，记录所有来源URL

3. **结构合并策略**：
   - **章节排序**：
     - 按URL提交顺序排列
     - 或按章节标题的语义相关性聚类
   - **来源标注**：
     - 每个章节添加 `sources: ["url1", "url2"]` 字段
     - 每个段落添加 `source_url` 属性
   - **合并后数据结构**：
     ```python
     {
       "merged_title": "综合标题（基于多来源）",
       "source_urls": ["url1", "url2", "url3"],
       "sections": [
         {
           "title": "合并章节1",
           "content": ["要点1 (来自url1)", "要点2 (来自url2)"],
           "sources": ["url1", "url2"],
           "level": 2
         }
       ],
       "images": [...],
       "merge_time": "2025-10-23 16:05:00"
     }
     ```

4. **AI综合分析**：
   - 将合并后的内容提交千问，生成跨文档的综合摘要
   - Prompt 模板：
     ```
     以下是从 {N} 个来源整合的内容：
     来源1: {url1}
     来源2: {url2}
     ...
     
     请生成：
     1. 综合摘要（200字以内）
     2. 核心要点（5-10条）
     3. 各来源的独特观点
     4. 综合结论与建议
     ```

### 4.4 PPT 生成模块

**模板管理**：
- 基于 `python-pptx` 预置主题模板
- 支持 `BusinessStylePPTGenerator`（商务风格）和 `AcademicStylePPTGenerator`（学术风格）
- 模板路径：`config/templates/business_template.pptx`、`config/templates/academic_template.pptx`

**多URL场景的内容填充**：

1. **封面页（Title Slide）**：
   - 主标题：合并后的综合标题或用户自定义标题
   - 副标题：显示"基于 N 个来源的综合分析"
   - 日期与作者信息

2. **目录页（Table of Contents）**：
   - 列出合并后的所有章节标题
   - 显示"本报告整合了以下 N 个来源："
   - 列出所有来源URL（缩短显示，完整URL放在备注）

3. **重点内容页（Content Slides）**：
   - 按章节渲染，支持文本、图片、表格布局
   - 每个章节页脚显示来源标注：
     ```
     来源：url1, url2
     ```
   - 或在页面备注中添加详细来源信息

4. **来源引用页（Sources Page）**：
   - 专门页面列出所有URL来源
   - 格式：
     ```
     参考来源：
     1. [文章标题1] - https://example.com/article1
        提取时间：2025-10-23 16:00
     2. [文章标题2] - https://example.com/article2
        提取时间：2025-10-23 16:01
     ```

5. **综合分析页（Summary & Insights）**：
   - AI生成的跨文档综合摘要
   - 核心要点列表
   - 各来源的独特观点对比

6. **结论与建议页（Conclusion）**：
   - AI生成的综合结论
   - 行动建议

**多URL标注策略**：
- 在每个章节的页脚或备注中标注内容来源URL
- 目录页显示"基于 N 个来源生成"
- 使用不同颜色或图标区分不同来源的内容（可选）

**导出格式**：
- 默认 PPTX
- 可选调用 `reportlab` 或 `docx2pdf` 转 PDF

### 4.5 任务调度与管理
- **异步执行**：`Celery + Redis` 处理长耗时任务，支持重试与优先级。
- **状态跟踪**：PostgreSQL 记录任务进度、执行耗时、文件指针。
- **通知服务**：邮件或站内信提醒任务完成。

## 5. 大模型接入方案（阿里云通义千问）
- **SDK**：推荐使用官方 `dashscope` SDK（参考 https://help.aliyun.com/zh/model-studio/developer-reference/qwen-api-overview）。
- **封装**：编写 `qwen_client.py`，实现统一的请求封装、重试机制、错误处理。
- **Prompt 策略**：针对摘要、重点提炼、PPT 结构分别设计提示模板，支持长度控制与多语言。
- **安全**：API Key 存储于环境变量；所有请求采用 HTTPS。

## 6. 安全与权限控制
- **认证**：Django Auth / JWT，支持角色（普通用户、审阅人、管理员）。
- **文件安全**：上传文件病毒扫描（ClamAV），对象存储按用户隔离。
- **日志审计**：使用 `utils.logger.setup_logger()` 输出结构化日志至 `logs/` 目录。
- **合规**：提示用户确保上传/链接内容具有合法使用权。

## 7. 部署与运维
- **部署方式**：Docker 容器化；测试/预发布/生产隔离；CI/CD（GitHub Actions、Jenkins）。
- **监控指标**：Celery 任务成功率、千问调用响应时间、OCR/解析耗时、PPT 生成耗时。
- **告警**：Prometheus Alertmanager + 飞书/钉钉。
- **备份策略**：定期备份 PostgreSQL 与对象存储；日志滚动与归档。

## 8. 迭代计划建议
1. **阶段 1**：完成千问接入、单文档摘要与 PPT MVP。
2. **阶段 2**：支持多文档整合、任务队列、模板管理。
3. **阶段 3**：完善权限体系、审计日志、监控告警。
4. **阶段 4**：扩展智能配图、行业化模板、知识库问答。

## 9. 下一步行动
- 集中确认业务侧对 PPT 模板与摘要粒度的需求。
- 在后端新增千问 SDK 集成模块，配置 API Key 与调用封装。
- 实施 Celery 任务流程、结果持久化与通知机制。
- 设计并实现 `python-pptx` 模板，与前端联调展示与下载。
- 编写端到端测试，配置基础监控和日志审查。

## 10. 文档生成界面与交互实现细节
- **左侧菜单布局**
  - 在 `templates/converter/base.html` 左侧导航栏中，沿用现有按钮样式，将“文档生成”菜单项追加在“语音处理”下方，并保持 `active` 样式逻辑与其他菜单一致。
  - 点击“文档生成”时，右侧主容器渲染新的文档生成表单视图，复用 `block content` 区域。

- **右侧内容结构**
  - 顶部采用 Tabs 形式区分“PPT生成”“Word生成”，默认选中 PPT；通过添加 `data-target` 或 Vue/Alpine 等轻量状态管理标记当前类型。
  - 页眉下方包含表单区块标题“文档生成”，整体沿用 `card` 风格背景。

- **输入源选择**
  - 提供“选择文件”“网络文章URL”两个输入源，分别带有左侧复选框，用户必须勾选对应复选框后才启用该输入组件。
  - 本地文件输入沿用 `<input type="file">`，支持多格式；网络输入为 `<input type="url">` 并提供示例占位符。
  - 校验逻辑：至少勾选并填写一种输入源；若两者同时启用，优先以本地文件为主并将 URL 作为补充信息入库。

- **生成类型驱动的联动**
  - 当 Tabs 选中“PPT生成”时，显示“PPT 模板选择”区域；切换到“Word生成”时隐藏该区域并重置模板选择值。
  - 模板列表支持单选按钮或卡片样式，从后端接口(`/api/templates?type=ppt`)加载，初始化时默认选中第一个模板。
  - `开始生成` 按钮需根据当前激活的生成类型、输入源校验结果、模板是否选择（PPT 场景）动态启用/禁用。

- **提交与结果反馈**
  - 表单提交调用 `/api/document-generation/`，请求体包含 `generate_type`(`ppt`/`word`)、`source_urls`（数组）、`local_file`、`selected_template`、任务描述。
  - **多URL请求示例**：
    ```json
    {
      "generate_type": "ppt",
      "source_urls": ["https://url1.com", "https://url2.com", "https://url3.com"],
      "selected_template": "style_a",
      "task_description": "多来源综合分析"
    }
    ```
  - **后端处理流程**：
    1. 并行提取各URL内容（每个URL独立缓存）
    2. 内容去重与合并（章节、段落、图片）
    3. AI分析生成综合摘要
    4. 生成PPT并标注来源
  - 提交后在前端展示进度条或状态提示，轮询任务状态接口 `/api/document-generation/{task_id}`，完成后提供下载链接。
  - 异常情况（输入缺失、任务失败）通过顶部横幅或弹窗提示，并记录在 `logs/` 中供审计。

---

## 11. 多URL前端实现细节（v2.0新增）

### 11.1 HTML结构

```html
<div class="form-group">
  <div class="form-check">
    <input type="checkbox" id="enableUrlInput" class="form-check-input">
    <label for="enableUrlInput">网络文章URL</label>
  </div>
  
  <div id="urlInputContainer" class="mt-2" style="display:none;">
    <div class="url-input-group mb-2">
      <input type="url" name="source_urls[]" class="form-control" 
             placeholder="https://mp.weixin.qq.com/s/xxxxx" required>
      <button type="button" class="btn btn-success btn-sm add-url-btn">+</button>
    </div>
  </div>
</div>
```

### 11.2 JavaScript实现

```javascript
// 启用/禁用URL输入区域
document.getElementById('enableUrlInput').addEventListener('change', function(e) {
  document.getElementById('urlInputContainer').style.display = e.target.checked ? 'block' : 'none';
});

// 添加URL输入框
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('add-url-btn')) {
    const container = document.getElementById('urlInputContainer');
    const newGroup = document.createElement('div');
    newGroup.className = 'url-input-group mb-2';
    newGroup.innerHTML = `
      <input type="url" name="source_urls[]" class="form-control" 
             placeholder="https://mp.weixin.qq.com/s/xxxxx" required>
      <button type="button" class="btn btn-danger btn-sm remove-url-btn">-</button>
    `;
    container.appendChild(newGroup);
  }
  
  // 删除URL输入框（至少保留1个）
  if (e.target.classList.contains('remove-url-btn')) {
    const groups = document.querySelectorAll('.url-input-group');
    if (groups.length > 1) {
      e.target.closest('.url-input-group').remove();
    } else {
      alert('至少需要保留一个URL输入框');
    }
  }
});

// 表单提交时收集所有URL
document.getElementById('docGenForm').addEventListener('submit', function(e) {
  e.preventDefault();
  
  const urls = Array.from(document.querySelectorAll('input[name="source_urls[]"]'))
    .map(input => input.value.trim())
    .filter(url => url.length > 0);
  
  const formData = {
    generate_type: document.querySelector('input[name="generate_type"]:checked').value,
    source_urls: urls,
    selected_template: document.querySelector('input[name="template"]:checked').value
  };
  
  // 发送到后端
  fetch('/api/document-generation/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(formData)
  }).then(response => response.json())
    .then(data => {
      // 处理响应
      console.log('Task ID:', data.task_id);
    });
});
```

### 11.3 CSS样式

```css
.url-input-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.url-input-group input {
  flex: 1;
}

.url-input-group button {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  padding: 0;
  font-size: 18px;
  font-weight: bold;
}

.add-url-btn {
  background-color: #28a745;
  border-color: #28a745;
}

.remove-url-btn {
  background-color: #dc3545;
  border-color: #dc3545;
}
```

---

## 12. 后端实现要点（v2.0新增）

### 12.1 Django View扩展

```python
# views.py
from concurrent.futures import ThreadPoolExecutor
from extract_web.converter.services.web_content_extractor import WebContentExtractor
from utils.config_manager import config
import logging

logger = logging.getLogger(__name__)

class DocumentGenerationView(APIView):
    def post(self, request):
        source_urls = request.data.get('source_urls', [])
        
        if not source_urls:
            return Response({'error': '至少需要提供一个URL'}, status=400)
        
        # 并行提取各URL内容
        extractor = WebContentExtractor()
        extracted_contents = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(extractor.extract_from_url, url): url 
                      for url in source_urls}
            
            for future in futures:
                url = futures[future]
                try:
                    content = future.result()
                    content['source_url'] = url
                    extracted_contents.append(content)
                    logger.info(f"成功提取URL: {url}")
                except Exception as e:
                    logger.error(f"提取URL失败 {url}: {e}")
        
        # 合并内容
        merged_content = self._merge_contents(extracted_contents)
        
        # 生成PPT
        ppt_path = self._generate_ppt(merged_content, request.data.get('selected_template'))
        
        return Response({'task_id': task_id, 'status': 'processing'})
    
    def _merge_contents(self, contents):
        """合并多个URL的内容，去重"""
        from utils.content_merger import ContentMerger
        
        merger = ContentMerger(
            title_similarity_threshold=config.get("text_processing.title_similarity_threshold", 0.85)
        )
        return merger.merge(contents)
```

### 12.2 内容合并工具

```python
# utils/content_merger.py
import hashlib
from difflib import SequenceMatcher

class ContentMerger:
    def __init__(self, title_similarity_threshold=0.85):
        self.threshold = title_similarity_threshold
    
    def merge(self, contents):
        """合并多个内容，去重"""
        merged = {
            'source_urls': [c['source_url'] for c in contents],
            'sections': [],
            'images': [],
            'merge_time': datetime.now().isoformat()
        }
        
        # 合并章节（去重）
        seen_titles = {}
        for content in contents:
            for section in content.get('sections', []):
                title = section['title']
                
                # 查找相似标题
                similar_key = self._find_similar_title(title, seen_titles.keys())
                
                if similar_key:
                    # 合并到现有章节
                    seen_titles[similar_key]['content'].extend(section['content'])
                    seen_titles[similar_key]['sources'].append(content['source_url'])
                else:
                    # 新章节
                    seen_titles[title] = {
                        'title': title,
                        'content': section['content'],
                        'sources': [content['source_url']],
                        'level': section.get('level', 2)
                    }
        
        merged['sections'] = list(seen_titles.values())
        
        # 合并图片（URL去重）
        seen_image_urls = set()
        for content in contents:
            for img in content.get('images', []):
                if img['url'] not in seen_image_urls:
                    merged['images'].append(img)
                    seen_image_urls.add(img['url'])
        
        return merged
    
    def _find_similar_title(self, title, existing_titles):
        """查找相似标题"""
        for existing in existing_titles:
            similarity = SequenceMatcher(None, title, existing).ratio()
            if similarity >= self.threshold:
                return existing
        return None
```

---

**文档更新日期**：2025-10-23  
**版本**：v2.0（新增多URL支持）