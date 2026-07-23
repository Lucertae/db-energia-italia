/**
 * useStore.js
 * 
 * Manages the global UI state of the application using Zustand.
 * Handles camera targeting, filters, playback controls, and general UI visibility flags.
 * Note: Earthquake data itself is managed separately in useEarthquakeStore.js.
 */

import { create } from 'zustand'
import { LOADING_PHASES } from '../constants'

const useStore = create((set, get) => ({
  // --- Loading State ---
  isLoading: true,
  loadingMessage: 'Initializing...',
  setIsLoading: (isLoading) => set({ isLoading }),
  setLoadingMessage: (loadingMessage) => set({ loadingMessage }),

  loadingPhase: LOADING_PHASES.LOADING_PARTICLES,
  particleProgress: 0,
  setLoadingPhase: (phase) => set({ loadingPhase: phase }),
  setParticleProgress: (progress) => set({ particleProgress: progress }),

  performanceMode: 'full',
  setPerformanceMode: (mode) => set({ performanceMode: mode }),

  selectedQuake: null,
  setSelectedQuake: (quake) => set({ selectedQuake: quake }),

  cameraTarget: { lat: 20, lng: 0, zoom: 2.8 },
  setCameraTarget: (target) => set({ cameraTarget: { ...get().cameraTarget, ...target } }),

  filters: {
    magnitude: 0,
    timeRange: 'day',
    depth: 'all',
    viewMode: 'points',
    layers: {
      quakes: true,
      fires: true,
      flights: true,
      ais: true,
      conflicts: true,
      natural: true,
      cyber: true,
      climate: true,
      other: true,
    },
  },
  setFilter: (key, value) => set({
    filters: { ...get().filters, [key]: value }
  }),
  toggleLayer: (id) => set({
    filters: {
      ...get().filters,
      layers: {
        ...get().filters.layers,
        [id]: !get().filters.layers[id],
      },
    },
  }),

  playback: {
    isPlaying: false,
    speed: 1,
    progress: 1.0, // 0.0 = oldest earthquake, 1.0 = newest (all visible)
  },
  setPlayback: (updates) => set({
    playback: { ...get().playback, ...updates }
  }),

  ui: {
    showAnalytics: false,
    showDetail: false,
    showFilters: true,
    showPerf: false,
    showKeyboardHints: false,
    globeReady: false,
    showStats: true,
    showFeed: true,
    hudCollapsed: false,
    feedExpanded: false,
    isFetchingData: false,
  },
  setUI: (updates) => set({
    ui: { ...get().ui, ...updates }
  }),
}))

export default useStore
