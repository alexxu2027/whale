// Before each round: the player reads their slip and memo with the clock
// stopped, then readies up. The bell rings once every connected trader is
// ready (or the host rings it anyway).

import type { Game } from '../game'
import { boardName } from '../pit/format'
import { Backdrop } from './Home'

export function Briefing({ game }: { game: Game }) {
  const { state, send, nameOf } = game
  const room = state.room!
  const b = state.briefing
  if (!b) {
    return (
      <Backdrop>
        <div className="led" style={{ display: 'grid', placeItems: 'center', height: '100%', fontSize: 36 }}>
          DEALING THE SLIPS…
        </div>
      </Backdrop>
    )
  }
  const isHost = room.host_id === state.me
  const amReady = !!state.me && room.ready.includes(state.me)
  const waitingOn = room.players.filter((p) => !p.is_bot && p.connected && !room.ready.includes(p.id) && p.id !== state.me)
  const minutes = b.round_seconds % 60 ? `${b.round_seconds} seconds` : `${b.round_seconds / 60} minute${b.round_seconds === 60 ? '' : 's'}`
  const lead = { color: 'var(--color-blue-ink)' } // Jersey has no bold; color carries the emphasis
  const card = { position: 'absolute', top: 236, width: 400, height: 430, padding: '16px 20px', background: '#e9e4d4' } as const

  return (
    <Backdrop>
      <div className="led" style={{ position: 'absolute', left: 370, top: 30, width: 700, padding: '14px 24px', boxSizing: 'border-box', background: '#0b0906', border: '8px solid #1f1d19', boxShadow: '8px 8px 0 rgba(0,0,0,.5)', textAlign: 'center' }}>
        <div style={{ fontSize: 16, color: 'var(--color-led-dim)' }}>
          ROUND {b.round_number} OF {b.rounds} · PIT {b.contract.pit}
        </div>
        <div style={{ fontSize: 60, lineHeight: 1.1, letterSpacing: 4 }}>{boardName(b.contract.name)}</div>
        <div style={{ fontSize: 16, color: 'var(--color-led-dim)', marginTop: 4 }}>{b.contract.description}</div>
      </div>

      <section className="paper" style={{ ...card, left: 50 }}>
        <div className="paper-head">
          <span>DESK SLIP</span>
          <span style={{ color: 'var(--color-stamp)', border: '2px solid var(--color-stamp)', padding: '0 4px', fontSize: 11 }}>EYES ONLY</span>
        </div>
        <p style={{ fontSize: 15, margin: '14px 0 6px', color: '#5a5446' }}>Your tip for this round. Nobody else sees it.</p>
        <p style={{ fontSize: 26, lineHeight: 1.25, margin: '10px 0 18px', color: 'var(--color-blue-ink)' }}>“{b.clue.flavor}”</p>
        <div style={{ border: '3px dashed var(--color-rule)', padding: '10px 12px', fontSize: 22 }}>{b.clue.precise}</div>
        <p style={{ fontSize: 15, margin: '16px 0 0', color: '#5a5446' }}>
          Plus means the price settles higher, minus means lower.
        </p>
      </section>

      <section className="paper" style={{ ...card, left: 520 }}>
        <div className="paper-head">
          <span>HOW THIS ROUND GOES</span>
        </div>
        <ol style={{ margin: '14px 0 0', paddingLeft: 26, fontSize: 16, lineHeight: 1.35, display: 'grid', gap: 10 }}>
          <li>
            <b style={lead}>Before the bell</b> ({b.opening_seconds} seconds): set the price you’ll buy at and the price you’ll sell at. They stay hidden until the bell.
          </li>
          <li>
            <b style={lead}>Then {minutes} of trading.</b> Post your prices, take someone else’s with Buy or Sell, or click a trader and ask them for a price.
          </li>
          <li>
            <b style={lead}>Partway through</b>, a runner brings you one more private tip.
          </li>
          <li>
            <b style={lead}>At the close</b>, the price settles at 100 plus all {b.recipe.factor_names.length} drivers. Buy below that, sell above it.
          </li>
        </ol>
      </section>

      <section className="paper" style={{ ...card, left: 990 }}>
        <div className="paper-head">
          <span>DESK MEMO · STANDING ORDER</span>
          <span>+{b.objective.bonus}</span>
        </div>
        <p style={{ fontSize: 15, margin: '14px 0 6px', color: '#5a5446' }}>A side job from your desk. Hit it for a bonus.</p>
        <p style={{ fontSize: 24, lineHeight: 1.25, margin: '10px 0 10px' }}>{b.objective.title}</p>
        <p style={{ fontSize: 19, lineHeight: 1.35, margin: 0 }}>{b.objective.description}</p>
        <p style={{ fontSize: 15, margin: '18px 0 0', color: '#5a5446' }}>Worth +{b.objective.bonus} points. Your trading profit still counts for more.</p>
      </section>

      <div style={{ position: 'absolute', left: 470, top: 700, width: 500, display: 'grid', gap: 12, justifyItems: 'center' }}>
        <button
          type="button"
          className="stamp-btn silk"
          disabled={amReady}
          onClick={() => send({ type: 'ready' })}
          style={{ width: 500, minHeight: 72, textAlign: 'center', background: '#2f5bd3', color: '#eef1fb', fontSize: 24, boxShadow: 'inset 0 -6px 0 #1f3f99, 5px 5px 0 rgba(0,0,0,.45)' }}
        >
          {amReady ? 'READY' : "I'M READY · TO THE PIT"}
        </button>
        {amReady && waitingOn.length > 0 && (
          <div className="silk" style={{ fontSize: 14, color: '#e9e4d4', textAlign: 'center' }}>
            WAITING FOR {waitingOn.map((p) => nameOf(p.id).toUpperCase()).join(', ')}
          </div>
        )}
        {isHost && waitingOn.length > 0 && (
          <button type="button" onClick={() => send({ type: 'begin' })} className="silk" style={{ background: 'transparent', border: 0, color: 'var(--color-led)', fontSize: 13, textDecoration: 'underline' }}>
            RING THE BELL WITHOUT THEM
          </button>
        )}
      </div>
    </Backdrop>
  )
}
