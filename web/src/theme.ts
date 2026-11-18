// 应用的极简雾蓝主题；页面自定义颜色也应从 theme.useToken() 读取。
import type { ThemeConfig } from 'antd'

export const jobpilotTheme: ThemeConfig = {
  token: {
    colorPrimary: '#50687F',
    colorPrimaryHover: '#3F566C',
    colorPrimaryBg: '#E4EAF0',
    colorPrimaryText: '#3B5268',
    colorLink: '#50687F',
    colorLinkHover: '#3F566C',
    colorInfo: '#50687F',
    colorBgLayout: '#FFFFFF',
    colorBgContainer: '#FFFFFF',
    colorFillQuaternary: '#FAFAF8',
    colorFillTertiary: '#F2F2F0',
    colorText: '#1F1F1F',
    colorTextSecondary: '#5F5F5B',
    colorTextTertiary: '#8F8F8A',
    colorBorder: '#E6E6E2',
    colorBorderSecondary: '#EFEFEC',
    colorSuccess: '#5B8A4A',
    colorWarning: '#B9842F',
    colorError: '#B5534A',
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    fontSize: 14,
    lineHeight: 1.75,
    borderRadius: 10,
  },
  components: {
    Layout: {
      bodyBg: '#FFFFFF',
      siderBg: '#F6F6F4',
      headerBg: '#F6F6F4',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#E4EAF0',
      itemSelectedColor: '#3B5268',
      itemColor: '#5F5F5B',
      itemBorderRadius: 10,
    },
  },
}
