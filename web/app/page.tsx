import { getLatestData } from '@/lib/data'
import TasteLanding from '@/components/TasteLanding'

export const revalidate = 300 // 5 minute ISR cache for fresh database reads without rebuilding on every request.

export default async function Home() {
  const data = await getLatestData()
  return <TasteLanding data={data} />
}
