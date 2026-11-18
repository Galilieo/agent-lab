// 共享侧栏与主区；窄屏仅把同一份导航放进抽屉，不另建一套路由。
import { MenuOutlined } from '@ant-design/icons'
import { Button, Drawer, Grid, Layout, theme } from 'antd'
import { useState, type ReactElement } from 'react'
import { Outlet } from 'react-router'
import { SideNavigation } from './SideNavigation'

export function AppShell(): ReactElement {
  const { token } = theme.useToken()
  const screens = Grid.useBreakpoint()
  // 与 index.css 里的 @media (max-width: 991px) 对应，改断点时两处一起改。
  const isNarrow = screens.lg === false
  const [navigationOpen, setNavigationOpen] = useState(false)

  return (
    <Layout className="app-shell" style={{ color: token.colorText, fontFamily: token.fontFamily }}>
      {!isNarrow && (
        <Layout.Sider width={232}>
          <SideNavigation />
        </Layout.Sider>
      )}
      <Layout className="app-main">
        {isNarrow && (
          <header
            className="mobile-header"
            style={{ borderBottom: `1px solid ${token.colorBorderSecondary}` }}
          >
            <Button
              type="text"
              icon={<MenuOutlined />}
              aria-label="打开导航"
              onClick={() => setNavigationOpen(true)}
            />
            <span className="brand">
              Job<span style={{ color: token.colorPrimary }}>Pilot</span>
            </span>
          </header>
        )}
        <Layout.Content className="app-content">
          <Outlet />
        </Layout.Content>
      </Layout>
      <Drawer
        title="导航"
        placement="left"
        size={260}
        open={isNarrow && navigationOpen}
        onClose={() => setNavigationOpen(false)}
        styles={{ body: { padding: 0, background: token.colorBgLayout } }}
      >
        <SideNavigation onNavigate={() => setNavigationOpen(false)} />
      </Drawer>
    </Layout>
  )
}
