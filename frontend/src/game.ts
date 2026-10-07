// Connection to the room and the client-side game state.
//
// All state comes from the server. The client never decides anything about
// the market; it renders what it's told and sends player intents.

import { useCallback, useEffect, useLayoutEffect, useReducer, useRef } from 'react'
import type {
  GameEvent,
  MarketMsg,
  PlayerInfo,
  RevealMsg,
  RoomMsg,
  RoundStartMsg,
  ServerMsg,
  YouMsg,
} from './types'

export interface FeedItem {
  id: number
  ts: number
  event: GameEvent
}

export interface GameState {
  connection: 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed'
  fatal: string | null
  toast: { id: number; text: string } | null
  me: string | null
  code: string | null
  room: RoomMsg | null
  round: RoundStartMsg | null
  market: MarketMsg | null
  you: YouMsg | null
  reveal: RevealMsg | null
  feed: FeedItem[]
  // serverNow ≈ Date.now() + offset
  offset: number
}

const initial: GameState = {
  connection: 'idle',
  fatal: null,
  toast: null,
  me: null,
  code: null,
  room: null,
  round: null,
  market: null,
  you: null,
  reveal: null,
  feed: [],
  offset: 0,
}

type Action =
  | { kind: 'connecting'; code: string }
  | { kind: 'open' }
  | { kind: 'lost' }
  | { kind: 'closed' }
  | { kind: 'message'; msg: ServerMsg; receivedAt: number }
  | { kind: 'toast'; text: string }
  | { kind: 'leave' }

const FEED_LIMIT = 80

const REJECT_TEXT: Record<string, string> = {
  market_not_open: "The market isn't open.",
  rate_limited: 'Slow down a little!',
  price_out_of_band: "That price is outside the item's possible range.",
  invalid_qty: 'That size is not allowed.',
  position_limit: "That would take you past your position limit.",
  would_cross: "Your price would trade with someone. Use Buy/Sell to trade instead.",
  invalid_quote: 'Your buy price must be below your sell price (and within the allowed gap).',
  unknown_order: 'That order is already gone.',
  self_call: "You can't call yourself.",
  player_busy: "They're busy with another call.",
  call_cooldown: 'You need to wait before calling again.',
  target_at_limit: "They can't quote right now: they're at their limit.",
  call_wrong_stage: 'Too late for that.',
  unknown_call: 'That call is over.',
}

let toastId = 0

function reducer(state: GameState, action: Action): GameState {
  switch (action.kind) {
    case 'connecting':
      return { ...state, connection: state.me ? 'reconnecting' : 'connecting', code: action.code, fatal: null }
    case 'open':
      return { ...state, connection: 'open' }
    case 'lost':
      return { ...state, connection: 'reconnecting' }
    case 'closed':
      return { ...state, connection: 'closed' }
    case 'leave':
      return initial
    case 'toast':
      return { ...state, toast: { id: ++toastId, text: action.text } }
    case 'message':
      return applyMessage(state, action.msg, action.receivedAt)
  }
}

function applyMessage(state: GameState, msg: ServerMsg, receivedAt: number): GameState {
  const withClock = 'server_now' in msg ? { offset: msg.server_now - receivedAt } : {}
  switch (msg.type) {
    case 'welcome':
      return { ...state, me: msg.player_id, code: msg.code }
    case 'room': {
      const next = { ...state, ...withClock, room: msg }
      if (msg.phase === 'lobby') return { ...next, round: null, market: null, you: null, reveal: null, feed: [] }
      if (msg.phase === 'playing' && state.room?.phase !== 'playing') return { ...next, reveal: null }
      return next
    }
    case 'round_start':
      return { ...state, ...withClock, round: msg, reveal: null, feed: [], market: null, you: null }
    case 'market':
      return { ...state, ...withClock, market: msg }
    case 'you':
      return { ...state, ...withClock, you: msg }
    case 'reveal':
      return { ...state, reveal: msg }
    case 'event': {
      const e = msg.event
      if (e.type === 'order_rejected') {
        const reason = String((e as { reason: string }).reason)
        return { ...state, toast: { id: ++toastId, text: REJECT_TEXT[reason] ?? `Rejected: ${reason}` } }
      }
      if (!['trade', 'call_started', 'call_answered', 'call_ended', 'status_changed'].includes(e.type)) return state
      if (state.feed.some((f) => f.id === e.seq)) return state
      const feed = [{ id: e.seq, ts: e.ts, event: e }, ...state.feed].slice(0, FEED_LIMIT)
      return { ...state, feed }
    }
    case 'error':
      if (msg.fatal) return { ...state, fatal: msg.message, connection: 'closed' }
      return { ...state, toast: { id: ++toastId, text: msg.message } }
  }
}

const TOKEN_KEY = (code: string) => `whale:token:${code}`

function wsUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws`
}

export interface Game {
  state: GameState
  join: (code: string, name: string) => void
  leave: () => void
  send: (msg: Record<string, unknown>) => void
  serverNow: () => number
  nameOf: (id: string | null | undefined) => string
  player: (id: string) => PlayerInfo | undefined
}

export function useGame(): Game {
  const [state, dispatch] = useReducer(reducer, initial)
  const ws = useRef<WebSocket | null>(null)
  const wanted = useRef<{ code: string; name: string } | null>(null)
  const retry = useRef<number | undefined>(undefined)
  const stateRef = useRef(state)
  useLayoutEffect(() => {
    stateRef.current = state
  })

  // Only refs and the stable dispatch inside, so one instance serves forever;
  // the name lets reconnect timers call it again.
  const connect = useCallback(function open(code: string, name: string) {
    window.clearTimeout(retry.current)
    ws.current?.close()
    dispatch({ kind: 'connecting', code })
    const socket = new WebSocket(wsUrl())
    ws.current = socket
    let opened = false
    socket.onopen = () => {
      opened = true
      dispatch({ kind: 'open' })
      const token = localStorage.getItem(TOKEN_KEY(code))
      socket.send(JSON.stringify(token ? { type: 'resume', code, token } : { type: 'hello', code, name }))
    }
    socket.onmessage = (ev) => {
      const msg = JSON.parse(ev.data) as ServerMsg
      if (msg.type === 'welcome') localStorage.setItem(TOKEN_KEY(msg.code), msg.token)
      if (msg.type === 'error' && msg.fatal && localStorage.getItem(TOKEN_KEY(code))) {
        // Stale session (e.g. server restarted): forget it and join fresh.
        localStorage.removeItem(TOKEN_KEY(code))
        if (stateRef.current.room?.phase === 'lobby' || !stateRef.current.room) {
          socket.close()
          window.setTimeout(() => open(code, name), 50)
          return
        }
      }
      dispatch({ kind: 'message', msg, receivedAt: Date.now() })
    }
    socket.onclose = () => {
      if (ws.current !== socket || !wanted.current) return
      if (stateRef.current.fatal) return dispatch({ kind: 'closed' })
      dispatch({ kind: 'lost' })
      retry.current = window.setTimeout(() => open(code, name), opened ? 500 : 2000)
    }
  }, [])

  const join = useCallback(
    (code: string, name: string) => {
      wanted.current = { code: code.toUpperCase(), name }
      connect(code.toUpperCase(), name)
    },
    [connect],
  )

  const leave = useCallback(() => {
    const code = wanted.current?.code
    wanted.current = null
    if (code) localStorage.removeItem(TOKEN_KEY(code))
    const url = new URL(location.href)
    url.searchParams.delete('room')
    history.replaceState(null, '', url)
    ws.current?.close()
    ws.current = null
    dispatch({ kind: 'leave' })
  }, [])

  const send = useCallback((msg: Record<string, unknown>) => {
    const socket = ws.current
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(msg))
    else dispatch({ kind: 'toast', text: 'Reconnecting… try again in a moment.' })
  }, [])

  useEffect(() => () => ws.current?.close(), [])

  const serverNow = useCallback(() => Date.now() + stateRef.current.offset, [])
  const player = useCallback((id: string) => stateRef.current.room?.players.find((p) => p.id === id), [])
  const nameOf = useCallback(
    (id: string | null | undefined) => {
      if (!id) return '?'
      if (id === stateRef.current.me) return 'You'
      return player(id)?.name ?? id
    },
    [player],
  )

  return { state, join, leave, send, serverNow, nameOf, player }
}

/** Re-render on an interval (for countdowns). */
export function useTicker(ms: number): void {
  const [, force] = useReducer((x: number) => x + 1, 0)
  useEffect(() => {
    const id = window.setInterval(force, ms)
    return () => window.clearInterval(id)
  }, [ms])
}
