# 部署与升级

## 0. 本地编译前端

正式服务器不需要 Node/npm。上传前在开发机执行：

```powershell
npm --prefix frontend install
npm --prefix frontend run build
Copy-Item -Recurse -Force frontend\dist release\frontend\dist
```

只上传 `release` 目录；其中必须包含已经编译好的 `frontend/dist`。

## 1. 创建正式环境配置

### 开发环境内网访问

开发环境的 Vite 服务器监听 `0.0.0.0:5173`，同一内网的其他设备可访问
`http://<开发机内网IP>:5173/admin/`。开发环境 `.env.development` 使用 `CORS_ORIGINS=*`，仅用于内网调试；
正式环境必须改为明确的前端来源列表，并通过 HTTPS/反向代理对外提供服务。Windows 主机还需要放行 TCP
`5173` 防火墙端口。

在服务器的项目目录中复制 `.env.example` 为 `.env.production`，至少修改：

- `APP_ENV=production`
- `APP_SECRET_KEY`：至少 32 字节的随机值
- `CORS_ORIGINS`：允许访问公开接口的数字人前端来源
- `DB_HOST`：Loan 项目正式 MySQL 的地址（不使用 `xiaozhi-esp32-server-db` 别名）
- `DB_NAME=digital_human_service_platform`
- 数据库账号和密码
- 正式环境的小智 URL、Token 和 JSESSIONID
- `MINIO_ENDPOINT=minio.example.com:9000`
- 正式环境 MinIO 凭据（`MINIO_ACCESS_KEY`、`MINIO_SECRET_KEY`）
- `MINIO_BUCKET=xiaozhi-project-assets`
- `MINIO_SECURE=false`（当前使用宿主机 `30900 -> 9000` 的 HTTP API）
- 首次管理员账号和强密码
- `LLM_PROXY_API_KEY`：仅提供给小智服务调用中间件
- `UPSTREAM_LLM_TIMEOUT_SECONDS`、`LLM_PROXY_FALLBACK_TEXT`：请求超时和中文兜底配置

外部大模型的 API 地址、模型名称和 API 密钥不再写入环境文件，部署后在后台每个数字人项目的“大语言模型”区域单独维护。

项目大模型供应器可选择 `OpenAI接口` 或 `Dify接口`。Dify 项目还需要选择 `chat-messages` 对话模式或 `workflows/run` 工作流模式。新增、修改或切换项目供应器只写入 MySQL，扩展服务会按请求动态读取，不需要重启容器；只有修改环境文件中的 `LLM_PROXY_API_KEY` 等服务级配置时才需要重新创建容器。

`.env.production` 不应上传到 Git、聊天或镜像仓库。

## 2. 加入现有 Docker Compose

目录示例：

```text
xiaozhi-compose/
├─ docker-compose.yml
├─ mysql/data/
└─ ZhiLianServicePlatform/
```

在现有 Compose 的 `services` 中增加 API 和 Worker（两者共用同一镜像与配置）。推荐先在开发机导出 `zhilian-service-platform:release`，服务器只执行 `docker load`，不再构建或下载依赖：

```yaml
  zhilian-service-platform:
    image: zhilian-service-platform:release
    pull_policy: never
    container_name: zhilian-service-platform
    restart: always
    env_file:
      - ./ZhiLianServicePlatform/.env.production
    ports:
      - "35081:8000"
    depends_on:
      shared-mysql:
        condition: service_healthy
    networks:
      shared_net:
        aliases:
          - zhilian-service-platform

  zhilian-service-platform-worker:
    image: zhilian-service-platform:release
    pull_policy: never
    container_name: zhilian-service-platform-worker
    restart: always
    env_file:
      - ./ZhiLianServicePlatform/.env.production
    command: ["python", "-m", "app.worker.main"]
    depends_on:
      shared-mysql:
        condition: service_healthy
    networks:
      shared_net:
        aliases:
          - zhilian-service-platform-worker
```

应用通过 Loan 项目正式 MySQL 的 `DB_HOST:3306` 访问，并只创建 `extended_` 前缀表。API 和 Worker 启动前必须先执行一次迁移。

迁移 `0003` 为数字人项目增加可空的 `qa_table_id` 外键。问答表为可选配置：绑定后优先匹配固定答案，未命中或未绑定时直接调用项目绑定的大语言模型；一张问答表可以被多个项目复用，被项目使用的问答表不能删除。

迁移 `0004` 增加项目级大模型配置字段；API 密钥以 `APP_SECRET_KEY` 加密后保存，迁移不会回填或覆盖现有项目配置。

迁移 `0010` 为小智中间件服务增加可空的 `digital_human_name`（数字人名称）字段；已有服务自动保留为空，可在后台编辑页面填写。

图片通过环境变量 `MINIO_ENDPOINT` 指定的服务写入 MinIO，不写入应用容器文件系统。开发环境建议使用
`.env.development` 和 Bucket `xiaozhi-project-assets-development`；正式环境使用
`.env.production` 和 Bucket `xiaozhi-project-assets`。两个环境必须使用不同 Bucket，避免测试图片出现在正式项目中。

## 3. 首次部署

正式环境推荐在开发机完成镜像构建并导出，再在服务器加载镜像，避免服务器网络慢导致 pip/系统依赖下载超时。详见 [本地构建与部署文档](release-build-and-deploy.md)。如果已经上传并加载 `zhilian-service-platform:release`，使用以下命令启动：

```bash
docker compose up -d --force-recreate --no-build
docker compose logs -f --tail=100 zhilian-service-platform
docker compose exec zhilian-service-platform python -m app.cli.seed_device_mappings
```

如果数据库中已经存在旧的设备映射，`alembic upgrade head` 会自动为其创建 `legacy-数字` 项目草稿并完成关联；不需要重复导入。首次部署后仍可执行上面的种子命令补充缺失映射。

确认：

```bash
curl http://127.0.0.1:35081/health
```

健康响应应同时显示应用和数据库正常。

## 4. 升级

升级前先按备份文档备份 `extended_` 表，然后覆盖或拉取新代码：

```bash
docker compose up -d --force-recreate --no-build
docker compose logs --tail=100 zhilian-service-platform
```

升级时先执行一次迁移，再重建 API/Worker；迁移失败时不要启动新版本容器：

```bash
docker compose run --rm zhilian-service-platform python -m alembic -c backend/alembic.ini upgrade head
docker compose up -d --force-recreate --no-build zhilian-service-platform zhilian-service-platform-worker
```

## 5. 反向代理

正式环境建议通过现有 Nginx/网关提供 HTTPS，并代理到 `zhilian-service-platform:8000`。使用 HTTPS 时认证 Cookie 自动带 `Secure` 标记；后台页面与 API 应保持同源。
