<script setup lang="ts">
// pages/dashboard/profile.vue
//
// Profile edit (PROF-01 + PROF-02 frontend half). Visual language
// mirrors the listing create/edit pages — same outer shell, same
// rounded-xl card styling, same input shapes, same footer button
// pattern, same character counter on the long-form field.
//
// Avatar upload is outside the validation form on purpose: the avatar
// is stored as a file reference, not a JSON field, and POSTs as
// multipart immediately on file pick. The text-fields form sends the
// ProfileSerializer JSON shape on Save.

import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import {
  profileSchema,
  AVATAR_MAX_BYTES,
  AVATAR_ACCEPT,
  type ProfileInput,
} from '~/schemas/profile'

definePageMeta({
  middleware: ['auth'],
})

const profileApi = useProfile()
const auth = useAuthStore()
const toast = useToast()

const { handleSubmit, errors, defineField, setValues, values, isSubmitting } = useForm({
  validationSchema: toTypedSchema(profileSchema),
  initialValues: {
    display_name: '',
    phone: '',
    bio: '',
  } as ProfileInput,
})

const [displayName, displayNameAttrs] = defineField('display_name')
const [phone, phoneAttrs] = defineField('phone')
const [bio, bioAttrs] = defineField('bio')

const displayNameRemaining = computed(() => 80 - String(displayName.value || '').length)
const bioRemaining = computed(() => 300 - String(bio.value || '').length)

const avatarUrl = ref<string | null>(null)
const avatarError = ref<string | null>(null)
const uploading = ref(false)

async function loadProfile() {
  try {
    const profile = await profileApi.fetchMyProfile()
    setValues({
      display_name: profile.display_name || '',
      phone: profile.phone || '',
      bio: profile.bio || '',
    })
    avatarUrl.value = profile.avatar
  } catch {
    // useAuthedApi handles 401 with a /login redirect; transient
    // failures the user can recover by reloading.
  }
}

// Client-only: SSR has no auth state, so the fetch would land
// without a Bearer token and fail.
onMounted(loadProfile)

const onSubmit = handleSubmit(async (val) => {
  try {
    await profileApi.updateMyProfile(val)
    toast.add({ title: 'Profile saved.' })
  } catch {
    toast.add({ title: 'Could not save profile.', color: 'error' })
  }
})

async function onAvatarSelected(event: Event) {
  avatarError.value = null
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > AVATAR_MAX_BYTES) {
    avatarError.value = 'Avatar must be at most 2 MB.'
    return
  }
  uploading.value = true
  try {
    const profile = await profileApi.uploadAvatar(file)
    avatarUrl.value = profile.avatar
    toast.add({ title: 'Avatar updated.' })
  } catch {
    avatarError.value = 'Upload failed. Try a JPEG, PNG, or WebP under 2 MB.'
  } finally {
    uploading.value = false
  }
}

const initial = computed(() => {
  const name = displayName.value || auth.user?.email || 'I'
  return name.charAt(0).toUpperCase()
})
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div class="max-w-3xl mx-auto px-6 py-10 space-y-8">
      <!-- Header -->
      <header class="space-y-2">
        <NuxtLink to="/dashboard/listings" class="text-sm text-gray-500 hover:text-gray-900">
          ← Dashboard
        </NuxtLink>
        <h1 class="text-3xl font-semibold tracking-tight">Profile</h1>
        <p class="text-sm text-gray-600">
          This is how you appear to renters and owners across Ijara. Public profile lives at
          <NuxtLink
            v-if="auth.user"
            :to="`/users/${auth.user.id}`"
            class="text-slate-700 underline underline-offset-2 hover:text-slate-900"
          >
            /users/{{ auth.user.id }} </NuxtLink
          >.
        </p>
      </header>

      <!-- Section indicator -->
      <div class="flex items-center gap-3 text-sm">
        <span class="flex items-center gap-2 text-gray-900 font-medium">
          <span
            class="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-medium"
          >
            1
          </span>
          Avatar
        </span>
        <span class="w-8 h-px bg-gray-300"></span>
        <span class="flex items-center gap-2 text-gray-900 font-medium">
          <span
            class="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-medium"
          >
            2
          </span>
          Details
        </span>
      </div>

      <!-- AVATAR -->
      <section class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="flex items-center gap-6">
          <div
            class="relative w-24 h-24 rounded-full bg-slate-200 overflow-hidden flex items-center justify-center text-slate-600 font-semibold text-3xl shrink-0"
          >
            <img
              v-if="avatarUrl"
              :src="avatarUrl"
              alt="Avatar"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ initial }}</span>
            <div
              v-if="uploading"
              class="absolute inset-0 bg-black/40 flex items-center justify-center"
            >
              <div
                class="w-6 h-6 border-2 border-white/40 border-t-white rounded-full animate-spin"
              />
            </div>
          </div>

          <div class="flex-1 space-y-2">
            <div>
              <p class="text-sm font-medium text-gray-800">Profile photo</p>
              <p class="text-xs text-gray-500 mt-0.5">
                JPEG, PNG, or WebP up to 2 MB. Resized to 256 × 256 on save.
              </p>
            </div>
            <label
              :class="[
                'inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm cursor-pointer transition',
                uploading
                  ? 'opacity-60 cursor-not-allowed'
                  : 'text-gray-700 hover:border-slate-900 hover:text-slate-900',
              ]"
            >
              <input
                type="file"
                :accept="AVATAR_ACCEPT"
                :disabled="uploading"
                class="sr-only"
                @change="onAvatarSelected"
              />
              <svg
                class="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {{ avatarUrl ? 'Replace photo' : 'Upload photo' }}
            </label>
            <p v-if="avatarError" class="text-sm text-red-600">{{ avatarError }}</p>
          </div>
        </div>
      </section>

      <!-- DETAILS -->
      <form class="rounded-xl border border-gray-200 bg-white p-6 space-y-6" @submit="onSubmit">
        <!-- Display name -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label for="display_name" class="text-sm font-medium text-gray-800">
              Display name
            </label>
            <span class="text-xs text-gray-400">{{ displayNameRemaining }} left</span>
          </div>
          <input
            id="display_name"
            v-model="displayName"
            v-bind="displayNameAttrs"
            type="text"
            maxlength="80"
            placeholder="The name renters and owners see"
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
          />
          <p class="text-xs text-gray-500">
            Real name works best for trust — it is shown next to your listings and bookings.
          </p>
          <span v-if="errors.display_name" class="block text-xs text-red-600">
            {{ errors.display_name }}
          </span>
        </div>

        <!-- Phone -->
        <div class="space-y-1.5">
          <label for="phone" class="text-sm font-medium text-gray-800">Phone</label>
          <input
            id="phone"
            v-model="phone"
            v-bind="phoneAttrs"
            type="tel"
            maxlength="20"
            inputmode="tel"
            placeholder="+998 90 123 45 67"
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
          />
          <p class="text-xs text-gray-500">
            Owners use this to coordinate handover. Visible only after a booking is accepted.
          </p>
          <span v-if="errors.phone" class="block text-xs text-red-600">
            {{ errors.phone }}
          </span>
        </div>

        <!-- Bio -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label for="bio" class="text-sm font-medium text-gray-800">Bio</label>
            <span class="text-xs text-gray-400">{{ bioRemaining }} left</span>
          </div>
          <textarea
            id="bio"
            v-model="bio"
            v-bind="bioAttrs"
            rows="4"
            maxlength="300"
            placeholder="A line or two about yourself — what you rent out, how to reach you, anything renters should know."
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-y"
          />
          <span v-if="errors.bio" class="block text-xs text-red-600">{{ errors.bio }}</span>
        </div>

        <!-- Email (read-only context) -->
        <div class="space-y-1.5">
          <p class="text-sm font-medium text-gray-800">Email</p>
          <p class="text-sm text-gray-700">{{ auth.user?.email }}</p>
          <p class="text-xs text-gray-500">Your sign-in address. Change is not yet supported.</p>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <NuxtLink
            v-if="auth.user"
            :to="`/users/${auth.user.id}`"
            class="text-xs text-gray-500 hover:text-gray-900 underline underline-offset-2"
          >
            Preview public profile
          </NuxtLink>
          <button
            type="submit"
            :disabled="isSubmitting"
            class="rounded-md bg-slate-900 text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="isSubmitting">Saving...</span>
            <span v-else>Save profile</span>
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
