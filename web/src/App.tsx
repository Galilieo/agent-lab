// 路由只决定主区显示哪个页面；侧栏由共同的布局外壳保留。
import type { ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { AppShell } from './layouts/AppShell'
import { ConversationPage } from './pages/ConversationPage'
import { JobsPage } from './pages/JobsPage'
import {
  AccountPage,
  JobDetailPage,
  NotFoundPage,
  ProfilePage,
  WorkspacePage,
} from './pages/PlaceholderPages'

export default function App(): ReactElement {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/jobs" replace />} />
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="conversations/new" element={<ConversationPage />} />
        <Route path="conversations/:conversationId" element={<ConversationPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="me" element={<ProfilePage />} />
        <Route path="account" element={<AccountPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
