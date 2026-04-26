import { forwardToDjango } from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const djangoResponse = await forwardToDjango(event, {
    path: 'auth/register/',
    method: 'POST',
    body,
    forwardAuthorization: false,
  })
  return djangoResponse._data
})
