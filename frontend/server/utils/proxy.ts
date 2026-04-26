// server/utils/proxy.ts
//
// The one place where Nitro knows about Django. Every server/api/auth/*
// route calls forwardToDjango() — adding a new authenticated endpoint
// in Phase 3+ is a one-line path change.
//
// CRITICAL INVARIANT — the cookie path rewrite: Django issues the
// refresh_token cookie under Path=/api/v1/auth/; the Nitro layer
// re-issues it under Path=/api/auth/ so the browser never sees the
// Django URL structure. The two exported constants below are the
// single source of truth for this rewrite and are asserted by
// bff-proxy.test.ts.
//
// Why $fetch.raw() not $fetch(): a plain $fetch() call drops response
// headers (including Set-Cookie), which silently breaks silent refresh.
// PITFALLS.md §BFF-proxy-leaks flagged this as the #1 silent failure
// mode for the BFF pattern. Always use .raw() on the Django side so
// the handler can read the Set-Cookie header and re-issue the cookie
// to the browser.

import type { H3Event } from 'h3'

export const DJANGO_REFRESH_COOKIE_PATH = '/api/v1/auth/'
export const BROWSER_REFRESH_COOKIE_PATH = '/api/auth/'
const REFRESH_COOKIE_NAME = 'refresh_token'
const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

interface ForwardOptions {
  path: string // e.g. 'auth/login/'
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'
  body?: unknown
  forwardAuthorization?: boolean // default true
  forwardRefreshCookie?: boolean // forward browser cookie as Cookie: refresh_token=<v>
  forwardContentType?: boolean // forward incoming Content-Type (needed for multipart)
}

/**
 * Forward a request from the Nitro layer to Django. Returns the raw
 * $fetch response so callers can read Set-Cookie for cookie rewriting.
 */
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
    // Django should never 3xx us here — surface any redirect as an
    // explicit error instead of following it silently.
    redirect: 'manual',
  })
}

/**
 * Re-issue the Django refresh cookie to the browser at the rewritten
 * path /api/auth/. HttpOnly + SameSite=Lax always, 7-day Max-Age.
 * Secure is turned off in dev so http://localhost can still carry the
 * cookie; a production build (import.meta.dev === false) gets Secure
 * back on.
 */
export function setBrowserRefreshCookie(event: H3Event, value: string): void {
  setCookie(event, REFRESH_COOKIE_NAME, value, {
    httpOnly: true,
    secure: !import.meta.dev,
    sameSite: 'lax',
    path: '/api/auth/',
    maxAge: SEVEN_DAYS_SECONDS,
  })
}

/**
 * Clear the browser refresh cookie. The path MUST match the one used
 * by setBrowserRefreshCookie, otherwise the browser treats it as a
 * different cookie and does not delete.
 */
export function clearBrowserRefreshCookie(event: H3Event): void {
  deleteCookie(event, REFRESH_COOKIE_NAME, { path: '/api/auth/' })
}

/**
 * Extract the refresh_token value from Django's Set-Cookie response
 * header so the caller can re-issue the cookie to the browser at the
 * rewritten path. Returns null if the header is absent or carries a
 * different cookie.
 */
export function extractDjangoRefresh(headers: Headers): string | null {
  const setCookieHeader = headers.get('set-cookie') || ''
  const match = setCookieHeader.match(/refresh_token=([^;]+)/)
  return match ? match[1] : null
}
