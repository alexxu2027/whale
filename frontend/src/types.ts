// Server -> client messages (see backend/whale/multiplayer/room.py).

export type Side = 'buy' | 'sell'
export type Phase = 'lobby' | 'briefing' | 'playing' | 'reveal' | 'finished'
export type MarketStatus = 'pre_open' | 'open' | 'halted' | 'closed'

export interface PlayerInfo {
  id: string
  name: string
  is_bot: boolean
  personality: string | null
  connected: boolean
  badge: string // 3 letters, unique in the room
  look: number // index into the jacket palette
}

export interface RoomMsg {
  type: 'room'
  code: string
  phase: Phase
  host_id: string | null
  round_number: number
  settings: { rounds: number; round_seconds: number }
  players: PlayerInfo[]
  scores: Record<string, number>
  reveal_until: number | null
  ready: string[] // during the briefing: humans who are ready for the bell
  server_now: number
  bot_types: string[]
}

/** Before each round: your own slip and memo, with the clock not yet running. */
export interface BriefingMsg {
  type: 'briefing'
  round_number: number
  rounds: number
  contract: Contract
  recipe: { title: string; description: string; factor_names: string[]; min: number; max: number }
  clue: { flavor: string; precise: string }
  objective: { id: string; title: string; description: string; bonus: number }
  round_seconds: number
  opening_seconds: number
}

export interface RoundStartMsg {
  type: 'round_start'
  round_number: number
  rounds: number
  contract: Contract
  recipe: { title: string; description: string; factor_names: string[]; min: number; max: number; average: number }
  clue: { flavor: string; precise: string }
  objective: { id: string; title: string; description: string; bonus: number }
  opens_at: number
  closes_at: number
  server_now: number
  rules: {
    position_limit: number
    max_order_qty: number
    call_max_width: number
    call_min_qty: number
    call_answer_ms: number
    call_decide_ms: number
    call_cooldown_ms: number
    maker_rebate: number
    taker_fee: number
    runner_travel_ms: number
  }
}

export interface Contract {
  name: string
  pit: number
  description: string
}

export interface PublicQuote {
  bid: number | null
  bid_qty: number
  ask: number | null
  ask_qty: number
}

export interface Slip {
  kind: 'start' | 'runner'
  flavor: string
  precise: string
  ts: number
}

export interface MarketMsg {
  type: 'market'
  seq: number
  server_now: number
  status: MarketStatus
  bids: [number, number][]
  asks: [number, number][]
  mid: number
  last: number | null
  quotes: Record<string, PublicQuote> // each player's posted market, by player id
}

export interface CallState {
  call_id: number
  role: 'caller' | 'responder'
  counterparty: string
  stage: 'awaiting_answer' | 'awaiting_decision'
  bid: number | null
  ask: number | null
  qty: number
  deadline: number
}

export interface YouMsg {
  type: 'you'
  position: number
  cash: number
  pnl_at_mid: number
  room_to_buy: number
  room_to_sell: number
  quote: { bid: number | null; bid_qty: number; ask: number | null; ask_qty: number }
  orders: { id: number; side: Side; price: number; qty: number }[]
  slips: Slip[]
  call: CallState | null
  server_now: number
}

export interface RevealPlayer {
  id: string
  name: string
  rank: number
  position: number
  pnl: number
  bonus: number
  score: number
  badge: string
  clue: { flavor: string; precise: string }
  slips: { flavor: string; precise: string }[]
  tell: string | null
  objective: { title: string; description: string; bonus: number; met: boolean }
  breakdown: {
    spread: number
    adverse_selection: number
    directional: number
    fees: number
    lost_to: Record<string, number>
  }
}

export interface RevealMsg {
  type: 'reveal'
  round_number: number
  rounds: number
  contract: { name: string; pit: number }
  final_value: number
  trades: number
  factors: { name: string; value: number; knew: string[] }[] // knew: badges of everyone told about it
  players: RevealPlayer[]
  match_scores: Record<string, number>
  last_round: boolean
}

export interface TradeEvent {
  type: 'trade'
  seq: number
  ts: number
  trade_id: number
  kind: 'book' | 'auction' | 'call'
  price: number
  qty: number
  buyer_id: string
  seller_id: string
  maker_id: string | null
  taker_id: string | null
  aggressor_side: Side | null
}

// Engine events, as serialized by event_to_wire.
export type GameEvent =
  | TradeEvent
  | { type: 'call_started'; seq: number; ts: number; call_id: number; caller_id: string; responder_id: string }
  | {
      type: 'call_answered'
      seq: number
      ts: number
      call_id: number
      responder_id: string
      bid_price: number
      ask_price: number
      qty: number
      automatic: boolean
      penalty_cents: number
    }
  | { type: 'call_ended'; seq: number; ts: number; call_id: number; outcome: string }
  | { type: 'status_changed'; seq: number; ts: number; status: MarketStatus }
  | { type: 'order_rejected'; seq: number; ts: number; reason: string }
  | { type: 'runner_dispatched'; seq: number; ts: number; runner_id: number; recipient_id: string; arrive_at: number }
  | { type: 'runner_arrived'; seq: number; ts: number; runner_id: number; recipient_id: string }
  | { type: 'runner_slip'; seq: number; ts: number; runner_id: number; player_id: string; flavor: string; precise: string }
  | { type: string; seq: number; ts: number; [key: string]: unknown }

export type ServerMsg =
  | { type: 'welcome'; player_id: string; token: string; code: string; protocol: number }
  | RoomMsg
  | BriefingMsg
  | RoundStartMsg
  | MarketMsg
  | YouMsg
  | RevealMsg
  | { type: 'event'; event: GameEvent }
  | { type: 'error'; message: string; fatal?: boolean }
