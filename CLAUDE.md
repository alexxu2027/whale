# Whale

Multiplayer market-making party game. The source of truth for product decisions is `docs/PRD.md`. Read the relevant section before building a feature.

## Stack

- `frontend/`: React + TypeScript + Vite + Tailwind CSS (Framer Motion optional)
- `backend/`: Python + FastAPI + WebSockets, managed with `uv`
- PostgreSQL later; MVP keeps live match state in memory

## Rules that must hold

- **The server is authoritative.** Order validation, matching, and settlement happen server-side only.
- **Never send to a client before the reveal:** the hidden final value, other players' clues, hidden objectives, or future events.
- Matching uses price-time priority (PRD §25): buys sorted highest price first, sells lowest first, ties broken by earliest timestamp. Partial fills and cancels are supported.
- Default UI copy avoids finance jargon: "I will buy at" / "I will sell at", "Position", "Final Value", "Clue" (PRD §5.6, §11).
- Trading P&L stays the primary scoring driver. Objective and award bonuses must not overwhelm it.

## Build order

Follow the phases in PRD §36. Start with the First Playable Prototype (PRD §37): 4 players, a 3-minute round, a final value between 80 and 120, one clue and one objective per player, and settlement when the timer runs out. Don't add features until the core loop is fun.
