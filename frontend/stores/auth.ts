// stores/auth.ts
//
// Pinia auth store. Holds the current user and the access JWT in memory.
// The access token lives in memory only — it is NEVER persisted to any
// browser storage API, IndexedDB, or a non-HttpOnly cookie. The browser
// instead carries an HttpOnly refresh cookie issued by the Nitro BFF
// under path=/api/auth/; a hard page refresh clears this store, the
// client plugin then calls init() which swaps the refresh cookie for a
// fresh access token via /api/auth/refresh. This is the AUTH-06
// "browser JS never reads the access token directly" contract, and the
// SC-2c static grep guard over the frontend source tree enforces it at
// commit time.
//
// All four action calls hit same-origin Nitro routes at /api/auth/*.
// The Nitro layer (see server/api/auth/*) proxies to Django and
// rewrites the cookie path from /api/v1/auth/ to /api/auth/.

import { defineStore } from 'pinia'
import type { LoginInput, RegisterInput } from '~/schemas/auth'

export interface User {
  id: number
  email: string
  date_joined: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  // One-shot latch: flipped to true the first time init() runs during
  // this app's lifecycle. Prevents the frontend/middleware/auth.ts
  // route guard from re-firing /api/auth/refresh on every protected
  // navigation. The auth.client.ts plugin fires init() once at app
  // mount; the guard only re-fires it in the narrow race where a
  // direct navigation to /dashboard/** lands before the plugin has
  // resolved its first call.
  _initTried: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    accessToken: null,
    _initTried: false,
  }),

  getters: {
    isAuthed: (state): boolean => state.user !== null && state.accessToken !== null,
  },

  actions: {
    /**
     * Runs once on app mount from frontend/plugins/auth.client.ts and,
     * in the narrow race where a deep-link to /dashboard/** lands
     * before the plugin has resolved, once from middleware/auth.ts.
     * Silent refresh: if the browser holds a refresh cookie issued by
     * the BFF, /api/auth/refresh rotates it and hands back a new
     * access token. If not, this is a no-op — the user stays logged
     * out. Never throws. The _initTried latch is set on entry so a
     * concurrent caller (plugin vs. middleware racing) does not
     * re-fire the network call.
     */
    async init(): Promise<void> {
      if (this._initTried) return
      this._initTried = true
      try {
        const { access } = await $fetch<{ access: string }>('/api/auth/refresh', { method: 'POST' })
        this.accessToken = access
        await this.fetchMe()
      } catch {
        // No valid refresh cookie, or Django rejected it. Stay logged out.
        this.user = null
        this.accessToken = null
      }
    },

    async register(body: RegisterInput): Promise<void> {
      // The Django contract (per 02-02) returns {id, email} and does NOT
      // auto-login. The caller (the register page in 02-05) is expected
      // to follow up with login() on success.
      await $fetch('/api/auth/register', { method: 'POST', body })
    },

    async login(body: LoginInput): Promise<void> {
      const { access } = await $fetch<{ access: string }>('/api/auth/login', {
        method: 'POST',
        body,
      })
      this.accessToken = access
      await this.fetchMe()
    },

    async fetchMe(): Promise<void> {
      this.user = await $fetch<User>('/api/auth/me', {
        headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
      })
    },

    async logout(): Promise<void> {
      try {
        await $fetch('/api/auth/logout', {
          method: 'POST',
          headers: this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {},
        })
      } catch {
        // Idempotent logout — even if the network call fails (already
        // expired, server down), drop local state so the user is not
        // stranded in a half-authenticated shell. The Django side
        // already wraps blacklist in contextlib.suppress(TokenError).
      } finally {
        this.user = null
        this.accessToken = null
      }
    },
  },
})
