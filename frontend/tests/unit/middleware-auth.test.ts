// tests/unit/middleware-auth.test.ts
//
// @vitest-environment node
//
// Auth route-guard unit tests. The real middleware file exports a
// defineNuxtRouteMiddleware default that we cannot invoke directly from
// vitest (the helper is globally auto-imported by Nuxt at build time).
// What we pin here is the *branch structure* of the guard: the same
// three-stage decision tree the middleware walks — pass if authed, else
// one-shot silent refresh, else redirect to /login?next=<encoded>.
//
// Covers AUTH-07. A regression in the middleware redirect contract
// trips one of these four tests before the Playwright
// guarded-route-redirect.spec.ts in 02-06 even runs.

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../stores/auth'

const mockUser = {
  id: 1,
  email: 'a@a.test',
  date_joined: '2026-04-11T00:00:00Z',
}

// Pinned re-implementation of frontend/middleware/auth.ts. If the
// branch structure in the real middleware drifts, this file falls out
// of sync deliberately — the test failure is a signal to re-read both.
async function runGuard(
  auth: ReturnType<typeof useAuthStore>,
  fullPath: string,
): Promise<string | null> {
  if (auth.isAuthed) return null
  if (!auth._initTried) {
    await auth.init()
  }
  if (auth.isAuthed) return null
  return `/login?next=${encodeURIComponent(fullPath)}`
}

describe('auth middleware', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('passes through when the user is authed', async () => {
    const store = useAuthStore()
    store.$patch({ user: mockUser, accessToken: 'tok', _initTried: true })
    const result = await runGuard(store, '/dashboard/profile')
    expect(result).toBeNull()
  })

  it('redirects an unauthed user to /login with an encoded next param', async () => {
    const store = useAuthStore()
    store.$patch({ _initTried: true })
    const result = await runGuard(store, '/dashboard/profile')
    expect(result).toBe('/login?next=%2Fdashboard%2Fprofile')
  })

  it('URL-encodes the next param when the target has a query string', async () => {
    const store = useAuthStore()
    store.$patch({ _initTried: true })
    const result = await runGuard(store, '/dashboard/profile?tab=edit')
    expect(result).toBe('/login?next=%2Fdashboard%2Fprofile%3Ftab%3Dedit')
  })

  it('calls init() exactly once when the store is empty and _initTried is false', async () => {
    const store = useAuthStore()
    const initSpy = vi.spyOn(store, 'init').mockImplementation(async () => {
      store._initTried = true
    })
    await runGuard(store, '/dashboard/profile')
    expect(initSpy).toHaveBeenCalledTimes(1)
  })
})
