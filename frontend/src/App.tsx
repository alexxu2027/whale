import { useEffect, useRef, useState } from 'react'
import { useGame } from './game'
import { markShot, shotSeen } from './pit/camera'
import { Stage } from './pit/parts'
import { Briefing } from './screens/Briefing'
import { Home } from './screens/Home'
import { Lobby } from './screens/Lobby'
import { Play } from './screens/Play'
import { Reveal } from './screens/Reveal'

export default function App() {
  const game = useGame()
  const { state } = game
  const solo = useRef(false)
  // Rounds whose closing shot has played (the camera pulls back once per round).
  const [closed, setClosed] = useState<Set<string>>(() => new Set())

  // "Play solo": as soon as we're the host of the new room, start with bots.
  useEffect(() => {
    if (solo.current && state.room?.phase === 'lobby' && state.room.host_id === state.me) {
      solo.current = false
      game.send({ type: 'start', fill_bots: true })
    }
  }, [state.room, state.me, game])

  // Keep the room in the address bar so a refresh or a shared link rejoins it.
  useEffect(() => {
    if (!state.code) return
    const url = new URL(location.href)
    url.searchParams.set('room', state.code)
    history.replaceState(null, '', url)
  }, [state.code])

  if (!state.room || state.connection === 'idle' || state.fatal) {
    const connecting = state.connection === 'connecting' && !state.fatal
    return connecting ? (
      <Stage background="#0e0c0a">
        <div className="led" style={{ display: 'grid', placeItems: 'center', height: '100%', fontSize: 36 }}>
          WALKING ONTO THE FLOOR…
        </div>
      </Stage>
    ) : (
      <Home
        error={state.fatal}
        onJoin={(code, name, isSolo) => {
          solo.current = !!isSolo
          game.join(code, name)
        }}
      />
    )
  }
  if (state.room.phase === 'lobby') return <Lobby game={game} />
  if (state.room.phase === 'briefing') return <Briefing game={game} />
  if ((state.room.phase === 'reveal' || state.room.phase === 'finished') && state.reveal) {
    const key = `whale:close:${state.code}:${state.round?.opens_at ?? state.reveal.round_number}`
    if (state.round && !closed.has(key) && !shotSeen(key)) {
      return (
        <Play
          game={game}
          closing
          onClosed={() => {
            markShot(key)
            setClosed((s) => new Set(s).add(key))
          }}
        />
      )
    }
    return <Reveal game={game} reveal={state.reveal} />
  }
  return <Play game={game} />
}
