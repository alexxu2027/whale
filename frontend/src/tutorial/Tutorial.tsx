// The practice round (a guided first game): the real briefing, booth and
// settlement screens, fed by a scripted round in the browser (./sim), with a
// coach's note on top that points at one thing at a time. Some steps wait for
// the player to try the control being explained.

import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Game } from '../game'
import { cast as castOf } from '../pit/cast'
import { Desk } from '../pit/Desk'
import { PitWindow } from '../pit/Floor'
import { Stage, StageOverlay } from '../pit/parts'
import { Ticker } from '../pit/Ticker'
import { Briefing } from '../screens/Briefing'
import { Reveal } from '../screens/Reveal'
import type { Side } from '../types'
import * as S from './sim'
import type { Sim } from './sim'

interface Rect {
  left: number
  top: number
  width: number
  height: number
}

type Msg = Record<string, unknown> & { type: string }

interface Step {
  title: string
  body: (sim: Sim) => ReactNode
  /** What to try; the step waits for it instead of showing NEXT. */
  todo?: string
  spot?: Rect
  card: { left: number; top: number }
  /** Runs when the step opens. */
  enter?: (sim: Sim) => Sim
  /** Handles a message the screens send: the new round state, or a nudge. */
  act?: (sim: Sim, msg: Msg) => Sim | string
  next?: string // label for NEXT
  /** Runs when NEXT is clicked, before the following step opens. */
  leave?: (sim: Sim) => Sim
}

// Where things sit on the 1440x900 stage.
const BOARD_BRIEF: Rect = { left: 362, top: 22, width: 716, height: 166 }
const SLIP_BRIEF: Rect = { left: 42, top: 228, width: 416, height: 446 }
const HOW_BRIEF: Rect = { left: 512, top: 228, width: 416, height: 446 }
const MEMO_BRIEF: Rect = { left: 982, top: 228, width: 416, height: 446 }
const READY: Rect = { left: 462, top: 692, width: 516, height: 88 }
const TAPE: Rect = { left: 0, top: 0, width: 1440, height: 48 }
const BOARD: Rect = { left: 412, top: 50, width: 616, height: 108 }
const TRADERS: Rect = { left: 290, top: 196, width: 860, height: 196 }
const PIT: Rect = { left: 0, top: 48, width: 1440, height: 426 }
const SLIPS: Rect = { left: 14, top: 482, width: 324, height: 268 }
const MEMO: Rect = { left: 16, top: 742, width: 316, height: 138 }
const TICKET: Rect = { left: 342, top: 480, width: 492, height: 400 }
const CARD: Rect = { left: 838, top: 488, width: 316, height: 392 }
const TRAY: Rect = { left: 1154, top: 488, width: 270, height: 392 }
const SCORE: Rect = { left: 1162, top: 784, width: 254, height: 88 }
const CALL: Rect = { left: 322, top: 496, width: 616, height: 290 }
const SETTLED: Rect = { left: 44, top: 18, width: 724, height: 450 }
const BOOK: Rect = { left: 44, top: 472, width: 724, height: 300 }
const FLOOR: Rect = { left: 800, top: 18, width: 596, height: 560 }

const b = (text: ReactNode) => <span style={{ color: 'var(--color-blue-ink)' }}>{text}</span>

const STEPS: Step[] = [
  // -- the briefing --
  {
    title: 'Welcome to the pit',
    body: () => (
      <>
        This is a practice round against three bots. Nothing here counts and the clock is frozen, so take your time.
        <br />
        <br />
        Click {b('NEXT')} to move on. When there's something to try, the note tells you what to do.
      </>
    ),
    card: { left: 500, top: 250 },
  },
  {
    title: 'One contract per round',
    body: () => (
      <>
        Everyone trades the same thing, here {b('December Corn')}. When the round ends it settles at one price:{' '}
        {b('100 plus six hidden drivers')}. Each driver is between −3 and +3, so the price always lands between 82 and 118.
      </>
    ),
    spot: BOARD_BRIEF,
    card: { left: 520, top: 250 },
  },
  {
    title: 'Your secret clue',
    body: () => (
      <>
        Only you can see this slip. {b('Weather = +2')} means the price will settle 2 higher because of the weather.
        <br />
        <br />
        Every trader has a different driver. Everyone knows a piece of the answer, and nobody knows all of it.
      </>
    ),
    spot: SLIP_BRIEF,
    card: { left: 520, top: 250 },
  },
  {
    title: 'The round in four beats',
    body: () => (
      <>
        A sealed opening, three minutes of trading, a runner with one more tip, then the price settles. This practice round walks
        through each of them.
      </>
    ),
    spot: HOW_BRIEF,
    card: { left: 990, top: 300 },
  },
  {
    title: 'A side job',
    body: () => (
      <>
        Your desk memo is a bonus goal. This one: make {b('a single trade of 10 lots or more')} for +30 points.
        <br />
        <br />
        Bonuses help, but buying below the final price and selling above it earns you more.
      </>
    ),
    spot: MEMO_BRIEF,
    card: { left: 520, top: 250 },
  },
  {
    title: 'Ready up',
    body: () => <>In a real game the clock starts only once everyone at the table is ready.</>,
    todo: "Click I'M READY · TO THE PIT.",
    spot: READY,
    card: { left: 520, top: 360 },
    act: (sim, msg) => (msg.type === 'ready' ? S.toBooth(sim) : 'Click the blue ready button.'),
  },

  // -- the booth, before the bell --
  {
    title: 'Your booth',
    body: () => (
      <>
        The top half is {b('the pit')}: the other traders stand on the steps and shout their prices.
        <br />
        <br />
        The bottom half is {b('your desk')}: your clue slips and memo, your order ticket, your trading card, and the BUY and SELL
        stamps.
      </>
    ),
    card: { left: 500, top: 210 },
  },
  {
    title: 'The price board',
    body: () => (
      <>
        {b('BELL IN 0:07')} counts down to the open. Until the bell, every trader's prices are sealed, so the board is blank. Once
        the bell rings, it shows the best prices in the pit.
      </>
    ),
    spot: BOARD,
    card: { left: 470, top: 180 },
  },
  {
    title: 'Your market',
    body: () => (
      <>
        This ticket tells the pit: {b('I will buy at')} this price, and {b('I will sell at')} a higher one.
        <br />
        <br />
        With no clue the best guess is 100, and your Weather +2 nudges it to about 102. So buy a little under 102 and sell a little
        over it.
      </>
    ),
    todo: 'Set BUY to 100 and SELL to 104 with the ▲▼ arrows (or type them), then click POST TO PIT.',
    spot: TICKET,
    card: { left: 870, top: 76 },
    act: (sim, msg) => {
      if (msg.type !== 'quote') return 'Use the ticket on the left of your desk.'
      const q = msg as unknown as { bid: number; bid_qty: number; ask: number; ask_qty: number }
      if (q.bid_qty === 0 && q.ask_qty === 0) return 'Post a market first. You can pull it later.'
      if (q.bid > 101 || q.ask < 103 || q.bid < 94 || q.ask > 110) return 'For this practice, keep BUY between 94 and 101 and SELL between 103 and 110. Try 100 and 104.'
      return S.postQuote(sim, q)
    },
  },
  {
    title: 'You’re in the pit',
    body: () => (
      <>
        The {b('IN THE PIT')} stamp means your prices are live. Anyone can sell to you at your buy price, or buy from you at your
        sell price, even while you're busy with something else.
        <br />
        <br />
        Each lot traded this way earns you a +0.25 rebate. To change your prices, edit them and click CHANGE MY MARKET.
      </>
    ),
    spot: TICKET,
    card: { left: 870, top: 76 },
    next: 'RING THE BELL',
    leave: S.bell,
  },

  // -- trading --
  {
    title: 'The bell!',
    body: () => (
      <>
        The pit is open. {b('BID')} is the highest price anyone will buy at. {b('OFFER')} is the lowest anyone will sell at.{' '}
        {b('LAST')} is the most recent trade.
        <br />
        <br />
        Click the board any time to see every price and who's quoting it.
      </>
    ),
    spot: BOARD,
    card: { left: 470, top: 180 },
  },
  {
    title: 'The other traders',
    body: () => (
      <>
        Gilda, Otto and Mirelle shout their own markets in the speech bubbles.
        <br />
        <br />
        Their prices are hints about their clues. A trader who's eager to buy has probably heard good news.
      </>
    ),
    spot: TRADERS,
    card: { left: 470, top: 410 },
    leave: S.ottoSells,
  },
  {
    title: 'Someone traded with you',
    body: (sim) => {
      const t = S.lastFill(sim)
      return (
        <>
          {t ? <>Otto sold you {t.qty} lots at your buy price, {t.price}.</> : <>Otto would have sold to your buy price.</>}{' '}
          Every trade you make is written on your {b('trading card')}: the time, B for bought or S for sold, how many, the price,
          and who with.
        </>
      )
    },
    spot: CARD,
    card: { left: 420, top: 90 },
  },
  {
    title: 'Position and profit',
    body: (sim) => (
      <>
        {b('POSITION')} is how many lots you hold. {S.signed(S.position(sim))} means you own {Math.max(0, S.position(sim))}. When
        the round ends, every lot you own is worth the settlement price, and every lot you've sold short costs it. You can hold at
        most 25 either way.
        <br />
        <br />
        {b('P&L AT MID')} is roughly your profit if the price settled at the middle of the board right now.
      </>
    ),
    spot: SCORE,
    card: { left: 700, top: 90 },
  },
  {
    title: 'Take a price',
    body: () => (
      <>
        You don't have to wait for people to trade with you. {b('BUY')} takes the cheapest price anyone is selling at, right now.
        Gilda will sell at 102, and your clue says the price should land around 102 or higher.
        <br />
        <br />
        The {b('LOTS')} buttons set how many.
      </>
    ),
    todo: 'Click LOTS 10 (that does your Big Ticket memo), then click BUY.',
    spot: TRAY,
    card: { left: 700, top: 90 },
    act: (sim, msg) => {
      if (msg.type === 'call') return 'Calls come later. For now, use the BUY stamp on the right.'
      if (msg.type !== 'order') return 'Use the BUY stamp on the right of your desk.'
      if (msg.side === 'sell') return 'Your clue leans higher, so this is a moment to buy, not sell.'
      return S.take(sim, msg.side as Side, Number(msg.qty))
    },
  },
  {
    title: 'Your desk memo',
    body: (sim) => {
      const t = S.lastFill(sim)
      return S.bigTicket(sim) ? (
        <>
          You {t && S.describe(t)}. That's one trade of 10 lots, so your memo's {b('Big Ticket')} goal is done. It pays +30 once
          the round settles.
        </>
      ) : (
        <>
          You {t && S.describe(t)}. That was under 10 lots, so the {b('Big Ticket')} memo isn't done yet. You'll get another chance
          when someone asks for your prices.
        </>
      )
    },
    spot: MEMO,
    card: { left: 360, top: 90 },
    leave: S.runnerOut,
  },
  {
    title: 'A runner!',
    body: () => (
      <>
        Partway through each round, a runner crosses the floor carrying one more private tip.
        <br />
        <br />
        Everyone sees the runner, so they know you got news, but only you get to read it.
      </>
    ),
    spot: PIT,
    card: { left: 500, top: 520 },
  },
  {
    title: 'Read your new slip',
    body: () => (
      <>
        {b('Funds Flow = +3.')} Add it to what you knew: 100 + 2 + 3 = 105, plus whatever the drivers you don't know add up to.
        <br />
        <br />
        Slips stack up. Click one that's behind to bring it to the front.
      </>
    ),
    spot: SLIPS,
    card: { left: 380, top: 90 },
  },
  {
    title: 'Make me a market',
    body: () => (
      <>
        Click any trader to put them on the spot. They have 5 seconds to shout a buy price and a sell price, no more than 4 apart,
        for at least 5 lots. Then you can trade with either one.
        <br />
        <br />
        It's a fast way to trade, and their answer tells you what they think.
      </>
    ),
    todo: 'Click Gilda, Otto or Mirelle up on the steps.',
    spot: TRADERS,
    card: { left: 470, top: 420 },
    act: (sim, msg) => (msg.type === 'call' ? S.callOut(sim, String(msg.target)) : 'Click one of the traders standing on the steps.'),
  },
  {
    title: 'They answered',
    body: (sim) => (
      <>
        {S.botName(sim.call?.counterparty ?? '')} says {b(`${S.CALL_BID} at ${S.CALL_ASK}`)}: they'll buy 5 from you at{' '}
        {S.CALL_BID} or sell you 5 at {S.CALL_ASK}.
        <br />
        <br />
        You think it's worth at least 105, and the pit keeps paying up. Your call.
      </>
    ),
    todo: `Click BUY AT ${S.CALL_ASK}, SELL AT ${S.CALL_BID}, or PASS.`,
    spot: CALL,
    card: { left: 960, top: 500 },
    act: (sim, msg) => (msg.type === 'decide' ? S.decide(sim, (msg.side as Side | null) ?? null) : 'Use the buttons on the yellow call slip.'),
  },
  {
    title: 'Now you’re on the spot',
    body: () => (
      <>
        Mirelle wants {b('your')} market. In a real round you have 5 seconds to answer, or you pay a 5-point fine and the pit
        answers for you. Here the clock is frozen.
        <br />
        <br />
        Whatever you shout, she can buy at your sell price or sell at your buy price.
      </>
    ),
    todo: 'Set a buy and a sell price at most 4 apart, then click SHOUT.',
    enter: S.calledBy,
    spot: CALL,
    card: { left: 40, top: 70 },
    act: (sim, msg) => {
      if (msg.type !== 'answer') return 'Answer Mirelle on the yellow call slip.'
      return S.answer(sim, { bid: Number(msg.bid), ask: Number(msg.ask), qty: Number(msg.qty) })
    },
  },
  {
    title: 'She bought from you',
    body: (sim) => {
      const t = S.lastFill(sim)
      return (
        <>
          Mirelle bought {t?.qty} from you at {t?.price}. Trades made on a call get a {b('*')} on your trading card.
          <br />
          <br />
          She jumped on it fast. Was that because she knows something? You'll find out at the settlement.
        </>
      )
    },
    spot: CARD,
    card: { left: 420, top: 90 },
  },
  {
    title: 'The tape',
    body: () => (
      <>
        The LED tape along the top runs everything happening on the floor: trades, calls, runners and everyone's prices. Glance at
        it when things get busy.
      </>
    ),
    spot: TAPE,
    card: { left: 500, top: 90 },
  },
  {
    title: 'The closing bell',
    enter: (sim) => S.at(sim, S.CLOSES_AT - 25_000),
    body: () => (
      <>
        A real round lasts three minutes. In the last 30 seconds the clock blinks. At zero, trading stops and the price settles.
        <br />
        <br />
        Whatever you're holding then is what counts.
      </>
    ),
    spot: BOARD,
    card: { left: 470, top: 180 },
    next: 'RING THE CLOSE',
    leave: S.close,
  },

  // -- the settlement --
  {
    title: 'Settlement',
    body: () => (
      <>
        The price settled at {b(S.FINAL)}: 100 plus all six drivers. Next to each driver is who knew about it. Nobody knew more than
        two.
      </>
    ),
    spot: SETTLED,
    card: { left: 830, top: 300 },
  },
  {
    title: 'Your book',
    body: () => (
      <>
        Every lot you bought earns {S.FINAL} minus what you paid. Every lot you sold earns what you got minus {S.FINAL}.
        <br />
        <br />
        The lines split that up: profit from your posted prices, losses to traders who knew more, your own trades, and fees. Then
        your memo bonus is added.
      </>
    ),
    spot: BOOK,
    card: { left: 830, top: 360 },
  },
  {
    title: 'Who knew what',
    body: (sim) => {
      const sold = sim.fills.some((f) => f.trade.buyer_id === 'p4' && f.trade.seller_id === S.ME)
      return (
        <>
          Everyone's slips are face up now.{' '}
          {sold ? (
            <>
              {b('The tell you missed')}: Mirelle knew Stockpiles was +2. When she was quick to buy from you, it was a clue that the
              price was going higher.
            </>
          ) : (
            <>Compare their clues to how they traded: the eager buyers knew good news.</>
          )}
        </>
      )
    },
    spot: FLOOR,
    card: { left: 140, top: 480 },
  },
  {
    title: 'You’re ready',
    body: () => (
      <>
        That's the whole game. A real match is three rounds, and the scores add up.
        <br />
        <br />
        Tips: keep your market close to what you think the price is worth, notice who trades with you, and use calls to find out
        what people know.
      </>
    ),
    card: { left: 500, top: 280 },
    next: 'BACK TO THE FRONT DOOR',
  },
]

export function Tutorial({ name, onExit }: { name: string; onExit: () => void }) {
  const [sim, setSim] = useState(() => S.newSim(name))
  const [i, setI] = useState(0)
  const [nudge, setNudge] = useState<string | null>(null)
  const step = STEPS[i]

  const goto = (n: number, from: Sim) => {
    const next = STEPS[n]
    if (!next) return onExit()
    setNudge(null)
    setI(n)
    setSim(next.enter ? next.enter(from) : from)
  }

  // The runner crosses in real time, then the clock freezes again.
  const runner = sim.runners[0]
  const running = !!runner && !runner.arrived
  const [crossing, setCrossing] = useState<number | null>(null)
  useEffect(() => {
    if (!running) return
    const startedAt = Date.now()
    setCrossing(startedAt)
    const id = window.setTimeout(() => {
      setCrossing(null)
      setSim((s) => S.runnerIn(s))
    }, S.RUNNER_MS)
    return () => window.clearTimeout(id)
  }, [running])

  const game: Game = useMemo(
    () => ({
      state: sim.state,
      join: () => {},
      leave: onExit,
      send: (msg) => {
        const m = msg as Msg
        const out = step.act?.(sim, m)
        if (out === undefined) return setNudge(step.todo ? 'Not that one yet: follow the note.' : 'Click NEXT on the note to keep going.')
        if (typeof out === 'string') return setNudge(out)
        goto(i + 1, out)
      },
      serverNow: () => sim.now + (crossing !== null ? Math.min(Date.now() - crossing, S.RUNNER_MS) : 0),
      nameOf: (id) => (!id ? '?' : id === S.ME ? 'You' : S.botName(id)),
      player: (id) => sim.state.room?.players.find((p) => p.id === id),
    }),
    // goto closes over i; step changes with i.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sim, i, crossing],
  )

  let screen: ReactNode
  if (sim.screen === 'briefing') screen = <Briefing game={game} />
  else if (sim.screen === 'reveal') screen = <Reveal game={game} reveal={sim.state.reveal!} />
  else {
    const c = castOf(game)
    const { round, market, you } = sim.state
    screen = (
      <Stage>
        <Ticker game={game} cast={c} round={round!} market={market!} />
        <PitWindow game={game} cast={c} round={round!} market={market!} you={you!} />
        <Desk game={game} cast={c} round={round!} market={market!} you={you!} />
      </Stage>
    )
  }

  return (
    <>
      {screen}
      <StageOverlay>
        <Coach
          step={step}
          sim={sim}
          n={i}
          total={STEPS.length}
          nudge={nudge}
          waiting={running}
          onNext={() => goto(i + 1, step.leave ? step.leave(sim) : sim)}
          onExit={onExit}
        />
      </StageOverlay>
    </>
  )
}

function Coach({ step, sim, n, total, nudge, waiting, onNext, onExit }: {
  step: Step
  sim: Sim
  n: number
  total: number
  nudge: string | null
  waiting: boolean
  onNext: () => void
  onExit: () => void
}) {
  return (
    <>
      {step.spot ? (
        <div
          key={`spot-${n}`}
          className="coach-spot"
          style={{ position: 'absolute', ...step.spot, boxShadow: '0 0 0 3000px rgba(8,6,4,.58)', pointerEvents: 'none' }}
        />
      ) : (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(8,6,4,.58)', pointerEvents: 'none' }} />
      )}
      <section
        key={`card-${n}`}
        className="paper drop-in"
        role="dialog"
        aria-label={step.title}
        style={{ position: 'absolute', ...step.card, width: 440, padding: '14px 20px 16px', background: '#e9e4d4', pointerEvents: 'auto', zIndex: 2, boxShadow: '8px 8px 0 rgba(0,0,0,.55)' }}
      >
        <div className="paper-head">
          <span>PRACTICE ROUND · COACH</span>
          <span>
            {n + 1} / {total}
          </span>
        </div>
        <div style={{ fontSize: 28, lineHeight: 1.1, margin: '12px 0 8px', color: 'var(--color-stamp)' }}>{step.title}</div>
        <div style={{ fontSize: 19, lineHeight: 1.3 }}>{step.body(sim)}</div>
        {step.todo && (
          <div style={{ marginTop: 12, padding: '8px 12px', border: '3px dashed var(--color-stamp)', fontSize: 19, lineHeight: 1.25 }}>
            <span className="silk" style={{ fontSize: 12, color: 'var(--color-stamp)' }}>
              DO THIS
            </span>
            <br />
            {step.todo}
          </div>
        )}
        {nudge && <div style={{ marginTop: 10, fontSize: 17, color: 'var(--color-stamp)' }}>{nudge}</div>}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 14 }}>
          {n + 1 < total && (
            <button type="button" onClick={onExit} className="silk" style={{ background: 'transparent', border: 0, padding: 0, color: '#5a5446', fontSize: 12, textDecoration: 'underline' }}>
              LEAVE PRACTICE
            </button>
          )}
          {n + 1 === total && <span />}
          {!step.todo && (
            <button
              type="button"
              className="stamp-btn silk"
              disabled={waiting}
              onClick={onNext}
              autoFocus
              style={{ minHeight: 48, padding: '0 20px', background: '#2f5bd3', color: '#eef1fb', fontSize: 16, boxShadow: 'inset 0 -5px 0 #1f3f99, 4px 4px 0 rgba(0,0,0,.4)' }}
            >
              {waiting ? 'WAIT FOR IT…' : (step.next ?? 'NEXT')} ▸
            </button>
          )}
        </div>
      </section>
    </>
  )
}
