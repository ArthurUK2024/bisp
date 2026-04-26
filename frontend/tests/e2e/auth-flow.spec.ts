import { test, expect } from '@playwright/test'

// auth-flow.spec.ts
//
// End-to-end happy path: register a fresh user, assert the post-register
// redirect lands on /dashboard/profile, reload the browser to prove silent
// refresh rehydrates the session through the HttpOnly cookie, then log
// out from the header and assert the landing is /login.
//
// The password zx7mnp45 is the Phase 2 test-credential baseline from the
// 02-02 decisions list: abcdef12 is on Django's CommonPasswordValidator
// blacklist and fails the register call with 400.

test('register -> redirect -> refresh survives -> logout', async ({ page }) => {
  const email = `e2e-${Date.now()}@example.test`
  const password = 'zx7mnp45'

  await page.goto('/register')
  await page.getByRole('textbox', { name: 'Email' }).fill(email)
  await page.getByRole('textbox', { name: 'Password' }).fill(password)
  await page.getByRole('button', { name: 'Create account' }).click()

  await page.waitForURL('**/dashboard/profile')
  await expect(page.getByRole('heading', { name: 'Your profile' })).toBeVisible()

  // Browser reload -- session must survive via silent refresh.
  await page.reload()
  await expect(page).toHaveURL(/\/dashboard\/profile$/)
  await expect(page.getByRole('heading', { name: 'Your profile' })).toBeVisible()

  // Logout from the header button.
  await page.getByRole('button', { name: 'Log out' }).click()
  await page.waitForURL('**/login')
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
})
