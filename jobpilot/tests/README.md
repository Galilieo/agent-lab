# JobPilot 测试

先按根目录 `.env.example` 配置本机 `.env`，并启动数据库容器。
在 `jobpilot/` 目录执行：

```bash
uv run pytest -q
uv run ruff format --check .
uv run ruff check .
```

数据库与接口测试只允许使用与开发库分开的本机 `jobpilot_test`。首次使用时
执行 Alembic 升级；每个数据库测试前后删除全部已登记业务表的数据，保留
`alembic_version`。不要在测试库保存需要保留的资料。

`conftest.py` 提供引擎、session 工厂、单个 session、HTTP 客户端和假模型。
数据库资源按测试创建和关闭，避免连接跨事件循环复用。HTTP 客户端通过
ASGITransport 在同进程中调用应用，并把数据库依赖替换为测试库 session；
这条路径不运行应用 lifespan，因此不代表启动脚本或启动任务已被验证。

`fake_model_client.responses[purpose]` 设置 JSON 响应，`calls` 保存收到的
消息快照，方便后续网关测试检查上下文。它只预设输出，不证明真实模型能力。
默认同步、异步 HTTP 传输均被禁止，避免 pytest 意外调用外部模型。

只运行假模型测试时不需要启动 PostgreSQL：

```bash
uv run pytest tests/test_fake_model_client.py -q
```
