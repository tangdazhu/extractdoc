# 文档提取与生成系统 - 文档总览

> **最后更新**：2025-10-23  
> **项目路径**：`d:/Python-Learning/extract_doc/`

---

## 📢 最新更新

- ✅ 配置管理统一完成，所有参数集中在 `config/application.yaml`，统一通过 `utils/config_manager.py` 访问。
- ✅ 《PPT系统完整实现文档》升级至 **v4.1**，修复封面标题溢出与补充图片过多问题。
- ✅ 文档索引合并至本文件，提供完整的学习与参考路径。

---

## 📚 核心文档

### 🎯 系统设计与实现（v2.0）
- [系统设计与实现文档-Part1](./系统设计与实现文档-Part1.md)：系统概述、技术架构、网页内容提取、Playwright渲染
- [系统设计与实现文档-Part2](./系统设计与实现文档-Part2.md)：图片下载与处理、PPT生成、开发规范、部署运维

> **涵盖内容**：系统架构、Playwright渲染、智能图片下载、配置管理规范、部署指南、更新日志

### 📘 配置管理
- [CONFIG_UNIFICATION_COMPLETE](./CONFIG_UNIFICATION_COMPLETE.md)：配置统一方案与规范
- [CONFIG_COMPLETE_GUIDE](./CONFIG_COMPLETE_GUIDE.md)：配置结构、管理器使用方法、测试与常见问题

---

## 📖 功能模块文档

### 🌐 网页内容提取
- [Playwright使用指南](./Playwright使用指南.md)：Playwright对比、安装配置、支持网站、最佳实践
- [AI_HTML_EXTRACTION](./AI_HTML_EXTRACTION.md)：AI驱动内容提取、通义千问集成、章节结构识别

### 🎨 文档生成
- [PPT系统完整实现文档](./PPT系统完整实现文档.md)：双风格模板、布局检测、图片处理、v4.1修复
- [WORD_GENERATION_COMPLETE_GUIDE](./WORD_GENERATION_COMPLETE_GUIDE.md)：Word生成流程、模板、格式控制
- [URL_TO_PPT_FEATURE](./URL_TO_PPT_FEATURE.md)：URL转PPT流程与示例

### 📄 文档处理
- [PDF_EXTRACTION_WORKFLOW](./PDF_EXTRACTION_WORKFLOW.md)：PDF文本提取、OCR处理、多模态数据

### 🛠️ 修复与优化记录
- `WORD_AI_TEXT_REWRITE_FIX.md`：AI文本改写问题修复说明
- 其他修复文档均已合并至对应主文档（例如PPT系统文档v4.1）

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境
```bash
# 创建 .env
DASHSCOPE_API_KEY=your_api_key_here
```

### 3. 运行项目
```bash
python manage.py runserver
```

### 4. 快速测试
```python
from extract_web.converter.services.web_content_extractor import WebContentExtractor

extractor = WebContentExtractor()
article = extractor.extract_from_url("https://mp.weixin.qq.com/s/xxx")
```

---

## ⚙️ 配置与规范

### 配置统一
- **配置文件路径**：`config/application.yaml`
- **配置节**：`application`、`paths`、`logging`、`pdf_extraction`、`ai_document_analysis`、`web_extraction`、`word_generation`、`ppt_generation`、`text_processing`
- **访问方式**：
```python
from utils.config_manager import config

model = config.get("ai_document_analysis.model")
ppt_styles = config.get("ppt_generation.styles")
word_section = config.get_section("word_generation")
```

### 管理规范
- ✅ 所有配置必须通过 `utils.config_manager` 访问
- ✅ 修改配置后可调用 `config.reload()` 热加载或重启服务
- ❌ 禁止hardcode任何可配置的数值、路径、密钥
- ❌ 禁止新增零散配置文件或直接读取YAML

### 旧配置文件
- 已备份至 `config/backup/`：`config.yaml.bak`、`ai_ppt_config.yaml.bak`、`document_generation_templates.json.bak`、`settings.py.bak`

---

## 📊 功能对照表

| 功能 | 参考文档 | 状态 | 说明 |
|------|----------|------|------|
| 微信文章提取 | `系统设计文档` | ✅ | HTTP请求 + 正文提取 |
| 头条文章提取 | `Playwright使用指南` | ✅ | Playwright渲染 + 推荐过滤 |
| 知乎文章提取 | `Playwright使用指南` | ✅ | Playwright渲染 |
| 图片智能下载 | `系统设计文档-Part2` | ✅ | Referer策略 + 扩展名识别 |
| PPT生成 | `PPT系统完整实现文档` | ✅ | 双风格模板 + 布局检测 |
| Word生成 | `WORD_GENERATION_COMPLETE_GUIDE` | ✅ | 双风格模板 |
| AI内容分析 | `AI_HTML_EXTRACTION` | ✅ | 通义千问章节解析 |
| 布局检测 | `PPT系统完整实现文档` | ✅ | 5种布局类型 |

---

## 🔄 文档更新流程

### 更新原则
- **持续更新**：功能上线后立即更新相关文档
- **版本控制**：文档头部注明版本号与最后更新时间
- **变更记录**：重要修改写入更新日志
- **索引同步**：本README作为唯一索引入口，必须保持最新

### 更新检查清单
- [ ] 更新系统设计文档
- [ ] 更新功能模块文档
- [ ] 更新配置文档
- [ ] 更新本README索引
- [ ] 更新更新日志
- [ ] 检查文档链接有效性

---

## 📝 文档贡献规范

- 使用中文撰写，遵循Markdown标准
- 提供完整代码示例和必要截图
- 文档头部包含版本、更新时间、维护者
- 重要章节需记录使用说明与问题排查

### 推荐模板
```markdown
# 文档标题

> **文档版本**: vX.X  
> **最后更新**: YYYY-MM-DD  
> **维护者**: XXX

## 概述
...

## 详细内容
...

## 示例
...

## 参考资料
...
```

---

## 🔗 外部资源

- [Playwright官方文档](https://playwright.dev/python/)
- [通义千问API文档](https://help.aliyun.com/zh/model-studio/developer-reference/qwen-api-overview)
- [python-pptx文档](https://python-pptx.readthedocs.io/)
- [Django官方文档](https://docs.djangoproject.com/)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)

---

## 📞 联系方式

- **项目维护**：Cascade AI
- **问题反馈**：通过项目 Issue 提交
- **文档更新**：在对应文档中提 Issue 或提交合并请求

---

## 📅 文档版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| v2.1 | 2025-10-23 | 合并文档索引与配置指南，更新PPT系统文档链接 |
| v2.0 | 2025-10-20 | 配置统一与测试验证，创建配置管理指南 |

---

**文档维护原则**：本README为唯一索引入口，新增或更新任何文档后务必同步更新此文件。
