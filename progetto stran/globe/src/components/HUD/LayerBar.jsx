import { memo } from 'react'
import { GLOBE_LAYERS } from '../../constants'
import useStore from '../../store/useStore'

export default memo(function LayerBar() {
  const layers = useStore((s) => s.filters.layers)
  const toggleLayer = useStore((s) => s.toggleLayer)
  const globeReady = useStore((s) => s.ui.globeReady)
  if (!globeReady) return null

  return (
    <div className="layer-bar" aria-label="Map layers">
      <span className="layer-bar-title">LAYERS</span>
      {GLOBE_LAYERS.map((L) => {
        const on = layers[L.id] !== false
        return (
          <button
            key={L.id}
            type="button"
            className={`layer-chip ${on ? 'layer-chip--on' : ''}`}
            style={{ '--layer-color': L.color }}
            onClick={() => toggleLayer(L.id)}
            aria-pressed={on}
          >
            {L.label}
          </button>
        )
      })}
    </div>
  )
})
