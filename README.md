# 智联服务台

智联服务台是面向数字人应用的统一 AI 服务管理平台，提供：

- 兼容原有 `POST /api/device/add` 的设备添加代理。
- MySQL 持久化的多问答表管理。
- Excel 追加/替换导入及公开下载。
- 小智中间件服务配置后台维护（设备 `agentId`、发布状态、可选图片和视频）。
- 单管理员登录、修改密码和左侧导航管理页面。
- 前端 AI 服务：服务级 API Key、异步语音识别和文生图/图生图任务，任务与结果状态持久化到 MySQL。

## 环境说明

- `development`：开发部署，使用 `.env.development`。该文件已被 Git 忽略。
- `production`：正式部署，服务器单独创建 `.env.production`。
- `test`：只供自动化测试，使用隔离数据库和虚拟凭据。

仓库只提交 `.env.example`，不会提交实际数据库密码、小智 Token 或 JSESSIONID。

## 本地启动

后端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:ENV_FILE = (Resolve-Path .env.development).Path
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m app.cli.seed_device_mappings
\.\.venv\Scripts\python.exe -m app.cli.seed_ai_models
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Worker 需要单独启动（不要在 API 进程中使用进程内后台任务）：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:ENV_FILE = (Resolve-Path .env.development).Path
.\.venv\Scripts\python.exe -m app.worker.main
```

前端另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173/admin/`。首次登录使用当前环境文件中的 `ADMIN_INITIAL_USERNAME` 和 `ADMIN_INITIAL_PASSWORD`；登录后立即修改密码。

开发环境需要让内网其他设备访问时，前端开发服务器会监听所有网卡。请在运行开发机上查看内网 IP，其他设备访问
`http://<开发机内网IP>:5173/admin/`（例如 `http://192.168.1.100:5173/admin/`）。如果无法访问，请在
Windows 防火墙中放行 TCP 端口 `5173`；后端 `8000` 由 Vite 代理，一般不需要对内网开放。

## 测试

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m pytest -c backend\pytest.ini backend\tests -q
npm --prefix frontend run test -- --run
npm --prefix frontend run build
```

## Docker 部署

正式部署前在本地编译前端并构建正式 Docker 镜像，再将 `release` 目录和镜像 tar 上传到服务器。服务器只执行 `docker load` 和启动，不需要 Node/npm，也不会重新下载 Python 依赖。具体步骤见 [本地构建与部署文档](docs/release-build-and-deploy.md)。

本地编译前端：

```powershell
npm --prefix frontend install
npm --prefix frontend run build
Copy-Item -Recurse -Force frontend\dist release\frontend\dist
```

将 `release` 目录和导出的 `zhilian-service-platform-release.tar` 上传到正式服务器后执行：

```bash
docker load -i zhilian-service-platform-release.tar
docker compose up -d --force-recreate --no-build
```

容器启动时自动执行 Alembic 数据库迁移。应用容器不保存业务数据；业务数据位于现有 MySQL 数据卷。

首次部署后导入现有设备映射：

```bash
docker compose exec zhilian-service-platform python -m app.cli.seed_device_mappings
```

该命令可重复运行，只补充缺失映射，不覆盖后台已修改的数据。

导入 Unity 参考项目对应的 AI 模型模板（不包含任何密钥）：

```bash
docker compose exec zhilian-service-platform python -m app.cli.seed_ai_models
```

该命令会创建百度短语音识别、火山豆包 ASR v2 和火山 Seedream 4.0 三条模板；
请登录后台，在“AI 能力管理”中补充各供应器凭据后再绑定前端 AI 服务。

## 主要地址

- 管理后台：`/admin/`
- 健康检查：`GET /health`
- 设备添加：`POST /api/device/add`
- Excel 下载：`GET /api/tables/{tableName}/download`
- OpenAPI：`/docs`

前端 AI 服务公开接口（请求头使用 `Authorization: Bearer <服务 API Key>`）：

- `GET /api/v1/ai-services/{serviceCode}`：读取服务能力。
- `POST /api/v1/ai-services/{serviceCode}/speech-tasks`：multipart 上传音频，异步返回任务编号。
- `POST /api/v1/ai-services/{serviceCode}/image-tasks`：multipart 提交提示词及可选单张参考图，异步返回任务编号。
- `GET /api/v1/ai-services/{serviceCode}/tasks/{taskId}`：查询任务状态；成功后返回识别文字或图片临时地址。
- `GET /api/v1/ai-services/{serviceCode}/image-results/{taskId}?token=...`：下载图片结果。
  该地址自带平台签名令牌，**不需要** Bearer 头，可直接用于二维码、浏览器直开等无法附加请求头的场景；
  令牌有效期默认 10 分钟（`AI_RESULT_DOWNLOAD_TTL_SECONDS` 可调），过期后重新查询任务获取新地址。

前端 AI 服务的 `serviceCode` 在后台创建时由系统自动生成（格式为 `svc-` 加随机标识），创建成功后请与只展示一次的服务 API Key 一起安全保存。

## Unity 模型接入

执行 `app.cli.seed_ai_models` 后，后台会出现 Unity 参考项目对应的三条模型模板：

- `百度短语音识别（Unity）`：对应 `BaiduSpeechService`，固定使用 16kHz、16bit、单声道 PCM。
- `火山豆包 ASR v2`：对应小智平台的豆包非流式 ASR 协议。
- `火山 Seedream 4.0（Unity）`：对应 `VolcImageService`，模型 ID 为
  `doubao-seedream-4-0-250828`，同一配置同时支持文生图和单图图生图。

模板只写入供应器地址、协议默认值和模型 ID，不包含任何 API Key。管理员需要在后台
“AI 能力管理”中填写凭据，点击“测试连接”确认后，再绑定到前端 AI 服务。

如果需要导入 Unity `SampleScene.unity` 中已配置的百度和 Seedream 凭据，可执行：

```powershell
$env:PYTHONPATH=(Resolve-Path backend).Path
$env:ENV_FILE=(Resolve-Path .env.development).Path
.\.venv\Scripts\python.exe -m app.cli.import_unity_credentials `
  "C:\\Users\\Administrator\\unityProject\\ScanToPaintStyleTransferInteraction\\Assets\\Scenes\\SampleScene.unity"
```

命令只导入 Unity 场景中对应组件的密钥并加密写入数据库，不会在终端输出密钥；
火山 ASR 的 AppID、Access Token 仍需从火山控制台或小智实际部署配置中填写。

小智中间件服务公开配置：先调用 `GET /api/xiaozhi-services` 获取已发布的 `serviceName` 列表，
再调用 `GET /api/xiaozhi-services/config?serviceName=...` 获取 `agentId`、页面配置以及可选图片、视频地址。
公开响应不会包含内部 `serviceCode`；媒体由中间件代理读取 MinIO。八张图片和站立、思考、说话三个视频均可为空，不影响服务发布。

完整接口见 [API 文档](docs/api.md)，数据保护见 [备份与恢复](docs/backup-restore.md)。
