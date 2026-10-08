// The booth, framed by the round camera (PRD §14, §36): at the bell the
// camera dives from above the pit into your booth; at the close it pulls
// back up over the paper before the settlement ledger.

import { useEffect, useState } from 'react'
import type { Game } from '../game'
import { cast as castOf } from '../pit/cast'
import { Desk } from '../pit/Desk'
import { PitWindow } from '../pit/Floor'
import { Banner, Overhead } from '../pit/Overhead'
import { markShot, shotSeen } from '../pit/camera'
import { boardName } from '../pit/format'
import { Stage } from '../pit/parts'
import { Ticker } from '../pit/Ticker'

/** `closing`: the round is over; play the pull-back, then call onClosed. */
export function Play({ game, closing, onClosed }: { game: Game; closing?: boolean; onClosed?: () => void }) {
  const { round, market, you } = game.state
  if (!round || !market || !you) {
    return (
      <Stage>
        <div className="led" style={{ display: 'grid', placeItems: 'center', height: '100%', fontSize: 36 }}>
          RINGING THE BELL…
        </div>
      </Stage>
    )
  }
  return <Camera key={round.opens_at} game={game} closing={closing} onClosed={onClosed} />
}

function Camera({ game, closing, onClosed }: { game: Game; closing?: boolean; onClosed?: () => void }) {
  const { state } = game
  const round = state.round!
  const diveKey = `whale:dive:${state.code}:${round.opens_at}`
  const [shot, setShot] = useState<'dive' | 'booth'>(() => (state.market?.status === 'pre_open' && !shotSeen(diveKey) ? 'dive' : 'booth'))
  useEffect(() => markShot(diveKey), [diveKey])
  if (!state.market || !state.you) return null
  const cast = castOf(game)
  const name = boardName(round.contract.name)
  const reveal = state.reveal
  const booth = (
    <>
      <Ticker game={game} cast={cast} round={round} market={state.market} />
      <PitWindow game={game} cast={cast} round={round} market={state.market} you={state.you} />
      <Desk game={game} cast={cast} round={round} market={state.market} you={state.you} />
    </>
  )

  if (closing && reveal) {
    // At least a few scraps per trade: the floor is ankle-deep by the close.
    const paper = Math.min(520, 60 + reveal.trades * 6)
    return (
      <Stage>
        <div onClick={onClosed} onAnimationEnd={(e) => e.target === e.currentTarget && onClosed?.()} className="cam-pull" style={{ position: 'absolute', inset: 0, cursor: 'pointer' }}>
          <Overhead
            others={cast.others}
            me={cast.me}
            paper={paper}
            paperClass="paper-in"
            banners={
              <Banner className="banner-late">
                CLOSED {reveal.final_value} · {reveal.trades} TRADES
              </Banner>
            }
          />
        </div>
        <div className="booth-out" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
          {booth}
        </div>
      </Stage>
    )
  }

  return (
    <Stage>
      {shot === 'dive' && (
        <div
          className="cam-dive"
          onAnimationEnd={(e) => e.target === e.currentTarget && setShot('booth')}
          onClick={() => setShot('booth')}
          style={{ position: 'absolute', inset: 0, zIndex: 50, cursor: 'pointer' }}
        >
          <Overhead
            others={cast.others}
            me={cast.me}
            paper={0}
            banners={
              <Banner className="banner-early">
                {name} · PIT {round.contract.pit} · ROUND {round.round_number} OF {round.rounds}
              </Banner>
            }
          />
        </div>
      )}
      <div className={shot === 'dive' ? 'booth-in' : undefined} style={{ position: 'absolute', inset: 0 }}>
        {booth}
      </div>
    </Stage>
  )
}
