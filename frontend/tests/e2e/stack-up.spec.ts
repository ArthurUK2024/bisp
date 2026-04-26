import { expect, test } from '@playwright/test'

test('stack-up: home page renders with API badge', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('h1')).toHaveText('Ijara')
  await expect(page.locator('span.inline-flex')).toContainText(/^API ok/)
})
