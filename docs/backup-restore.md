# MySQL 备份与恢复

应用容器删除或重建不会删除数据；现有 Compose 的 `./mysql/data` 是持久化边界。删除该目录或磁盘损坏仍会丢失数据，因此升级和批量导入前应备份。

## 备份中间件表

在小智 Compose 目录执行：

```bash
docker exec shared-mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" digital_human_service_platform extended_admin_users extended_ai_tasks extended_asr_baidu_configs extended_asr_volcengine_configs extended_device_name_mappings extended_frontend_ai_service_image_bindings extended_frontend_ai_service_speech_bindings extended_frontend_ai_services extended_image_generation_models extended_image_volcengine_configs extended_llm_dify_configs extended_llm_models extended_llm_openai_configs extended_qa_items extended_qa_tables extended_speech_recognition_models extended_xiaozhi_service_assets extended_xiaozhi_services alembic_version' > zhilian-service-platform-backup.sql
```

服务图片和视频本体位于 MinIO 数据卷，不在 MySQL 中。备份时同时备份 MinIO 的 `shared-minio-data` 卷（或使用 MinIO 客户端导出两个项目 Bucket），否则恢复 SQL 后只能看到媒体元数据而无法读取文件。

备份文件包含管理员密码哈希和业务问答，应按敏感数据保管。

## 恢复

先停止中间件，避免恢复过程中产生新写入：

```bash
docker compose stop zhilian-service-platform
docker exec -i shared-mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" digital_human_service_platform' < zhilian-service-platform-backup.sql
docker compose start zhilian-service-platform
```

恢复后检查 `/health`、管理员登录、问答表数量和 Excel 下载内容。
还应检查数字人项目列表、已发布项目配置和项目图片代理地址是否正常。
