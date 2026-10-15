import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import type { Look, Pose } from './sprites'
import { SPRITE_H, SPRITE_W, spriteShadow } from './sprites'

export const STAGE_W = 1440
export const STAGE_H = 900

/** The game is drawn on a fixed 1440x900 stage, scaled to fit the window
 * (laptop browsers; pixel art stays crisp at any scale). */
export function Stage({ children, background = '#16130f' }: { children: ReactNode; background?: string }) {
  const scale = useFit()
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'grid', placeItems: 'center', background: '#0e0c0a', overflow: 'hidden' }}>
      <div style={{ width: STAGE_W * scale, height: STAGE_H * scale, position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: STAGE_W,
            height: STAGE_H,
            transform: `scale(${scale})`,
            transformOrigin: '0 0',
            overflow: 'hidden',
            background,
          }}
        >
          {children}
        </div>
      </div>
    </div>
  )
}

/** A see-through layer over whatever Stage is showing, in the same 1440x900
 * coordinates. Clicks pass through except on children that opt back in. */
export function StageOverlay({ children }: { children: ReactNode }) {
  const scale = useFit()
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'grid', placeItems: 'center', pointerEvents: 'none', zIndex: 100 }}>
      <div style={{ width: STAGE_W * scale, height: STAGE_H * scale, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, width: STAGE_W, height: STAGE_H, transform: `scale(${scale})`, transformOrigin: '0 0' }}>
          {children}
        </div>
      </div>
    </div>
  )
}

function useFit(): number {
  const [scale, setScale] = useState(fit)
  useEffect(() => {
    const onResize = () => setScale(fit())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return scale
}

function fit(): number {
  return Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H)
}

/** A pixel trader whose feet stand at (x, feet). */
export function Trader({
  x,
  feet,
  s,
  pose,
  look,
  className,
  style,
  children,
  onClick,
  title,
  flip,
}: {
  x: number
  feet: number
  s: number
  pose: Pose
  look: Look
  className?: string
  style?: CSSProperties
  children?: ReactNode
  onClick?: () => void
  title?: string
  flip?: boolean // face left
}) {
  return (
    <div
      className={className}
      onClick={onClick}
      title={title}
      style={{
        position: 'absolute',
        left: x,
        top: feet - SPRITE_H * s,
        width: SPRITE_W * s,
        height: SPRITE_H * s,
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}
    >
      <div
        style={{
          position: 'absolute', left: 0, top: 0, width: s, height: s, boxShadow: spriteShadow(pose, look, s),
          transform: flip ? 'scaleX(-1)' : undefined, transformOrigin: `${(SPRITE_W * s) / 2}px 0`,
        }}
      />
      {children}
    </div>
  )
}

export function Badge({ text, look, style }: { text: string; look: Look; style?: CSSProperties }) {
  return (
    <div
      className="silk"
      style={{
        position: 'absolute',
        left: '50%',
        transform: 'translateX(-50%)',
        padding: '1px 6px',
        fontSize: 12,
        whiteSpace: 'nowrap',
        background: look.jacket,
        color: look.fg ?? '#16130f',
        border: '2px solid #16130f',
        ...style,
      }}
    >
      {text}
    </div>
  )
}

/** Small label + big amber number, as on the LED boards. */
export function LedCell({ label, value, size = 40, align = 'left' }: { label: string; value: ReactNode; size?: number; align?: 'left' | 'right' }) {
  return (
    <div style={{ textAlign: align }}>
      <div style={{ fontSize: 13, color: 'var(--color-led-dim)' }}>{label}</div>
      <div style={{ fontSize: size, lineHeight: 1 }}>{value}</div>
    </div>
  )
}
