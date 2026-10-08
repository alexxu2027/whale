# Whale

## Product Requirements Document

**Working title:** Whale  
**Product type:** Multiplayer market-making party game  
**Primary platforms:** Web. Desktop browser for Standard and Pro interfaces; phone-first layout for Party interface  
**Status:** MVP planning (revision 2)  
**Audience:** Friend groups, solo strategy players, finance students, trading-interview candidates, quants and professional traders

---

## 1. Product Summary

Whale is a fast, social market-making game where players quote prices, trade a fictional asset, react to incomplete information, bluff, manage inventory, and try to finish each round with the highest score.

The setting is an **open-outcry trading pit**. Players are floor traders in loud jackets, shouting bids and offers on commodity futures such as December Corn, Live Cattle, and Crude Oil until the closing bell. Every contract has a hidden settlement price, and every trader has heard something different from their desk, delivered by runner (§7.6, §7.7).

The game should feel closer to a party game than a professional trading terminal on the surface, and hold up to scrutiny from a professional underneath.

Players do not need finance knowledge. The interface hides market jargon, teaches mechanics through play, and makes the social dynamics as important as the math. Underneath, the game runs on an exact information model and a real exchange engine, and every round can be analyzed the way a trading desk analyzes a day.

The core fantasy is:

> "I think I know what this thing is worth. Do you know more than me, or are you bluffing?"

And the market-maker's version of it:

> "You just asked me for a price. Why? What do you know?"

Each round lasts approximately 3 to 6 minutes. Players receive partial information about an asset's hidden final value, then quote and trade with each other while new clues, events, objectives, and behavioral signals emerge.

The game should support:

- Solo play against bots
- Private multiplayer rooms for friends
- Public matchmaking later
- Short party sessions
- Competitive ranked or skill-focused modes later
- Replayable rounds with different information structures and modifiers

---

## 2. Product Vision

Build a market-making game that is:

1. Fun before it is educational.
2. Understandable without trading experience.
3. Deep enough that skilled players, including professionals, improve over time.
4. Social enough that groups create memorable moments.
5. Fast enough that losing a round does not feel punishing.
6. Structured enough that players naturally learn pricing, probability, bluffing, inventory management, and adverse selection.
7. Rigorous enough that every number the game shows is exactly correct and explainable.

The game should create moments like:

- "Why are you buying so aggressively?"
- "There is no way you know the answer."
- "I thought you were informed."
- "You dumped all of that on me."
- "I was just trying to complete my objective."
- "You moved the entire market with one trade."
- "I knew that clue mattered more than you thought."
- "You asked me for a market right after the leak. Of course you did."
- "I made money on the spread and lost it all to Alex."

---

## 3. Product Goals

### Primary Goals

- Make market making entertaining for non-finance players.
- Make market making the actual mechanic, not just the theme: players quote two-sided prices, earn spread, carry inventory, and get picked off.
- Support both solo and multiplayer play.
- Create strong social interaction between friends.
- Make each round understandable within approximately 60 seconds.
- Generate meaningful strategic decisions every few seconds.
- Encourage bluffing, inference, and reactive play.
- Provide satisfying post-round reveals and score breakdowns.
- Make players want to immediately queue another round.

### Secondary Goals

- Teach market-making intuition indirectly, then explicitly for players who want it.
- Offer enough depth for finance students, trading-interview candidates, and quants.
- Build a portfolio-quality real-time systems project: a deterministic, event-sourced matching engine with a formal information model, rigorous tests, and desk-grade post-trade analytics.
- Support future expansion into tournaments, custom games, ranked play, and user-generated round formats.

### Non-Goals for MVP

- Real-money trading
- Cryptocurrency integration
- Brokerage integration
- Real financial securities
- Complex options pricing
- Multiple simultaneous assets
- Persistent economies or pay-to-win mechanics

Note: "high-fidelity exchange simulation" is no longer a non-goal for the engine. The engine should behave like a real exchange (§28). The *interface* stays simple.

---

## 4. Target Users

### Persona A: Friend Group

A group of 3 to 8 friends wants a competitive game they can play together for 20 to 45 minutes, often in the same room on their phones.

They care about:

- Easy room creation
- Fast rounds
- Funny situations
- Bluffing
- Rivalries
- Scoreboards
- Rematches
- Minimal setup

They do not need to understand financial markets.

### Persona B: Solo Strategy Player

A user wants something quick and replayable.

They care about:

- Bots with different personalities
- Increasing difficulty
- Challenges
- High scores
- Unlockable modes
- Short sessions

### Persona C: Finance Student / Interview Candidate

A user likes Figgie, probability games, trading interviews, or market-making concepts.

They care about:

- Two-sided markets and "make me a market" practice
- Expected value
- Information asymmetry
- Inventory management
- Adverse selection
- Post-game analytics that explain their mistakes
- Skill progression

### Persona D: Quant / Professional Trader

A user who does this for a living, or wants to. They will try to break the game.

They care about:

- The information model being exact and the game being solvable in principle
- A matching engine with correct, documented semantics (priority, amends, self-trade prevention, risk checks)
- Bots that reason like real participants rather than following scripts
- Analytics they recognize: markouts, P&L attribution, fill quality, price discovery
- Keyboard-driven Pro interface
- Replays and exportable trade logs

The product serves Persona A first. Personas C and D determine the depth ceiling: nothing they see should be hand-wavy or wrong.

---

## 5. Core Design Principles

### 5.1 Fun Before Realism

If realism conflicts with game clarity or pacing, game clarity should usually win. Realism lives in the engine and the analytics, where it costs casual players nothing.

### 5.2 Hidden Information Creates Interaction

Players should rarely know whether another player's behavior is:

- informed
- deceptive
- mistaken
- inventory-driven
- objective-driven
- random

### 5.3 Short Rounds

A bad early decision should not ruin 30 minutes of gameplay.

Target round length:

**3 to 6 minutes**

### 5.4 Constant Decisions

Players should regularly decide whether to:

- buy
- sell
- quote
- wait
- widen their spread
- move their price
- bluff
- follow another player
- ask another player for a price
- complete an objective
- reduce inventory

### 5.5 Big Reveal

Each round should end with a strong settlement moment where:

- hidden value is revealed
- secret information is revealed
- objectives are revealed
- trades are explained
- P&L swings become visible
- winners and losers react

### 5.6 Minimal Finance Vocabulary

Prefer:

- Buy
- Sell
- Your Price
- Your Position
- Settlement Price
- Clue

Avoid requiring users to understand terms like:

- bid-ask spread
- adverse selection
- mark-to-market
- alpha
- gamma
- microstructure

Advanced terminology can appear in the Pro interface, optional learning screens, and analytics.

### 5.7 Low Floor, High Ceiling: One Engine, Three Lenses

There is one game engine and one set of rules. Players choose how much of it they see:

| Interface | Audience | Shows |
|-----------|----------|-------|
| **Party** | Persona A | Big buttons, best buyer / best seller, "Your Market" as two numbers, reactions. Phone-first. |
| **Standard** | Personas B, C | Simplified order book, trade feed, position and cash, post-round breakdown. |
| **Pro** | Personas C, D | Full order book depth, keyboard shortcuts, fair-value overlays after reveal, markouts, P&L attribution, exportable logs. |

A Party player and a Pro player can sit at the same table. Neither has an information or speed advantage from their interface. Pro only shows more of what is already public.

### 5.8 Market Making Is a Mechanic, Not a Theme

A game where everyone simply takes liquidity when they have an opinion is a betting game played on an order book. Whale must make quoting both sides necessary, rewarding, and risky:

- Every player has a two-sided quote ("Your Market").
- Any player can force another to quote ("Make Me a Market").
- Posting liquidity is rewarded and taking it costs a little.
- Quoting exposes you to better-informed players, and the reveal shows exactly when that happened.

See §8.

### 5.9 Every Number Is Exact

The server knows the exact probability distribution behind every round. Fair values, clue strengths, and analytics are computed, not approximated or invented. If the game tells a player "you had an edge of 3.2 on this trade," that number is mathematically correct given what they knew.

---

## 6. Core Game Loop

Each round follows this structure.

### Phase 1: Setup

The server samples the hidden state from a publicly known **recipe** (§7). The final value is a function of that hidden state.

Example recipe, shown to all players:

```text
Final Value = 100 + A + B + C + D
Each letter is a whole number from -5 to +5, equally likely.
```

The values of A, B, C and D are hidden.

### Phase 2: Private Information

Each player receives a different clue (§7.3).

Examples:

```text
C = +4
```

```text
B is not negative.
```

```text
A + D is between 2 and 6.
```

```text
The final value is greater than 105.
```

Some clues are stronger than others. Clue strength is measured exactly (§7.4) and balanced by the server.

Players do not know the quality of other players' clues.

### Phase 3: Opening Market

Players see the recipe and its implied range and average:

```text
Final value: somewhere from 80 to 120. Average: 100.
```

Every player is asked to set an opening two-sided market (§8.1) during a 10-second opening phase. Opening markets are revealed simultaneously when trading starts. This avoids an awkward silent start and gives everyone an immediate read on the table.

If opening markets cross (someone's buy price is at or above someone else's sell price), they are matched in a single-price **opening auction** (§28.7) rather than in arbitrary arrival order, so nobody wins the open by being first.

### Phase 4: Trading

Players can:

- set or update their two-sided market
- post additional buy or sell offers
- accept another player's offer
- ask another player to make a market (§8.2)
- cancel open offers
- change order sizes

All actions happen in real time.

### Phase 5: Mid-Round Events

Depending on mode, the game may introduce:

- public clues
- surprise events
- player objectives
- forced inventory
- rumors with stated reliability
- trading halts
- bonus zones
- temporary multipliers

### Phase 6: Final Trading Window

The game announces:

```text
30 SECONDS LEFT
```

The interface becomes more urgent.

Players decide whether to:

- flatten inventory
- double down
- bluff
- take liquidity
- complete objectives

### Phase 7: Settlement

The hidden value is revealed dramatically.

Example:

```text
FINAL VALUE: 117
```

Positions settle instantly.

### Phase 8: Reveal

Reveal:

- each player's private clue and what it was worth (§7.4)
- each player's secret objective
- the price discovery chart (§17.3)
- biggest winning trade
- biggest losing trade
- who got picked off, and by whom
- who moved the market most
- who bluffed successfully
- who was most accurate

### Phase 9: Scoreboard

Players earn points.

Then:

```text
NEXT ROUND
```

The next round should begin with minimal downtime.

---

## 7. Value and Information Model

This section is the mathematical core of the game. Everything else (clue balancing, bots, analytics, the reveal) depends on it.

### 7.1 Recipes

A **recipe** defines how a round's hidden state is generated and how the final value is computed. Recipes are public. Players always know the rules that generated the value, just not the outcome. This makes every round solvable in principle, which is what lets skilled players genuinely outplay others.

A recipe specifies:

- a set of hidden **components**, each with a known discrete distribution
- a settlement function from components to the final value
- a clue library and clue-assignment rules
- the price band (minimum and maximum possible final value)

Default recipe (**Four Cards**, used by the prototype):

```text
Components: A, B, C, D
Each uniform on the integers -5..+5 (independent)
Final Value V = 100 + A + B + C + D
Range: 80..120, mean 100, standard deviation ≈ 6.3
```

Other recipes, post-MVP:

- **Lopsided:** one component has a much wider range than the others, so the player who sees it holds the most valuable clue.
- **Coin Flip:** one component is either -15 or +15, which creates a bimodal value and a real reason to be scared of size.
- **Card Count:** the final value counts cards of a suit in a hidden deck, in the spirit of Figgie.
- **Product:** V = 100 + A × B, which makes the value nonlinear and fat-tailed.

### 7.2 Hidden State and Determinism

- The hidden state is sampled from a per-round random seed.
- Given the seed, the recipe, and the event log, a round is fully reproducible (§28.1).
- The seed is generated server-side with a cryptographically secure source and never leaves the server before the reveal.
- Optional post-MVP: publish a hash of the seed at round start and the seed itself at the reveal, so players can verify the value was not changed mid-round (commit-reveal).

### 7.3 Clues

A clue is a **true statement about the hidden state**. Clue types:

| Type | Example | Typical strength |
|------|---------|------------------|
| Exact component | `C = +4` | Strong |
| Component range | `B is between 1 and 5` | Medium |
| Component sign | `A is not negative` | Weak to medium |
| Comparison | `A is at least as high as D` | ~0 on its own (symmetric); useful combined with other clues |
| Sum range | `A + D is between 2 and 6` | Medium |
| Total bound | `The final value is greater than 105` | Varies widely |
| Rumor | `B is positive (70% reliable)` | Weak, and may be false |

Rules:

- Every clue is the answer to a **question chosen without looking at the hidden state** ("What is Export Demand?", "Is the settlement price at least 105?"). Each question has a fixed set of possible answers and a known probability of each answer in every state: truthful questions give the answer containing the true state; rumors give the true answer with their stated probability and the opposite answer otherwise.
- Because the choice of question carries no information and the answer process is fully specified, the posterior after a clue is exactly prior × P(answer | state). Picking clues by peeking at the state (for example, "choose a true statement that sounds interesting") would leak information and is not allowed.
- In the default recipe, each player's clue concerns different components where possible, so pooling everyone's information approximately reveals the value. The market can discover the answer only if people trade on what they know.
- Clue text is generated from templates and stored with a machine-readable form (a predicate over the state), so the server can compute with it.

### 7.4 Posterior Fair Value and Clue Strength

For each player at each moment, the server computes the exact posterior distribution of V given the recipe, that player's private clue, and all public information released so far.

The posterior gives:

- **Fair value:** the posterior mean of V
- **Uncertainty:** the posterior standard deviation of V
- **Clue strength:** the share of variance removed, `1 − Var(V | clue) / Var(V)`

Computation: recipes in MVP have small discrete state spaces (Four Cards has 11⁴ = 14,641 states), so posteriors are computed by **exact enumeration** with vectorized arithmetic: filter the states consistent with the information and weight them. Rumors weight states by their reliability rather than filtering them. Recipes with state spaces too large to enumerate use Monte Carlo sampling with a fixed seed and report the sampling error.

Three reference values exist at every moment:

```text
Public fair value     E[V | public info]
Player fair value     E[V | public info + that player's clue]
True value            V
```

These values are never sent to clients before the reveal (§31). After the reveal, they drive the analytics (§17).

### 7.5 Clue Balancing

- The clue generator targets a configured strength distribution per mode. For example, Insider mode gives every player a clue of strength 0.15 to 0.40, and One Insider mode gives one player 0.60 or more and everyone else 0.10 or less.
- Strength is measured *ex ante*, averaged over states that could have produced that clue type, so a clue does not leak information by being "obviously strong this round."
- Balancing is validated offline by the simulation harness (§32.4): across thousands of bot-played rounds, no seat or clue type should have a systematic advantage beyond what the mode intends.

### 7.6 Theme: The Pit

The math in §7.1–7.5 stays abstract. The theme is a **skin over the recipe**: it renames components, rewrites clue text, and supplies art. It never changes the probabilities. Research and sources for everything below: `docs/design/pit-references.md`.

#### Setting

Players are floor traders in an **open-outcry futures pit**, modeled on the Chicago grain and livestock pits of the 1970s to 1990s. Hundreds of traders in loud jackets stand on tiered steps around an octagonal ring, shouting bids and offers and trading with anyone across the pit. Figgie, which Jane Street uses to teach trading, was designed to simulate this kind of market.

Each round is one **contract**, such as December Corn or Live Cattle, traded for a few minutes until the closing bell. At the bell the contract settles at its **settlement price**, which is the round's final value, and every position settles at that price.

#### Vocabulary

| Market concept | In the game |
|----------------|-------------|
| Asset | The contract (e.g. December Corn) |
| Final value | Settlement price at the closing bell |
| Recipe range | "Settles between 80 and 120" |
| Private clue | A runner slip from your desk |
| Mid-round private news | A runner arriving at your booth (§7.7) |
| Buy offer / sell offer | "I will buy at" / "I will sell at". In the pit, bubbles show the shorthand "98 BID" and "102 OFFER" |
| Position | Lots you hold (long) or owe (short) |
| Unit | One lot |
| Cash | Points |
| Public information event | A wire flash on the LED ticker: crop report, weather bulletin, export sale |
| Insider (One Insider mode) | The trader whose desk got the scoop |
| Player identity | Jacket color and pattern, plus a 3-letter badge |
| Settlement | The closing bell |

#### Components Become Market Drivers

In the Four Cards recipe, each component becomes a named market driver. A driver is defined as its **effect on the price**, so a drought that pushes prices up is "Weather +4":

```text
Settlement price = 100 + Weather + Supply Report + Export Demand + Stockpiles
Each driver: -5 to +5
```

Every contract uses the same four drivers, so players learn them once. Contract-specific flavor lives in the clue text. Runners (§7.7) need drivers that nobody starts with, so the runner recipe adds two more drivers (for example **Funds Flow** and **Freight**) to make six.

#### Clue Text Is Flavor Plus a Precise Statement

Every clue has two lines: an in-world line, and the exact statement it stands for. Flavor alone would be ambiguous, and the information model only works if every player can know exactly what their clue means.

```text
"Drought watch across Iowa. Keep it quiet."
Weather = +4

"Elevators are full from here to Kansas."
Stockpiles is negative

"Big export sale to Japan on the wire tonight."
Export Demand is at least +2
```

The pit interface prints the precise line on the slip under the handwritten flavor line. Flavor text is chosen from per-contract template pools so that a clue's wording never hints at its strength beyond what the precise statement says.

#### Events Are Part of the Recipe

A mid-round event like "USDA crop report at 2:00" must be either:

- **a public clue** about existing drivers (for example, "Supply Report is at least +2"), or
- **a recipe component** whose distribution was public from the start (for example, "Export embargo: 30% chance of −10, announced at minute 2").

Either way, the event's outcome is sampled with the rest of the hidden state at round start. It is never invented mid-round, and it is never sent to clients before it fires (§31). This keeps fair values exact and events fair. Public events arrive as wire flashes on the LED ticker.

#### Prices and Units

- **Prices stay abstract: 80 to 120 points on every contract.** Real contracts quote in different units (cents per bushel, dollars per barrel), which adds flavor but makes every round harder to read at a glance. Realistic per-contract quoting is a possible Pro-mode option later.
- **One unit is one lot.**

#### Contract Catalog

Each round draws a contract from a catalog. A contract defines its name, pit number, short description, and flavor pools for each driver. Contracts do not change the math, so the catalog can grow freely without rebalancing.

| Contract | Description |
|----------|-------------|
| December Corn | The pit everyone watches when the weather turns |
| Soybeans | Moves on every rumor out of Brazil |
| Live Cattle | Feed costs, weather, and a lot of shouting |
| Pork Bellies | The contract your uncle still talks about |
| Frozen Orange Juice | One frost in Florida and the pit goes wild |
| Crude Oil | Pipelines, tankers, and politics |

#### Example Round

```text
DECEMBER CORN · PIT 4
Settles between 80 and 120

Runner slip:  "Drought watch across Iowa. Keep it quiet."
              Weather = +4

Desk memo (secret objective): Finish long 15 or more.

1:30 left · WIRE FLASH on the ticker
"USDA: export sales strong this week."
Export Demand is at least +2.

0:58 left · a runner sprints toward MRL's booth.
```

#### Theme and Name

"Whale" fits the pit: a whale is the trader whose size moves the market. Awards and objectives keep their names where they read naturally on the floor.

### 7.7 Runners: Mid-Round Private News

On the real floor, orders and news reached traders by phone and by **runners** carrying paper slips, and traders watched the runners: when a runner reached a broker, the pit noticed. Whale uses this as a mechanic.

#### Rules

- **Starting clues arrive together at the bell,** as runner slips on every desk, so the start of a round has no tell.
- **Each player receives one runner per round,** at a random time between 25% and 75% of the trading window. Every player gets the same number, and the order is random. Runners never favor players who are behind, since that would leak the standings.
- **A runner brings new information:** the answer to a question about a driver that nobody started with (the six-driver recipe in §7.6), at medium strength (0.10 to 0.25, §7.4).
- **Everyone sees the runner, nobody sees the slip.** The runner is visible crossing the floor toward the recipient's booth for about 2 seconds before arriving. Only the recipient reads the slip.

#### Why it works

- It reveals **that** someone is informed, not **what** they know. That is the market maker's real situation: you can't see the news, but you can see who just got some.
- **The recipient** chooses between trading immediately, before others react, and waiting or bluffing, because everyone is watching.
- **Market makers** choose between pulling or widening their quotes whenever a runner moves (safe but costly) and keeping their quotes up and risking being picked off.
- **Calls** gain a natural target: call the player whose runner just arrived. They must quote within the width limit, which squeezes their information out, or quote the widest market they're allowed, which is itself a tell.

#### Exactness

A runner slip is one more answer in the recipient's information. The question is chosen without looking at the hidden state and answered from the same likelihoods as any clue (§7.3), so fair values stay exact. The server emits a public `runner_dispatched` event (recipient and arrival time) and a private slip for the recipient only (§31).

#### Bots

Bots track how informed each other player is likely to be. When a runner reaches a player, bots raise that player's informed weight (π in §19.2), let it fade over about 20 seconds, and widen their regret-free quotes accordingly.

#### Tuning

The simulator (§32.4) measures how much the recipient earns in the seconds after a runner arrives, how far spreads widen, and whether the market keeps trading or freezes. The knobs are travel time (a short walk favors the recipient, a long one favors market makers), news strength, and runners per round.

#### Later options

- **Rumor slips:** some runners carry news with a stated reliability (for example 70%).
- **Decoy runners (Chaos mode):** a player pays to send an empty runner to someone else's booth, to make them look informed.
- **Analytics:** markouts around runner arrivals, for example "you were picked off 3 seconds after MRL's runner arrived" (§17.1).

---

## 8. Market-Making Mechanics

### 8.1 Your Market

Every player has exactly one **two-sided quote**, shown in plain language:

```text
YOUR MARKET

I WILL BUY AT    104   (size 5)
I WILL SELL AT   108   (size 5)
```

- Your Market sits on the order book as a pair of orders linked by the engine.
- Updating it is a single atomic cancel-replace of both sides (§28.4). There is no moment when only one side is updated.
- When one side fills, the other side stays live. The player chooses whether to re-quote. Optional auto-requote can refill the filled side at the same price after a short delay.
- Players may also place additional one-off buy and sell offers and take other offers directly.
- **Quote width** (sell price minus buy price) is always visible next to Your Market. In Party UI it is shown as "Gap: 4".

### 8.2 Make Me a Market

This is the classic trading-interview interaction, turned into a social mechanic.

Flow:

1. Player A **calls** player B by tapping their name.
2. B has **5 seconds** to answer with a two-sided price, at most **W** wide (default 4) and for at least **S** units (default 5).
3. A has **5 seconds** to **buy** at B's sell price, **sell** at B's buy price, or **pass**.
4. The result appears in the trade feed:

```text
Alex asked Sam for a market → 104 / 108
Alex bought 5 @ 108
```

Rules:

- A call is a bilateral request for quote (RFQ). The trade executes directly between A and B, not through the order book, but it counts as a normal trade for positions, the feed, and analytics. B is the maker and A is the taker.
- If B does not answer in time, B's current Your Market is used as their answer, provided it meets the width and size limits. If it does not, the engine builds a quote of the maximum width W centered on the middle of B's current market (or the middle of the order book if B has no market, or the recipe's average if the book is empty too), and B pays a small **no-quote penalty**.
- While B's answer is live, its size is reserved against B's position limit on both sides, so B can always honor it.
- Rate limits: each player can make one call every 15 seconds. A player cannot be called again while they are answering a call, or within 5 seconds of finishing one.
- Calls are public as they happen ("Alex is asking Sam for a market…"). The pressure of answering in front of everyone is part of the fun.

Why it matters: calls force players to quote, and to quote *to a specific person who might know more than them*. Answering a call is the purest form of the market-maker's dilemma. If the quote is too tight, you get picked off. If it is too wide, you look scared, which is information too. It is also one of the best-known exercises in trading interviews, so the solo version of it (§22.9) doubles as interview practice.

### 8.3 Liquidity Incentives

To make posting liquidity worth the risk:

- **Maker rebate:** a player whose resting order is filled earns a small rebate per unit (default 0.25).
- **Taker fee:** a player who takes an existing order pays the same amount per unit (default 0.25).
- The fee and rebate cancel out, so trading P&L between players stays **zero-sum**.
- Party UI shows them as "+0.25 for posting" and "−0.25 for taking." Pro UI shows "maker rebate" and "taker fee."
- Fees are configurable per mode, and Chaos Mode may disable them.

### 8.4 Position Limits

- Each player has a position limit (default **±25 units**).
- Limits are enforced **before** a trade, against worst-case exposure: current position plus every resting buy, and current position minus every resting sell (§28.6).
- Limits keep the score scale bounded, stop one player from cornering the market, and make inventory management a real constraint. When you are full, you can only trade one way, and the table can see you are stuck.

### 8.5 Quoting Obligations (Mode Option)

- **Designated Dealer:** one player at a time, rotating every 45 seconds, must keep Your Market live with width at most W. They earn double the maker rebate. Breaking the obligation costs points. This mode is good for teaching and for Pro play.
- **Everyone Quotes:** all players must keep Your Market live with width at most W, as in a market-making competition. This is the default for Pro mode.

---

## 9. Primary Game Mode: Insider

### Description

Every player receives partial information about one hidden final value.

Players quote and trade against each other while trying to infer who knows what.

### Recommended Player Count

- Minimum: 2
- Recommended: 4 to 6
- Maximum MVP target: 8

### Round Length

4 minutes by default. The first playable prototype uses 3 minutes (§42).

### Win Condition

Highest total score across the match.

### Strategic Tension

Players must distinguish between:

- genuine information
- bluffing
- panic
- mistaken valuation
- inventory management
- secret objectives

---

## 10. Secret Objectives

Secret objectives create party-game behavior and prevent every trade from being interpreted as pure information.

### Calibration Rule

Objective bonuses must stay meaningfully smaller than trading P&L. Under default settings (Four Cards, ±25 position limit), a strong player's round P&L is typically 50 to 200 points. Objective bonuses are therefore set around **30 to 50 points**, roughly the value of one good trade. That makes an objective worth bending your strategy for, but not worth abandoning it. Final values are tuned using the simulation harness (§32.4) so that no objective's expected bonus exceeds about 25% of the median absolute round P&L.

### Collector

```text
Finish with at least +15 units.
Bonus: +40 points.
```

### Short King

```text
Finish with at least -15 units.
Bonus: +40 points.
```

### Volume Trader

```text
Trade at least 50 units this round.
Bonus: +35 points.
```

### Market Maker

```text
Get at least 5 of your posted buy offers and 5 of your posted sell offers filled.
(Taking other players' offers does not count.)
Bonus: +50 points.
```

### Steady Hands

```text
Do not trade during the final 30 seconds.
Bonus: +30 points.
```

### Big Ticket

```text
Complete one trade of at least 10 units.
Bonus: +30 points.
```

### Contrarian

```text
Finish with a position on the opposite side from the table's total
(add up every other player's position; if it is zero, this objective fails).
Bonus: +40 points.
```

### Flat Finish

```text
Finish between -3 and +3 inventory.
Bonus: +40 points.
```

### Tight Quoter

```text
Keep Your Market live with a width of 3 or less for at least 2 minutes.
Bonus: +45 points.
```

Objectives should influence behavior without completely overriding the core trading game.

---

## 11. Party Mechanics

### 11.1 Player Reactions

Allow fast reactions such as:

- "Sus"
- "No way"
- "Free money"
- "Panic"
- "Interesting..."
- "You know something"
- "LOL"

These appear briefly near the trade feed.

### 11.2 Market Events

Occasional event cards can alter a round.

Examples:

#### Trading Halt

No trading for 10 seconds. Resting orders stay on the book.

#### Double Size

Minimum trade size doubles for 20 seconds.

#### Leak

A random player's clue becomes public.

#### Anonymous Mode

Player names disappear from the trade feed for 30 seconds.

#### Whale Alert

One random player must trade at least 10 units within 20 seconds or lose points.

#### Rumor

A public clue appears with a stated reliability, such as "70% reliable." The server's fair-value math uses exactly that reliability (§7.4).

#### Position Reveal

One random player's inventory becomes public.

#### News Drop

A component is revealed publicly. Every resting quote is now possibly stale. This tests who reprices fastest and who gets picked off.

These should be used sparingly to preserve strategy.

---

## 12. Social Information

The trade feed should be a major part of the game.

Example:

```text
Alex bought 8 @ 106 from Sam
Jordan sold 12 @ 104 to Maya
Alex asked Maya for a market → 105 / 109
Maya bought 5 @ 108 from Alex
```

Players should learn to interpret behavior.

The feed distinguishes who **took** and who **posted** ("Alex bought from Sam" means Alex took Sam's offer). Who pays to trade immediately is one of the most informative signals in a market.

Optional modes can hide identities:

```text
Player 3 bought 10 @ 112
```

This creates a different information environment.

---

## 13. Beginner UX

The game must be playable without knowing what a bid or ask is.

### Default Interface

Instead of:

```text
Bid
Ask
```

Use:

```text
I WILL BUY AT:
[ 104 ]

I WILL SELL AT:
[ 108 ]
```

Then optionally show:

```text
104 / 108
```

for users who want trading notation.

### Tutorial Prompt

Example:

```text
You think the asset is worth about 110.

Someone is willing to sell it to you for 103.

Buying may be a good deal.
```

### Contextual Tooltips

Example:

```text
Position: +12

You currently own 12 units.
You make more money if the final value ends above your average purchase price.
```

```text
Gap: 4

The difference between your buy and sell price.
A small gap gets more trades. A big gap protects you when someone knows more than you.
```

---

## 14. Trading Interface

### Core Elements: The Booth

The main screen (laptop browser first) is your **booth** at the edge of the pit: a window onto the pit above, your desk below (§36).

#### The ticker (top)

An amber LED ticker crawls with the public tape: trades with badges, quote changes, calls, and wire flashes.

#### The pit window

- The far side of the pit, packed with traders on its steps. Named traders show their current market in a bubble ("98 BID / 102 OFFER") and shout when they trade.
- The **LED wall board**: contract, bid, offer, last, and time to close. In Standard and Pro views it extends into the price ladder, listing badges at each price, with your own badge shown inverted.
- **Runners** crossing the floor (§7.7). A player calling you steps up to the front of the window.
- Each trader has a **Call** action for Make Me a Market.

#### The desk

```text
RUNNER SLIP        "Drought watch across Iowa."  Weather = +4
DESK MEMO          Standing order: finish long 15 or more (+40)   6 of 15
ORDER TICKET       BUY [97] for [5] lots   SELL [103] for [5] lots   Gap 6   [POST TO PIT] [PULL]
TRADING CARD       14:31  S  5  101  BRN   (your fills, in ink)
STAMPS             [BUY 5 at 102 from GLD]  [SELL 3 at 99 to MRL]   size 1 / 2 / 5 / 10
LED COUNTER        POSITION +6   P&L +18
```

- The **runner slip** is your private clue: the flavor line and the precise statement.
- The **desk memo** is your secret objective, with a tally.
- The **order ticket** is Your Market (§8.1).
- The **trading card** lists your fills: time, side, size, price, and counterparty badge.
- The **stamps** take the best offer (palms in) or the best bid (palms out).
- When you are called, a call slip lands on the desk with the countdown, and the caller stands at the front of the window.

### Party Interface (phone-first)

Party interface replaces the full order book with large actionable offers:

```text
BEST BUYER
104 × 8

BEST SELLER
108 × 5

[ SELL TO THEM ]
[ BUY FROM THEM ]

YOUR MARKET  104 / 108   [ − ] [ + ]
```

When a player is called, their phone takes over with a large two-number quote picker and a countdown.

### Pro Interface

- Full order book depth, with your orders and queue position highlighted
- Keyboard shortcuts for every action (quote, shift the quote up or down a tick, widen, narrow, take best offer, cancel all)
- Running position, average entry price, and realized vs. unrealized P&L
- After the reveal: fair-value overlays, markouts, and P&L attribution (§17)

Pro adds visibility of public data only. It never reveals more information than other interfaces.

---

## 15. Scoring System

The scoring system rewards good trading while preserving party-game variability.

### Base P&L

At settlement:

```text
Trading P&L = Cash Change + Position × Final Value + Rebates − Fees
```

Between players, trading P&L is zero-sum (fees and rebates cancel out). Bots, when present, are counterparties like any other player.

### Round Points

```text
Round Score = Trading P&L + Objective Bonus + Award Bonuses
```

### Award Bonuses

Examples:

```text
Best Bluff              +20
Most Accurate Market    +20
Best Liquidity Provider +20
Biggest Comeback        +15
Market Mover            +10
```

Award bonuses are smaller than objective bonuses, which are smaller than typical trading P&L (§10 calibration rule). Trading performance must remain the primary driver of rank.

### Match Score

Round scores add up across the match. Cash and inventory reset every round. There is no compounding bankroll in default modes (§40, Risk 3).

---

## 16. Post-Round Reveal

This is a critical product feature.

### Reveal Sequence

1. **The closing bell:** the camera pulls back to the overhead view, and the floor is covered in paper, one scrap per trade (§36.6).
2. **The settlement price** lights up on the LED board.
3. **The settlement ledger**, itemized like an end-of-day ledger:
   - **How it settled:** each driver's value, marked with who knew it ("Weather +4, your slip"; "Export Demand −1, MRL knew").
   - **Your book:** earned from your gap, lost to better-informed players (by counterparty), your own bets, fees, and the total (§17.2).
   - **Your standing order:** met or missed, and the bonus.
4. **The floor, who knew what:** every trader's slips, including runner slips, their objective, and their round score, ranked.
5. **The tell you missed:** one plain-language line drawn from the attribution, for example "MRL sold to you 4 times at 102 and up; her desk said Export Demand was weak."
6. Price discovery chart (§17.3), awards, and key trades, including "picked off" moments.

### Example

```text
SETTLEMENT PRICE
117
```

```text
Alex
+182

Sam
+64

Maya
+14

Jordan
-260
```

Then:

```text
ALEX'S CLUE
Final value > 110
(told Alex the value was about 114, not 100)

SAM'S CLUE
A is positive

MAYA'S OBJECTIVE
Finish short 15 units
COMPLETED
```

Then a personal breakdown, in plain language:

```text
YOUR ROUND (Jordan)

Earned from your buy/sell gap      +46
Lost to better-informed players    −188   (mostly Alex)
Your own bets                      −118
                                   ────
Trading P&L                        −260
```

This lets players understand behavior retroactively, and teaches adverse selection without using the term.

---

## 17. Trade Analytics and Learning Layer

The analytics layer is where the game earns respect from Personas C and D. It also explains the game to Persona A in one glance. Every metric here is computed from the event log and the exact information model (§7.4).

### 17.1 Per-Fill Metrics

For each fill, with signed quantity q (positive for a buy):

- **Edge vs. true value:** `q × (V − price)`. Was the trade good in hindsight?
- **Edge vs. own fair value:** `q × (FV_player(t) − price)`. Was the trade good given what the player knew at that moment? This separates skill from luck.
- **Markouts:** `q × (mid(t + Δ) − price)` for Δ = 5s, 30s, and settlement (where the middle price at settlement is defined as V). Markouts show whether the market moved against a fill right after it, which is the signature of being picked off.
- **Maker or taker**, and for calls, who called whom.

### 17.2 P&L Attribution

Each player's trading P&L is decomposed exactly. For each fill, `mid(t)` is the middle of the best buy and best sell price just before the fill. If one side of the book is empty, it falls back to the last trade price, then to the public fair value.

Each fill's settlement P&L, `q × (V − price)`, splits into two parts: what the fill earned against the market at that moment, and what happened afterward. That gives:

```text
Spread P&L           = Σ all fills         q × (mid(t) − price)
Adverse selection    = Σ passive fills     q × (V − mid(t))
Directional P&L      = Σ aggressive fills  q × (V − mid(t))
Fees/Rebates         = Σ rebates − Σ fees
Trading P&L          = Spread + Adverse selection + Directional + Fees/Rebates
```

The sum is exact by construction.

- **Spread P&L** is usually positive for makers (they earn the gap) and negative for takers (they pay it).
- **Adverse selection** is the market-maker's cost: how much of the spread they earned was taken back because the counterparty knew more. The analytics break it down **by counterparty**, which enables the "you lost 140 to Alex" line in the reveal.
- **Directional P&L** is how well a player's own decisions to take offers worked out.

An alternative view, shown in Pro, splits P&L by time instead of by fill: execution P&L plus inventory P&L, `∫ position(t) d mid(t)` with `mid(end) := V`.

### 17.3 Price Discovery Chart

A post-round chart showing:

- the market's middle price over time
- each player's fair value over time (revealed after settlement)
- the public fair value over time
- the true value V as a horizontal line
- event markers (news, leaks, rumors) and large trades

It shows visually whether the market found the answer, how fast, and who pushed it there. Headline metric:

```text
Price discovery = 1 − |mid(end) − V| / |prior mean − V|
```

### 17.4 Skill Ratings

Descriptive ratings shown on the profile, computed over many rounds:

| Rating | Measured as |
|--------|-------------|
| Pricing | How far the middle of Your Market sits from your own fair value |
| Information Reading | How well your trade direction matches your fair-value edge after accounting for others' flow |
| Liquidity | Time quoting × tightness × size |
| Risk Control | Time-weighted average size of your position relative to your limit |
| Adverse Selection | Average markout on your passive fills (higher is better) |
| Bluffing | How often opponents traded against your fills and lost |

Ratings are labeled as descriptive, not authoritative, until validated against outcomes.

### 17.5 Replays and Export

- Any completed round can be replayed tick by tick from the event log, with the order book, feed, and (after the reveal) fair values shown.
- Pro users can export a round's full event log and fills as CSV or JSON.

---

## 18. End-of-Game Awards

At the end of a multi-round match, assign fun titles.

Examples:

- The Market Maker
- The Insider
- The Bag Holder
- The Whale
- The Contrarian
- The Panic Seller
- Steady Hands
- The Liquidity Goblin
- The Human Bloomberg
- The Exit Liquidity
- Picked Off (most adverse selection suffered)
- Most Suspicious
- Best Bluff
- Biggest Comeback
- Worst Trade of the Night

Awards are computed from the analytics in §17, so they are funny *and* accurate. "The Exit Liquidity" goes to the player whose passive fills had the worst settlement markout.

These awards are primarily social and comedic.

---

## 19. Solo Mode and Bots

Solo mode depends entirely on bots, so bot quality is a core feature, not a filler.

### 19.1 Bot Architecture

- Bots are **ordinary clients** of the engine. They connect through the same protocol (§29), receive the same filtered information as a human in their seat, and have no privileged access to hidden state.
- Bots receive clues from the same generator as humans.
- Bots have a minimum **think time** (400–700 ms by default, never below 300 ms at any difficulty). A bot's commands reach the exchange that long after the moment it looked at the market, as in ABIDES's computation-delay model, so no bot can react to anything faster than its think time. Bots compete on reasoning, not reflexes.

### 19.2 Bot Reasoning Core

Every bot shares a model, with personality parameters:

**Beliefs.** The bot keeps a probability distribution over the hidden state, starting from the posterior given its clue and public information (§7.4). It updates on **order flow**: an aggressive buy at price p is evidence that the buyer's fair value is above p. The update uses a likelihood with an assumed informed-trader fraction π, a simplified version of the Glosten-Milgrom model:

```text
P(buy at p | state) ∝ π · P(trader's FV > p | state) + (1 − π) · ½
```

where `P(trader's FV > p | state)` is estimated from the clue types the trader could have received.

**Quoting.** Quotes follow Glosten–Milgrom: the ask is the lowest price at or above fair value where `ask ≥ E[V | an unknown player buys at the ask]`, and the bid the highest where `bid ≤ E[V | an unknown player sells at the bid]`. Both are computed exactly from the bot's belief, so a flat bot never posts a price it expects to regret, and its spread widens automatically when it believes others are better informed. On top of that:

```text
bid = min(regret-free bid, FV − margin) − γ · position
ask = max(regret-free ask, FV + margin) − γ · position
```

The inventory lean (γ, after Avellaneda–Stoikov) lets a bot give up its adverse-selection premium to shed inventory, but never quote the unloading side past its own fair value.

**Taking.** The bot takes an offer when its edge versus fair value is above a threshold and its position limit allows.

**Answering calls.** The bot widens its gap based on how informed it believes the caller is, using the caller's past flow.

**Reacting to runners.** When a runner reaches another player, the bot raises its estimate of how informed that player is, lets it fade over about 20 seconds, and widens its quotes to them in the meantime (§7.7).

### 19.3 Personalities

| Bot | Parameters |
|-----|-----------|
| The Conservative | wide gap, small size, strong inventory lean, low π assumed |
| The Whale | large size, low take threshold, moves markets |
| The Insider | gets strong clues, trades selectively, mostly takes |
| The Noise Trader | trades at random intervals and directions, often wrong |
| The Market Maker | tight gap, fast requoting, disciplined inventory lean, high activity |
| The Bluffer | sometimes trades against its own fair value to mislead, then reverses |

### 19.4 Difficulty

Difficulty modifies:

- belief-update accuracy (from ignoring flow up to the full model)
- reaction latency
- pricing noise
- bluff frequency
- inventory discipline (γ)

Difficulty is validated in the simulation harness (§32.4). Each level should beat the level below it by a measurable margin over many rounds.

---

## 20. Multiplayer Lobby

### Room Creation

Host selects:

```text
Number of rounds
Round duration
Game mode
Recipe
Interface default (Party / Standard / Pro) – each player can override
Secret objectives on/off
Events on/off
Fees on/off
Bots allowed
```

### Joining

Players join using:

- room code
- invite link
- QR code later

No account should be required for private MVP games.

Player enters:

```text
Display Name
```

and joins immediately.

### Lobby Experience

Show:

- player avatars
- readiness state
- game settings
- host controls

Players can select simple cosmetic avatars.

---

## 21. Match Structure

Recommended default:

```text
5 rounds
4 minutes per round
~25 minute session
```

Scores accumulate across rounds.

Between rounds:

```text
20 to 30 seconds
```

for reveals and banter. Analytics remain viewable in a match summary at the end.

---

## 22. Additional Game Modes

These are post-MVP unless otherwise noted.

### 22.1 Chaos Mode

More event cards and unusual objectives. Fees off.

Designed specifically for friend groups.

### 22.2 Pure Market

No events or objectives. Only information, quoting, and trading. Fees on.

Best for competitive users.

### 22.3 Pro Mode

Pure Market with Everyone Quotes obligations (§8.5), the Pro interface default, and full analytics. The mode for Persona D.

### 22.4 Trivia Market

Settlement value is based on a real-world answer.

Example:

```text
How many NYC subway stations are there?
```

Players trade contracts based on their estimate.

At the end, the answer is revealed. There is no exact posterior here, so fair-value analytics are replaced by markouts and the final answer.

### 22.5 Prediction Mode

Players trade on binary outcomes.

Example:

```text
Will the next card be red?
```

Settlement:

```text
YES = 100
NO = 0
```

### 22.6 News Cycle

Public information arrives throughout the round, through scheduled News Drops.

Players continuously reprice the asset. This is the best mode for learning to manage stale quotes.

### 22.7 One Insider

Exactly one player receives a highly informative clue.

Everyone knows there is one insider but does not know who.

### 22.8 Teams

Players are secretly or openly paired.

Possible 2v2 or 3v3 formats.

### 22.9 Interview Mode (Solo)

Bots repeatedly call you for markets (§8.2) on a series of recipes. Some bots are informed and some are not. You are scored on:

- P&L
- average gap (tighter is better)
- adverse selection suffered
- how fast you adjust after being picked off

This mirrors the market-making exercises used in trading interviews, with feedback after every round.

### 22.10 Hot Potato

Holding inventory near the end becomes increasingly risky.

Designed for chaotic party sessions.

---

## 23. Tutorial

The tutorial should last under 5 minutes.

### Tutorial Round

User plays against two bots.

Teach only:

1. There is a hidden final value.
2. You received a clue.
3. Buy when something seems cheap.
4. Sell when something seems expensive.
5. Your Market is a price you will buy at and a price you will sell at.
6. Other players may know things you do not.
7. Your position matters at settlement.

Do not explain advanced market-making theory before gameplay.

After the first round, optionally explain, using that round's actual data:

- spread ("your gap earned you +30")
- inventory ("you held 20 units when the price dropped")
- adverse selection ("this bot knew more than you; here is the trade where it showed")
- fair value ("given your clue, the average outcome was 106")

---

## 24. Progression

Progression should not create competitive advantages.

Possible unlocks:

- avatars
- titles
- table themes
- reaction packs
- alternative card designs
- analytics screens
- challenge modes
- recipes

Skill progression displays the ratings from §17.4:

```text
Pricing
Information Reading
Liquidity
Risk Control
Adverse Selection
Bluffing
```

These ratings should initially be descriptive rather than authoritative.

---

## 25. Achievements

Examples:

### First Blood

Complete your first trade.

### Two-Sided

Get both sides of Your Market filled at least 10 times in one game.

### Perfectly Flat

Finish a round with exactly zero inventory.

### Conviction

Hold a position of at least 20 units through settlement and profit.

### Contrarian

Profit while holding the opposite position of every other player.

### Picked Off

Lose more than 100 points on one trade.

### Fast Hands

Reprice Your Market within 1 second of a News Drop.

### Insider Trading

Make five profitable trades within 10 seconds of receiving new information.

### Exit Liquidity

Take the worst trade of the round.

### Price Discovery

Have Your Market's middle price within 1 of the final value at the end of a round.

---

## 26. Technical Architecture

### Frontend

```text
React
TypeScript
Vite
Tailwind CSS
```

Optional:

```text
Framer Motion
```

for game animations.

### Backend

```text
Python
FastAPI
WebSockets
NumPy (posterior computation)
```

### Database

```text
PostgreSQL
```

MVP keeps live match state in memory and persists completed rounds (event logs) at round end.

### Real-Time Communication

WebSockets carry:

- commands (orders, quotes, calls, cancels)
- order book updates
- trades
- private fills and acknowledgements
- timer
- player state
- reactions
- events
- round transitions

---

## 27. Backend Components

```text
backend/
  engine/                 # pure, deterministic, no I/O
    book.py               # price-level order book
    matching.py           # matching, amends, self-trade prevention
    orders.py             # order and quote types, validation
    risk.py               # position limits, price band, rate limits
    accounts.py           # cash, position, fees and rebates
    rfq.py                # Make Me a Market state machine
    room_state.py         # whole-room state + apply(command) -> events

  game/
    recipes.py            # recipe definitions and state sampling
    clues.py              # clue templates, predicates, generation, balancing
    posterior.py          # exact enumeration and Monte Carlo posteriors
    round.py              # phases, timer, events
    objectives.py
    events.py
    settlement.py

  runtime/
    room_actor.py         # one asyncio task per room, sequential command queue
    event_log.py          # append-only log, sequence numbers, replay
    visibility.py         # per-recipient projection of events
    clock.py              # injectable clock

  multiplayer/
    rooms.py
    websocket.py
    protocol.py           # message schemas (pydantic), versioned
    players.py

  bots/
    client.py             # bots use the same protocol as humans
    beliefs.py            # Bayesian state belief + flow updates
    quoting.py            # inventory-skewed quoting
    personalities.py

  analytics/
    fills.py              # per-fill edge and markouts
    attribution.py        # P&L decomposition
    discovery.py          # price discovery series and metrics
    awards.py
    round_summary.py

  sim/
    harness.py            # headless bot-vs-bot rounds at scale
    calibrate.py          # clue strength, objective bonuses, bot difficulty

  tests/
    property/             # Hypothesis invariant tests
    differential/         # engine vs. reference implementation
    replay/               # determinism tests
```

---

## 28. Matching Engine

The engine should behave like a real exchange: exact, deterministic, and fully specified. Every behavior below is documented and tested.

### 28.1 Architecture

- **Pure core.** The engine is a pure state machine: `apply(state, command, timestamp) → (state, events)`. It does no I/O and reads no wall clock or global random number generator. Time and randomness are injected.
- **One sequential actor per room.** Each room runs as a single asyncio task consuming a command queue. All state changes for a room are processed in order, so there are no locks and no races.
- **Sequence numbers.** Every accepted command and every emitted event gets a monotonically increasing sequence number. Arrival order at the room actor defines time priority.
- **Event sourcing.** The append-only event log is the source of truth. Any round can be rebuilt exactly by replaying the log from the seed (§32.3).

### 28.2 Prices and Money

- Prices are **integer ticks** (tick size 1 point in default recipes). There are no floats anywhere in the engine.
- Cash is stored as integer hundredths of a point, so that fees and rebates of 0.25 are exact.
- Orders must be priced within the recipe's **price band** (for example, 80 to 120 in Four Cards). Prices outside the range of possible final values are rejected.

### 28.3 Order Types

| Type | Behavior |
|------|----------|
| Limit | Matches what it can, and the rest rests on the book until filled, cancelled, or round end |
| IOC (immediate-or-cancel) | Matches what it can, then cancels the rest. Used by "Buy from them" / "Sell to them" buttons |
| Post-only | Rejected if it would match on arrival. Guarantees maker status |
| Quote | A linked buy + sell pair belonging to Your Market (§8.1). Each side is post-only by default. The whole quote is replaced atomically |

### 28.4 Priority, Matching, Amends

Matching uses **price-time priority**.

Buy orders:

```text
Highest price first
Then earliest sequence number
```

Sell orders:

```text
Lowest price first
Then earliest sequence number
```

A new buy order matches against the lowest sell offer while:

```text
buy_price >= sell_price
```

A new sell order matches against the highest buy offer while:

```text
sell_price <= buy_price
```

Fills happen at the **resting order's price**. An incoming order may sweep several price levels and partially fill against each.

Amend rules:

- **Reducing size** keeps the order's queue position.
- **Increasing size or changing price** is a cancel-replace and loses queue position.
- **Quote replace** is atomic: both old sides are removed and both new sides inserted in a single command. No event is emitted between them.

### 28.5 Self-Trade Prevention

A player's incoming order must never fill against their own resting order. This matters because every player quotes both sides. Policy: **cancel the resting order** and continue matching the incoming order against the next eligible order. The cancellation is reported to the player with reason `self_trade_prevented`.

### 28.6 Pre-Trade Risk Checks

Every command is validated before it can affect the book:

- **Position limit:** `position + Σ resting buys + incoming buy ≤ limit`, and the same for sells. Worst-case exposure is checked, not just current position.
- **Price band** (§28.2).
- **Size bounds:** minimum 1, maximum per order (default 10), with event modifiers such as Double Size applied.
- **Rate limit:** a token bucket per player (default 10 commands per second, burst of 20).
- **Phase checks:** no trading during the opening phase (only quote setup), halts, or after the round's cutoff time.

Rejections return a specific reason code to the sender only.

### 28.7 Opening Auction, Halts, and Round End

- **Opening auction:** at the end of the opening phase, all opening quotes are crossed at a single price. That price maximizes matched volume. Ties go to the smallest imbalance between buy and sell size at that price, then to the price closest to the recipe mean. Orders at the auction price are filled in random order using the round's random seed. Unfilled quotes rest on the book in that same order.
- **Halt:** new orders, amends that would trade, and calls are rejected. Cancels are allowed. Resting orders stay.
- **Round end:** the cutoff is a server timestamp. Commands sequenced after the cutoff are rejected. All resting orders are cancelled, then settlement runs (§15).

### 28.8 Data Structures and Performance

- The order book is indexed by price tick. The price band is small and bounded, so price levels sit in fixed arrays with FIFO queues at each level. Best-price tracking takes O(1) amortized time.
- An order-ID index makes cancels and amends O(1).
- Targets, measured by a benchmark in CI:
  - engine throughput above 100,000 commands per second on one core, with no I/O
  - p99 server-side processing per command under 2 ms, including fan-out
  - hundreds of concurrent rooms per process

---

## 29. Market Data and Protocol

### 29.1 Channels

- **Public stream:** order book changes (level, side, new size), trades, calls, events, timer. Each message carries the room sequence number.
- **Private stream:** order acknowledgements and rejections (with reason codes), the player's own fills, position, cash, and private clue.

### 29.2 Snapshots, Gaps, Reconnects

- On join or reconnect, the client receives a full **snapshot** (book, recent trades, own state) tagged with a sequence number, then incremental updates.
- The client checks sequence numbers. If it sees a gap, it requests a fresh snapshot.
- Commands carry a **client order ID**, so a retried command after a reconnect is not applied twice.
- A disconnected player's resting orders stay live by default. The host can set them to cancel on disconnect.

### 29.3 Schemas

- All messages are typed and versioned (pydantic on the server, generated TypeScript types on the client).
- The same schemas define the event log format, so live play, replays, and exports share one data model.

---

## 30. Game State

```text
Game
  id
  room_code
  status
  round_number
  settings
  players
  scoreboard

Round
  id
  recipe
  seed                  (server only)
  hidden_state          (server only)
  final_value           (server only until reveal)
  public_information
  phase
  cutoff_time
  event_log
  book
  open_calls

Player
  id
  display_name
  is_bot
  cash                  (integer hundredths)
  position
  position_limit
  quote                 (linked buy/sell order ids)
  score
  private_clue          (visible to self only)
  secret_objective      (visible to self only)
```

The hidden state, final value, and private information must never be sent to unauthorized clients.

---

## 31. Anti-Cheating Requirements

The server must be authoritative.

Never send:

- the hidden state or final settlement value
- other players' private clues
- any fair value or posterior computed by the server
- future events
- hidden objectives

to clients before the reveal.

All order validation, matching, and settlement happen server-side.

Implementation requirement: every outbound message passes through a single **visibility projection** (`runtime/visibility.py`) that decides what each recipient may see. No other code path sends to sockets. This is enforced by tests (§32.2).

---

## 32. Engine Quality and Testing

Correctness is a feature. A quant should be able to read the tests and trust the game.

### 32.1 Invariants (property-based tests with Hypothesis)

Random command sequences are generated and these invariants are checked after every command:

- The book is never crossed (best buy < best sell) after matching completes.
- Price-time priority holds for every fill.
- Units are conserved: Σ positions = 0 across all players.
- Cash is conserved: Σ cash changes + Σ fees − Σ rebates = 0.
- Worst-case exposure never exceeds a player's position limit.
- No player ever trades with themselves.
- Settlement P&L sums to zero across players (before objectives and awards).

### 32.2 Visibility Fuzzing

Simulated rounds are run, and every outbound message to every recipient is inspected. The test fails if any message before the reveal contains another player's clue, the hidden state, the final value, or a server-computed fair value.

### 32.3 Determinism and Replay

Replaying a round's event log from its seed produces a byte-identical final state and identical analytics.

### 32.4 Simulation Harness

A headless runner plays thousands of bot-vs-bot rounds per minute without networking. It is used to:

- calibrate clue strength and check balance across seats (§7.5)
- set objective and award bonus sizes against the P&L distribution (§10)
- validate that bot difficulty levels are ordered (§19.4)
- catch engine regressions under realistic load

### 32.5 Differential Testing

The optimized order book is checked against a simple, obviously correct reference implementation (sorted lists, linear scans) on random command streams. Their outputs must match exactly.

---

## 33. MVP Scope

### Required

- Create private room
- Join by room code
- 2 to 6 players
- Bots fill empty seats (with clues, §19.1)
- Single asset, Four Cards recipe
- Deterministic matching engine with price-time priority, partial fills, cancels, IOC, post-only, self-trade prevention, position limits
- Your Market (two-sided quote)
- Make Me a Market
- Maker rebate / taker fee
- Real-time order book
- Position and cash tracking
- Hidden settlement value
- Private player clues with exact fair values computed server-side
- Secret objectives
- Round timer
- Settlement
- Post-round reveal with personal P&L breakdown (§17.2)
- Match scoreboard
- Rematch
- Solo mode with at least three bot personalities
- Event log and replay of completed rounds

### Nice to Have

- Price discovery chart
- Markouts in Pro view
- Reactions
- Game events
- End-of-game awards
- Basic tutorial
- Sound effects
- Player avatars
- Interview Mode

### Explicitly Not MVP

- User accounts
- Ranked matchmaking
- Public lobbies
- Friends system
- Voice chat
- Multiple assets
- Tournament brackets
- Custom clue editor
- User-generated content
- Mobile native app
- Monetization

---

## 34. MVP User Stories

### Room Creation

As a player, I can create a private game and receive a room code so my friends can join.

### Joining

As a player, I can enter a room code and display name without creating an account.

### Information

As a player, I receive private information that no other player can see.

### Quoting

As a player, I can set a price I will buy at and a price I will sell at, and change it instantly.

### Calling

As a player, I can ask another player to make me a market, and I must answer when someone asks me.

### Trading

As a player, I can buy and sell during the round.

### Feedback

As a player, I immediately see when my order trades.

### Position

As a player, I can see whether I am long or short and how close I am to my limit.

### Social Inference

As a player, I can see what other players are trading and who asked whom for prices.

### Settlement

As a player, I see the hidden value at the end of the round.

### Reveal

As a player, I can see what information other players had after settlement.

### Scoring

As a player, I can understand why I won or lost, including how much I earned from my prices and how much I lost to better-informed players.

### Replay

As a player, I can immediately start the next round.

---

## 35. UX Requirements

### Latency

Trade actions should feel immediate.

Target perceived response:

```text
< 200 ms
```

where network conditions permit. Server-side processing is a small fraction of this (§28.8).

### Click Count

A basic trade should require no more than:

```text
2 interactions
```

Example:

```text
Select size
Click BUY
```

Answering a call should require no more than 3 interactions (adjust price, adjust gap, confirm), with sensible defaults pre-filled from Your Market.

### Information Hierarchy

The player should always be able to identify:

1. Current market
2. Their clue
3. Their position (and limit)
4. Time remaining
5. Best available buy/sell opportunity
6. Their own market

within one glance.

---

## 36. Visual Direction

The game should not look like Bloomberg or a brokerage platform. The Pro interface may be denser, but it uses the same visual language.

Concept mockups live on the Whale UI concepts canvas (the "pit" row and the sprite review). The research behind them is in `docs/design/pit-references.md`.

### 36.1 Setting and tone

An open-outcry pit in the Chicago of the 1970s to 1990s (§7.6): loud, crowded, and papery. The party energy comes from the crowd, the shouting, and the paper, not from glossy UI.

### 36.2 Art style

- **Low-resolution pixel art in the spirit of *Papers, Please*:** a window onto the world above, your desk below, and restraint everywhere. It is a style reference only; nothing is copied from that game.
- **Hand-placed pixels, small palettes:** three tones per material (light, base, shadow), lit from the left. No dithering noise, no outlines on every edge, no faces. Detail beyond this looked worse in testing, not better.

### 36.3 Traders (sprite spec "B3")

- **Base body:** 14×20 pixels, symmetric about its center.
- **Poses:** idle; **buy** (palms in, both arms straight up); **sell** (palms out, arms out wide); **call** (one arm up); **run** (for runners). Buy and sell must read as clearly different shapes at game size.
- **Identity:** jacket color and pattern (solid, plaid, or stripes, as on the real floor) and a 3-letter **badge** on the wearer's left chest. Faces are not used for identity.
- **Dress:** lapels with either a short tapered tie or an open collar, roughly two ties to one open collar across the crowd. Tie colors contrast with the jacket. Trousers are mid-tones so they stay visible on the dark floor.
- **Named traders** keep a fixed look across rounds. Runners wear tan jackets.
- **Perspective:** the far step renders at 3× scale, the middle step at 4×, the front step at 5×, and the pit floor at 6×. Every trader stands on their own step.
- **Art pipeline:** sprites are palette-indexed grids, so a pixel artist can replace them with a sprite sheet (one base body, five poses, recolors) without code changes.

### 36.4 The floor and the desk

- **The pit window:** the far side of the pit, with steps drawn as lit treads over dark risers, packed with traders. Named traders show speech bubbles ("98 BID / 102 OFFER", "BUY 'EM!"). Runners cross the floor (§7.7).
- **Digital, not chalk:** an amber dot-matrix **LED ticker** across the top and an **LED wall board** in the pit (bid, offer, last, time to close). In Standard and Pro views, the board doubles as the price ladder.
- **Private information is paper on your desk:** runner slips, carbon-copy order tickets (white over canary), trading cards in blue ink, desk memos, and rubber stamps for taking the best price.
- **Paper accumulates on the floor** during the round: one scrap per real trade.

### 36.5 Palette and type

- **Colors:** a muted olive-grey pit, a walnut desk, paper whites with canary and pink carbon copies, carbon-blue ink, stamp red, and amber LED. **Buy is blue and sell is orange**, distinguishable by lightness as well as hue.
- **Type:** Pixelify Sans for UI and handwriting, Silkscreen for small form labels, Doto for the LED dot matrix.

### 36.6 The round camera

1. **The bell:** overhead view of the pit, floor clean, your spot ringed.
2. **The dive:** a smooth, eased zoom onto your spot (about 1.5–2 seconds), crossfading into the booth.
3. **The round:** the booth view.
4. **The close:** a smooth pull-back to overhead as the paper settles; the floor shows how wild the round was before any numbers appear. Then the settlement ledger (§16).

### 36.7 Avoid

- dashboards, candlestick charts, and unnecessary financial widgets
- glossy gradients, glows, rounded cards, and emoji
- high-detail procedural shading and faces
- tiny numbers

---

## 37. Sound Design

Sound can substantially improve party-game feel.

Possible sounds:

- order placed
- trade executed
- you got called
- countdown
- event triggered
- objective completed
- settlement reveal
- leaderboard movement

Allow players to mute sounds.

---

## 38. Product Analytics

Track:

- trades per round
- average quote width
- time spent quoting
- calls per round and pass rate
- average inventory
- maximum inventory
- objective completion
- order cancellation rate
- time to first trade
- player retention by round
- rematch rate
- interface choice (Party / Standard / Pro)

For playtesting, especially track:

```text
Rounds completed per session
Rematch rate
Average trades per player
Share of fills that were passive (maker) vs. aggressive (taker)
Percentage of players completing secret objectives
Percentage of rounds with meaningful score changes in final minute
Price discovery score (§17.3) per round
```

---

## 39. Success Metrics

Early product success should be measured primarily through engagement.

### Strong MVP Signals

- Most first-time users complete the tutorial.
- Players average at least 5 meaningful trades per round.
- At least 40% of fills are passive, meaning players actually make markets.
- Friend groups complete at least 3 rounds.
- More than 40% of multiplayer sessions trigger a rematch.
- Players understand why they won or lost.
- Players naturally discuss other players' behavior during games.
- The final reveal regularly creates surprises.
- Markets usually discover the value: median price discovery above 0.5.
- Finance-literate playtesters describe the analytics as correct and useful.

---

## 40. Major Product Risks

### Risk 1: Too Financial

If players feel they need finance knowledge, casual adoption will suffer.

Mitigation:

- use simple language
- guided onboarding
- Party interface as default for friend groups
- visual feedback
- analytics framed in plain language first, with jargon only in Pro

### Risk 2: Too Random

If secret objectives and events dominate outcomes, skilled play becomes meaningless.

Mitigation:

- keep trading P&L as primary scoring mechanism
- calibrate bonuses with the simulation harness (§10)
- limit event frequency
- clearly separate Chaos Mode from competitive modes

### Risk 3: Early Snowballing

A player who gets ahead early could become impossible to catch.

Mitigation:

- short rounds
- multiple-round matches
- position limits bound per-round swings
- varied clue strength
- small party bonuses
- no compounding bankroll across rounds in default mode

### Risk 4: Passive Players

Some players may wait rather than trade.

Mitigation:

- Your Market is always present, so every player is in the market by default
- Make Me a Market forces engagement
- short timers
- objectives
- bots providing liquidity
- visible opportunities

### Risk 5: Excessive Complexity

A full order book may overwhelm first-time users.

Mitigation:

- Party interface hides the book
- Standard and Pro are opt-in
- contextual explanations

### Risk 6: Depth Is Invisible

If the information model and engine are sophisticated but nobody can see it, they do not impress anyone.

Mitigation:

- the reveal surfaces fair values, clue strength, and P&L attribution in plain language
- Pro interface and replays expose the full model
- public engine documentation and test suite

### Risk 7: Bots Are Exploitable or Unbeatable

Scripted bots get solved quickly. Perfect bots feel unfair.

Mitigation:

- bots reason from beliefs, not scripts (§19.2)
- reaction latency floor
- difficulty levels validated by simulation

---

## 41. Development Phases

### Phase 1: Core Engine and Local Prototype

Build:

- recipe sampling and clue generation
- exact posterior computation
- matching engine (§28) with invariant tests (§32.1)
- Your Market and Make Me a Market
- settlement
- simple belief-based bots
- headless simulation harness

Goal:

Prove that one round is fun, and that the engine is correct.

### Phase 2: Real-Time Multiplayer

Build:

- rooms
- room actors and event log
- WebSocket protocol with snapshots and sequence numbers
- visibility projection and fuzz tests
- reconnect support
- multi-player trading

Goal:

Four players can complete a full match reliably.

### Phase 3: The Pit, Party Layer and Reveal

Add:

- the pit interface: booth window, desk, LED ticker and board, pixel traders (§14, §36)
- the round camera: overhead dive at the bell, pull-back over the paper at the close (§36)
- runners and the six-driver recipe (§7.7)
- secret objectives
- reactions
- settlement ledger reveal with P&L breakdown (§16)
- awards
- sound

Goal:

The game becomes entertaining for non-finance friend groups.

### Phase 4: Depth Layer

Add:

- Pro interface
- markouts, attribution, price discovery chart
- replays and export
- full bot personalities and difficulty
- Interview Mode

Goal:

A finance student or quant finds the game worth replaying for its own sake.

### Phase 5: Game Variety

Add:

- events
- additional recipes and modes
- tutorial

### Phase 6: Retention

Add:

- profiles
- stats and skill ratings
- achievements
- cosmetics
- ranked or challenge modes

---

## 42. First Playable Prototype

The first playable version should be intentionally small, but it must test **market making**, not just directional trading.

### Rules

```text
4 players (humans and/or bots)
3-minute round (plus 10-second opening phase)
Four Cards recipe: V = 100 + A + B + C + D, each from -5 to +5 (range 80..120)
Each player privately sees exactly one component
One secret objective per player
Your Market (two-sided quote) for every player
Make Me a Market calls
Position limit ±25, order size 1..10
Maker rebate / taker fee 0.25
Settlement at timer expiration
```

Exact-component clues keep the prototype's math transparent. Each player's fair value is 100 plus their card, with a standard deviation of about 5.5 from the three cards they cannot see.

### Interface

Only show:

```text
Your Clue
Your Objective
Your Market
Best Buy Offer
Best Sell Offer
Players (with Call buttons)
Your Position
Your Cash
Trade Feed
Timer
```

Reveal shows: final value, every clue, every objective, and each player's three-line P&L breakdown (earned from gap / lost to better-informed players / own bets, §17.2).

### Goal

Determine whether players naturally:

- infer information from trades
- quote both sides rather than only taking
- widen their quotes when they feel outmatched, and lean them when holding inventory
- use calls to probe each other
- bluff
- question aggressive traders
- care about inventory
- react emotionally to settlement
- want another round

If those behaviors do not emerge, additional features should not be built until the core loop is fixed.

---

## 43. Example Round

### Hidden State

```text
A = +5   B = +4   C = −1   D = +2
Final Value = 100 + 5 + 4 − 1 + 2 = 110
```

### Player Clues and Fair Values

Each player sees one card. Their fair value is 100 plus that card, with about ±5.5 uncertainty from the three cards they cannot see.

| Player | Clue | Fair value |
|--------|------|-----------|
| Alex | A = +5 | 105 |
| Sam | B = +4 | 104 |
| Maya | C = −1 | 99 |
| Jordan | D = +2 | 102 |

If all four clues were pooled, the fair value would be exactly 110.

### Objectives

| Player | Objective |
|--------|-----------|
| Alex | Collector: finish with at least +15 |
| Sam | Volume Trader: trade at least 50 units |
| Maya | Flat Finish: finish between −3 and +3 |
| Jordan | Big Ticket: one trade of at least 10 units |

### Opening Markets

```text
Alex     102 / 106
Sam      101 / 105
Maya      97 / 101
Jordan    99 / 104
```

Alex's buy at 102 crosses Maya's sell at 101, so the opening auction (§28.7) runs. At 102, Alex buys 5 and Maya sells 5, with no imbalance, so Alex buys 5 from Maya at 102. The opening markets alone already hint that Maya holds the low card.

### Market Action

Sam calls Maya: "Make me a market." Maya, now short, answers 99 / 103 and leans up because of her inventory. Sam buys 5 at 103.

Alex keeps lifting offers up to 106, both because 105 looks like fair value and because Collector rewards a long finish.

Jordan, seeing everyone buy, infers that most cards are positive. Jordan buys 10 at 107 for Big Ticket, then reprices Your Market to 106 / 110.

Maya realizes she is the only seller and that the table is collectively informed. She widens to 104 / 112, buys back at 105–106, and finishes flat.

The market ends around 108 / 110. It has discovered most, but not all, of the pooled answer.

### Settlement

```text
FINAL VALUE: 110
```

### Reveal Highlights

- Alex profits on early purchases below 106 and completes Collector.
- Jordan's 10 at 107 makes +30 and completes Big Ticket. Other players thought it was informed flow. In reality, Jordan had the second-weakest card.
- Maya's breakdown shows she **earned** from her gap but **lost** more to informed buyers (adverse selection). She quoted to a table that knew more than she did, and the reveal shows exactly which trades did it.
- The price discovery chart shows the middle price climbing from 101 toward 110 as each player's information entered through trades.

This is the intended dynamic: the market aggregates private information through trading, players profit from inference and quoting, and the reveal explains everything.

---

## 44. Product North Star

A successful round should cause players to spend as much time thinking about:

> "Why did they just do that?"

as:

> "What is the asset actually worth?"

And a successful product should make a first-year student and a quant both say, for different reasons:

> "That was fair, and I want to play again."

That is the core identity of Whale.

The market is the game board.

Information is the resource.

Quotes are promises; trades are the communication system.

Bluffing, inference, risk-taking, and social misdirection are what make it a party game. Exact math and a real engine are what make it worth mastering.
