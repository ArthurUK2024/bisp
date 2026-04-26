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

  return djangoResponse._data
})
