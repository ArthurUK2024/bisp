// schemas/auth.ts
//
// Zod schemas for the login and register forms. Duplicated on the Django
// side in apps/accounts/serializers.py::UserRegistrationSerializer, which
// is the authoritative check — this schema powers inline form feedback as
// the user types. The register schema mirrors Django's
// LetterAndDigitValidator so the two rulesets stay in lockstep, per
// ARCHITECTURE.md §Form-validation.
//
// The login schema uses a weaker `min(8)` password rule because the real
// check is Django's — we just want to avoid a pointless round trip on an
// obviously invalid field.

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
