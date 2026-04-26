<script setup lang="ts">
// pages/dashboard/bookings.vue
// Card list split by renter/owner role. Action buttons drive the
// 9-state FSM via PATCH bookings/<id>/ {state}.

import {
  BOOKING_STATE_LABELS,
  formatTashkent,
  useBookings,
  type BookingState,
} from '~/composables/useBookings'
import { CATEGORIES, DISTRICTS } from '~/composables/useListings'

definePageMeta({
  middleware: ['auth'],
})

const { myBookings, transitionBooking } = useBookings()

const tab = ref<'renter' | 'owner'>('renter')
const bookings = ref<any[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

async function load() {
  loading.value = true
  errorMsg.value = null
  try {
    bookings.value = await myBookings(tab.value)
  } catch {
    errorMsg.value = 'Could not load bookings.'
  } finally {
    loading.value = false
  }
}

watch(tab, load, { immediate: true })

async function act(b: any, state: BookingState) {
  try {
    await transitionBooking(b.id, state)
    await load()
  } catch (err: any) {
    errorMsg.value = err?.data?.state?.[0] ?? 'Action failed.'
  }
}

interface Action {
  label: string
  state: BookingState
  primary?: boolean
  danger?: boolean
}

function ownerActions(b: any): Action[] {
  if (b.state === 'requested') {
    return [
      { label: 'Accept', state: 'accepted', primary: true },
      { label: 'Reject', state: 'rejected', danger: true },
    ]
  }
  if (b.state === 'accepted') {
    // Stripe bookings: owner must wait for the renter to pay before
    // pickup. The "Mark picked up" button is hidden until state=paid.
    if (b.payment_method === 'stripe') {
      return [{ label: 'Cancel', state: 'cancelled', danger: true }]
    }
    return [
      { label: 'Mark picked up', state: 'picked_up', primary: true },
      { label: 'Cancel', state: 'cancelled' },
    ]
  }
  if (b.state === 'paid') {
    return [
      { label: 'Mark picked up', state: 'picked_up', primary: true },
      { label: 'Cancel', state: 'cancelled' },
    ]
  }
  if (b.state === 'picked_up') {
    return [{ label: 'Mark returned', state: 'returned', primary: true }]
  }
  if (b.state === 'returned') {
    return [{ label: 'Complete', state: 'completed', primary: true }]
  }
  return []
}

function renterActions(b: any): Action[] {
  if (b.state === 'requested' || b.state === 'accepted') {
    return [{ label: 'Cancel', state: 'cancelled', danger: true }]
  }
  return []
}

function stateStyle(state: string): string {
  if (state === 'requested') return 'bg-amber-50 text-amber-800 border-amber-200'
  if (state === 'accepted' || state === 'paid')
    return 'bg-emerald-50 text-emerald-800 border-emerald-200'
  if (state === 'picked_up' || state === 'returned')
    return 'bg-blue-50 text-blue-800 border-blue-200'
  if (state === 'completed') return 'bg-slate-100 text-slate-700 border-slate-200'
  if (state === 'rejected' || state === 'cancelled') return 'bg-red-50 text-red-700 border-red-200'
  if (state === 'disputed') return 'bg-purple-50 text-purple-800 border-purple-200'
  return 'bg-gray-100 text-gray-600 border-gray-200'
}

function categoryLabel(v: string): string {
  return CATEGORIES.find((c) => c.value === v)?.label ?? v
}

function districtLabel(v: string): string {
  return DISTRICTS.find((d) => d.value === v)?.label ?? v
}

function durationLabel(b: any): string {
  return `${b.quantity} ${b.unit}${b.quantity === 1 ? '' : 's'}`
}
</script>

<template>
  <main class="min-h-[calc(100vh-4rem)] bg-gray-50">
    <div class="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <header>
        <h1 class="text-3xl font-semibold tracking-tight">Bookings</h1>
        <p class="text-sm text-gray-600 mt-1">
          Items you have rented and requests on your listings.
        </p>
      </header>

      <!-- Tabs -->
      <div class="inline-flex rounded-lg border border-gray-200 bg-white p-1">
        <button
          type="button"
          :class="[
            'rounded-md px-4 py-2 text-sm font-medium transition',
            tab === 'renter' ? 'bg-slate-900 text-white' : 'text-gray-600 hover:text-gray-900',
          ]"
          @click="tab = 'renter'"
        >
          As renter
        </button>
        <button
          type="button"
          :class="[
            'rounded-md px-4 py-2 text-sm font-medium transition',
            tab === 'owner' ? 'bg-slate-900 text-white' : 'text-gray-600 hover:text-gray-900',
          ]"
          @click="tab = 'owner'"
        >
          As owner
        </button>
      </div>

      <p
        v-if="errorMsg"
        class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      >
        {{ errorMsg }}
      </p>

      <div v-if="loading" class="py-16 text-center text-sm text-gray-500">Loading bookings...</div>

      <div
        v-else-if="bookings.length === 0"
        class="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center space-y-2"
      >
        <p class="font-medium text-gray-700">
          <template v-if="tab === 'renter'">You have not booked anything yet.</template>
          <template v-else>No one has booked your items yet.</template>
        </p>
        <p class="text-sm text-gray-500">
          <template v-if="tab === 'renter'">
            <NuxtLink to="/listings" class="underline hover:text-gray-900">Browse rentals</NuxtLink>
            to find something.
          </template>
          <template v-else>
            <NuxtLink to="/dashboard/listings" class="underline hover:text-gray-900">
              Manage your listings
            </NuxtLink>
            or post a new one.
          </template>
        </p>
      </div>

      <ul v-else class="space-y-4">
        <li
          v-for="b in bookings"
          :key="b.id"
          class="rounded-xl border border-gray-200 bg-white overflow-hidden flex flex-col sm:flex-row"
        >
          <NuxtLink
            :to="`/listings/${b.listing}`"
            class="sm:w-48 h-36 sm:h-auto bg-gray-100 shrink-0 overflow-hidden"
          >
            <img
              v-if="b.listing_photo"
              :src="b.listing_photo"
              :alt="b.listing_title"
              class="w-full h-full object-cover"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-xs text-gray-400"
            >
              No photo
            </div>
          </NuxtLink>

          <div class="flex-1 p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <NuxtLink
                  :to="`/listings/${b.listing}`"
                  class="font-semibold text-gray-900 hover:underline"
                >
                  {{ b.listing_title }}
                </NuxtLink>
                <p class="text-xs text-gray-500 mt-0.5">
                  {{ categoryLabel(b.listing_category) }} · {{ districtLabel(b.listing_district) }}
                </p>
              </div>
              <span
                :class="[
                  'shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium',
                  stateStyle(b.state),
                ]"
              >
                {{ BOOKING_STATE_LABELS[b.state as BookingState] ?? b.state }}
              </span>
            </div>

            <div class="mt-4 grid sm:grid-cols-3 gap-3 text-sm">
              <div>
                <p class="text-xs text-gray-500">From</p>
                <p class="font-medium">{{ formatTashkent(b.start_at) }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-500">To</p>
                <p class="font-medium">{{ formatTashkent(b.end_at) }}</p>
              </div>
              <div>
                <p class="text-xs text-gray-500">{{ durationLabel(b) }} · Total</p>
                <p class="font-medium">UZS {{ Number(b.total_amount).toLocaleString('en-US') }}</p>
              </div>
            </div>

            <p class="mt-3 text-xs text-gray-500">
              {{ tab === 'owner' ? 'Renter' : 'Owner' }}:
              <NuxtLink
                :to="`/users/${tab === 'owner' ? b.renter : b.owner_id}`"
                class="text-gray-700 hover:underline"
              >
                {{
                  tab === 'owner'
                    ? b.renter_display_name || 'Ijara user'
                    : b.owner_display_name || 'Ijara user'
                }}
              </NuxtLink>
              · {{ b.payment_method === 'stripe' ? 'Stripe' : 'Cash on pickup' }}
            </p>

            <p
              v-if="b.note"
              class="mt-3 rounded-md bg-slate-50 border border-slate-200 px-3 py-2 text-xs text-slate-600 italic"
            >
              "{{ b.note }}"
            </p>

            <div class="mt-4 flex flex-wrap items-center gap-2">
              <NuxtLink
                :to="`/bookings/${b.id}`"
                class="text-xs text-slate-700 underline hover:text-slate-900"
              >
                View timeline →
              </NuxtLink>
              <span class="flex-1"></span>
              <template v-if="tab === 'owner'">
                <button
                  v-for="a in ownerActions(b)"
                  :key="a.state"
                  type="button"
                  :class="[
                    'rounded-md px-3 py-1.5 text-xs font-medium transition',
                    a.primary
                      ? 'bg-slate-900 text-white hover:bg-slate-800'
                      : a.danger
                        ? 'border border-red-300 text-red-700 hover:bg-red-50'
                        : 'border border-gray-300 text-gray-700 hover:bg-gray-50',
                  ]"
                  @click="act(b, a.state)"
                >
                  {{ a.label }}
                </button>
              </template>
              <template v-else>
                <!--
                  Stripe bookings: surface a "Pay now" CTA the moment
                  the owner accepts so the renter does not have to dig
                  into the booking detail page to find the Payment Element.
                -->
                <NuxtLink
                  v-if="b.state === 'accepted' && b.payment_method === 'stripe'"
                  :to="`/bookings/${b.id}`"
                  class="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 text-white px-3 py-1.5 text-xs font-medium hover:bg-emerald-700 transition"
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
                    <rect x="2" y="5" width="20" height="14" rx="2" />
                    <path d="M2 10h20" />
                  </svg>
                  Pay now
                </NuxtLink>
                <button
                  v-for="a in renterActions(b)"
                  :key="a.state"
                  type="button"
                  class="rounded-md border border-red-300 text-red-700 px-3 py-1.5 text-xs font-medium hover:bg-red-50 transition"
                  @click="act(b, a.state)"
                >
                  {{ a.label }}
                </button>
              </template>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </main>
</template>
