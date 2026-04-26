<script setup lang="ts">
import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const listingsApi = useListings()
const toast = useToast()

const MAX_PHOTOS = 8
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 5 * 1024 * 1024

type StagedPhoto = {
  file: File
  url: string
}

const step = ref<1 | 2>(1)

const photos = ref<StagedPhoto[]>([])
const photoError = ref<string | null>(null)
const dragActive = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const title = ref('')
const description = ref('')
const category = ref('')
const district = ref('')
const price_hour = ref('')
const price_day = ref('')
const price_month = ref('')

const aiBusy = ref(false)
const aiUsed = ref(false)
const aiError = ref<string | null>(null)
const submitError = ref<string | null>(null)
const submitting = ref(false)

const titleRemaining = computed(() => 80 - title.value.length)
const descriptionRemaining = computed(() => 2000 - description.value.length)

function addFiles(files: FileList | File[]) {
  photoError.value = null
  const list = Array.from(files)
  for (const file of list) {
    if (photos.value.length >= MAX_PHOTOS) {
      photoError.value = `You can attach up to ${MAX_PHOTOS} photos.`
      break
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      photoError.value = 'Only JPEG, PNG, or WebP images are accepted.'
      continue
    }
    if (file.size > MAX_BYTES) {
      photoError.value = `${file.name} is over 5 MB.`
      continue
    }
    photos.value.push({ file, url: URL.createObjectURL(file) })
  }
}

function onFilesPicked(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) addFiles(input.files)
  input.value = ''
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  dragActive.value = false
  if (event.dataTransfer?.files?.length) addFiles(event.dataTransfer.files)
}

function removePhoto(idx: number) {
  const removed = photos.value.splice(idx, 1)[0]
  if (removed) URL.revokeObjectURL(removed.url)
}

onBeforeUnmount(() => {
  for (const p of photos.value) URL.revokeObjectURL(p.url)
})

async function runAISuggestion() {
  if (!photos.value.length) return
  aiBusy.value = true
  aiError.value = null
  try {
    const suggestion = await listingsApi.aiSuggestFromPhotos(photos.value.map((p) => p.file))
    if (suggestion.title) title.value = suggestion.title
    if (suggestion.description) description.value = suggestion.description
    if (suggestion.category) category.value = suggestion.category
    if (suggestion.price_hour) price_hour.value = String(suggestion.price_hour)
    if (suggestion.price_day) price_day.value = String(suggestion.price_day)
    if (suggestion.price_month) price_month.value = String(suggestion.price_month)
    aiUsed.value = true
  } catch (err: unknown) {
    const status = (err as { statusCode?: number; status?: number })?.statusCode
    const data = (err as { data?: { detail?: string } })?.data
    if (status === 503) {
      aiError.value =
        data?.detail || 'AI suggestions are not available right now. Please fill the form manually.'
    } else {
      aiError.value = 'Could not analyse the photos. Please fill the form manually.'
    }
  } finally {
    aiBusy.value = false
  }
}

async function continueWithPhotos() {
  step.value = 2
  await runAISuggestion()
}

function skipPhotos() {
  for (const p of photos.value) URL.revokeObjectURL(p.url)
  photos.value = []
  step.value = 2
}

function goBackToPhotos() {
  step.value = 1
}

async function onSubmit() {
  submitError.value = null
  if (title.value.trim().length < 3) {
    submitError.value = 'Title must be at least 3 characters.'
    return
  }
  if (!category.value || !district.value) {
    submitError.value = 'Pick a category and a district.'
    return
  }
  if (!price_hour.value && !price_day.value && !price_month.value) {
    submitError.value = 'Set at least one price — hour, day, or month.'
    return
  }
  submitting.value = true
  try {
    const created = await listingsApi.createListing({
      title: title.value.trim(),
      description: description.value.trim(),
      category: category.value,
      district: district.value,
      price_hour: price_hour.value || null,
      price_day: price_day.value || null,
      price_month: price_month.value || null,
    })

    let uploadedCount = 0
    for (const p of photos.value) {
      try {
        await listingsApi.uploadPhoto(created.id, p.file)
        uploadedCount += 1
      } catch {
        // ignore individual photo failures
      }
    }
    toast.add({
      title: photos.value.length
        ? `Listing published with ${uploadedCount} photo${uploadedCount === 1 ? '' : 's'}.`
        : 'Listing published.',
    })
    await navigateTo(`/listings/${created.id}`)
  } catch (err: unknown) {
    const data = (err as { data?: Record<string, string[]> })?.data
    if (data) {
      const firstKey = Object.keys(data)[0]
      submitError.value = `${firstKey}: ${data[firstKey]?.[0] ?? 'invalid'}`
    } else {
      submitError.value = 'Could not publish the listing.'
    }
  } finally {
    submitting.value = false
  }
}
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
          {{ step === 1 ? 'Add photos' : 'Listing details' }}
        </h1>
        <p class="text-sm text-gray-600">
          <template v-if="step === 1">
            Drop a few photos of the item. We can suggest a title, description, and price for you
            when you continue.
          </template>
          <template v-else-if="aiBusy">
            One moment — looking at your photos to draft the listing for you.
          </template>
          <template v-else>
            Review the fields and edit anything that needs changing before publishing.
          </template>
        </p>
      </header>

      <!-- Stepper -->
      <div class="flex items-center gap-3 text-sm">
        <span
          :class="[
            'flex items-center gap-2',
            step === 1 ? 'text-gray-900 font-medium' : 'text-emerald-700',
          ]"
        >
          <span
            :class="[
              'w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium',
              step === 1 ? 'bg-slate-900 text-white' : 'bg-emerald-500 text-white',
            ]"
          >
            <template v-if="step === 1">1</template>
            <template v-else>✓</template>
          </span>
          Photos
        </span>
        <span class="w-8 h-px bg-gray-300"></span>
        <span
          :class="[
            'flex items-center gap-2',
            step === 2 ? 'text-gray-900 font-medium' : 'text-gray-400',
          ]"
        >
          <span
            :class="[
              'w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium',
              step === 2 ? 'bg-slate-900 text-white' : 'bg-gray-200 text-gray-500',
            ]"
          >
            2
          </span>
          Details
        </span>
      </div>

      <!-- STEP 1: PHOTOS -->
      <section v-if="step === 1" class="space-y-5">
        <div
          :class="[
            'rounded-xl border-2 border-dashed bg-white p-8 transition',
            dragActive ? 'border-slate-900 bg-slate-50' : 'border-gray-300',
          ]"
          @dragover.prevent="dragActive = true"
          @dragenter.prevent="dragActive = true"
          @dragleave.prevent="dragActive = false"
          @drop="onDrop"
        >
          <div class="flex flex-col items-center text-center gap-3">
            <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
              <svg
                class="w-6 h-6 text-gray-500"
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
            </div>
            <div class="space-y-1">
              <p class="text-sm font-medium text-gray-900">Drop photos here</p>
              <p class="text-xs text-gray-500">JPEG, PNG, or WebP · up to 8 photos · 5 MB each</p>
            </div>
            <button
              type="button"
              class="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50 transition"
              @click="fileInput?.click()"
            >
              Choose files
            </button>
            <input
              ref="fileInput"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              class="sr-only"
              @change="onFilesPicked"
            />
          </div>
        </div>

        <div v-if="photos.length" class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-gray-800">
              {{ photos.length }} photo<span v-if="photos.length !== 1">s</span> staged
            </p>
            <p class="text-xs text-gray-500">First photo becomes the cover</p>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div
              v-for="(p, i) in photos"
              :key="p.url"
              class="relative aspect-square rounded-lg border border-gray-200 overflow-hidden bg-gray-100 group"
            >
              <img :src="p.url" class="w-full h-full object-cover" />
              <span
                v-if="i === 0"
                class="absolute top-2 left-2 rounded-md bg-slate-900 text-white text-[10px] px-2 py-0.5 font-medium"
              >
                Cover
              </span>
              <button
                type="button"
                class="absolute top-2 right-2 w-6 h-6 rounded-full bg-white/90 backdrop-blur text-gray-800 text-sm leading-none hover:bg-white opacity-0 group-hover:opacity-100 transition"
                aria-label="Remove photo"
                @click="removePhoto(i)"
              >
                ×
              </button>
            </div>
          </div>
        </div>

        <p v-if="photoError" class="text-sm text-red-600">{{ photoError }}</p>

        <div
          class="flex flex-col-reverse sm:flex-row sm:justify-between sm:items-center gap-3 pt-2"
        >
          <button
            type="button"
            class="text-sm text-gray-600 hover:text-gray-900 underline-offset-2 hover:underline"
            @click="skipPhotos"
          >
            Skip — enter details manually
          </button>
          <button
            type="button"
            :disabled="!photos.length"
            class="rounded-md bg-slate-900 text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
            @click="continueWithPhotos"
          >
            <svg
              class="w-4 h-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M9.5 2 8 5.5 4.5 7 8 8.5 9.5 12 11 8.5 14.5 7 11 5.5z" />
              <path d="M18 13l-1 2-2 1 2 1 1 2 1-2 2-1-2-1z" />
            </svg>
            <span v-if="photos.length"
              >Continue with {{ photos.length }} photo<span v-if="photos.length !== 1"
                >s</span
              ></span
            >
            <span v-else>Add photos to continue</span>
          </button>
        </div>
      </section>

      <!-- STEP 2: DETAILS -->
      <form
        v-else
        class="rounded-xl border border-gray-200 bg-white p-6 space-y-6"
        @submit.prevent="onSubmit"
      >
        <!-- AI status banner -->
        <div
          v-if="aiBusy"
          class="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 flex items-center gap-3"
        >
          <div
            class="w-5 h-5 border-2 border-slate-300 border-t-slate-900 rounded-full animate-spin"
          />
          <p class="text-sm text-slate-800">
            Analysing {{ photos.length }} photo<span v-if="photos.length !== 1">s</span> to draft
            your listing…
          </p>
        </div>
        <div
          v-else-if="aiUsed"
          class="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 space-y-1"
        >
          <p class="text-sm font-medium text-emerald-900">Draft filled from your photos.</p>
          <p class="text-xs text-emerald-800">
            Please review every field and edit anything that does not match. We picked the price as
            a rough guide — adjust to your usual rate.
          </p>
        </div>
        <div
          v-else-if="aiError"
          class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {{ aiError }}
        </div>

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
            <label for="description" class="text-sm font-medium text-gray-800">Description</label>
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
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
                  >UZS</span
                >
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
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
                  >UZS</span
                >
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
                <span class="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-500"
                  >UZS</span
                >
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

        <!-- Photo summary -->
        <div
          v-if="photos.length"
          class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 flex items-center gap-3"
        >
          <div class="flex -space-x-2">
            <img
              v-for="(p, i) in photos.slice(0, 4)"
              :key="p.url"
              :src="p.url"
              :class="[
                'w-10 h-10 rounded-md object-cover border-2 border-white',
                i > 0 ? 'shadow-sm' : '',
              ]"
            />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs text-gray-700">
              {{ photos.length }} photo<span v-if="photos.length !== 1">s</span> ready to upload
              after publishing.
            </p>
          </div>
          <button
            type="button"
            class="text-xs text-gray-500 hover:text-gray-900 underline-offset-2 hover:underline whitespace-nowrap"
            @click="goBackToPhotos"
          >
            Edit photos
          </button>
        </div>

        <!-- Error -->
        <p
          v-if="submitError"
          class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ submitError }}
        </p>

        <!-- Footer -->
        <div class="flex items-center justify-between pt-2 border-t border-gray-100">
          <button
            type="button"
            class="text-sm text-gray-600 hover:text-gray-900 underline-offset-2 hover:underline"
            @click="goBackToPhotos"
          >
            ← Back to photos
          </button>
          <button
            type="submit"
            :disabled="submitting || aiBusy"
            class="rounded-md bg-slate-900 text-white px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <span v-if="submitting">Publishing…</span>
            <span v-else>Publish listing</span>
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
