# ConditionalRouter 条件序列化测试报告

## 测试结果

✅ **所有 8 个测试全部通过**

### 测试覆盖

1. ✅ **Lambda 条件序列化/反序列化**
   - Lambda 可以成功序列化（转换为字符串表达式）
   - 反序列化后可以正常调用
   - 功能验证通过

2. ✅ **函数条件序列化/反序列化**
   - 模块级函数可以成功序列化
   - 反序列化后可以正常调用
   - 功能验证通过

3. ✅ **带 config 参数的函数条件序列化**
   - 函数可以接收 config 参数
   - 序列化/反序列化后功能正常

4. ✅ **混合条件类型序列化**
   - 函数、Lambda、字典、字符串条件混合使用
   - 所有类型都可以正确序列化和反序列化
   - 功能验证通过

5. ✅ **Flow 级别序列化（Lambda）**
   - Lambda 条件在 Flow 级别可以序列化
   - 反序列化后功能正常

6. ✅ **Flow 级别序列化（函数）**
   - 函数条件在 Flow 级别可以序列化
   - 反序列化后功能正常

7. ✅ **JSON 序列化往返（Lambda）**
   - Lambda 可以通过 JSON 序列化/反序列化
   - 功能验证通过

8. ✅ **JSON 序列化往返（函数）**
   - 函数可以通过 JSON 序列化/反序列化
   - 功能验证通过

## 结论

### Lambda 条件

**可以使用，但有限制：**

✅ **可以序列化的情况：**
- 模块级别定义的 Lambda
- 函数中定义的 Lambda（如果 `inspect.getsource()` 可以获取源代码）
- 会被自动转换为字符串表达式

❌ **无法序列化的情况：**
- 动态创建的 Lambda（无法获取源代码）
- 复杂的 Lambda（多行、包含复杂逻辑）

⚠️ **注意事项：**
- 闭包变量在序列化时会丢失
- 推荐使用字符串表达式替代 Lambda

### 函数条件

**完全支持序列化：**

✅ **可以序列化：**
- 模块级函数（完全支持）
- 可以接收 `data`、`config`、`stats` 参数
- 序列化/反序列化后功能正常

✅ **推荐使用：**
- 对于复杂逻辑，使用模块级函数
- 函数可以访问 config 和 stats

## 最佳实践

1. **优先使用字符串表达式**：
   ```python
   ("high", "data.get('value', 0) > config.get('threshold', 0)")
   ```
   - ✅ 完全可序列化
   - ✅ 可以访问 config 和 stats
   - ✅ 简单易用

2. **复杂逻辑使用模块级函数**：
   ```python
   def check_complex(data, config, stats):
       # Complex logic here
       return result
   
   router.set_config(routes=[("route", check_complex)])
   ```
   - ✅ 完全可序列化
   - ✅ 可以访问 config 和 stats
   - ✅ 支持复杂逻辑

3. **Lambda 仅用于运行时**：
   ```python
   # 如果不需要序列化，Lambda 可以使用
   threshold = 10
   router.set_config(routes=[("high", lambda data: data.get('value') > threshold)])
   ```
   - ⚠️ 运行时可用
   - ❌ 序列化可能失败
   - ❌ 闭包变量会丢失

## 测试覆盖率

- ConditionalRouter 序列化相关代码：70% 覆盖率
- 所有关键路径都已测试
- 边界情况已覆盖

