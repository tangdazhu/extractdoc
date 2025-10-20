# 项目文档目录

## 📢 最新更新 (2025-10-20)

✅ **配置管理已完全统一**
- 所有配置文件已合并到 `config/application.yaml`
- 新增统一配置管理器 `utils/config_manager.py`
- 向后兼容，旧代码无需修改
- 所有测试通过（10/10）

---

## 📚 主要文档

### 📘 [配置管理完整指南](CONFIG_COMPLETE_GUIDE.md) ⭐ 推荐

**统一的配置管理文档**，包含：
- ✅ 配置统一状态和架构
- 📄 配置文件完整说明
- 💻 配置管理器使用方法（含代码示例）
- 📊 迁移完成总结
- ✅ 测试验证结果
- ❓ 常见问题解答（8个Q&A）
- 📋 项目规则建议

**推荐阅读顺序**：
1. **概述** - 了解配置统一的背景和解决方案
2. **配置文件说明** - 了解 `application.yaml` 的完整结构
3. **配置管理器使用** - 学习如何在代码中使用配置
4. **常见问题** - 解决使用中的问题

---

### 📝 其他文档

- `WORD_AI_TEXT_REWRITE_FIX.md` - AI文本改写问题修复文档

---

## 🚀 快速开始

### 使用配置管理器（Django应用 - 推荐）

```python
from utils.config_manager import config

# 获取单个配置值（支持点号路径）
model = config.get("ai_document_analysis.model")
# 返回: "qwen-max"

# 获取配置节
word_config = config.get_section("word_generation")
# 返回: {"page_margins": {...}, "font_sizes": {...}, ...}

# 检查配置是否存在
if config.exists("ai_document_analysis.model"):
    # 配置存在
    pass
```

### 使用兼容层（旧版脚本）

```python
from utils import load_config, setup_logging

# 加载配置（自动从统一配置文件加载）
config = load_config()
input_dir = config.get("input_directory")
log_file = config.get("log_file")

# 设置日志
logger = setup_logging(log_file, "app_logger")
```

---

## 📁 配置文件位置

### 统一配置文件

**位置**：`config/application.yaml`

**包含的配置节**（8个）：
- `application` - 应用基础配置
- `paths` - 文件路径配置
- `logging` - 日志配置
- `pdf_extraction` - PDF提取配置
- `ai_document_analysis` - AI文档分析配置
- `word_generation` - Word生成配置
- `ppt_generation` - PPT生成配置
- `text_processing` - 文本处理配置

### 旧配置文件（已废弃）

已备份到 `config/backup/` 目录：
- `config.yaml.bak`
- `ai_ppt_config.yaml.bak`
- `document_generation_templates.json.bak`
- `settings.py.bak`

---

## ✅ 测试脚本

### 配置迁移测试

测试配置文件加载和各配置节的正确性：

```bash
python test_config_migration.py
```

**测试项目**（7个）：
- 配置文件加载
- AI配置
- Word配置
- PPT配置
- 模板配置加载
- PDF提取配置
- 配置存在性检查

### 兼容性测试

测试向后兼容层是否正常工作：

```bash
python test_config_compatibility.py
```

**测试项目**（3个）：
- load_config 向后兼容性
- setup_logging 向后兼容性
- 旧版脚本使用模拟

### 测试结果

✅ **所有测试通过：10/10**

---

## 📖 配置使用示例

### 示例1：Word生成器

```python
from utils.config_manager import config

class SmartWordGenerator:
    def __init__(self, style_config: Optional[Dict] = None):
        # 从配置文件加载，允许运行时覆盖
        if style_config is None:
            self.config = config.get_section("word_generation")
        else:
            self.config = style_config
    
    def _set_page_margins(self):
        margins = self.config["page_margins"]
        # 使用配置设置页边距
        ...
```

### 示例2：AI文档分析器

```python
from utils.config_manager import config

class AIDocumentAnalyzer:
    def __init__(self, model: Optional[str] = None):
        # 从配置文件加载AI模型配置
        if model is None:
            self.model = config.get("ai_document_analysis.model", "qwen-max")
            self.temperature = config.get("ai_document_analysis.temperature", 0.1)
            self.max_tokens = config.get("ai_document_analysis.max_tokens", 4000)
```

### 示例3：文档生成

```python
from utils.config_manager import config

def load_generation_templates():
    """从统一配置文件加载模板配置"""
    ppt_styles = config.get("ppt_generation.styles", {})
    word_styles = config.get("word_generation.styles", {})
    
    return {
        "ppt": ppt_styles,
        "word": word_styles,
    }
```

---

## 🔧 配置管理规范

### 添加新配置

1. 在 `config/application.yaml` 中添加配置项
   ```yaml
   new_feature:
     setting1: value1
     setting2: value2
   ```

2. 在代码中使用
   ```python
   from utils.config_manager import config
   
   setting1 = config.get("new_feature.setting1")
   ```

### 修改配置

1. 编辑 `config/application.yaml`
2. 重启Django服务器
3. 或调用 `config.reload()` 热重载

### 禁止事项

- ❌ 禁止硬编码配置值
- ❌ 禁止创建新的配置文件
- ❌ 禁止在代码中直接读取配置文件

---

## 📊 配置统一架构

```
config/application.yaml (统一配置源)
        ↓
utils/config_manager.py (核心配置管理器)
        ↓
    ┌───┴───────────┐
    ↓               ↓
Django Web应用      utils/config.py (兼容层)
(直接使用)          ↓
                   旧版脚本 (无需修改)
```

---

## ❓ 常见问题

### Q: 为什么有两个配置工具？

**A**: 
- `utils/config_manager.py` - 新版，功能强大，Django应用使用
- `utils/config.py` - 兼容层，为旧版脚本提供向后兼容

现在 `config.py` 内部调用 `config_manager.py`，所有配置都来自统一配置文件。

### Q: 旧版脚本需要修改吗？

**A**: 不需要！旧版脚本继续使用原有API，内部自动从统一配置文件加载。

### Q: 如何验证配置是否正确？

**A**: 运行测试脚本：
```bash
python test_config_migration.py
python test_config_compatibility.py
```

更多问题请参考 [配置管理完整指南](CONFIG_COMPLETE_GUIDE.md) 的"常见问题"章节。

---

## 📝 更新历史

### 2025-10-20
- ✅ 配置文件统一到 `config/application.yaml`
- ✅ 创建统一配置管理器 `utils/config_manager.py`
- ✅ 实现向后兼容层 `utils/config.py`
- ✅ 所有测试通过（10/10）
- ✅ 创建完整的配置管理文档

---

**最后更新**：2025-10-20  
**维护人员**：项目团队  
**文档版本**：2.0
