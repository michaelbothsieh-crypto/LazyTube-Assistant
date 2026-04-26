import { readFileSync } from 'fs'
import { join } from 'path'
import type { ConsensusData, Episode } from '@/types'

// Module-level in-memory cache — survives across requests in the same process.
// Works correctly with Next.js ISR: each revalidation cycle gets fresh data
// once the TTL expires. In serverless cold starts, the file is re-read.
const CACHE_TTL_MS = 10 * 60 * 1000 // 10 min (shorter than ISR 30 min)

let _data: ConsensusData | null = null
let _dataTs = 0

export function getLatestData(): ConsensusData {
  const now = Date.now()
  if (_data && now - _dataTs < CACHE_TTL_MS) return _data

  const raw = readFileSync(join(process.cwd(), 'data', 'latest.json'), 'utf-8')
  _data = JSON.parse(raw) as ConsensusData
  _dataTs = now
  return _data
}

export function getEpisodeByKolId(data: ConsensusData, kolId: string): Episode | null {
  return data.episodes.find(ep => ep.kol_id === kolId) ?? null
}

// Cache key for podcast deduplication (use in Python Redis layer):
// Key pattern: podcast:dedupe:{kol_id}:{sha256(episode_title)[:12]}
// TTL: 86400s (24h)
// On hit: return cached result URL → skip NotebookLM analysis
// On miss: run analysis → store result URL under this key
export function podcastCacheKey(kolId: string, episodeTitle: string): string {
  // This function is only for documentation — actual hashing happens in Python
  return `podcast:dedupe:${kolId}:${episodeTitle.slice(0, 12).replace(/\s/g, '_')}`
}
