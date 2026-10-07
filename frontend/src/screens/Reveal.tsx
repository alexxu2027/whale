import type { Game } from '../game'
import { useTicker } from '../game'
import type { RevealMsg, RevealPlayer } from '../types'
import { Button, Card, Pill } from '../ui'
import { cx, gold, secondsLeft } from '../format'

export function Reveal({ game, reveal }: { game: Game; reveal: RevealMsg }) {
  useTicker(500)
  const { state, send } = game
  const room = state.room!
  const isHost = room.host_id === state.me
  const me = reveal.players.find((p) => p.id === state.me)
  const finished = room.phase === 'finished'
  const standings = [...room.players].sort((a, b) => (room.scores[b.id] ?? 0) - (room.scores[a.id] ?? 0))
  const nextIn = room.reveal_until !== null ? secondsLeft(room.reveal_until, game.serverNow()) : null

  return (
    <main className="mx-auto flex min-h-full max-w-4xl flex-col gap-4 px-4 py-6">
      <Card className="pop-in text-center">
        <div className="text-xs font-extrabold uppercase tracking-widest text-velvet-400">
          {reveal.item.name} · round {reveal.round_number} of {reveal.rounds}
        </div>
        <div className="font-display text-2xl text-velvet-200">Hammer price</div>
        <div className="font-display text-8xl text-gold-400 drop-shadow-[0_4px_0_rgba(0,0,0,0.4)]">{reveal.final_value}</div>
        <div className="mt-2 flex flex-wrap justify-center gap-2 text-sm">
          <span className="text-velvet-400">100</span>
          {reveal.factors.map((f) => (
            <span key={f.name} className="rounded-lg bg-velvet-950/50 px-2 py-0.5">
              {f.name} <b className={f.value > 0 ? 'text-buy-400' : f.value < 0 ? 'text-sell-400' : ''}>{gold(f.value)}</b>
            </span>
          ))}
        </div>
      </Card>

      {me && <Breakdown me={me} />}

      <Card title="Who knew what">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-velvet-400">
              <tr>
                <th className="py-1">#</th>
                <th>Merchant</th>
                <th>Their clue</th>
                <th>Objective</th>
                <th className="text-right">Trading</th>
                <th className="text-right">Bonus</th>
                <th className="text-right">Round</th>
              </tr>
            </thead>
            <tbody>
              {reveal.players.map((p) => (
                <tr key={p.id} className={cx('border-t border-velvet-700', p.id === state.me && 'bg-gold-400/10')}>
                  <td className="py-2 font-display text-lg">{p.rank}</td>
                  <td className="font-semibold">
                    {p.name}
                    <div className="text-xs font-normal text-velvet-400">ended {p.position > 0 ? `+${p.position}` : p.position}</div>
                  </td>
                  <td className="font-mono text-xs text-gold-300">{p.clue.precise}</td>
                  <td>
                    <span className="font-semibold">{p.objective.title}</span>{' '}
                    {p.objective.met ? <Pill className="bg-buy-400/20 text-buy-400">done</Pill> : <Pill className="bg-velvet-700 text-velvet-400">missed</Pill>}
                  </td>
                  <td className={cx('text-right font-semibold', p.pnl >= 0 ? 'text-buy-400' : 'text-sell-400')}>{gold(Math.round(p.pnl))}</td>
                  <td className="text-right text-gold-300">{p.bonus ? `+${p.bonus}` : '—'}</td>
                  <td className="text-right font-display text-lg">{gold(Math.round(p.score))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={finished ? 'Final standings' : 'Match standings'}>
        <ol className="flex flex-col gap-1">
          {standings.map((p, i) => (
            <li key={p.id} className="flex justify-between">
              <span>
                <span className="mr-2 font-display text-gold-400">{i + 1}.</span>
                {p.name}
                {p.id === state.me && ' (you)'}
              </span>
              <span className="font-bold">{gold(Math.round(room.scores[p.id] ?? 0))}</span>
            </li>
          ))}
        </ol>
      </Card>

      <div className="flex flex-wrap items-center justify-center gap-3 pb-6">
        {finished ? (
          isHost ? (
            <Button tone="gold" onClick={() => send({ type: 'rematch' })}>
              Rematch
            </Button>
          ) : (
            <span className="text-velvet-200">Waiting for the host to start a rematch…</span>
          )
        ) : (
          <>
            <span className="text-velvet-200">Next round in {nextIn ?? '…'}s</span>
            {isHost && (
              <Button tone="gold" onClick={() => send({ type: 'next_round' })}>
                Start now
              </Button>
            )}
          </>
        )}
        <Button tone="ghost" onClick={game.leave}>
          Leave
        </Button>
      </div>
    </main>
  )
}

function Breakdown({ me }: { me: RevealPlayer }) {
  const b = me.breakdown
  const lostTo = Object.entries(b.lost_to)
  const line = (label: string, value: number, hint: string) => (
    <div className="flex items-baseline justify-between gap-4 py-1">
      <div>
        <div className="font-semibold">{label}</div>
        <div className="text-xs text-velvet-400">{hint}</div>
      </div>
      <div className={cx('font-display text-2xl', value >= 0 ? 'text-buy-400' : 'text-sell-400')}>{gold(Math.round(value))}</div>
    </div>
  )
  return (
    <Card title="Your round" accent="text-gold-400">
      {line('Earned from your gap', b.spread, 'Buying below and selling above the market at the time')}
      {line(
        b.adverse_selection < 0 ? 'Lost to better-informed players' : 'Won from less-informed players',
        b.adverse_selection,
        lostTo.length
          ? `Mostly ${lostTo.map(([n, v]) => `${n} (${Math.round(v)})`).join(', ')}`
          : 'How the price moved after others traded with your market',
      )}
      {line('Your own bets', b.directional, 'Trades you chose to make, valued at the hammer price')}
      {Math.abs(b.fees) >= 0.5 && line('Fees and rebates', b.fees, 'Paid for taking, earned for posting')}
      <div className="mt-2 flex justify-between border-t border-velvet-600 pt-2 font-bold">
        <span>Trading P&amp;L</span>
        <span>{gold(Math.round(me.pnl))}</span>
      </div>
      <div className="flex justify-between text-sm text-velvet-200">
        <span>
          {me.objective.title}: {me.objective.met ? 'completed' : 'missed'}
        </span>
        <span>{me.bonus ? `+${me.bonus}` : '+0'}</span>
      </div>
    </Card>
  )
}
