# Whale

A fast, social market-making party game. Everyone gets a partial clue about an asset's hidden final value, then buys and sells with each other in real time — bluffing, inferring, and managing inventory — until the value is revealed and the positions settle.

> "I think I know what this thing is worth. Do you know more than me, or are you bluffing?"

**Status:** pre-development. The full product spec is in [docs/PRD.md](docs/PRD.md).

## Planned stack

| Layer | Tech |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS (Framer Motion for animations) |
| Backend | Python, FastAPI, WebSockets |
| Database | PostgreSQL (persist completed games; live match state in memory) |

## Planned layout

```text
frontend/   React + Vite client
backend/    FastAPI server: game engine, matching engine, rooms, bots
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
