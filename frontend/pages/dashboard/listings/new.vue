<script setup lang="ts">
// pages/dashboard/listings/new.vue
// Two-step create flow: details first, photos second.

import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const listingsApi = useListings()
const toast = useToast()

const title = ref('')
const description = ref('')
const category = ref('')
const district = ref('')
const price_hour = ref('')
const price_day = ref('')
const price_month = ref('')

const created = ref<any>(null)
const createError = ref<string | null>(null)
const creating = ref(false)

async function onCreate() {
  createError.value = null
  if (title.value.length < 3) {
    createError.value = 'Title must be at least 3 characters.'
    return
  }
  if (!category.value || !district.value) {
    createError.value = 'Pick a category and a district.'
    return
  }
  if (!price_hour.value && !price_day.value && !price_month.value) {
    createError.value = 'Set at least one price — hour, day, or month.'
    return
  }
  creating.value = true
  try {
    created.value = await listingsApi.createListing({
      title: title.value,
      description: description.value,
      category: category.value,
      district: district.value,
      price_hour: price_hour.value || null,
      price_day: price_day.value || null,
      price_month: price_month.value || null,
    })
    toast.add({ title: 'Listing created. Add photos below.' })
  } catch (err: unknown) {
    const data = (err as { data?: Record<string, string[]> })?.data
    if (data) {
      const firstKey = Object.keys(data)[0]
      createError.value = `${firstKey}: ${data[firstKey]?.[0] ?? 'invalid'}`
    } else {
      createError.value = 'Could not create the listing.'
    }
  } finally {
    creating.value = false
  }
}

const photos = ref<any[]>([])
const photoError = ref<string | null>(null)
const uploading = ref(false)

async function onPhotoSelected(event: Event) {
  if (!created.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  photoError.value = null
  uploading.value = true
  try {
    const photo = await listingsApi.uploadPhoto(created.value.id, file)
    photos.value.push(photo)
  } catch (err: unknown) {
    const data = (err as { data?: { photo?: string[] } })?.data
    photoError.value = data?.photo?.[0] ?? 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

const titleRemaining = computed(() => 80 - title.value.length)
const descriptionRemaining = computed(() => 2000 - description.value.length)
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div class="max-w-3xl mx-auto px-6 py-10 space-y-8">
      <!-- Header -->
      <header class="space-y-2">
        <NuxtLink to="/dashboard/listings" class="text-sm text-gray-500 hover:text-gray-900">
          ← My listings
        </NuxtLink>
        <h1 class="text-3xl font-semibold tracking-tight">
          {{ created ? 'Add photos' : 'List an item' }}
        </h1>
        <p class="text-sm text-gray-600">
          <template v-if="!created">
            Describe what you are renting out. You can edit every field later from your listings.
          </template>
          <template v-else>
            Your listing is live. Add a few photos so renters can see what they are getting.
          </template>
        </p>
      </header>

      <!-- Progress indicator -->
      <div class="flex items-center gap-3 text-sm">
        <span
          :class="[
            'flex items-center gap-2',
            !created ? 'text-gray-900 font-medium' : 'text-emerald-700',
          ]"
        >
          <span
            :class="[
              'w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium',
              !created ? 'bg-slate-900 text-white' : 'bg-emerald-500 text-white',
            ]"
          >
            <template v-if="!created">1</template>
            <template v-else>✓</template>
          </span>
          Details
        </span>
        <span class="w-8 h-px bg-gray-300"></span>
        <span
          :class="[
            'flex items-center gap-2',
            created ? 'text-gray-900 font-medium' : 'text-gray-400',
          ]"
        >
          <span
            :class="[
              'w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium',
              created ? 'bg-slate-900 text-white' : 'bg-gray-200 text-gray-500',
            ]"
          >
            2
          </span>
          Photos
        </span>
      </div>

      <!-- STEP 1: DETAILS -->
      <form
        v-if="!created"
        class="rounded-xl border border-gray-200 bg-white p-6 space-y-6"
        @submit.prevent="onCreate"
      >
        <!-- Title -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label for="title" class="text-sm font-medium text-gray-800">Title</label>
            <span class="text-xs text-gray-400">{{ titleRemaining }} left</span>
          </div>
          <input
            id="title"
            v-model="title"
            type="text"
            maxlength="80"
            placeholder="Dewalt 18V cordless drill set"
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
          />
          <p class="text-xs text-gray-500">A short, descriptive name. 3 to 80 characters.</p>
        </div>

        <!-- Description -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <label for="description" class="text-sm font-medium text-gray-800"> Description </label>
            <span class="text-xs text-gray-400">{{ descriptionRemaining }} left</span>
          </div>
          <textarea
            id="description"
            v-model="description"
            rows="5"
            maxlength="2000"
            placeholder="Model, condition, what's included, anything a renter should know..."
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-y"
          />
        </div>

        <!-- Category + District -->
        <div class="grid sm:grid-cols-2 gap-5">
          <div class="space-y-1.5">
            <label for="category" class="text-sm font-medium text-gray-800">Category</label>
            <div class="relative">
              <select
                id="category"
                v-model="category"
                class="appearance-none block w-full rounded-md border border-gray-300 bg-white pl-3 pr-9 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer"
              >
                <option value="">Pick one</option>
                <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">
                  {{ c.label }}
                </option>
              </select>
              <svg
                class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </div>
          </div>
          <div class="space-y-1.5">
            <label for="district" class="text-sm font-medium text-gray-800">District</label>
            <div class="relative">
              <select
                id="district"
                v-model="district"
                class="appearance-none block w-full rounded-md border border-gray-300 bg-white pl-3 pr-9 py-2.5 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900 cursor-pointer"
              >
                <option value="">Pick one</option>
                <option v-for="d in DISTRICTS" :key="d.value" :value="d.value">
                  {{ d.label }}
                </option>
              </select>
              <svg
                class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Pricing -->
        <div class="space-y-3">
          <div>
            <p class="text-sm font-medium text-gray-800">Pricing</p>
            <p class="text-xs text-gray-500 mt-0.5">
              Set at least one rate. Leave the others blank if you do not offer them.
            </p>
          </div>
          <div class="grid sm:grid-cols-3 gap-3">
            <div class="space-y-1">
              <label for="price_hour" class="text-xs text-gray-600">Per hour</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">
                  UZS
                </span>
                <input
                  id="price_hour"
                  v-model="price_hour"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="0"
                  class="block w-full rounded-md border border-gray-300 bg-white pl-12 pr-3 py-2.5 text-sm tabular-nums focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            </div>
            <div class="space-y-1">
              <label for="price_day" class="text-xs text-gray-600">Per day</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">
                  UZS
                </span>
                <input
                  id="price_day"
                  v-model="price_day"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="0"
                  class="block w-full rounded-md border border-gray-300 bg-white pl-12 pr-3 py-2.5 text-sm tabular-nums focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            </div>
            <div class="space-y-1">
              <label for="price_month" class="text-xs text-gray-600">Per month</label>
              <div class="relative">
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">
                  UZS
                </span>
                <input
                  id="price_month"
                  v-model="price_month"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="0"
                  class="block w-full rounded-md border border-gray-300 bg-white pl-12 pr-3 py-2.5 text-sm tabular-nums focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Error -->
        <p
          v-if="createError"
          class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ createError }}
        </p>

        <!-- Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <p class="text-xs text-gray-500">Renters can message you after they request a booking.</p>
          <button
            type="submit"
            :disabled="creating"
            class="rounded-md bg-slate-900 text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="creating">Publishing...</span>
            <span v-else>Publish listing</span>
          </button>
        </div>
      </form>

      <!-- STEP 2: PHOTOS -->
      <section v-else class="space-y-5">
        <div
          class="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 flex items-start gap-3"
        >
          <div
            class="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center shrink-0 text-sm"
          >
            ✓
          </div>
          <div>
            <p class="text-sm font-medium text-emerald-900">Listing published</p>
            <p class="text-xs text-emerald-800 mt-0.5">
              Add up to 8 photos so renters can see what they are getting.
            </p>
          </div>
        </div>

        <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-gray-800">Photos</p>
            <p class="text-xs text-gray-500">
              {{ photos.length }} / 8 · JPEG, PNG, WebP, up to 5 MB each
            </p>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div
              v-for="(p, i) in photos"
              :key="p.id"
              class="relative aspect-square rounded-lg border border-gray-200 overflow-hidden bg-gray-100"
            >
              <img :src="p.image" class="w-full h-full object-cover" />
              <span
                v-if="i === 0"
                class="absolute top-2 left-2 rounded-md bg-slate-900 text-white text-[10px] px-2 py-0.5 font-medium"
              >
                Cover
              </span>
            </div>

            <label
              v-if="photos.length < 8"
              :class="[
                'aspect-square rounded-lg border-2 border-dashed flex flex-col items-center justify-center gap-2 text-sm transition',
                uploading
                  ? 'border-gray-300 text-gray-400'
                  : 'border-gray-300 text-gray-500 cursor-pointer hover:border-slate-900 hover:text-slate-900 hover:bg-slate-50',
              ]"
            >
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                class="sr-only"
                :disabled="uploading"
                @change="onPhotoSelected"
              />
              <template v-if="uploading">
                <div
                  class="w-6 h-6 border-2 border-gray-300 border-t-slate-900 rounded-full animate-spin"
                />
                <span class="text-xs">Uploading</span>
              </template>
              <template v-else>
                <svg
                  class="w-6 h-6"
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
                <span class="text-xs font-medium">Add photo</span>
              </template>
            </label>
          </div>

          <p v-if="photoError" class="text-sm text-red-600">{{ photoError }}</p>
        </div>

        <div class="flex gap-3 justify-end pt-2">
          <NuxtLink
            to="/dashboard/listings"
            class="rounded-md border border-gray-300 bg-white text-sm text-gray-700 px-4 py-2.5 hover:bg-gray-50 transition"
          >
            Finish later
          </NuxtLink>
          <NuxtLink
            :to="`/listings/${created.id}`"
            class="rounded-md bg-slate-900 text-white text-sm px-5 py-2.5 hover:bg-slate-800 transition"
          >
            View public page →
          </NuxtLink>
        </div>
      </section>
    </div>
  </main>
</template>
