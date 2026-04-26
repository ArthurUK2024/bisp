// server/api/auth/refresh.post.ts
//
// POST /api/auth/refresh — the silent-refresh endpoint. Reads the
// browser's refresh_token cookie, forwards it to Django
// /api/v1/auth/refresh/, then re-issues the rotated refresh cookie to
// the browser at the rewritten path /api/auth/. Returns the new access
// token in the response body.
//
// Django's RefreshView (from 02-02) returns 401 when the refresh is
// missing, which the Pinia store's init() action catches silently —
// that is the "user is not logged in, stay logged out" branch of
// silent refresh.

import {
  forwardToDjango,
  extractDjangoRefresh,
  setBrowserRefreshCookie,
} from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  const djangoResponse = await forwardToDjango(event, {
    path: 'auth/refresh/',
    method: 'POST',
    forwardAuthorization: false,
    forwardRefreshCookie: true,
  })

  // Rotate: re-issue the new refresh cookie at the browser-facing path.
  const rotated = extractDjangoRefresh(djangoResponse.headers)
  if (rotated) {
    setBrowserRefreshCookie(event, rotated)
  }

  return djangoResponse._data
})
