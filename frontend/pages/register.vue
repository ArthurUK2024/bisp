<script setup lang="ts">
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

const showPassword = ref(false)
const submitError = ref<string | null>(null)

const onSubmit = handleSubmit(async (values) => {
  submitError.value = null
  try {
    await auth.register(values)
    await auth.login(values)
    await navigateTo('/dashboard/profile')
  } catch (err: unknown) {
    const data = (err as { data?: { email?: string[]; password?: string[] } })?.data
    if (data?.email?.length) {
      submitError.value = data.email[0]
    } else if (data?.password?.length) {
      submitError.value = data.password[0]
    } else {
      submitError.value =
        'Could not finish registration. Try a different email, or pick a stronger password.'
    }
  }
})
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] flex items-center justify-center p-6 bg-white">
    <section class="w-full max-w-md">
      <div class="w-full space-y-8">
        <div class="space-y-2">
          <h1 class="text-3xl font-semibold tracking-tight">Make an account</h1>
          <p class="text-sm text-gray-600">
            Takes about a minute. You can add your name and phone number after.
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
              <button
                type="button"
                class="text-xs text-gray-500 hover:text-gray-800 underline-offset-2 hover:underline"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? 'Hide' : 'Show' }}
              </button>
            </div>
            <input
              v-model="password"
              v-bind="passwordAttrs"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="new-password"
              placeholder="At least 8 characters"
              class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            <span class="block text-xs text-gray-500"> Mix letters and numbers, please. </span>
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
            <span v-if="isSubmitting">Creating account...</span>
            <span v-else>Create account</span>
          </button>
        </form>

        <div class="relative">
          <div class="absolute inset-0 flex items-center">
            <div class="w-full border-t border-gray-200" />
          </div>
          <div class="relative flex justify-center">
            <span class="bg-white px-2 text-xs uppercase tracking-wider text-gray-400">
              Already a member?
            </span>
          </div>
        </div>

        <NuxtLink
          to="/login"
          class="block w-full text-center rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
        >
          Sign in instead
        </NuxtLink>

        <p class="text-xs text-center text-gray-400">
          By creating an account you agree to the community guidelines.
        </p>
      </div>
    </section>
  </main>
</template>
