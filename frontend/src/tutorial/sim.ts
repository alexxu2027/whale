// The practice round behind the tutorial: a fixed scenario played entirely in
// the browser. It builds the same messages the server would send (room,
// briefing, round_start, market, you, reveal), so the real screens render it
// unchanged. Nothing here talks to the server, and the clock only moves when
// the script moves it.

import type { FeedItem, GameState, Runner } from '../game'
import type {
  BriefingMsg,
  CallState,
  GameEvent,
  MarketMsg,
  PlayerInfo,
  PublicQuote,
  RevealMsg,
  RevealPlayer,
  RoomMsg,
  RoundStartMsg,
  Side,
  Slip,
  TradeEvent,
  YouMsg,
} from '../types'

export const ME = 'p1'
const GIL = 'p2'
const OTT = 'p3'
const MIR = 'p4'

export const OPENS_AT = 1_000_000
export const CLOSES_AT = OPENS_AT + 180_000
export const FINAL = 107
const FEE = 0.25 // maker rebate and taker fee, per lot

interface Clue {
  flavor: string
  precise: string
}

interface Bot {
  id: string
  name: string
  badge: string
  look: number
  slips: Clue[]
  objective: { id: string; title: string; description: string; bonus: number; met: boolean }
  // Their trading away from you this round, and where it left them.
  otherPnl: number
  otherPosition: number
}

const BOTS: Bot[] = [
  {
    id: GIL, name: 'Gilda', badge: 'GIL', look: 1,
    slips: [{ flavor: 'The supply report is going to come in short.', precise: 'Supply Report = +1' }],
    objective: { id: 'market_maker', title: 'Market Maker', description: 'Get your posted offers filled at least 5 times on each side.', bonus: 50, met: false },
    otherPnl: 4, otherPosition: 2,
  },
  {
    id: OTT, name: 'Otto', badge: 'OTT', look: 2,
    slips: [{ flavor: 'Exporters are cancelling orders.', precise: 'Export Demand = −1' }],
    objective: { id: 'short_king', title: 'Short King', description: 'Finish at -15 or lower.', bonus: 40, met: false },
    otherPnl: -6, otherPosition: -4,
  },
  {
    id: MIR, name: 'Mirelle', badge: 'MIR', look: 3,
    slips: [
      { flavor: 'Warehouses are nearly empty.', precise: 'Stockpiles = +2' },
      { flavor: 'Shipping is on schedule.', precise: 'Freight = 0' },
    ],
    objective: { id: 'steady_hands', title: 'Steady Hands', description: "Don't buy or sell from anyone in the final 30 seconds.", bonus: 30, met: true },
    otherPnl: 9, otherPosition: 2,
  },
]

export const botName = (id: string) => BOTS.find((b) => b.id === id)?.name ?? id

const MY_CLUE: Clue = { flavor: 'Drought watch across the growing region. Keep it quiet.', precise: 'Weather = +2' }
const MY_RUNNER: Clue = { flavor: 'A big fund just got an order to go long.', precise: 'Funds Flow = +3' }
const MY_OBJECTIVE = { id: 'big_ticket', title: 'Big Ticket', description: 'Make one trade of at least 10 units.', bonus: 30 }

const DRIVERS: { name: string; value: number; knew: string[] }[] = [
  { name: 'Weather', value: 2, knew: [ME] },
  { name: 'Supply Report', value: 1, knew: [GIL] },
  { name: 'Export Demand', value: -1, knew: [OTT] },
  { name: 'Stockpiles', value: 2, knew: [MIR] },
  { name: 'Funds Flow', value: 3, knew: [ME] },
  { name: 'Freight', value: 0, knew: [MIR] },
]

const CONTRACT = { name: 'December Corn', pit: 4, description: 'The pit everyone watches when the weather turns.' }
const FACTOR_NAMES = DRIVERS.map((d) => d.name)
const RECIPE = {
  title: 'Six Drivers',
  description: `The Settlement Price is 100 + ${FACTOR_NAMES.join(' + ')}.`,
  factor_names: FACTOR_NAMES,
  min: 80,
  max: 120,
  average: 100,
}
const RULES: RoundStartMsg['rules'] = {
  position_limit: 25,
  max_order_qty: 10,
  call_max_width: 4,
  call_min_qty: 5,
  call_answer_ms: 5000,
  call_decide_ms: 5000,
  call_cooldown_ms: 15_000,
  maker_rebate: FEE,
  taker_fee: FEE,
  runner_travel_ms: 2000,
}

export type Screen = 'briefing' | 'booth' | 'reveal'

interface Fill {
  trade: TradeEvent
  mid: number // middle of the board just before the trade
}

export interface Sim {
  screen: Screen
  now: number
  status: MarketMsg['status']
  quotes: Record<string, PublicQuote> // everyone's posted market, yours included
  fills: Fill[]
  slips: Slip[]
  call: CallState | null
  events: GameEvent[] // newest first
  runners: Runner[]
  seq: number
  myName: string
  myBadge: string
  state: GameState // what the screens read; rebuilt by sync()
}

// -- building the screens' state --------------------------------------------------------

const noQuote = (): PublicQuote => ({ bid: null, bid_qty: 0, ask: null, ask_qty: 0 })

export function newSim(name: string): Sim {
  const myName = name.trim() || 'You'
  const guess = myName.replace(/[^a-z]/gi, '').slice(0, 3).toUpperCase()
  const myBadge = guess.length === 3 && !BOTS.some((b) => b.badge === guess) ? guess : 'YOU'
  return sync({
    screen: 'briefing',
    now: OPENS_AT - 10_000,
    status: 'pre_open',
    quotes: { [ME]: noQuote(), [GIL]: noQuote(), [OTT]: noQuote(), [MIR]: noQuote() },
    fills: [],
    slips: [{ kind: 'start', ...MY_CLUE, ts: OPENS_AT - 10_000 }],
    call: null,
    events: [],
    runners: [],
    seq: 1,
    myName,
    myBadge,
    state: null as unknown as GameState,
  })
}

function players(sim: Sim): PlayerInfo[] {
  return [
    { id: ME, name: sim.myName, is_bot: false, personality: null, connected: true, badge: sim.myBadge, look: 0 },
    ...BOTS.map((b) => ({ id: b.id, name: b.name, is_bot: true, personality: null, connected: true, badge: b.badge, look: b.look })),
  ]
}

function room(sim: Sim): RoomMsg {
  return {
    type: 'room',
    code: 'PRACTICE',
    phase: sim.screen === 'briefing' ? 'briefing' : sim.screen === 'booth' ? 'playing' : 'finished',
    host_id: null, // no host buttons (rematch, ring the bell) in practice
    round_number: 1,
    settings: { rounds: 1, round_seconds: 180 },
    players: players(sim),
    scores: {},
    reveal_until: null,
    ready: [],
    server_now: sim.now,
    bot_types: [],
  }
}

function briefing(): BriefingMsg {
  return {
    type: 'briefing', round_number: 1, rounds: 1, contract: CONTRACT, recipe: RECIPE, clue: MY_CLUE,
    objective: MY_OBJECTIVE, round_seconds: 180, opening_seconds: 10,
  }
}

function roundStart(sim: Sim): RoundStartMsg {
  return {
    type: 'round_start', round_number: 1, rounds: 1, contract: CONTRACT, recipe: RECIPE, clue: MY_CLUE,
    objective: MY_OBJECTIVE, opens_at: OPENS_AT, closes_at: CLOSES_AT, server_now: sim.now, rules: RULES,
  }
}

function lastPrice(sim: Sim): number | null {
  return sim.fills.length ? sim.fills[sim.fills.length - 1].trade.price : null
}

function levels(sim: Sim, side: 'bid' | 'ask'): [number, number][] {
  const qty = side === 'bid' ? 'bid_qty' : 'ask_qty'
  const at = new Map<number, number>()
  for (const q of Object.values(sim.quotes)) {
    const p = q[side]
    if (p !== null && q[qty] > 0) at.set(p, (at.get(p) ?? 0) + q[qty])
  }
  return [...at.entries()].sort((a, b) => (side === 'bid' ? b[0] - a[0] : a[0] - b[0]))
}

export function mid(sim: Sim): number {
  const bid = levels(sim, 'bid')[0]?.[0]
  const ask = levels(sim, 'ask')[0]?.[0]
  if (sim.status !== 'pre_open' && bid !== undefined && ask !== undefined && bid < ask) return (bid + ask) / 2
  return lastPrice(sim) ?? RECIPE.average
}

function market(sim: Sim): MarketMsg {
  const sealed = sim.status === 'pre_open'
  return {
    type: 'market',
    seq: sim.seq,
    server_now: sim.now,
    status: sim.status,
    bids: sealed ? [] : levels(sim, 'bid'),
    asks: sealed ? [] : levels(sim, 'ask'),
    mid: mid(sim),
    last: lastPrice(sim),
    // Before the bell, opening markets are sealed: you only see your own.
    quotes: sealed ? { [ME]: sim.quotes[ME] } : sim.quotes,
  }
}

export function position(sim: Sim, who = ME): number {
  return sim.fills.reduce((s, { trade: t }) => s + (t.buyer_id === who ? t.qty : t.seller_id === who ? -t.qty : 0), 0)
}

function cash(sim: Sim, who = ME): number {
  return sim.fills.reduce((s, { trade: t }) => {
    if (t.buyer_id !== who && t.seller_id !== who) return s
    const paid = (t.buyer_id === who ? -1 : 1) * t.price * t.qty
    return s + paid + (t.maker_id === who ? FEE : -FEE) * t.qty
  }, 0)
}

function you(sim: Sim): YouMsg {
  const q = sim.quotes[ME]
  const pos = position(sim)
  return {
    type: 'you',
    position: pos,
    cash: cash(sim),
    pnl_at_mid: cash(sim) + pos * mid(sim),
    room_to_buy: RULES.position_limit - pos - (q.bid !== null ? q.bid_qty : 0),
    room_to_sell: RULES.position_limit + pos - (q.ask !== null ? q.ask_qty : 0),
    quote: q,
    orders: [],
    slips: sim.slips,
    call: sim.call,
    server_now: sim.now,
  }
}

function sync(sim: Sim): Sim {
  const feed: FeedItem[] = sim.events.map((e) => ({ id: e.seq, ts: e.ts, event: e }))
  const booth = sim.screen !== 'briefing'
  const state: GameState = {
    connection: 'open',
    fatal: null,
    toast: null,
    me: ME,
    code: 'PRACTICE',
    room: room(sim),
    briefing: sim.screen === 'briefing' ? briefing() : null,
    round: booth ? roundStart(sim) : null,
    market: booth ? market(sim) : null,
    you: booth ? you(sim) : null,
    reveal: sim.screen === 'reveal' ? reveal(sim) : null,
    feed,
    runners: sim.runners,
    myTrades: sim.fills.map((f) => f.trade).filter((t) => t.buyer_id === ME || t.seller_id === ME).reverse(),
    offset: 0,
  }
  return { ...sim, state }
}

// -- what happens ----------------------------------------------------------------------

function emit(sim: Sim, event: Record<string, unknown> & { type: string }): Sim {
  const e = { ...event, seq: sim.seq, ts: sim.now } as GameEvent
  return { ...sim, seq: sim.seq + 1, events: [e, ...sim.events] }
}

function trade(sim: Sim, f: { price: number; qty: number; buyer: string; seller: string; maker: string; kind: 'book' | 'call' }): Sim {
  const before = mid(sim)
  const t: TradeEvent = {
    type: 'trade', seq: sim.seq, ts: sim.now, trade_id: sim.fills.length + 1, kind: f.kind, price: f.price, qty: f.qty,
    buyer_id: f.buyer, seller_id: f.seller, maker_id: f.maker, taker_id: f.maker === f.buyer ? f.seller : f.buyer,
    aggressor_side: f.maker === f.buyer ? 'sell' : 'buy',
  }
  return { ...sim, seq: sim.seq + 1, events: [t, ...sim.events], fills: [...sim.fills, { trade: t, mid: before }] }
}

/** Use up `qty` of a resting quote side; an emptied side comes down. */
function consume(sim: Sim, who: string, side: 'bid' | 'ask', qty: number): Sim {
  const q = sim.quotes[who]
  const key = side === 'bid' ? 'bid_qty' : 'ask_qty'
  const left = q[key] - qty
  const next = left > 0 ? { ...q, [key]: left } : { ...q, [side]: null, [key]: 0 }
  return { ...sim, quotes: { ...sim.quotes, [who]: next } }
}

export function at(sim: Sim, now: number): Sim {
  return sync({ ...sim, now: Math.max(sim.now, now) })
}

export function toBooth(sim: Sim): Sim {
  return sync({ ...sim, screen: 'booth', now: OPENS_AT - 7000 })
}

export function postQuote(sim: Sim, q: { bid: number; bid_qty: number; ask: number; ask_qty: number }): Sim {
  return sync({ ...sim, quotes: { ...sim.quotes, [ME]: { bid: q.bid, bid_qty: q.bid_qty, ask: q.ask, ask_qty: q.ask_qty } } })
}

/** The opening bell. The bots' markets sit just under yours, so the first
 * seller in the pit hits your bid. */
export function bell(sim: Sim): Sim {
  const b = sim.quotes[ME].bid ?? 100
  let s: Sim = {
    ...sim,
    now: OPENS_AT + 4000,
    status: 'open',
    quotes: {
      ...sim.quotes,
      [GIL]: { bid: b - 1, bid_qty: 5, ask: 102, ask_qty: 10 },
      [OTT]: { bid: b - 2, bid_qty: 5, ask: 103, ask_qty: 5 },
      [MIR]: { bid: b - 1, bid_qty: 5, ask: 105, ask_qty: 5 },
    },
  }
  s = emit(s, { type: 'status_changed', status: 'open' })
  return sync(s)
}

/** Otto sells into your buy price. */
export function ottoSells(sim: Sim): Sim {
  let s = { ...sim, now: OPENS_AT + 14_000 }
  const q = s.quotes[ME]
  if (q.bid === null) return sync(s)
  const qty = Math.min(5, q.bid_qty)
  s = trade(s, { price: q.bid, qty, buyer: ME, seller: OTT, maker: ME, kind: 'book' })
  return sync(consume(s, ME, 'bid', qty))
}

/** You take the best price on one side of the board. */
export function take(sim: Sim, side: Side, qty: number): Sim {
  const book = side === 'buy' ? 'ask' : 'bid'
  const best = levels(sim, book)[0]
  if (!best) return sim
  const holder = Object.keys(sim.quotes).find((id) => id !== ME && sim.quotes[id][book] === best[0])!
  const n = Math.min(qty, sim.quotes[holder][book === 'ask' ? 'ask_qty' : 'bid_qty'])
  let s = { ...sim, now: Math.max(sim.now, OPENS_AT + 31_000) }
  s = trade(s, side === 'buy'
    ? { price: best[0], qty: n, buyer: ME, seller: holder, maker: holder, kind: 'book' }
    : { price: best[0], qty: n, buyer: holder, seller: ME, maker: holder, kind: 'book' })
  s = consume(s, holder, book, n)
  // Gilda and Mirelle both heard good news, so they chase the price up.
  return sync(reprice(s, { [GIL]: [101, 104], [MIR]: [102, 106] }))
}

function reprice(sim: Sim, to: Record<string, [number, number]>): Sim {
  // Never through your own sell price: that would trade, not sit on the board.
  const cap = (sim.quotes[ME].ask ?? Infinity) - 1
  const quotes = { ...sim.quotes }
  for (const [id, [bid, ask]] of Object.entries(to)) quotes[id] = { bid: Math.min(bid, cap), bid_qty: 5, ask, ask_qty: 5 }
  return { ...sim, quotes }
}

export const RUNNER_MS = 2400

export function runnerOut(sim: Sim): Sim {
  const s = { ...sim, now: OPENS_AT + 52_000 }
  const r: Runner = { id: 1, recipient: ME, dispatchedAt: s.now, arriveAt: s.now + RUNNER_MS, arrived: false }
  return sync({ ...emit(s, { type: 'runner_dispatched', runner_id: 1, recipient_id: ME, arrive_at: r.arriveAt }), runners: [r] })
}

export function runnerIn(sim: Sim): Sim {
  const r = sim.runners[0]
  let s: Sim = { ...sim, now: r.arriveAt, runners: [{ ...r, arrived: true }] }
  s = emit(s, { type: 'runner_arrived', runner_id: 1, recipient_id: ME })
  return sync({ ...s, slips: [...s.slips, { kind: 'runner', ...MY_RUNNER, ts: s.now }] })
}

// Whoever you call answers with the same market: the pit agrees it's going up.
export const CALL_BID = 103
export const CALL_ASK = 106

export function callOut(sim: Sim, target: string): Sim {
  let s: Sim = { ...sim, now: OPENS_AT + 70_000 }
  s = emit(s, { type: 'call_started', call_id: 1, caller_id: ME, responder_id: target })
  s = emit(s, { type: 'call_answered', call_id: 1, responder_id: target, bid_price: CALL_BID, ask_price: CALL_ASK, qty: 5, automatic: false, penalty_cents: 0 })
  const call: CallState = { call_id: 1, role: 'caller', counterparty: target, stage: 'awaiting_decision', bid: CALL_BID, ask: CALL_ASK, qty: 5, deadline: s.now + RULES.call_decide_ms }
  // The whole pit is paying up by now.
  return sync(reprice({ ...s, call }, { [GIL]: [103, 106], [OTT]: [100, 105], [MIR]: [104, 107] }))
}

export function decide(sim: Sim, side: Side | null): Sim {
  const c = sim.call!
  let s: Sim = { ...sim, call: null }
  if (side === 'buy') s = trade(s, { price: CALL_ASK, qty: c.qty, buyer: ME, seller: c.counterparty, maker: c.counterparty, kind: 'call' })
  if (side === 'sell') s = trade(s, { price: CALL_BID, qty: c.qty, buyer: c.counterparty, seller: ME, maker: c.counterparty, kind: 'call' })
  s = emit(s, { type: 'call_ended', call_id: c.call_id, outcome: side ? 'traded' : 'passed' })
  return sync(s)
}

/** Mirelle calls you. */
export function calledBy(sim: Sim): Sim {
  let s: Sim = { ...sim, now: OPENS_AT + 96_000 }
  s = emit(s, { type: 'call_started', call_id: 2, caller_id: MIR, responder_id: ME })
  const call: CallState = { call_id: 2, role: 'responder', counterparty: MIR, stage: 'awaiting_answer', bid: null, ask: null, qty: 0, deadline: s.now + RULES.call_answer_ms }
  return sync({ ...s, call })
}

/** You answer; Mirelle (who knows Stockpiles is +2) buys at your sell price. */
export function answer(sim: Sim, a: { bid: number; ask: number; qty: number }): Sim {
  let s: Sim = { ...sim, call: null }
  s = emit(s, { type: 'call_answered', call_id: 2, responder_id: ME, bid_price: a.bid, ask_price: a.ask, qty: a.qty, automatic: false, penalty_cents: 0 })
  s = trade(s, { price: a.ask, qty: a.qty, buyer: MIR, seller: ME, maker: ME, kind: 'call' })
  s = emit(s, { type: 'call_ended', call_id: 2, outcome: 'traded' })
  return sync(s)
}

export function close(sim: Sim): Sim {
  const s = emit({ ...sim, now: CLOSES_AT, status: 'closed', call: null }, { type: 'status_changed', status: 'closed' })
  return sync({ ...s, screen: 'reveal' })
}

/** The last trade you made, for the coach to talk about. */
export function lastFill(sim: Sim): TradeEvent | undefined {
  return sim.fills[sim.fills.length - 1]?.trade
}

export function bigTicket(sim: Sim): boolean {
  return sim.fills.some(({ trade: t }) => (t.buyer_id === ME || t.seller_id === ME) && t.qty >= 10)
}

// -- settlement ------------------------------------------------------------------------

/** The same split as the server's attribution (PRD §17.2): each fill's
 * profit splits at the middle of the board just before it. */
function book(sim: Sim) {
  const out = { spread: 0, adverse_selection: 0, directional: 0, fees: 0, lost_to: {} as Record<string, number> }
  for (const { trade: t, mid: m } of sim.fills) {
    if (t.buyer_id !== ME && t.seller_id !== ME) continue
    const q = t.buyer_id === ME ? t.qty : -t.qty
    const other = t.buyer_id === ME ? t.seller_id : t.buyer_id
    out.spread += q * (m - t.price)
    const after = q * (FINAL - m)
    if (t.maker_id === ME) {
      out.adverse_selection += after
      out.lost_to[botName(other)] = (out.lost_to[botName(other)] ?? 0) + after
    } else {
      out.directional += after
    }
    out.fees += (t.maker_id === ME ? FEE : -FEE) * t.qty
  }
  out.lost_to = Object.fromEntries(Object.entries(out.lost_to).filter(([, v]) => v < 0).sort((a, b) => a[1] - b[1]))
  return out
}

function reveal(sim: Sim): RevealMsg {
  const pnl = (who: string) => cash(sim, who) + position(sim, who) * FINAL
  const b = book(sim)
  const worst = Object.entries(b.lost_to)[0]
  const worstBot = worst && BOTS.find((x) => x.name === worst[0])
  const hits = worstBot ? sim.fills.filter(({ trade: t }) => t.maker_id === ME && t.taker_id === worstBot.id).length : 0
  const myPnl = pnl(ME)
  const myBonus = bigTicket(sim) ? MY_OBJECTIVE.bonus : 0
  const unranked: RevealPlayer[] = [
    {
      id: ME, name: sim.myName, rank: 0, position: position(sim), pnl: myPnl, bonus: myBonus, score: myPnl + myBonus, badge: sim.myBadge,
      clue: MY_CLUE, slips: [MY_CLUE, MY_RUNNER],
      tell: worstBot && worst[1] <= -1
        ? `${worstBot.name} traded against your market ${hits === 1 ? 'once' : `${hits} times`} and took ${Math.round(-worst[1])} off you. Their desk said: ${worstBot.slips.map((c) => c.precise).join('; ')}.`
        : null,
      objective: { ...MY_OBJECTIVE, met: myBonus > 0 },
      breakdown: b,
    },
    ...BOTS.map((bot) => {
      const p = pnl(bot.id) + bot.otherPnl
      const bonus = bot.objective.met ? bot.objective.bonus : 0
      return {
        id: bot.id, name: bot.name, rank: 0, position: position(sim, bot.id) + bot.otherPosition, pnl: p, bonus, score: p + bonus,
        badge: bot.badge, clue: bot.slips[0], slips: bot.slips, tell: null, objective: bot.objective,
        breakdown: { spread: 0, adverse_selection: 0, directional: 0, fees: 0, lost_to: {} },
      }
    }),
  ]
  unranked.sort((x, y) => y.score - x.score)
  const ranked = unranked.map((p) => ({ ...p, rank: 1 + unranked.filter((o) => o.score > p.score).length }))
  const badge = (id: string) => (id === ME ? sim.myBadge : BOTS.find((x) => x.id === id)!.badge)
  return {
    type: 'reveal',
    round_number: 1,
    rounds: 1,
    contract: { name: CONTRACT.name, pit: CONTRACT.pit },
    final_value: FINAL,
    trades: sim.fills.length + 9, // the bots' own trades with each other
    factors: DRIVERS.map((d) => ({ name: d.name, value: d.value, knew: d.knew.map(badge) })),
    players: ranked,
    match_scores: Object.fromEntries(ranked.map((p) => [p.id, p.score])),
    last_round: true,
  }
}

/** "+5 lots at 100" style summary used in the coach's lines. */
export function describe(t: TradeEvent): string {
  return `${t.buyer_id === ME ? 'bought' : 'sold'} ${t.qty} at ${t.price}`
}

export { signed } from '../pit/format'
