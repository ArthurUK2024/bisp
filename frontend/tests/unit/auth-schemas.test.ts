// tests/unit/auth-schemas.test.ts
//
// @vitest-environment node
//
// Zod schemas are the inline form-validation source of truth. These tests
// pin the behaviour that mirrors Django's LetterAndDigitValidator so a
// future refactor of the regex cannot drift silently.
//
// The node environment override keeps this file independent of happy-dom
// (not installed in the Phase 2 Wave 0 dep set) — zod has no DOM
// dependencies.

import { describe, it, expect } from 'vitest'
import { loginSchema, registerSchema } from '../../schemas/auth'

describe('loginSchema', () => {
  it('accepts valid email and min-8 password', () => {
    const parsed = loginSchema.parse({ email: 'a@a.test', password: 'abcdef12' })
    expect(parsed.email).toBe('a@a.test')
    expect(parsed.password).toBe('abcdef12')
  })

  it('rejects empty email', () => {
    expect(() => loginSchema.parse({ email: '', password: 'abcdef12' })).toThrow()
  })

  it('rejects short password', () => {
    expect(() => loginSchema.parse({ email: 'a@a.test', password: 'abc1' })).toThrow()
  })
})

describe('registerSchema (mirrors Django LetterAndDigitValidator)', () => {
  it('accepts valid input', () => {
    const parsed = registerSchema.parse({
      email: 'a@a.test',
      password: 'abcdef12',
    })
    expect(parsed.password).toBe('abcdef12')
  })

  it('rejects letters-only password', () => {
    expect(() => registerSchema.parse({ email: 'a@a.test', password: 'abcdefgh' })).toThrow()
  })

  it('rejects digits-only password', () => {
    expect(() => registerSchema.parse({ email: 'a@a.test', password: '12345678' })).toThrow()
  })

  it('rejects short password', () => {
    expect(() => registerSchema.parse({ email: 'a@a.test', password: 'abc1' })).toThrow()
  })
})
