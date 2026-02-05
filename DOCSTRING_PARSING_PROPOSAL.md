# Docstring 自动提取方案（简化版）

## 方案概述

**核心思路**：原封不动返回 docstring，不进行解析，让客户端自己解析展示。

### 优势
1. ✅ **简单**：不需要复杂的解析逻辑
2. ✅ **灵活**：客户端可以按需解析和展示
3. ✅ **向后兼容**：不影响现有的手动设置的 metadata
4. ✅ **自动提取**：注册时自动从类 docstring 提取

## 实施内容

### 1. 扩展 ObjectMetadata

在 `routilux/tools/factory/metadata.py` 中添加：
```python
@dataclass
class ObjectMetadata:
    # 现有字段...
    docstring: Optional[str] = None  # 完整的 docstring，原封不动返回
```

### 2. 自动提取 docstring

在注册时自动提取：
- **overseer_demo_app.py**: 在 `main()` 中注册时自动提取
- **factory.py**: 当没有提供 metadata 时，自动从类 docstring 提取

### 3. 扩展 API 响应

在 `routilux/server/models/object.py` 中：
```python
class ObjectMetadataResponse(BaseModel):
    # 现有字段...
    docstring: Optional[str] = Field(
        None,
        description="Full docstring from the class/object. Returned as-is for client parsing."
    )
```

### 4. API 端点更新

`GET /api/factory/objects/{name}` 现在返回：
```json
{
  "name": "data_source",
  "description": "Generates sample data for testing pipelines",
  "category": "data_generation",
  "tags": ["source", "generator"],
  "example_config": {"count": 3},
  "version": "1.0.0",
  "docstring": "Generates sample data for testing pipelines.\n\nPurpose:\n    Generates a configurable number of data items...\n\nConfiguration:\n    {\n        \"count\": 3  # Number of data items...\n    }\n..."
}
```

## 使用方式

### 客户端解析示例

客户端可以按需解析 docstring：

```javascript
// 解析 docstring
function parseDocstring(docstring) {
  const sections = {};
  const lines = docstring.split('\n');
  let currentSection = null;
  let content = [];
  
  for (const line of lines) {
    const sectionMatch = line.match(/^(\w+)\s*(\(.*?\))?:/);
    if (sectionMatch) {
      if (currentSection) {
        sections[currentSection] = content.join('\n').trim();
      }
      currentSection = sectionMatch[1].toLowerCase();
      content = [line.substring(sectionMatch[0].length).trim()];
    } else if (currentSection) {
      content.push(line);
    }
  }
  
  if (currentSection) {
    sections[currentSection] = content.join('\n').trim();
  }
  
  return sections;
}
```

## 实施状态

✅ **已完成**：
1. 扩展 `ObjectMetadata` 添加 `docstring` 字段
2. 在 `overseer_demo_app.py` 中自动提取 docstring
3. 在 `factory.py` 中自动提取 docstring（当 metadata 未提供时）
4. 扩展 `ObjectMetadataResponse` 添加 `docstring` 字段
5. 更新 API 端点返回 docstring

## 注意事项

1. **不影响现有 metadata**：手动设置的 `description`, `category`, `tags` 等仍然有效
2. **可选字段**：`docstring` 是可选字段，如果没有 docstring 则返回 `null`
3. **原样返回**：docstring 不做任何处理，保持原始格式
4. **客户端解析**：客户端可以根据自己的需求解析和展示 docstring
