// 验收浏览器 → Vite 代理 → FastAPI → PostgreSQL 的真实连通性。
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Skeleton, Space, Tag, Typography } from 'antd'
import type { ReactElement } from 'react'
import { fetchHealth } from '../api/health'

const HEALTH_STALE_TIME_MS = 30_000

export function HealthStatusCard(): ReactElement {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => fetchHealth(signal),
    staleTime: HEALTH_STALE_TIME_MS,
    retry: false,
  })

  return (
    <Card
      title="服务状态"
      className="health-status"
      size="small"
      extra={
        <Button
          type="text"
          icon={<ReloadOutlined />}
          loading={healthQuery.isFetching}
          onClick={() => {
            void healthQuery.refetch()
          }}
        >
          重新检查
        </Button>
      }
    >
      <div role="status" aria-live="polite">
        {healthQuery.isPending ? (
          <Skeleton active paragraph={{ rows: 1 }} title={false} />
        ) : healthQuery.isError ? (
          <Alert
            type="error"
            title="暂时无法确认服务状态"
            description="请确认本地服务已启动，再点重新检查。"
            showIcon
          />
        ) : (
          <Space wrap>
            <Tag color="success">服务正常</Tag>
            <Tag color="success">数据库正常</Tag>
            <Typography.Text type="secondary">
              status: {healthQuery.data.status} · database: {healthQuery.data.database}
            </Typography.Text>
          </Space>
        )}
      </div>
    </Card>
  )
}
