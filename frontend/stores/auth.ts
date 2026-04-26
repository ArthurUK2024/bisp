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
    async init(): Promise<void> {
      if (this._initTried) return
      this._initTried = true
      try {
        const { access } = await $fetch<{ access: string }>('/api/auth/refresh', { method: 'POST' })
        this.accessToken = access
        await this.fetchMe()
      } catch {
        this.user = null
        this.accessToken = null
      }
    },

    async register(body: RegisterInput): Promise<void> {
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
        // ignore
      } finally {
        this.user = null
        this.accessToken = null
      }
    },
  },
})
