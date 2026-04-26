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

  const rotated = extractDjangoRefresh(djangoResponse.headers)
  if (rotated) {
    setBrowserRefreshCookie(event, rotated)
  }

  return djangoResponse._data
})
