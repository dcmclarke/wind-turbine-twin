import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchJson } from './api'

// Behaves like fetch on a server that never answers: settles only when aborted
function hangingFetch(_url: string, init?: RequestInit): Promise<Response> {
  return new Promise((_resolve, reject) => {
    init?.signal?.addEventListener('abort', () => reject(init.signal?.reason))
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('fetchJson', () => {
  it('gives up on a request that never answers', async () => {
    vi.stubGlobal('fetch', hangingFetch)
    await expect(fetchJson('/api/dashboard', 50)).rejects.toThrow('Request timed out')
  })

  it('rejects an error status', async () => {
    vi.stubGlobal('fetch', async () => new Response('', { status: 503 }))
    await expect(fetchJson('/api/dashboard', 1000)).rejects.toThrow('API error 503')
  })

  it('returns the parsed body', async () => {
    vi.stubGlobal('fetch', async () => Response.json({ ok: true }))
    await expect(fetchJson('/api/dashboard', 1000)).resolves.toEqual({ ok: true })
  })
})
