# 数字人项目配置模块设计

## 目标与范围

在现有小智数字人中间件中新增“数字人项目”模块。管理员按项目维护前端界面、语音唤醒、智能体和图片配置；数字人前端按稳定项目编码公开读取配置。项目配置保存在 MySQL，图片保存在正式服务器的 MinIO 数据卷，应用容器删除或重建不会导致业务数据丢失。

现有设备映射后台合并进项目模块，公开的 `POST /api/device/add` 兼容接口保持不变。本次不改造问答表，也不实现“固定答案命中，否则调用百度大模型”的后续问答代理模块；该模块以后单独设计。

## 数据模型

### 数字人项目

新增 `extended_digital_human_projects`：

| 字段 | 类型与约束 | 用途 |
| --- | --- | --- |
| `id` | 自增整数主键 | 内部项目编号 |
| `project_code` | `VARCHAR(64)`，唯一、不可修改 | 前端请求使用的稳定项目标识，只允许 2–64 位小写字母、数字和短横线 |
| `project_name` | `VARCHAR(128)`，必填 | 前端显示名称及后台项目名称 |
| `title` | `VARCHAR(255)`，必填 | 数字人页面标题 |
| `subtitle` | `VARCHAR(255)`，可空 | 数字人页面副标题 |
| `questions` | JSON，默认空数组 | 首页推荐问题字符串数组 |
| `voice_wakeup_enabled` | 布尔值，默认关闭 | 是否启用语音唤醒 |
| `wake_word` | `VARCHAR(255)`，可空 | 唤醒词 |
| `wake_listening_texts` | JSON，默认空数组 | 唤醒词监听文字字符串数组 |
| `wake_requirement_count` | 非负整数，默认 0 | 仅透传给前端，不在本服务解释业务含义 |
| `published` | 布尔值，默认关闭 | 是否允许前端公开读取配置 |
| `created_at`、`updated_at` | UTC 时间 | 审计时间 |

两个数组保留输入顺序，对每项执行外部空白清理，拒绝空字符串；不擅自解释或关联现有问答表。

### 设备映射整合

现有 `extended_device_name_mappings` 增加可迁移后设为非空的唯一 `project_id` 外键，指向数字人项目并启用数据库级联删除。一个项目只能拥有一条设备映射，一条映射只能属于一个项目。

- 公开配置的 `agentName` 实时取设备映射的 `name`。
- 公开配置的 `agentId` 实时取设备映射的 `agent_id`。
- 项目编辑器直接维护设备名称、32 位十六进制 `agentId` 和设备映射启用状态。
- 独立设备映射后台页面与 `/api/admin/device-mappings` 管理接口移除。
- `POST /api/device/add` 继续直接查询设备映射表，路径和请求结构不变。

迁移现有数据时，为每条设备映射创建未发布的草稿项目：项目编码为 `legacy-{mapping_id}`，项目名称和标题暂用原设备名称，映射启用状态保持不变。管理员之后补齐配置并发布，不影响迁移前已经可用的设备添加代理。

### 项目图片资产

新增 `extended_project_assets`：

| 字段 | 用途 |
| --- | --- |
| `id` | 图片资产编号 |
| `project_id` | 所属项目，项目删除时级联删除记录 |
| `slot` | 固定图片位置 |
| `object_key` | MinIO 对象路径，唯一且不暴露给前端 |
| `original_filename` | 原始文件名，仅供后台显示 |
| `content_type` | 已验证的 MIME 类型 |
| `size_bytes` | 文件大小 |
| `etag` | MinIO 对象版本标识 |
| `created_at`、`updated_at` | 审计时间 |

`project_id + slot` 唯一。固定图片位置和公开字段映射如下：

| `slot` | 公开 JSON 字段 |
| --- | --- |
| `background_icon` | `backgroundIconUrl` |
| `wake_icon` | `wakeIconUrl` |
| `menu_background` | `menuBackgroundUrl` |
| `keyboard_icon` | `keyboardIconUrl` |
| `voice_icon` | `voiceIconUrl` |
| `home_icon` | `homeIconUrl` |
| `hold_to_talk_background` | `holdToTalkBackgroundUrl` |
| `send_icon` | `sendIconUrl` |

## MinIO 存储边界

管理员不直接接触 MinIO。后台把文件上传给中间件，中间件完成登录、CSRF、格式、真实文件内容和大小校验后写入 MinIO。仅允许 PNG、JPEG、WebP，单张最大 10 MiB，不允许 SVG。

MinIO Endpoint、Access Key、Secret Key、Bucket 和 Secure 开关全部来自环境变量，不进入 Git，也不返回浏览器。服务器访问地址通过 `MINIO_ENDPOINT` 配置；若使用 Compose 端口映射，可将宿主机端口映射到容器 MinIO API `9000`，不依赖 Compose 网络别名；开发环境连接同一 MinIO 服务但使用独立的 `xiaozhi-project-assets-development` Bucket，正式环境使用 `xiaozhi-project-assets` Bucket；自动化测试使用内存模拟，不访问真实 MinIO。

Bucket 保持私有。数字人前端只访问中间件的图片代理接口。数据库保存对象路径而非 MinIO URL，因此 MinIO 地址变化不需要修改历史项目。替换图片先上传新对象，数据库更新成功后再删除旧对象；清理失败只记录不含凭据的日志，不回滚已经成功的配置。项目删除后清理项目图片对象。

## 后台 API

所有后台读取接口要求管理员会话，所有写接口额外要求 `X-CSRF-Token`：

- `GET /api/admin/projects`：分页、关键词和发布状态查询。
- `POST /api/admin/projects`：在同一数据库事务中创建项目与设备映射。
- `GET /api/admin/projects/{project_id}`：读取完整后台配置和图片元数据。
- `PUT /api/admin/projects/{project_id}`：同时修改项目配置与设备映射；项目编码不可修改。
- `DELETE /api/admin/projects/{project_id}`：删除项目、映射和资产记录，并清理 MinIO 对象。
- `POST /api/admin/projects/{project_id}/assets/{slot}`：上传或替换指定图片。
- `DELETE /api/admin/projects/{project_id}/assets/{slot}`：删除指定图片。
- `POST /api/admin/projects/{project_id}/publish`：完整性校验通过后发布。
- `POST /api/admin/projects/{project_id}/unpublish`：停止公开读取。

重复项目编码、项目名称或设备名称返回 409；项目或图片不存在返回 404；无效图片返回 415，文件过大返回 413；MinIO 不可用返回中文 503。错误响应继续使用 `code`、`message`、`requestId`，不得包含对象存储地址或凭据。

## 公开 API

无需登录：

- `GET /api/projects/{project_code}/config`
- `GET /api/project-assets/{asset_id}?v={etag}`

项目不存在或未发布时统一返回 404，避免公开草稿状态。公开配置使用 camelCase：

```json
{
  "projectCode": "museum-a",
  "projectName": "示例展馆数字人",
  "title": "欢迎来到示例展馆",
  "subtitle": "请向数字人提问",
  "questions": ["这里的开放时间是什么？"],
  "backgroundIconUrl": "https://middleware.example/api/project-assets/1?v=etag",
  "wakeIconUrl": "https://middleware.example/api/project-assets/2?v=etag",
  "menuBackgroundUrl": "https://middleware.example/api/project-assets/3?v=etag",
  "keyboardIconUrl": "https://middleware.example/api/project-assets/4?v=etag",
  "voiceIconUrl": "https://middleware.example/api/project-assets/5?v=etag",
  "homeIconUrl": "https://middleware.example/api/project-assets/6?v=etag",
  "holdToTalkBackgroundUrl": "https://middleware.example/api/project-assets/7?v=etag",
  "sendIconUrl": "https://middleware.example/api/project-assets/8?v=etag",
  "voiceWakeupEnabled": true,
  "wakeWord": "你好小智",
  "wakeListeningTexts": ["你好小智"],
  "wakeRequirementCount": 1,
  "agentId": "0123456789abcdef0123456789abcdef",
  "agentName": "示例展馆设备"
}
```

图片 URL 根据当前请求的对外域名生成，不写入数据库。图片代理设置正确的 `Content-Type`、ETag 和长期缓存头；URL 的 `v` 参数随 ETag 变化，避免替换后命中旧缓存。若对象不存在或 MinIO 暂时不可用，返回统一中文错误。

## 发布规则

项目创建后默认为草稿。草稿允许图片和可选文字暂时为空。发布时必须满足：

1. 项目编码、项目名称、标题完整。
2. 设备名称和合法的 32 位十六进制 `agentId` 完整，设备映射已启用。
3. 八个固定图片位置均已上传。
4. `wake_requirement_count` 为非负整数。
5. 启用语音唤醒时，唤醒词和监听文字数组均不为空。

已发布项目不允许保存会令配置变得不完整的修改，管理员必须先停止发布。删除单张图片同样要求先停止发布。

## 后台页面

左侧导航新增“数字人项目”，移除“设备映射”。项目列表显示项目名称、项目编码、设备名称、`agentId`、设备映射状态、发布状态和配置完整度，并提供编辑、发布/停止发布、删除操作。

项目编辑使用独立页面，分为基础信息、推荐问题、设备与智能体、语音唤醒、八类图片、发布状态六个区域。数组字段使用可增删和排序的多行输入；图片区域显示预览、上传、替换、删除和上传状态。普通字段保存与图片上传分离，避免保存文字时重复传输图片。

删除项目必须二次确认，并明确提示会同时删除设备映射和图片。

## 配置与部署

新增环境变量：

- `MINIO_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET`
- `MINIO_SECURE`

生产示例只使用占位符。生产配置校验拒绝空凭据和示例占位值。部署文档说明 development/production Bucket 隔离、MinIO 数据卷备份和项目图片恢复流程。

## 测试与验收

- Alembic 从 `0001` 升级、降级、再次升级，并验证历史设备映射生成草稿项目。
- 测试项目、设备映射一对一约束、事务创建、修改、级联删除和唯一冲突。
- 测试数组清理、发布完整性、语音唤醒条件和已发布配置保护。
- 使用模拟对象存储测试图片格式、内容识别、大小、替换、删除、ETag、缓存和故障处理。
- 测试公开配置字段、绝对图片 URL、草稿 404 以及设备添加代理兼容性。
- 更新中文 Swagger 契约测试。
- 测试后台项目列表、编辑器、数组交互、图片交互和发布流程。
- 运行完整后端测试、Ruff、前端 Vitest、生产构建和依赖审计。
- 使用浏览器检查桌面和手机宽度下的项目列表与编辑页，并验证控制台无错误。
