# 缓存目录说明

## 目录结构

```
cache/
└── web_extraction/     # 网页提取缓存
    ├── <md5_hash>.json # 缓存文件（以URL的MD5命名）
    └── ...
```

## 缓存机制

### 工作原理

1. **缓存生成**：当使用AI提取网页内容时，提取结果会自动保存到缓存文件
2. **缓存命中**：再次提取相同URL时，直接从缓存加载，跳过AI调用
3. **节省Token**：避免重复调用AI API，大幅节省Token消耗

### 缓存文件格式

缓存文件为JSON格式，包含完整的提取结果：
```json
{
  "title": "文章标题",
  "subtitle": "副标题",
  "author": "作者",
  "publish_time": "发布时间",
  "content": "正文内容",
  "sections": [...],
  "images": [...]
}
```

### 缓存Key生成

- 使用URL的MD5哈希作为缓存文件名
- 相同URL始终对应相同的缓存文件

## 使用方法

### 自动缓存

正常使用即可，系统会自动处理缓存：

```python
from extract_web.converter.services.web_content_extractor import WebContentExtractor

extractor = WebContentExtractor(use_ai=True)

# 第一次调用：会调用AI并保存缓存
result1 = extractor.extract_from_url("https://example.com/article")

# 第二次调用：直接从缓存加载，不调用AI
result2 = extractor.extract_from_url("https://example.com/article")
```

### 清理缓存

#### 清理指定URL的缓存

```python
# 清理特定URL的缓存（下次访问会重新调用AI）
extractor.clear_cache("https://example.com/article")
```

#### 清理所有缓存

```python
# 清理所有缓存
extractor.clear_cache()
```

#### 手动删除缓存文件

直接删除 `cache/web_extraction/` 目录下的文件即可。

## 配置

缓存目录可在 `config/application.yaml` 中配置：

```yaml
web_extraction:
  cache_dir: "cache/web_extraction"  # 缓存目录路径
```

## 注意事项

1. **缓存不会自动过期**：如果网页内容更新，需要手动清理缓存
2. **缓存占用空间**：每个缓存文件约几KB到几十KB，定期清理可节省空间
3. **测试时建议启用缓存**：避免重复消耗Token
4. **生产环境谨慎使用**：确保缓存的内容是最新的

## 日志输出

启用缓存后，日志会显示：

```
INFO 从缓存加载: cache/web_extraction/abc123def456.json
INFO 使用缓存结果，跳过AI调用
```

或

```
INFO 保存到缓存: cache/web_extraction/abc123def456.json
```
