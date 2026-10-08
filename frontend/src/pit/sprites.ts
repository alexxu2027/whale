// Pixel traders, level B3 (PRD §36): 14x20 hand-placed grids, three tones per
// material lit from the left, drawn as one box-shadow per pixel.
//
// H/h hair, S/s skin, L/J/j/d jacket light/base/shadow/lapel, W shirt,
// T/t tie, B badge, P/p trousers, K shoes.

export type Pose = 'idle' | 'run' | 'buy' | 'sell' | 'call'

export interface Look {
  jacket: string
  skin: string
  hair: string
  tie?: string
  pants?: string
  collar?: 'tie' | 'open'
  pattern?: { kind: 'plaid' | 'stripes'; color: string }
  fg?: string // badge text color on this jacket
}

export function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16)
  const c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.max(0, Math.min(255, Math.round(v * f))))
  return '#' + c.map((v) => v.toString(16).padStart(2, '0')).join('')
}

const HEAD = ['.....HHHh.....', '....HHHHHh....', '....HSSSsh....', '....SSSSSs....', '.....SSSs.....', '......Ss......']
const LEGS = ['....PPPPpp....', '....PP..Pp....', '....PP..Pp....', '....PP..Pp....', '....Pp..Pp....', '...KKK..KKK...']
const RUN_LEGS = ['....PPPPpp....', '...PPP..pp....', '..PPP....pp...', '.PP.......pp..', 'PP.........pp.', 'KK.........KK.']
const TORSO = {
  tie: ['..LLLWWWWjjj..', '.LLLdWTTWdjjd.', '.LLJJdTTdJjjd.', '.LLJJdttdBBjd.', '.LLJJJddJJjjd.', '.SSJJJJJJjjss.', '...LJJJJJjj...'],
  open: ['..LLLWWWWjjj..', '.LLLdWWWWdjjd.', '.LLJJdWWdJjjd.', '.LLJJJddJBBjd.', '.LLJJJJJJjjjd.', '.SSJJJJJJjjss.', '...LJJJJJjj...'],
}
type ArmMode = 'hang' | 'up' | 'call'
const arms = (rows: string[], mode: ArmMode) =>
  rows.map((r, i) => {
    if (i === 0 || i === 6 || mode === 'hang') return r
    const c = r.split('')
    if (mode === 'up') {
      c[0] = '.'
      c[1] = '.'
      c[12] = '.'
      c[13] = '.'
      if (c[2] === 'S') c[2] = 'L'
    }
    if (mode === 'call') {
      c[12] = '.'
      c[13] = '.'
    }
    if (c[11] === 's') c[11] = 'j'
    return c.join('')
  })
// Hand signals: palms in (toward you) is buying, palms out is selling.
const TOPS: Record<Pose, string[]> = {
  idle: ['..............', ...HEAD],
  run: ['..............', ...HEAD],
  buy: ['.SS........ss.', '.LL..HHHh..jj.', '.LL.HHHHHh.jj.', '.LL.HSSSsh.jj.', '.LL.SSSSSs.jj.', '.LLL.SSSs.jjj.', '..LL..Ss..jj..'],
  sell: ['..............', '.....HHHh.....', '....HHHHHh....', 'S...HSSSsh...s', 'S...SSSSSs...s', 'LL...SSSs...jj', 'LLLL..Ss..jjjj'],
  call: ['...........ss.', '.....HHHh..jj.', '....HHHHHh.jj.', '....HSSSsh.jj.', '....SSSSSs.jj.', '.....SSSs.jjj.', '......Ss..jj..'],
}
const MODE: Record<Pose, ArmMode> = { idle: 'hang', run: 'hang', buy: 'up', sell: 'up', call: 'call' }

export const SPRITE_W = 14
export const SPRITE_H = 20

const cache = new Map<string, string>()

/** The box-shadow that draws a trader at `s` screen pixels per sprite pixel. */
export function spriteShadow(pose: Pose, look: Look, s: number): string {
  const key = `${pose}|${s}|${JSON.stringify(look)}`
  const hit = cache.get(key)
  if (hit) return hit
  const rows = [...TOPS[pose], ...arms(TORSO[look.collar ?? 'tie'], MODE[pose]), ...(pose === 'run' ? RUN_LEGS : LEGS)]
  const pants = look.pants ?? '#4a453d'
  const tie = look.tie ?? '#7a2a22'
  const pal: Record<string, string> = {
    H: look.hair, h: shade(look.hair, 0.7), S: look.skin, s: shade(look.skin, 0.8),
    L: shade(look.jacket, 1.18), J: look.jacket, j: shade(look.jacket, 0.74), d: shade(look.jacket, 0.52),
    W: '#e8e3d3', T: tie, t: shade(tie, 0.7), B: '#efe3a4', P: pants, p: shade(pants, 0.72), K: '#17140f',
  }
  const out: string[] = []
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const ch = row[x]
      let c = pal[ch]
      if (!c) continue
      const pt = look.pattern
      if (pt && 'LJj'.includes(ch) && (pt.kind === 'plaid' ? x % 3 === 0 || y % 4 === 1 : x % 2 === 0)) {
        c = ch === 'L' ? shade(pt.color, 1.15) : ch === 'j' ? shade(pt.color, 0.75) : pt.color
      }
      out.push(`${x * s}px ${y * s}px 0 0 ${c}`)
    }
  })
  const shadow = out.join(',')
  cache.set(key, shadow)
  return shadow
}

// The floor crowd.
const CROWD: Look[] = [
  { jacket: '#a8482f', skin: '#e0b08a', hair: '#2a1d12', tie: '#d8c464', pants: '#585a52' },
  { jacket: '#6f7a35', skin: '#c68c63', hair: '#5a3a1e', tie: '#7a2a22', pattern: { kind: 'plaid', color: '#d8c464' } },
  { jacket: '#2c3d6b', skin: '#8d5a3b', hair: '#1a1a1a', tie: '#a8322d', pants: '#6b5b45' },
  { jacket: '#cfcabb', skin: '#f0c8a4', hair: '#a0703a', tie: '#2c3d6b', pants: '#3d4a5c', pattern: { kind: 'stripes', color: '#8a6d3b' } },
  { jacket: '#b98a2f', skin: '#a8714b', hair: '#1a1a1a', tie: '#2c3d6b' },
  { jacket: '#9b3f5c', skin: '#e0b08a', hair: '#8a8a80', tie: '#e8e3d3', pants: '#3d4a5c' },
  { jacket: '#3f6b4f', skin: '#6b4430', hair: '#2a1d12', tie: '#c9a23a', pattern: { kind: 'stripes', color: '#cfcabb' } },
  { jacket: '#c25f2a', skin: '#f0c8a4', hair: '#5a3a1e', tie: '#2c3d6b', pants: '#585a52', pattern: { kind: 'plaid', color: '#2c3d6b' } },
  { jacket: '#e0c24a', skin: '#c68c63', hair: '#1a1a1a', tie: '#7a2a22', pants: '#6b5b45' },
  { jacket: '#5b6b7a', skin: '#e0b08a', hair: '#c9a36a', tie: '#a8322d' },
  { jacket: '#4a3f6b', skin: '#8d5a3b', hair: '#2a1d12', tie: '#d8c464', pants: '#585a52' },
  { jacket: '#7a2a22', skin: '#f0c8a4', hair: '#5a3a1e', tie: '#d9d4c3', pattern: { kind: 'stripes', color: '#d9d4c3' } },
  { jacket: '#d9d4c3', skin: '#a8714b', hair: '#1a1a1a', tie: '#7a2a22', pants: '#3d4a5c' },
  { jacket: '#2f7a72', skin: '#e0b08a', hair: '#8a8a80', tie: '#e0c24a', pattern: { kind: 'plaid', color: '#e9e4d4' } },
]

/** Roughly a third of the floor goes without a tie. */
export function crowdLook(k: number): Look {
  return { collar: (k * 7) % 3 === 0 ? 'open' : 'tie', ...CROWD[k % CROWD.length] }
}

// Players: loud, distinct jackets so badges are easy to find on the floor.
// The server hands out `look` indices in join order.
export const PLAYER_LOOKS: Look[] = [
  { jacket: '#d9d4c3', skin: '#e0b08a', hair: '#3b2a1a', tie: '#24418c', pants: '#3d4a5c', collar: 'tie', fg: '#16130f' },
  { jacket: '#c49a2c', skin: '#e0b08a', hair: '#5a3a1e', tie: '#2c3d6b', collar: 'tie', fg: '#16130f' },
  { jacket: '#2f7a72', skin: '#8d5a3b', hair: '#1a1a1a', pants: '#585a52', collar: 'open', pattern: { kind: 'plaid', color: '#d8c464' }, fg: '#eef1ea' },
  { jacket: '#74467f', skin: '#f0c8a4', hair: '#a0703a', tie: '#e8e3d3', pants: '#3d4a5c', collar: 'tie', pattern: { kind: 'stripes', color: '#9b6aa6' }, fg: '#f2ecf4' },
  { jacket: '#a8322d', skin: '#c68c63', hair: '#2a1d12', tie: '#e0c24a', pants: '#4a453d', collar: 'tie', fg: '#f3ece0' },
  { jacket: '#2c3d6b', skin: '#a8714b', hair: '#8a8a80', tie: '#d8c464', collar: 'open', fg: '#eef1fb' },
  { jacket: '#6f7a35', skin: '#f0c8a4', hair: '#c9a36a', tie: '#7a2a22', pants: '#585a52', collar: 'tie', pattern: { kind: 'stripes', color: '#d9d4c3' }, fg: '#f3ece0' },
  { jacket: '#e08a3c', skin: '#6b4430', hair: '#1a1a1a', tie: '#2c3d6b', collar: 'open', fg: '#16130f' },
]

export function playerLook(look: number): Look {
  return PLAYER_LOOKS[look % PLAYER_LOOKS.length]
}

export const RUNNER_LOOK: Look = { jacket: '#d4b98a', skin: '#c68c63', hair: '#3b3a35', pants: '#585a52', collar: 'open' }

// -- overhead tokens ----------------------------------------------------------------

const TOKEN_TOP = {
  idle: ['...hhhh...', '..hhhhhH..', '.jhhhhhHJ.', 'jjjhhhHJJJ', 'jjjjjjJJJJ', 'jjjjjJJJJJ', '.jjjjJJJJ.', '..jjJJJJ..'],
  signal: ['s..hhhh..s', 'j.hhhhhH.J', 'jjhhhhhHJJ', 'jjjhhhHJJJ', 'jjjjjjJJJJ', 'jjjjjJJJJJ', '.jjjjJJJJ.', '..jjJJJJ..'],
}

/** A trader seen from above (the round camera's overhead view), 4px per pixel. */
export function tokenShadow(look: Look, signal: boolean): string {
  const key = `token|${signal}|${look.jacket}|${look.hair}|${look.skin}`
  const hit = cache.get(key)
  if (hit) return hit
  const pal: Record<string, string> = { h: look.hair, H: shade(look.hair, 0.65), s: look.skin, j: shade(look.jacket, 1.12), J: shade(look.jacket, 0.75) }
  const out: string[] = []
  TOKEN_TOP[signal ? 'signal' : 'idle'].forEach((row, y) => {
    for (let x = 0; x < row.length; x++) if (pal[row[x]]) out.push(`${x * 4}px ${y * 4}px 0 0 ${pal[row[x]]}`)
  })
  for (let x = 1; x <= 7; x++) out.push(`${x * 4}px 32px 0 0 rgba(0,0,0,.25)`)
  const shadow = out.join(',')
  cache.set(key, shadow)
  return shadow
}
