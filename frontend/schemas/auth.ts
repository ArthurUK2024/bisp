import { z } from 'zod'

const registerPasswordSchema = z
  .string()
  .min(8, { message: 'Password must be at least 8 characters.' })
  .regex(/[A-Za-z]/, { message: 'Password must contain at least one letter.' })
  .regex(/\d/, { message: 'Password must contain at least one digit.' })

export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8, { message: 'Password must be at least 8 characters.' }),
})

export const registerSchema = z.object({
  email: z.string().email(),
  password: registerPasswordSchema,
})

export type LoginInput = z.infer<typeof loginSchema>
export type RegisterInput = z.infer<typeof registerSchema>
