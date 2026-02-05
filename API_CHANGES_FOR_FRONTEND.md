# Flow API 变更说明 - 前端团队

## 变更摘要

本次更新修复了 Flow API 的设计缺陷，使其与 Workers/Jobs API 保持一致，符合 RESTful 最佳实践。所有变更都是**向后不兼容**的，需要前端代码相应调整。

## 变更日期

2025-01-21

## 主要变更

### 1. 重复 flow_id 创建现在返回 409 Conflict

**变更前**：
- `POST /api/v1/flows` 使用已存在的 `flow_id` 时，返回 `201 Created`
- 会静默覆盖现有 flow

**变更后**：
- `POST /api/v1/flows` 使用已存在的 `flow_id` 时，返回 `409 Conflict`
- 错误代码：`FLOW_ALREADY_EXISTS`
- 不会覆盖现有 flow

**影响**：
- 前端需要处理 409 错误，显示"flow_id 已存在"的错误提示
- 不再需要手动检查 flow_id 是否存在（API 会自动检查）

**示例响应**：
```json
{
  "error": {
    "code": "FLOW_ALREADY_EXISTS",
    "message": "Flow 'my_flow' already exists",
    "details": {
      "flow_id": "my_flow"
    }
  }
}
```

**迁移指南**：
```typescript
// 变更前
const response = await api.flows.create({ flow_id: "my_flow" });
if (response.status === 201) {
  // 可能覆盖了现有 flow
}

// 变更后
try {
  const response = await api.flows.create({ flow_id: "my_flow" });
  // 成功创建
} catch (error) {
  if (error.status === 409 && error.body?.error?.code === "FLOW_ALREADY_EXISTS") {
    // 显示错误：flow_id 已存在
    showError("Flow ID already exists. Please choose a different name.");
  }
}
```

---

### 2. flow_id 优先级：请求参数优先于 DSL

**变更前**：
- 如果同时提供 `request.flow_id` 和 DSL（包含 `flow_id`），DSL 中的 `flow_id` 会覆盖请求参数
- 基于模板创建新 flow 时无法使用新的 flow_id

**变更后**：
- `request.flow_id` **优先于** DSL 中的 `flow_id`
- 如果提供了 `request.flow_id`，它会覆盖 DSL 中的 `flow_id`
- 支持基于模板创建新 flow（通过覆盖模板的 flow_id）

**影响**：
- 基于模板创建 flow 的功能现在可以正常工作
- 前端可以安全地使用模板 DSL，同时指定新的 flow_id

**示例**：
```typescript
// 从模板创建新 flow
const templateDsl = await api.flows.exportDSL("template_flow", "yaml");

// 现在可以安全地覆盖 flow_id
const newFlow = await api.flows.create({
  flow_id: "my_new_flow",  // 这个会覆盖 DSL 中的 flow_id
  dsl: templateDsl.dsl
});

// 创建的 flow_id 是 "my_new_flow"，而不是 "template_flow"
console.log(newFlow.flow_id); // "my_new_flow"
```

---

### 3. 404 错误现在返回正确的错误代码

**变更前**：
- 所有 404 错误返回 `INTERNAL_ERROR` 错误代码
- 客户端无法区分"资源不存在"和"内部错误"

**变更后**：
- 所有 404 错误返回正确的资源特定错误代码：
  - `FLOW_NOT_FOUND` - Flow 不存在
  - `ROUTINE_NOT_FOUND` - Routine 不存在
- 错误响应包含结构化信息

**影响**：
- 前端可以更精确地处理不同类型的"不存在"错误
- 错误处理逻辑更清晰

**示例响应**：
```json
{
  "error": {
    "code": "FLOW_NOT_FOUND",
    "message": "Flow 'my_flow' not found",
    "details": {
      "flow_id": "my_flow"
    }
  }
}
```

**迁移指南**：
```typescript
// 变更前
try {
  await api.flows.delete("my_flow");
} catch (error) {
  if (error.status === 404) {
    // 无法区分是 flow 不存在还是其他资源不存在
    console.log("Not found");
  }
}

// 变更后
try {
  await api.flows.delete("my_flow");
} catch (error) {
  if (error.status === 404) {
    const errorCode = error.body?.error?.code;
    if (errorCode === "FLOW_NOT_FOUND") {
      // 明确知道是 flow 不存在
      showError("Flow not found");
    }
  }
}
```

---

## 受影响的端点

### POST /api/v1/flows
- **变更**：添加重复 flow_id 检查，返回 409 Conflict
- **变更**：`request.flow_id` 现在优先于 DSL 中的 `flow_id`

### DELETE /api/v1/flows/{flow_id}
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### GET /api/v1/flows/{flow_id}
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### GET /api/v1/flows/{flow_id}/dsl
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### POST /api/v1/flows/{flow_id}/validate
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### GET /api/v1/flows/{flow_id}/routines/{routine_id}/info
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 或 `ROUTINE_NOT_FOUND`

### GET /api/v1/flows/{flow_id}/routines
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### GET /api/v1/flows/{flow_id}/connections
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### POST /api/v1/flows/{flow_id}/connections
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

### DELETE /api/v1/flows/{flow_id}/routines/{routine_id}
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 或 `ROUTINE_NOT_FOUND`

### DELETE /api/v1/flows/{flow_id}/connections/{connection_index}
- **变更**：404 错误现在返回 `FLOW_NOT_FOUND` 而不是 `INTERNAL_ERROR`

---

## 错误代码参考

### Flow 相关错误代码
- `FLOW_NOT_FOUND` - Flow 不存在
- `FLOW_ALREADY_EXISTS` - Flow ID 已存在（新）
- `FLOW_VALIDATION_FAILED` - Flow 验证失败

### Routine 相关错误代码
- `ROUTINE_NOT_FOUND` - Routine 不存在

---

## 测试建议

建议前端团队更新以下测试场景：

1. **重复 flow_id 测试**：
   - 创建 flow 后，尝试使用相同 flow_id 再次创建
   - 验证返回 409 和 `FLOW_ALREADY_EXISTS` 错误代码

2. **flow_id 优先级测试**：
   - 使用模板 DSL 创建 flow，同时提供不同的 `request.flow_id`
   - 验证创建的 flow_id 是 `request.flow_id` 而不是 DSL 中的 flow_id

3. **404 错误代码测试**：
   - 删除/获取不存在的 flow
   - 验证返回 `FLOW_NOT_FOUND` 错误代码

---

## 向后兼容性

**这些变更不是向后兼容的**。前端代码需要更新以：
1. 处理 409 Conflict 错误（重复 flow_id）
2. 利用新的 flow_id 优先级行为（模板创建）
3. 使用正确的错误代码进行错误处理

---

## 问题反馈

如有任何问题或需要澄清，请联系后端团队。
