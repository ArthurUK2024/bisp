// server/api/__tests__/bff-proxy.test.ts
//
// @vitest-environment node
//
// Unit tests for the BFF proxy helpers. These pin the two fragile seams
// of the silent-refresh loop:
//
//   1. extractDjangoRefresh() — regex parse of Django's Set-Cookie
//      header. A refactor that breaks the match silently breaks every
//      /api/auth/login, /api/auth/refresh, and /api/auth/logout flow
//      with no other observable failure — the access token still lands
//      in the response body, the cookie just never gets re-issued.
//   2. setBrowserRefreshCookie() / clearBrowserRefreshCookie() — the
//      cookie path rewrite from Django /api/v1/auth/ to browser
//      /api/auth/. This is the CRITICAL INVARIANT of the BFF pattern:
//      the browser never sees the /api/v1/ path, and any future
//      refactor that leaks /api/v1/auth/ into a setCookie call would
//      silently expose the Django URL structure to browser JS.
//
// Full H3 event mocking via @nuxt/test-utils is possible but fragile
// across minor versions. The end-to-end handler behaviour is covered
// by the Phase 2 Playwright suite in 02-06.

import { describe, it, expect } from 'vitest'
import {
  extractDjangoRefresh,
  setBrowserRefreshCookie,
  clearBrowserRefreshCookie,
  BROWSER_REFRESH_COOKIE_PATH,
  DJANGO_REFRESH_COOKIE_PATH,
} from '../../utils/proxy'

describe('extractDjangoRefresh', () => {
  it('parses refresh_token out of a real Django Set-Cookie header', () => {
    const headers = new Headers()
    headers.set(
      'set-cookie',
      'refresh_token=abc123xyz; expires=Fri, 18 Apr 2026 12:00:00 GMT; HttpOnly; Max-Age=604800; Path=/api/v1/auth/; SameSite=Lax; Secure',
    )
    expect(extractDjangoRefresh(headers)).toBe('abc123xyz')
  })

  it('parses refresh_token out of a header without Secure (dev mode, DEBUG=True)', () => {
    const headers = new Headers()
    headers.set(
      'set-cookie',
      'refresh_token=devtoken.abc; HttpOnly; Max-Age=604800; Path=/api/v1/auth/; SameSite=Lax',
    )
    expect(extractDjangoRefresh(headers)).toBe('devtoken.abc')
  })

  it('returns null when the Set-Cookie header is absent', () => {
    const headers = new Headers()
    expect(extractDjangoRefresh(headers)).toBeNull()
  })

  it('returns null when the Set-Cookie header is present but carries a different cookie', () => {
    const headers = new Headers()
    headers.set('set-cookie', 'csrftoken=foo; Path=/; HttpOnly')
    expect(extractDjangoRefresh(headers)).toBeNull()
  })
})

describe('cookie path invariant — the browser never sees /api/v1/auth/', () => {
  it('BROWSER_REFRESH_COOKIE_PATH is /api/auth/', () => {
    expect(BROWSER_REFRESH_COOKIE_PATH).toBe('/api/auth/')
  })

  it('DJANGO_REFRESH_COOKIE_PATH is /api/v1/auth/', () => {
    expect(DJANGO_REFRESH_COOKIE_PATH).toBe('/api/v1/auth/')
  })

  it('setBrowserRefreshCookie source body mentions /api/auth/ and NOT /api/v1/auth/', () => {
    const source = setBrowserRefreshCookie.toString()
    expect(source).toContain('/api/auth/')
    expect(source).not.toContain('/api/v1/auth/')
  })

  it('clearBrowserRefreshCookie source body mentions /api/auth/ and NOT /api/v1/auth/', () => {
    const source = clearBrowserRefreshCookie.toString()
    expect(source).toContain('/api/auth/')
    expect(source).not.toContain('/api/v1/auth/')
  })
})
