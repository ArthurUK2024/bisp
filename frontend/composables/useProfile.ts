// composables/useProfile.ts
//
// Browser-side profile actions. Wraps useAuthedApi() so the Bearer
// header from the Pinia store is attached on every call and a 401
// triggers the single silent-refresh retry. The three actions mirror
// the Django endpoints one-to-one:
//
//   fetchMyProfile()  → GET   /api/auth/users/me/profile/
//   updateMyProfile() → PATCH /api/auth/users/me/profile/
//   uploadAvatar()    → POST  /api/auth/users/me/avatar/  (multipart)
//
// The catch-all BFF at server/api/auth/[...path].ts forwards each call
// to Django /api/v1/users/me/{profile,avatar}/ with the Bearer attached.

import type { ProfileInput } from '~/schemas/profile'

export interface Profile {
  display_name: string
  phone: string
  bio: string
  avatar: string | null
}

export function useProfile() {
  const api = useAuthedApi()

  async function fetchMyProfile(): Promise<Profile> {
    return await api<Profile>('users/me/profile/', { method: 'GET' })
  }

  async function updateMyProfile(body: ProfileInput): Promise<Profile> {
    return await api<Profile>('users/me/profile/', {
      method: 'PATCH',
      body,
    })
  }

  async function uploadAvatar(file: File): Promise<Profile> {
    const form = new FormData()
    form.append('avatar', file)
    return await api<Profile>('users/me/avatar/', {
      method: 'POST',
      body: form,
    })
  }

  return { fetchMyProfile, updateMyProfile, uploadAvatar }
}
