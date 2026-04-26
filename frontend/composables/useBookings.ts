export type BookingState =
  | 'requested'
  | 'accepted'
  | 'paid'
  | 'picked_up'
  | 'returned'
  | 'completed'
  | 'rejected'
  | 'cancelled'
  | 'disputed'

export type PaymentMethod = 'cash' | 'stripe'

export interface PriceQuote {
  unit: 'hour' | 'day' | 'month'
  unit_price: string
  quantity: number
  total_amount: string
}

export function useBookings() {
  const api = useAuthedApi()
  const publicApi = useApi()

  return {
    myBookings: (role: 'all' | 'renter' | 'owner' = 'all') => api<any[]>(`bookings/?role=${role}`),

    fetchBooking: (id: number | string) => api<any>(`bookings/${id}/`),

    createBooking: (body: {
      listing: number
      start_at: string
      end_at: string
      payment_method?: PaymentMethod
      note?: string
    }) => api<any>('bookings/', { method: 'POST', body }),

    transitionBooking: (id: number, state: BookingState, reason = '') =>
      api<any>(`bookings/${id}/`, { method: 'PATCH', body: { state, reason } }),

    quote: (listing: number, start_at: string, end_at: string) =>
      publicApi<PriceQuote>('bookings/quote/', {
        method: 'POST',
        body: { listing, start_at, end_at },
      }),

    ownerAnalytics: () => api<OwnerAnalytics>('bookings/owner-analytics/'),
  }
}

export interface OwnerAnalytics {
  listings_total: number
  listings_active: number
  bookings_total: number
  earned_revenue: string
  pipeline_revenue: string
  acceptance_rate: number
  last_30d_count: number
  last_30d_revenue: string
  state_breakdown: { state: BookingState; count: number }[]
  top_listings: {
    id: number
    title: string
    category: string
    district: string
    is_active: boolean
    booking_count: number
    revenue: string
  }[]
  recent_bookings: {
    id: number
    listing_id: number
    listing_title: string
    renter_display_name: string
    state: BookingState
    payment_method: PaymentMethod
    total_amount: string
    start_at: string
    created_at: string
  }[]
}

export const BOOKING_STATE_LABELS: Record<BookingState, string> = {
  requested: 'Requested',
  accepted: 'Accepted',
  paid: 'Paid',
  picked_up: 'Picked up',
  returned: 'Returned',
  completed: 'Completed',
  rejected: 'Rejected',
  cancelled: 'Cancelled',
  disputed: 'Disputed',
}

export const TASHKENT_OFFSET = '+05:00'

export function tashkentISO(localDateTime: string): string {
  if (!localDateTime) return ''
  const withSeconds = localDateTime.length === 16 ? `${localDateTime}:00` : localDateTime
  return `${withSeconds}${TASHKENT_OFFSET}`
}

export function formatTashkent(iso: string, opts: Intl.DateTimeFormatOptions = {}): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('en-GB', {
    timeZone: 'Asia/Tashkent',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...opts,
  })
}
