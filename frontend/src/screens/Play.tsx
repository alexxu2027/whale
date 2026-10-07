import { useEffect, useRef, useState } from 'react'
import type { FeedItem, Game } from '../game'
import { useTicker } from '../game'
import type { CallState, MarketMsg, RoundStartMsg, YouMsg } from '../types'
import { Button, Card, Pill, Stepper } from '../ui'
import { cx, gold, secondsLeft } from '../format'

export function Play({ game }: { game: Game }) {
  const { state } = game
  const round = state.round
  if (!round || !state.market || !state.you) {
    return <div className="grid h-full place-items-center text-velvet-200">Dealing the cards…</div>
  }
  return <Table game={game} round={round} market={state.market} you={state.you} />
}

function Table({ game, round, market, you }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg }) {
  return (
    <main className="mx-auto flex min-h-full max-w-6xl flex-col gap-3 px-3 py-3 sm:px-4">
      <TopBar game={game} round={round} market={market} />
      <div className="grid gap-3 lg:grid-cols-[1fr_1.35fr_1fr]">
        <div className="flex flex-col gap-3">
          <ClueCard round={round} />
          <PositionCard round={round} you={you} />
        </div>
        <div className="flex flex-col gap-3">
          <MarketCard game={game} round={round} market={market} you={you} />
          <YourMarketCard game={game} round={round} market={market} you={you} />
        </div>
        <div className="flex flex-col gap-3">
          <PlayersCard game={game} round={round} you={you} />
          <FeedCard game={game} />
        </div>
      </div>
      <CallOverlay game={game} round={round} market={market} you={you} />
      <Toast game={game} />
    </main>
  )
}

// -- header ------------------------------------------------------------------------

function TopBar({ game, round, market }: { game: Game; round: RoundStartMsg; market: MarketMsg }) {
  useTicker(250)
  const now = game.serverNow()
  const opening = market.status === 'pre_open'
  const left = secondsLeft(opening ? round.opens_at : round.closes_at, now)
  const urgent = !opening && left <= 30
  const mm = Math.floor(left / 60)
  const ss = String(left % 60).padStart(2, '0')
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-velvet-800/80 px-4 py-3 ring-1 ring-velvet-700">
      <div>
        <div className="text-xs font-extrabold uppercase tracking-widest text-velvet-400">
          Round {round.round_number} of {round.rounds} · {game.state.connection === 'reconnecting' ? 'reconnecting…' : 'live'}
        </div>
        <div className="font-display text-2xl text-gold-400 sm:text-3xl">{round.item.name}</div>
        <div className="text-sm italic text-velvet-200">{round.item.description}</div>
      </div>
      <div className="text-right">
        <div className={cx('text-xs font-extrabold uppercase tracking-widest', urgent ? 'text-sell-400' : 'text-velvet-400')}>
          {opening ? 'Market opens in' : urgent ? 'Last call!' : 'Hammer falls in'}
        </div>
        <div className={cx('font-display text-5xl tabular-nums', urgent ? 'animate-pulse text-sell-400' : 'text-white')}>
          {mm}:{ss}
        </div>
      </div>
    </header>
  )
}

// -- left column ---------------------------------------------------------------------

function ClueCard({ round }: { round: RoundStartMsg }) {
  return (
    <>
      <Card title="Your appraisal" accent="text-gold-400">
        <p className="text-lg font-semibold italic leading-snug">“{round.clue.flavor}”</p>
        <p className="mt-2 rounded-lg bg-velvet-950/50 px-3 py-2 font-mono text-sm text-gold-300">{round.clue.precise}</p>
        <p className="mt-3 text-xs text-velvet-400">
          Hammer price = {round.recipe.average} + {round.recipe.factor_names.join(' + ')}. Each factor is −5 to +5, so the price is
          between {round.recipe.min} and {round.recipe.max}.
        </p>
      </Card>
      <Card title="Secret objective" accent="text-velvet-200">
        <div className="flex items-baseline justify-between gap-2">
          <span className="font-bold">{round.objective.title}</span>
          <Pill className="bg-gold-400/20 text-gold-300">+{round.objective.bonus} bonus</Pill>
        </div>
        <p className="text-sm text-velvet-200">{round.objective.description}</p>
      </Card>
    </>
  )
}

function PositionCard({ round, you }: { round: RoundStartMsg; you: YouMsg }) {
  const limit = round.rules.position_limit
  const pct = (Math.abs(you.position) / limit) * 50
  return (
    <Card title="Your position">
      <div className="flex items-end justify-between">
        <div>
          <div className={cx('font-display text-5xl', you.position > 0 ? 'text-buy-400' : you.position < 0 ? 'text-sell-400' : 'text-white')}>
            {you.position > 0 ? `+${you.position}` : you.position}
          </div>
          <div className="text-xs text-velvet-400">
            {you.position === 0 ? 'Holding nothing' : you.position > 0 ? `Holding ${you.position} ${round.item.unit}s` : `Owe ${-you.position} ${round.item.unit}s`}
          </div>
        </div>
        <div className="text-right text-sm">
          <div className="text-velvet-400">Gold</div>
          <div className="font-bold">{gold(you.cash)}</div>
          <div className="mt-1 text-velvet-400">P&amp;L at market</div>
          <div className={cx('font-bold', you.pnl_at_mid >= 0 ? 'text-buy-400' : 'text-sell-400')}>{gold(Math.round(you.pnl_at_mid))}</div>
        </div>
      </div>
      <div className="relative mt-3 h-2 rounded-full bg-velvet-950/60" title={`Limit ±${limit}`}>
        <div className="absolute left-1/2 top-0 h-2 w-0.5 bg-velvet-400" />
        <div
          className={cx('absolute top-0 h-2 rounded-full', you.position >= 0 ? 'left-1/2 bg-buy-400' : 'right-1/2 bg-sell-400')}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-velvet-400">
        <span>−{limit}</span>
        <span>limit</span>
        <span>+{limit}</span>
      </div>
    </Card>
  )
}

// -- center column -------------------------------------------------------------------

function MarketCard({ game, round, market, you }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg }) {
  const [qty, setQty] = useState(5)
  const open = market.status === 'open'
  const bestAsk = market.asks[0]
  const bestBid = market.bids[0]
  const mineAsk = you.quote.ask
  const mineBid = you.quote.bid
  const take = (side: 'buy' | 'sell', price: number, available: number) => {
    const room = side === 'buy' ? you.room_to_buy : you.room_to_sell
    game.send({ type: 'order', side, price, qty: Math.max(1, Math.min(qty, available, room)), kind: 'ioc' })
  }
  return (
    <Card title="The trading floor">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-velvet-950/40 p-3 text-center ring-1 ring-sell-500/40">
          <div className="text-[11px] font-extrabold uppercase tracking-widest text-sell-400">Best seller</div>
          <div className="font-display text-4xl">{bestAsk ? bestAsk[0] : '—'}</div>
          <div className="text-xs text-velvet-400">{bestAsk ? `${bestAsk[1]} for sale` : 'nobody selling'}</div>
          <Button
            tone="buy"
            className="mt-2 w-full"
            disabled={!open || !bestAsk || you.room_to_buy <= 0 || bestAsk[0] === mineAsk}
            onClick={() => bestAsk && take('buy', bestAsk[0], bestAsk[1])}
          >
            Buy from them
          </Button>
        </div>
        <div className="rounded-xl bg-velvet-950/40 p-3 text-center ring-1 ring-buy-500/40">
          <div className="text-[11px] font-extrabold uppercase tracking-widest text-buy-400">Best buyer</div>
          <div className="font-display text-4xl">{bestBid ? bestBid[0] : '—'}</div>
          <div className="text-xs text-velvet-400">{bestBid ? `wants ${bestBid[1]}` : 'nobody buying'}</div>
          <Button
            tone="sell"
            className="mt-2 w-full"
            disabled={!open || !bestBid || you.room_to_sell <= 0 || bestBid[0] === mineBid}
            onClick={() => bestBid && take('sell', bestBid[0], bestBid[1])}
          >
            Sell to them
          </Button>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-center gap-2 text-sm">
        <span className="text-velvet-400">Trade size</span>
        {[1, 2, 5, 10].filter((n) => n <= round.rules.max_order_qty).map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => setQty(n)}
            className={cx('h-8 w-10 rounded-lg font-bold', qty === n ? 'bg-gold-400 text-velvet-950' : 'bg-velvet-700 hover:bg-velvet-600')}
          >
            {n}
          </button>
        ))}
      </div>
      <Ladder market={market} you={you} />
    </Card>
  )
}

function Ladder({ market, you }: { market: MarketMsg; you: YouMsg }) {
  const asks = market.asks.slice(0, 5).reverse()
  const bids = market.bids.slice(0, 5)
  const max = Math.max(1, ...market.asks.map((l) => l[1]), ...market.bids.map((l) => l[1]))
  const row = (price: number, qty: number, side: 'buy' | 'sell') => {
    const mine = side === 'buy' ? you.quote.bid === price : you.quote.ask === price
    return (
      <div key={`${side}${price}`} className="relative flex h-6 items-center justify-between px-2 text-sm">
        <div
          className={cx('absolute inset-y-0.5 right-0 rounded', side === 'buy' ? 'bg-buy-400/15' : 'bg-sell-400/15')}
          style={{ width: `${(qty / max) * 100}%` }}
        />
        <span className={cx('relative font-bold', side === 'buy' ? 'text-buy-400' : 'text-sell-400')}>{price}</span>
        <span className="relative text-velvet-200">
          {mine && <span className="mr-2 text-[10px] font-bold uppercase text-gold-400">yours</span>}
          {qty}
        </span>
      </div>
    )
  }
  return (
    <details className="mt-3 rounded-xl bg-velvet-950/30 ring-1 ring-velvet-700">
      <summary className="cursor-pointer px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-velvet-400">All offers</summary>
      <div className="px-1 pb-2">
        {asks.map(([p, q]) => row(p, q, 'sell'))}
        <div className="my-1 border-t border-dashed border-velvet-600" />
        {bids.map(([p, q]) => row(p, q, 'buy'))}
        {asks.length === 0 && bids.length === 0 && <p className="py-2 text-center text-xs text-velvet-400">No offers yet.</p>}
      </div>
    </details>
  )
}

function YourMarketCard({ game, round, market, you }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg }) {
  const { min, max, average } = round.recipe
  const center = Math.round(market.mid || average)
  const [bid, setBid] = useState(() => you.quote.bid ?? center - 2)
  const [ask, setAsk] = useState(() => you.quote.ask ?? center + 2)
  const [size, setSize] = useState(() => Math.max(you.quote.bid_qty, you.quote.ask_qty) || 5)
  const live = you.quote.bid !== null || you.quote.ask !== null
  const tradable = market.status === 'open' || market.status === 'pre_open'
  const gap = ask - bid
  return (
    <Card title="Your market" accent="text-gold-400">
      <p className="mb-3 text-sm text-velvet-200">
        {market.status === 'pre_open'
          ? 'Set your opening prices. Everyone’s are revealed together when the market opens.'
          : 'Post a price you’ll buy at and one you’ll sell at. Others can trade with you any time.'}
      </p>
      <div className="flex flex-wrap items-end justify-center gap-4">
        <Stepper label="I will buy at" tone="buy" value={bid} min={min} max={max - 1} onChange={setBid} />
        <Stepper label="I will sell at" tone="sell" value={ask} min={min + 1} max={max} onChange={setAsk} />
        <Stepper label="Size" value={size} min={1} max={round.rules.max_order_qty} onChange={setSize} />
      </div>
      <div className="mt-2 text-center text-sm">
        <span className={cx('font-bold', gap <= 0 ? 'text-sell-400' : 'text-velvet-200')}>Gap: {gap}</span>
        {gap <= 0 && <span className="ml-2 text-sell-400">buy price must be below sell price</span>}
      </div>
      <div className="mt-3 grid grid-cols-[2fr_1fr] gap-2">
        <Button
          tone="gold"
          disabled={!tradable || gap <= 0}
          onClick={() => game.send({ type: 'quote', bid, bid_qty: size, ask, ask_qty: size })}
        >
          {live ? 'Update my market' : 'Post my market'}
        </Button>
        <Button tone="ghost" disabled={!live} onClick={() => game.send({ type: 'quote', bid: 0, bid_qty: 0, ask: 0, ask_qty: 0 })}>
          Pull
        </Button>
      </div>
      <div className="mt-2 text-center text-xs text-velvet-400">
        Live: {you.quote.bid !== null ? `${you.quote.bid} ×${you.quote.bid_qty}` : '—'} /{' '}
        {you.quote.ask !== null ? `${you.quote.ask} ×${you.quote.ask_qty}` : '—'} · +{round.rules.maker_rebate} per unit when someone trades
        with you
      </div>
    </Card>
  )
}

// -- right column --------------------------------------------------------------------

function PlayersCard({ game, round, you }: { game: Game; round: RoundStartMsg; you: YouMsg }) {
  useTicker(1000)
  const players = game.state.room?.players ?? []
  const now = game.serverNow()
  // The server starts the cooldown only when a call actually begins.
  const myLastCall = game.state.feed.find((f) => f.event.type === 'call_started' && f.event.caller_id === game.state.me)
  const cooldownLeft = myLastCall ? secondsLeft(myLastCall.ts + round.rules.call_cooldown_ms, now) : 0
  const open = game.state.market?.status === 'open'
  return (
    <Card title="Merchants">
      <ul className="flex flex-col gap-1.5">
        {players.map((p) => {
          const me = p.id === game.state.me
          return (
            <li key={p.id} className="flex items-center justify-between gap-2">
              <span className="flex min-w-0 items-center gap-1.5">
                <span className={cx('truncate font-semibold', me && 'text-gold-300')}>{me ? `${p.name} (you)` : p.name}</span>
                {p.is_bot && <Pill className="bg-velvet-700 text-velvet-200">bot</Pill>}
                {!p.connected && <Pill className="bg-sell-500/30 text-sell-400">away</Pill>}
              </span>
              {!me && (
                <button
                  type="button"
                  disabled={!open || !!you.call || cooldownLeft > 0}
                  onClick={() => game.send({ type: 'call', target: p.id })}
                  className="rounded-lg bg-velvet-700 px-2.5 py-1 text-xs font-bold hover:bg-gold-400 hover:text-velvet-950 disabled:opacity-40 disabled:hover:bg-velvet-700 disabled:hover:text-white"
                  title="Ask them for a two-sided price"
                >
                  {cooldownLeft > 0 ? `${cooldownLeft}s` : 'Make me a market'}
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

function describe(item: FeedItem, game: Game): { text: string; tone?: string } {
  const e = item.event as Record<string, unknown> & { type: string }
  const n = (id: unknown) => game.nameOf(id as string)
  switch (e.type) {
    case 'trade': {
      const how = e.kind === 'auction' ? ' (opening)' : e.kind === 'call' ? ' (call)' : ''
      if (e.taker_id === e.seller_id)
        return { text: `${n(e.seller_id)} sold ${e.qty} @ ${e.price} to ${n(e.buyer_id)}${how}`, tone: 'text-sell-400' }
      return { text: `${n(e.buyer_id)} bought ${e.qty} @ ${e.price} from ${n(e.seller_id)}${how}`, tone: 'text-buy-400' }
    }
    case 'call_started':
      return { text: `${n(e.caller_id)} asks ${n(e.responder_id)} for a market…`, tone: 'text-gold-300' }
    case 'call_answered':
      return {
        text: `${n(e.responder_id)}: ${e.bid_price} / ${e.ask_price} ×${e.qty}${e.automatic ? ' (too slow, auto-quoted)' : ''}`,
        tone: 'text-gold-300',
      }
    case 'call_ended':
      return e.outcome === 'traded' ? { text: '' } : { text: `Call ${String(e.outcome).replace('_', ' ')}`, tone: 'text-velvet-400' }
    case 'status_changed':
      return {
        text: e.status === 'open' ? 'The market is open!' : e.status === 'closed' ? 'Hammer down!' : `Market ${e.status}`,
        tone: 'text-white font-bold',
      }
    default:
      return { text: '' }
  }
}

function FeedCard({ game }: { game: Game }) {
  const items = game.state.feed.map((f) => ({ f, d: describe(f, game) })).filter(({ d }) => d.text)
  return (
    <Card title="Trade feed" className="flex min-h-48 flex-1 flex-col">
      <ul className="max-h-80 flex-1 overflow-y-auto pr-1 text-sm lg:max-h-[26rem]">
        {items.length === 0 && <li className="text-velvet-400">Quiet so far…</li>}
        {items.map(({ f, d }) => (
          <li key={f.id} className={cx('flash rounded px-1 py-0.5', d.tone)}>
            {d.text}
          </li>
        ))}
      </ul>
    </Card>
  )
}

// -- calls -------------------------------------------------------------------------

function CallOverlay({ game, round, market, you }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg }) {
  const call = you.call
  if (!call) return null
  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-velvet-950/70 p-4" role="dialog" aria-modal="true">
      <div className="pop-in w-full max-w-sm rounded-2xl bg-velvet-800 p-5 text-center ring-2 ring-gold-400">
        <CallBody game={game} round={round} market={market} you={you} call={call} key={`${call.call_id}-${call.stage}`} />
      </div>
    </div>
  )
}

function CallBody({ game, round, market, you, call }: { game: Game; round: RoundStartMsg; market: MarketMsg; you: YouMsg; call: CallState }) {
  useTicker(200)
  const left = secondsLeft(call.deadline, game.serverNow())
  const who = game.nameOf(call.counterparty)
  const W = round.rules.call_max_width
  const center = Math.round(you.quote.bid !== null && you.quote.ask !== null ? (you.quote.bid + you.quote.ask) / 2 : market.mid || round.recipe.average)
  const [bid, setBid] = useState(center - Math.floor(W / 2))
  const [ask, setAsk] = useState(center - Math.floor(W / 2) + W)
  const [qty, setQty] = useState(round.rules.call_min_qty)
  const answerRef = useRef<HTMLButtonElement>(null)
  useEffect(() => answerRef.current?.focus(), [])
  const timer = <div className={cx('font-display text-4xl', left <= 2 ? 'text-sell-400' : 'text-gold-400')}>{left}</div>

  if (call.role === 'responder' && call.stage === 'awaiting_answer') {
    const gap = ask - bid
    const ok = gap > 0 && gap <= W
    return (
      <>
        <div className="text-xs font-extrabold uppercase tracking-widest text-gold-400">You've been called!</div>
        <h3 className="font-display text-2xl">{who} wants your market</h3>
        <p className="text-sm text-velvet-200">
          They can buy at your sell price or sell at your buy price. Gap at most {W}, size at least {round.rules.call_min_qty}.
        </p>
        {timer}
        <div className="my-3 flex justify-center gap-3">
          <Stepper label="Buy at" tone="buy" value={bid} min={round.recipe.min} max={round.recipe.max - 1} onChange={setBid} />
          <Stepper label="Sell at" tone="sell" value={ask} min={round.recipe.min + 1} max={round.recipe.max} onChange={setAsk} />
        </div>
        <Stepper label="Size" value={qty} min={round.rules.call_min_qty} max={round.rules.max_order_qty} onChange={setQty} />
        <Button
          ref={answerRef}
          tone="gold"
          className="mt-4 w-full"
          disabled={!ok}
          onClick={() => game.send({ type: 'answer', call_id: call.call_id, bid, ask, qty })}
        >
          {ok ? `Quote ${bid} / ${ask}` : `Gap must be 1 to ${W}`}
        </Button>
      </>
    )
  }
  if (call.role === 'caller' && call.stage === 'awaiting_decision') {
    return (
      <>
        <div className="text-xs font-extrabold uppercase tracking-widest text-gold-400">{who} answered</div>
        <div className="my-2 font-display text-5xl">
          <span className="text-buy-400">{call.bid}</span> <span className="text-velvet-400">/</span>{' '}
          <span className="text-sell-400">{call.ask}</span>
        </div>
        <p className="text-sm text-velvet-200">for {call.qty} {round.item.unit}s</p>
        {timer}
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Button tone="buy" disabled={you.room_to_buy < call.qty} onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: 'buy' })}>
            Buy @ {call.ask}
          </Button>
          <Button tone="sell" disabled={you.room_to_sell < call.qty} onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: 'sell' })}>
            Sell @ {call.bid}
          </Button>
        </div>
        <Button tone="ghost" className="mt-2 w-full" onClick={() => game.send({ type: 'decide', call_id: call.call_id, side: null })}>
          Pass
        </Button>
      </>
    )
  }
  return (
    <>
      <div className="text-xs font-extrabold uppercase tracking-widest text-velvet-400">Call in progress</div>
      <h3 className="font-display text-2xl">
        {call.role === 'caller' ? `Waiting for ${who}'s market…` : `${who} is deciding on ${call.bid} / ${call.ask}…`}
      </h3>
      {timer}
    </>
  )
}

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
    <div className="pop-in fixed bottom-4 left-1/2 z-30 -translate-x-1/2 rounded-xl bg-sell-500 px-4 py-2 font-semibold text-white shadow-lg" role="status">
      {toast.text}
    </div>
  )
}
