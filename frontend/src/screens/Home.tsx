import { useState } from 'react'
import { Button, Card } from '../ui'

const NAME_KEY = 'whale:name'

async function createRoom(): Promise<string> {
  const res = await fetch('/api/rooms', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
  if (!res.ok) throw new Error('Could not create a room.')
  return ((await res.json()) as { code: string }).code
}

export function Home({ onJoin, error }: { onJoin: (code: string, name: string, solo?: boolean) => void; error: string | null }) {
  const params = new URLSearchParams(location.search)
  const [name, setName] = useState(() => localStorage.getItem(NAME_KEY) ?? '')
  const [code, setCode] = useState(params.get('room')?.toUpperCase() ?? '')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const cleanName = name.trim().slice(0, 20)

  const go = async (mode: 'create' | 'solo' | 'join') => {
    if (!cleanName) return setProblem('Pick a name first.')
    localStorage.setItem(NAME_KEY, cleanName)
    setProblem(null)
    if (mode === 'join') {
      if (code.trim().length < 4) return setProblem('Enter the 4-letter room code.')
      return onJoin(code.trim().toUpperCase(), cleanName)
    }
    setBusy(true)
    try {
      onJoin(await createRoom(), cleanName, mode === 'solo')
    } catch (e) {
      setProblem((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-full max-w-md flex-col justify-center gap-6 px-4 py-10">
      <header className="text-center">
        <div className="font-display text-7xl tracking-wide text-gold-400 drop-shadow-[0_4px_0_rgba(0,0,0,0.35)]">WHALE</div>
        <p className="mt-2 text-velvet-200">
          A market-making party game in a fantasy auction house. Everyone has heard a different rumor about the item's true
          worth. Buy low, sell high, and work out who knows what.
        </p>
      </header>

      <Card>
        <label className="text-xs font-extrabold uppercase tracking-widest text-velvet-400" htmlFor="name">
          Your merchant name
        </label>
        <input
          id="name"
          value={name}
          maxLength={20}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Lady Marigold"
          className="mt-1 w-full rounded-xl bg-velvet-950/60 px-3 py-3 text-lg outline-none ring-1 ring-velvet-600 focus:ring-gold-400"
        />
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Button tone="gold" disabled={busy} onClick={() => go('solo')}>
            Play solo vs bots
          </Button>
          <Button tone="plain" disabled={busy} onClick={() => go('create')}>
            Host a room
          </Button>
        </div>
        <div className="mt-5 flex items-center gap-2">
          <input
            aria-label="Room code"
            value={code}
            maxLength={8}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="CODE"
            className="w-0 flex-1 rounded-xl bg-velvet-950/60 px-3 py-2.5 text-center font-display text-2xl tracking-[0.3em] outline-none ring-1 ring-velvet-600 focus:ring-gold-400"
          />
          <Button tone="ghost" onClick={() => go('join')}>
            Join
          </Button>
        </div>
        {(problem || error) && <p className="mt-3 text-sm font-semibold text-sell-400">{problem ?? error}</p>}
      </Card>

      <p className="text-center text-xs text-velvet-400">
        The hammer price is 100 plus four hidden factors, each between −5 and +5. You see one.
      </p>
    </main>
  )
}
