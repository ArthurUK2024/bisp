import { test, expect } from '@playwright/test'

// cookie-inaccessible.spec.ts
//
// The Playwright-side proof that the refresh_token cookie issued by the
// Nitro BFF is genuinely HttpOnly. Two assertions:
//
//   1. page.evaluate(() => document.cookie) must NOT contain
//      "refresh_token" -- browser JS cannot see the value.
//   2. page.context().cookies() (which reads cookies through Playwright
//      at the network layer, not document.cookie) DOES see the cookie
//      with httpOnly=true, sameSite=Lax, path=/api/auth/.
//
// DevTools is still the viva-panel-definitive check for the HttpOnly
// badge; this spec is the automated gate that fails loud if the flag
// regresses.

test('refresh_token cookie is not exposed to document.cookie', async ({ page }) => {
  const email = `cookie-${Date.now()}@example.test`
  const password = 'zx7mnp45'

  await page.goto('/register')
  await page.getByRole('textbox', { name: 'Email' }).fill(email)
  await page.getByRole('textbox', { name: 'Password' }).fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await page.waitForURL('**/dashboard/profile')

  const jsVisibleCookie = await page.evaluate(() => document.cookie)
  expect(jsVisibleCookie).not.toContain('refresh_token')

  const allCookies = await page.context().cookies()
  const refreshCookie = allCookies.find((c) => c.name === 'refresh_token')
  expect(refreshCookie).toBeDefined()
  expect(refreshCookie?.httpOnly).toBe(true)
  expect(refreshCookie?.sameSite).toBe('Lax')
  expect(refreshCookie?.path).toBe('/api/auth/')
})
