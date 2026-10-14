// Your booth's desk (PRD §14): slips from your desk, the standing order, the
// order ticket, your trading card, the stamp tray, and the call slip.

import { Fragment, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { Game } from '../game'
import { useTicker } from '../game'
import type { CallState, MarketMsg, RoundStartMsg, Slip, TradeEvent, YouMsg } from '../types'
import type { Cast } from './cast'
import { clock, signed } from './format'

const BLUE = '#24418c'
const ORANGE = '#b5501f'
const RED = '#9e2b25'

interface DeskProps {
  game: Game
  cast: Cast
  round: RoundStartMsg
  market: MarketMsg
  you: YouMsg
}

export function Desk({ game, cast, round, market, you }: DeskProps) {
  const [lots, setLots] = useState(5)
  return (
    <div style={{ position: 'absolute', left: 0, top: 474, width: 1440, height: 426, background: 'repeating-linear-gradient(0deg, #5a4433 0 22px, #553f2f 22px 24px)', borderTop: '8px solid #3e2e22' }}>
      <Slips round={round} slips={you.slips} />
      <Memo round={round} you={you} trades={game.state.myTrades} me={game.state.me} />
      <Ticket game={game} round={round} market={market} you={you} />
      <TradingCard round={round} trades={game.state.myTrades} me={game.state.me} cast={cast} />
      <Tray game={game} cast={cast} round={round} market={market} you={you} lots={lots} setLots={setLots} />
      {you.call && <CallSlip key={`${you.call.call_id}-${you.call.stage}`} game={game} cast={cast} round={round} market={market} you={you} call={you.call} />}
      <Toast game={game} />
    </div>
  )
}

// -- slips ------------------------------------------------------------------------

function Slips({ round, slips }: { round: RoundStartMsg; slips: Slip[] }) {
  const [front, setFront] = useState<number | null>(null)
  const top = front ?? slips.length - 1
  const order = slips.map((_, i) => i).filter((i) => i !== top)
  order.push(top)
  return (
    <>
      {order.map((i, depth) => {
        const behind = depth < order.length - 1
        return (
          <SlipCard
            key={`${slips[i].kind}-${slips[i].ts}`}
            round={round}
            slip={slips[i]}
            n={i}
            behind={behind}
            offset={(order.length - 1 - depth) * 12}
            onClick={behind ? () => setFront(i) : undefined}
          />
        )
      })}
    </>
  )
}

function SlipCard({ round, slip, n, behind, offset, onClick }: { round: RoundStartMsg; slip: Slip; n: number; behind: boolean; offset: number; onClick?: () => void }) {
  const runner = slip.kind === 'runner'
  const m = /^(.+?) = ([+−-]?\d+)$/.exec(slip.precise)
  return (
    <section
      onClick={onClick}
      className={`paper ${runner && !behind ? 'drop-in fresh' : ''}`}
      title={behind ? 'Bring this slip to the front' : undefined}
      style={{
        position: 'absolute', left: 24 + offset, top: 22 - offset, width: 300, height: 236, padding: '12px 14px',
        background: runner ? '#e9e4d4' : '#e4dfcd', cursor: onClick ? 'pointer' : undefined, transform: behind ? 'rotate(-2deg)' : undefined,
        // The fold sits below the writing, so a two-line quote never runs into it.
        backgroundImage: 'linear-gradient(180deg, transparent 84%, rgba(43,36,24,.18) 84%, rgba(43,36,24,.18) 85%, transparent 85%)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '3px solid #2b2418', paddingBottom: 4 }}>
        <span className="silk" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>{runner ? 'RUNNER SLIP' : 'DESK SLIP'}</span>
        <span className="silk" style={{ fontSize: 11, color: RED, border: `2px solid ${RED}`, padding: '0 4px', whiteSpace: 'nowrap' }}>EYES ONLY</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 13 }}>
        <span>To: YOU · pit {round.contract.pit}</span>
        <span>{runner ? `${clock(slip.ts - round.opens_at)} in · runner ${n}` : 'before the open'}</span>
      </div>
      <p style={{ margin: '8px 0 6px', fontSize: 19, lineHeight: 1.15, color: BLUE, minHeight: 44 }}>“{slip.flavor}”</p>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '4px 10px', border: '2px dashed #2b2418' }}>
        {m ? (
          <>
            <span style={{ fontWeight: 700 }}>{m[1].toUpperCase()}</span>
            <span style={{ fontSize: 24, fontWeight: 700, color: BLUE }}>{m[2]}</span>
          </>
        ) : (
          <span style={{ fontWeight: 700, fontSize: 18, lineHeight: 1.1 }}>{slip.precise}</span>
        )}
      </div>
    </section>
  )
}

// -- standing order -----------------------------------------------------------------

function progress(id: string, you: YouMsg, trades: TradeEvent[], me: string | null): { have: number; need: number } | { note: string } | null {
  const mine = trades.filter((t) => t.buyer_id === me || t.seller_id === me)
  const volume = mine.reduce((s, t) => s + t.qty, 0)
  const passive = (bought: boolean) => trades.filter((t) => t.maker_id === me && (bought ? t.buyer_id : t.seller_id) === me).length
  switch (id) {
    case 'collector':
      return { have: Math.max(0, you.position), need: 15 }
    case 'short_king':
      return { have: Math.max(0, -you.position), need: 15 }
    case 'volume_trader':
      return { have: volume, need: 50 }
    case 'market_maker':
      return { note: `Filled ${passive(true)} bought · ${passive(false)} sold (need 5 each)` }
    case 'big_ticket':
      return { have: Math.max(0, ...mine.filter((t) => t.kind !== 'auction').map((t) => t.qty)), need: 10 }
    case 'flat_finish':
      return { note: `Holding ${signed(you.position)} · ${Math.abs(you.position) <= 3 ? 'on target' : 'off target'}` }
    default:
      return null
  }
}

function Memo({ round, you, trades, me }: { round: RoundStartMsg; you: YouMsg; trades: TradeEvent[]; me: string | null }) {
  const o = round.objective
  const p = progress(o.id, you, trades, me)
  return (
    <section className="paper" style={{ position: 'absolute', left: 24, top: 276, width: 300, height: 122, padding: '10px 16px' }}>
      <div className="silk" style={{ fontSize: 12, display: 'flex', justifyContent: 'space-between' }}>
        <span>DESK MEMO · STANDING ORDER</span>
        <span>+{o.bonus}</span>
      </div>
      <div style={{ marginTop: 4, fontSize: 16, fontWeight: 700, lineHeight: 1.15 }}>{o.description}</div>
      {p && 'have' in p ? (
        <>
          <div style={{ display: 'flex', gap: 3, marginTop: 6 }}>
            {Array.from({ length: 15 }, (_, i) => (
              <div key={i} style={{ width: 14, height: 14, border: '2px solid #2b2418', background: i < Math.round((15 * Math.min(p.have, p.need)) / p.need) ? BLUE : 'transparent' }} />
            ))}
          </div>
          <div style={{ marginTop: 2, fontSize: 13 }}>
            {Math.min(p.have, p.need)} of {p.need}
          </div>
        </>
      ) : (
        p && <div style={{ marginTop: 6, fontSize: 13 }}>{p.note}</div>
      )}
    </section>
  )
}

// -- order ticket -------------------------------------------------------------------

function Ticket({ game, round, market, you }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg }) {
  const { min, max } = round.recipe
  const center = Math.round(market.mid || round.recipe.average)
  const [bid, setBid] = useState(() => you.quote.bid ?? center - 2)
  const [ask, setAsk] = useState(() => you.quote.ask ?? center + 2)
  const [bidQty, setBidQty] = useState(() => you.quote.bid_qty || 5)
  const [askQty, setAskQty] = useState(() => you.quote.ask_qty || 5)
  const live = you.quote.bid !== null || you.quote.ask !== null
  const tradable = market.status === 'open' || market.status === 'pre_open'
  const gap = ask - bid
  const changed = !live || you.quote.bid !== bid || you.quote.ask !== ask || you.quote.bid_qty !== bidQty || you.quote.ask_qty !== askQty
  const post = () => {
    if (tradable && gap > 0) game.send({ type: 'quote', bid, bid_qty: bidQty, ask, ask_qty: askQty })
  }
  const maxQty = round.rules.max_order_qty
  return (
    <section className="paper" style={{ position: 'absolute', left: 350, top: 22, width: 470, height: 376, background: '#d8c464' }}>
      <div
        className="paper"
        style={{ position: 'absolute', left: 8, top: -8, right: -8, bottom: 8, padding: '16px 20px', boxShadow: 'none' }}
        onKeyDown={(e) => e.key === 'Enter' && post()}
      >
        <div className="paper-head">
          <span>{market.status === 'pre_open' ? 'OPENING CALL · SEALED TILL THE BELL' : `ORDER TICKET · ${round.contract.name.toUpperCase()}`}</span>
          <span>BADGE YOU</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 16 }}>
          <PriceRow label="I will buy at" color={BLUE} price={bid} setPrice={setBid} qty={bidQty} setQty={setBidQty} min={min} max={max - 1} maxQty={maxQty} side="buy" />
          <PriceRow label="I will sell at" color={ORANGE} price={ask} setPrice={setAsk} qty={askQty} setQty={setAskQty} min={min + 1} max={max} maxQty={maxQty} side="sell" />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 14, fontSize: 15, borderTop: '2px dashed #2b2418', paddingTop: 8 }}>
          <span style={{ color: gap <= 0 ? RED : undefined, fontWeight: gap <= 0 ? 700 : undefined }}>{gap <= 0 ? 'Buy must be below sell' : `Gap ${gap}`}</span>
          <span>+{round.rules.maker_rebate} per lot when someone trades with you</span>
        </div>
        <div style={{ display: 'flex', gap: 14, marginTop: 14 }}>
          <button type="button" className="rule-btn" disabled={!tradable || gap <= 0 || !changed} onClick={post} style={{ flex: 2, border: `4px solid ${RED}`, color: RED, fontSize: 20 }}>
            {live ? 'CHANGE MY MARKET' : 'POST TO PIT'}
          </button>
          <button
            type="button"
            className="rule-btn"
            disabled={!live || !tradable}
            onClick={() => game.send({ type: 'quote', bid: 0, bid_qty: 0, ask: 0, ask_qty: 0 })}
            style={{ flex: 1, border: '4px solid #2b2418', color: '#2b2418', fontSize: 18 }}
          >
            PULL
          </button>
        </div>
        {live && (
          <div
            className="silk"
            key={`${you.quote.bid}-${you.quote.ask}`}
            style={{ position: 'absolute', right: 18, top: 48, padding: '2px 8px', border: `3px solid ${RED}`, color: RED, fontSize: 14, transform: 'rotate(-8deg)', opacity: 0.85, animation: 'thud .3s ease-out', background: 'rgba(217,212,195,.6)' }}
          >
            IN THE PIT {you.quote.bid ?? '--'} / {you.quote.ask ?? '--'}
          </div>
        )}
      </div>
    </section>
  )
}

function PriceRow(props: {
  label: string
  color: string
  price: number
  setPrice: (n: number) => void
  qty: number
  setQty: (n: number) => void
  min: number
  max: number
  maxQty: number
  side: 'buy' | 'sell'
}) {
  const { label, color, price, setPrice, qty, setQty, min, max, maxQty, side } = props
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
  return (
    <div>
      <div style={{ fontSize: 15, color }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 66, fontSize: 26, fontWeight: 700, color }}>{side === 'buy' ? 'BUY' : 'SELL'}</span>
        <button type="button" className="nudge" aria-label={`Lower my ${side} price`} onClick={() => setPrice(clamp(price - 1, min, max))}>▼</button>
        <NumberField value={price} onChange={(v) => setPrice(clamp(v, min, max))} width={80} size={38} color={color} label={`My ${side} price`} />
        <button type="button" className="nudge" aria-label={`Raise my ${side} price`} onClick={() => setPrice(clamp(price + 1, min, max))}>▲</button>
        <span style={{ fontSize: 20 }}>for</span>
        <NumberField value={qty} onChange={(v) => setQty(clamp(v, 1, maxQty))} width={50} size={30} color={color} label={`My ${side} size`} />
        <span style={{ fontSize: 17 }}>lots</span>
      </div>
    </div>
  )
}

function NumberField({ value, onChange, width, size, color, label }: { value: number; onChange: (v: number) => void; width: number; size: number; color: string; label: string }) {
  const [draft, setDraft] = useState<string | null>(null)
  return (
    <input
      aria-label={label}
      inputMode="numeric"
      className="hand-num"
      value={draft ?? String(value)}
      onFocus={(e) => e.currentTarget.select()}
      onChange={(e) => setDraft(e.target.value.replace(/\D/g, '').slice(0, 3))}
      onBlur={() => {
        if (draft) onChange(parseInt(draft, 10))
        setDraft(null)
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && draft) {
          onChange(parseInt(draft, 10))
          setDraft(null)
        }
        if (e.key === 'ArrowUp') onChange(value + 1)
        if (e.key === 'ArrowDown') onChange(value - 1)
      }}
      style={{ width, height: 50, fontSize: size, color }}
    />
  )
}

// -- trading card ---------------------------------------------------------------------

function TradingCard({ round, trades, me, cast }: { round: RoundStartMsg; trades: TradeEvent[]; me: string | null; cast: Cast }) {
  const rows = trades.slice(0, 11)
  const bought = trades.filter((t) => t.buyer_id === me).reduce((s, t) => s + t.qty, 0)
  const sold = trades.filter((t) => t.seller_id === me).reduce((s, t) => s + t.qty, 0)
  const head = { fontFamily: 'var(--font-silk)', fontSize: 10, padding: '4px 0' }
  return (
    <section className="paper" style={{ position: 'absolute', left: 846, top: 22, width: 290, height: 376, padding: 14, boxShadow: '5px 5px 0 rgba(0,0,0,.4), 10px -6px 0 -3px #c9c3b0, 10px -6px 0 0 #2b2418' }}>
      <div className="paper-head">
        <span>TRADING CARD · YOU</span>
        <span>PIT {round.contract.pit}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '50px 30px 36px 50px minmax(0, 1fr)', marginTop: 6, fontSize: 15 }}>
        <div style={head}>TIME</div>
        <div style={head}>B/S</div>
        <div style={head}>QTY</div>
        <div style={head}>PRICE</div>
        <div style={head}>WITH</div>
        {rows.map((t, i) => {
          const buy = t.buyer_id === me
          const other = buy ? t.seller_id : t.buyer_id
          const cell = { padding: '3px 0', borderTop: '2px solid rgba(43,36,24,.25)', color: BLUE }
          const cls = i === 0 ? 'ink' : undefined // fresh ink on the newest line
          return (
            <Fragment key={t.seq}>
              <div className={cls} style={cell}>{clock(t.ts - round.opens_at)}</div>
              <div className={cls} style={{ ...cell, fontWeight: 700, color: buy ? BLUE : ORANGE }}>{buy ? 'B' : 'S'}</div>
              <div className={cls} style={cell}>{t.qty}</div>
              <div className={cls} style={cell}>{t.price}</div>
              <div className={cls} style={cell}>{t.kind === 'auction' ? 'OPEN' : `${cast.badge(other)}${t.kind === 'call' ? '*' : ''}`}</div>
            </Fragment>
          )
        })}
      </div>
      <div style={{ position: 'absolute', left: 14, right: 14, bottom: 10, fontSize: 13, display: 'flex', justifyContent: 'space-between' }}>
        {trades.length ? (
          <>
            <span>Bought {bought} · Sold {sold}</span>
            {trades.some((t) => t.kind === 'call') && <span>* on a call</span>}
          </>
        ) : (
          <span>Written in ink, timed from the bell.</span>
        )}
      </div>
    </section>
  )
}

// -- stamps -----------------------------------------------------------------------

function Tray({ game, cast, round, market, you, lots, setLots }: DeskProps & { lots: number; setLots: (n: number) => void }) {
  const open = market.status === 'open'
  const ask = market.asks[0]
  const bid = market.bids[0]
  const holder = (price: number, side: 'bid' | 'ask') => {
    const ids = Object.entries(market.quotes).filter(([id, q]) => q[side] === price && id !== game.state.me).map(([id]) => cast.badge(id))
    if (ids.length) return ids.join(' / ')
    return you.quote[side] === price ? 'yourself (your own price)' : 'the pit'
  }
  const take = (side: 'buy' | 'sell', price: number, available: number) => {
    const room = side === 'buy' ? you.room_to_buy : you.room_to_sell
    game.send({ type: 'order', side, price, qty: Math.max(1, Math.min(lots, available, room)), kind: 'ioc' })
  }
  const buyQty = ask ? Math.min(lots, ask[1], you.room_to_buy) : 0
  const sellQty = bid ? Math.min(lots, bid[1], you.room_to_sell) : 0
  const sizes = [1, 2, 5, 10].filter((n) => n <= round.rules.max_order_qty)
  return (
    <section style={{ position: 'absolute', left: 1162, top: 22, width: 254, height: 376, boxSizing: 'border-box', padding: 12, background: '#3e2e22', border: '3px solid #1d150f', boxShadow: '5px 5px 0 rgba(0,0,0,.4)', display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="silk" style={{ fontSize: 12, color: '#d9d4c3', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>LOTS</span>
        <span style={{ display: 'flex', gap: 4 }}>
          {sizes.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setLots(n)}
              aria-pressed={lots === n}
              className="silk"
              style={{ width: 30, height: 24, fontSize: 12, border: '2px solid #16130f', background: lots === n ? '#d9d4c3' : '#5a4433', color: lots === n ? '#16130f' : '#d9d4c3' }}
            >
              {n}
            </button>
          ))}
        </span>
      </div>
      <button
        type="button"
        className="stamp-btn"
        disabled={!open || !ask || buyQty <= 0 || you.quote.ask === ask?.[0]}
        onClick={() => ask && take('buy', ask[0], ask[1])}
        style={{ minHeight: 98, background: '#2f5bd3', color: '#eef1fb', boxShadow: 'inset 0 -8px 0 #1f3f99, 4px 4px 0 rgba(0,0,0,.4)' }}
      >
        <div className="silk" style={{ fontSize: 26 }}>BUY</div>
        <div style={{ fontSize: 18 }}>{ask ? `${Math.max(buyQty, 0)} at ${ask[0]} from ${holder(ask[0], 'ask')}` : 'nobody selling'}</div>
        <div style={{ fontSize: 12, opacity: 0.85 }}>palms in · take the best offer</div>
      </button>
      <button
        type="button"
        className="stamp-btn"
        disabled={!open || !bid || sellQty <= 0 || you.quote.bid === bid?.[0]}
        onClick={() => bid && take('sell', bid[0], bid[1])}
        style={{ minHeight: 98, background: '#e08a3c', color: '#23130a', boxShadow: 'inset 0 -8px 0 #a85f1f, 4px 4px 0 rgba(0,0,0,.4)' }}
      >
        <div className="silk" style={{ fontSize: 26 }}>SELL</div>
        <div style={{ fontSize: 18 }}>{bid ? `${Math.max(sellQty, 0)} at ${bid[0]} to ${holder(bid[0], 'bid')}` : 'nobody buying'}</div>
        <div style={{ fontSize: 12, opacity: 0.85 }}>palms out · hit the best bid</div>
      </button>
      <div className="led" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#0b0906', border: '3px solid #000', marginTop: 'auto' }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--color-led-dim)' }}>POSITION · ±{round.rules.position_limit}</div>
          <div style={{ fontSize: 30 }}>{signed(you.position)}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 12, color: 'var(--color-led-dim)' }}>P&amp;L AT MID</div>
          <div style={{ fontSize: 30 }}>{signed(you.pnl_at_mid)}</div>
        </div>
      </div>
    </section>
  )
}

// -- the call slip --------------------------------------------------------------------

function CallSlip({ game, cast, round, market, you, call }: DeskProps & { call: CallState }) {
  useTicker(200)
  const left = Math.max(0, call.deadline - game.serverNow())
  const who = cast.badge(call.counterparty)
  const W = round.rules.call_max_width
  const center = Math.round(you.quote.bid !== null && you.quote.ask !== null ? (you.quote.bid + you.quote.ask) / 2 : market.mid || round.recipe.average)
  const [bid, setBid] = useState(center - Math.floor(W / 2))
  const [ask, setAsk] = useState(center - Math.floor(W / 2) + W)
  const [qty, setQty] = useState(round.rules.call_min_qty)
  const first = useRef<HTMLButtonElement>(null)
  useEffect(() => first.current?.focus(), [])
  const { min, max } = round.recipe
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
  const secs = Math.ceil(left / 1000)

  let body: ReactNode
  if (call.role === 'responder' && call.stage === 'awaiting_answer') {
    const gap = ask - bid
    const ok = gap > 0 && gap <= W
    body = (
      <>
        <Head who={who} title="WANTS YOUR MARKET" secs={secs} />
        <p style={{ margin: '6px 0 10px', fontSize: 15 }}>
          They can buy at your sell price or sell at your buy price. Gap at most {W}, at least {round.rules.call_min_qty} lots.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 20 }}>
          <span style={{ color: BLUE, fontWeight: 700, width: 54 }}>BUY</span>
          <button type="button" className="nudge" aria-label="Lower buy" onClick={() => setBid(clamp(bid - 1, min, max - 1))}>▼</button>
          <NumberField value={bid} onChange={(v) => setBid(clamp(v, min, max - 1))} width={70} size={32} color={BLUE} label="Call buy price" />
          <button type="button" className="nudge" aria-label="Raise buy" onClick={() => setBid(clamp(bid + 1, min, max - 1))}>▲</button>
          <span style={{ color: ORANGE, fontWeight: 700, width: 54, marginLeft: 10 }}>SELL</span>
          <button type="button" className="nudge" aria-label="Lower sell" onClick={() => setAsk(clamp(ask - 1, min + 1, max))}>▼</button>
          <NumberField value={ask} onChange={(v) => setAsk(clamp(v, min + 1, max))} width={70} size={32} color={ORANGE} label="Call sell price" />
          <button type="button" className="nudge" aria-label="Raise sell" onClick={() => setAsk(clamp(ask + 1, min + 1, max))}>▲</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 10, fontSize: 20 }}>
          <span>for</span>
          <NumberField value={qty} onChange={(v) => setQty(clamp(v, round.rules.call_min_qty, round.rules.max_order_qty))} width={50} size={28} color="#16130f" label="Call size" />
          <span>lots</span>
          <button
            ref={first}
            type="button"
            className="rule-btn"
            disabled={!ok}
            onClick={() => game.send({ type: 'answer', call_id: call.call_id, bid, ask, qty })}
            style={{ marginLeft: 'auto', padding: '0 18px', border: `4px solid ${RED}`, color: RED, fontSize: 20 }}
          >
            {ok ? `SHOUT ${bid} AT ${ask}` : `GAP 1 TO ${W}`}
          </button>
        </div>
      </>
    )
  } else if (call.role === 'caller' && call.stage === 'awaiting_decision') {
    body = (
      <>
        <Head who={who} title="SAYS" secs={secs} />
        <div style={{ fontSize: 44, fontWeight: 700, margin: '8px 0' }}>
          <span style={{ color: BLUE }}>{call.bid}</span> <span style={{ fontSize: 26 }}>at</span> <span style={{ color: ORANGE }}>{call.ask}</span>
          <span style={{ fontSize: 22, marginLeft: 12 }}>for {call.qty}</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button ref={first} type="button" className="stamp-btn silk" disabled={you.room_to_buy < call.qty} onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: 'buy' })} style={{ flex: 1, minHeight: 60, background: '#2f5bd3', color: '#eef1fb', fontSize: 20, boxShadow: 'inset 0 -6px 0 #1f3f99, 4px 4px 0 rgba(0,0,0,.4)' }}>
            BUY AT {call.ask}
          </button>
          <button type="button" className="stamp-btn silk" disabled={you.room_to_sell < call.qty} onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: 'sell' })} style={{ flex: 1, minHeight: 60, background: '#e08a3c', color: '#23130a', fontSize: 20, boxShadow: 'inset 0 -6px 0 #a85f1f, 4px 4px 0 rgba(0,0,0,.4)' }}>
            SELL AT {call.bid}
          </button>
          <button type="button" className="rule-btn" onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: null })} style={{ padding: '0 16px', border: '4px solid #2b2418', color: '#2b2418', fontSize: 18 }}>
            PASS
          </button>
        </div>
      </>
    )
  } else {
    body = (
      <>
        <Head who={who} title={call.role === 'caller' ? 'IS MAKING YOU A MARKET' : `IS DECIDING ON ${call.bid} AT ${call.ask}`} secs={secs} />
        <p style={{ fontSize: 18 }}>Hold on…</p>
      </>
    )
  }
  return (
    <section
      className="paper drop-in"
      role="dialog"
      aria-label="Make me a market"
      style={{ position: 'absolute', left: 330, top: 30, width: 600, padding: '14px 18px', zIndex: 20, background: '#f3e3a8', border: `4px solid ${RED}`, boxShadow: '8px 8px 0 rgba(0,0,0,.5)' }}
    >
      {body}
    </section>
  )
}

function Head({ who, title, secs }: { who: string; title: string; secs: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '3px solid #2b2418', paddingBottom: 6 }}>
      <span className="silk" style={{ fontSize: 22, color: RED }}>
        {who} {title}
      </span>
      <span className="led" style={{ fontSize: 34, background: '#0b0906', padding: '0 10px', color: secs <= 2 ? '#ff5a3a' : undefined }}>
        {secs}
      </span>
    </div>
  )
}

// -- toast ----------------------------------------------------------------------------

function Toast({ game }: { game: Game }) {
  const toast = game.state.toast
  const [dismissed, setDismissed] = useState<number | null>(null)
  useEffect(() => {
    if (!toast) return
    const id = window.setTimeout(() => setDismissed(toast.id), 3000)
    return () => window.clearTimeout(id)
  }, [toast])
  if (!toast || dismissed === toast.id) return null
  return (
    <div
      role="status"
      className="paper drop-in"
      style={{ position: 'absolute', left: '50%', bottom: 14, transform: 'translateX(-50%)', padding: '6px 16px', zIndex: 30, color: RED, fontSize: 18, fontWeight: 700, border: `3px solid ${RED}`, background: '#e9e4d4' }}
    >
      {toast.text}
    </div>
  )
}
