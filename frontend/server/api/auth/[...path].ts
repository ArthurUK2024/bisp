import { forwardToDjango } from '~/server/utils/proxy'

const EXPLICIT = new Set(['login', 'logout', 'refresh', 'register', 'me'])

export default defineEventHandler(async (event) => {
  const segments = (event.context.params?.path as string) || ''
  const method = event.method as 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'

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

  const url = getRequestURL(event)
  const pathWithSlash = segments.endsWith('/') ? segments : `${segments}/`
  const path = `${pathWithSlash}${url.search}`

  const response = await forwardToDjango(event, {
    path,
    method,
    body,
    forwardAuthorization: true,
    forwardContentType: isMultipart,
  })
  return response._data
})
