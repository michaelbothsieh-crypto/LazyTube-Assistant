import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PodConsensus — 財經 KOL 共識儀表板',
  description: '每天自動分析 12+ 台灣財經 Podcast，提取股票標的與 KOL 共識，讓你一眼掌握今日市場焦點。',
  keywords: ['台股', '美股', 'Podcast', '財經', 'KOL', '共識', '投資'],
  openGraph: {
    title: 'PodConsensus — 財經 KOL 共識儀表板',
    description: '每天自動分析 12+ 台灣財經 Podcast，提取股票標的與 KOL 共識',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW">
      <body className="antialiased">{children}</body>
    </html>
  )
}
