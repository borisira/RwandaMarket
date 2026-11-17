<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Listing } from './types'

const props = defineProps<{
  listings: Listing[]
  focus?: { latitude: number; longitude: number; label?: string } | null
}>()
const emit = defineEmits<{ select: [listing: Listing] }>()
const host = ref<HTMLDivElement | null>(null)
const layer = ref<'street' | 'master'>('street')
let map: L.Map | undefined
let pins: L.LayerGroup | undefined
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

onMounted(() => {
  if (!host.value) return
  map = L.map(host.value, { zoomControl: false }).setView(kigali, 9)
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map)
  pins = L.layerGroup().addTo(map)
  renderPins()
  centerOnFocus()
})

watch(() => props.listings, renderPins)
watch(() => props.focus, centerOnFocus, { deep: true })
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div class="map-frame">
    <div ref="host" class="leaflet-map" aria-label="Interactive map of property listings in Rwanda"></div>
    <div class="map-tools">
      <button class="map-toggle active" type="button" @click="layer = 'street'">Street map</button>
      <button class="map-toggle" type="button" @click="layer = 'master'" :class="{ active: layer === 'master' }">Master Plan</button>
    </div>
    <div v-if="layer === 'master'" class="map-layer-note">
      <strong>Official layer unavailable</strong>
      <span>No licensed Master Plan dataset is connected. No zoning is shown.</span>
      <small>Master Plan data is not a building permit.</small>
    </div>
    <div class="map-attribution-note">Map pins are indicative only · Street map © OpenStreetMap</div>
  </div>
</template>
