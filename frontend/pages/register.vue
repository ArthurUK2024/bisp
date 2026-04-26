<script setup lang="ts">
// pages/register.vue
//
// Public register page. VeeValidate form bound to registerSchema
// (which mirrors Django's LetterAndDigitValidator — min 8, one
// letter, one digit). On success, the page first calls
// authStore.register() (Django responds 201 with {id, email} and
// issues no tokens — locked decision #10 from 02-04), then chains
// into authStore.login() so the user lands on /dashboard/profile
// already signed in. Two round trips, one form submit.
//
// Nuxt UI v3 components used: UCard, UFormField, UInput, UButton.

import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { registerSchema } from '~/schemas/auth'

definePageMeta({
  middleware: [],
})

const auth = useAuthStore()

const { handleSubmit, errors, defineField, isSubmitting } = useForm({
  validationSchema: toTypedSchema(registerSchema),
})

const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')

const submitError = ref<string | null>(null)

const onSubmit = handleSubmit(async (values) => {
  submitError.value = null
  try {
    await auth.register(values)
    // Locked decision 10 — Django does not auto-login on register.
    // Chain into login() so the user lands authed on /dashboard/profile
    // without a second form submit.
    await auth.login(values)
    await navigateTo('/dashboard/profile')
  } catch (err: unknown) {
    // DRF ValidationError responses come through $fetch as FetchError
    // with a `.data` payload shaped like {email: [...], password: [...]}.
    const data = (err as { data?: { email?: string[]; password?: string[] } })?.data
    if (data?.email?.length) {
      submitError.value = data.email[0]
    } else if (data?.password?.length) {
      submitError.value = data.password[0]
    } else {
      submitError.value = 'Registration failed. Try a different email or a stronger password.'
    }
  }
})
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-8">
    <UCard class="w-full max-w-md">
      <template #header>
        <h1 class="text-2xl font-semibold">Create an account</h1>
      </template>

      <form class="space-y-4" @submit="onSubmit">
        <UFormField label="Email" :error="errors.email" required>
          <UInput
            v-model="email"
            v-bind="emailAttrs"
            type="email"
            autocomplete="email"
            placeholder="you@example.com"
            class="w-full"
          />
        </UFormField>

        <UFormField
          label="Password"
          :error="errors.password"
          hint="At least 8 characters, with one letter and one digit."
          required
        >
          <UInput
            v-model="password"
            v-bind="passwordAttrs"
            type="password"
            autocomplete="new-password"
            class="w-full"
          />
        </UFormField>

        <p v-if="submitError" class="text-sm text-red-600">{{ submitError }}</p>

        <UButton type="submit" :disabled="isSubmitting" :loading="isSubmitting" block>
          Create account
        </UButton>
      </form>

      <template #footer>
        <p class="text-sm text-gray-600">
          Already have an account?
          <NuxtLink to="/login" class="underline">Sign in</NuxtLink>
        </p>
      </template>
    </UCard>
  </main>
</template>
