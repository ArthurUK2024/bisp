// report-screenshots.mjs
//
// Take real screenshots of the running Ijara stack for embedding in
// the BSc final-year report. Runs inside the `web` compose service
// so it can talk to Django at http://api:8000/ via Docker DNS and to
// Nuxt at http://localhost:3000/ on its own host loopback.
//
// Output: PNG files under /app/report-screenshots/ (bind-mounted to
// report/figures/ on the host).

import { chromium } from 'playwright'
import { writeFile } from 'node:fs/promises'

const OUT = '/app/report-screenshots'

async function main() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
  })

  // A fresh page for each shot so the state is predictable.
  async function shot(name, url, { actions } = {}) {
    const page = await context.newPage()
    await page.goto(url, { waitUntil: 'networkidle' })
    if (actions) await actions(page)
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
    console.log(`captured ${name}.png from ${url}`)
    await page.close()
  }

  // Figure 5.1: index page with live API health badge
  await shot('fig-5-1-index-page', 'http://localhost:3000/')

  // Figure 5.2: login page (VeeValidate form)
  await shot('fig-5-2-login-page', 'http://localhost:3000/login')

  // Figure 5.3: register page
  await shot('fig-5-3-register-page', 'http://localhost:3000/register')

  // Figure 5.4: middleware redirect trace — hit /dashboard/profile unauthed,
  // the redirect lands on /login?next=/dashboard/profile
  await shot('fig-5-4-middleware-redirect', 'http://localhost:3000/dashboard/profile')

  // Figure 5.5: register + login flow — create a user, then capture the
  // logged-in header with the user menu visible.
  {
    const email = `reportshot${Date.now()}@example.test`
    const password = 'zx7mnp45'
    const page = await context.newPage()
    await page.goto('http://localhost:3000/register', { waitUntil: 'networkidle' })
    await page.fill('input[type="email"]', email)
    const pwInputs = await page.$$('input[type="password"]')
    for (const input of pwInputs) await input.fill(password)
    await page.screenshot({ path: `${OUT}/fig-5-5-register-filled.png` })
    console.log('captured fig-5-5-register-filled.png')
    await page.click('button[type="submit"]')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: `${OUT}/fig-5-6-logged-in.png` })
    console.log('captured fig-5-6-logged-in.png (post-register redirect)')
    await page.close()
  }

  // Figure 5.7: Django admin login page (proves admin is mounted)
  await shot('fig-5-7-django-admin', 'http://api:8000/admin/')

  // Figure 5.8: DRF browsable API on the health endpoint
  // Note: health returns JSON so the browsable API renders as plain text.
  // This shot is still useful evidence that /api/v1/health/ is live.
  await shot('fig-5-8-health-endpoint', 'http://api:8000/api/v1/health/')

  await browser.close()
  console.log('all shots done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
