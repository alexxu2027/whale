import { useState } from 'react'
import type { Game } from '../game'
import { Badge, Trader } from '../pit/parts'
import { playerLook } from '../pit/sprites'
import { Backdrop } from './Home'

export function Lobby({ game }: { game: Game }) {
  const { state, send, leave } = game
  const room = state.room!
  const isHost = room.host_id === state.me
  const [botType, setBotType] = useState('')
  const link = `${location.origin}/?room=${room.code}`
  const [copied, setCopied] = useState(false)
  const n = room.players.length
  const field = { height: 40, fontSize: 18, padding: '0 6px', border: '3px solid #2b2418', background: '#e9e4d4', fontFamily: 'var(--font-pixel)' }

  return (
    <Backdrop>
      <div className="led" style={{ position: 'absolute', left: 420, top: 30, width: 600, padding: '12px 24px', boxSizing: 'border-box', background: '#0b0906', border: '8px solid #1f1d19', boxShadow: '8px 8px 0 rgba(0,0,0,.5)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 14, color: 'var(--color-led-dim)' }}>PIT CODE</div>
          <div style={{ fontSize: 64, lineHeight: 1, letterSpacing: 10 }}>{room.code}</div>
        </div>
        <button
          type="button"
          className="led"
          onClick={() => {
            navigator.clipboard?.writeText(link).then(() => setCopied(true), () => setCopied(false))
          }}
          style={{ background: 'transparent', border: '3px solid var(--color-led-dim)', padding: '8px 14px', fontSize: 18 }}
        >
          {copied ? 'LINK COPIED' : 'COPY INVITE LINK'}
        </button>
      </div>

      {/* Everyone who's in, standing on the front step. */}
      <div style={{ position: 'absolute', left: 0, top: 230, width: 1440, height: 426 }}>
        {room.players.map((p, k) => {
          const look = playerLook(p.look)
          const x = Math.round(720 + (k - (n - 1) / 2) * 150 - 35)
          return (
            <Trader key={p.id} x={x} feet={326} s={5} pose={k % 2 ? 'call' : 'idle'} look={look}>
              <Badge text={p.badge} look={look} style={{ top: '44%' }} />
              <div className="silk" style={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)', top: 'calc(100% + 8px)', whiteSpace: 'nowrap', fontSize: 12, color: '#e9e4d4', textAlign: 'center' }}>
                {p.id === state.me ? 'YOU' : p.name.toUpperCase()}
                {p.is_bot && <div style={{ color: '#bfb9a6' }}>{p.personality?.toUpperCase()}</div>}
                {p.id === room.host_id && <div style={{ color: 'var(--color-led)' }}>HOST</div>}
                {!p.connected && <div style={{ color: '#e08a3c' }}>AWAY</div>}
                {isHost && p.is_bot && (
                  <button type="button" onClick={() => send({ type: 'remove_player', player_id: p.id })} className="silk" style={{ marginTop: 2, fontSize: 11, background: '#16130f', color: '#e9e4d4', border: '2px solid #000', padding: '0 6px' }}>
                    SEND HOME
                  </button>
                )}
              </div>
            </Trader>
          )
        })}
      </div>

      <section className="paper" style={{ position: 'absolute', left: 420, top: 640, width: 600, padding: '14px 20px', background: '#e9e4d4' }}>
        <div className="paper-head">
          <span>FLOOR SHEET · {n} OF 8 TRADERS</span>
          <button type="button" onClick={leave} className="silk" style={{ background: 'transparent', border: 0, fontSize: 12, textDecoration: 'underline' }}>
            LEAVE THE PIT
          </button>
        </div>
        {isHost ? (
          <>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 12 }}>
              <select aria-label="Bot type" value={botType} onChange={(e) => setBotType(e.target.value)} style={{ ...field, flex: 1 }}>
                <option value="">Any bot</option>
                {room.bot_types.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <button type="button" className="rule-btn" disabled={n >= 8} onClick={() => send({ type: 'add_bot', personality: botType || null })} style={{ minHeight: 40, padding: '0 14px', border: '3px solid #2b2418', color: '#2b2418', fontSize: 14 }}>
                + ADD BOT
              </button>
              <select
                aria-label="Rounds"
                value={room.settings.rounds}
                onChange={(e) => send({ type: 'settings', rounds: Number(e.target.value), round_seconds: room.settings.round_seconds })}
                style={field}
              >
                {[1, 2, 3, 4, 5].map((r) => (
                  <option key={r} value={r}>
                    {r} {r === 1 ? 'round' : 'rounds'}
                  </option>
                ))}
              </select>
              <select
                aria-label="Round length"
                value={room.settings.round_seconds}
                onChange={(e) => send({ type: 'settings', rounds: room.settings.rounds, round_seconds: Number(e.target.value) })}
                style={field}
              >
                {[...new Set([90, 120, 180, 240, 300, room.settings.round_seconds])].sort((a, b) => a - b).map((s) => (
                  <option key={s} value={s}>
                    {s % 60 ? `${s} s` : `${s / 60} min`}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 14 }}>
              <button type="button" className="rule-btn" disabled={n < 2} onClick={() => send({ type: 'start' })} style={{ border: '4px solid #2b2418', color: '#2b2418', fontSize: 16 }}>
                RING THE BELL
              </button>
              <button type="button" className="stamp-btn silk" onClick={() => send({ type: 'start', fill_bots: true })} style={{ minHeight: 52, background: '#2f5bd3', color: '#eef1fb', fontSize: 16, boxShadow: 'inset 0 -6px 0 #1f3f99, 4px 4px 0 rgba(0,0,0,.4)' }}>
                FILL WITH BOTS &amp; START
              </button>
            </div>
          </>
        ) : (
          <p style={{ fontSize: 18, margin: '14px 0 4px' }}>Waiting for the host to ring the bell…</p>
        )}
      </section>
    </Backdrop>
  )
}
