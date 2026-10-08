// The pit from above: an octagon of steps, the crowd as tokens, the players
// with their badges, and you at the front. The round camera dives into it at
// the bell and pulls back out of it at the close.

import { memo, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { PlayerInfo } from '../types'
import { crowdLook, playerLook, tokenShadow } from './sprites'

export const CX = 720
export const CY = 430
export const YOU_X = 720
export const YOU_Y = 790

const OCT = 'polygon(29% 0,71% 0,100% 29%,100% 71%,71% 100%,29% 100%,0 71%,0 29%)'
const RINGS: [number, string][] = [
  [850, '#2a2c25'],
  [836, '#8b9079'],
  [672, '#7a7f69'],
  [520, '#6a6f5b'],
  [366, '#565a49'],
]
const PAPER = ['#d9d4c3', '#d8c464', '#e9e4d4', '#c9c3b0']

const at = (r: number, deg: number): [number, number] => [CX + r * Math.cos((deg * Math.PI) / 180), CY + r * Math.sin((deg * Math.PI) / 180)]

interface Props {
  others: PlayerInfo[]
  me: PlayerInfo | undefined
  paper: number // scraps on the floor
  className?: string
  paperClass?: string
  banners?: ReactNode
}

export const Overhead = memo(function Overhead({ others, me, paper, className, paperClass, banners }: Props) {
  const crowd = useMemo(() => {
    const radii = [384, 330, 277, 224, 177]
    const out: { x: number; y: number; i: number }[] = []
    for (let i = 0; i < 74; i++) {
      const [x, y] = at(radii[i % radii.length], (i * 47 + (i % 5) * 9) % 360)
      if (Math.hypot(x - YOU_X, y - YOU_Y) < 56) continue
      out.push({ x: Math.round(x), y: Math.round(y), i })
    }
    return out
  }, [])

  const scraps = useMemo(() => {
    const out: { x: number; y: number; w: number; h: number; c: string; r: number }[] = []
    for (let i = 0; i < paper; i++) {
      const [x, y] = at(30 + ((i * 53) % 390), (i * 79 + Math.floor(i / 360) * 11) % 360)
      out.push({ x: Math.round(x), y: Math.round(y), w: 8 + (i % 3) * 4, h: 5 + (i % 2) * 3, c: PAPER[i % 4], r: ((i * 37) % 70) - 35 })
    }
    return out
  }, [paper])

  // Players stand on the far rings, facing you.
  const seats = others.map((p, k) => {
    const deg = 200 + ((k + 0.5) * 140) / Math.max(1, others.length)
    const [x, y] = at(250, deg)
    return { p, x: Math.round(x), y: Math.round(y) }
  })

  return (
    <div className={className} style={{ position: 'absolute', inset: 0 }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: '#5f6556',
          backgroundImage: 'linear-gradient(#565b4d 2px, transparent 2px), linear-gradient(90deg, #565b4d 2px, transparent 2px)',
          backgroundSize: '40px 40px',
        }}
      />
      {RINGS.map(([s, c]) => (
        <div key={s} style={{ position: 'absolute', left: CX - s / 2, top: CY - s / 2, width: s, height: s, background: c, clipPath: OCT }} />
      ))}
      <div className={paperClass} style={{ position: 'absolute', inset: 0 }}>
        {scraps.map((p, i) => (
          <div key={i} style={{ position: 'absolute', left: p.x, top: p.y, width: p.w, height: p.h, background: p.c, transform: `rotate(${p.r}deg)` }} />
        ))}
      </div>
      {crowd.map(({ x, y, i }) => (
        <Token key={i} x={x} y={y} shadow={tokenShadow(crowdLook(i * 5), i % 3 === 0)} />
      ))}
      {seats.map(({ p, x, y }) => {
        const look = playerLook(p.look)
        return (
          <Token key={p.id} x={x} y={y} shadow={tokenShadow(look, true)}>
            <div
              className="silk"
              style={{ position: 'absolute', left: '50%', top: -22, transform: 'translateX(-50%)', padding: '0 5px', fontSize: 11, background: look.jacket, color: look.fg, border: '2px solid #16130f' }}
            >
              {p.badge}
            </div>
          </Token>
        )
      })}
      <div style={{ position: 'absolute', left: YOU_X - 26, top: YOU_Y - 22, width: 52, height: 44, border: '3px solid #ffb43a', outline: '3px solid #000' }} />
      {me && <Token x={YOU_X} y={YOU_Y} shadow={tokenShadow(playerLook(me.look), false)} />}
      {banners}
    </div>
  )
})

function Token({ x, y, shadow, children }: { x: number; y: number; shadow: string; children?: ReactNode }) {
  return (
    <div style={{ position: 'absolute', left: x - 20, top: y - 16, width: 40, height: 36 }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 4, height: 4, boxShadow: shadow }} />
      {children}
    </div>
  )
}

export function Banner({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`led ${className ?? ''}`}
      style={{
        position: 'absolute',
        left: '50%',
        top: 26,
        transform: 'translateX(-50%)',
        padding: '8px 22px',
        background: '#0b0906',
        border: '4px solid #000',
        fontSize: 32,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </div>
  )
}
