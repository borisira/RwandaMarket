<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { API_BASE, api, getToken, jsonBody } from './api'
import MapPanel from './MapPanel.vue'
import { getResults } from './types'
import type { Booking, Language, Listing, Page, PropertyReport, Role, Surveyor, SurveyRequest, SurveyorDocument, User } from './types'

type ViewName = 'home' | 'listings' | 'surveyors' | 'map' | 'activity' | 'reports' | 'admin' | 'support'
type DialogName = 'auth' | 'listing' | 'listing-photos' | 'request' | 'enquiry' | 'support' | 'complaint' | 'surveyor-profile' | null
type AuthMode = 'login' | 'register'
type ListingPhotoDraft = { file: File; previewUrl: string }
type RwandaCell = { name: string; villages: string[] }
type RwandaSector = { name: string; cells: RwandaCell[] }
type RwandaDistrict = { name: string; sectors: RwandaSector[] }
type RwandaProvince = { name: string; districts: RwandaDistrict[] }

const user = ref<User | null>(null)
const view = ref<ViewName>('home')
const dialog = ref<DialogName>(null)
const authMode = ref<AuthMode>('login')
const language = ref<Language>((localStorage.getItem('rwm_language') as Language) || 'rw')
const listings = ref<Listing[]>([])
const surveyors = ref<Surveyor[]>([])
const favourites = ref<string[]>([])
const surveyRequests = ref<SurveyRequest[]>([])
const bookings = ref<Booking[]>([])
const reports = ref<PropertyReport[]>([])
const adminData = ref<Record<string, unknown> | null>(null)
const loading = ref(false)
const toast = ref('')
const search = ref('')
const typeFilter = ref('all')
const districtFilter = ref('')
const focus = ref<{ latitude: number; longitude: number; label?: string } | null>(null)
const selectedListing = ref<Listing | null>(null)
const detailListing = ref<Listing | null>(null)
const authError = ref('')
const showPassword = ref(false)
const rwandaLocations = ref<RwandaProvince[]>([])
const listingLocationsLoading = ref(false)
const authPasswordRules = computed(() => [
  { label: 'At least 10 characters', valid: authForm.password.length >= 10 },
  { label: 'One uppercase letter', valid: /[A-Z]/.test(authForm.password) },
  { label: 'One lowercase letter', valid: /[a-z]/.test(authForm.password) },
  { label: 'One number', valid: /\d/.test(authForm.password) },
  { label: 'One special character', valid: /[^A-Za-z0-9]/.test(authForm.password) },
])
const authPasswordValid = computed(() => authMode.value === 'login'
  ? authForm.password.length > 0
  : authPasswordRules.value.every((rule) => rule.valid))
const authEmailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(authForm.email.trim()))
const authFormValid = computed(() => authEmailValid.value
  && authPasswordValid.value
  && (authMode.value === 'login' || (authForm.first_name.trim().length > 0 && authForm.last_name.trim().length > 0)))

const authForm = reactive({ email: '', password: '', first_name: '', last_name: '', role: 'client' as Role, language: 'rw' as Language })
const listingForm = reactive({
  title: '', description: '', property_type: 'land', price_rwf: '', area_sqm: '',
  province: '', district: '', sector: '', cell: '', village: '', latitude: '-1.9441',
  longitude: '30.0619', upi: '', photo_url: '',
})
const createdListing = ref<Listing | null>(null)
const listingPhotoDrafts = ref<ListingPhotoDraft[]>([])
const uploadedListingPhotos = ref<string[]>([])
const listingPhotoError = ref('')
const listingPhotosUploading = ref(false)
const requestForm = reactive({ service: 'Boundary survey', location: '', latitude: '', longitude: '', upi: '', description: '', desired_date: '', budget_rwf: '' })
const quoteForm = reactive<Record<string, { price_rwf: string; timeline_days: string; scope_notes: string }>>({})
const enquiryText = ref('')
const supportForm = reactive({ subject: '', message: '' })
const complaintForm = reactive({ subject: '', details: '' })
const surveyorForm = reactive({ bio: '', qualifications: '', licence_number: '', service_areas: '', services: 'Boundary survey, Topographic survey', years_experience: '0' })
const surveyorDocuments = ref<SurveyorDocument[]>([])
const surveyorDocumentFile = ref<File | null>(null)
const surveyorDocumentType = ref('licence')
const surveyMapSearch = ref('')
const filterMenuOpen = ref(false)
const selectedProvince = computed(() => rwandaLocations.value.find((item) => item.name === listingForm.province))
const availableDistricts = computed(() => selectedProvince.value?.districts ?? [])
const selectedDistrict = computed(() => availableDistricts.value.find((item) => item.name === listingForm.district))
const availableSectors = computed(() => selectedDistrict.value?.sectors ?? [])
const selectedSector = computed(() => availableSectors.value.find((item) => item.name === listingForm.sector))
const availableCells = computed(() => selectedSector.value?.cells ?? [])
const selectedCell = computed(() => availableCells.value.find((item) => item.name === listingForm.cell))
const availableVillages = computed(() => selectedCell.value?.villages ?? [])
const availableProvinces = computed(() => rwandaLocations.value.map((item) => item.name))

watch(() => listingForm.province, () => {
  listingForm.district = ''
  listingForm.sector = ''
  listingForm.cell = ''
  listingForm.village = ''
})
watch(() => listingForm.district, () => {
  listingForm.sector = ''
  listingForm.cell = ''
  listingForm.village = ''
})
watch(() => listingForm.sector, () => {
  listingForm.cell = ''
  listingForm.village = ''
})
watch(() => listingForm.cell, () => {
  listingForm.village = ''
})

const translations: Record<Language, Record<string, string>> = {
  rw: {
    nav_home: 'Ahabanza', nav_listings: 'Ubutaka n’amazu', nav_surveyors: 'Abapima ubutaka', nav_map: 'Ikarita', nav_activity: 'Ibikorwa byanjye', nav_reports: 'Raporo', nav_support: 'Ubufasha', sign_in: 'Injira', join: 'Fungura konti', logout: 'Sohoka', post_listing: 'Shyiraho itangazo',
    hero_kicker: 'RwandaMarket · Kigali na hose mu Rwanda', hero_title: 'Ahantu hawe heza hatangirira hano.', hero_text: 'Shakisha ubutaka, amazu n’abapima ubutaka bizewe — byose ahantu hamwe.', search_placeholder: 'Shakisha ahantu, akarere cyangwa UPI', search_button: 'Shakisha', explore: 'Reba amatangazo', verified: 'Byagenzuwe', unverified: 'Ntibiragenzurwa', featured: 'Ibibanza byatoranyijwe', view_all: 'Reba byose', all: 'Byose', land: 'Ubutaka', house: 'Amazu', surveyors_heading: 'Abapima ubutaka bemejwe', how_title: 'Kuva ku gitekerezo kugeza ku butaka.', how_1: 'Shakisha ubutaka cyangwa inzu', how_2: 'Reba aho biherereye', how_3: 'Vugana n’umupima ubutaka', how_4: 'Gerageza neza mbere yo gufata icyemezo', map_title: 'Shaka ubutaka. Menya aho buri.', map_subtitle: 'Shakisha UPI, akarere cyangwa izina ry’ahantu. Reba amapine y’amatangazo ku ikarita.', map_not_official: 'Amakuru yemewe ya UPI n’igishushanyombonera cy’imikoreshereze y’ubutaka ntaraboneka. Nta makuru y’ubutaka yahimbwe.', all_rwanda: 'Mu Rwanda hose', trust_title: 'Buri gihe menya amakuru yizewe.', trust_text: 'Amakuru y’ubutaka n’ikarita agaragaza inkomoko n’uko yagenzuwe. Amapine ntiyemeza nyir’ubutaka cyangwa imbibi zemewe.', contact: 'Vugana n’ugurisha', report: 'Raporo y’ubutaka', create_account: 'Fungura konti', language: 'Ururimi', filter: 'Akayunguruzo', district: 'Akarere', price: 'Igiciro', area: 'Ubuso', close: 'Funga', send: 'Ohereza', cancel: 'Kureka', loading: 'Birimo gupakirwa…', empty: 'Nta makuru ahari ubu.', demo_notice: 'Amatangazo agaragara ni ingero zo kugerageza, si amatangazo nyayo.', source_notice: 'Ikarita ya OpenStreetMap. Amashusho y’icyogajuru ntarahuzwa n’uburenganzira bwemewe.', trust_badge: 'Umutekano n’ukuri', footer_disclaimer: 'Amatangazo, amapine na raporo ni amakuru yo gufasha gufata icyemezo gusa. Ntabwo byemeza nyir’ubutaka, imbibi cyangwa uruhushya rwo kubaka.',
  },
  en: {
    nav_home: 'Discover', nav_listings: 'Land & homes', nav_surveyors: 'Surveyors', nav_map: 'Land map', nav_activity: 'My activity', nav_reports: 'Reports', nav_support: 'Help & support', sign_in: 'Sign in', join: 'Create account', logout: 'Sign out', post_listing: 'Post a listing',
    hero_kicker: 'RwandaMarket · Kigali and all of Rwanda', hero_title: 'Your next place starts here.', hero_text: 'Find land, homes and trusted surveyors — all in one place.', search_placeholder: 'Search a place, district or UPI', search_button: 'Search', explore: 'Explore listings', verified: 'Verified', unverified: 'Not verified', featured: 'Places worth a closer look', view_all: 'View all', all: 'All', land: 'Land', house: 'Homes', surveyors_heading: 'Meet verified surveyors', how_title: 'From first thought to solid ground.', how_1: 'Find land or a home', how_2: 'See where it is', how_3: 'Connect with a surveyor', how_4: 'Make your next move with care', map_title: 'Find the land. Know where it is.', map_subtitle: 'Search by UPI, district or place name. See listing pins on the map.', map_not_official: 'Authorised UPI and Master Plan datasets are not connected. No parcel information is invented.', all_rwanda: 'Across Rwanda', trust_title: 'Know what you can trust.', trust_text: 'Property and map details show their source and verification status. A map pin does not confirm legal ownership or boundaries.', contact: 'Contact seller', report: 'Property report', create_account: 'Create account', language: 'Language', filter: 'Filters', district: 'District', price: 'Price', area: 'Area', close: 'Close', send: 'Send', cancel: 'Cancel', loading: 'Loading…', empty: 'Nothing here yet.', demo_notice: 'Listings shown are sample data for demonstration, not real offers.', source_notice: 'OpenStreetMap street map. Satellite imagery is unavailable until a licensed provider is selected.', trust_badge: 'Built around trust', footer_disclaimer: 'Listings, map pins and reports are decision aids only. They do not prove ownership, legal boundaries or permission to build.',
  },
  fr: {
    nav_home: 'Découvrir', nav_listings: 'Terrains et maisons', nav_surveyors: 'Géomètres', nav_map: 'Carte', nav_activity: 'Mon activité', nav_reports: 'Rapports', nav_support: 'Aide et support', sign_in: 'Connexion', join: 'Créer un compte', logout: 'Déconnexion', post_listing: 'Publier une annonce',
    hero_kicker: 'RwandaMarket · Kigali et tout le Rwanda', hero_title: 'Votre prochain lieu commence ici.', hero_text: 'Trouvez des terrains, des maisons et des géomètres de confiance — au même endroit.', search_placeholder: 'Rechercher un lieu, un district ou un UPI', search_button: 'Rechercher', explore: 'Voir les annonces', verified: 'Vérifié', unverified: 'Non vérifié', featured: 'Des lieux à découvrir', view_all: 'Tout voir', all: 'Tout', land: 'Terrain', house: 'Maisons', surveyors_heading: 'Géomètres vérifiés', how_title: 'De l’idée au terrain.', how_1: 'Trouver un terrain ou une maison', how_2: 'Voir son emplacement', how_3: 'Contacter un géomètre', how_4: 'Avancer en toute confiance', map_title: 'Trouvez le terrain. Situez-le.', map_subtitle: 'Recherche par UPI, district ou lieu. Consultez les annonces sur la carte.', map_not_official: 'Les données UPI et du plan directeur autorisées ne sont pas connectées. Aucune parcelle n’est inventée.', all_rwanda: 'Dans tout le Rwanda', trust_title: 'Sachez à quelles informations vous fier.', trust_text: 'Les informations sur les biens et les cartes indiquent leur source et leur vérification. Un repère ne confirme ni propriété ni limites légales.', contact: 'Contacter le vendeur', report: 'Rapport immobilier', create_account: 'Créer un compte', language: 'Langue', filter: 'Filtres', district: 'District', price: 'Prix', area: 'Surface', close: 'Fermer', send: 'Envoyer', cancel: 'Annuler', loading: 'Chargement…', empty: 'Rien ici pour le moment.', demo_notice: 'Les annonces affichées sont des exemples de démonstration, pas des offres réelles.', source_notice: 'Carte OpenStreetMap. Les images satellite nécessitent un fournisseur licencié.', trust_badge: 'La confiance avant tout', footer_disclaimer: 'Les annonces, repères et rapports sont des aides à la décision. Ils ne prouvent ni propriété, ni limites légales, ni autorisation de construire.',
  },
}

const t = (key: string) => translations[language.value][key] ?? translations.en[key] ?? key
const navItems = computed(() => [
  { id: 'home' as ViewName, label: t('nav_home'), icon: '⌂' },
  { id: 'listings' as ViewName, label: t('nav_listings'), icon: '▦' },
  { id: 'surveyors' as ViewName, label: t('nav_surveyors'), icon: '⌖' },
  { id: 'map' as ViewName, label: t('nav_map'), icon: '◉' },
  ...(user.value ? [
    { id: 'activity' as ViewName, label: t('nav_activity'), icon: '↗' },
    { id: 'reports' as ViewName, label: t('nav_reports'), icon: '▤' },
  ] : []),
])
const filteredListings = computed(() => listings.value.filter((listing) => {
  const query = search.value.trim().toLocaleLowerCase()
  const matchesQuery = !query || [listing.title, listing.district, listing.province, listing.sector, listing.cell, listing.village, listing.upi].some((value) => value?.toLocaleLowerCase().includes(query))
  const matchesType = typeFilter.value === 'all' || listing.property_type === typeFilter.value
  const matchesDistrict = !districtFilter.value || listing.district.toLocaleLowerCase().includes(districtFilter.value.toLocaleLowerCase())
  return matchesQuery && matchesType && matchesDistrict
}))
const featuredListings = computed(() => filteredListings.value.slice(0, 3))
const currentTitle = computed(() => ({
  home: t('nav_home'), listings: t('nav_listings'), surveyors: t('nav_surveyors'), map: t('nav_map'),
  activity: t('nav_activity'), reports: t('nav_reports'), admin: 'Admin dashboard', support: t('nav_support'),
}[view.value]))
const isAdmin = computed(() => Boolean(user.value?.is_staff))
const money = (value: string | number) => `RWF ${Number(value).toLocaleString(language.value === 'rw' ? 'rw-RW' : language.value === 'fr' ? 'fr-RW' : 'en-RW', { maximumFractionDigits: 0 })}`
const displayArea = (value: string | number) => `${Number(value).toLocaleString(language.value === 'fr' ? 'fr-RW' : 'en-RW')} m²`
const photo = (listing: Listing) => listing.photos?.[0] || listing.photo_url || ({
  Gasabo: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=900&q=82',
  Kicukiro: 'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=900&q=82',
  Nyarugenge: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=82',
  Musanze: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=900&q=82',
}[listing.district] || 'https://images.unsplash.com/photo-1600607687644-c7171b42498f?auto=format&fit=crop&w=900&q=82')

function notify(message: string) {
  toast.value = message
  window.setTimeout(() => { if (toast.value === message) toast.value = '' }, 3800)
}

function requireAccount(message = 'Please sign in to continue.') {
  if (user.value) return true
  notify(message)
  authMode.value = 'login'
  dialog.value = 'auth'
  return false
}

async function loadListings() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (search.value) params.set('search', search.value)
    if (typeFilter.value !== 'all') params.set('property_type', typeFilter.value)
    if (districtFilter.value) params.set('district', districtFilter.value)
    const data = await api<Listing[] | Page<Listing>>(`/listings/?${params}`)
    listings.value = getResults(data)
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not load property listings.')
  } finally {
    loading.value = false
  }
}

async function loadSurveyors() {
  try {
    surveyors.value = getResults(await api<Surveyor[] | Page<Surveyor>>('/surveyor-profiles/'))
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not load surveyor profiles.')
  }
}

async function loadActivity() {
  if (!user.value) return
  try {
    if (user.value.role === 'client') {
      surveyRequests.value = getResults(await api<SurveyRequest[] | Page<SurveyRequest>>('/survey-requests/'))
      bookings.value = getResults(await api<Booking[] | Page<Booking>>('/bookings/'))
      favourites.value = getResults(await api<Array<{ listing: Listing }> | Page<{ listing: Listing }>>('/favourites/')).map((item) => item.listing.id)
    } else if (user.value.role === 'surveyor') {
      surveyRequests.value = getResults(await api<SurveyRequest[] | Page<SurveyRequest>>('/survey-requests/'))
      bookings.value = getResults(await api<Booking[] | Page<Booking>>('/bookings/'))
    } else {
      const mine = await api<Listing[] | Page<Listing>>(`/listings/?search=`)
      listings.value = getResults(mine)
      bookings.value = getResults(await api<Booking[] | Page<Booking>>('/bookings/'))
    }
    reports.value = getResults(await api<PropertyReport[] | Page<PropertyReport>>('/reports/'))
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not load your activity.')
  }
}

async function refreshSession() {
  if (!getToken()) return
  try {
    user.value = await api<User>('/auth/me/')
    language.value = user.value.language
    await loadActivity()
  } catch {
    localStorage.removeItem('rwm_token')
    user.value = null
  }
}

async function submitAuth() {
  authError.value = ''
  try {
    if (authMode.value === 'login') {
      const data = await api<{ token: string }>('/auth/login/', { method: 'POST', body: jsonBody({ username: authForm.email, password: authForm.password }) })
      localStorage.setItem('rwm_token', data.token)
      user.value = await api<User>('/auth/me/')
    } else {
      const result = await api<{ token: string; user: User }>('/auth/register/', {
        method: 'POST',
        body: jsonBody({ ...authForm, email: authForm.email }),
      })
      localStorage.setItem('rwm_token', result.token)
      user.value = result.user
    }
    if (user.value) {
      language.value = user.value.language
      localStorage.setItem('rwm_language', language.value)
    }
    dialog.value = null
    await loadActivity()
    notify(language.value === 'rw' ? 'Winjiye neza.' : language.value === 'fr' ? 'Vous êtes connecté.' : 'You’re signed in.')
  } catch (error) {
    authError.value = error instanceof Error ? error.message : 'Could not sign in.'
  }
}

async function signOut() {
  try {
    await api('/auth/me/', { method: 'DELETE' })
  } catch {
    // The local session is cleared even if the network is unavailable.
  }
  localStorage.removeItem('rwm_token')
  user.value = null
  surveyRequests.value = []
  bookings.value = []
  reports.value = []
  favourites.value = []
  view.value = 'home'
  notify('Signed out.')
}

async function changeLanguage(value: string) {
  language.value = value as Language
  localStorage.setItem('rwm_language', language.value)
  if (user.value) {
    try {
      user.value = await api<User>('/auth/me/', { method: 'PATCH', body: jsonBody({ language: value }) })
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not save your language.')
    }
  }
}

function openView(next: ViewName) {
  if (next === 'admin' && !isAdmin.value) {
    window.open('/admin/', '_blank', 'noopener')
    return
  }
  view.value = next
  if (next === 'listings' || next === 'map') loadListings()
  if (next === 'activity' || next === 'reports') loadActivity()
  if (next === 'surveyors') loadSurveyors()
  if (next === 'admin') loadAdmin()
}

async function openListingForm() {
  if (!rwandaLocations.value.length) {
    listingLocationsLoading.value = true
    dialog.value = 'listing'
    try {
      const locationModule = await import('./data/rwanda-locations.json')
      rwandaLocations.value = locationModule.default
    } catch (error) {
      dialog.value = null
      notify(error instanceof Error ? `Could not load Rwanda locations: ${error.message}` : 'Could not load Rwanda locations.')
    } finally {
      listingLocationsLoading.value = false
    }
    return
  }
  dialog.value = 'listing'
}

async function submitListing() {
  if (!requireAccount() || user.value?.role !== 'seller') return
  try {
    createdListing.value = await api<Listing>('/listings/', { method: 'POST', body: jsonBody(listingForm) })
    uploadedListingPhotos.value = createdListing.value.photos ?? []
    dialog.value = 'listing-photos'
    listingPhotoError.value = ''
    Object.assign(listingForm, {
      title: '', description: '', price_rwf: '', area_sqm: '',
      province: '', district: '', sector: '', cell: '', village: '', upi: '', photo_url: '',
    })
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not submit listing.')
  }
}

function selectListingPhotos(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files ?? [])
  input.value = ''
  listingPhotoError.value = ''
  const remaining = 10 - uploadedListingPhotos.value.length - listingPhotoDrafts.value.length
  if (files.length > remaining) {
    listingPhotoError.value = `You can add ${remaining} more photo${remaining === 1 ? '' : 's'} to this listing.`
    return
  }
  const invalid = files.find((file) => !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024)
  if (invalid) {
    listingPhotoError.value = invalid.size > 5 * 1024 * 1024
      ? 'Each photo must be 5 MB or smaller.'
      : 'Choose a JPEG, PNG or WebP image.'
    return
  }
  listingPhotoDrafts.value.push(...files.map((file) => ({ file, previewUrl: URL.createObjectURL(file) })))
}

function removeListingPhoto(index: number) {
  const [removed] = listingPhotoDrafts.value.splice(index, 1)
  if (removed) URL.revokeObjectURL(removed.previewUrl)
}

async function uploadListingPhotos() {
  if (!createdListing.value || !listingPhotoDrafts.value.length || listingPhotosUploading.value) return
  listingPhotosUploading.value = true
  listingPhotoError.value = ''
  const formData = new FormData()
  listingPhotoDrafts.value.forEach(({ file }) => formData.append('files', file))
  try {
    const result = await api<{ photos: string[] }>(`/listings/${createdListing.value.id}/photos/`, {
      method: 'POST',
      body: formData,
    })
    uploadedListingPhotos.value = result.photos
    listingPhotoDrafts.value.forEach(({ previewUrl }) => URL.revokeObjectURL(previewUrl))
    listingPhotoDrafts.value = []
  } catch (error) {
    listingPhotoError.value = error instanceof Error ? error.message : 'Could not upload the selected photos.'
  } finally {
    listingPhotosUploading.value = false
  }
}

async function finishListingPhotos() {
  listingPhotoDrafts.value.forEach(({ previewUrl }) => URL.revokeObjectURL(previewUrl))
  listingPhotoDrafts.value = []
  createdListing.value = null
  dialog.value = null
  await loadListings()
  notify('Listing sent for review. It will appear publicly after moderation.')
}

async function toggleFavourite(listing: Listing) {
  if (!requireAccount()) return
  try {
    if (favourites.value.includes(listing.id)) {
      const existing = await api<Array<{ id: string; listing: Listing }> | Page<{ id: string; listing: Listing }>>('/favourites/')
      const item = getResults(existing).find((favourite) => favourite.listing.id === listing.id)
      if (item) await api(`/favourites/${item.id}/`, { method: 'DELETE' })
      favourites.value = favourites.value.filter((id) => id !== listing.id)
    } else {
      await api('/favourites/', { method: 'POST', body: jsonBody({ listing_id: listing.id }) })
      favourites.value.push(listing.id)
    }
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not update saved properties.')
  }
}

function showMap(listing: Listing) {
  selectedListing.value = listing
  focus.value = { latitude: Number(listing.latitude), longitude: Number(listing.longitude), label: listing.title }
  view.value = 'map'
  void loadListings()
}

function searchMap() {
  const coordinates = surveyMapSearch.value.trim().match(/^\s*(-?\d{1,2}(?:\.\d+)?)\s*[, ]\s*(-?\d{1,3}(?:\.\d+)?)\s*$/)
  if (coordinates) {
    const latitude = Number(coordinates[1])
    const longitude = Number(coordinates[2])
    if (latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180) {
      focus.value = { latitude, longitude, label: surveyMapSearch.value }
      selectedListing.value = null
      return
    }
  }
  search.value = surveyMapSearch.value
  void loadListings()
}

async function sendEnquiry() {
  if (!detailListing.value || !requireAccount()) return
  if (!enquiryText.value.trim()) return notify('Add a short message before sending.')
  try {
    await api('/enquiries/', { method: 'POST', body: jsonBody({ listing: detailListing.value.id, message: enquiryText.value }) })
    dialog.value = null
    enquiryText.value = ''
    notify('Your enquiry has been sent to the seller.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not send your enquiry.')
  }
}

async function orderReport(listing?: Listing) {
  if (!requireAccount()) return
  try {
    const report = await api<PropertyReport>('/reports/', {
      method: 'POST',
      body: jsonBody({ listing: listing?.id, location: listing?.district ?? search.value, upi: listing?.upi ?? '' }),
    })
    reports.value.unshift(report)
    view.value = 'reports'
    notify('Report preview created. Payment is unavailable until a provider is configured.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not create the report preview.')
  }
}

async function downloadReport(report: PropertyReport) {
  try {
    const response = await fetch(`${API_BASE}/reports/${report.id}/download/`, {
      headers: { Authorization: `Token ${getToken()}` },
    })
    if (!response.ok) throw new Error('Could not download report.')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `property-report-${report.id}.pdf`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not download report.')
  }
}

async function submitSurveyRequest() {
  if (!requireAccount() || user.value?.role !== 'client') return
  try {
    await api('/survey-requests/', {
      method: 'POST',
      body: jsonBody({
        ...requestForm,
        latitude: requestForm.latitude || null,
        longitude: requestForm.longitude || null,
        desired_date: requestForm.desired_date || null,
        budget_rwf: requestForm.budget_rwf || null,
      }),
    })
    dialog.value = null
    Object.assign(requestForm, { service: 'Boundary survey', location: '', latitude: '', longitude: '', upi: '', description: '', desired_date: '', budget_rwf: '' })
    await loadActivity()
    notify('Your survey request was sent to verified providers.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not send your request.')
  }
}

async function sendQuote(request: SurveyRequest) {
  if (!user.value || user.value.role !== 'surveyor') return
  const form = quoteForm[request.id]
  if (!form?.price_rwf || !form.scope_notes.trim()) return notify('Add a price and scope notes to send a quote.')
  try {
    await api('/quotes/', {
      method: 'POST',
      body: jsonBody({
        request: request.id, price_rwf: form.price_rwf,
        timeline_days: Number(form.timeline_days), scope_notes: form.scope_notes,
      }),
    })
    await loadActivity()
    notify('Quote sent to the client.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not send your quote.')
  }
}

async function acceptQuote(quoteId: string) {
  try {
    await api(`/quotes/${quoteId}/accept/`, { method: 'POST', body: '{}' })
    await loadActivity()
    notify('Quote accepted. Your booking is confirmed.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not accept this quote.')
  }
}

async function updateBooking(booking: Booking, status: string, reportText = '') {
  try {
    await api(`/bookings/${booking.id}/transition/`, { method: 'POST', body: jsonBody({ status, report_text: reportText }) })
    await loadActivity()
    notify('Project status updated.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not update this project.')
  }
}

async function leaveReview(booking: Booking) {
  const rating = Number(window.prompt('Rate this completed survey (1–5):', '5'))
  if (!Number.isInteger(rating) || rating < 1 || rating > 5) return
  const comment = window.prompt('Share a short review (optional):', '') ?? ''
  try {
    await api('/reviews/', { method: 'POST', body: jsonBody({ booking: booking.id, rating, comment }) })
    await loadActivity()
    notify('Thank you. Your review has been saved.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not save your review.')
  }
}

async function createSupportTicket() {
  if (!requireAccount()) return
  try {
    await api('/support-tickets/', { method: 'POST', body: jsonBody(supportForm) })
    dialog.value = null
    Object.assign(supportForm, { subject: '', message: '' })
    notify('Support ticket created. You can track it in My activity.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not create support ticket.')
  }
}

async function createComplaint() {
  if (!detailListing.value || !requireAccount()) return
  try {
    await api('/complaints/', { method: 'POST', body: jsonBody({ ...complaintForm, listing: detailListing.value.id }) })
    dialog.value = null
    Object.assign(complaintForm, { subject: '', details: '' })
    notify('Thank you. Your report has been sent for review.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not submit your report.')
  }
}

async function loadAdmin() {
  try {
    adminData.value = await api('/admin/dashboard/')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not load the admin dashboard.')
  }
}

async function moderate(type: string, id: string, decision: string) {
  const reason = decision === 'reject' ? window.prompt('Please enter a rejection reason:') ?? '' : ''
  if (decision === 'reject' && !reason.trim()) return notify('A rejection reason is required.')
  try {
    await api('/admin/dashboard/', { method: 'PATCH', body: jsonBody({ type, id, decision, reason }) })
    await loadAdmin()
    notify('Moderation decision saved and recorded.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not save this decision.')
  }
}

async function saveSurveyorProfile() {
  try {
    const data = await api<Surveyor>('/surveyor-profiles/me/', {
      method: 'PATCH',
      body: jsonBody({ ...surveyorForm, services: surveyorForm.services.split(',').map((item) => item.trim()).filter(Boolean), years_experience: Number(surveyorForm.years_experience) }),
    })
    surveyorDocuments.value = data.documents
    notify(`Profile saved · verification: ${data.verification_status}.`)
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not save your surveyor profile.')
  }
}

async function openSurveyorProfile() {
  if (!requireAccount() || user.value?.role !== 'surveyor') return
  try {
    const profile = await api<Surveyor>('/surveyor-profiles/me/')
    Object.assign(surveyorForm, {
      bio: profile.bio,
      qualifications: profile.qualifications,
      licence_number: profile.licence_number,
      service_areas: profile.service_areas,
      services: profile.services.join(', '),
      years_experience: String(profile.years_experience),
    })
    surveyorDocuments.value = profile.documents
    dialog.value = 'surveyor-profile'
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not load your surveyor profile.')
  }
}

async function uploadSurveyorDocument() {
  if (!surveyorDocumentFile.value) {
    notify('Choose a verification document to upload.')
    return
  }
  const formData = new FormData()
  formData.set('document_type', surveyorDocumentType.value)
  formData.set('file', surveyorDocumentFile.value)
  try {
    await api('/surveyor-documents/', { method: 'POST', body: formData })
    surveyorDocumentFile.value = null
    const input = document.getElementById('surveyor-document-file') as HTMLInputElement | null
    if (input) input.value = ''
    const profile = await api<Surveyor>('/surveyor-profiles/me/')
    surveyorDocuments.value = profile.documents
    notify('Verification document uploaded to private storage.')
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not upload this document.')
  }
}

async function downloadSurveyorDocument(documentId: string, filename: string) {
  try {
    const response = await fetch(`${API_BASE}/surveyor-documents/${documentId}/download/`, {
      headers: { Authorization: `Token ${getToken()}` },
    })
    if (!response.ok) throw new Error('You do not have access to this document.')
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not download this document.')
  }
}

function moneyLink(listing: Listing, provider: 'maps' | 'earth' | 'directions') {
  const destination = `${listing.latitude},${listing.longitude}`
  const urls = {
    maps: `https://www.google.com/maps/search/?api=1&query=${destination}`,
    earth: `https://earth.google.com/web/@${listing.latitude},${listing.longitude},1200a,1000d,35y,0h,0t,0r`,
    directions: `https://www.google.com/maps/dir/?api=1&destination=${destination}`,
  }
  return urls[provider]
}

function shareListing(listing: Listing) {
  const url = moneyLink(listing, 'maps')
  if (navigator.share) void navigator.share({ title: listing.title, url }).catch(() => undefined)
  else void navigator.clipboard.writeText(url).then(() => notify('Map link copied to clipboard.')).catch(() => notify(url))
}

function useMyLocation() {
  if (!navigator.geolocation) {
    notify('Location is not supported by this browser.')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      focus.value = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        label: 'Your location',
      }
    },
    () => notify('Location permission was not granted.'),
  )
}

async function downloadSurveyReport(booking: Booking) {
  try {
    const text = await api<string>(`/bookings/${booking.id}/download_report/`)
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `survey-report-${booking.id}.txt`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    notify(error instanceof Error ? error.message : 'Could not download the survey report.')
  }
}

function submitSurveyReport(booking: Booking) {
  const reportText = window.prompt('Enter your survey report summary (at least 20 characters):')
  if (reportText === null) return
  void updateBooking(booking, 'report_submitted', reportText)
}

onMounted(async () => {
  await refreshSession()
  await Promise.all([loadListings(), loadSurveyors()])
})
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <button class="brand-lockup" type="button" @click="openView('home')">
        <span class="brand-mark"><span></span><span></span><span></span></span>
        <span class="brand-type"><strong>rwanda<span>market</span></strong><small>LAND · HOMES · SURVEY</small></span>
      </button>
      <div class="sidebar-caption">EXPLORE</div>
      <nav class="side-nav" aria-label="Main navigation">
        <button v-for="item in navItems.slice(0, 4)" :key="item.id" class="nav-link" :class="{ selected: view === item.id }" @click="openView(item.id)">
          <span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span>
        </button>
        <div v-if="user" class="sidebar-caption second-caption">YOUR ACCOUNT</div>
        <button v-for="item in navItems.slice(4)" :key="item.id" class="nav-link" :class="{ selected: view === item.id }" @click="openView(item.id)">
          <span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span>
        </button>
        <button v-if="user?.role === 'seller'" class="nav-link" :class="{ selected: view === 'activity' }" @click="openView('activity')">
          <span class="nav-icon">◫</span><span>Seller dashboard</span>
        </button>
        <button v-if="user?.role === 'surveyor'" class="nav-link" @click="openSurveyorProfile">
          <span class="nav-icon">✳</span><span>My surveyor profile</span>
        </button>
        <button v-if="isAdmin" class="nav-link" :class="{ selected: view === 'admin' }" @click="openView('admin')">
          <span class="nav-icon">▤</span><span>Admin dashboard</span>
        </button>
      </nav>
      <div class="sidebar-bottom">
        <div class="sidebar-help">
          <span class="help-icon">?</span>
          <strong>Need a hand?</strong>
          <p>Our team is here to help you find your way.</p>
          <button type="button" @click="openView('support')">Visit help centre <span>↗</span></button>
        </div>
        <div class="side-legal">© 2026 RwandaMarket <span>·</span> Made for Rwanda</div>
      </div>
    </aside>

    <section class="main-shell">
      <header class="topbar">
        <div class="crumb"><span>Rwanda</span><i>›</i><strong>{{ currentTitle }}</strong></div>
        <div class="top-actions">
          <div class="market-status"><span class="live-dot"></span> <span>{{ t('all_rwanda') }}</span></div>
          <label class="language-picker" aria-label="Language">
            <span>文</span>
            <select :value="language" @change="changeLanguage(($event.target as HTMLSelectElement).value)">
              <option value="rw">RW</option><option value="en">EN</option><option value="fr">FR</option>
            </select>
          </label>
          <button v-if="!user" class="text-action" type="button" @click="authMode = 'login'; dialog = 'auth'">{{ t('sign_in') }}</button>
          <button v-if="user?.role === 'seller'" class="primary-small" type="button" @click="openListingForm">＋ {{ t('post_listing') }}</button>
          <button v-if="user?.role === 'client'" class="primary-small" type="button" @click="dialog = 'request'">＋ Request a survey</button>
          <button v-if="user" class="account-chip" type="button" @click="openView('activity')">
            <span class="avatar">{{ (user.first_name || user.email)[0]?.toUpperCase() }}</span>
            <span class="account-name">{{ user.first_name || user.email.split('@')[0] }}</span><span class="chevron">⌄</span>
          </button>
          <button v-if="user" class="icon-top" :title="t('logout')" @click="signOut">↪</button>
          <button v-else class="primary-small" type="button" @click="authMode = 'register'; dialog = 'auth'">{{ t('join') }}</button>
        </div>
      </header>

      <main class="content">
        <section v-if="view === 'home'" class="home-view">
          <div class="hero">
            <img class="hero-image" src="https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=2200&q=88" alt="A modern home in the green hills" />
            <div class="hero-shade"></div>
            <div class="hero-content">
              <div class="eyebrow hero-eyebrow"><span class="eyebrow-line"></span>{{ t('hero_kicker') }}</div>
              <h1>{{ t('hero_title') }}</h1>
              <p>{{ t('hero_text') }}</p>
              <form class="hero-search" @submit.prevent="openView('listings')">
                <span class="search-icon">⌕</span>
                <input v-model="search" :placeholder="t('search_placeholder')" aria-label="Search listings" />
                <button type="submit">{{ t('search_button') }} <span>→</span></button>
              </form>
              <div class="hero-quick">
                <button type="button" @click="typeFilter = 'land'; openView('listings')"><span>▱</span>{{ t('land') }}</button>
                <button type="button" @click="typeFilter = 'house'; openView('listings')"><span>⌂</span>{{ t('house') }}</button>
                <button type="button" @click="openView('surveyors')"><span>⌖</span>{{ t('nav_surveyors') }}</button>
              </div>
            </div>
            <div class="hero-stamp"><span>RW</span><i>·</i> {{ t('all_rwanda') }}<b>↗</b></div>
          </div>

          <div class="trust-strip">
            <div class="trust-icon">✳</div>
            <div><strong>{{ t('trust_title') }}</strong><p>{{ t('trust_text') }}</p></div>
            <span class="trust-badge"><span>✓</span>{{ t('trust_badge') }}</span>
          </div>

          <section class="section-block">
            <div class="section-heading">
              <div><div class="eyebrow"><span class="eyebrow-line"></span> A PLACE TO BEGIN</div><h2>{{ t('featured') }}</h2></div>
              <button class="view-all" type="button" @click="openView('listings')">{{ t('view_all') }} <span>→</span></button>
            </div>
            <div class="listing-grid">
              <article v-for="(listing, index) in featuredListings" :key="listing.id" class="property-card">
                <button class="property-photo" type="button" @click="detailListing = listing" :aria-label="`View ${listing.title}`">
                  <img :src="photo(listing)" :alt="listing.title" :class="`photo-${index + 1}`" />
                  <span class="type-chip">{{ listing.property_type === 'land' ? t('land') : t('house') }}</span>
                  <span v-if="listing.is_verified" class="verified-chip">✓ {{ t('verified') }}</span>
                  <span v-else class="unverified-chip">{{ t('unverified') }}</span>
                </button>
                <button class="save-property" type="button" :aria-label="favourites.includes(listing.id) ? 'Remove saved property' : 'Save property'" @click.stop="toggleFavourite(listing)">{{ favourites.includes(listing.id) ? '♥' : '♡' }}</button>
                <div class="property-info">
                  <div class="property-meta"><span>{{ [listing.village, listing.cell, listing.sector, listing.district, listing.province].filter(Boolean).join(', ') }}</span><span>·</span><span>{{ displayArea(listing.area_sqm) }}</span></div>
                  <button class="property-title" type="button" @click="detailListing = listing">{{ listing.title }}</button>
                  <div class="property-bottom"><strong>{{ money(listing.price_rwf) }}</strong><button type="button" @click="showMap(listing)">View map ↗</button></div>
                </div>
              </article>
              <div v-if="loading && !featuredListings.length" class="empty-state">{{ t('loading') }}</div>
              <div v-else-if="!featuredListings.length" class="empty-state">{{ t('empty') }}</div>
            </div>
            <p class="sample-note">ⓘ {{ t('demo_notice') }}</p>
          </section>

          <section class="map-promo">
            <div class="map-promo-copy"><div class="eyebrow light-eyebrow"><span class="eyebrow-line"></span> LAND INTELLIGENCE</div><h2>{{ t('map_title') }}</h2><p>{{ t('map_subtitle') }}</p><button class="light-button" type="button" @click="openView('map')">Explore the map <span>→</span></button></div>
            <div class="map-promo-art">
              <div class="map-grid"></div><div class="map-contour contour-a"></div><div class="map-contour contour-b"></div>
              <div class="map-pin pin-a">⌂</div><div class="map-pin pin-b">⌂</div><div class="map-pin pin-c">⌖</div>
              <div class="map-card-float"><span class="mini-status"></span> Kigali City <strong>Explore area ↗</strong></div>
              <div class="map-coordinate">01°56'39.2"S<br>30°03'43.0"E</div>
            </div>
          </section>

          <section class="section-block steps-section">
            <div class="section-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span> A BETTER WAY TO BEGIN</div><h2>{{ t('how_title') }}</h2></div></div>
            <div class="steps-grid">
              <div v-for="(step, index) in [t('how_1'), t('how_2'), t('how_3'), t('how_4')]" :key="step" class="step-item">
                <span class="step-no">0{{ index + 1 }}</span><div class="step-rule"></div><p>{{ step }}</p>
              </div>
            </div>
          </section>
          <section class="survey-cta">
            <div><div class="eyebrow"><span class="eyebrow-line"></span> INDEPENDENT PROFESSIONALS</div><h2>{{ t('surveyors_heading') }}</h2><p>Find a specialist in boundary, topographic, cadastral, drone and GIS surveys.</p></div>
            <button type="button" @click="openView('surveyors')">Meet the professionals <span>→</span></button>
          </section>
        </section>

        <section v-else-if="view === 'listings'" class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> BUY · SELL · INVEST</div><h1>{{ t('nav_listings') }}</h1><p>Thoughtful places, all across Rwanda.</p></div><button v-if="user?.role === 'seller'" class="primary-small" @click="openListingForm">＋ {{ t('post_listing') }}</button></div>
          <div class="search-filter-bar">
            <form class="compact-search" @submit.prevent="loadListings"><span>⌕</span><input v-model="search" :placeholder="t('search_placeholder')" /><button>{{ t('search_button') }}</button></form>
            <button class="filter-toggle" type="button" @click="filterMenuOpen = !filterMenuOpen">☷ {{ t('filter') }} <span>⌄</span></button>
            <div v-if="filterMenuOpen" class="filter-popover">
              <label>Property type<select v-model="typeFilter"><option value="all">{{ t('all') }}</option><option value="land">{{ t('land') }}</option><option value="house">{{ t('house') }}</option></select></label>
              <label>{{ t('district') }}<input v-model="districtFilter" placeholder="Gasabo, Musanze…" /></label>
              <button type="button" class="primary-small" @click="filterMenuOpen = false; loadListings()">Apply filters</button>
              <button type="button" class="filter-clear" @click="typeFilter = 'all'; districtFilter = ''; filterMenuOpen = false; loadListings()">Clear all</button>
            </div>
          </div>
          <div class="listing-grid listing-grid-large">
            <article v-for="(listing, index) in filteredListings" :key="listing.id" class="property-card">
              <button class="property-photo" type="button" @click="detailListing = listing">
                <img :src="photo(listing)" :alt="listing.title" :class="`photo-${(index % 3) + 1}`" />
                <span class="type-chip">{{ listing.property_type === 'land' ? t('land') : t('house') }}</span>
                <span v-if="listing.is_verified" class="verified-chip">✓ {{ t('verified') }}</span><span v-else class="unverified-chip">{{ t('unverified') }}</span>
              </button>
              <button class="save-property" type="button" @click.stop="toggleFavourite(listing)">{{ favourites.includes(listing.id) ? '♥' : '♡' }}</button>
              <div class="property-info"><div class="property-meta"><span>{{ [listing.village, listing.cell, listing.sector, listing.district, listing.province].filter(Boolean).join(', ') }}</span><span>·</span><span>{{ displayArea(listing.area_sqm) }}</span></div>
                <button class="property-title" type="button" @click="detailListing = listing">{{ listing.title }}</button>
                <div class="property-bottom"><strong>{{ money(listing.price_rwf) }}</strong><button type="button" @click="showMap(listing)">View map ↗</button></div>
              </div>
            </article>
          </div>
          <div v-if="!filteredListings.length" class="empty-card"><span>⌕</span><h3>No matching listings</h3><p>Try a different district or clear your filters.</p><button @click="search = ''; districtFilter = ''; typeFilter = 'all'; loadListings()">Clear search</button></div>
          <p class="sample-note">ⓘ {{ t('demo_notice') }}</p>
        </section>

        <section v-else-if="view === 'surveyors'" class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> INDEPENDENT EXPERTS</div><h1>{{ t('surveyors_heading') }}</h1><p>Compare verified professionals by experience, service and area.</p></div><button v-if="user?.role === 'client'" class="primary-small" @click="dialog = 'request'">＋ Request a survey</button><button v-else-if="!user" class="primary-small" @click="authMode = 'register'; dialog = 'auth'">Join as a surveyor</button><button v-else-if="user.role === 'surveyor'" class="primary-small" @click="openSurveyorProfile">Edit my profile</button></div>
          <div class="surveyor-banner"><div class="surveyor-banner-icon">⌖</div><div><strong>Independent, not employed by RwandaMarket.</strong><p>Only profiles approved by an administrator can carry the Verified badge or quote on a request.</p></div><span class="survey-count">{{ surveyors.length }} verified profiles</span></div>
          <div class="surveyor-grid">
            <article v-for="(surveyor, index) in surveyors" :key="surveyor.id" class="surveyor-card">
              <div class="surveyor-card-top"><div class="surveyor-avatar" :class="`surveyor-avatar-${index % 4}`">{{ surveyor.full_name.split(' ').map((name) => name[0]).slice(0, 2).join('').toUpperCase() }}</div><span class="verified-label">✓ Verified</span></div>
              <h3>{{ surveyor.full_name }}</h3><p class="survey-qual">{{ surveyor.qualifications || 'Licensed land surveyor' }}</p>
              <div class="survey-rating"><span>★</span> {{ surveyor.rating?.toFixed(1) ?? 'New' }} <small>· {{ surveyor.completed_jobs }} jobs</small></div>
              <p class="surveyor-bio">{{ surveyor.bio || 'Independent surveyor serving Rwanda. Contact to discuss your land survey requirements.' }}</p>
              <div class="service-tags"><span v-for="service in surveyor.services.slice(0, 3)" :key="service">{{ service }}</span></div>
              <div class="surveyor-location">⌖ {{ surveyor.service_areas || 'Rwanda' }}</div>
              <button v-if="user?.role === 'client'" class="surveyor-contact" @click="dialog = 'request'; requestForm.location = surveyor.service_areas">Request a quote <span>→</span></button>
              <button v-else class="surveyor-contact" @click="requireAccount('Sign in as a client to request a quote.')">Request a quote <span>→</span></button>
            </article>
          </div>
          <div v-if="!surveyors.length" class="empty-card"><span>⌖</span><h3>Verified surveyors are on their way</h3><p>Profiles appear here after document review. No surveyor is shown as verified before approval.</p><button v-if="!user" @click="authMode = 'register'; dialog = 'auth'">Register as a surveyor</button></div>
        </section>

        <section v-else-if="view === 'map'" class="page-view map-page">
          <div class="map-page-heading"><div><div class="eyebrow"><span class="eyebrow-line"></span> RWANDA · LAND INTELLIGENCE</div><h1>{{ t('map_title') }}</h1><p>{{ t('map_subtitle') }}</p></div><button v-if="user?.role === 'client'" class="primary-small" @click="dialog = 'request'">＋ Request a survey</button></div>
          <div class="map-search-row">
            <form class="map-search" @submit.prevent="searchMap"><span>⌕</span><input v-model="surveyMapSearch" :placeholder="t('search_placeholder') + ' · coordinates'" /><button type="submit">Search map</button></form>
            <button class="location-button" @click="useMyLocation">◎ Use my location</button>
          </div>
          <div class="map-content-grid"><MapPanel :listings="filteredListings" :focus="focus" @select="(listing) => { selectedListing = listing }" />
            <aside class="map-side-panel">
              <div class="map-side-head"><div><strong>{{ selectedListing ? 'Selected property' : 'Visible places' }}</strong><span>{{ selectedListing ? selectedListing.district + ', Rwanda' : `${filteredListings.length} listings on map` }}</span></div><button v-if="selectedListing" class="subtle-close" @click="selectedListing = null">×</button></div>
              <template v-if="selectedListing">
                <img class="map-side-photo" :src="photo(selectedListing)" :alt="selectedListing.title" />
                <div class="map-side-details"><span class="small-caps">{{ selectedListing.is_verified ? t('verified') : t('unverified') }} · {{ selectedListing.property_type }}</span><h3>{{ selectedListing.title }}</h3><p>{{ [selectedListing.village, selectedListing.cell, selectedListing.sector, selectedListing.district, selectedListing.province].filter(Boolean).join(', ') }}</p><strong>{{ money(selectedListing.price_rwf) }}</strong><span class="side-area">{{ displayArea(selectedListing.area_sqm) }}</span></div>
                <div class="map-data-card"><div class="data-row"><span>UPI</span><strong>{{ selectedListing.upi || 'Not available' }}</strong></div><div class="data-row"><span>Data source</span><strong>Seller listing</strong></div><div class="data-row"><span>Verification</span><strong>{{ selectedListing.is_verified ? 'Admin reviewed' : 'Not independently verified' }}</strong></div><div class="data-row"><span>Zoning</span><strong>Not available</strong></div></div>
                <div class="map-out-links"><a :href="moneyLink(selectedListing, 'maps')" target="_blank" rel="noopener">Google Maps ↗</a><a :href="moneyLink(selectedListing, 'earth')" target="_blank" rel="noopener">Google Earth ↗</a><a :href="moneyLink(selectedListing, 'directions')" target="_blank" rel="noopener">Directions ↗</a><button type="button" @click="shareListing(selectedListing!)">Share ↗</button></div>
                <button class="report-cta" @click="orderReport(selectedListing!)">Create report preview <span>→</span></button>
              </template>
              <template v-else>
                <button v-for="listing in filteredListings.slice(0, 5)" :key="listing.id" class="map-result" @click="selectedListing = listing; focus = { latitude: Number(listing.latitude), longitude: Number(listing.longitude) }">
                  <img :src="photo(listing)" :alt="listing.title" /><span><strong>{{ listing.title }}</strong><small>{{ listing.district }} · {{ money(listing.price_rwf) }}</small></span><b>→</b>
                </button>
                <p v-if="!filteredListings.length" class="map-no-results">Search a place or enter coordinates to move the map pin. Official parcel search is not connected.</p>
                <div class="map-legend"><strong>MAP DATA STATUS</strong><p><span class="legend-dot green-dot"></span> Listing location · seller supplied</p><p><span class="legend-dot gray-dot"></span> UPI and zoning · not connected</p></div>
              </template>
              <p class="map-provider-note">{{ t('source_notice') }}</p>
            </aside>
          </div>
          <div class="map-disclaimer">ⓘ {{ t('map_not_official') }} {{ t('footer_disclaimer') }}</div>
        </section>

        <section v-else-if="view === 'activity'" class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> YOUR RWANDAMARKET</div><h1>{{ t('nav_activity') }}</h1><p>Stay on top of your property journey.</p></div><button v-if="user?.role === 'seller'" class="primary-small" @click="openListingForm">＋ {{ t('post_listing') }}</button><button v-if="user?.role === 'client'" class="primary-small" @click="dialog = 'request'">＋ New survey request</button><button v-if="user?.role === 'surveyor'" class="primary-small" @click="openSurveyorProfile">Edit profile</button></div>
          <div v-if="user?.role === 'client'" class="activity-stats"><div><span>OPEN REQUESTS</span><strong>{{ surveyRequests.filter((item) => item.status !== 'completed').length }}</strong></div><div><span>ACTIVE BOOKINGS</span><strong>{{ bookings.filter((item) => !['completed', 'cancelled'].includes(item.status)).length }}</strong></div><div><span>SAVED PLACES</span><strong>{{ favourites.length }}</strong></div></div>
          <div v-if="user?.role === 'seller'" class="activity-stats"><div><span>MY LISTINGS</span><strong>{{ listings.filter((item) => item.owner === user?.id).length }}</strong></div><div><span>PENDING REVIEW</span><strong>{{ listings.filter((item) => item.owner === user?.id && item.status === 'pending_review').length }}</strong></div><div><span>VIEWS</span><strong>{{ listings.filter((item) => item.owner === user?.id).reduce((sum, item) => sum + item.views, 0) }}</strong></div></div>
          <div v-if="user?.role === 'surveyor'" class="activity-stats"><div><span>OPEN REQUESTS</span><strong>{{ surveyRequests.length }}</strong></div><div><span>ACTIVE PROJECTS</span><strong>{{ bookings.filter((item) => !['completed', 'cancelled'].includes(item.status)).length }}</strong></div><div><span>COMPLETED</span><strong>{{ bookings.filter((item) => item.status === 'completed').length }}</strong></div></div>
          <section v-if="user?.role === 'client' || user?.role === 'surveyor'" class="activity-section">
            <div class="activity-section-head"><div><h2>{{ user.role === 'client' ? 'Your survey requests' : 'Requests open for quote' }}</h2><p>{{ user.role === 'client' ? 'Compare offers and choose the right surveyor.' : 'Respond to requests in your verified service areas.' }}</p></div><span class="section-count">{{ surveyRequests.length }} total</span></div>
            <article v-for="request in surveyRequests" :key="request.id" class="request-card">
              <div class="request-icon">⌖</div><div class="request-main"><div class="request-head"><strong>{{ request.service }}</strong><span class="status-pill" :class="`status-${request.status}`">{{ request.status.replace('_', ' ') }}</span></div><p>{{ request.location }} <span v-if="request.upi">· UPI {{ request.upi }}</span></p><p class="request-description">{{ request.description }}</p><div class="request-metadata"><span>Submitted {{ new Date(request.created_at).toLocaleDateString() }}</span><span v-if="request.budget_rwf">Budget {{ money(request.budget_rwf) }}</span></div></div>
              <div v-if="user?.role === 'surveyor'" class="quote-form">
                <template v-if="!request.quotes.some((quote) => quote.surveyor === user?.id)">
                  <input v-model="(quoteForm[request.id] ??= { price_rwf: '', timeline_days: '7', scope_notes: '' }).price_rwf" inputmode="numeric" placeholder="Price (RWF)" />
                  <input v-model="(quoteForm[request.id] ??= { price_rwf: '', timeline_days: '7', scope_notes: '' }).timeline_days" type="number" min="1" placeholder="Days" />
                  <input v-model="(quoteForm[request.id] ??= { price_rwf: '', timeline_days: '7', scope_notes: '' }).scope_notes" placeholder="Scope notes" />
                  <button @click="sendQuote(request)">Send quote</button>
                </template><span v-else class="quote-sent">Quote sent ✓</span>
              </div>
              <div v-else-if="request.quotes.length" class="quote-list"><div v-for="quote in request.quotes" :key="quote.id" class="quote-row"><div><strong>{{ quote.surveyor_name }}</strong><small>{{ quote.timeline_days }} days · {{ quote.scope_notes }}</small></div><b>{{ money(quote.price_rwf) }}</b><button v-if="request.status !== 'booked' && request.status !== 'completed'" @click="acceptQuote(quote.id)">Accept quote</button><span v-else-if="quote.status === 'accepted'" class="accepted-label">✓ Booked</span><span v-else class="closed-label">{{ quote.status }}</span></div></div>
              <div v-else class="no-quotes">{{ user?.role === 'client' ? 'Waiting for surveyor quotes' : 'No quote yet' }}</div>
            </article>
            <div v-if="!surveyRequests.length" class="empty-card small-empty"><h3>{{ user?.role === 'client' ? 'No survey requests yet' : 'No requests available' }}</h3><p>{{ user?.role === 'client' ? 'Create a request to compare quotes from verified surveyors.' : 'New matching survey requests will appear here.' }}</p><button v-if="user?.role === 'client'" @click="dialog = 'request'">Request a survey</button><button v-else @click="openSurveyorProfile">Complete your profile</button></div>
          </section>
          <section v-if="user?.role === 'seller'" class="activity-section"><div class="activity-section-head"><div><h2>Your listings</h2><p>Track review, enquiries and listing visibility.</p></div></div>
            <article v-for="listing in listings.filter((item) => item.owner === user?.id)" :key="listing.id" class="seller-listing-row"><img :src="photo(listing)" :alt="listing.title" /><div><strong>{{ listing.title }}</strong><span>{{ listing.district }} · {{ money(listing.price_rwf) }}</span></div><span class="status-pill" :class="`status-${listing.status}`">{{ listing.status.replace('_', ' ') }}</span><span>{{ listing.views }} views · {{ listing.enquiry_count }} enquiries</span></article>
            <div v-if="!listings.some((item) => item.owner === user?.id)" class="empty-card small-empty"><h3>Start with your first listing</h3><p>Your listing stays private until it passes review.</p><button @click="openListingForm">Create listing</button></div>
          </section>
          <section v-if="bookings.length" class="activity-section"><div class="activity-section-head"><div><h2>Survey projects</h2><p>Project tracking from booking through report and review.</p></div></div>
            <article v-for="booking in bookings" :key="booking.id" class="booking-card"><div class="booking-card-main"><div class="booking-heading"><strong>{{ booking.request.service }} · {{ booking.request.location }}</strong><span class="status-pill" :class="`status-${booking.status}`">{{ booking.status.replace('_', ' ') }}</span></div><p>{{ user?.role === 'client' ? `Surveyor · ${booking.surveyor_name}` : `Client · ${booking.client_name}` }} · {{ money(booking.quote.price_rwf) }}</p>
              <div v-if="booking.report_text" class="report-text"><strong>Surveyor's report</strong><p>{{ booking.report_text }}</p><button @click="downloadSurveyReport(booking)">Download report</button></div>
            </div>
            <div class="booking-actions" v-if="user?.role === 'surveyor'">
              <button v-if="booking.status === 'booked'" @click="updateBooking(booking, 'in_progress')">Start project</button>
              <button v-if="booking.status === 'in_progress'" @click="submitSurveyReport(booking)">Submit report</button>
            </div>
            <div class="booking-actions" v-if="user?.role === 'client'">
              <button v-if="booking.status === 'report_submitted'" @click="updateBooking(booking, 'completed')">Confirm completion</button>
              <button v-if="booking.status === 'completed' && !booking.has_review" @click="leaveReview(booking)">Leave a review</button>
            </div>
          </article>
          </section>
          <section v-if="reports.length" class="activity-section"><div class="activity-section-head"><div><h2>Your report previews</h2><p>Property research reports you have requested.</p></div><button class="view-all" @click="openView('reports')">View all →</button></div><div class="report-list compact-reports"><div v-for="report in reports.slice(0, 3)" :key="report.id" class="report-row"><div class="report-file-icon">▤</div><div><strong>Property Insight Report · {{ report.location || 'Property' }}</strong><span>{{ new Date(report.created_at).toLocaleDateString() }} · Preview · Payment not configured</span></div><button @click="downloadReport(report)">Download PDF ↓</button></div></div></section>
        </section>

        <section v-else-if="view === 'reports'" class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> PROPERTY INTELLIGENCE</div><h1>{{ t('nav_reports') }}</h1><p>Reports separate seller-submitted information from unavailable official data.</p></div></div>
          <div class="report-warning"><span>ⓘ</span><div><strong>Preview only · payment provider not connected</strong><p>Official UPI and Master Plan datasets are not available. This report never invents parcel details, ownership or zoning.</p></div></div>
          <div v-if="reports.length" class="report-list"><div v-for="report in reports" :key="report.id" class="report-row"><div class="report-file-icon">▤</div><div><strong>Property Insight Report · {{ report.location || 'Property' }}</strong><span>Created {{ new Date(report.created_at).toLocaleDateString() }} · {{ report.status }} · {{ report.payment_status.replace('_', ' ') }}</span><small>{{ report.source_note }}</small></div><button @click="downloadReport(report)">Download PDF ↓</button></div></div>
          <div v-else class="empty-card"><span>▤</span><h3>No reports yet</h3><p>Create a preview from any published property listing or a map location.</p><button @click="openView('listings')">Explore listings</button></div>
          <div class="report-footnote">Property Insight Reports are decision aids, not government decisions, title deeds or proof of ownership. Master Plan information is not a building permit.</div>
        </section>

        <section v-else-if="view === 'admin'" class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> PLATFORM OVERSIGHT</div><h1>Admin dashboard</h1><p>Review and record decisions for surveyors and property listings.</p></div><a class="admin-link" href="/admin/" target="_blank" rel="noopener">Open Django admin ↗</a></div>
          <template v-if="adminData">
            <div class="admin-stats"><div><span>ACCOUNTS</span><strong>{{ adminData.users }}</strong></div><div><span>SURVEYORS TO REVIEW</span><strong>{{ adminData.surveyors_pending }}</strong></div><div><span>LISTINGS TO REVIEW</span><strong>{{ adminData.listings_pending }}</strong></div><div><span>OPEN COMPLAINTS</span><strong>{{ adminData.open_complaints }}</strong></div></div>
            <section class="activity-section"><div class="activity-section-head"><div><h2>Listings awaiting review</h2><p>Approve only after checking the listing information.</p></div></div>
              <article v-for="listing in (adminData.listings as Listing[])" :key="listing.id" class="moderation-row"><img :src="photo(listing)" :alt="listing.title" /><div><strong>{{ listing.title }}</strong><span>{{ listing.district }} · {{ money(listing.price_rwf) }} · {{ listing.owner_name }}</span></div><button class="approve-button" @click="moderate('listing', listing.id, 'approve')">Approve</button><button class="reject-button" @click="moderate('listing', listing.id, 'reject')">Reject</button></article>
              <div v-if="!(adminData.listings as Listing[]).length" class="empty-inline">No listings need review.</div>
            </section>
            <section class="activity-section"><div class="activity-section-head"><div><h2>Surveyors awaiting verification</h2><p>Documents must be reviewed before a profile receives the Verified badge.</p></div></div>
              <article v-for="profile in (adminData.surveyors as Surveyor[]).filter((item) => item.verification_status === 'pending')" :key="profile.id" class="moderation-row surveyor-moderation"><div class="surveyor-avatar">{{ profile.full_name.split(' ').map((name) => name[0]).slice(0, 2).join('') }}</div><div><strong>{{ profile.full_name }}</strong><span>{{ profile.qualifications || 'Qualification not provided' }} · {{ profile.service_areas || 'Service area not provided' }}</span><small>Licence reference: {{ profile.licence_number || 'Not provided' }}</small><span v-for="document in profile.documents" :key="document.id" class="moderation-document"><button type="button" @click="downloadSurveyorDocument(document.id, document.original_filename)">Review {{ document.document_type }} · {{ document.status }} ↗</button></span><small v-if="!profile.documents.length">Upload and review at least one certificate before verification.</small></div><button class="approve-button" :disabled="!profile.documents.length" :title="!profile.documents.length ? 'A private verification document is required' : 'Verify this surveyor'" @click="moderate('surveyor', profile.id, 'approve')">Verify</button><button class="reject-button" @click="moderate('surveyor', profile.id, 'reject')">Reject</button></article>
              <div v-if="!(adminData.surveyors as Surveyor[]).some((item) => item.verification_status === 'pending')" class="empty-inline">No surveyors need review.</div>
            </section>
            <section class="activity-section"><div class="activity-section-head"><div><h2>Recent audit activity</h2><p>Important moderation actions are recorded.</p></div></div><div class="audit-table"><div v-for="entry in (adminData.audit_logs as Array<Record<string, string>>)" :key="entry.id"><span>{{ entry.action }}</span><span>{{ entry.object_type }} · {{ entry.object_id }}</span><span>{{ entry.actor__username || 'System' }}</span><span>{{ new Date(entry.created_at).toLocaleString() }}</span></div><p v-if="!(adminData.audit_logs as Array<unknown>).length" class="empty-inline">No administrative actions have been recorded.</p></div></section>
          </template>
          <div v-else class="empty-card"><p>Loading admin workspace…</p></div>
        </section>

        <section v-else class="page-view">
          <div class="page-heading-row"><div><div class="eyebrow"><span class="eyebrow-line"></span> WE’RE HERE TO HELP</div><h1>{{ t('nav_support') }}</h1><p>Questions about listings, surveyors or land information? Send us a message.</p></div></div>
          <div class="support-layout"><div class="support-info-card"><span class="support-big-icon">✳</span><h2>How can we help?</h2><p>Send a support request and track its status from your account. For urgent matters, contact the platform administrator.</p><div class="support-hours"><span>SUPPORT HOURS</span><strong>Monday – Friday</strong><small>Response times depend on platform availability.</small></div><div class="support-caveat">RwandaMarket is a marketplace. Surveyors are independent professionals and are not employed by the platform.</div></div>
            <form class="support-form" @submit.prevent="createSupportTicket"><h2>Send a support request</h2><label>Subject<input v-model="supportForm.subject" required maxlength="180" placeholder="What can we help with?" /></label><label>Message<textarea v-model="supportForm.message" required maxlength="3000" rows="6" placeholder="Tell us a little more…" /></label><button class="primary-small" type="submit">Send request →</button></form></div>
        </section>

        <footer class="main-footer"><span>© 2026 O.M.N RwandaMarket</span><span>{{ t('footer_disclaimer') }}</span><button type="button" @click="openView('support')">Support</button></footer>
      </main>
    </section>
    <div class="mobile-nav">
      <button v-for="item in navItems.slice(0, 5)" :key="item.id" :class="{ selected: view === item.id }" @click="openView(item.id)"><span>{{ item.icon }}</span>{{ item.label.split(' ')[0] }}</button>
    </div>

    <div v-if="dialog" class="modal-backdrop" @click.self="dialog = null">
      <section v-if="dialog === 'auth'" class="modal auth-modal">
        <button class="modal-close" @click="dialog = null" aria-label="Close">×</button>
        <div class="modal-brand"><span class="brand-mark"><span></span><span></span><span></span></span><strong>rwanda<span>market</span></strong></div>
        <div class="eyebrow"><span class="eyebrow-line"></span> A PLACE TO BEGIN</div><h2>{{ authMode === 'login' ? 'Welcome back.' : 'Make yourself at home.' }}</h2><p class="modal-intro">{{ authMode === 'login' ? 'Sign in to pick up where you left off.' : 'Join RwandaMarket and take your next step.' }}</p>
        <form class="modal-form" novalidate @submit.prevent="submitAuth">
          <div v-if="authMode === 'register'" class="two-fields"><label>First name<input v-model="authForm.first_name" autocomplete="given-name" /><span v-if="!authForm.first_name.trim()" class="field-hint field-hint-error">First name is required.</span></label><label>Last name<input v-model="authForm.last_name" autocomplete="family-name" /><span v-if="!authForm.last_name.trim()" class="field-hint field-hint-error">Last name is required.</span></label></div>
          <label>Email address
            <input v-model="authForm.email" type="email" autocomplete="email" placeholder="you@example.com" :aria-invalid="!authEmailValid" />
            <span v-if="!authEmailValid" class="field-hint field-hint-error">{{ authForm.email ? 'Enter a valid email address.' : 'Email address is required.' }}</span>
          </label>
          <label>Password
            <span v-if="authMode === 'login'" class="field-hint">Enter the password you used when you created your account.</span>
            <span class="password-control">
              <input v-model="authForm.password" :type="showPassword ? 'text' : 'password'" :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'" :aria-invalid="!authPasswordValid" />
              <button type="button" class="password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" :aria-pressed="showPassword" @click="showPassword = !showPassword">{{ showPassword ? 'Hide' : 'Show' }}</button>
            </span>
            <span v-if="authMode === 'login' && !authPasswordValid" class="field-hint field-hint-error">Password is required.</span>
            <span v-if="authMode === 'register'" class="field-hint">Use a password that meets all the requirements below.</span>
            <span v-if="authMode === 'register' && !authForm.password" class="field-hint field-hint-error">Password is required.</span>
            <ul v-if="authMode === 'register'" class="password-rules" aria-live="polite">
              <li v-for="rule in authPasswordRules" :key="rule.label" :class="{ 'password-rule-valid': rule.valid }"><span aria-hidden="true">{{ rule.valid ? '✓' : '○' }}</span>{{ rule.label }}</li>
            </ul>
          </label>
          <div v-if="authMode === 'register'" class="two-fields"><label>Join as<select v-model="authForm.role"><option value="client">Client / buyer</option><option value="seller">Seller / agent</option><option value="surveyor">Surveyor</option></select></label><label>Language<select v-model="authForm.language"><option value="rw">Kinyarwanda</option><option value="en">English</option><option value="fr">Français</option></select></label></div>
          <div v-if="authError" class="form-error">{{ authError }}</div>
          <button class="modal-primary" type="submit" :disabled="!authFormValid">{{ authMode === 'login' ? 'Sign in securely' : 'Create my account' }} <span>→</span></button>
        </form>
        <p class="switch-auth">{{ authMode === 'login' ? 'New to RwandaMarket?' : 'Already have an account?' }} <button type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'; authError = ''; showPassword = false">{{ authMode === 'login' ? 'Create an account' : 'Sign in' }}</button></p>
        <p class="verification-note">Email and phone verification providers are not configured. Do not rely on verification status for a real transaction in this demo.</p>
      </section>

      <section v-else-if="dialog === 'listing-photos'" class="modal form-modal listing-photos-modal">
        <button class="modal-close" @click="finishListingPhotos" aria-label="Finish adding listing photos">×</button>
        <div class="eyebrow"><span class="eyebrow-line"></span> LISTING SUBMITTED</div>
        <h2>Add photos to {{ createdListing?.title }}</h2>
        <p class="modal-intro">Your listing is awaiting review. Add up to 10 JPEG, PNG or WebP photos (5 MB each) to help people see the property.</p>
        <label class="photo-picker">＋ Choose photos
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple :disabled="listingPhotosUploading || uploadedListingPhotos.length + listingPhotoDrafts.length >= 10" @change="selectListingPhotos" />
        </label>
        <div v-if="listingPhotoDrafts.length" class="listing-photo-grid">
          <figure v-for="(photoDraft, index) in listingPhotoDrafts" :key="photoDraft.previewUrl">
            <img :src="photoDraft.previewUrl" :alt="photoDraft.file.name" />
            <figcaption>{{ photoDraft.file.name }}<button type="button" @click="removeListingPhoto(index)">Remove</button></figcaption>
          </figure>
        </div>
        <div v-if="uploadedListingPhotos.length" class="listing-photo-grid">
          <figure v-for="(photoUrl, index) in uploadedListingPhotos" :key="photoUrl">
            <img :src="photoUrl" :alt="`Listing photo ${index + 1}`" />
            <figcaption>Photo {{ index + 1 }} uploaded</figcaption>
          </figure>
        </div>
        <p v-if="listingPhotoError" class="form-error" role="alert">{{ listingPhotoError }}</p>
        <div class="photo-step-actions">
          <button class="modal-primary" type="button" :disabled="!listingPhotoDrafts.length || listingPhotosUploading" @click="uploadListingPhotos">{{ listingPhotosUploading ? 'Uploading…' : `Upload ${listingPhotoDrafts.length || ''} selected photo${listingPhotoDrafts.length === 1 ? '' : 's'}` }} <span>↑</span></button>
          <button class="secondary-button" type="button" @click="finishListingPhotos">Finish</button>
        </div>
      </section>

      <section v-else-if="dialog === 'listing'" class="modal form-modal">
        <button class="modal-close" @click="dialog = null">×</button><div class="eyebrow"><span class="eyebrow-line"></span> SELL WITH CONFIDENCE</div><h2>Create a property listing</h2><p class="modal-intro">Listings stay private until an administrator reviews them. A seller-submitted listing is not independently verified.</p>
        <form class="modal-form" @submit.prevent="submitListing">
          <label>Listing title<input v-model="listingForm.title" required maxlength="180" placeholder="e.g. Hillside residential plot in Gasabo" /></label>
          <label>Description<textarea v-model="listingForm.description" required maxlength="5000" rows="3" /></label>
          <div class="two-fields"><label>Property type<select v-model="listingForm.property_type"><option value="land">Land</option><option value="house">House</option></select></label><label>Price (RWF)<input v-model="listingForm.price_rwf" type="number" min="0" required /></label></div>
          <label>Province / city<select v-model="listingForm.province" required :disabled="listingLocationsLoading"><option disabled value="">{{ listingLocationsLoading ? 'Loading locations…' : 'Choose a province' }}</option><option v-for="province in availableProvinces" :key="province" :value="province">{{ province }}</option></select></label>
          <div class="two-fields">
            <label>District<select v-model="listingForm.district" required :disabled="!listingForm.province"><option disabled value="">Choose a district</option><option v-for="district in availableDistricts" :key="district.name" :value="district.name">{{ district.name }}</option></select></label>
            <label>Sector<select v-model="listingForm.sector" required :disabled="!listingForm.district"><option disabled value="">Choose a sector</option><option v-for="sector in availableSectors" :key="sector.name" :value="sector.name">{{ sector.name }}</option></select></label>
          </div>
          <div class="two-fields">
            <label>Cell<select v-model="listingForm.cell" required :disabled="!listingForm.sector"><option disabled value="">Choose a cell</option><option v-for="cell in availableCells" :key="cell.name" :value="cell.name">{{ cell.name }}</option></select></label>
            <label>Village<select v-model="listingForm.village" required :disabled="!listingForm.cell"><option disabled value="">Choose a village</option><option v-for="(village, index) in availableVillages" :key="`${village}-${index}`" :value="village">{{ village }}</option></select></label>
          </div>
          <div class="two-fields"><label>Latitude<input v-model="listingForm.latitude" type="number" step="any" min="-90" max="90" required /></label><label>Longitude<input v-model="listingForm.longitude" type="number" step="any" min="-180" max="180" required /></label></div>
          <label>UPI (optional)<input v-model="listingForm.upi" /></label>
          <button class="modal-primary" type="submit">Submit for review <span>→</span></button>
        </form>
      </section>

      <section v-else-if="dialog === 'request'" class="modal form-modal">
        <button class="modal-close" @click="dialog = null">×</button><div class="eyebrow"><span class="eyebrow-line"></span> FIND YOUR SURVEYOR</div><h2>Request a land survey</h2><p class="modal-intro">Your request is shared with verified surveyors. Compare quotes and choose one before a booking is created.</p>
        <form class="modal-form" @submit.prevent="submitSurveyRequest">
          <label>Survey service<select v-model="requestForm.service"><option>Boundary survey</option><option>Topographic survey</option><option>Cadastral survey</option><option>Drone survey</option><option>GIS and mapping</option><option>Construction survey</option></select></label>
          <label>Location<input v-model="requestForm.location" required placeholder="District, sector or landmark" /></label>
          <div class="two-fields"><label>Latitude (optional)<input v-model="requestForm.latitude" type="number" step="any" /></label><label>Longitude (optional)<input v-model="requestForm.longitude" type="number" step="any" /></label></div>
          <label>UPI (optional)<input v-model="requestForm.upi" placeholder="Only if you already have one" /></label>
          <label>What do you need?<textarea v-model="requestForm.description" required rows="3" maxlength="3000" /></label>
          <div class="two-fields"><label>Preferred date<input v-model="requestForm.desired_date" type="date" /></label><label>Budget (RWF, optional)<input v-model="requestForm.budget_rwf" type="number" min="0" /></label></div>
          <button class="modal-primary" type="submit">Send survey request <span>→</span></button>
        </form>
      </section>

      <section v-else-if="dialog === 'enquiry'" class="modal form-modal">
        <button class="modal-close" @click="dialog = null">×</button><div class="eyebrow"><span class="eyebrow-line"></span> CONTACT THE SELLER</div><h2>Ask about this place</h2><p class="modal-intro">{{ detailListing?.title }}</p>
        <form class="modal-form" @submit.prevent="sendEnquiry"><label>Your message<textarea v-model="enquiryText" required maxlength="2000" rows="5" placeholder="Ask a question or arrange a viewing…" /></label><button class="modal-primary" type="submit">Send enquiry <span>→</span></button></form>
      </section>

      <section v-else-if="dialog === 'complaint'" class="modal form-modal">
        <button class="modal-close" @click="dialog = null">×</button><div class="eyebrow"><span class="eyebrow-line"></span> HELP KEEP THE MARKET SAFE</div><h2>Report this listing</h2><form class="modal-form" @submit.prevent="createComplaint"><label>Reason<select v-model="complaintForm.subject"><option>Incorrect information</option><option>Possible fraud</option><option>Duplicate listing</option><option>Other concern</option></select></label><label>Details<textarea v-model="complaintForm.details" required maxlength="3000" rows="4" /></label><button class="modal-primary" type="submit">Send report <span>→</span></button></form></section>

      <section v-else-if="dialog === 'surveyor-profile'" class="modal form-modal">
        <button class="modal-close" @click="dialog = null">×</button><div class="eyebrow"><span class="eyebrow-line"></span> PROFESSIONAL PROFILE</div><h2>Your surveyor profile</h2><p class="modal-intro">Your profile remains pending until an administrator reviews at least one uploaded verification document.</p>
        <form class="modal-form" @submit.prevent="saveSurveyorProfile"><label>About you<textarea v-model="surveyorForm.bio" rows="3" maxlength="3000" /></label><label>Qualifications<input v-model="surveyorForm.qualifications" /></label><div class="two-fields"><label>Licence reference<input v-model="surveyorForm.licence_number" /></label><label>Years of experience<input v-model="surveyorForm.years_experience" type="number" min="0" max="80" /></label></div><label>Service areas<input v-model="surveyorForm.service_areas" placeholder="Gasabo, Kicukiro, Rwanda" /></label><label>Services (separate with commas)<input v-model="surveyorForm.services" /></label><button class="modal-primary" type="submit">Save profile <span>→</span></button></form>
        <div class="document-upload"><strong>Private verification documents</strong><p>PDF, JPEG or PNG · up to 5 MB. Only you and administrators can access these files.</p><div class="document-upload-row"><select v-model="surveyorDocumentType"><option value="licence">Professional licence</option><option value="qualification">Qualification</option><option value="identity">Identity document</option><option value="other">Other</option></select><input id="surveyor-document-file" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" @change="surveyorDocumentFile = ($event.target as HTMLInputElement).files?.[0] ?? null" /><button type="button" class="primary-small" @click="uploadSurveyorDocument">Upload</button></div><div v-for="document in surveyorDocuments" :key="document.id" class="document-item"><span>{{ document.document_type }} · {{ document.status }}</span><small>{{ document.original_filename }}</small></div></div>
      </section>

      <section v-else-if="dialog === 'support'" class="modal form-modal"><button class="modal-close" @click="dialog = null">×</button><h2>Contact support</h2><p class="modal-intro">Sign in to create a trackable support ticket.</p><button class="modal-primary" @click="dialog = null; openView('support')">Go to support centre <span>→</span></button></section>
    </div>

    <div v-if="detailListing" class="modal-backdrop detail-backdrop" @click.self="detailListing = null">
      <section class="modal listing-detail-modal">
        <button class="modal-close" @click="detailListing = null">×</button>
        <img class="detail-cover" :src="photo(detailListing)" :alt="detailListing.title" />
        <div class="detail-body"><div class="eyebrow"><span class="eyebrow-line"></span>{{ [detailListing.village, detailListing.cell, detailListing.sector, detailListing.district, detailListing.province].filter(Boolean).join(', ') }}</div><h2>{{ detailListing.title }}</h2><div class="detail-price">{{ money(detailListing.price_rwf) }} <span>· {{ displayArea(detailListing.area_sqm) }}</span></div>
          <div class="detail-trust">{{ detailListing.is_verified ? '✓ Reviewed by platform administrator' : 'ⓘ Seller-submitted · not independently verified' }}</div><p class="detail-description">{{ detailListing.description }}</p>
          <div class="detail-meta"><span>UPI <strong>{{ detailListing.upi || 'Not provided' }}</strong></span><span>Seller <strong>{{ detailListing.owner_name }}</strong></span><span>Location <strong>{{ detailListing.sector ? `${detailListing.sector}, ` : '' }}{{ detailListing.district }}</strong></span><span>Data source <strong>Seller submission</strong></span></div>
          <div class="detail-buttons"><button class="modal-primary" @click="detailListing = detailListing; enquiryText = ''; dialog = 'enquiry'">{{ t('contact') }} <span>→</span></button><button class="secondary-button" @click="showMap(detailListing!); detailListing = null">View on map</button><button class="secondary-button" @click="orderReport(detailListing!)">{{ t('report') }}</button></div>
          <div class="detail-lower"><button @click="shareListing(detailListing!)">Share location ↗</button><button @click="dialog = 'complaint'">Report this listing</button></div>
        </div>
      </section>
    </div>

    <transition name="toast"><div v-if="toast" class="toast-message"><span>✓</span>{{ toast }}<button @click="toast = ''">×</button></div></transition>
  </div>
</template>
