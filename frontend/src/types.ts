export type Role = 'client' | 'seller' | 'surveyor' | 'admin'
export type Language = 'rw' | 'en' | 'fr'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  language: Language
  status: string
  is_verified: boolean
  is_staff?: boolean
}

export interface SupportTicket {
  id: string
  user: number
  user_name: string
  user_email: string
  subject: string
  message: string
  status: string
  created_at: string
}

export interface Listing {
  id: string
  title: string
  description: string
  property_type: 'land' | 'house'
  price_rwf: string
  area_sqm: string
  province: string
  district: string
  sector: string
  cell: string
  village: string
  latitude: string
  longitude: string
  upi: string
  photo_url: string
  photos: string[]
  status: string
  is_verified: boolean
  is_featured: boolean
  moderation_note: string
  views: number
  owner: number
  owner_name: string
  owner_role: Role
  enquiry_count: number
  created_at: string
}

export interface Surveyor {
  id: string
  user: number
  full_name: string
  bio: string
  qualifications: string
  licence_number: string
  service_areas: string
  services: string[]
  verification_status: string
  rejection_reason: string
  years_experience: number
  rating: number | null
  completed_jobs: number
  documents: SurveyorDocument[]
}

export interface SurveyorDocument {
  id: string
  document_type: string
  original_filename: string
  status: string
  created_at: string
}

export interface SurveyQuote {
  id: string
  request: string
  surveyor: number
  surveyor_name: string
  surveyor_verified: boolean
  surveyor_rating: number | null
  price_rwf: string
  timeline_days: number
  scope_notes: string
  valid_until: string | null
  status: string
  created_at: string
}

export interface SurveyRequest {
  id: string
  client: number
  client_name: string
  service: string
  location: string
  latitude: string | null
  longitude: string | null
  upi: string
  description: string
  desired_date: string | null
  budget_rwf: string | null
  status: string
  quote_count: number
  quotes: SurveyQuote[]
  created_at: string
}

export interface Booking {
  id: string
  request: SurveyRequest
  quote: SurveyQuote
  client: number
  surveyor: number
  client_name: string
  surveyor_name: string
  status: string
  report_text: string
  has_review: boolean
  created_at: string
}

export interface PropertyReport {
  id: string
  location: string
  upi: string
  status: string
  payment_status: string
  source_note: string
  disclaimer: string
  created_at: string
  listing_details?: Listing
}

export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export function getResults<T>(value: T[] | Page<T>): T[] {
  return Array.isArray(value) ? value : value.results
}
