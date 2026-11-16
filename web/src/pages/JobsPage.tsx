// P0 默认首页；业务列表接入前只提供入口、空状态和真实健康检查。
import { Button, Card, Empty, Typography } from 'antd'
import type { ReactElement } from 'react'
import { Link } from 'react-router'
import { HealthStatusCard } from '../components/HealthStatusCard'

export function JobsPage(): ReactElement {
  return (
    <section className="page">
      <header className="page-heading">
        <Typography.Title level={1}>岗位库</Typography.Title>
        <Typography.Text type="secondary">在对话里提供 JD，整理岗位要求，再用已确认的经历生成定制简历。</Typography.Text>
      </header>
      <Card>
        <Empty className="page-empty" description="岗位库准备中，从一段新对话开始。">
          <Link to="/conversations/new"><Button type="primary">开始对话</Button></Link>
        </Empty>
      </Card>
      <HealthStatusCard />
    </section>
  )
}
