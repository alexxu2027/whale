// Number and name formatting for the pit's boards and paper.

export function signed(n: number): string {
  const r = Math.round(n)
  return r > 0 ? `+${r}` : r < 0 ? `−${-r}` : '0'
}

export function clock(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

const BOARD_NAMES: Record<string, string> = {
  'December Corn': 'DEC CORN',
  'Frozen Orange Juice': 'FROZEN OJ',
  'Crude Oil': 'CRUDE',
}

/** "December Corn" -> "DEC CORN", the way the boards abbreviate. */
export function boardName(name: string): string {
  return BOARD_NAMES[name] ?? name.toUpperCase()
}
