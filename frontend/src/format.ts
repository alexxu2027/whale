// Formatting and small helpers shared by components.

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ')
}

export function signed(n: number, digits = 0): string {
  const s = Math.abs(n).toFixed(digits)
  if (Math.abs(n) < 0.5 * 10 ** -digits) return (0).toFixed(digits)
  return n > 0 ? `+${s}` : `−${s}`
}

export function gold(n: number): string {
  return `${signed(n, Number.isInteger(n) ? 0 : 2)}`
}

export function secondsLeft(deadline: number, now: number): number {
  return Math.max(0, Math.ceil((deadline - now) / 1000))
}
