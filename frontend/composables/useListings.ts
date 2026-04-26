export function useListings() {
  const publicApi = useApi()
  const authedApi = useAuthedApi()

  return {
    fetchListings: (filters?: {
      category?: string
      district?: string
      q?: string
      unit?: string
      min_price?: string | number
      max_price?: string | number
    }) => {
      const params = new URLSearchParams()
      if (filters?.category) params.set('category', filters.category)
      if (filters?.district) params.set('district', filters.district)
      if (filters?.q) params.set('q', filters.q)
      if (filters?.unit) params.set('unit', filters.unit)
      if (filters?.min_price) params.set('min_price', String(filters.min_price))
      if (filters?.max_price) params.set('max_price', String(filters.max_price))
      const qs = params.toString()
      return publicApi<any[]>(`listings/${qs ? '?' + qs : ''}`)
    },

    fetchMyListings: () => authedApi<any[]>('listings/?mine=1'),

    fetchListing: (id: number | string) => publicApi<any>(`listings/${id}/`),

    createListing: (body: any) => authedApi<any>('listings/', { method: 'POST', body }),

    updateListing: (id: number | string, body: any) =>
      authedApi<any>(`listings/${id}/`, { method: 'PATCH', body }),

    uploadPhoto: (listingId: number | string, file: File) => {
      const form = new FormData()
      form.append('photo', file)
      return authedApi<any>(`listings/${listingId}/photos/`, { method: 'POST', body: form })
    },

    deletePhoto: (listingId: number | string, photoId: number) =>
      authedApi(`listings/${listingId}/photos/${photoId}/`, { method: 'DELETE' }),

    deleteListing: (id: number) => authedApi(`listings/${id}/`, { method: 'DELETE' }),

    aiSuggestFromPhotos: (files: File[]) => {
      const form = new FormData()
      for (const file of files) form.append('photos', file)
      return authedApi<{
        title: string | null
        description: string | null
        category: string | null
        price_hour: number | null
        price_day: number | null
        price_month: number | null
      }>('listings/ai-suggest/', { method: 'POST', body: form })
    },
  }
}

export const CATEGORIES = [
  { value: 'tools', label: 'Tools' },
  { value: 'electronics', label: 'Electronics' },
  { value: 'event_gear', label: 'Event gear' },
  { value: 'sports', label: 'Sports' },
  { value: 'furniture', label: 'Furniture' },
  { value: 'vehicles', label: 'Vehicles' },
  { value: 'other', label: 'Other' },
]

export const DISTRICTS = [
  { value: 'bektemir', label: 'Bektemir' },
  { value: 'chilonzor', label: 'Chilonzor' },
  { value: 'mirobod', label: 'Mirobod' },
  { value: 'mirzo_ulugbek', label: 'Mirzo Ulugbek' },
  { value: 'olmazor', label: 'Olmazor' },
  { value: 'sergeli', label: 'Sergeli' },
  { value: 'shaykhontohur', label: 'Shaykhontohur' },
  { value: 'uchtepa', label: 'Uchtepa' },
  { value: 'yakkasaray', label: 'Yakkasaray' },
  { value: 'yashnabad', label: 'Yashnabad' },
  { value: 'yunusobod', label: 'Yunusobod' },
  { value: 'yangihayot', label: 'Yangihayot' },
]
