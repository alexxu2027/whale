// The LED tape across the top of the booth: what just happened on the floor.

import type { FeedItem, Game } from '../game'
import type { MarketMsg, RoundStartMsg } from '../types'
import type { Cast } from './cast'
import { boardName } from './format'

const verb = (id: unknown, cast: Cast, v: string) => (cast.badge(id as string) === 'YOU' ? v : `${v}S`)

function line(f: FeedItem, cast: Cast): string | null {
  const e = f.event as Record<string, unknown> & { type: string }
  const b = (id: unknown) => cast.badge(id as string)
  switch (e.type) {
    case 'trade':
      if (e.kind === 'auction') return `OPENING CROSS ${e.qty} LOTS AT ${e.price}`
      if (e.taker_id === e.seller_id) return `${b(e.seller_id)} ${verb(e.seller_id, cast, 'SELL')} ${e.qty} TO ${b(e.buyer_id)} AT ${e.price}`
      return `${b(e.buyer_id)} ${verb(e.buyer_id, cast, 'BUY')} ${e.qty} FROM ${b(e.seller_id)} AT ${e.price}`
    case 'call_started':
      return `${b(e.caller_id)} ${verb(e.caller_id, cast, 'ASK')} ${b(e.responder_id)} FOR A MARKET`
    case 'call_answered':
      return `${b(e.responder_id)} ${verb(e.responder_id, cast, 'SHOUT')} ${e.bid_price} AT ${e.ask_price}${e.automatic ? ' (TOO SLOW)' : ''}`
    case 'runner_dispatched':
      return `RUNNER ON THE FLOOR FOR ${b(e.recipient_id)}`
    case 'status_changed':
      return e.status === 'open' ? 'THE BELL! PIT IS OPEN' : e.status === 'closed' ? 'CLOSING BELL' : null
    default:
      return null
  }
}

export function Ticker({ game, cast, round, market }: { game: Game; cast: Cast; round: RoundStartMsg; market: MarketMsg }) {
  const news = game.state.feed
    .map((f) => line(f, cast))
    .filter((x): x is string => !!x)
    .slice(0, 8)
  const quotes = Object.entries(market.quotes)
    .filter(([id]) => id !== game.state.me)
    .map(([id, q]) => `${cast.badge(id)} ${q.bid ?? '--'} BID / ${q.ask ?? '--'} OFFER`)
  const head = `${boardName(round.contract.name)} ${market.last ?? '--'}`
  const items = [head, ...news, ...quotes]
  if (items.length < 3) items.push(round.contract.description.toUpperCase())
  const text = items.join(' · ') + ' ·'
  const reconnecting = game.state.connection === 'reconnecting'
  return (
    <div style={{ position: 'absolute', left: 0, top: 0, width: 1440, height: 44, background: '#0b0906', borderBottom: '4px solid #000', overflow: 'hidden', display: 'flex', alignItems: 'center' }}>
      <div className="led" style={{ display: 'flex', whiteSpace: 'nowrap', fontSize: 24, letterSpacing: 1, animation: `tape ${Math.max(30, text.length / 6)}s linear infinite` }}>
        <span style={{ paddingRight: 80 }}>{text}</span>
        <span style={{ paddingRight: 80 }}>{text}</span>
      </div>
      {reconnecting && (
        <div className="led blink" style={{ position: 'absolute', right: 0, top: 0, bottom: 0, padding: '8px 16px', background: '#0b0906', color: '#ff5a3a', fontSize: 22 }}>
          RECONNECTING
        </div>
      )}
    </div>
  )
}
