import { memo } from 'react'
import { motion } from 'motion/react'

const GlassPanel = memo(function GlassPanel({ children, className = '', style = {}, ...props }) {
  return (
    <motion.div
      className={`glass-panel ${className}`}
      style={style}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      {...props}
    >
      {children}
    </motion.div>
  )
})

export default GlassPanel
