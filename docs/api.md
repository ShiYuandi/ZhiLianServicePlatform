# API 摘要

错误响应统一包含：

```json
{"code":"ERROR_CODE","message":"可读错误信息","requestId":"请求编号"}
```

## 公开接口

### `POST /api/device/add`

```json
{
  "name": "示例设备-A",
  "board": "esp32",
  "appVersion": "1.0.0",
  "macAddress": "00:11:22:33:44:55"
}
```

服务从 MySQL 查找启用的数字人项目设备映射，补充 `agentId` 后调用当前环境的小智平台；设备名称忽略前后空格并按不区分大小写匹配。

### `GET /api/xiaozhi-services`

获取所有已发布的小智中间件服务名称。响应只包含 `serviceNames`，不会暴露内部 `serviceCode`。

### `GET /api/xiaozhi-services/config?serviceName=...`

按服务名称读取已发布配置，返回前端显示名称、可选的数字人名称、推荐问题、页面文字、语音唤醒参数、`agentId`、八张可选图片地址，以及可选的站立、思考、说话视频地址。
服务名称忽略首尾空格和大小写匹配；草稿、已停止发布或名称不唯一的服务不会正常返回。
响应不会包含内部 `serviceCode`。

媒体字段均允许为 `null`：

```json
{
  "digitalHumanName": "示例展馆数字人",
  "backgroundIconUrl": null,
  "wakeIconUrl": null,
  "menuBackgroundUrl": null,
  "keyboardIconUrl": null,
  "voiceIconUrl": null,
  "homeIconUrl": null,
  "holdToTalkBackgroundUrl": null,
  "sendIconUrl": null,
  "standingVideoUrl": null,
  "thinkingVideoUrl": null,
  "speakingVideoUrl": null
}
```

### `GET /api/xiaozhi-service-assets/{assetId}`

通过中间件代理读取 MinIO 中的服务图片或视频。前端不需要直接持有 MinIO 凭据。

### `GET /api/tables/{tableName}/download`

公开下载指定问答表。响应为 `.xlsx`，两列表头固定为“问题、固定答案”。

### `/api/external-proxies/{proxyUuid}`

外部接口原样转发。后台配置上游完整网址并自动生成 `proxyUuid` 后，前端访问此地址即可；平台会透传请求方法、Query 参数、请求体和业务 Header，并原样返回上游状态码、响应头和响应内容。代理 UUID 不需要登录，但应仅提供给可信前端使用。

### `POST /v1/chat/completions`

这是给小智服务调用的 OpenAI 兼容接口。请求头使用服务端配置的代理密钥：

```text
Authorization: Bearer <LLM_PROXY_API_KEY>
```

请求中的 `model` 必须是已发布的小智中间件服务编码（`serviceCode`），仅供小智平台内部使用，前端不需要获取。`messages` 使用标准 OpenAI 消息数组。系统会取最后一条 `user` 消息；如果服务绑定了问答表，则按“忽略前后空格和大小写”的精确规则查询，命中时直接返回固定答案，未命中再调用该服务在后台配置的外部模型。问答表为可选配置，未绑定时直接调用外部模型。`stream=true` 返回 SSE，`stream=false` 返回标准 JSON。小智服务继续负责文字转语音，中间件不保存对话正文。

每个数字人项目在后台“项目编辑 → 大语言模型”中选择供应器并维护配置：

- `OpenAI接口`：基础 URL、模型名称和 API 密钥。
- `Dify接口`：Dify 基础 URL、API 密钥和 `chat-messages`（对话）或 `workflows/run`（工作流）模式。

API 密钥写入 MySQL 前会使用 `MODEL_CREDENTIAL_ENCRYPTION_KEY` 加密，详情接口只返回脱敏值；修改时重新输入，留空表示保持原密钥。新增或修改配置会立即保存到 MySQL，不需要重启服务。

## 后台接口

- `/api/admin/auth/*`：登录、退出、当前管理员、修改密码。
- `/api/admin/qa-tables`：问答表 CRUD。
- `/api/admin/qa-tables/{id}/items`：问答项列表和新增。
- `/api/admin/qa-items/{id}`：问答项修改和删除。
- `/api/admin/qa-tables/{id}/items/batch`：批量添加。
- `/api/admin/qa-tables/{id}/import?mode=append|replace`：Excel 导入。
- `/api/admin/qa-tables/{id}/export`：后台导出。
- `/api/admin/xiaozhi-services`：小智中间件服务列表、新建、编辑、删除、发布和停止发布。
- `/api/admin/xiaozhi-services/{id}/assets/{slot}`：服务图片或视频上传、替换和删除。
- `/api/admin/external-api-proxies`：外部接口代理网址和启用状态维护；UUID 由系统自动生成。
- `/api/admin/dashboard`：概览计数。

后台写接口要求登录 Cookie 和 `X-CSRF-Token`。完整请求结构与在线调试可查看 `/docs`。
