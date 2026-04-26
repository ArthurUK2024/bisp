import type { H3Event } from 'h3'

export const DJANGO_REFRESH_COOKIE_PATH = '/api/v1/auth/'
export const BROWSER_REFRESH_COOKIE_PATH = '/api/auth/'
const REFRESH_COOKIE_NAME = 'refresh_token'
const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

interface ForwardOptions {
  path: string
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'
  body?: unknown
  forwardAuthorization?: boolean
  forwardRefreshCookie?: boolean
  forwardContentType?: boolean
}

export async function forwardToDjango<T = unknown>(event: H3Event, opts: ForwardOptions) {
  const config = useRuntimeConfig()
  const url = `${config.apiBaseServer}${opts.path}`
  const headers: Record<string, string> = {}

  if (opts.forwardAuthorization !== false) {
    const incomingAuth = getHeader(event, 'authorization')
    if (incomingAuth) {
      headers.authorization = incomingAuth
    }
  }

  if (opts.forwardRefreshCookie) {
    const value = getCookie(event, REFRESH_COOKIE_NAME)
    if (value) {
      headers.cookie = `${REFRESH_COOKIE_NAME}=${value}`
    }
  }

  if (opts.forwardContentType) {
    const contentType = getHeader(event, 'content-type')
    if (contentType) {
      headers['content-type'] = contentType
    }
  }

  return await $fetch.raw<T>(url, {
    method: opts.method ?? 'GET',
    body: opts.body,
    headers,
    redirect: 'manual',
  })
}

export function setBrowserRefreshCookie(event: H3Event, value: string): void {
  setCookie(event, REFRESH_COOKIE_NAME, value, {
    httpOnly: true,
    secure: !import.meta.dev,
    sameSite: 'lax',
    path: '/api/auth/',
    maxAge: SEVEN_DAYS_SECONDS,
  })
}

export function clearBrowserRefreshCookie(event: H3Event): void {
  deleteCookie(event, REFRESH_COOKIE_NAME, { path: '/api/auth/' })
}

export function extractDjangoRefresh(headers: Headers): string | null {
  const setCookieHeader = headers.get('set-cookie') || ''
  const match = setCookieHeader.match(/refresh_token=([^;]+)/)
  return match ? match[1] : null
}
