# Whale

A fast, social market-making party game. Everyone gets a partial clue about an asset's hidden final value, then buys and sells with each other in real time — bluffing, inferring, and managing inventory — until the value is revealed and the positions settle.

> "I think I know what this thing is worth. Do you know more than me, or are you bluffing?"

**Status:** playable prototype. Solo against bots, or with friends by room code. The full product spec is in [docs/PRD.md](docs/PRD.md).

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
# Terminal 1: game server on :8000
cd backend
uv run uvicorn whale.multiplayer.server:app --reload

# Terminal 2: web client on :5173 (proxies /api and /ws to the server)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173, pick a name, and choose **Play solo vs bots** or **Host a room** (friends join with the 4-letter code or the invite link).

For a single server, run `npm run build` in `frontend/`; the game server then serves the built client at http://localhost:8000.

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS (Framer Motion for animations) |
| Backend | Python, FastAPI, WebSockets |
| Database | PostgreSQL later; live match state is in memory |

## Layout

```text
frontend/   React + Vite client
backend/    FastAPI server: matching engine, game logic, rooms, bots, simulator
docs/       Product requirements and design notes
```

## Roadmap

1. **Core local prototype**: hidden value, clues, buy/sell, settlement, simple bots. Prove one round is fun.
2. **Real-time multiplayer**: rooms, WebSockets, authoritative server state, reconnects.
3. **Party layer**: secret objectives, reactions, awards, reveal animations, sound.
4. **Game variety**: events, extra modes, bot personalities, difficulty, tutorial.
5. **Retention**: profiles, stats, achievements, cosmetics.

## License

[MIT](LICENSE)
