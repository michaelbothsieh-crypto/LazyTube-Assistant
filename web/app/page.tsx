import { getLatestData } from '@/lib/data'
import TopBar from '@/components/TopBar'
import HeroConsensus from '@/components/HeroConsensus'
import StockRanking from '@/components/StockRanking'
import SentimentMeter from '@/components/SentimentMeter'
import KOLGrid from '@/components/KOLGrid'
import KeywordCloud from '@/components/KeywordCloud'
import ConsensusChart from '@/components/ConsensusChart'

export const revalidate = 1800 // ISR: 每 30 分鐘重新生成

export default function Home() {
  const data = getLatestData()
  const { consensus, episodes, consensus_history, date, generated_at, episodes_analyzed } = data

  return (
    <div className="min-h-screen">
      <TopBar date={date} generatedAt={generated_at} episodesCount={episodes_analyzed} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* Hero */}
        <HeroConsensus
          score={consensus.consensus_score}
          theme={consensus.weekly_theme}
          date={date}
        />

        {/* 主要 Bento Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

          {/* 左：股票共識排行 (2/3) */}
          <div className="lg:col-span-2 space-y-5">
            <StockRanking stocks={consensus.stocks} />
            <ConsensusChart history={consensus_history} />
          </div>

          {/* 右：情緒儀表 + 關鍵詞 (1/3) */}
          <div className="space-y-5">
            <SentimentMeter sentiment={consensus.market_sentiment} />
            <KeywordCloud keywords={consensus.top_keywords} />
          </div>
        </div>

        {/* KOL 集數卡片 */}
        <KOLGrid episodes={episodes} />

      </main>

      <footer className="border-t border-[rgba(59,130,246,0.1)] mt-12 py-6 text-center">
        <p className="text-xs text-slate-600">
          PodConsensus · 每日 09:30 自動更新 · 內容由 AI 分析，不構成投資建議
        </p>
      </footer>
    </div>
  )
}
