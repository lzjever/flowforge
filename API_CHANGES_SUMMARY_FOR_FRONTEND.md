# Flow API 变更简要说明 - 前端团队

## 变更概述

Flow API 已修复设计缺陷，现在与 Workers/Jobs API 保持一致。**这些变更不是向后兼容的**，需要前端代码更新。

## 主要变更

### 1. 重复 flow_id 现在返回 409 Conflict

**变更前**：`POST /api/v1/flows` 使用已存在的 `flow_id` 时返回 `201 Created`（静默覆盖）

**变更后**：返回 `409 Conflict`，错误代码 `FLOW_ALREADY_EXISTS`

**需要更新**：前端需要处理 409 错误，显示"flow_id 已存在"提示

**示例**：
```typescript
try {
  await api.flows.create({ flow_id: "my_flow" });
} catch (error) {
  if (error.status === 409 && error.body?.error?.code === "FLOW_ALREADY_EXISTS") {
    showError("Flow ID already exists");
  }
}
```

---

### 2. request.flow_id 现在优先于 DSL 中的 flow_id

**变更前**：DSL 中的 `flow_id` 会覆盖 `request.flow_id`

**变更后**：`request.flow_id` **优先于** DSL 中的 `flow_id`

**影响**：基于模板创建新 flow 的功能现在可以正常工作

**示例**：
```typescript
// 从模板创建新 flow
const templateDsl = await api.flows.exportDSL("template_flow", "yaml");
const newFlow = await api.flows.create({
  flow_id: "my_new_flow",  // 这个会覆盖 DSL 中的 flow_id
  dsl: templateDsl.dsl
});
// 创建的 flow_id 是 "my_new_flow"，而不是 "template_flow"
```

---

### 3. 404 错误现在返回正确的错误代码

**变更前**：所有 404 错误返回 `INTERNAL_ERROR` 错误代码

**变更后**：返回正确的资源特定错误代码：
- `FLOW_NOT_FOUND` - Flow 不存在
- `ROUTINE_NOT_FOUND` - Routine 不存在

**需要更新**：前端可以使用错误代码进行更精确的错误处理

**示例**：
```typescript
try {
  await api.flows.delete("my_flow");
} catch (error) {
  if (error.status === 404) {
    const errorCode = error.body?.error?.code;
    if (errorCode === "FLOW_NOT_FOUND") {
      showError("Flow not found");
    }
  }
}
```

---

## 受影响的端点

- `POST /api/v1/flows` - 添加重复检查，flow_id 优先级修复
- `DELETE /api/v1/flows/{flow_id}` - 404 错误代码修复
- `GET /api/v1/flows/{flow_id}` - 404 错误代码修复
- `GET /api/v1/flows/{flow_id}/dsl` - 404 错误代码修复
- 其他所有返回 404 的 Flow 相关端点

---

## 测试状态

✅ 所有修复已通过测试验证
✅ 152 个用户故事测试通过
✅ 新增 6 个测试用例验证修复

---

## 详细文档

完整变更说明请参考：`API_CHANGES_FOR_FRONTEND.md`
