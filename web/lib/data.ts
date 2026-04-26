import { readFileSync } from 'fs'
import { join } from 'path'
import type { ConsensusData } from '@/types'

export function getLatestData(): ConsensusData {
  const filePath = join(process.cwd(), 'data', 'latest.json')
  const raw = readFileSync(filePath, 'utf-8')
  return JSON.parse(raw)
}
