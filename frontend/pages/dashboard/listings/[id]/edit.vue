<script setup lang="ts">
// pages/dashboard/listings/[id]/edit.vue
// Owner edit form. Visual language mirrors pages/dashboard/listings/new.vue
// so the create-vs-edit flow feels like the same surface — same card
// styling, same custom selects, same UZS-prefixed pricing inputs, same
// character counters, same footer button group. Photos section stays
// inline (no two-step indicator) because edit is single-screen.

import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const route = useRoute()
const auth = useAuthStore()
const toast = useToast()
const { fetchListing, updateListing, uploadPhoto, deletePhoto } = useListings()

const listing = ref<any>(null)
const loadError = ref<string | null>(null)

// Form fields start empty — populated by load() once the listing arrives.
const title = ref('')
const description = ref('')
const category = ref('')
const district = ref('')
const price_hour = ref<string | number>('')
const price_day = ref<string | number>('')
const price_month = ref<string | number>('')

const titleRemaining = computed(() => 80 - String(title.value).length)
const descriptionRemaining = computed(() => 2000 - String(description.value).length)

async function load() {
  try {
    listing.value = await fetchListing(route.params.id as string)
  } catch {
    loadError.value = 'Could not load listing.'
    return
  }
  if (listing.value.owner_id !== auth.user?.id) {
    await navigateTo(`/listings/${listing.value.id}`, { replace: true })
    return
  }
  title.value = listing.value.title
  description.value = listing.value.description
  category.value = listing.value.category
  district.value = listing.value.district
  price_hour.value = listing.value.price_hour ?? ''
  price_day.value = listing.value.price_day ?? ''
  price_month.value = listing.value.price_month ?? ''
}

// Client-only: SSR has no auth state (cookie is HttpOnly + Path=/api/auth/),
// so an SSR fetch would be anonymous and produce a hydration mismatch.
onMounted(load)

const saving = ref(false)
const saveError = ref<string | null>(null)

async function onSave() {
  saveError.value = null
  if (String(title.value).length < 3) {
    saveError.value = 'Title must be at least 3 characters.'
    return
  }
  if (!category.value || !district.value) {
    saveError.value = 'Pick a category and a district.'
    return
  }
  if (!price_hour.value && !price_day.value && !price_month.value) {
    saveError.value = 'Set at least one price — hour, day, or month.'
    return
  }
  saving.value = true
  try {
    listing.value = await updateListing(listing.value.id, {
      title: title.value,
      description: description.value,
      category: category.value,
      district: district.value,
      price_hour: price_hour.value || null,
      price_day: price_day.value || null,
      price_month: price_month.value || null,
    })
    toast.add({ title: 'Listing updated.' })
  } catch (err: any) {
    const data = err?.data
    if (data && typeof data === 'object') {
      const firstKey = Object.keys(data)[0]
      saveError.value = `${firstKey}: ${data[firstKey]?.[0] ?? 'invalid'}`
    } else {
      saveError.value = 'Could not save changes.'
    }
  } finally {
    saving.value = false
  }
}

const uploading = ref(false)
const photoError = ref<string | null>(null)

async function onPhotoSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  photoError.value = null
  uploading.value = true
  try {
    const photo = await uploadPhoto(listing.value.id, file)
    listing.value.photos.push(photo)
  } catch (err: any) {
    photoError.value = err?.data?.photo?.[0] ?? 'Upload failed.'
  } finally {
    uploading.value = false
  }
}

async function onDeletePhoto(photoId: number) {
  if (!confirm('Remove this photo?')) return
  try {
    await deletePhoto(listing.value.id, photoId)
    listing.value.photos = listing.value.photos.filter((p: any) => p.id !== photoId)
  } catch {
    toast.add({ title: 'Could not delete photo.', color: 'error' })
  }
}
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div v-if="loadError" class="max-w-xl mx-auto py-20 text-center space-y-3">
      <p class="text-2xl">🔍</p>
      <h1 class="text-xl font-semibold">Listing not found</h1>
      <NuxtLink
        to="/dashboard/listings"
        class="inline-block rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
      >
        ← Back to my listings
      </NuxtLink>
    </div>

    <div v-else-if="listing" class="max-w-3xl mx-auto px-6 py-10 space-y-8">
      <!-- Header -->
      <header class="space-y-2">
        <NuxtLink to="/dashboard/listings" class="text-sm text-gray-500 hover:text-gray-900">
          ← My listings
        </NuxtLink>
        <h1 class="text-3xl font-semibold tracking-tight">Edit listing</h1>
        <p class="text-sm text-gray-600">
          Update what you are renting out. Changes go live immediately; existing bookings keep their
          original price.
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
          Details
        </span>
        <span class="w-8 h-px bg-gray-300"></span>
        <span class="flex items-center gap-2 text-gray-900 font-medium">
          <span
            class="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-medium"
          >
            2
          </span>
          Photos
        </span>
      </div>

      <!-- DETAILS -->
      <form
        class="rounded-xl border border-gray-200 bg-white p-6 space-y-6"
        @submit.prevent="onSave"
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
          v-if="saveError"
          class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ saveError }}
        </p>

        <!-- Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <NuxtLink
            :to="`/listings/${listing.id}`"
            class="text-xs text-gray-500 hover:text-gray-900 underline underline-offset-2"
          >
            View public page
          </NuxtLink>
          <button
            type="submit"
            :disabled="saving"
            class="rounded-md bg-slate-900 text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="saving">Saving...</span>
            <span v-else>Save changes</span>
          </button>
        </div>
      </form>

      <!-- PHOTOS -->
      <section class="space-y-5">
        <div class="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-gray-800">Photos</p>
            <p class="text-xs text-gray-500">
              {{ listing.photos.length }} / 8 · JPEG, PNG, WebP, up to 5 MB each
            </p>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div
              v-for="(p, i) in listing.photos"
              :key="p.id"
              class="relative aspect-square rounded-lg border border-gray-200 overflow-hidden bg-gray-100 group"
            >
              <img :src="p.image" class="w-full h-full object-cover" />
              <span
                v-if="i === 0"
                class="absolute top-2 left-2 rounded-md bg-slate-900 text-white text-[10px] px-2 py-0.5 font-medium"
              >
                Cover
              </span>
              <button
                type="button"
                class="absolute top-2 right-2 rounded-full bg-black/60 text-white text-xs px-2 py-1 opacity-0 group-hover:opacity-100 transition"
                @click="onDeletePhoto(p.id)"
              >
                Remove
              </button>
            </div>

            <label
              v-if="listing.photos.length < 8"
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

        <div class="flex justify-end">
          <NuxtLink
            to="/dashboard/listings"
            class="rounded-md border border-gray-300 bg-white text-sm text-gray-700 px-4 py-2.5 hover:bg-gray-50 transition"
          >
            Done
          </NuxtLink>
        </div>
      </section>
    </div>
  </main>
</template>
