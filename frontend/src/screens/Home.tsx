import { useState } from 'react'
import type { ReactNode } from 'react'
import { Crowd, Steps } from '../pit/Floor'
import { Stage } from '../pit/parts'

const NAME_KEY = 'whale:name'

async function createRoom(): Promise<string> {
  const res = await fetch('/api/rooms', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
  if (!res.ok) throw new Error('Could not open a pit. Is the server running?')
  return ((await res.json()) as { code: string }).code
}

/** The floor behind the menus: the pit at a lull. */
export function Backdrop({ children }: { children: ReactNode }) {
  return (
    <Stage background="#2f322a">
      <div style={{ position: 'absolute', left: 0, top: 0, width: 1440, height: 176, background: 'repeating-linear-gradient(90deg, #34372f 0 118px, #2b2e27 118px 122px)' }} />
      <div style={{ position: 'absolute', left: 0, top: 230, width: 1440, height: 426 }}>
        <Steps />
        <Crowd heat={0} />
      </div>
      <div style={{ position: 'absolute', left: 0, top: 656, width: 1440, height: 244, background: 'repeating-linear-gradient(0deg, #5a4433 0 22px, #553f2f 22px 24px)', borderTop: '8px solid #3e2e22' }} />
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(14,12,10,.35)' }} />
      {children}
    </Stage>
  )
}

export function Home({ onJoin, error }: { onJoin: (code: string, name: string, solo?: boolean) => void; error: string | null }) {
  const params = new URLSearchParams(location.search)
  const [name, setName] = useState(() => {
    try {
      return localStorage.getItem(NAME_KEY) ?? ''
    } catch {
      return ''
    }
  })
  const [code, setCode] = useState(params.get('room')?.toUpperCase() ?? '')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const cleanName = name.trim().slice(0, 20)

  const go = async (mode: 'create' | 'solo' | 'join') => {
    if (!cleanName) return setProblem('Sign your name first.')
    try {
      localStorage.setItem(NAME_KEY, cleanName)
    } catch {
      // Storage blocked: we'll just ask again next time.
    }
    setProblem(null)
    if (mode === 'join') {
      if (code.trim().length < 4) return setProblem('Enter the 4-letter pit code.')
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
    <Backdrop>
      <div className="led" style={{ position: 'absolute', left: 370, top: 40, width: 700, padding: '18px 30px', boxSizing: 'border-box', background: '#0b0906', border: '8px solid #1f1d19', boxShadow: '8px 8px 0 rgba(0,0,0,.5)', textAlign: 'center' }}>
        <div style={{ fontSize: 110, lineHeight: 1, letterSpacing: 6 }}>WHALE</div>
        <div style={{ fontSize: 20, color: 'var(--color-led-dim)', marginTop: 6 }}>OPEN OUTCRY · EVERYONE KNOWS SOMETHING DIFFERENT</div>
      </div>

      <section className="paper" style={{ position: 'absolute', left: 470, top: 300, width: 500, padding: '18px 24px', background: '#e9e4d4' }} onKeyDown={(e) => e.key === 'Enter' && void go(code ? 'join' : 'solo')}>
        <div className="paper-head">
          <span>TRADING FLOOR · BADGE REQUEST</span>
          <span style={{ color: 'var(--color-stamp)' }}>ONE DAY PASS</span>
        </div>
        <label htmlFor="name" style={{ display: 'block', marginTop: 14, fontSize: 16 }}>
          Your name on the floor
        </label>
        <input
          id="name"
          value={name}
          maxLength={20}
          autoFocus
          onChange={(e) => setName(e.target.value)}
          placeholder="Gilda"
          className="hand-num"
          style={{ width: '100%', height: 48, fontSize: 32, textAlign: 'left', color: 'var(--color-blue-ink)' }}
        />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 18 }}>
          <button type="button" className="stamp-btn silk" disabled={busy} onClick={() => void go('solo')} style={{ minHeight: 64, background: '#2f5bd3', color: '#eef1fb', fontSize: 20, boxShadow: 'inset 0 -6px 0 #1f3f99, 4px 4px 0 rgba(0,0,0,.4)' }}>
            TRADE VS BOTS
          </button>
          <button type="button" className="rule-btn" disabled={busy} onClick={() => void go('create')} style={{ border: '4px solid #9e2b25', color: '#9e2b25', fontSize: 18 }}>
            OPEN A PIT
          </button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 18, borderTop: '2px dashed #2b2418', paddingTop: 14 }}>
          <span style={{ fontSize: 16, whiteSpace: 'nowrap' }}>Friend’s pit code</span>
          <input
            aria-label="Pit code"
            value={code}
            maxLength={8}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="CODE"
            className="hand-num silk"
            style={{ flex: 1, width: 0, minWidth: 0, height: 44, fontSize: 26, letterSpacing: 6, color: 'var(--color-blue-ink)' }}
          />
          <button type="button" className="rule-btn" onClick={() => void go('join')} style={{ padding: '0 18px', border: '4px solid #2b2418', color: '#2b2418', fontSize: 16 }}>
            JOIN
          </button>
        </div>
        {(problem || error) && <p style={{ margin: '12px 0 0', color: 'var(--color-stamp)', fontWeight: 700 }}>{problem ?? error}</p>}
      </section>

      <div className="paper" style={{ position: 'absolute', left: 470, top: 690, width: 500, padding: '12px 18px', fontSize: 16, lineHeight: 1.35 }}>
        The contract settles at 100 plus six hidden market drivers. You start the round knowing one; a runner may bring you another. Buy
        below where you think it settles, sell above, and watch who's trading with you.
      </div>
    </Backdrop>
  )
}
