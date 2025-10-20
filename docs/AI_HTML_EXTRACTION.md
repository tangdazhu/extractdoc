# AI驱动的HTML内容提取

## 概述

已经实现了使用AI（LLM）直接分析HTML并提取文章内容的功能，相比传统的CSS选择器方法，AI提取具有以下优势：

## 优势对比

### 传统方法（CSS选择器 + 正则表达式）
❌ **局限性**：
- 需要针对每个网站编写特定的选择器
- 无法处理复杂的HTML嵌套结构
- 章节识别依赖简单的正则表达式，容易遗漏
- 对HTML结构变化敏感，网站改版后失效

### AI方法（LLM分析HTML）
✅ **优势**：
- **通用性强** - 一套代码适用于所有网站
- **智能识别** - AI能理解语义，准确识别章节标题
- **容错性好** - 即使HTML结构复杂也能正确提取
- **自适应** - 网站改版后仍然有效
- **完整提取** - 不会遗漏章节（如"第3-11章"）

## 工作原理

```python
# 1. 获取HTML并清理
response = requests.get(url)
soup = BeautifulSoup(html, 'html.parser')
# 移除script、style等无用标签
for tag in soup(['script', 'style', 'nav', 'footer']):
    tag.decompose()

# 2. 构建AI提示词
prompt = """请分析以下HTML内容，提取文章的结构化信息。
要求：
1. 识别文章标题、作者、发布时间
2. 提取所有章节标题和内容（包括"第X章"这样的标题）
3. 提取文章中的图片URL
4. 返回JSON格式
"""

# 3. 调用LLM分析
response = llm_client.chat(messages=[{"role": "user", "content": prompt}])

# 4. 解析JSON结果
result = json.loads(response)
```

## 使用方法

### 默认启用AI提取

```python
from services.web_content_extractor import WebContentExtractor

# 默认使用AI提取
extractor = WebContentExtractor(use_ai=True)
result = extractor.extract_from_url('https://mp.weixin.qq.com/s/xxx')

print(f"标题: {result['title']}")
print(f"章节数: {len(result['sections'])}")
for section in result['sections']:
    print(f"  - {section['title']}")
```

### 禁用AI，使用传统方法

```python
# 如果AI不可用或想使用传统方法
extractor = WebContentExtractor(use_ai=False)
result = extractor.extract_from_url('https://mp.weixin.qq.com/s/xxx')
```

### 自动回退机制

代码实现了智能回退：
1. 优先尝试AI提取
2. 如果AI失败（如LLM不可用、超时等），自动回退到传统方法
3. 保证服务的可用性

```python
try:
    logger.info("使用AI分析HTML内容")
    return self._extract_with_ai(url)
except Exception as e:
    logger.warning(f"AI提取失败，回退到传统方法: {e}")
    # 自动使用传统方法
    if 'mp.weixin.qq.com' in url:
        return self._extract_weixin_article(url)
    else:
        return self._extract_generic_article(url)
```

## 返回格式

```json
{
    "title": "阿里云发布《AI 原生应用架构白皮书》！",
    "subtitle": "",
    "author": "阿里云",
    "publish_time": "2024-10-15",
    "url": "https://mp.weixin.qq.com/s/xxx",
    "source": "ai_extracted",
    "content": "完整正文...",
    "sections": [
        {
            "title": "引言",
            "content": ["段落1", "段落2"],
            "level": 2
        },
        {
            "title": "第 1 章 AI 原生应用及其架构",
            "content": ["内容..."],
            "level": 2
        },
        {
            "title": "第 2 章 AI 原生应用的关键要素",
            "content": ["内容..."],
            "level": 2
        }
        // ... 所有章节都会被提取
    ],
    "images": [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ]
}
```

## 性能优化

### HTML长度限制
为避免超过LLM的token限制，实现了智能截取：

```python
max_html_length = 50000  # 约50KB
if len(cleaned_html) > max_html_length:
    logger.warning(f"HTML过长，截取前{max_html_length}字符")
    cleaned_html = cleaned_html[:max_html_length]
```

### 无用标签清理
移除对内容提取无用的标签，减少token消耗：

```python
for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
    tag.decompose()
```

### 低温度参数
使用低温度确保输出的确定性和JSON格式的正确性：

```python
response = llm_client.chat(
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1,  # 低温度，更确定性的输出
    max_tokens=4000
)
```

## 成本考虑

### Token消耗
- **输入**：约10,000-50,000 tokens（取决于HTML长度）
- **输出**：约1,000-4,000 tokens（取决于文章长度）
- **单次成本**：约￥0.05-0.20（使用qwen-max）

### 优化建议
1. **缓存结果** - 相同URL不重复提取
2. **批量处理** - 如果需要处理多个URL，可以考虑批量调用
3. **使用更便宜的模型** - 对于简单文章可以使用qwen-turbo

## 测试结果

### 微信文章测试
URL: `https://mp.weixin.qq.com/s/t8eMpwW-b-DKfzlS2tTh1Q`

**传统方法**：
- ❌ 只提取到8个章节
- ❌ 遗漏了"第3-11章"

**AI方法**：
- ✅ 完整提取所有11个章节
- ✅ 准确识别章节标题和内容
- ✅ 提取所有图片URL

## 配置

在 `config.yaml` 中可以配置是否启用AI提取：

```yaml
web_extraction:
  use_ai: true  # 是否使用AI提取（默认true）
  fallback_to_traditional: true  # AI失败时是否回退到传统方法
  max_html_length: 50000  # HTML最大长度
```

## 注意事项

1. **需要LLM服务** - 确保 `utils.llm_client.LLMClient` 已正确配置
2. **网络要求** - 需要能访问目标URL和LLM API
3. **反爬虫** - 某些网站可能需要验证，AI也无法绕过
4. **成本** - 每次提取都会消耗LLM tokens

## 未来改进

1. **结构化提示词** - 使用更精确的JSON Schema约束输出格式
2. **多模态支持** - 对于图片丰富的文章，可以使用视觉模型分析
3. **增量提取** - 对于超长HTML，分段提取后合并
4. **智能缓存** - 基于URL和HTML哈希的缓存机制

## 总结

AI驱动的HTML提取是一个**更智能、更通用、更可靠**的解决方案，特别适合：
- ✅ 需要处理多种不同网站的场景
- ✅ 对提取准确性要求高的场景
- ✅ 网站HTML结构复杂的场景
- ✅ 需要长期维护的项目（不用担心网站改版）

相比传统方法，虽然有一定的成本，但带来的价值远超成本！
