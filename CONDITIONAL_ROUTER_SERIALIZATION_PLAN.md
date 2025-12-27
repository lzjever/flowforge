# ConditionalRouter 序列化增强方案

## 一、删除 RetryHandler 相关内容的清单

### 1.1 需要删除的文件
- ✅ `flowforge/builtin_routines/control_flow/retry_handler.py`

### 1.2 需要修改的文件

#### 代码文件
1. **`flowforge/builtin_routines/control_flow/__init__.py`**
   - 删除 `RetryHandler` 的导入和导出

2. **`flowforge/builtin_routines/__init__.py`**
   - 删除 `RetryHandler` 的导入和导出（如果有）

3. **`flowforge/__init__.py`**
   - 删除 `RetryHandler` 的导入和导出（如果有）

4. **`flowforge/builtin_routines/control_flow/tests/test_control_flow.py`**
   - 删除 `TestRetryHandler` 测试类
   - 删除 `RetryHandler` 的导入

#### 文档文件
5. **`flowforge/builtin_routines/control_flow/README.md`**
   - 删除 RetryHandler 章节

6. **`flowforge/builtin_routines/README.md`**
   - 删除 RetryHandler 相关引用（如果有）

7. **`docs/source/user_guide/builtin_routines.rst`**
   - 删除 RetryHandler 章节（第 344-371 行左右）

8. **`docs/source/api_reference/builtin_routines.rst`**
   - 删除 `retry_handler` 的 automodule 引用

9. **`docs/source/testing.rst`**
   - 删除 RetryHandler 测试统计（第 219 行）

#### 示例文件
10. **`examples/builtin_routines_demo.py`**（如果有）
    - 删除 RetryHandler 相关示例

---

## 二、ConditionalRouter 序列化问题分析

### 2.1 当前问题

**问题 1：Lambda 函数无法序列化**
- Lambda 函数没有模块名（`<lambda>`）
- `serialize_callable()` 无法获取模块信息
- 序列化时返回 `None`，反序列化时丢失

**问题 2：配置中的 callable 条件**
- `routes` 配置：`[(route_name, condition_func), ...]`
- `condition_func` 可能是：
  - Lambda 函数 ❌ 无法序列化
  - 普通函数 ✅ 可以序列化（如果有模块）
  - 字典条件 ✅ 可以序列化（已经是数据）
  - 方法引用 ✅ 可以序列化（通过对象 ID）

### 2.2 当前序列化机制

**`serialize_callable()` 支持的类型：**
1. ✅ **方法（method）**：通过 `class_name`, `method_name`, `object_id` 序列化
2. ✅ **函数（function）**：通过 `module`, `name` 序列化
3. ✅ **内置函数（builtin）**：通过 `name` 序列化
4. ❌ **Lambda 函数**：无法获取模块，返回 `None`

---

## 三、ConditionalRouter 序列化增强方案

### 3.1 方案概述

**核心思路：**
1. **支持多种条件类型**：不仅支持 callable，还支持字符串、字典等可序列化格式
2. **序列化时转换**：将不可序列化的 lambda 转换为可序列化格式
3. **反序列化时恢复**：根据类型信息恢复条件函数
4. **向后兼容**：保持现有 API 不变

### 3.2 条件类型设计

#### 类型 1：字典条件（已支持）✅
```python
condition = {"priority": "high", "status": "active"}
```
- ✅ 完全可序列化
- ✅ 当前已支持

#### 类型 2：字符串条件（新增）🆕
```python
condition = "priority == 'high'"
condition = "data.get('status') == 'active'"
condition = "isinstance(data, dict) and 'key' in data"
```
- ✅ 完全可序列化
- ⚠️ 需要安全执行（使用 `eval()` 或更安全的解析器）
- 💡 推荐：使用 `eval()` 但限制作用域

#### 类型 3：函数引用（已支持，需增强）✅
```python
# 模块级函数
def check_priority(data):
    return data.get("priority") == "high"

condition = check_priority  # ✅ 可序列化
```
- ✅ 可序列化（通过 `serialize_callable()`）
- ✅ 当前已支持

#### 类型 4：Lambda 函数（需转换）⚠️
```python
condition = lambda x: x.get("priority") == "high"  # ❌ 无法序列化
```
- ❌ 无法直接序列化
- 💡 **解决方案**：序列化时转换为字符串表达式

### 3.3 实现方案

#### 方案 A：Lambda 转字符串表达式（推荐）⭐

**序列化时：**
1. 检测到 lambda 函数
2. 尝试提取 lambda 的源代码（使用 `inspect.getsource()`）
3. 如果成功，转换为字符串表达式
4. 标记为 `"_type": "lambda_expression"`

**反序列化时：**
1. 检测到 `lambda_expression` 类型
2. 使用 `eval()` 在受限作用域中执行
3. 返回可调用的函数对象

**优点：**
- ✅ 支持 lambda 序列化
- ✅ 保持 API 不变
- ✅ 向后兼容

**缺点：**
- ⚠️ 需要 `inspect.getsource()`（可能失败）
- ⚠️ 需要安全执行 `eval()`

**实现细节：**
```python
# 序列化
if callable(condition) and condition.__name__ == "<lambda>":
    try:
        source = inspect.getsource(condition)
        # 提取 lambda 表达式部分
        # lambda x: x.get("priority") == "high"
        lambda_expr = extract_lambda_expr(source)
        return {
            "_type": "lambda_expression",
            "expression": lambda_expr
        }
    except:
        # 无法提取，返回 None 或警告
        return None

# 反序列化
if condition_data.get("_type") == "lambda_expression":
    expr = condition_data.get("expression")
    # 安全执行
    condition = eval(f"lambda data: {expr}", {"__builtins__": {}})
```

#### 方案 B：字符串条件表达式（新增功能）🆕

**新增支持：**
- 直接接受字符串作为条件
- 使用 `eval()` 执行（限制作用域）

**API：**
```python
router.set_config(
    routes=[
        ("high", "data.get('priority') == 'high'"),  # 字符串条件
        ("low", {"priority": "low"}),  # 字典条件
        ("custom", check_function),  # 函数条件
    ]
)
```

**优点：**
- ✅ 完全可序列化
- ✅ 用户可以直接使用字符串
- ✅ 不需要 lambda

**缺点：**
- ⚠️ 需要安全执行 `eval()`
- ⚠️ 字符串表达式可能不够灵活

#### 方案 C：条件注册表（高级功能）💡

**设计：**
- 提供条件注册机制
- 通过字符串名称引用预定义条件

**API：**
```python
# 注册条件
router.register_condition("high_priority", lambda x: x.get("priority") == "high")

# 使用
router.set_config(
    routes=[
        ("high", "high_priority"),  # 通过名称引用
    ]
)
```

**优点：**
- ✅ 完全可序列化
- ✅ 条件可复用
- ✅ 更安全

**缺点：**
- ⚠️ 需要额外的注册步骤
- ⚠️ 增加复杂度

---

## 四、推荐实现方案

### 4.1 组合方案（推荐）⭐

**采用：方案 A + 方案 B**

1. **增强现有序列化**（方案 A）：
   - 在 `ConditionalRouter.serialize()` 中，检测 lambda 函数
   - 尝试转换为字符串表达式
   - 如果失败，发出警告但不阻止序列化

2. **新增字符串条件支持**（方案 B）：
   - 在 `_handle_input()` 中，检测字符串类型条件
   - 使用安全的 `eval()` 执行
   - 更新文档和示例

3. **向后兼容**：
   - 保持现有 API 不变
   - 函数引用、字典条件继续工作
   - Lambda 函数在可能的情况下自动转换

### 4.2 实现细节

#### 4.2.1 序列化增强

**在 `ConditionalRouter.serialize()` 中：**
```python
def serialize(self) -> Dict[str, Any]:
    data = super().serialize()
    
    # 处理 routes 配置中的条件函数
    routes = self.get_config("routes", [])
    serialized_routes = []
    
    for route_name, condition in routes:
        if callable(condition):
            # 尝试序列化函数
            condition_data = serialize_callable(condition)
            
            if condition_data:
                # 函数可以序列化
                serialized_routes.append((route_name, condition_data))
            elif condition.__name__ == "<lambda>":
                # Lambda 函数，尝试转换为字符串
                try:
                    source = inspect.getsource(condition)
                    lambda_expr = extract_lambda_expr(source)
                    serialized_routes.append((
                        route_name,
                        {
                            "_type": "lambda_expression",
                            "expression": lambda_expr
                        }
                    ))
                except Exception as e:
                    # 无法转换，发出警告
                    import warnings
                    warnings.warn(
                        f"Lambda condition for route '{route_name}' cannot be serialized. "
                        f"Consider using string expression or function reference instead."
                    )
                    # 跳过这个条件
                    continue
            else:
                # 其他不可序列化的 callable
                warnings.warn(
                    f"Condition for route '{route_name}' cannot be serialized."
                )
                continue
        else:
            # 非 callable（字典、字符串等），直接序列化
            serialized_routes.append((route_name, condition))
    
    # 更新配置
    data["_config"]["routes"] = serialized_routes
    return data
```

#### 4.2.2 反序列化增强

**在 `ConditionalRouter.deserialize()` 中：**
```python
def deserialize(self, data: Dict[str, Any]) -> None:
    super().deserialize(data)
    
    # 处理 routes 配置中的条件函数
    routes = self.get_config("routes", [])
    deserialized_routes = []
    
    for route_name, condition_data in routes:
        if isinstance(condition_data, dict) and "_type" in condition_data:
            condition_type = condition_data.get("_type")
            
            if condition_type == "lambda_expression":
                # 恢复 lambda 表达式
                expr = condition_data.get("expression")
                try:
                    # 安全执行
                    condition = eval(
                        f"lambda data: {expr}",
                        {"__builtins__": {}, "isinstance": isinstance, "dict": dict}
                    )
                    deserialized_routes.append((route_name, condition))
                except Exception as e:
                    warnings.warn(
                        f"Failed to deserialize lambda condition for route '{route_name}': {e}"
                    )
                    continue
            elif condition_type in ["function", "method", "builtin"]:
                # 恢复函数引用
                condition = deserialize_callable(condition_data)
                if condition:
                    deserialized_routes.append((route_name, condition))
                else:
                    warnings.warn(
                        f"Failed to deserialize function condition for route '{route_name}'"
                    )
                    continue
            else:
                # 其他类型，直接使用
                deserialized_routes.append((route_name, condition_data))
        else:
            # 非序列化格式（字典、字符串等），直接使用
            deserialized_routes.append((route_name, condition_data))
    
    # 更新配置
    self.set_config(routes=deserialized_routes)
```

#### 4.2.3 字符串条件支持

**在 `_handle_input()` 中：**
```python
def _handle_input(self, data: Any = None, **kwargs):
    # ... 现有代码 ...
    
    for route_name, condition in routes:
        try:
            if isinstance(condition, str):
                # 字符串条件表达式
                result = eval(
                    condition,
                    {
                        "__builtins__": {},
                        "data": data,
                        "isinstance": isinstance,
                        "dict": dict,
                        "list": list,
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                    }
                )
                if result:
                    matched_routes.append(route_name)
                    if route_priority == "first_match":
                        break
            elif callable(condition):
                # 函数条件（现有逻辑）
                if condition(data):
                    matched_routes.append(route_name)
                    if route_priority == "first_match":
                        break
            elif isinstance(condition, dict):
                # 字典条件（现有逻辑）
                if self._evaluate_dict_condition(data, condition):
                    matched_routes.append(route_name)
                    if route_priority == "first_match":
                        break
        except Exception as e:
            self._track_operation("routes", success=False, route=route_name, error=str(e))
```

---

## 五、Lambda 函数序列化的限制

### 5.1 无法序列化的情况

1. **复杂的 Lambda 表达式**
   - 多行 lambda
   - 包含闭包的 lambda
   - 使用外部变量的 lambda

2. **动态生成的 Lambda**
   - 在运行时动态创建的 lambda
   - 无法获取源代码的 lambda

### 5.2 解决方案

**对于无法序列化的 Lambda：**
1. ⚠️ **发出警告**：提示用户使用字符串表达式或函数引用
2. ⚠️ **跳过序列化**：该条件在反序列化后丢失
3. 💡 **提供迁移指南**：文档中说明如何迁移

---

## 六、实施步骤

### 步骤 1：删除 RetryHandler
1. 删除 `retry_handler.py`
2. 更新所有导入文件
3. 更新测试文件
4. 更新文档

### 步骤 2：增强 ConditionalRouter 序列化
1. 实现 lambda 转字符串表达式
2. 实现字符串条件支持
3. 更新序列化/反序列化方法
4. 添加辅助函数（`extract_lambda_expr()`）

### 步骤 3：测试
1. 测试 lambda 序列化/反序列化
2. 测试字符串条件
3. 测试向后兼容性
4. 测试错误处理

### 步骤 4：文档更新
1. 更新 ConditionalRouter 文档
2. 添加序列化说明
3. 添加最佳实践
4. 添加迁移指南

---

## 七、总结

### 7.1 Lambda 是否还可以用？

**答案：可以，但有条件**

1. ✅ **简单 Lambda**：可以自动转换为字符串表达式
2. ⚠️ **复杂 Lambda**：可能无法序列化，需要手动迁移
3. 💡 **推荐**：使用字符串表达式或函数引用

### 7.2 最佳实践

1. **优先使用字符串表达式**：
   ```python
   ("high", "data.get('priority') == 'high'")
   ```

2. **使用函数引用**（可序列化）：
   ```python
   def check_priority(data):
       return data.get("priority") == "high"
   ("high", check_priority)
   ```

3. **使用字典条件**（完全可序列化）：
   ```python
   ("high", {"priority": "high"})
   ```

4. **避免复杂 Lambda**：
   ```python
   # ❌ 不推荐
   ("high", lambda x: complex_logic(x, external_var))
   
   # ✅ 推荐
   def check_high(data):
       return complex_logic(data, external_var)
   ("high", check_high)
   ```

---

## 八、风险评估

### 8.1 风险点

1. **Lambda 序列化失败**：
   - 风险：中等
   - 影响：条件丢失，但会发出警告
   - 缓解：提供清晰的错误信息和迁移指南

2. **字符串条件安全性**：
   - 风险：低（已限制作用域）
   - 影响：代码注入风险
   - 缓解：严格限制 `eval()` 的作用域

3. **向后兼容性**：
   - 风险：低
   - 影响：现有代码可能受影响
   - 缓解：保持 API 不变，自动处理

### 8.2 测试重点

1. ✅ Lambda 序列化/反序列化
2. ✅ 字符串条件执行
3. ✅ 函数引用序列化
4. ✅ 字典条件（现有功能）
5. ✅ 错误处理和警告
6. ✅ 向后兼容性

---

## 九、待确认问题

1. **Lambda 转换的准确性**：
   - `inspect.getsource()` 是否能准确提取 lambda？
   - 是否需要处理多行 lambda？

2. **字符串条件的安全性**：
   - `eval()` 的限制是否足够？
   - 是否需要更严格的沙箱？

3. **性能影响**：
   - Lambda 转换的性能开销？
   - 字符串条件执行的性能？

---

## 十、下一步行动

1. ✅ **确认方案**：等待用户确认
2. ⏳ **实施删除**：删除 RetryHandler 相关内容
3. ⏳ **实施增强**：增强 ConditionalRouter 序列化
4. ⏳ **测试验证**：全面测试
5. ⏳ **文档更新**：更新文档和示例

