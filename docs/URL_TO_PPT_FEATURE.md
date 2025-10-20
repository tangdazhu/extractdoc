# URL到PPT功能说明

## 功能概述

从网络文章URL智能提取内容并生成专业PPT演示文稿。

**支持的URL类型**：
- ✅ 微信公众号文章（mp.weixin.qq.com）
- ✅ 通用网页文章

---

## 功能特性

### 1. 智能内容提取

**提取信息**：
- 文章标题
- 作者信息
- 发布时间
- 章节结构
- 正文内容
- 图片资源

**提取策略**：
- 微信公众号：专门优化的提取器
- 通用网页：智能识别文章结构

### 2. AI内容分析

**使用AI模型**：Qwen-Max（通义千问）

**分析内容**：
- 自动提取核心主题
- 识别重要章节
- 生成PPT结构
- 提炼关键要点

**生成结构**：
```json
{
  "cover": {
    "title": "文章标题",
    "subtitle": "核心主题",
    "author": "作者",
    "date": "发布时间"
  },
  "slides": [
    {
      "title": "章节标题",
      "points": ["要点1", "要点2", "要点3"],
      "summary": "总结文字"
    }
  ]
}
```

### 3. 专业PPT生成

**支持模板**：
- `style_a`: 简约商务风格
- `style_b`: 学术报告风格

**PPT结构**：
1. **封面页**：标题、副标题、作者、时间
2. **内容页**：3-8页核心内容，每页3-5个要点
3. **格式规范**：符合预定义模板样式

---

## 使用方法

### 方法1：通过Web界面

1. 访问"文档生成"页面
2. 选择"网络文章URL"选项
3. 输入文章URL（如：https://mp.weixin.qq.com/s/xxxxx）
4. 选择PPT模板样式
5. 点击"生成PPT"
6. 等待生成完成并下载

### 方法2：通过API调用

```python
from extract_web.converter.services.url_to_ppt_converter import URLToPPTConverter

# 创建转换器
converter = URLToPPTConverter(style="style_a")

# 转换URL到PPT
result = converter.convert(
    url="https://mp.weixin.qq.com/s/t8eMpwW-b-DKfzlS2tTh1Q",
    output_path="output.pptx"
)

if result['success']:
    print(f"成功生成PPT: {result['slides_count']}页")
else:
    print(f"生成失败: {result['message']}")
```

### 方法3：通过Django视图

```python
# POST /api/document-generation/
{
    "mode": "ppt",
    "source_url": "https://mp.weixin.qq.com/s/xxxxx",
    "template": "style_a"
}
```

---

## 示例URL

### 微信公众号文章

```
https://mp.weixin.qq.com/s/t8eMpwW-b-DKfzlS2tTh1Q
```

**特点**：
- 完整的文章结构
- 清晰的章节划分
- 丰富的内容信息

---

## 技术架构

### 组件说明

#### 1. WebContentExtractor（网页内容提取器）

**文件**：`extract_web/converter/services/web_content_extractor.py`

**功能**：
- 从URL获取网页内容
- 解析HTML结构
- 提取文章信息
- 识别章节和段落

**支持的网站**：
- 微信公众号（专门优化）
- 通用网页（智能识别）

#### 2. WebToPPTAnalyzer（AI内容分析器）

**文件**：`extract_web/converter/services/web_to_ppt_analyzer.py`

**功能**：
- 调用AI模型分析内容
- 生成PPT结构
- 提炼关键要点
- 优化内容呈现

**AI模型配置**：
```yaml
ai_document_analysis:
  model: "qwen-max"
  temperature: 0.1
  max_tokens: 4000
```

#### 3. URLToPPTConverter（URL到PPT转换器）

**文件**：`extract_web/converter/services/url_to_ppt_converter.py`

**功能**：
- 整合提取和分析流程
- 生成PPT文件
- 应用模板样式
- 格式化内容

---

## 配置说明

### PPT模板配置

**位置**：`config/application.yaml`

```yaml
ppt_generation:
  slide_size:
    width: 10.0
    height: 7.5
  
  styles:
    style_a:
      name: "简约商务风格"
      template_path: "config/templates/business_template.pptx"
      title_font_size: 44
      content_font_size: 18
    
    style_b:
      name: "学术报告风格"
      template_path: "config/templates/academic_template.pptx"
      title_font_size: 40
      content_font_size: 16
```

### AI模型配置

```yaml
ai_document_analysis:
  provider: "dashscope"
  model: "qwen-max"
  temperature: 0.1
  max_tokens: 4000
```

---

## 测试

### 运行测试脚本

```bash
python test_url_to_ppt.py
```

**测试内容**：
1. ✅ 网页内容提取
2. ✅ AI内容分析
3. ✅ PPT生成

**预期输出**：
```
总计: 3/3 测试通过
[SUCCESS] 所有测试通过！URL到PPT功能正常！
```

---

## 工作流程

```
1. 用户输入URL
   ↓
2. WebContentExtractor 提取网页内容
   - 获取HTML
   - 解析文章结构
   - 提取标题、作者、时间
   - 识别章节和段落
   ↓
3. WebToPPTAnalyzer AI分析
   - 构建AI提示词
   - 调用Qwen-Max模型
   - 解析AI返回结果
   - 生成PPT结构
   ↓
4. URLToPPTConverter 生成PPT
   - 加载模板文件
   - 创建封面页
   - 创建内容页
   - 应用样式格式
   ↓
5. 返回生成的PPT文件
```

---

## 注意事项

### 1. 网络访问

- 需要能够访问目标URL
- 微信公众号文章可能有访问限制
- 建议使用稳定的网络环境

### 2. AI模型调用

- 需要配置DashScope API密钥
- AI调用可能需要一定时间
- 建议设置合理的超时时间

### 3. 内容质量

- PPT质量取决于原文章质量
- 结构清晰的文章效果更好
- 建议选择章节明确的文章

### 4. 模板文件

- 确保模板文件存在
- 模板路径配置正确
- 可以自定义模板样式

---

## 常见问题

### Q1: URL提取失败怎么办？

**A**: 检查以下几点：
- URL格式是否正确（需要http://或https://）
- 网络连接是否正常
- 目标网站是否可访问
- 是否有反爬虫限制

### Q2: AI分析失败怎么办？

**A**: 可能的原因：
- DashScope API密钥未配置
- AI模型调用超时
- 文章内容过长或过短

**解决方案**：
- 检查API密钥配置
- 增加超时时间
- 使用备用结构生成器

### Q3: 生成的PPT页数太少？

**A**: 
- AI会根据文章内容自动决定页数（3-8页）
- 如果文章内容较少，页数会相应减少
- 可以修改AI提示词调整页数范围

### Q4: 如何自定义PPT样式？

**A**: 
1. 创建自己的PPT模板文件
2. 在 `config/application.yaml` 中添加新样式配置
3. 指定模板路径和字体大小
4. 使用新样式名称生成PPT

---

## 未来改进

### 计划功能

- [ ] 支持更多网站类型
- [ ] 图片自动下载并插入PPT
- [ ] 支持视频链接提取
- [ ] 批量URL转换
- [ ] 自定义AI提示词
- [ ] PPT预览功能

### 性能优化

- [ ] 缓存已提取的内容
- [ ] 并行处理多个URL
- [ ] 优化AI调用效率
- [ ] 减少网络请求次数

---

## 相关文档

- [配置管理完整指南](CONFIG_COMPLETE_GUIDE.md)
- [项目README](../README.md)

---

**创建时间**：2025-10-20  
**维护人员**：项目团队  
**版本**：1.0
