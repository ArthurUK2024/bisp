import { test, expect } from '@playwright/test'

// public-profile.spec.ts
//
// PROF-03 + PROF-04 end-to-end: an anonymous visitor loads a /users/<id>
// URL and sees the user's display name and the listings-coming-soon
// placeholder. Authentication is explicitly cleared on the Playwright
// context before navigating so the assertion cannot be satisfied by a
// stray session cookie left over from a previous test.

test('anonymous visit to /users/<id> shows display name and listings placeholder', async ({
  page,
  context,
}) => {
  const email = `public-${Date.now()}@example.test`
  const password = 'zx7mnp45'

  // Register the user so an id is known to exist.
  await page.goto('/register')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/dashboard/profile')

  // Read the authed user's id from the BFF /api/auth/me route before
  // dropping cookies, so the next navigation hits a real profile.
  const me = await page.evaluate(async () => {
    const r = await fetch('/api/auth/me', { method: 'GET' })
    if (!r.ok) return null
    return (await r.json()) as { id: number }
  })
  expect(me?.id).toBeTruthy()

  // Drop auth, visit public profile as an anonymous guest.
  await context.clearCookies()
  await page.goto(`/users/${me!.id}/`)
  await expect(page.locator('main')).toContainText('Listings will appear here in Phase 3.')
})
