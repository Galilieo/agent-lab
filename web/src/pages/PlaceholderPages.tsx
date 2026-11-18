// 集中存放尚未接业务接口的页面；只建立导航与内容槽位，不展示虚构业务结果。
import { Card, Empty, Tabs, Typography } from 'antd'
import type { ReactElement, ReactNode } from 'react'
import { Link } from 'react-router'

interface PlaceholderProps {
  title: string
  description: ReactNode
}

function PagePlaceholder({ title, description }: PlaceholderProps): ReactElement {
  return (
    <section className="page">
      <header className="page-heading">
        <Typography.Title level={1}>{title}</Typography.Title>
      </header>
      <Card>
        <Empty className="page-empty" description={description} />
      </Card>
    </section>
  )
}

export function WorkspacePage(): ReactElement {
  return (
    <PagePlaceholder
      title="工作台"
      description={
        <>
          工作台将在后续开放，先从<Link to="/jobs">岗位库</Link>开始。
        </>
      }
    />
  )
}

export function JobDetailPage(): ReactElement {
  return (
    <PagePlaceholder
      title="岗位详情"
      description={
        <>
          岗位详情准备中。<Link to="/jobs">返回岗位库</Link>
        </>
      }
    />
  )
}

export function ProfilePage(): ReactElement {
  return (
    <section className="page">
      <header className="page-heading">
        <Typography.Title level={1}>我的</Typography.Title>
      </header>
      <Tabs
        items={[
          {
            key: 'facts',
            label: '经历',
            children: <Empty description="经历事实库准备中，改写将只引用你确认过的事实。" />,
          },
          {
            key: 'resumes',
            label: '简历',
            children: <Empty description="定制简历准备中，每份简历将关联岗位与事实库版本。" />,
          },
          {
            key: 'memories',
            label: '记忆',
            children: <Empty description="偏好记忆准备中，记忆只保存偏好，不保存经历。" />,
          },
        ]}
      />
    </section>
  )
}

export function AccountPage(): ReactElement {
  return <PagePlaceholder title="账号设置" description="登录与账号管理准备中。" />
}

export function NotFoundPage(): ReactElement {
  return (
    <PagePlaceholder
      title="找不到这个页面"
      description={
        <>
          可以<Link to="/jobs">返回岗位库</Link>继续。
        </>
      }
    />
  )
}
