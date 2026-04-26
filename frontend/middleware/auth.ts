// middleware/auth.ts
//
// AUTH-07 — Nuxt route guard for /dashboard/** and /bookings/**.
// Attach via definePageMeta({ middleware: ['auth'] }) on every page
// that requires a signed-in user. An unauthed visit is redirected to
// /login?next=<encoded-original-path> so the login page can navigate
// the user back to the originally requested page after a successful
// authStore.login() call.
//
// The guard walks a three-stage decision tree:
//
//   1. authStore.isAuthed → pass
//   2. !authStore._initTried → await authStore.init() (silent refresh)
//   3. still not authed → navigateTo('/login?next=' + encoded)
//
// Stage 2 is the race guard. The auth.client.ts plugin already fires
// init() once at app mount, but a deep-link navigation to /dashboard/**
// can land before that first init() has resolved; the _initTried
// latch on the Pinia store ensures init() runs exactly once per app
// lifecycle even when plugin and middleware both race to call it.
//
// The middleware unit tests in tests/unit/middleware-auth.test.ts pin
// the branch structure of this guard.

export default defineNuxtRouteMiddleware(async (to) => {
  // Skip on SSR. The refresh_token cookie is Path=/api/auth/, so it is
  // NOT sent on a reload of /dashboard/**. The SSR middleware would
  // therefore see no auth and redirect to /login before the client has
  // a chance to silent-refresh. Letting the client plugin
  // (plugins/auth.client.ts) run init() first fixes the reload flow.
  if (import.meta.server) return

  const auth = useAuthStore()

  if (auth.isAuthed) return

  if (!auth._initTried) {
    await auth.init()
  }

  if (auth.isAuthed) return

  return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
})
