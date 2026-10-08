// The pit window: the LED board, the steps, the crowd, the other players
// shouting their markets, and runners crossing the floor (PRD §14, §36).

import { memo, useEffect, useMemo, useState } from 'react'
import type { Game, Runner } from '../game'
import { useTicker } from '../game'
import type { MarketMsg, RoundStartMsg, TradeEvent, YouMsg } from '../types'
import type { Cast } from './cast'
import { boardName, clock } from './format'
import { Badge, LedCell, Trader } from './parts'
import type { Pose } from './sprites'
import { RUNNER_LOOK, SPRITE_W, crowdLook } from './sprites'

export const PIT_H = 426
const FRONT = 326 // feet on the front step
const FLOOR = 426 // feet on the pit floor (the caller steps down to you)

interface FloorProps {
  game: Game
  cast: Cast
  round: RoundStartMsg
  market: MarketMsg
  you: YouMsg
}

/** Where each other player stands on the front step. */
function slotX(k: number, n: number): number {
  const span = 1000
  return Math.round(200 + ((k + 0.5) * span) / Math.max(1, n) - (SPRITE_W * 5) / 2)
}

export function PitWindow({ game, cast, round, market, you }: FloorProps) {
  useTicker(250)
  const now = game.serverNow()
  const feed = game.state.feed
  const trades = feed.filter((f) => f.event.type === 'trade').map((f) => f.event as TradeEvent)
  const heat = trades.filter((t) => now - t.ts < 6000).length

  return (
    <div style={{ position: 'absolute', left: 0, top: 48, width: 1440, height: PIT_H, overflow: 'hidden', background: '#2f322a' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 1440, height: 176, background: 'repeating-linear-gradient(90deg, #34372f 0 118px, #2b2e27 118px 122px)' }} />
      <Board round={round} market={market} trades={trades} now={now} cast={cast} />
      <Steps />
      <Crowd heat={heat} />
      <Players game={game} cast={cast} market={market} you={you} trades={trades} now={now} canCall={callCooldown(game, round, now) <= 0} />
      <Runners game={game} cast={cast} runners={game.state.runners} now={now} />
      <CallHint game={game} round={round} you={you} now={now} />
      <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 0 10px #1f1a14, inset 0 0 0 14px #000', pointerEvents: 'none' }} />
    </div>
  )
}

// -- the board ------------------------------------------------------------------------

function Board({ round, market, trades, now, cast }: { round: RoundStartMsg; market: MarketMsg; trades: TradeEvent[]; now: number; cast: Cast }) {
  const [depth, setDepth] = useState(false)
  const sealed = market.status === 'pre_open'
  const closed = market.status === 'closed'
  const bid = market.bids[0]?.[0]
  const ask = market.asks[0]?.[0]
  const last = market.last
  const prev = trades.find((t, i) => i > 0 && t.price !== last)?.price
  const arrow = last === null || prev === undefined || prev === last ? '' : last > prev ? '▲' : '▼'
  const label = sealed ? `BELL IN ${clock(round.opens_at - now)}` : closed ? 'CLOSED' : `CLOSE ${clock(round.closes_at - now)}`
  const urgent = !sealed && !closed && round.closes_at - now < 30_000
  const quoter = (price: number, side: 'bid' | 'ask') =>
    Object.entries(market.quotes)
      .filter(([, q]) => q[side] === price)
      .map(([id]) => cast.badge(id))
      .join(' ')

  return (
    <>
      <button
        type="button"
        onClick={() => setDepth((d) => !d)}
        title="Show every price in the pit"
        className="led"
        style={{
          position: 'absolute', left: 420, top: 8, width: 600, height: 92, background: '#0b0906', border: '6px solid #1f1d19',
          boxShadow: '6px 6px 0 rgba(0,0,0,.45)', padding: '6px 20px', boxSizing: 'border-box', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between', textAlign: 'left',
        }}
      >
        <div>
          <div style={{ fontSize: 13, color: 'var(--color-led-dim)' }}>
            {boardName(round.contract.name)} · PIT {round.contract.pit}
          </div>
          <div className={urgent ? 'blink' : undefined} style={{ fontSize: 20 }}>
            {label}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-led-dim)' }}>{depth ? 'DEPTH ▴' : 'DEPTH ▾'}</div>
        </div>
        <LedCell label="BID" value={sealed || bid === undefined ? '--' : bid} />
        <LedCell label="OFFER" value={sealed || ask === undefined ? '--' : ask} />
        <LedCell label="LAST" value={last === null ? '--' : `${last}${arrow}`} />
      </button>
      {depth && (
        <div
          className="led"
          style={{ position: 'absolute', left: 420, top: 106, width: 600, padding: '10px 20px', boxSizing: 'border-box', background: '#0b0906', border: '6px solid #1f1d19', zIndex: 5, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, fontSize: 18 }}
        >
          {sealed ? (
            <div style={{ gridColumn: '1 / 3', textAlign: 'center' }}>OPENING MARKETS ARE SEALED TILL THE BELL</div>
          ) : (
            (['bids', 'asks'] as const).map((side) => (
              <div key={side}>
                <div style={{ fontSize: 12, color: 'var(--color-led-dim)' }}>{side === 'bids' ? 'BIDS · WILL BUY AT' : 'OFFERS · WILL SELL AT'}</div>
                {market[side].slice(0, 5).map(([p, q]) => (
                  <div key={p} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>{p}</span>
                    <span style={{ color: 'var(--color-led-dim)', fontSize: 14 }}>{quoter(p, side === 'bids' ? 'bid' : 'ask')}</span>
                    <span>×{q}</span>
                  </div>
                ))}
                {market[side].length === 0 && <div style={{ color: 'var(--color-led-dim)' }}>NONE</div>}
              </div>
            ))
          )}
        </div>
      )}
    </>
  )
}

// -- the steps and the crowd ----------------------------------------------------------

const TREADS: [number, number][] = [
  [170, 246],
  [246, 322],
  [322, 350],
]

export const Steps = memo(function Steps() {
  return (
    <>
      {TREADS.map(([tread, next]) => (
        <div key={tread}>
          <div style={{ position: 'absolute', left: 0, top: tread, width: 1440, height: 8, background: '#8b9079', boxShadow: '0 -2px 0 #a4a990' }} />
          <div style={{ position: 'absolute', left: 0, top: tread + 8, width: 1440, height: next - tread - 8, background: 'repeating-linear-gradient(90deg,#4f5446 0 46px,#4a4f42 46px 48px)' }} />
        </div>
      ))}
      <div style={{ position: 'absolute', left: 0, top: 350, width: 1440, height: 76, background: '#666b59', borderTop: '4px solid #7f846f' }} />
    </>
  )
})

interface Extra {
  x: number
  feet: number
  s: number
  k: number
}

const CROWD: Extra[] = (() => {
  const out: Extra[] = []
  const row = (feet: number, s: number, gap: number, n: number, seed: number, skip: number[] = []) => {
    for (let i = 0; i < n; i++) {
      if (skip.includes(i)) continue
      out.push({ x: -12 + i * gap + ((i * 7 + seed) % 3) * 4, feet: feet + 4 - ((i + seed) % 2) * 2, s, k: i * 5 + seed })
    }
  }
  row(170, 3, 38, 39, 1)
  row(246, 4, 53, 28, 6, [6, 7])
  for (const [x, k] of [[12, 2], [96, 9], [1248, 4], [1336, 11]]) out.push({ x, feet: FRONT, s: 5, k })
  return out
})()

/** The floor never stands still: hands go up more when trades are flying. */
export const Crowd = memo(function Crowd({ heat }: { heat: number }) {
  const [beat, setBeat] = useState(0)
  useEffect(() => {
    const id = window.setInterval(() => setBeat((b) => b + 1), 700)
    return () => window.clearInterval(id)
  }, [])
  const busy = Math.min(0.65, 0.22 + heat * 0.06)
  return (
    <>
      {CROWD.map((c, i) => {
        // Each trader changes signal on their own rhythm.
        const phase = Math.floor((beat + (i % 5)) / (2 + (i % 3)))
        const r = hash(i * 131 + phase * 7919)
        const pose: Pose = r < busy / 2 ? 'buy' : r < busy ? 'sell' : 'idle'
        return <Trader key={i} x={c.x} feet={c.feet} s={c.s} pose={pose} look={crowdLook(c.k)} />
      })}
    </>
  )
})

function hash(n: number): number {
  let x = (n ^ 0x9e3779b9) >>> 0
  x = Math.imul(x ^ (x >>> 16), 0x85ebca6b) >>> 0
  x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35) >>> 0
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296
}

// -- the players ----------------------------------------------------------------------

function Players({ game, cast, market, you, trades, now, canCall: free }: { game: Game; cast: Cast; market: MarketMsg; you: YouMsg; trades: TradeEvent[]; now: number; canCall: boolean }) {
  const open = market.status === 'open'
  const answers = game.state.feed.filter((f) => f.event.type === 'call_answered' && now - f.ts < 3500)
  return (
    <>
      {cast.others.map((p, k) => {
        const look = cast.look(p.id)
        const x = slotX(k, cast.others.length)
        const shout = trades.find((t) => t.taker_id === p.id && now - t.ts < 2500)
        const callingMe = you.call && you.call.counterparty === p.id && you.call.role === 'responder'
        const answered = answers.find((f) => (f.event as { responder_id?: string }).responder_id === p.id)
        const quote = market.quotes[p.id]

        let pose: Pose = 'idle'
        let lines: [string, string] | null = null
        let call = false
        let tone: 'buy' | 'sell' | 'plain' = 'plain'
        if (callingMe) {
          pose = 'call'
          call = true
          lines = ['MAKE ME A MARKET', `${you.call!.qty || 5} lots · quick`]
        } else if (shout) {
          const bought = shout.buyer_id === p.id
          pose = bought ? 'buy' : 'sell'
          tone = bought ? 'buy' : 'sell'
          lines = [bought ? 'BUY ’EM!' : 'SOLD!', `${shout.qty} at ${shout.price}${shout.seller_id === game.state.me || shout.buyer_id === game.state.me ? ', you' : ''}`]
        } else if (answered) {
          const e = answered.event as { bid_price: number; ask_price: number; qty: number }
          pose = 'call'
          lines = [`${e.bid_price} AT ${e.ask_price}`, `${e.qty} lots`]
        } else if (quote && (quote.bid !== null || quote.ask !== null)) {
          pose = 'call'
          lines = [quote.bid !== null ? `${quote.bid} BID` : 'NO BID', quote.ask !== null ? `${quote.ask} OFFER` : 'NO OFFER']
        }
        const s = callingMe ? 6 : 5
        const feet = callingMe ? FLOOR : FRONT
        const canCall = open && !you.call && free
        return (
          <Trader
            key={p.id}
            x={callingMe ? x - 7 : x}
            feet={feet}
            s={s}
            pose={pose}
            look={look}
            style={{ zIndex: callingMe ? 4 : 2 }}
            onClick={canCall ? () => game.send({ type: 'call', target: p.id }) : undefined}
            title={canCall ? `Ask ${p.name} for a market` : p.name}
          >
            <Badge text={p.badge} look={look} style={{ top: '44%' }} />
            {!p.connected && <Badge text="AWAY" look={{ ...look, jacket: '#16130f', fg: '#d9d4c3' }} style={{ top: '64%', fontSize: 10 }} />}
            {lines && <Bubble lines={lines} call={call} tone={tone} />}
          </Trader>
        )
      })}
    </>
  )
}

function Bubble({ lines, call, tone }: { lines: [string, string]; call: boolean; tone: 'buy' | 'sell' | 'plain' }) {
  const first = call ? '#9e2b25' : tone === 'buy' ? '#24418c' : tone === 'sell' ? '#b5501f' : '#16130f'
  return (
    <div
      style={{
        position: 'absolute', left: '50%', transform: 'translateX(-50%)', bottom: 'calc(100% + 8px)', minWidth: 112, padding: '5px 8px',
        textAlign: 'center', whiteSpace: 'nowrap', border: `3px solid ${call ? '#9e2b25' : '#16130f'}`, background: call ? '#f3e3a8' : '#e9e4d4',
        boxShadow: '3px 3px 0 rgba(0,0,0,.4)', pointerEvents: 'none',
      }}
    >
      <div style={{ fontSize: call ? 19 : 17, fontWeight: 700, color: first }}>{lines[0]}</div>
      <div style={{ fontSize: 14, color: '#16130f' }}>{lines[1]}</div>
    </div>
  )
}

// -- runners --------------------------------------------------------------------------

const LINGER_MS = 2200 // a runner waits at the booth after handing over the slip

function Runners({ game, cast, runners, now }: { game: Game; cast: Cast; runners: Runner[]; now: number }) {
  const visible = runners.filter((r) => now < r.arriveAt + LINGER_MS)
  return (
    <>
      {visible.map((r) => {
        const mine = r.recipient === game.state.me
        const k = cast.others.findIndex((p) => p.id === r.recipient)
        const target = mine ? 64 : slotX(Math.max(0, k), cast.others.length) + (k % 2 ? 76 : -60)
        return <RunnerSprite key={r.id} runner={r} mine={mine} target={target} label={mine ? 'YOUR RUNNER' : `RUNNER → ${cast.badge(r.recipient)}`} now={now} />
      })}
    </>
  )
}

function RunnerSprite({ runner, mine, target, label, now }: { runner: Runner; mine: boolean; target: number; label: string; now: number }) {
  const start = useMemo(() => (mine || target > 720 ? 1480 : -80), [mine, target])
  const travel = Math.max(1, runner.arriveAt - runner.dispatchedAt)
  const t0 = Math.min(1, Math.max(0, (now - runner.dispatchedAt) / travel))
  const [x, setX] = useState(() => start + (target - start) * t0)
  const [moving, setMoving] = useState(false)
  useEffect(() => {
    // Next frame: glide to the booth for the rest of the trip.
    const id = requestAnimationFrame(() => {
      setMoving(true)
      setX(target)
    })
    return () => cancelAnimationFrame(id)
  }, [target])
  const left = Math.max(0, runner.arriveAt - now)
  const arrived = now >= runner.arriveAt
  const s = mine ? 5 : 4
  const feet = mine ? 432 : 338
  return (
    <Trader
      x={x}
      feet={feet}
      s={s}
      pose={arrived ? 'call' : 'run'}
      look={RUNNER_LOOK}
      flip={start > target}
      className={arrived ? undefined : 'bob'}
      style={{ zIndex: 6, transition: moving ? `left ${left}ms linear` : undefined }}
    >
      <Badge text={label} look={RUNNER_LOOK} style={{ top: -26 }} />
      <div
        style={{
          position: 'absolute', width: arrived ? 20 : 14, height: arrived ? 14 : 10, background: '#e9e4d4', border: '2px solid #16130f',
          ...(arrived ? { right: -8, top: -6 } : start > target ? { left: -10, top: '52%' } : { right: -10, top: '52%' }),
        }}
      />
    </Trader>
  )
}

// -- calling ------------------------------------------------------------------------

/** Ms until you may call again (the server starts the cooldown when a call begins). */
function callCooldown(game: Game, round: RoundStartMsg, now: number): number {
  const mine = game.state.feed.find((f) => f.event.type === 'call_started' && f.event.caller_id === game.state.me)
  return mine ? mine.ts + round.rules.call_cooldown_ms - now : 0
}

function CallHint({ game, round, you, now }: { game: Game; round: RoundStartMsg; you: YouMsg; now: number }) {
  const cooldown = callCooldown(game, round, now)
  const open = game.state.market?.status === 'open'
  const text = !open ? 'CALLS OPEN AT THE BELL' : you.call ? 'ON A CALL' : cooldown > 0 ? `NEXT CALL IN ${clock(cooldown)}` : 'CLICK A TRADER: “MAKE ME A MARKET”'
  return (
    <div className="silk" style={{ position: 'absolute', right: 24, bottom: 22, padding: '4px 10px', fontSize: 12, background: 'rgba(11,9,6,.82)', color: '#d9d4c3', border: '2px solid #000', zIndex: 7 }}>
      {text}
    </div>
  )
}
