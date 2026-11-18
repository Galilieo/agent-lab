// 对话页先保留欢迎区与展示用 Sender；接线时由自有代码管理消息、SSE 和 Agent 状态。
import { Sender, Welcome } from '@ant-design/x'
import { Button, Space, Tag, Typography, theme } from 'antd'
import type { ReactElement } from 'react'
import { Link, useParams } from 'react-router'

export function ConversationPage(): ReactElement {
  const { token } = theme.useToken()
  const { conversationId } = useParams()

  return (
    <section className="conversation-page">
      <header
        className="conversation-heading"
        style={{ borderBottom: `1px solid ${token.colorBorderSecondary}` }}
      >
        <Typography.Text strong>{conversationId ? '对话' : '新对话'}</Typography.Text>
        <Tag>未关联岗位</Tag>
      </header>
      <div className="conversation-body">
        <div className="conversation-welcome">
          <Welcome
            variant="borderless"
            title="今天想准备哪个岗位？"
            description="提供简历、JD 或补充经历，基于你确认过的事实准备简历。"
          />
          <Space wrap style={{ marginTop: token.marginLG }}>
            <Button disabled>上传简历</Button>
            <Button disabled>发 JD 或截图</Button>
            <Link to="/jobs">
              <Button>从岗位库选一个</Button>
            </Link>
            <Button disabled>补充经历</Button>
          </Space>
        </div>
      </div>
      <div className="conversation-composer">
        <Sender disabled placeholder="对话功能准备中" autoSize={{ minRows: 2, maxRows: 6 }} />
        <Typography.Text type="secondary" className="composer-note">
          新增、修改和删除前，会先请你确认。
        </Typography.Text>
      </div>
    </section>
  )
}
