import { forwardToDjango } from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  const djangoResponse = await forwardToDjango(event, {
    path: 'auth/me/',
    method: 'GET',
  })
  return djangoResponse._data
})
