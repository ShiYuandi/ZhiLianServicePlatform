# 小智数字人中间件管理平台设计

日期：2026-08-24

## 1. 目标与范围

本项目在 `ZhiLianServicePlatform` 中新建一个面向数字人前端的小智中间件管理平台。平台负责：

- 兼容现有 `XiaozhiDeviceAdd` 的设备添加代理接口。
- 在 MySQL 中维护多张问答表，并通过后台页面增删改查。
- 支持 Excel 导入、导出，以及供多个数字人前端按表名公开下载。
- 在 MySQL 中维护“设备名称 → agentId”映射。
- 提供单管理员登录与密码修改。
- 通过 Docker 加入现有小智 Compose 和 `shared_net` 网络。

MySQL 是问答和设备映射的唯一业务数据源。Excel 仅作为导入、导出和前端下载格式，不作为服务器端持久化源。前端下载后自行完成问题匹配和文字转语音；第一版不提供在线问答查询或语音合成接口。

项目不修改 `XiaozhiDeviceAdd` 目录，也不在第一版中实现多管理员、前端下载鉴权或微服务拆分。

## 2. 总体架构

采用单仓库、模块化单体和单应用镜像：

- 后端：Python、FastAPI、SQLAlchemy 2、Alembic。
- 后台：Vue 3、TypeScript、Vite、Vue Router、Element Plus。
- 数据库：现有 MySQL 8 容器。
- Excel：后端使用 `openpyxl` 在内存中导入和生成 `.xlsx`。
- HTTP 客户端：`httpx` 调用小智设备添加接口。
- 部署：多阶段 Dockerfile 先构建 Vue，再将静态产物交给 FastAPI 同源托管。

生产环境只运行一个中间件容器。后台页面、后台 API、设备代理 API 和 Excel 下载 API 使用同一域名，避免维护独立前端容器及跨域登录链路。

建议目录：

```text
ZhiLianServicePlatform/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  └─ services/
│  ├─ migrations/
│  └─ tests/
├─ frontend/
│  ├─ src/api/
│  ├─ src/components/
│  ├─ src/router/
│  └─ src/views/
├─ docs/
├─ Dockerfile
├─ .env.example
└─ README.md
```

模块边界如下：

- `api` 只处理 HTTP 输入输出、鉴权依赖和状态码。
- `services` 承担设备代理、问答维护、Excel、管理员认证等业务逻辑。
- `models` 和 `schemas` 分别定义数据库实体与接口结构。
- `core` 统一管理配置、安全、日志、异常与应用生命周期。
- Vue 的 `api` 层封装 HTTP 调用，页面不直接拼接请求。

## 3. 数据模型

所有新表使用 `extended_` 前缀，不改动小智服务的既有表。

### 3.1 `extended_admin_users`

- `id`
- `username`，唯一
- `password_hash`
- `session_version`，修改密码时递增，使旧登录失效
- `created_at`
- `updated_at`

系统只允许存在一个管理员。首次启动且表中无管理员时，使用环境变量中的初始账号和密码创建；数据库只保存 Argon2 密码哈希。

### 3.2 `extended_qa_tables`

- `id`
- `name`，唯一，作为前端下载接口中的 `tableName`
- `description`，可空
- `created_at`
- `updated_at`

表名去除前后空格后保存，长度为 1 至 128 个字符，不允许控制字符、路径分隔符或 `..`。

### 3.3 `extended_qa_items`

- `id`
- `table_id`，外键指向 `extended_qa_tables`，删除问答表时级联删除
- `question`
- `answer`
- `question_fingerprint`，规范化问题的 SHA-256
- `sort_order`
- `created_at`
- `updated_at`

问题规范化算法固定为 `question.strip().casefold()`，即忽略前后空格和大小写，但保留内部空格。数据库通过 `(table_id, question_fingerprint)` 唯一约束阻止同一张表内出现等价问题；服务在写入前同时比较规范化文本，避免只依赖哈希。问题和答案均不能为空。问题最长 1,000 字符，答案最长 20,000 字符。

### 3.4 `extended_device_name_mappings`

- `id`
- `name`，唯一
- `agent_id`，32 位十六进制字符串
- `enabled`
- `created_at`
- `updated_at`

现有 `DEVICE_NAME_MAP` 在首次部署时通过显式种子命令导入一次，种子操作可重复执行且不会覆盖管理员后续修改。

## 4. HTTP 接口

### 4.1 公开接口

#### `POST /api/device/add`

保持现有请求兼容：

```json
{
  "name": "设备名称",
  "board": "开发板型号",
  "appVersion": "应用版本",
  "macAddress": "MAC 地址"
}
```

服务从 `extended_device_name_mappings` 查询同名且已启用的映射，补充 `agentId` 后调用小智平台，并将成功响应返回前端。找不到映射返回 400；小智平台的业务错误保留对应 HTTP 状态，但敏感响应内容不直接透传。

POST 不自动重试，避免网络抖动导致重复添加设备。连接和总请求超时默认 10 秒，可由环境变量调整。

#### `GET /api/tables/{tableName}/download`

按表名读取 MySQL 当前数据，生成包含“问题、固定答案”两列表头的 `.xlsx` 并下载。数据按 `sort_order`、`id` 排序。表不存在返回 404。响应文件名由经过安全处理的表名生成，不访问服务器文件路径。

第一版下载接口公开，不要求 API Key。

#### `GET /health`

返回应用和数据库可用状态，供 Docker 健康检查使用，不暴露配置值。

### 4.2 管理员认证接口

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/me`
- `PUT /api/admin/auth/password`

登录成功后使用带签名、有限时长的 `HttpOnly` Cookie。Cookie 设置 `SameSite=Strict`；生产 HTTPS 环境设置 `Secure`。所有管理写接口校验 CSRF Token 和请求来源。修改密码后递增 `session_version`，使已有登录立即失效。

### 4.3 问答管理接口

- `GET /api/admin/qa-tables`
- `POST /api/admin/qa-tables`
- `PUT /api/admin/qa-tables/{id}`
- `DELETE /api/admin/qa-tables/{id}`
- `GET /api/admin/qa-tables/{id}/items`
- `POST /api/admin/qa-tables/{id}/items`
- `PUT /api/admin/qa-items/{id}`
- `DELETE /api/admin/qa-items/{id}`
- `POST /api/admin/qa-tables/{id}/items/batch`
- `POST /api/admin/qa-tables/{id}/import?mode=append|replace`
- `GET /api/admin/qa-tables/{id}/export`

列表接口支持分页和关键词搜索。批量接口返回逐行校验信息。删除整张表与替换导入要求前端二次确认。

Excel 仅接受 `.xlsx`，默认最大 10 MiB、最多 10,000 条问答。第一行必须包含“问题”和“固定答案”两个表头，列顺序固定，额外列拒绝导入。追加模式遇到任何空值或重复问题时整次回滚；替换模式先完整解析和校验，在同一事务内删除旧数据并写入新数据，因此失败时保留旧表。

### 4.4 设备映射管理接口

- `GET /api/admin/device-mappings`
- `POST /api/admin/device-mappings`
- `PUT /api/admin/device-mappings/{id}`
- `DELETE /api/admin/device-mappings/{id}`

支持按名称搜索、增删改及启用/停用。

## 5. 后台页面

采用已确认的左侧导航布局：

- 登录页：管理员账号密码登录。
- 概览：问答表数量、问答条数、设备映射数量、数据库状态和服务状态。
- 问答表管理：搜索、新建、重命名、删除、导入和下载。
- 问答编辑器：分页、搜索、单行增删改、批量粘贴和保存状态提示。
- Excel 导入：明确选择追加或替换；替换前二次确认。
- 设备映射：维护名称、`agentId` 和启用状态。
- 账号设置：修改密码和退出登录。

页面优先适配电脑，并为手机和平板提供可用的响应式布局。敏感平台凭据和数据库密码不在页面展示或修改。

## 6. 配置与环境隔离

配置由 `pydantic-settings` 在启动时读取。仓库只提交 `.env.example`，真实配置不进入 Git 或 Docker 镜像。

主要变量及取值规则：

| 变量 | 取值规则 |
| --- | --- |
| `APP_ENV` | 开发部署固定为 `development`，正式部署固定为 `production`；`test` 仅供自动化测试 |
| `APP_SECRET_KEY` | 每个环境独立生成的至少 32 字节随机值 |
| `LOG_LEVEL` | 默认 `INFO` |
| `CORS_ORIGINS` | 逗号分隔的允许来源 |
| `DB_HOST` | 开发环境使用开发 MySQL 地址，正式环境使用 Compose 别名 |
| `DB_PORT` | 默认 `3306` |
| `DB_NAME` | `xiaozhi_esp32_server` |
| `DB_USER`、`DB_PASSWORD` | 对应环境的数据库账号和密码 |
| `XIAOZHI_API_URL` | 对应环境的小智设备添加接口地址 |
| `XIAOZHI_TOKEN` | 对应环境的小智访问令牌 |
| `XIAOZHI_JSESSIONID` | 对应环境的小智会话标识 |
| `XIAOZHI_TIMEOUT_SECONDS` | 默认 `10` |
| `ADMIN_INITIAL_USERNAME`、`ADMIN_INITIAL_PASSWORD` | 仅在数据库中不存在管理员时用于初始化 |

- 开发环境使用未提交的 `.env.development`，数据库主机指向开发 MySQL。
- 正式环境使用未提交的 `.env.production`，数据库主机为 `xiaozhi-esp32-server-db`。
- 自动化测试使用 `APP_ENV=test`、隔离的临时数据库和虚拟小智凭据，不读取开发环境配置。
- Docker Compose 的 `env_file` 明确选择当前环境文件。
- `XIAOZHI_API_URL`、`XIAOZHI_TOKEN`、`XIAOZHI_JSESSIONID` 按环境分别维护。更新后重启中间件容器生效。
- 启动时校验数据库、小智平台和安全相关必填配置；不满足要求时输出不含密钥的明确错误并停止启动。
- CORS 来源通过 `CORS_ORIGINS` 配置。开发环境可显式设置 `*`；正式环境应列出允许的数字人前端来源。

## 7. 数据流与事务

### 7.1 设备添加

1. 校验四个前端字段。
2. 从 MySQL 查询启用的名称映射。
3. 使用当前环境的小智 URL、Token 和 JSESSIONID 发起请求。
4. 将成功结果或统一错误响应返回前端。

### 7.2 后台编辑与 Excel 下载

1. 管理员通过后台 API 修改数据。
2. 后端在数据库事务中写入并更新排序。
3. 前端请求公开下载接口。
4. 后端在内存中生成 Excel 并流式返回，不在服务器保留业务临时文件。
5. 数字人前端读取 Excel，以去除前后空格并忽略大小写的规则匹配答案，再自行转语音。

### 7.3 Excel 导入

1. 验证文件类型、大小、表头和行数。
2. 在内存中解析全部行。
3. 校验空值、长度、规范化重复及数据库现有重复。
4. 全部通过后在单个事务中追加或替换。
5. 失败时返回文件行号、字段和原因，数据库保持导入前状态。

## 8. 错误处理与日志

API 使用统一错误结构，包含稳定错误码、可读消息和请求编号。典型错误包括：参数错误、未登录、权限失效、问答重复、导入格式错误、表不存在、设备映射不存在、数据库不可用、小智平台超时和小智平台拒绝请求。

日志使用结构化格式，记录请求编号、路径、状态码、耗时、管理员操作类型和失败原因。日志不得记录密码、Token、JSESSIONID、完整 Cookie 或数据库密码。外部平台原始错误只在脱敏后写日志，前端只收到安全摘要。

## 9. 数据持久化、迁移与备份

Alembic 管理所有 `extended_` 表。容器启动命令先执行 `alembic upgrade head`，成功后启动 Uvicorn；迁移失败则不启动 Web 服务。

中间件应用容器不保存业务数据。删除或重建该容器不会影响 MySQL。正式环境复用现有 MySQL 数据卷 `./mysql/data:/var/lib/mysql`，因此应用升级不会丢失数据。

宿主机上的 `./mysql/data` 仍是最终持久化边界。删除该目录、磁盘损坏或错误操作仍可能丢失数据。README 必须提供基于 `mysqldump` 的备份命令和恢复步骤，并建议在迁移或版本升级前备份 `extended_` 表。

## 10. Docker 部署

应用服务加入小智 Compose 的 `shared_net`：

```yaml
zhilian-service-platform:
  build:
    context: ./ZhiLianServicePlatform
  container_name: zhilian-service-platform
  restart: always
  env_file:
    - ./ZhiLianServicePlatform/.env.production
  ports:
    - "35081:8000"
  networks:
    shared_net:
      aliases:
        - zhilian-service-platform
```

生产数据库通过 `xiaozhi-esp32-server-db:3306` 访问。开发环境只替换 `.env.development` 中的数据库主机和凭据，不修改代码；自动化测试不连接开发数据库。

首次部署和后续升级均执行：

```bash
docker compose up -d --build zhilian-service-platform
```

## 11. 验证策略

### 后端单元测试

- 问题规范化和指纹。
- 表名与 `agentId` 校验。
- 密码哈希、登录 Cookie、CSRF 和会话失效。
- Excel 表头、空值、重复、追加与替换规则。
- 小智平台响应和超时映射。

### 接口与数据库集成测试

- 管理员首次初始化、登录、退出和修改密码。
- 问答表及问答项完整 CRUD。
- Excel 导入失败回滚和成功导出。
- 设备映射增删改、停用和设备添加代理。
- 并发编辑时唯一约束和事务行为。

### 前端测试

- 登录保护和过期会话处理。
- 表格分页、搜索、编辑与批量粘贴。
- 导入模式选择、校验错误展示和危险操作确认。
- 设备映射编辑和响应式布局。

### 发布验证

- 在测试 MySQL 上执行完整迁移。
- 生成实际 Excel，核对表头、中文内容、顺序和行数。
- 验证 Docker 健康检查与数据库断连表现。
- 对现有 `POST /api/device/add` 请求做兼容性回归。
- 确认镜像、日志、页面和接口响应中均无真实密钥。
