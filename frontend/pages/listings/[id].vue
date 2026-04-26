<script setup lang="ts">
// pages/listings/[id].vue
// Listing detail page with gallery, booking card, and owner block.

import { CATEGORIES, DISTRICTS, useListings } from '~/composables/useListings'
import {
  tashkentISO,
  useBookings,
  type PaymentMethod,
  type PriceQuote,
} from '~/composables/useBookings'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const { fetchListing } = useListings()
const bookingsApi = useBookings()

const { data: listing, error } = await useAsyncData(`listing-${route.params.id}`, () =>
  fetchListing(route.params.id as string),
)

// Gallery state -- user clicks a thumb to swap the hero.
const activePhotoIndex = ref(0)
const activePhoto = computed(() => listing.value?.photos?.[activePhotoIndex.value] ?? null)

// Is the current user the owner of this listing? Hide the booking form
// and show a "manage your listing" panel instead.
const isOwner = computed(() => auth.isAuthed && auth.user?.id === listing.value?.owner_id)

// Booking form state. datetime-local inputs; we attach +05:00 (Asia/Tashkent)
// when sending to the API and ask the backend for the authoritative quote.
const startAt = ref('')
const endAt = ref('')
const paymentMethod = ref<PaymentMethod>('cash')
const note = ref('')
const bookingError = ref<string | null>(null)
const booking = ref(false)

function defaultLocal(offsetHours: number): string {
  const d = new Date(Date.now() + offsetHours * 3600_000)
  d.setMinutes(0, 0, 0)
  // Render in Tashkent local time as YYYY-MM-DDTHH:MM for the input.
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tashkent',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(d)
  const get = (t: string) => fmt.find((p) => p.type === t)?.value ?? '00'
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
}

onMounted(() => {
  if (!startAt.value) startAt.value = defaultLocal(24)
  if (!endAt.value) endAt.value = defaultLocal(48)
})

const minLocal = computed(() => defaultLocal(0))

const quote = ref<PriceQuote | null>(null)
const quoteError = ref<string | null>(null)
let quoteSeq = 0

watch([startAt, endAt], async ([s, e]) => {
  quote.value = null
  quoteError.value = null
  if (!listing.value || !s || !e) return
  const seq = ++quoteSeq
  try {
    const q = await bookingsApi.quote(listing.value.id, tashkentISO(s), tashkentISO(e))
    if (seq === quoteSeq) quote.value = q
  } catch (err: any) {
    if (seq !== quoteSeq) return
    const data = err?.data
    quoteError.value = data
      ? (data[Object.keys(data)[0]]?.[0] ?? 'Could not price these dates.')
      : 'Could not price these dates.'
  }
})

async function onBook() {
  bookingError.value = null
  if (!auth.isAuthed) {
    await navigateTo('/login?next=' + encodeURIComponent(route.fullPath))
    return
  }
  if (!startAt.value || !endAt.value) {
    bookingError.value = 'Pick both a start and end time.'
    return
  }
  booking.value = true
  try {
    await bookingsApi.createBooking({
      listing: listing.value!.id,
      start_at: tashkentISO(startAt.value),
      end_at: tashkentISO(endAt.value),
      payment_method: paymentMethod.value,
      note: note.value,
    })
    toast.add({ title: 'Booking sent. Waiting for the owner.' })
    await router.push(`/dashboard/bookings`)
  } catch (err: any) {
    const data = err?.data
    if (data && typeof data === 'object') {
      const firstKey = Object.keys(data)[0]
      bookingError.value = Array.isArray(data[firstKey])
        ? data[firstKey][0]
        : String(data[firstKey])
    } else {
      bookingError.value = 'Could not create booking.'
    }
  } finally {
    booking.value = false
  }
}

function fmtPrice(price: string | null): string {
  if (price == null) return '—'
  return Number(price).toLocaleString('en-US')
}

// Headline price for the booking widget — shows the most common unit
// the listing supports (day → hour → month). Lets the renter scan the
// rate before committing to a date window.
const headline = computed<{ amount: string; unit: string } | null>(() => {
  if (!listing.value) return null
  if (listing.value.price_day) return { amount: listing.value.price_day, unit: 'day' }
  if (listing.value.price_hour) return { amount: listing.value.price_hour, unit: 'hour' }
  if (listing.value.price_month) return { amount: listing.value.price_month, unit: 'month' }
  return null
})

const otherRates = computed<string[]>(() => {
  if (!listing.value || !headline.value) return []
  const out: string[] = []
  if (headline.value.unit !== 'hour' && listing.value.price_hour) {
    out.push(`UZS ${fmtPrice(listing.value.price_hour)}/h`)
  }
  if (headline.value.unit !== 'day' && listing.value.price_day) {
    out.push(`UZS ${fmtPrice(listing.value.price_day)}/d`)
  }
  if (headline.value.unit !== 'month' && listing.value.price_month) {
    out.push(`UZS ${fmtPrice(listing.value.price_month)}/mo`)
  }
  return out
})

// "Add a note" reveals the textarea on click — keeps the default form
// shape compact for the common case where there's nothing extra to say.
const noteOpen = ref(false)

function unitLabel(unit: string, qty: number): string {
  const map: Record<string, [string, string]> = {
    hour: ['hour', 'hours'],
    day: ['day', 'days'],
    month: ['month', 'months'],
  }
  const [singular, plural] = map[unit] ?? [unit, unit + 's']
  return qty === 1 ? singular : plural
}

function categoryLabel(value: string): string {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value
}

function districtLabel(value: string): string {
  return DISTRICTS.find((d) => d.value === value)?.label ?? value
}

const categoryIcons: Record<string, string> = {
  tools: '🔧',
  electronics: '📷',
  event_gear: '🎪',
  sports: '⛷️',
  furniture: '🪑',
  vehicles: '🚗',
  other: '📦',
}

const daysSinceCreated = computed(() => {
  if (!listing.value) return 0
  const created = new Date(listing.value.created_at)
  const diff = Date.now() - created.getTime()
  return Math.max(1, Math.floor(diff / 86400000))
})
</script>

<template>
  <div v-if="error" class="max-w-xl mx-auto p-16 text-center space-y-4">
    <div class="text-5xl">🔍</div>
    <h1 class="text-2xl font-semibold">Listing not found</h1>
    <p class="text-gray-600">This listing was removed or never existed.</p>
    <NuxtLink
      to="/listings"
      class="inline-block rounded-md border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
    >
      ← Back to browse
    </NuxtLink>
  </div>

  <div v-else-if="listing" class="bg-white">
    <!-- Breadcrumb strip ------------------------------------------------->
    <nav class="max-w-6xl mx-auto px-6 pt-6 text-xs text-gray-500 flex items-center gap-1.5">
      <NuxtLink to="/" class="hover:text-gray-900">Home</NuxtLink>
      <span>/</span>
      <NuxtLink to="/listings" class="hover:text-gray-900">Browse</NuxtLink>
      <span>/</span>
      <NuxtLink :to="`/listings?category=${listing.category}`" class="hover:text-gray-900">
        {{ categoryLabel(listing.category) }}
      </NuxtLink>
      <span>/</span>
      <span class="text-gray-900 truncate">{{ listing.title }}</span>
    </nav>

    <!-- Header ------------------------------------------------------------>
    <header class="max-w-6xl mx-auto px-6 pt-4 pb-6 space-y-3">
      <h1 class="text-3xl md:text-4xl font-semibold tracking-tight">{{ listing.title }}</h1>
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-slate-700"
        >
          <span>{{ categoryIcons[listing.category] ?? '📦' }}</span>
          {{ categoryLabel(listing.category) }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-slate-700"
        >
          <span>📍</span>
          {{ districtLabel(listing.district) }}
        </span>
        <span class="text-gray-500"
          >Listed {{ daysSinceCreated }} day{{ daysSinceCreated === 1 ? '' : 's' }} ago</span
        >
      </div>
    </header>

    <!-- Gallery ----------------------------------------------------------->
    <section class="max-w-6xl mx-auto px-6">
      <div
        v-if="listing.photos.length"
        class="grid grid-cols-4 grid-rows-2 gap-2 h-[420px] rounded-xl overflow-hidden"
      >
        <div class="col-span-2 row-span-2 bg-gray-100 relative">
          <img
            v-if="activePhoto"
            :src="activePhoto.image"
            :alt="listing.title"
            class="w-full h-full object-cover"
          />
        </div>
        <button
          v-for="(p, i) in listing.photos.slice(0, 4)"
          :key="p.id"
          type="button"
          :class="[
            'bg-gray-100 overflow-hidden relative group transition',
            i === activePhotoIndex ? 'ring-2 ring-slate-900' : '',
          ]"
          @click="activePhotoIndex = i"
        >
          <img
            :src="p.image"
            :alt="`${listing.title} photo ${i + 1}`"
            class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        </button>
        <template v-if="listing.photos.length < 4">
          <div
            v-for="n in 4 - listing.photos.length"
            :key="`empty-${n}`"
            class="bg-gray-50 flex items-center justify-center text-xs text-gray-400"
          >
            —
          </div>
        </template>
      </div>
      <div
        v-else
        class="h-[420px] rounded-xl bg-gray-100 flex items-center justify-center text-gray-400"
      >
        No photos yet
      </div>
    </section>

    <!-- Main grid: content + sticky booking card -------------------------->
    <section class="max-w-6xl mx-auto px-6 py-10 grid lg:grid-cols-3 gap-10">
      <!-- Left column -->
      <div class="lg:col-span-2 space-y-8">
        <!-- Owner block -->
        <div class="flex items-center justify-between gap-4 pb-6 border-b border-gray-200">
          <div>
            <p class="text-xs uppercase tracking-wider text-gray-500">Hosted by</p>
            <p class="text-xl font-semibold mt-0.5">
              {{ listing.owner_display_name || 'Ijara user' }}
            </p>
            <NuxtLink
              :to="`/users/${listing.owner_id}/`"
              class="text-sm text-slate-700 hover:text-slate-900 underline underline-offset-2"
            >
              View profile
            </NuxtLink>
          </div>
          <div
            class="w-14 h-14 rounded-full bg-slate-200 overflow-hidden flex items-center justify-center text-slate-600 font-semibold text-lg shrink-0"
          >
            <img
              v-if="listing.owner_avatar"
              :src="listing.owner_avatar"
              class="w-full h-full object-cover"
            />
            <span v-else>{{ (listing.owner_display_name || 'I').charAt(0).toUpperCase() }}</span>
          </div>
        </div>

        <!-- Features strip -->
        <div class="grid grid-cols-3 gap-4 text-sm">
          <div class="space-y-1">
            <p class="text-xs text-gray-500">Category</p>
            <p class="font-medium">{{ categoryLabel(listing.category) }}</p>
          </div>
          <div class="space-y-1">
            <p class="text-xs text-gray-500">Pickup district</p>
            <p class="font-medium">{{ districtLabel(listing.district) }}</p>
          </div>
          <div class="space-y-1">
            <p class="text-xs text-gray-500">Photos</p>
            <p class="font-medium">{{ listing.photos.length }}</p>
          </div>
        </div>

        <!-- Description -->
        <div class="space-y-3">
          <h2 class="text-lg font-semibold">About this rental</h2>
          <p class="whitespace-pre-line text-gray-700 leading-relaxed">
            {{ listing.description }}
          </p>
        </div>

        <!-- Pricing tiers -->
        <div class="space-y-3">
          <h2 class="text-lg font-semibold">Pricing options</h2>
          <div class="grid sm:grid-cols-3 gap-3">
            <div
              :class="[
                'rounded-lg border p-4',
                listing.price_hour ? 'border-gray-200' : 'border-dashed border-gray-200 opacity-50',
              ]"
            >
              <p class="text-xs uppercase tracking-wider text-gray-500">Per hour</p>
              <p class="text-lg font-semibold mt-1">
                {{ listing.price_hour ? `UZS ${fmtPrice(listing.price_hour)}` : 'Not offered' }}
              </p>
            </div>
            <div
              :class="[
                'rounded-lg border p-4',
                listing.price_day
                  ? 'border-slate-900 bg-slate-50'
                  : 'border-dashed border-gray-200 opacity-50',
              ]"
            >
              <p class="text-xs uppercase tracking-wider text-gray-500">Per day</p>
              <p class="text-lg font-semibold mt-1">
                {{ listing.price_day ? `UZS ${fmtPrice(listing.price_day)}` : 'Not offered' }}
              </p>
            </div>
            <div
              :class="[
                'rounded-lg border p-4',
                listing.price_month
                  ? 'border-gray-200'
                  : 'border-dashed border-gray-200 opacity-50',
              ]"
            >
              <p class="text-xs uppercase tracking-wider text-gray-500">Per month</p>
              <p class="text-lg font-semibold mt-1">
                {{ listing.price_month ? `UZS ${fmtPrice(listing.price_month)}` : 'Not offered' }}
              </p>
            </div>
          </div>
        </div>

        <!-- What to expect -->
        <div class="space-y-3">
          <h2 class="text-lg font-semibold">What to expect</h2>
          <ul class="space-y-2 text-sm text-gray-700">
            <li class="flex gap-3">
              <span>✅</span>
              <span
                >Request a booking -- the owner confirms the handover time directly with you.</span
              >
            </li>
            <li class="flex gap-3">
              <span>💵</span>
              <span>Pay cash or card on pickup. Online payments land in a future release.</span>
            </li>
            <li class="flex gap-3">
              <span>📍</span>
              <span
                >Collection and return in {{ districtLabel(listing.district) }} unless you agree
                otherwise.</span
              >
            </li>
            <li class="flex gap-3">
              <span>↩️</span>
              <span>Cancel any time before the owner confirms, at no cost.</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Right sidebar (sticky on lg+) -->
      <aside class="lg:col-span-1">
        <div class="lg:sticky lg:top-6 space-y-3">
          <!-- Owner view: you cannot book your own listing -->
          <div
            v-if="isOwner"
            class="rounded-xl border border-gray-200 shadow-sm bg-white p-6 space-y-4"
          >
            <div class="flex items-baseline gap-2">
              <p v-if="listing.price_day" class="text-2xl font-semibold">
                UZS {{ fmtPrice(listing.price_day) }}
              </p>
              <p v-else class="text-lg text-gray-500">Daily pricing not set</p>
              <p v-if="listing.price_day" class="text-sm text-gray-500">/ day</p>
            </div>

            <div
              class="rounded-md border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700"
            >
              <p class="font-medium">This is your listing.</p>
              <p class="text-xs text-gray-500 mt-1">
                Manage it from your dashboard or check who has requested it.
              </p>
            </div>

            <div class="space-y-2">
              <NuxtLink
                to="/dashboard/listings"
                class="block w-full text-center rounded-md bg-slate-900 text-white px-4 py-2.5 text-sm font-medium hover:bg-slate-800 transition-colors"
              >
                Manage listings
              </NuxtLink>
              <NuxtLink
                to="/dashboard/bookings"
                class="block w-full text-center rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                See booking requests
              </NuxtLink>
            </div>
          </div>

          <!-- Non-owner view: booking form -->
          <div v-else class="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            <!-- Hero price -->
            <div class="px-5 sm:px-6 pt-5 sm:pt-6 pb-4">
              <div v-if="headline" class="flex items-baseline gap-1.5">
                <span class="text-2xl sm:text-3xl font-semibold tracking-tight text-gray-900">
                  UZS {{ fmtPrice(headline.amount) }}
                </span>
                <span class="text-sm text-gray-500">/ {{ headline.unit }}</span>
              </div>
              <div v-else class="text-base text-gray-500">Pricing not set</div>
              <p v-if="otherRates.length" class="mt-1 text-xs text-gray-500 truncate">
                Also available: {{ otherRates.join(' · ') }}
              </p>
            </div>

            <!-- Date pickers grouped (Airbnb-style) -->
            <div class="mx-5 sm:mx-6 mb-3">
              <div
                class="rounded-xl border border-gray-300 grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-gray-300 overflow-hidden focus-within:border-slate-900 focus-within:ring-1 focus-within:ring-slate-900 transition"
              >
                <label class="px-3.5 py-2.5 cursor-text">
                  <span
                    class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold"
                  >
                    Pickup
                  </span>
                  <input
                    v-model="startAt"
                    :min="minLocal"
                    type="datetime-local"
                    class="mt-0.5 block w-full bg-transparent border-0 p-0 text-sm text-gray-900 focus:ring-0 focus:outline-none"
                  />
                </label>
                <label class="px-3.5 py-2.5 cursor-text">
                  <span
                    class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold"
                  >
                    Return
                  </span>
                  <input
                    v-model="endAt"
                    :min="startAt || minLocal"
                    type="datetime-local"
                    class="mt-0.5 block w-full bg-transparent border-0 p-0 text-sm text-gray-900 focus:ring-0 focus:outline-none"
                  />
                </label>
              </div>
              <p class="mt-1 text-[11px] text-gray-400">Times are in Asia/Tashkent.</p>
            </div>

            <!-- Payment method (full-width segmented) -->
            <div class="px-5 sm:px-6 mb-3">
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">
                Pay how
              </p>
              <div class="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  :class="[
                    'group rounded-xl border px-3 py-2.5 text-left transition',
                    paymentMethod === 'cash'
                      ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400',
                  ]"
                  @click="paymentMethod = 'cash'"
                >
                  <span class="flex items-center gap-1.5 text-sm font-medium">
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <rect x="2" y="6" width="20" height="12" rx="2" />
                      <circle cx="12" cy="12" r="2.5" />
                    </svg>
                    Cash
                  </span>
                  <span
                    :class="[
                      'block text-[11px] mt-0.5',
                      paymentMethod === 'cash' ? 'text-white/75' : 'text-gray-500',
                    ]"
                  >
                    On pickup
                  </span>
                </button>
                <button
                  type="button"
                  :class="[
                    'group rounded-xl border px-3 py-2.5 text-left transition',
                    paymentMethod === 'stripe'
                      ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-400',
                  ]"
                  @click="paymentMethod = 'stripe'"
                >
                  <span class="flex items-center gap-1.5 text-sm font-medium">
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.8"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    >
                      <rect x="2" y="5" width="20" height="14" rx="2" />
                      <path d="M2 10h20" />
                      <path d="M6 15h4" />
                    </svg>
                    Card
                  </span>
                  <span
                    :class="[
                      'block text-[11px] mt-0.5',
                      paymentMethod === 'stripe' ? 'text-white/75' : 'text-gray-500',
                    ]"
                  >
                    Stripe
                  </span>
                </button>
              </div>
            </div>

            <!-- Optional note (collapsed by default) -->
            <div class="px-5 sm:px-6 mb-3">
              <button
                v-if="!noteOpen && !note"
                type="button"
                class="inline-flex items-center gap-1 text-xs font-medium text-slate-700 hover:text-slate-900"
                @click="noteOpen = true"
              >
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M12 5v14M5 12h14" />
                </svg>
                Add a note for the owner
              </button>
              <div v-else>
                <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1.5">
                  Note for the owner
                </p>
                <textarea
                  v-model="note"
                  rows="2"
                  maxlength="500"
                  placeholder="When would you like to pick it up?"
                  class="block w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900 resize-y"
                />
              </div>
            </div>

            <!-- Quote breakdown -->
            <div class="px-5 sm:px-6 pt-3 pb-4 border-t border-gray-100 bg-gray-50/50">
              <div v-if="quote" class="space-y-2 text-sm">
                <div class="flex justify-between text-gray-600">
                  <span>
                    UZS {{ fmtPrice(quote.unit_price) }}
                    <span class="text-gray-400">×</span>
                    {{ quote.quantity }} {{ unitLabel(quote.unit, quote.quantity) }}
                  </span>
                  <span class="tabular-nums"
                    >UZS {{ Number(quote.total_amount).toLocaleString('en-US') }}</span
                  >
                </div>
                <div class="flex justify-between items-baseline pt-2 border-t border-gray-200">
                  <span class="font-semibold text-gray-900">Total</span>
                  <span class="font-semibold text-base text-gray-900 tabular-nums">
                    UZS {{ Number(quote.total_amount).toLocaleString('en-US') }}
                  </span>
                </div>
              </div>
              <div
                v-else-if="quoteError"
                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
              >
                {{ quoteError }}
              </div>
              <p v-else class="text-xs text-gray-500 italic">
                Pick pickup and return times above to see the price.
              </p>
            </div>

            <!-- Booking error -->
            <div
              v-if="bookingError"
              class="mx-5 sm:mx-6 mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
            >
              {{ bookingError }}
            </div>

            <!-- CTA -->
            <div class="px-5 sm:px-6 pb-5 pt-4">
              <button
                type="button"
                :disabled="booking || !quote"
                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white px-4 py-3 text-sm font-semibold hover:bg-slate-800 active:bg-slate-950 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
                @click="onBook"
              >
                <svg
                  v-if="booking"
                  class="w-4 h-4 animate-spin"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                >
                  <path d="M21 12a9 9 0 1 1-6.2-8.55" />
                </svg>
                <span v-if="booking">Sending request…</span>
                <span v-else-if="!quote">Pick a window first</span>
                <span v-else>Request booking</span>
              </button>
              <p class="mt-2.5 flex items-center justify-center gap-1 text-[11px] text-gray-500">
                <svg
                  class="w-3 h-3"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                No charge until the owner accepts
              </p>
            </div>
          </div>

          <p class="text-xs text-gray-500 text-center">Report a problem · Share this listing</p>
        </div>
      </aside>
    </section>
  </div>
</template>
