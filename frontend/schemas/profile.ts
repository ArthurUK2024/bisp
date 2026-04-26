import { z } from 'zod'

export const profileSchema = z.object({
  display_name: z.string().max(80, { message: 'Display name is at most 80 characters.' }),
  phone: z.string().max(20, { message: 'Phone is at most 20 characters.' }),
  bio: z.string().max(300, { message: 'Bio is at most 300 characters.' }),
})

export type ProfileInput = z.infer<typeof profileSchema>

export const AVATAR_MAX_BYTES = 2 * 1024 * 1024
export const AVATAR_ACCEPT = 'image/jpeg,image/png,image/webp'
