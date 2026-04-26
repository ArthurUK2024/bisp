import { forwardToDjango, clearBrowserRefreshCookie } from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  try {
    await forwardToDjango(event, {
      path: 'auth/logout/',
      method: 'POST',
      forwardRefreshCookie: true,
    })
  } catch {
    // ignore
  } finally {
    clearBrowserRefreshCookie(event)
  }
  setResponseStatus(event, 204)
  return null
})
