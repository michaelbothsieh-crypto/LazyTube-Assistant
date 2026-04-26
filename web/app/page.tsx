import { getLatestData } from '@/lib/data'
import TasteLanding from '@/components/TasteLanding'

export const revalidate = 1800

export default function Home() {
  const data = getLatestData()
  return <TasteLanding data={data} />
}
