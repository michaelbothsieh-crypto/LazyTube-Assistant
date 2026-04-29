import { getLatestData } from '@/lib/data'
import TasteLanding from '@/components/TasteLanding'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export default async function Home() {
  const data = await getLatestData()
  return <TasteLanding data={data} />
}
