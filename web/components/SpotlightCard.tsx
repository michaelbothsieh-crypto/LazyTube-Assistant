'use client'
import { useRef, useCallback } from 'react'

interface Props {
  children: React.ReactNode
  className?: string
  color?: string
  style?: React.CSSProperties
}

export function SpotlightCard({ children, className = '', color = 'rgba(59,130,246,0.13)', style }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect || !overlayRef.current) return
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    overlayRef.current.style.background =
      `radial-gradient(260px circle at ${x}px ${y}px, ${color}, transparent 70%)`
  }, [color])

  const handleMouseLeave = useCallback(() => {
    if (overlayRef.current) overlayRef.current.style.background = 'transparent'
  }, [])

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={`relative group ${className}`}
      style={style}
    >
      <div
        ref={overlayRef}
        className="pointer-events-none absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ zIndex: 0 }}
      />
      <div className="relative z-10 h-full">{children}</div>
    </div>
  )
}
