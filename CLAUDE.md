# Whale

Multiplayer market-making party game. The source of truth for product decisions is `docs/PRD.md`. Read the relevant section before building a feature.

## Stack

- `frontend/`: React + TypeScript + Vite + Tailwind CSS (Framer Motion optional)
- `backend/`: Python + FastAPI + WebSockets, managed with `uv`
- PostgreSQL later; MVP keeps live match state in memory

## Commands

From `backend/`:

- `uv run pytest`: all tests, including the Hypothesis stateful engine tests
- `uv run python bench/bench_engine.py`: engine throughput benchmark
- `uv run python -m whale.sim.harness --rounds 300 [--table "Market Maker,Shark,..."]`: headless bot-vs-bot rounds with balance stats
- `uv run uvicorn whale.multiplayer.server:app --reload`: game server on :8000

From `frontend/`: `npm run dev` (client on :5173, proxies to :8000), `npm run build`, `npm run lint`, `npx tsc -b`.

Backend code lives in the `whale` package (`backend/whale/`), so PRD §27's `engine/` is `whale/engine/`.

## Rules that must hold

- **The server is authoritative.** Order validation, matching, and settlement happen server-side only.
- **Never send to a client before the reveal:** the hidden final value, other players' clues, hidden objectives, server-computed fair values, or future events.
- The matching engine is a pure, deterministic state machine (PRD §28): integer ticks, price-time priority (buys highest first, sells lowest first, ties by earliest sequence number), partial fills, cancels, IOC, post-only, self-trade prevention, and pre-trade position limits. Every outbound message goes through the visibility projection (PRD §31).
- Default UI copy avoids finance jargon: "I will buy at" / "I will sell at", "Position", "Final Value", "Clue" (PRD §5.6, §13).
- Trading P&L stays the primary scoring driver. Objective and award bonuses must not overwhelm it.

## Build order

Follow the phases in PRD §41. Start with the First Playable Prototype (PRD §42): 4 players, a 3-minute round, the Four Cards recipe (final value 80 to 120, each player sees one card), one objective per player, Your Market plus Make Me a Market, and settlement when the timer runs out. Don't add features until the core loop is fun.
