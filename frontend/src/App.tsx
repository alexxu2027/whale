import { useEffect, useRef } from 'react'
import { useGame } from './game'
import { Home } from './screens/Home'
import { Lobby } from './screens/Lobby'
import { Play } from './screens/Play'
import { Reveal } from './screens/Reveal'

export default function App() {
  const game = useGame()
  const { state } = game
  const solo = useRef(false)

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
      <div className="grid h-full place-items-center text-velvet-200">Finding the auction house…</div>
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
  if ((state.room.phase === 'reveal' || state.room.phase === 'finished') && state.reveal) {
    return <Reveal game={game} reveal={state.reveal} />
  }
  return <Play game={game} />
}
