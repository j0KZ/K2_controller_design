const BASE_URL = '/api'

class ApiError extends Error {
  constructor(response, data) {
    super(data?.detail || response.statusText)
    this.status = response.status
    this.data = data
  }
}

export function useApi() {
  async function request(method, path, body = null) {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' },
    }
    if (body) options.body = JSON.stringify(body)

    const response = await fetch(`${BASE_URL}${path}`, options)
    const data = await response.json().catch(() => null)

    if (!response.ok) throw new ApiError(response, data)
    return data
  }

  return {
    get: (path) => request('GET', path),
    put: (path, body) => request('PUT', path, body),
    post: (path, body) => request('POST', path, body),
    del: (path) => request('DELETE', path),
  }
}
