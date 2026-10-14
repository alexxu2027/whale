// The settlement ledger (PRD §16): how the price settled and who knew which
// part of it, where your P&L came from, the floor's results, and the tell
// you missed.

import type { ReactNode } from 'react'
import type { Game } from '../game'
import { useTicker } from '../game'
import type { RevealMsg, RevealPlayer } from '../types'
import { boardName, clock, signed } from '../pit/format'
import { Stage } from '../pit/parts'
import { playerLook } from '../pit/sprites'

const BLUE = '#8fb0ff'
const ORANGE = '#e08a3c'
const tone = (v: number) => (Math.round(v) > 0 ? BLUE : Math.round(v) < 0 ? ORANGE : '#d9d4c3')

export function Reveal({ game, reveal }: { game: Game; reveal: RevealMsg }) {
  useTicker(500)
  const { state, send } = game
  const room = state.room!
  const isHost = room.host_id === state.me
  const me = reveal.players.find((p) => p.id === state.me)
  const finished = room.phase === 'finished'
  const lookOf = (id: string) => playerLook(room.players.find((p) => p.id === id)?.look ?? 0)
  const nextIn = room.reveal_until !== null ? room.reveal_until - game.serverNow() : null
  // Up to 8 traders share the column: past 5, cards tighten up to fit.
  const compact = reveal.players.length > 5
  const slipLines = Math.max(1, ...reveal.players.map((p) => p.slips.length))

  return (
    <Stage background="#0e0c0a">
      <div style={{ position: 'absolute', inset: 0, boxSizing: 'border-box', padding: '28px 56px', color: '#d9d4c3', display: 'grid', gridTemplateColumns: '700px minmax(0, 1fr)', gap: 56 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <div className="silk" style={{ fontSize: 15, color: '#8c8676' }}>
              SETTLEMENT · {boardName(reveal.contract.name)} · PIT {reveal.contract.pit} · ROUND {reveal.round_number} OF {reveal.rounds}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 20, marginTop: 6 }}>
              <div className="led" style={{ fontSize: 104, lineHeight: 1 }}>{reveal.final_value}</div>
              <div style={{ fontSize: 22, color: '#b5ae9b' }}>
                final settlement price
                <br />
                <span style={{ fontSize: 16 }}>{reveal.trades} trades on the floor</span>
              </div>
            </div>
          </div>

          <Section title="HOW IT SETTLED">
            <Line name="Base" value="100" />
            {reveal.factors.map((f) => {
              const mine = me && f.knew.includes(me.badge)
              const others = f.knew.filter((b) => b !== me?.badge)
              const who = [mine ? 'you' : null, ...others].filter(Boolean).join(', ')
              return (
                <Line
                  key={f.name}
                  name={f.name}
                  who={who ? `${who} knew` : 'nobody knew'}
                  whoColor={mine ? '#ffb43a' : '#8c8676'}
                  value={signed(f.value)}
                  color={tone(f.value)}
                />
              )
            })}
          </Section>

          {me && <Book me={me} reveal={reveal} />}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 8 : 12, position: 'relative', minWidth: 0 }}>
          <div className="silk" style={{ fontSize: 14, color: '#8c8676', borderBottom: '3px solid #3a362e', paddingBottom: 6 }}>
            THE FLOOR · WHO KNEW WHAT
          </div>
          {reveal.players.map((p) => (
            <FloorCard key={p.id} p={p} me={p.id === state.me} look={lookOf(p.id)} compact={compact} slipLines={slipLines} match={finished || reveal.last_round ? reveal.match_scores[p.id] : undefined} />
          ))}

          <div style={{ marginTop: 4, padding: '12px 16px', background: '#1b1814', border: '3px solid #3a362e', fontSize: 17, lineHeight: 1.4 }}>
            <span className="silk" style={{ fontSize: 13, color: '#ffb43a' }}>THE TELL YOU MISSED</span>
            <br />
            {me?.tell ?? 'Nobody picked you off this round. Whoever traded with your market didn’t know more than you did.'}
          </div>

          {/* The stamp lands in the free space under the cards, never on them. */}
          <div style={{ flex: 1, minHeight: 0, display: 'grid', placeItems: 'center', overflow: 'hidden' }}>
            {!compact && (
              <div
                className="silk"
                style={{ padding: '8px 18px', border: '6px solid #a8322d', color: '#a8322d', fontSize: 46, letterSpacing: 2, transform: 'rotate(-8deg)', opacity: 0.9, animation: 'thud .35s ease-out 0.4s both', pointerEvents: 'none' }}
              >
                SETTLED
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div className="led" style={{ flex: 1, padding: '12px 14px', background: '#0b0906', border: '3px solid #000', fontSize: 20, whiteSpace: 'nowrap' }}>
              {finished ? 'MATCH OVER' : nextIn !== null ? `NEXT BELL IN ${clock(nextIn)}` : 'NEXT BELL SOON'}
            </div>
            {finished && isHost && (
              <Big onClick={() => send({ type: 'rematch' })}>REMATCH</Big>
            )}
            {!finished && isHost && <Big onClick={() => send({ type: 'next_round' })}>TO THE PIT</Big>}
            <Big ghost onClick={game.leave}>LEAVE</Big>
          </div>
        </div>
      </div>
    </Stage>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <div className="silk" style={{ fontSize: 14, color: '#8c8676', borderBottom: '3px solid #3a362e', paddingBottom: 6 }}>{title}</div>
      {children}
    </section>
  )
}

function Line({ name, value, color = '#d9d4c3', who, whoColor }: { name: string; value: string; color?: string; who?: string; whoColor?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, padding: '3px 0', fontSize: 19 }}>
      <span>{name}</span>
      <span style={{ flex: 1, borderBottom: '3px dotted #3a362e', transform: 'translateY(-5px)' }} />
      {who && <span style={{ fontSize: 15, color: whoColor }}>{who}</span>}
      <span style={{ minWidth: 52, textAlign: 'right', fontWeight: 700, color }}>{value}</span>
    </div>
  )
}

function Book({ me, reveal }: { me: RevealPlayer; reveal: RevealMsg }) {
  const b = me.breakdown
  const worst = Object.entries(b.lost_to)[0]?.[0]
  const worstBadge = reveal.players.find((p) => p.name === worst)?.badge
  return (
    <Section title="YOUR BOOK">
      <Line name="Earned on your quotes" value={signed(b.spread)} color={tone(b.spread)} />
      <Line
        name={Math.round(b.adverse_selection) < 0 ? `Lost to traders who knew more${worstBadge ? ` (mostly ${worstBadge})` : ''}` : Math.round(b.adverse_selection) > 0 ? 'Won from traders who knew less' : 'Lost to traders who knew more'}
        value={signed(b.adverse_selection)}
        color={tone(b.adverse_selection)}
      />
      <Line name="Your own trades" value={signed(b.directional)} color={tone(b.directional)} />
      <Line name="Fees and rebates" value={signed(b.fees)} color={tone(b.fees)} />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, padding: '8px 0 0', marginTop: 4, borderTop: '3px solid #d9d4c3', fontSize: 26, fontWeight: 700 }}>
        <span>TRADING TOTAL</span>
        <span style={{ flex: 1 }} />
        <span style={{ color: tone(me.pnl) }}>{signed(me.pnl)}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, paddingTop: 8, fontSize: 18, color: '#b5ae9b' }}>
        <span>Standing order: {me.objective.description}</span>
        <span style={{ flex: 1 }} />
        <span style={{ color: me.objective.met ? BLUE : ORANGE, whiteSpace: 'nowrap' }}>
          {me.objective.met ? `DONE · +${me.bonus}` : 'MISSED · +0'}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, paddingTop: 6, fontSize: 18 }}>
        <span>Ended holding {signed(me.position)} · round score</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontWeight: 700, color: tone(me.score) }}>{signed(me.score)}</span>
      </div>
    </Section>
  )
}

const oneLine = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } as const

function FloorCard({ p, me, look, match, compact, slipLines }: { p: RevealPlayer; me: boolean; look: ReturnType<typeof playerLook>; match?: number; compact: boolean; slipLines: number }) {
  const slipSize = compact ? 14 : 17
  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: 14, padding: compact ? '4px 12px' : '10px 14px', background: '#d9d4c3', color: '#16130f', border: '3px solid #16130f',
        boxShadow: '5px 5px 0 #000', outline: me ? '3px solid #ffb43a' : undefined, outlineOffset: 3,
      }}
    >
      <div className="led" style={{ width: 28, fontSize: 30, color: '#16130f' }}>{p.rank}</div>
      <div className="silk" style={{ padding: '2px 8px', fontSize: 16, background: look.jacket, color: look.fg, border: '2px solid #16130f' }}>
        {me ? 'YOU' : p.badge}
      </div>
      <div style={{ flex: 1, minWidth: 0, lineHeight: 1.25 }}>
        {/* One clue per line, and room for as many lines as anyone has, so every card is the same height. */}
        <div style={{ fontSize: slipSize, minHeight: slipLines * slipSize * 1.25 }}>
          {p.slips.map((s, i) => (
            <div key={i} style={oneLine} title={s.precise}>
              {s.precise}
            </div>
          ))}
        </div>
        <div style={{ ...oneLine, fontSize: compact ? 12 : 14, color: '#6b665a' }}>
          {p.name} · ended {p.position === 0 ? 'flat' : `${p.position > 0 ? 'long' : 'short'} ${Math.abs(p.position)}`} · {p.objective.title}{' '}
          {p.objective.met ? `done +${p.bonus}` : 'missed'}
        </div>
      </div>
      <div style={{ textAlign: 'right', lineHeight: 1.1 }}>
        <div style={{ fontSize: compact ? 22 : 26, color: p.score >= 0 ? '#24418c' : '#b5501f' }}>{signed(p.score)}</div>
        {match !== undefined && <div style={{ fontSize: compact ? 12 : 13, whiteSpace: 'nowrap' }}>match {signed(match)}</div>}
      </div>
    </div>
  )
}

function Big({ children, onClick, ghost }: { children: ReactNode; onClick: () => void; ghost?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="silk"
      style={{ minHeight: 52, padding: '0 20px', border: '4px solid #d9d4c3', background: ghost ? 'transparent' : '#d9d4c3', color: ghost ? '#d9d4c3' : '#0e0c0a', fontSize: 18, boxShadow: '4px 4px 0 #3a362e' }}
    >
      {children}
    </button>
  )
}
