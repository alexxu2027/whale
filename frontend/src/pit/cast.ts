// Who's who on the floor: badges and jackets for every player id.

import type { Game } from '../game'
import type { PlayerInfo } from '../types'
import type { Look } from './sprites'
import { playerLook } from './sprites'

export interface Cast {
  me: PlayerInfo | undefined
  others: PlayerInfo[]
  badge: (id: string | null | undefined) => string
  look: (id: string | null | undefined) => Look
}

export function cast(game: Game): Cast {
  const players = game.state.room?.players ?? []
  const meId = game.state.me
  const byId = new Map(players.map((p) => [p.id, p]))
  return {
    me: meId ? byId.get(meId) : undefined,
    others: players.filter((p) => p.id !== meId),
    badge: (id) => (!id ? '?' : id === meId ? 'YOU' : (byId.get(id)?.badge ?? '???')),
    look: (id) => playerLook(byId.get(id ?? '')?.look ?? 0),
  }
}
