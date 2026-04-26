// server/api/auth/me.get.ts
//
// GET /api/auth/me — forwards the browser's Authorization: Bearer
// header to Django /api/v1/auth/me/ and returns the user shape. Used
// by the Pinia store's fetchMe() action after a successful login or
// a successful silent refresh on init().

import { forwardToDjango } from '~/server/utils/proxy'

export default defineEventHandler(async (event) => {
  const djangoResponse = await forwardToDjango(event, {
    path: 'auth/me/',
    method: 'GET',
  })
  return djangoResponse._data
})
