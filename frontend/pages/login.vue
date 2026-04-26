<script setup lang="ts">
// pages/login.vue
// Sign-in page. Simple email + password form posting through the Pinia
// auth store. On success, read ?next=... and navigate there.

import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { loginSchema } from '~/schemas/auth'

definePageMeta({
  middleware: [],
})

const route = useRoute()
const auth = useAuthStore()

const { handleSubmit, errors, defineField, isSubmitting } = useForm({
  validationSchema: toTypedSchema(loginSchema),
})

const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')

const submitError = ref<string | null>(null)

const onSubmit = handleSubmit(async (values) => {
  submitError.value = null
  try {
    await auth.login(values)
    const next = (route.query.next as string) || '/dashboard/profile'
    await navigateTo(next)
  } catch {
    submitError.value =
      'Those credentials did not match. Check your email and password and try again.'
  }
})
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-6 bg-white">
    <section class="w-full max-w-md">
      <div class="w-full space-y-8">
        <div class="space-y-2">
          <h1 class="text-3xl font-semibold tracking-tight">Sign in</h1>
          <p class="text-sm text-gray-600">
            Good to see you again. Enter your email and password to continue.
          </p>
        </div>

        <form class="space-y-5" @submit="onSubmit">
          <label class="block space-y-1">
            <span class="text-sm font-medium text-gray-800">Email</span>
            <input
              v-model="email"
              v-bind="emailAttrs"
              type="email"
              autocomplete="email"
              placeholder="you@example.com"
              class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <span v-if="errors.email" class="block text-xs text-red-600">{{ errors.email }}</span>
          </label>

          <label class="block space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-800">Password</span>
              <span class="text-xs text-gray-400">Min 8 characters</span>
            </div>
            <input
              v-model="password"
              v-bind="passwordAttrs"
              type="password"
              autocomplete="current-password"
              placeholder="••••••••"
              class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <span v-if="errors.password" class="block text-xs text-red-600">{{
              errors.password
            }}</span>
          </label>

          <p
            v-if="submitError"
            class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {{ submitError }}
          </p>

          <button
            type="submit"
            :disabled="isSubmitting"
            class="w-full rounded-md bg-slate-900 text-white px-4 py-3 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span v-if="isSubmitting">Signing in...</span>
            <span v-else>Sign in</span>
          </button>
        </form>

        <div class="relative">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-gray-200" />
          </div>
          <div class="relative flex justify-center">
            <span class="bg-white px-2 text-xs uppercase tracking-wider text-gray-400">
              New to Ijara?
            </span>
          </div>
        </div>

        <NuxtLink
          to="/register"
          class="block w-full text-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
        >
          Create an account
        </NuxtLink>

        <p class="text-xs text-center text-gray-400">
          By signing in you agree to the community guidelines.
        </p>
      </div>
    </section>
  </main>
</template>
