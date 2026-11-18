# JobPilot 前端

React + Vite + TypeScript 的 P0 骨架，界面依据 `notes/求职助手Agent/07-前端界面规范.md`。
当前包含导航、页面占位与真实健康查询；对话输入、上传、账号和业务数据尚未接入。
工作台属于 P1，只保留路由占位，默认首页为岗位库。

## 运行

需要 Node `>=22.22.0` 与 pnpm `11.7.0`。先启动 PostgreSQL 与 JobPilot 后端：
后端在 `jobpilot/` 中执行 `uv run uvicorn jobpilot.main:app --reload --app-dir ..`，
健康接口应为 `http://127.0.0.1:8000/api/health`。

然后在本目录执行：

```bash
pnpm install --frozen-lockfile
pnpm dev
```

打开 `http://127.0.0.1:5174`，岗位库下方应显示服务、数据库正常及后端返回的两个 `ok`。
5174 避开本机心屿占用的 5173；`strictPort` 防止静默换端口。

```bash
pnpm format:check
pnpm lint
pnpm build
```

`format:check` 用 Prettier 检查格式（配置在 `.prettierrc.json`），`pnpm format` 直接改写；
`lint` 用 ESLint 检查 TypeScript、React Hooks 和热更新约束；`build` 先运行 TypeScript
项目检查，再由 Vite 打包到已忽略的 `dist/`。`pnpm preview` 只预览静态产物，
当前的 API 代理只属于 `pnpm dev`，不代表生产部署已配置。

GitHub Actions（`.github/workflows/web.yml`）在 `web/` 有改动时，按顺序运行上面三条命令；
只做检查，不部署。

## 文件职责

| 文件                                  | 作用                                                       |
| ------------------------------------- | ---------------------------------------------------------- |
| `vite.config.ts`                      | 本机开发端口、`/api` 到 FastAPI 的代理                     |
| `src/main.tsx`                        | 主题、Ant Design App、查询缓存、浏览器路由四层上下文       |
| `src/theme.ts`                        | 全局 token 与 Layout、Menu 的组件 token，统一极简雾蓝配色  |
| `src/App.tsx`                         | 路由表；默认跳转 `/jobs`，共同外壳下切换页面               |
| `src/layouts/`                        | 232px 侧栏、账号菜单、窄屏导航抽屉，以及主区 `Outlet`      |
| `src/pages/`                          | 岗位库、对话欢迎区、其他页面占位                           |
| `src/api/health.ts`                   | HTTP 状态及响应结构校验、取消信号传递                      |
| `src/components/HealthStatusCard.tsx` | 查询加载、成功、错误与手动重试；缓存 30 秒，失败不自动重试 |
| `src/index.css`                       | 结构和间距；颜色通过 `theme.useToken()` 或主题组件样式获得 |

页面路由：`/jobs`、`/jobs/:jobId`、`/conversations/new`、`/conversations/:conversationId`、
`/me`、`/account`，以及 P1 占位 `/workspace`。

## 三处关键约定

浏览器始终用相对路径请求 `/api`。从浏览器看，请求与页面同为 `127.0.0.1:5174`；
Vite 代为请求 `127.0.0.1:8000`，这一段不受浏览器 CORS 限制。之后登录响应的
HttpOnly Cookie 经代理返回，后续同源请求会携带 Cookie；不要在前端改成直连 8000，
也不要混用 localhost 和 127.0.0.1。后端应省略 Cookie 的 Domain，设置适当的 Path。
当前尚未实现登录，因此健康查询通过不等于 Cookie 登录已验证。

`ConfigProvider` 接收 `theme.ts`，Ant Design 组件从上下文生成样式。
自定义区域通过 `theme.useToken()` 获取同一套计算后的 token；仅导入配置对象不会自动给页面配色。
嵌套的 Ant Design `App` 为以后 `App.useApp()` 的 message、modal 提供同一份主题上下文。

`BrowserRouter` 管 URL，`App.tsx` 匹配页面，`AppShell` 保留导航，`Outlet` 放当前页面。
Ant Design X 当前仅使用 Welcome 与禁用的 Sender，不使用 X SDK，也不接管 SSE、消息状态或 Agent 运行。

## 版本确认

精确版本见 `package.json`、`pnpm-lock.yaml` 与 06 的版本表。2026-11-16 用户确认：
当前 create-vite 9.3.4 模板默认 oxlint、TypeScript 7.0.2；项目改配 ESLint，并采用
官方 create-vite 9.2.0 模板的 TypeScript 6.0.2，以满足 typescript-eslint 的 peer 范围。
Ant Design X 2.10.0 所需的 antd `^6.1.1` 由本项目 6.7.1 满足。
