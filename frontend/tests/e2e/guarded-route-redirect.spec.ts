import { test, expect } from '@playwright/test'

// guarded-route-redirect.spec.ts
//
// AUTH-07 end-to-end:
//   - Unauthed visit to /dashboard/profile redirects to
//     /login?next=%2Fdashboard%2Fprofile
//   - Login from that screen navigates back to /dashboard/profile
//
// Two separate tests so the failure mode for each direction is visible
// in the harness output.

test('unauthed visit to /dashboard/profile redirects to /login with next', async ({
  page,
  context,
}) => {
  await context.clearCookies()
  await page.goto('/dashboard/profile')
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard%2Fprofile/)
})

test('login from /login?next returns to the original path', async ({ page, context }) => {
  await context.clearCookies()
  const email = `guard-${Date.now()}@example.test`
  const password = 'zx7mnp45'

  // Create the user via the register flow so the login target is real.
  await page.goto('/register')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/dashboard/profile')

  // Logout, then go to the guarded route directly.
  await page.click('button:has-text("Log out")')
  await page.waitForURL('**/login')
  await page.goto('/dashboard/profile')
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard%2Fprofile/)

  // Log in from the login screen -- lands back on /dashboard/profile.
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/dashboard/profile')
  await expect(page.locator('h1')).toContainText('Your profile')
})
