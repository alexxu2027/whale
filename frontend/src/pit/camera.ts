// Each camera shot plays once per round, even across a refresh.
export function shotSeen(key: string): boolean {
  try {
    return !!sessionStorage.getItem(key)
  } catch {
    return false
  }
}

export function markShot(key: string): void {
  try {
    sessionStorage.setItem(key, '1')
  } catch {
    // Storage blocked: the shot may replay after a refresh.
  }
}
