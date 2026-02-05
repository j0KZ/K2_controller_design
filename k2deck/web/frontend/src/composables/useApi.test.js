import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useApi } from './useApi'

describe('useApi composable', () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    global.fetch = vi.fn()
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  it('should make GET requests', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
    })

    const api = useApi()
    const result = await api.get('/test')

    expect(global.fetch).toHaveBeenCalledWith('/api/test', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })
    expect(result).toEqual({ data: 'test' })
  })

  it('should make PUT requests with body', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })

    const api = useApi()
    const result = await api.put('/test', { key: 'value' })

    expect(global.fetch).toHaveBeenCalledWith('/api/test', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'value' }),
    })
    expect(result).toEqual({ success: true })
  })

  it('should make POST requests', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 1 }),
    })

    const api = useApi()
    const result = await api.post('/items', { name: 'test' })

    expect(global.fetch).toHaveBeenCalledWith('/api/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'test' }),
    })
    expect(result).toEqual({ id: 1 })
  })

  it('should make DELETE requests', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ deleted: true }),
    })

    const api = useApi()
    const result = await api.del('/items/1')

    expect(global.fetch).toHaveBeenCalledWith('/api/items/1', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    })
    expect(result).toEqual({ deleted: true })
  })

  it('should throw ApiError on failure', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail: 'Item not found' }),
    })

    const api = useApi()

    await expect(api.get('/missing')).rejects.toThrow('Item not found')
  })

  it('should handle non-JSON responses', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.reject(new Error('Not JSON')),
    })

    const api = useApi()
    const result = await api.get('/empty')

    expect(result).toBeNull()
  })

  it('should include status in ApiError', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.resolve({ detail: 'Server error' }),
    })

    const api = useApi()

    try {
      await api.get('/error')
    } catch (error) {
      expect(error.status).toBe(500)
      expect(error.message).toBe('Server error')
    }
  })
})
