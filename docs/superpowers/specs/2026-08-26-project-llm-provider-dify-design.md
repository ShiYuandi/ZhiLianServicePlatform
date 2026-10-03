# 数字人项目级 OpenAI / Dify 大模型供应器设计

## 目标

为每个数字人项目提供可在后台维护的外部大模型供应器，支持 OpenAI 兼容接口和 Dify。小智服务继续只对接扩展服务的 OpenAI 兼容代理，不需要修改小智源码或为每个项目重启扩展服务。

## 现状与范围

现有项目已经保存 `llm_base_url`、`llm_model` 和加密的 `llm_api_key`，`POST /v1/chat/completions` 会先匹配项目问答表，未命中后调用项目配置的 OpenAI 兼容模型。本次在此基础上增加供应器选择和 Dify 适配，不改变公开代理协议、固定问答优先级和密钥加密方式。

## 方案

### 项目配置

新增项目字段：

- `llm_provider`：`openai` 或 `dify`，默认 `openai`，兼容已有项目。
- `llm_mode`：Dify 模式为 `chat-messages` 或 `workflows/run`；OpenAI 忽略该字段。

现有字段继续复用：

- `llm_base_url`：OpenAI 填兼容服务的 `/v1` 根地址；Dify 填 Dify API 根地址，通常为 `/v1`。
- `llm_model`：OpenAI 的模型名；Dify 可为空，保留用于兼容不同部署或将来扩展。
- `llm_api_key_encrypted`：供应器 API Key，继续使用 `APP_SECRET_KEY` 加密，接口只返回脱敏值。

后台编辑页显示“供应器”下拉框：

- OpenAI：基础 URL、模型名称、API 密钥。
- Dify：基础 URL、API 密钥、对话模式（对话 / 工作流）。

创建和更新时按供应器校验必填项；已配置密钥留空表示保持原密钥。项目发布要求问答表、设备映射、图片和对应供应器配置完整。

## 请求流程

```text
小智 → POST /v1/chat/completions(model=projectCode)
     → 认证和项目发布/设备校验
     → 问答表精确匹配（忽略前后空格和大小写）
        ├─ 命中：返回 OpenAI JSON 或 SSE 固定答案
        └─ 未命中：按 llmProvider 调用外部供应器
             ├─ openai：POST {base_url}/chat/completions
             └─ dify：POST {base_url}/chat-messages 或 /workflows/run
     → 统一转换为 OpenAI Chat Completion 响应
小智 → TTS 转语音
```

固定问答命中时不调用 Dify，也不调用 OpenAI。

## Dify 适配

### 对话模式

请求 Dify `POST /v1/chat-messages`，使用 `Authorization: Bearer <API Key>`，`response_mode` 根据代理请求选择 `blocking` 或 `streaming`，`query` 使用最后一条用户消息，`user` 使用稳定但不包含敏感信息的项目编码。`answer` 映射为 OpenAI assistant message；流式响应解析 Dify `message` 事件的 `answer` 字段并输出 OpenAI SSE chunk。

### 工作流模式

请求 Dify `POST /v1/workflows/run`，使用 `inputs` 中的 `query` 传入最后一条用户消息，`response_mode` 为 `blocking` 或 `streaming`，`user` 使用项目编码。阻塞响应从 `data.outputs.answer`（不存在时兼容第一个字符串输出）读取文本；流式响应解析工作流节点/结束事件中的 answer 或输出文本，转换成 OpenAI SSE chunk。

Dify 会话 ID 不由中间件持久化，默认每次请求创建独立会话，避免不同设备和项目串话。Dify 错误、超时或返回无法解析时沿用现有中文兜底文本，并记录不含 API Key 和完整用户问题的结构化日志。

## 错误处理

- 未知供应器或模式：422，返回中文参数错误。
- 项目供应器配置不完整：409 `LLM_NOT_CONFIGURED`。
- 外部供应器 HTTP 错误、超时、格式错误：非流式返回统一兜底 JSON；流式返回一段兜底文本后结束 SSE。
- 代理鉴权、项目发布、设备停用和问答匹配规则保持不变。

## 数据迁移与兼容

新增 Alembic 迁移，为 `extended_digital_human_projects` 增加 `llm_provider` 和 `llm_mode`，已有项目回填 `openai` 和空模式。迁移可重复执行且不覆盖现有密钥。回滚删除新增列，不删除项目数据。

## 测试

- 后端：供应器默认值和校验、OpenAI 请求、Dify 对话阻塞/流式、Dify 工作流阻塞/流式、固定问答短路、异常兜底、密钥不明文返回。
- 前端：供应器切换显示字段、Dify 模式提交、已配置密钥留空保持、发布缺少配置提示。
- 集成：使用 Mock HTTP 服务验证请求路径、认证头、`model/query/inputs` 映射和 SSE 输出。
- 现有全部测试必须继续通过。

## 非目标

- 不修改小智服务源码和智控台供应器实现。
- 不在扩展服务保存 Dify 会话历史。
- 不在本次增加新的外部供应器或把问答表重新开放给数字人前端。
