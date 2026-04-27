import { getLatestData } from '@/lib/data'
import TasteLanding from '@/components/TasteLanding'

export const revalidate = 300  // 5 分鐘重新驗證（DB 有新資料即反映）

export default async function Home() {
  const data = await getLatestData()
  return <TasteLanding data={data} />
}
