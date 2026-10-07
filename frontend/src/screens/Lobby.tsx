import { useState } from 'react'
import type { Game } from '../game'
import { Button, Card, Pill } from '../ui'

export function Lobby({ game }: { game: Game }) {
  const { state, send, leave } = game
  const room = state.room!
  const isHost = room.host_id === state.me
  const [botType, setBotType] = useState('')
  const link = `${location.origin}/?room=${room.code}`
  const [copied, setCopied] = useState(false)

  return (
    <main className="mx-auto flex min-h-full max-w-xl flex-col gap-4 px-4 py-8">
      <header className="flex items-center justify-between">
        <button type="button" onClick={leave} className="text-sm text-velvet-400 hover:text-white">
          ← Leave
        </button>
        <div className="font-display text-2xl text-gold-400">WHALE</div>
        <div className="w-12" />
      </header>

      <Card className="text-center">
        <div className="text-xs font-extrabold uppercase tracking-widest text-velvet-400">Room code</div>
        <div className="font-display text-6xl tracking-[0.25em] text-white">{room.code}</div>
        <button
          type="button"
          className="mt-2 text-sm font-semibold text-gold-300 hover:underline"
          onClick={() => {
            void navigator.clipboard?.writeText(link)
            setCopied(true)
          }}
        >
          {copied ? 'Invite link copied!' : 'Copy invite link'}
        </button>
      </Card>

      <Card title={`Merchants (${room.players.length}/8)`}>
        <ul className="divide-y divide-velvet-700">
          {room.players.map((p) => (
            <li key={p.id} className="flex items-center justify-between py-2">
              <span className="flex items-center gap-2">
                <span className="font-semibold">{p.name}</span>
                {p.id === state.me && <Pill className="bg-gold-400 text-velvet-950">you</Pill>}
                {p.id === room.host_id && <Pill className="bg-velvet-600 text-white">host</Pill>}
                {p.is_bot && <Pill className="bg-velvet-700 text-velvet-200">bot · {p.personality}</Pill>}
                {!p.connected && <Pill className="bg-sell-500/30 text-sell-400">away</Pill>}
              </span>
              {isHost && p.is_bot && (
                <button
                  type="button"
                  className="text-sm text-velvet-400 hover:text-sell-400"
                  onClick={() => send({ type: 'remove_player', player_id: p.id })}
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
        {isHost && (
          <div className="mt-3 flex gap-2">
            <select
              aria-label="Bot type"
              value={botType}
              onChange={(e) => setBotType(e.target.value)}
              className="flex-1 rounded-xl bg-velvet-950/60 px-3 py-2 ring-1 ring-velvet-600"
            >
              <option value="">Any bot</option>
              {room.bot_types.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <Button tone="ghost" onClick={() => send({ type: 'add_bot', personality: botType || null })}>
              + Add bot
            </Button>
          </div>
        )}
      </Card>

      {isHost ? (
        <Card title="Match settings">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label className="flex flex-col gap-1">
              Rounds
              <select
                value={room.settings.rounds}
                onChange={(e) => send({ type: 'settings', rounds: Number(e.target.value), round_seconds: room.settings.round_seconds })}
                className="rounded-xl bg-velvet-950/60 px-3 py-2 ring-1 ring-velvet-600"
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              Round length
              <select
                value={room.settings.round_seconds}
                onChange={(e) => send({ type: 'settings', rounds: room.settings.rounds, round_seconds: Number(e.target.value) })}
                className="rounded-xl bg-velvet-950/60 px-3 py-2 ring-1 ring-velvet-600"
              >
                {[...new Set([90, 120, 180, 240, 300, room.settings.round_seconds])].sort((a, b) => a - b).map((s) => (
                  <option key={s} value={s}>
                    {s % 60 ? `${s} s` : `${s / 60} min`}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Button tone="ghost" disabled={room.players.length < 2} onClick={() => send({ type: 'start' })}>
              Start
            </Button>
            <Button tone="gold" onClick={() => send({ type: 'start', fill_bots: true })}>
              Start (fill with bots)
            </Button>
          </div>
        </Card>
      ) : (
        <p className="text-center text-velvet-200">Waiting for the host to start…</p>
      )}
    </main>
  )
}
