import { memo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import useStore from '../../store/useStore'
import useEarthquakeStore from '../../store/useEarthquakeStore'
import GlassPanel from './GlassPanel'
import MagnitudeBadge from './MagnitudeBadge'
import { timeAgo, formatDepth } from '../../utils/formatters'
import { getMagnitudeColor } from '../../utils/magnitudeScale'

function getMagnitudeLabel(mag) {
    if (mag < 2) return 'Micro'
    if (mag < 4) return 'Minor'
    if (mag < 5) return 'Light'
    if (mag < 6) return 'Moderate'
    if (mag < 7) return 'Strong'
    if (mag < 8) return 'Major'
    return 'Great'
}

function getDepthLabel(depth) {
    if (depth < 70) return 'Shallow'
    if (depth < 300) return 'Intermediate'
    return 'Deep'
}

const DetailCard = memo(function DetailCard() {
    const showDetail = useStore((s) => s.ui.showDetail)
    const setUI = useStore((s) => s.setUI)
    const selectedQuake = useStore((s) => s.selectedQuake)
    const setSelectedQuake = useStore((s) => s.setSelectedQuake)
    const earthquakes = useEarthquakeStore((s) => s.earthquakes)
    const setCameraTarget = useStore((s) => s.setCameraTarget)
    const modalRef = useRef(null)

    useEffect(() => {
      if (showDetail && modalRef.current) {
        const closeBtn = modalRef.current.querySelector('.detail-close')
        if (closeBtn) closeBtn.focus()
      }
    }, [showDetail])

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape' && showDetail) {
                setUI({ showDetail: false })
                setSelectedQuake(null)
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [showDetail, setUI, setSelectedQuake])

    if (!selectedQuake) return null

    const quakeDate = new Date(selectedQuake.time)
    const localTime = quakeDate.toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
    })
    const utcTime = quakeDate.toISOString().replace('.000', '')

    const nearby = earthquakes
        .filter(q => q.id !== selectedQuake.id)
        .map(q => {
            const dLat = q.lat - selectedQuake.lat
            const dLng = q.lng - selectedQuake.lng
            const dist = Math.sqrt(dLat * dLat + dLng * dLng) * 111
            return { ...q, dist }
        })
        .filter(q => q.dist < 500)
        .sort((a, b) => a.dist - b.dist)
        .slice(0, 3)

    const handleNearbyClick = (quake) => {
        setSelectedQuake(quake)
        const depthTilt = quake.depth > 70 ? Math.min(25, quake.depth / 10) : 0
        setCameraTarget({ lat: quake.lat - depthTilt, lng: quake.lng, zoom: 2.0 })
    }

    const magColor = getMagnitudeColor(selectedQuake.magnitude)

    return (
        <AnimatePresence>
            {showDetail && (
                <div
                    className="detail-modal-overlay"
                    onClick={() => { setUI({ showDetail: false }); setSelectedQuake(null) }}
                    style={{ pointerEvents: 'auto' }}
                    role="dialog"
                    aria-modal="true"
                    aria-label={`Magnitude ${selectedQuake.magnitude.toFixed(1)} earthquake details, ${selectedQuake.place}`}
                >
                    <motion.div
                        ref={modalRef}
                        onClick={(e) => e.stopPropagation()}
                        initial={{ scale: 0.9, opacity: 0, y: 20 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        exit={{ scale: 0.9, opacity: 0, y: 20 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                        className="detail-card-container pointer-events-auto"
                    >
                        <GlassPanel className="detail-card">

                            <button
                                onClick={() => { setUI({ showDetail: false }); setSelectedQuake(null) }}
                                className="detail-close"
                                aria-label="Close earthquake details"
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </button>

                            <div className="detail-content no-scrollbar">

                                <div className="detail-header">
                                    <div className="detail-mag-row">
                                        <span className="detail-mag-val mono" style={{ color: magColor }}>
                                            {selectedQuake.magnitude.toFixed(1)}
                                        </span>
                                        <span className="detail-mag-label">
                                            {getMagnitudeLabel(selectedQuake.magnitude)}
                                        </span>
                                    </div>
                                    <h2 className="detail-place">
                                        {selectedQuake.place}
                                    </h2>
                                    <div className="detail-coords mono">
                                        {Math.abs(selectedQuake.lat).toFixed(4)}&deg;{selectedQuake.lat >= 0 ? 'N' : 'S'}, {Math.abs(selectedQuake.lng).toFixed(4)}&deg;{selectedQuake.lng >= 0 ? 'E' : 'W'}
                                    </div>
                                </div>

                                {selectedQuake.tsunami && (
                                    <div className="detail-warning">
                                        <span className="warning-icon">&#9888;</span>
                                        <span className="warning-text">Tsunami Warning Issued</span>
                                    </div>
                                )}

                                <div className="detail-depth-box">
                                    <div className="detail-depth-indicator">
                                        <motion.div
                                            initial={{ top: 0, opacity: 0 }}
                                            animate={{ top: `${Math.min(100, (selectedQuake.depth / 700) * 100)}%`, opacity: 1 }}
                                            transition={{ type: 'spring', delay: 0.2 }}
                                            className="depth-pip"
                                        />
                                    </div>
                                    <div className="detail-depth-info">
                                        <span className="detail-label">Depth</span>
                                        <span className="detail-depth-val mono">
                                            {formatDepth(selectedQuake.depth)}
                                        </span>
                                        <span className="detail-depth-cat">
                                            {getDepthLabel(selectedQuake.depth)}
                                        </span>
                                        <span className="detail-depth-range">Surface to 700km</span>
                                    </div>
                                </div>

                                <div className="detail-time-box">
                                    <span className="detail-label block">Origin time</span>
                                    <div className="detail-local-time">{localTime}</div>
                                    <div className="detail-utc-time mono">{utcTime}</div>
                                </div>

                                {selectedQuake.felt && (
                                    <div className="detail-felt-box">
                                        <span className="detail-felt-text">
                                            Reported felt by <strong>{selectedQuake.felt}</strong> people
                                        </span>
                                    </div>
                                )}

                                {nearby.length > 0 && (
                                    <div className="detail-nearby-box">
                                        <span className="detail-label block">
                                            Nearby activity — {nearby.length} quake{nearby.length !== 1 ? 's' : ''} within 500 km
                                        </span>
                                        <div className="detail-nearby-list">
                                            {nearby.map(q => (
                                                <div
                                                    key={q.id}
                                                    onClick={() => handleNearbyClick(q)}
                                                    className="detail-nearby-item"
                                                >
                                                    <MagnitudeBadge magnitude={q.magnitude} />
                                                    <div className="detail-nearby-info">
                                                        <div className="detail-nearby-place">{q.place.split(' of ').pop()}</div>
                                                        <div className="detail-nearby-dist mono">{Math.round(q.dist)} km away</div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                <div className="detail-footer">
                                    <a
                                        href={selectedQuake.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="detail-usgs-link"
                                    >
                                        View on USGS
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <line x1="5" y1="12" x2="19" y2="12"></line>
                                            <polyline points="12 5 19 12 12 19"></polyline>
                                        </svg>
                                    </a>
                                </div>
                            </div>

                        </GlassPanel>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
})

export default DetailCard
