// 只负责健康接口的 HTTP 契约；缓存和界面状态由调用它的 Query 管理。
export interface HealthStatus {
  status: 'ok'
  database: 'ok'
}

export async function fetchHealth(signal: AbortSignal): Promise<HealthStatus> {
  const response = await fetch('/api/health', {
    credentials: 'same-origin',
    signal,
  })
  if (!response.ok) {
    throw new Error('暂时无法连接服务，请稍后重试。')
  }

  const health: unknown = await response.json()
  if (
    typeof health !== 'object' || health === null ||
    !('status' in health) || health.status !== 'ok' ||
    !('database' in health) || health.database !== 'ok'
  ) {
    throw new Error('服务状态暂时无法确认，请稍后重试。')
  }
  return { status: health.status, database: health.database }
}
