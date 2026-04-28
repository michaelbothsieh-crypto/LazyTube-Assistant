import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PodConsensus | Podcast Market Research',
  description: 'Daily podcast intelligence for Taiwan and US equities, generated from episode analysis, ticker mentions, and market signal aggregation.',
  keywords: ['Podcast', 'Market research', 'Taiwan equities', 'US equities', 'KOL analysis'],
  openGraph: {
    title: 'PodConsensus | Podcast Market Research',
    description: 'A daily web surface for podcast-derived market research.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW">
      <body>{children}</body>
    </html>
  )
}
