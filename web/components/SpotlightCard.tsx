'use client'
import { useRef, useCallback } from 'react'
import { motion, useMotionValue, useTransform } from 'framer-motion'

interface Props {
  children: React.ReactNode
  className?: string
  color?: string
  style?: React.CSSProperties
}

export function SpotlightCard({ children, className = '', color = 'rgba(59,130,246,0.13)', style }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const mouseX = useMotionValue(-999)
  const mouseY = useMotionValue(-999)

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    mouseX.set(e.clientX - rect.left)
    mouseY.set(e.clientY - rect.top)
  }, [mouseX, mouseY])

  const handleMouseLeave = useCallback(() => {
    mouseX.set(-999)
    mouseY.set(-999)
  }, [mouseX, mouseY])

  const spotlight = useTransform(
    [mouseX, mouseY],
    ([x, y]: number[]) =>
      `radial-gradient(260px circle at ${x}px ${y}px, ${color}, transparent 70%)`
  )

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`relative group ${className}`}
      style={style}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: spotlight, zIndex: 0 }}
      />
      <div className="relative z-10 h-full">{children}</div>
    </motion.div>
  )
}
