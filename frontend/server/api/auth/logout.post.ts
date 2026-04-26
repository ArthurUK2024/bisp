// server/api/auth/logout.post.ts
//
// POST /api/auth/logout — forwards the Bearer header + refresh cookie
// to Django /api/v1/auth/logout/, then clears the browser refresh
// cookie regardless of the Django response. Idempotent — a stale /
// expired / already-blacklisted cookie still ends in a clean 204 with
// the browser cookie cleared, matching the Django LogoutView
// contextlib.suppress(TokenError) pattern from 02-02.

import { forwardToDjango, clearBrowserRefreshCookie } from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  try {
    await forwardToDjango(event, {
      path: 'auth/logout/',
      method: 'POST',
      forwardRefreshCookie: true,
    })
  } catch {
    // Swallow any Django-side error — logout must be idempotent on
    // the client side. The browser cookie still gets cleared below.
  } finally {
    clearBrowserRefreshCookie(event)
  }
  setResponseStatus(event, 204)
  return null
})
