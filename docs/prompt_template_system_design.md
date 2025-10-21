# 提示词模板系统设计文档

## 1. 概述

### 1.1 设计目标
- 将硬编码的提示词提取为可配置的YAML模板
- 提供多个系统默认模板，适应不同文档类型
- 允许用户在Web界面查看、复制、修改提示词
- 用户修改后保存为个人模板，不影响系统默认模板

### 1.2 核心原则
- **分离关注点**：提示词配置与业务逻辑分离
- **多租户隔离**：系统模板与用户模板分离存储
- **易于扩展**：支持添加新模板类型
- **版本控制**：支持模板版本管理

---

## 2. 系统架构

### 2.1 目录结构

```
extract_web/
├── prompts/                          # 提示词模板目录
│   ├── __init__.py
│   ├── templates/                    # 系统默认模板（只读）
│   │   ├── technical_article.yaml   # 技术文章模板
│   │   ├── architecture_doc.yaml    # 架构文档模板
│   │   ├── api_reference.yaml       # API文档模板
│   │   └── tutorial.yaml            # 教程类模板
│   ├── user_templates/              # 用户自定义模板（gitignore）
│   │   └── {user_id}/
│   │       ├── my_template_1.yaml
│   │       └── my_template_2.yaml
│   ├── template_manager.py          # 模板管理器
│   └── schema.py                    # 模板数据结构定义
│
├── converter/
│   └── services/
│       └── web_content_extractor.py # 修改为使用模板
│
└── api/
    └── routes/
        └── prompt_templates.py       # 提示词模板API
```

---

## 3. YAML模板格式

### 3.1 技术文章模板示例

```yaml
# prompts/templates/technical_article.yaml

metadata:
  name: "技术文章提取模板"
  description: "适用于技术博客、技术文章的知识提取"
  type: "technical_article"
  version: "1.0.0"
  author: "system"

# 系统提示词
system_prompt: |
  你是技术知识提取专家。你的任务是从技术文章中提取可直接学习的知识点。

  【严格要求 - 违反将视为失败】
  1. 禁止写"介绍了"、"阐述了"、"讨论了"等废话
  2. 原文提到"N个要素/框架"，必须全部列出（数一遍确认数量）
  3. 有父子关系的内容必须用缩进表示（子项前加"  - "）
  4. 原文提到"介绍X和Y两个技术"，必须将相关内容归类到X和Y下

  【提取优先级】
  1. 架构图/分层设计：必须详细提取各层名称、组件、职责
  2. 完整列表：原文说"11个要素"就必须提取11个，不能少
  3. 层次关系：子类型/子组件必须缩进在父项下
  4. 技术细节：保留框架名、API名、工具名、数字、案例

  【输出格式】
  {"title":"","sections":[{"title":"第X章","content":["知识点1","知识点2"],"level":2}],"images":[]}

  【关键规则】
  - 如果原文有"X包含Y、Z、W"，必须写成：
    - **X**：说明
      - Y：说明
      - Z：说明
      - W：说明
  - 如果原文说"N个要素"，提取后数一遍，确保数量正确

# 用户提示词模板（支持变量替换）
user_prompt_template: |
  【文章内容第{batch_index}/{total_batches}部分】（[标题]标记章节标题）

  {batch_content}

  【提取指令】
  1. 找出所有章节标题（通常是[标题]标记的内容）
  2. 对每个章节：
     a) 如果提到"N个要素/框架/技术"，必须全部列出（提取后数一遍确认）
     b) 如果有架构/分层设计，必须详细提取各层名称和组件
     c) 如果有父子关系（如"X包含Y、Z"），子项必须缩进（前加"  - "）
     d) 如果提到"介绍A和B两个技术"，必须将相关内容归类到A和B下
     e) 禁止写"介绍了"、"阐述了"等废话，直接写知识点

  【缩进规则 - 必须严格遵守】
  - 如果原文说"FlowAgent包含SequentialAgent、ParallelAgent、LoopAgent"，必须写成：
    - **FlowAgent**：说明
      - SequentialAgent：说明
      - ParallelAgent：说明
      - LoopAgent：说明

  【数量验证】
  - 原文说"11个要素"，提取后必须有11个
  - 原文说"3类框架"，提取后必须有3类
  - 提取完成后数一遍，确保数量正确

  【去重】{dedup_hint}

  返回JSON格式：{{"title":"","sections":[{{"title":"第X章","content":["知识点1","  - 子知识点1","知识点2"],"level":2}}],"images":[]}}

# 模板变量说明
variables:
  - name: "batch_index"
    description: "当前批次索引（从1开始）"
    type: "int"
    required: true
  
  - name: "total_batches"
    description: "总批次数"
    type: "int"
    required: true
  
  - name: "batch_content"
    description: "当前批次的文章内容"
    type: "string"
    required: true
  
  - name: "dedup_hint"
    description: "去重提示（已提取的章节列表）"
    type: "string"
    required: false
    default: ""
```

### 3.2 架构文档模板示例

```yaml
# prompts/templates/architecture_doc.yaml

metadata:
  name: "架构文档提取模板"
  description: "专注于提取系统架构、组件关系、技术选型"
  type: "architecture_doc"
  version: "1.0.0"

system_prompt: |
  你是系统架构分析专家。专注提取架构设计、组件关系、技术选型。

  【核心要求】
  1. 架构图必须详细提取（层次、组件、职责、交互）
  2. 技术选型必须包含理由和对比
  3. 组件关系必须用层次结构表示
  4. 保留所有技术栈名称、版本号、配置参数

  【输出重点】
  - 系统分层架构
  - 组件职责划分
  - 技术选型依据
  - 部署架构
  - 数据流向

user_prompt_template: |
  【架构文档内容】
  {batch_content}

  【提取重点】
  1. 系统架构（必须详细）：
     - 分层结构（每层的名称、组件、职责）
     - 组件关系（依赖、调用、数据流）
  
  2. 技术选型：
     - 技术栈名称和版本
     - 选型理由
     - 替代方案对比
  
  3. 部署架构：
     - 部署拓扑
     - 服务器配置
     - 网络架构

  返回JSON格式。

variables:
  - name: "batch_content"
    type: "string"
    required: true
```

---

## 4. 核心代码实现

### 4.1 模板数据结构（schema.py）

```python
# -*- coding: utf-8 -*-
"""
提示词模板数据结构定义
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TemplateVariable:
    """模板变量定义"""
    name: str
    description: str
    type: str  # int, string, bool
    required: bool = True
    default: Optional[str] = None


@dataclass
class TemplateMetadata:
    """模板元数据"""
    name: str
    description: str
    type: str
    version: str
    author: str = "system"


@dataclass
class PromptTemplate:
    """提示词模板"""
    metadata: TemplateMetadata
    system_prompt: str
    user_prompt_template: str
    variables: List[TemplateVariable] = field(default_factory=list)
    
    def render_user_prompt(self, **kwargs) -> str:
        """渲染用户提示词（变量替换）"""
        # 验证必需变量
        for var in self.variables:
            if var.required and var.name not in kwargs:
                raise ValueError(f"缺少必需变量: {var.name}")
        
        # 填充默认值
        for var in self.variables:
            if var.name not in kwargs and var.default is not None:
                kwargs[var.name] = var.default
        
        # 变量替换
        return self.user_prompt_template.format(**kwargs)
```

### 4.2 模板管理器（template_manager.py）

```python
# -*- coding: utf-8 -*-
"""
提示词模板管理器
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict
from .schema import PromptTemplate, TemplateMetadata, TemplateVariable
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptTemplateManager:
    """提示词模板管理器"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self.user_templates_dir = Path(__file__).parent / "user_templates"
        
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.user_templates_dir.mkdir(parents=True, exist_ok=True)
        
        self._template_cache: Dict[str, PromptTemplate] = {}
    
    def list_system_templates(self) -> List[Dict]:
        """列出所有系统模板"""
        templates = []
        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    templates.append({
                        'id': yaml_file.stem,
                        'name': data['metadata']['name'],
                        'description': data['metadata']['description'],
                        'type': data['metadata']['type'],
                        'is_system': True
                    })
            except Exception as e:
                logger.error(f"加载模板失败: {yaml_file}, 错误: {e}")
        
        return templates
    
    def list_user_templates(self, user_id: str) -> List[Dict]:
        """列出用户自定义模板"""
        user_dir = self.user_templates_dir / user_id
        if not user_dir.exists():
            return []
        
        templates = []
        for yaml_file in user_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    templates.append({
                        'id': yaml_file.stem,
                        'name': data['metadata']['name'],
                        'description': data['metadata']['description'],
                        'is_system': False,
                        'user_id': user_id
                    })
            except Exception as e:
                logger.error(f"加载用户模板失败: {yaml_file}, 错误: {e}")
        
        return templates
    
    def load_template(self, template_id: str, user_id: Optional[str] = None) -> PromptTemplate:
        """加载模板"""
        cache_key = f"{user_id or 'system'}:{template_id}"
        
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]
        
        if user_id:
            template_path = self.user_templates_dir / user_id / f"{template_id}.yaml"
        else:
            template_path = self.templates_dir / f"{template_id}.yaml"
        
        if not template_path.exists():
            raise FileNotFoundError(f"模板不存在: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        template = self._parse_template(data)
        self._template_cache[cache_key] = template
        
        logger.info(f"加载模板成功: {template_id}")
        return template
    
    def save_user_template(self, user_id: str, template_id: str, template_data: Dict) -> str:
        """保存用户自定义模板"""
        user_dir = self.user_templates_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        template_path = user_dir / f"{template_id}.yaml"
        
        with open(template_path, 'w', encoding='utf-8') as f:
            yaml.dump(template_data, f, allow_unicode=True, sort_keys=False)
        
        cache_key = f"{user_id}:{template_id}"
        if cache_key in self._template_cache:
            del self._template_cache[cache_key]
        
        logger.info(f"保存用户模板成功: {user_id}/{template_id}")
        return template_id
    
    def _parse_template(self, data: Dict) -> PromptTemplate:
        """解析模板数据为对象"""
        metadata = TemplateMetadata(**data['metadata'])
        variables = [TemplateVariable(**v) for v in data.get('variables', [])]
        
        return PromptTemplate(
            metadata=metadata,
            system_prompt=data['system_prompt'],
            user_prompt_template=data['user_prompt_template'],
            variables=variables
        )
```

### 4.3 修改web_content_extractor.py

```python
# 在文件开头添加
from extract_web.prompts.template_manager import PromptTemplateManager

class WebContentExtractor:
    def __init__(self, ...):
        # 现有代码...
        self.template_manager = PromptTemplateManager()
        self.default_template_id = "technical_article"
    
    def _extract_with_ai(self, url: str, template_id: str = None, user_id: str = None):
        """使用AI提取内容"""
        # 加载模板
        if template_id is None:
            template_id = self.default_template_id
        
        template = self.template_manager.load_template(template_id, user_id)
        
        # 使用模板
        system_prompt = template.system_prompt
        
        for i, batch_content in enumerate(batches):
            user_prompt = template.render_user_prompt(
                batch_index=i+1,
                total_batches=len(batches),
                batch_content=batch_content,
                dedup_hint=dedup_hint
            )
            # ... AI调用代码 ...
```

### 4.4 API路由（prompt_templates.py）

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from extract_web.prompts.template_manager import PromptTemplateManager

router = APIRouter(prefix="/api/prompt-templates")
template_manager = PromptTemplateManager()


@router.get("/system")
async def list_system_templates():
    """列出系统模板"""
    return template_manager.list_system_templates()


@router.get("/user/{user_id}")
async def list_user_templates(user_id: str):
    """列出用户模板"""
    return template_manager.list_user_templates(user_id)


@router.get("/{template_id}")
async def get_template(template_id: str, user_id: Optional[str] = None):
    """获取模板详情"""
    template = template_manager.load_template(template_id, user_id)
    return {
        "id": template_id,
        "metadata": template.metadata.__dict__,
        "system_prompt": template.system_prompt,
        "user_prompt_template": template.user_prompt_template
    }


@router.post("/user/{user_id}/{template_id}")
async def save_user_template(user_id: str, template_id: str, data: dict):
    """保存用户模板"""
    template_manager.save_user_template(user_id, template_id, data)
    return {"success": True}
```

---

## 5. 前端实现

### 5.1 页面布局

```html
<!-- 在PPT模板选择下方添加 -->
<div class="form-group">
  <label>提示词模板选择</label>
  <select id="templateSelect" class="form-control">
    <option value="technical_article">技术文章模板（系统）</option>
  </select>
  <button class="btn-secondary" onclick="viewTemplate()">查看/编辑</button>
</div>

<!-- 模板编辑弹窗 -->
<div id="templateModal" class="modal">
  <div class="modal-content">
    <h3>提示词模板编辑</h3>
    <div class="form-group">
      <label>模板名称</label>
      <input type="text" id="templateName" class="form-control">
    </div>
    <div class="form-group">
      <label>系统提示词</label>
      <textarea id="systemPrompt" rows="15"></textarea>
    </div>
    <div class="form-group">
      <label>用户提示词模板</label>
      <textarea id="userPromptTemplate" rows="15"></textarea>
    </div>
    <button onclick="saveAsMyTemplate()">保存为我的模板</button>
  </div>
</div>
```

### 5.2 JavaScript

```javascript
// 加载模板列表
async function loadTemplates() {
  const system = await fetch('/api/prompt-templates/system').then(r => r.json());
  const user = await fetch('/api/prompt-templates/user/current_user').then(r => r.json());
  
  const select = document.getElementById('templateSelect');
  select.innerHTML = '';
  
  system.forEach(t => {
    select.add(new Option(`${t.name}（系统）`, t.id));
  });
  
  user.forEach(t => {
    select.add(new Option(`${t.name}（我的）`, `user:${t.id}`));
  });
}

// 查看模板
async function viewTemplate() {
  const templateId = document.getElementById('templateSelect').value;
  const [type, id] = templateId.includes(':') ? templateId.split(':') : ['system', templateId];
  
  const template = await fetch(`/api/prompt-templates/${id}?user_id=${type === 'user' ? 'current_user' : ''}`).then(r => r.json());
  
  document.getElementById('templateName').value = template.metadata.name;
  document.getElementById('systemPrompt').value = template.system_prompt;
  document.getElementById('userPromptTemplate').value = template.user_prompt_template;
  
  document.getElementById('templateModal').style.display = 'block';
}

// 保存为我的模板
async function saveAsMyTemplate() {
  const data = {
    metadata: {
      name: document.getElementById('templateName').value,
      type: 'custom',
      version: '1.0.0'
    },
    system_prompt: document.getElementById('systemPrompt').value,
    user_prompt_template: document.getElementById('userPromptTemplate').value
  };
  
  await fetch('/api/prompt-templates/user/current_user/my_template_1', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  
  alert('保存成功！');
  loadTemplates();
}
```

---

## 6. 实施步骤

1. **创建目录结构**：创建`prompts/templates/`和`prompts/user_templates/`
2. **提取当前提示词**：将`web_content_extractor.py`中的提示词保存为`technical_article.yaml`
3. **实现核心类**：
   - `schema.py`：数据结构
   - `template_manager.py`：模板管理器
4. **修改提取器**：`web_content_extractor.py`使用模板管理器
5. **添加API**：`prompt_templates.py`提供REST接口
6. **前端UI**：在PPT生成页面添加模板选择和编辑功能
7. **测试验证**：确保系统模板和用户模板都能正常工作

---

## 7. 注意事项

- 系统模板目录只读，用户不能直接修改
- 用户模板目录添加到`.gitignore`
- 模板缓存机制避免重复加载
- 变量替换使用Python的`str.format()`
- 用户ID从会话中获取（需要实现用户认证）
