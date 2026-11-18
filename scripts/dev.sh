#!/usr/bin/env bash
# 准备本地数据库和表结构，并统一管理两个开发服务的生命周期。
set -euo pipefail

for dependency in colima docker uv pnpm; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf '缺少命令 %s，请先安装。\n' "$dependency" >&2
    exit 1
  fi
done

if ! colima status >/dev/null 2>&1; then
  printf 'Colima 未运行，请先执行 colima start。\n' >&2
  exit 1
fi

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

docker --context colima compose up -d --wait --wait-timeout 60 db
(cd jobpilot && uv run --locked alembic upgrade head)

backend_pid=
frontend_pid=

# shellcheck disable=SC2329 # 由 EXIT trap 调用。
stop_services() {
  trap '' INT TERM
  local service_pid
  for service_pid in "$backend_pid" "$frontend_pid"; do
    if [[ -n "$service_pid" ]]; then
      kill -TERM -- "-$service_pid" 2>/dev/null || true
    fi
  done
  wait
}

# 为每个服务建立独立进程组，退出时也能清理热重载和包管理器启动的子进程。
set -m
trap stop_services EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(cd jobpilot && exec uv run --locked uvicorn jobpilot.main:app --reload --app-dir ..) </dev/null &
backend_pid=$!
(cd web && exec pnpm dev) </dev/null &
frontend_pid=$!

printf 'JobPilot 前端 http://127.0.0.1:5174（Ctrl+C 停止前后端）\n'

# macOS 自带的 Bash 3.2 没有 wait -n，轮询以便任一服务退出时回收另一侧。
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

if kill -0 "$backend_pid" 2>/dev/null; then
  stopped_service=前端
  stopped_pid=$frontend_pid
else
  stopped_service=后端
  stopped_pid=$backend_pid
fi

exit_status=0
wait "$stopped_pid" || exit_status=$?
printf '%s已退出（退出码 %s），正在停止开发服务。\n' "$stopped_service" "$exit_status" >&2
# 即使子进程正常返回，开发服务提前结束也视为启动脚本失败。
exit "$((exit_status == 0 ? 1 : exit_status))"
