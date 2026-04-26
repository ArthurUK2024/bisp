// server/api/auth/register.post.ts
//
// POST /api/auth/register — proxies to Django /api/v1/auth/register/.
// Per 02-02 contract, register returns {id, email} on success and does
// NOT auto-login — no cookie is set. The Pinia store's register()
// action follows this with an explicit login() call on success.

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
