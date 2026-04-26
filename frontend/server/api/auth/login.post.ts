// server/api/auth/login.post.ts
//
// POST /api/auth/login — proxies to Django /api/v1/auth/login/. Reads
// the refresh_token from Django's Set-Cookie header and re-issues it
// to the browser at the rewritten path /api/auth/. The response body
// carries only the access token — the refresh value never touches
// browser JS.

import {
  forwardToDjango,
  extractDjangoRefresh,
  setBrowserRefreshCookie,
} from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const djangoResponse = await forwardToDjango(event, {
    path: 'auth/login/',
    method: 'POST',
    body,
    forwardAuthorization: false,
  })

  const refresh = extractDjangoRefresh(djangoResponse.headers)
  if (refresh) {
    setBrowserRefreshCookie(event, refresh)
  }

  // Only return {access} — never the refresh token.
  return djangoResponse._data
})
