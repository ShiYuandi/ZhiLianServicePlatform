# 本地构建镜像、同步 release 与正式部署

本文说明如何在开发机编译前端并构建 Docker 镜像，将构建结果同步到 `release` 目录，再上传到正式服务器部署。

正式服务器只加载本地构建好的镜像并启动，不执行 Dockerfile、npm 或 pip 构建，也不会因网络问题下载 Python 依赖。

## 一、构建前检查

在开发机 PowerShell 中执行：

```powershell
Set-Location "C:\Users\Administrator\Desktop\dmx\ZhiLianServicePlatform"
```

确认当前代码、数据库迁移和配置模板是最新版本。正式环境密钥只写入服务器上的 `release/.env`，不要写入项目目录或提交到 Git。

## 二、本地编译前端

首次构建或依赖发生变化时安装依赖：

```powershell
npm --prefix frontend install
```

编译前端：

```powershell
npm --prefix frontend run build
```

编译成功后应存在：

```text
frontend\dist\index.html
```

如果构建失败，不要继续同步或上传，先修复构建错误。

## 三、同步构建结果到 release

执行以下命令，将前端编译结果复制到上传目录：

```powershell
$root = "C:\Users\Administrator\Desktop\dmx\ZhiLianServicePlatform"
$source = Join-Path $root "frontend\dist\*"
$target = Join-Path $root "release\frontend\dist"

New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -Path $source -Destination $target -Recurse -Force
```

检查同步结果：

```powershell
Test-Path ".\release\frontend\dist\index.html"
Get-ChildItem ".\release\frontend\dist" -Recurse -File | Measure-Object
```

第一个命令必须返回 `True`。

如果本次修改了后端代码、数据库迁移或 Docker 配置，除了前端 `dist` 外还要同步对应文件。可在项目根目录执行：

```powershell
$root = "C:\Users\Administrator\Desktop\dmx\ZhiLianServicePlatform"
robocopy "$root\backend" "$root\release\backend" /E `
  /XD tests __pycache__ .pytest_cache `
  /XF requirements-dev.txt *.pyc
if ($LASTEXITCODE -gt 7) { throw "backend 同步失败，robocopy exit code=$LASTEXITCODE" }

Copy-Item "$root\Dockerfile", "$root\.dockerignore" `
  -Destination "$root\release" -Force
```

没有后端改动时，只需重新构建并同步 `frontend/dist`。

## 四、检查 release 目录

正式上传目录为：

```text
C:\Users\Administrator\Desktop\dmx\ZhiLianServicePlatform\release
```

目录至少需要包含：

```text
release/
├─ Dockerfile
├─ .dockerignore
├─ .env
├─ docker-compose.yml
├─ backend/
│  ├─ app/
│  ├─ migrations/
│  ├─ alembic.ini
│  ├─ entrypoint.py
│  └─ requirements.txt
└─ frontend/
   └─ dist/
```

`release` 不包含部署文档、前端源码、Node.js 依赖、测试依赖、Python 缓存或业务数据；这些内容不会参与正式镜像运行。

上传前确认没有开发环境配置或本地数据库：

```powershell
Get-ChildItem ".\release" -Recurse -Force `
  | Where-Object {
      $_.Name -in @(".env.development", ".env.production", "node_modules", ".venv") `
      -or $_.Extension -in @(".db", ".sqlite", ".sqlite3")
    }
```

该命令不应返回开发环境配置、数据库文件或依赖目录；正式 `release/.env` 是唯一需要上传的环境文件。

## 五、本地构建正式镜像并导出

在开发机安装并启动 Docker Desktop（使用 Linux 容器），执行：

```powershell
Set-Location "C:\Users\Administrator\Desktop\dmx\ZhiLianServicePlatform"

# release/Dockerfile 会复制 release/frontend/dist 和 release/backend
# Docker Hub 不通时先用国内镜像拉取基础镜像并在本地改名
docker pull docker.m.daocloud.io/library/python:3.12-slim
docker tag docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim

docker build --platform linux/amd64 `
  --build-arg DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn `
  -t zhilian-service-platform:release .\release

# 导出镜像，上传到服务器后用 docker load 导入
docker save zhilian-service-platform:release `
  -o .\zhilian-service-platform-release.tar
```

基础镜像和 Debian 软件源使用国内镜像，避免 Docker Hub 鉴权或 Debian 官方源超时。导出的 tar 可能较大，必须与 `release` 目录一起上传。

## 六、上传到正式服务器

上传整个 `release` 目录和 `zhilian-service-platform-release.tar`。不要上传开发环境的 `.env.development`。

例如使用文件传输工具上传到：

```text
/opt/zhilian-service-platform/
```

上传后服务器目录应额外包含：

```text
/opt/zhilian-service-platform/zhilian-service-platform-release.tar
```

上传后服务器目录结构应类似：

```text
/opt/zhilian-service-platform/
├─ Dockerfile
├─ .dockerignore
├─ .env
├─ docker-compose.yml
├─ backend/
└─ frontend/dist/
```

## 七、填写正式环境配置

上传后编辑服务器上的 `.env`：

```bash
cd /opt/zhilian-service-platform
vi .env
```

将其中所有 `CHANGE_ME` 和示例地址替换为正式值，至少确认：

```text
APP_ENV=production
DB_HOST=正式 MySQL 地址
DB_PORT=3306
DB_NAME=digital_human_service_platform
DB_USER=数据库用户名
DB_PASSWORD=数据库密码
MINIO_ENDPOINT=MinIO 地址
MINIO_ACCESS_KEY=MinIO 用户名
MINIO_SECRET_KEY=MinIO 密码
MINIO_BUCKET=正式环境 Bucket
XIAOZHI_API_URL=小智设备添加接口地址
XIAOZHI_TOKEN=正式环境 Token
XIAOZHI_JSESSIONID=正式环境会话标识
LLM_PROXY_API_KEY=提供给小智调用的代理密钥
```

如果正式后台暂时通过 `http://IP:35081` 访问，必须设置 `AUTH_COOKIE_SECURE=false`，否则浏览器不会发送登录 Cookie，页面会持续收到 401。接入 HTTPS 后请改为 `AUTH_COOKIE_SECURE=true`。

密钥只保存在服务器的 `.env` 中，不要复制回开发机或提交到代码仓库。

### 首次正式部署：轮换历史模型凭据密钥

本次正式配置使用新的 `MODEL_CREDENTIAL_ENCRYPTION_KEY`，并通过
`MODEL_CREDENTIAL_PREVIOUS_ENCRYPTION_KEY` 临时兼容开发数据库中已经加密的模型凭据。首次启动并确认数据库备份后执行：

```bash
docker compose exec zhilian-service-platform python -m app.cli.rotate_model_credentials
```

命令成功后会显示更新数量，不会输出任何 API Key。随后从 `.env` 删除
`MODEL_CREDENTIAL_PREVIOUS_ENCRYPTION_KEY`，再重新创建两个容器：

```bash
docker compose up -d --force-recreate
```

该轮换只需执行一次。轮换成功后不要再恢复旧模型加密密钥。

## 八、检查 Compose 网络

`release/docker-compose.yml` 已包含 API 和 Worker，并通过外部 `shared_net` 网络访问现有的 MySQL、Redis、MinIO 服务别名。
部署服务器必须已经存在该网络；如果平台 Compose 与基础设施 Compose 分开运行，先执行：

```bash
docker network inspect shared_net >/dev/null 2>&1 || docker network create shared_net
```

如果正式环境使用的是其他网络名称，修改 `docker-compose.yml` 的 `shared_net`，并同步修改 `.env` 中的 MySQL、MinIO 地址。不要把平台表写入 Loan 业务数据库；平台使用独立的 `digital_human_service_platform` 数据库。

## 九、加载镜像并启动

服务器执行：

```bash
cd /opt/zhilian-service-platform
docker load -i zhilian-service-platform-release.tar
docker image inspect zhilian-service-platform:release >/dev/null
docker compose up -d --force-recreate --no-build
```

`release/docker-compose.yml` 使用固定的 `zhilian-service-platform:release` 镜像并设置了 `pull_policy: never`，因此不会尝试从 Docker Hub 拉取，也不会在服务器重新编译。若 `docker load` 前镜像文件损坏，Compose 会立即报错而不是长时间等待网络。

如果日志仍出现 `[+] Building`，说明当前目录使用的还是旧版 Compose 文件；请确认已覆盖 `/opt/zhilian-service-platform/docker-compose.yml`，并检查：

```bash
docker compose config | grep -E 'build:|image:'
```

输出中应只有 `image: zhilian-service-platform:release`，不应出现 `build:`。

查看日志：

```bash
docker compose logs -f --tail=100 zhilian-service-platform
docker compose logs -f --tail=100 zhilian-service-platform-worker
```

## 十、部署后检查

健康检查：

```bash
curl http://127.0.0.1:35081/health
```

后台地址：

```text
http://服务器地址:35081/admin/
```

重点检查：

1. 健康检查显示数据库正常。
2. 管理员可以登录。
3. 原有小智中间件服务、问答表和大语言模型配置存在。
4. 已上传的服务图片和视频可以正常访问。
5. 小智调用代理时能看到 `POST /v1/chat/completions`。
6. 语音识别和图像生成任务能够创建并由 Worker 执行。

## 十一、升级和回滚

升级前先备份 `digital_human_service_platform` 数据库和 MinIO 媒体数据。

升级（开发机重新构建并导出 tar，上传后执行）：

```bash
docker load -i zhilian-service-platform-release.tar
docker compose up -d --force-recreate --no-build
```

应用启动时会自动执行 Alembic 迁移。若新版本启动异常，先停止新容器，再恢复上一版本镜像或代码，并根据备份文档恢复数据。

不要删除正式 MySQL 数据卷、正式 MinIO 数据卷或 `.env`。
