<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Listing } from './types'

type MapCoordinates = { latitude: number; longitude: number }

const props = defineProps<{
  listings: Listing[]
  focus?: { latitude: number; longitude: number; label?: string } | null
  pinMode?: boolean
  pin?: MapCoordinates | null
}>()
const emit = defineEmits<{
  select: [listing: Listing]
  pick: [coordinates: MapCoordinates]
}>()
const host = ref<HTMLDivElement | null>(null)
const layer = ref<'street' | 'master'>('street')
let map: L.Map | undefined
let pins: L.LayerGroup | undefined
let pinMarker: L.Marker | undefined
const kigali: L.LatLngExpression = [-1.9441, 30.0619]

function renderPins() {
  if (!map || !pins) return
  pins.clearLayers()
  for (const listing of props.listings) {
    const lat = Number(listing.latitude)
    const lng = Number(listing.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue
    const marker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'property-marker',
        html: `<span>RWF ${Number(listing.price_rwf).toLocaleString('en')}</span>`,
        iconSize: [112, 30],
        iconAnchor: [56, 30],
      }),
    })
    marker.bindPopup(`<strong>${escapeHtml(listing.title)}</strong><br>${escapeHtml(listing.district)} · ${Number(listing.area_sqm).toLocaleString()} m²`)
    marker.on('click', () => emit('select', listing))
    marker.addTo(pins)
  }
}

function escapeHtml(text: string) {
  return text.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char] ?? char)
}

function centerOnFocus() {
  if (!map || !props.focus) return
  map.flyTo([props.focus.latitude, props.focus.longitude], 15, { duration: 0.6 })
}

function renderPin() {
  if (!map) return
  if (!props.pin) {
    pinMarker?.remove()
    pinMarker = undefined
    return
  }
  const position: L.LatLngExpression = [props.pin.latitude, props.pin.longitude]
  if (pinMarker) {
    pinMarker.setLatLng(position)
    return
  }
  pinMarker = L.marker(position, { draggable: props.pinMode }).addTo(map)
  pinMarker.on('dragend', () => {
    const point = pinMarker?.getLatLng()
    if (point) emit('pick', { latitude: point.lat, longitude: point.lng })
  })
}

onMounted(() => {
  if (!host.value) return
  map = L.map(host.value, { zoomControl: false }).setView(kigali, 9)
  map.on('click', (event: L.LeafletMouseEvent) => {
    if (props.pinMode) emit('pick', { latitude: event.latlng.lat, longitude: event.latlng.lng })
  })
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  pins = L.layerGroup().addTo(map)
  renderPins()
  renderPin()
  centerOnFocus()
})

watch(() => props.listings, renderPins)
watch(() => props.focus, centerOnFocus, { deep: true })
watch(() => props.pin, renderPin, { deep: true })
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div class="map-frame" :class="{ 'pin-picker-map': pinMode }">
    <div ref="host" class="leaflet-map" aria-label="Interactive map of property listings in Rwanda"></div>
    <div v-if="!pinMode" class="map-tools">
      <button class="map-toggle active" type="button" @click="layer = 'street'">Street map</button>
      <button class="map-toggle" type="button" @click="layer = 'master'" :class="{ active: layer === 'master' }">Master Plan</button>
    </div>
    <div v-if="layer === 'master'" class="map-layer-note">
      <strong>Official planning data</strong>
      <span>No authorised Master Plan dataset is available, so zoning is not displayed.</span>
      <small>Planning information does not replace a building permit.</small>
    </div>
    <div class="map-attribution-note">Map pins are indicative only · Street map © OpenStreetMap</div>
  </div>
</template>
