// server/api/auth/[...path].ts
//
// Catch-all BFF proxy for authed browser calls under /api/auth/*.
// 02-04 ships five explicit handlers (register, login, logout, refresh,
// me) which always take priority over this catch-all per Nitro routing
// rules. Every other /api/auth/* path — profile GET/PATCH, avatar POST,
// and Phase 3+ authenticated endpoints — is forwarded to Django
// /api/v1/* with the browser's Authorization header attached.
//
// Multipart passthrough: the avatar upload from useProfile sends a
// FormData body. Reading it as raw bytes with readRawBody() and passing
// straight to $fetch.raw keeps the multipart boundary intact; reading
// it via readBody() would re-serialise as JSON and corrupt the upload.

import { forwardToDjango } from '~/server/utils/proxy'

const EXPLICIT = new Set(['login', 'logout', 'refresh', 'register', 'me'])

export default defineEventHandler(async (event) => {
  const segments = (event.context.params?.path as string) || ''
  const method = event.method as 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'

  // Defensive: explicit handlers shadow this file per Nitro routing,
  // but a stray call must not slip past with unexpected behaviour.
  const head = segments.split('/')[0]
  if (EXPLICIT.has(head)) {
    throw createError({ statusCode: 404, statusMessage: 'Not Found' })
  }

  let body: unknown = undefined
  let isMultipart = false
  if (method !== 'GET' && method !== 'DELETE') {
    const contentType = getHeader(event, 'content-type') || ''
    if (contentType.startsWith('multipart/form-data')) {
      isMultipart = true
      body = await readRawBody(event, false)
    } else {
      body = await readBody(event)
    }
  }

  // Preserve the query string — without this, filters like ?mine=1 or
  // ?role=owner are silently dropped on their way to Django and the
  // endpoint returns the unfiltered set.
  const url = getRequestURL(event)
  const pathWithSlash = segments.endsWith('/') ? segments : `${segments}/`
  const path = `${pathWithSlash}${url.search}`

  const response = await forwardToDjango(event, {
    path,
    method,
    body,
    forwardAuthorization: true,
    // Preserve multipart Content-Type (with boundary) so Django can
    // parse the upload. For JSON bodies ofetch handles it automatically.
    forwardContentType: isMultipart,
  })
  return response._data
})
