# Whale

## Product Requirements Document

**Working title:** Whale  
**Product type:** Multiplayer market-making party game  
**Primary platforms:** Web, desktop browser first, mobile-friendly responsive layout  
**Status:** MVP planning  
**Audience:** Individuals, friend groups, finance students, trading interview candidates, casual strategy-game players

---

## 1. Product Summary

Whale is a fast, social market-making game where players trade fictional assets, react to incomplete information, bluff, manage inventory, and try to finish each round with the highest score.

The game should feel closer to a party game than a professional trading terminal.

Players do not need finance knowledge. The interface should hide unnecessary market jargon, teach mechanics through play, and make the social dynamics as important as the math.

The core fantasy is:

> "I think I know what this thing is worth. Do you know more than me, or are you bluffing?"

Each round lasts approximately 3 to 6 minutes. Players receive partial information about an asset's hidden final value, then buy and sell with each other while new clues, events, objectives, and behavioral signals emerge.

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
3. Deep enough that skilled players improve over time.
4. Social enough that groups create memorable moments.
5. Fast enough that losing a round does not feel punishing.
6. Structured enough that players naturally learn pricing, probability, bluffing, inventory management, and adverse selection.

The game should create moments like:

- "Why are you buying so aggressively?"
- "There is no way you know the answer."
- "I thought you were informed."
- "You dumped all of that on me."
- "I was just trying to complete my objective."
- "You moved the entire market with one trade."
- "I knew that clue mattered more than you thought."

---

## 3. Product Goals

### Primary Goals

- Make market making entertaining for non-finance players.
- Support both solo and multiplayer play.
- Create strong social interaction between friends.
- Make each round understandable within approximately 60 seconds.
- Generate meaningful strategic decisions every few seconds.
- Encourage bluffing, inference, and reactive play.
- Provide satisfying post-round reveals and score breakdowns.
- Make players want to immediately queue another round.

### Secondary Goals

- Teach market-making intuition indirectly.
- Offer enough depth for finance and trading-interview users.
- Create a portfolio-quality real-time systems project.
- Support future expansion into tournaments, custom games, ranked play, and user-generated round formats.

### Non-Goals for MVP

- Real-money trading
- Cryptocurrency integration
- Brokerage integration
- Real financial securities
- Complex options pricing
- Professional trading analytics
- High-fidelity exchange simulation
- Multiple simultaneous assets
- Persistent economies or pay-to-win mechanics

---

## 4. Target Users

### Persona A: Friend Group

A group of 3 to 8 friends wants a competitive game they can play together for 20 to 45 minutes.

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

### Persona C: Trading / Finance Student

A user likes Figgie, probability games, trading interviews, or market-making concepts.

They care about:

- Two-sided markets
- Expected value
- Information asymmetry
- Inventory management
- Adverse selection
- Post-game analytics
- Skill progression

The product should serve Persona A first while retaining enough depth for Persona C.

---

## 5. Core Design Principles

### 5.1 Fun Before Realism

If realism conflicts with game clarity or pacing, game clarity should usually win.

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
- Final Value
- Clue

Avoid requiring users to understand terms like:

- bid-ask spread
- adverse selection
- mark-to-market
- alpha
- gamma
- microstructure

Advanced terminology can appear in optional learning and analytics screens.

---

## 6. Core Game Loop

Each round follows this structure.

### Phase 1: Setup

The game generates a hidden final value.

Example:

```text
Final Value = 100 + A + B + C
```

Possible components:

```text
A = -10 to +10
B = -20, 0, or +20
C = 0 to +15
```

The actual values are hidden.

### Phase 2: Private Information

Each player receives a different clue.

Examples:

```text
A is positive.
```

```text
B is not zero.
```

```text
C is between 8 and 15.
```

```text
The final value is greater than 105.
```

Some clues should be stronger than others.

Players do not know the quality of other players' clues.

### Phase 3: Opening Market

Players see a broad starting reference range.

Example:

```text
Expected range: 70 to 140
```

The game may provide a neutral starting midpoint for beginner modes.

### Phase 4: Trading

Players can:

- post buy offers
- post sell offers
- accept another player's offer
- cancel open offers
- adjust prices
- change order sizes

All actions happen in real time.

### Phase 5: Mid-Round Events

Depending on mode, the game may introduce:

- public clues
- surprise events
- player objectives
- forced inventory
- fake news
- trading freezes
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

- each player's private clue
- each player's secret objective
- biggest winning trade
- biggest losing trade
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

## 7. Primary Game Mode: Insider

### Description

Every player receives partial information about one hidden final value.

Players trade against each other while trying to infer who knows what.

### Recommended Player Count

- Minimum: 2
- Recommended: 4 to 6
- Maximum MVP target: 8

### Round Length

4 minutes

### Win Condition

Highest total round score.

### Strategic Tension

Players must distinguish between:

- genuine information
- bluffing
- panic
- mistaken valuation
- inventory management
- secret objectives

---

## 8. Secret Objectives

Secret objectives create party-game behavior and prevent every trade from being interpreted as pure information.

Examples:

### Collector

```text
Finish with at least +20 units.
Bonus: +150 points.
```

### Short King

```text
Finish with at least -15 units.
Bonus: +150 points.
```

### Volume Trader

```text
Trade at least 50 units this round.
Bonus: +125 points.
```

### Market Maker

```text
Complete at least 8 trades on both sides of the market.
Bonus: +175 points.
```

### Diamond Hands

```text
Do not trade during the final 30 seconds.
Bonus: +100 points.
```

### Whale

```text
Complete one trade of at least 15 units.
Bonus: +100 points.
```

### Contrarian

```text
End the round opposite the majority position.
Bonus: +125 points.
```

### Flat Finish

```text
Finish between -3 and +3 inventory.
Bonus: +150 points.
```

Objectives should influence behavior without completely overriding the core trading game.

---

## 9. Party Mechanics

### 9.1 Player Reactions

Allow fast reactions such as:

- "Sus"
- "No way"
- "Free money"
- "Panic"
- "Interesting..."
- "You know something"
- "LOL"

These appear briefly near the trade feed.

### 9.2 Market Events

Occasional event cards can alter a round.

Examples:

#### Trading Halt

No trading for 10 seconds.

#### Double Size

Minimum trade size doubles for 20 seconds.

#### Leak

A random player's clue becomes public.

#### Anonymous Mode

Player names disappear from the trade feed for 30 seconds.

#### Whale Alert

One random player must trade at least 10 units within 20 seconds or lose points.

#### Rumor

A public clue appears, but players are warned it has only a 70% probability of being accurate.

#### Position Reveal

One random player's inventory becomes public.

These should be used sparingly to preserve strategy.

---

## 10. Social Information

The trade feed should be a major part of the game.

Example:

```text
Alex bought 8 @ 106 from Sam
Jordan sold 12 @ 104 to Maya
Maya bought 5 @ 108 from Alex
```

Players should learn to interpret behavior.

Optional modes can hide identities:

```text
Player 3 bought 10 @ 112
```

This creates a different information environment.

---

## 11. Beginner UX

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

---

## 12. Trading Interface

### Core Elements

Desktop layout should contain:

#### Center

Order book / available offers

```text
SELL OFFERS

112    5
110    8
108    3

──────────

106    10
104    6
102    5

BUY OFFERS
```

#### Left Panel

Private clue

```text
YOUR CLUE

B > 0
```

Secret objective

```text
SECRET OBJECTIVE

Finish with at least +15 inventory.
```

#### Right Panel

Player status

```text
Cash
Position
Round P&L
Score
```

#### Bottom

Fast trade controls

```text
BUY
SELL

PRICE
SIZE
```

### Simplified Party Mode

Party Mode may replace the full order book with large actionable offers:

```text
BEST BUYER
104 × 8

BEST SELLER
108 × 5

[ SELL TO THEM ]
[ BUY FROM THEM ]
```

Advanced users can toggle the full book.

---

## 13. Scoring System

The scoring system should reward good trading while preserving party-game variability.

### Base P&L

At settlement:

```text
Trading P&L =
Cash Change + Position × Final Value
```

### Round Points

Suggested conversion:

```text
Round Score =
Trading P&L
+ Objective Bonus
+ Achievement Bonuses
```

### Possible Achievement Bonuses

Examples:

```text
Best Bluff
+50

Most Accurate Market
+50

Biggest Comeback
+50

Most Trades
+25

Market Mover
+25
```

These should not overwhelm actual trading performance.

---

## 14. Post-Round Reveal

This is a critical product feature.

### Reveal Sequence

1. Final value animation
2. P&L recalculation
3. Ranking movement
4. Private clues revealed
5. Secret objectives revealed
6. Awards shown
7. Key trades highlighted

### Example

```text
FINAL VALUE
117
```

```text
Alex
+382

Sam
+194

Maya
+44

Jordan
-207
```

Then:

```text
ALEX'S CLUE
Final value > 110

SAM'S CLUE
A is positive

MAYA'S OBJECTIVE
Finish short 15 units
COMPLETED
```

This lets players understand behavior retroactively.

---

## 15. End-of-Game Awards

At the end of a multi-round match, assign fun titles.

Examples:

- The Market Maker
- The Insider
- The Bag Holder
- The Whale
- The Contrarian
- The Panic Seller
- The Diamond Hands
- The Liquidity Goblin
- The Human Bloomberg
- The Exit Liquidity
- Most Suspicious
- Best Bluff
- Biggest Comeback
- Worst Trade of the Night

These awards are primarily social and comedic.

---

## 16. Solo Mode

Solo mode should use bots with visible personalities.

### Bot Types

#### The Conservative

- wide spreads
- small size
- avoids inventory

#### The Whale

- large trades
- aggressive pricing
- moves markets

#### The Insider

- trades selectively
- highly informed
- difficult to identify

#### The Noise Trader

- unpredictable
- often wrong
- creates confusion

#### The Market Maker

- high trade frequency
- tight spreads
- actively manages inventory

#### The Bluffer

- intentionally trades in misleading directions

### Difficulty

Difficulty can modify:

- signal quality
- bot reaction time
- pricing accuracy
- bluff frequency
- inventory discipline

---

## 17. Multiplayer Lobby

### Room Creation

Host selects:

```text
Number of rounds
Round duration
Game mode
Beginner / Advanced interface
Secret objectives on/off
Events on/off
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

## 18. Match Structure

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

for reveals and banter.

---

## 19. Additional Game Modes

These are post-MVP unless otherwise noted.

### 19.1 Chaos Mode

More event cards and unusual objectives.

Designed specifically for friend groups.

### 19.2 Pure Market

No events or objectives.

Only information and trading.

Best for competitive users.

### 19.3 Trivia Market

Settlement value is based on a real-world answer.

Example:

```text
How many NYC subway stations are there?
```

Players trade contracts based on their estimate.

At the end, the answer is revealed.

### 19.4 Prediction Mode

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

### 19.5 News Cycle

Public information arrives throughout the round.

Players continuously reprice the asset.

### 19.6 One Insider

Exactly one player receives a highly informative clue.

Everyone knows there is one insider but does not know who.

### 19.7 Teams

Players are secretly or openly paired.

Possible 2v2 or 3v3 formats.

### 19.8 Hot Potato

Holding inventory near the end becomes increasingly risky.

Designed for chaotic party sessions.

---

## 20. Tutorial

The tutorial should last under 5 minutes.

### Tutorial Round

User plays against two bots.

Teach only:

1. There is a hidden final value.
2. You received a clue.
3. Buy when something seems cheap.
4. Sell when something seems expensive.
5. Other players may know things you do not.
6. Your position matters at settlement.

Do not explain advanced market-making theory before gameplay.

After the first round, optionally explain:

- spread
- inventory
- adverse selection
- fair value

---

## 21. Progression

Progression should not create competitive advantages.

Possible unlocks:

- avatars
- titles
- table themes
- reaction packs
- alternative card designs
- analytics screens
- challenge modes

Skill progression can display:

```text
Pricing
Risk Control
Information Reading
Liquidity
Bluffing
```

These ratings should initially be descriptive rather than authoritative.

---

## 22. Achievements

Examples:

### First Blood

Complete your first trade.

### Market Maker

Trade both sides at least 10 times in one game.

### Perfectly Flat

Finish a round with exactly zero inventory.

### Diamond Hands

Hold a position of at least 20 units through settlement.

### Contrarian

Profit while holding the opposite position of every other player.

### Picked Off

Lose more than 200 points on one trade.

### Insider Trading

Make five profitable trades immediately after receiving new information.

### Exit Liquidity

Take the worst trade of the round.

---

## 23. Technical Architecture

### Frontend

Recommended:

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

Recommended:

```text
Python
FastAPI
WebSockets
```

### Database

Recommended:

```text
PostgreSQL
```

MVP may keep active match state in memory while persisting completed games.

### Real-Time Communication

Use WebSockets for:

- orders
- trades
- price updates
- timer
- player state
- reactions
- events
- round transitions

---

## 24. Backend Components

Suggested modules:

```text
backend/
  game/
    engine.py
    round.py
    settlement.py
    signals.py
    objectives.py
    events.py

  market/
    order_book.py
    matching_engine.py
    orders.py
    positions.py

  multiplayer/
    rooms.py
    websocket.py
    players.py

  bots/
    base.py
    conservative.py
    aggressive.py
    informed.py
    noise.py

  analytics/
    pnl.py
    awards.py
    round_summary.py
```

---

## 25. Matching Engine

The engine should support:

- limit buy orders
- limit sell orders
- marketable orders
- partial fills
- cancellations
- price-time priority

### Priority

Buy orders:

```text
Highest price first
Then earliest timestamp
```

Sell orders:

```text
Lowest price first
Then earliest timestamp
```

### Execution Rule

A new buy order executes against the lowest sell offer if:

```text
buy_price >= sell_price
```

A new sell order executes against the highest buy offer if:

```text
sell_price <= buy_price
```

---

## 26. Game State

Example state model:

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
  hidden_value
  public_information
  time_remaining
  orders
  trades
  events

Player
  id
  display_name
  cash
  inventory
  score
  private_signal
  secret_objective
```

The hidden value and private information must never be sent to unauthorized clients.

---

## 27. Anti-Cheating Requirements

The server must be authoritative.

Never send:

- final settlement value
- other players' private clues
- future events
- hidden objectives

to clients before reveal.

All order validation and settlement must happen server-side.

---

## 28. MVP Scope

### Required

- Create private room
- Join by room code
- 2 to 6 players
- Bots fill empty seats
- Single asset
- Real-time order book
- Buy and sell orders
- Position tracking
- Cash tracking
- Hidden settlement value
- Private player clues
- Secret objectives
- Round timer
- Settlement
- Post-round reveal
- Match scoreboard
- Rematch
- Solo mode

### Nice to Have

- Reactions
- Game events
- End-of-game awards
- Basic tutorial
- Sound effects
- Mobile-responsive layout
- Player avatars

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

## 29. MVP User Stories

### Room Creation

As a player, I can create a private game and receive a room code so my friends can join.

### Joining

As a player, I can enter a room code and display name without creating an account.

### Information

As a player, I receive private information that no other player can see.

### Trading

As a player, I can buy and sell during the round.

### Feedback

As a player, I immediately see when my order trades.

### Position

As a player, I can see whether I am long or short.

### Social Inference

As a player, I can see what other players are trading.

### Settlement

As a player, I see the hidden value at the end of the round.

### Reveal

As a player, I can see what information other players had after settlement.

### Scoring

As a player, I can understand why I won or lost.

### Replay

As a player, I can immediately start the next round.

---

## 30. UX Requirements

### Latency

Trade actions should feel immediate.

Target perceived response:

```text
< 200 ms
```

where network conditions permit.

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

### Information Hierarchy

The player should always be able to identify:

1. Current market
2. Their clue
3. Their position
4. Time remaining
5. Best available buy/sell opportunity

within one glance.

---

## 31. Visual Direction

The game should not look like Bloomberg or a brokerage platform.

Desired aesthetic:

- bold
- playful
- high-contrast
- game-show energy
- clean
- slightly chaotic during events
- readable under time pressure

Possible references in spirit:

- Jackbox
- Balatro
- Polymarket-style probability visualization
- arcade trading floor
- poker table dynamics

Avoid:

- dense professional dashboards
- excessive candlestick charts
- dark institutional terminal styling
- tiny numbers
- unnecessary financial widgets

---

## 32. Sound Design

Sound can substantially improve party-game feel.

Possible sounds:

- order placed
- trade executed
- countdown
- event triggered
- objective completed
- settlement reveal
- leaderboard movement

Allow players to mute sounds.

---

## 33. Analytics

Track:

- trades per round
- average spread
- average inventory
- maximum inventory
- realized P&L
- settlement P&L
- objective completion
- order cancellation rate
- time to first trade
- player retention by round
- rematch rate

For playtesting, especially track:

```text
Rounds completed per session
Rematch rate
Average trades per player
Percentage of players completing secret objectives
Percentage of rounds with meaningful score changes in final minute
```

---

## 34. Success Metrics

Early product success should be measured primarily through engagement.

### Strong MVP Signals

- Most first-time users complete the tutorial.
- Players average at least 5 meaningful trades per round.
- Friend groups complete at least 3 rounds.
- More than 40% of multiplayer sessions trigger a rematch.
- Players understand why they won or lost.
- Players naturally discuss other players' behavior during games.
- The final reveal regularly creates surprises.

---

## 35. Major Product Risks

### Risk 1: Too Financial

If players feel they need finance knowledge, casual adoption will suffer.

Mitigation:

- use simple language
- guided onboarding
- beginner interface
- visual feedback

### Risk 2: Too Random

If secret objectives and events dominate outcomes, skilled play becomes meaningless.

Mitigation:

- keep trading P&L as primary scoring mechanism
- limit event frequency
- clearly separate Chaos Mode from competitive modes

### Risk 3: Early Snowballing

A player who gets ahead early could become impossible to catch.

Mitigation:

- short rounds
- multiple-round matches
- varied clue strength
- small party bonuses
- no compounding bankroll across rounds in default mode

### Risk 4: Passive Players

Some players may wait rather than trade.

Mitigation:

- short timers
- objectives
- bots providing liquidity
- occasional incentives to trade
- visible opportunities

### Risk 5: Excessive Complexity

A full order book may overwhelm first-time users.

Mitigation:

- simplified default market
- advanced order book toggle
- contextual explanations

---

## 36. Development Phases

### Phase 1: Core Local Prototype

Build:

- hidden value generator
- player positions
- buy/sell mechanics
- settlement
- simple bots

Goal:

Prove that one round is fun.

### Phase 2: Real-Time Multiplayer

Build:

- rooms
- WebSockets
- authoritative game state
- reconnect support
- multi-player trading

Goal:

Four players can complete a full match reliably.

### Phase 3: Party Layer

Add:

- secret objectives
- reactions
- awards
- reveal animations
- sound

Goal:

The game becomes entertaining for non-finance friend groups.

### Phase 4: Game Variety

Add:

- events
- additional modes
- bot personalities
- difficulty
- tutorial

### Phase 5: Retention

Add:

- profiles
- stats
- achievements
- cosmetics
- ranked or challenge modes

---

## 37. First Playable Prototype

The first playable version should be intentionally small.

### Rules

```text
4 players
3-minute round
Final value between 80 and 120
One clue per player
One secret objective
Unlimited trading
Settlement at timer expiration
```

### Interface

Only show:

```text
Your Clue
Your Objective
Best Buy Offer
Best Sell Offer
Your Position
Your Cash
Trade Feed
Timer
```

### Goal

Determine whether players naturally:

- infer information from trades
- bluff
- question aggressive traders
- care about inventory
- react emotionally to settlement
- want another round

If those behaviors do not emerge, additional features should not be built until the core loop is fixed.

---

## 38. Example Round

### Hidden State

```text
Final Value = 116
```

### Player Clues

Alex:

```text
Final value > 108
```

Sam:

```text
Final value is less than 120
```

Maya:

```text
A major component is positive.
```

Jordan:

```text
Final value is between 100 and 118
```

### Objectives

Alex:

```text
Finish with at least +15 inventory.
```

Sam:

```text
Trade at least 40 total units.
```

Maya:

```text
Finish between -3 and +3 inventory.
```

Jordan:

```text
Complete one trade larger than 10 units.
```

### Market Action

Opening market:

```text
100 / 105
```

Alex aggressively buys at 105.

Other players infer that Alex may know something.

Sam begins buying too.

Maya thinks the market is overreacting and sells at 112.

Alex continues buying because the trades are both informationally attractive and help complete the secret objective.

The market reaches:

```text
114 / 118
```

Jordan executes a 12-unit purchase at 118 primarily to complete the Whale-style objective.

Other players interpret the purchase as informed flow and push the market to 121.

The round settles at:

```text
116
```

Jordan loses money on the trade but earns the objective bonus.

Maya profits from selling above settlement.

Alex profits from early purchases and completes the inventory objective.

The reveal explains why the apparently informed 118 purchase was actually objective-driven.

This is the intended social dynamic.

---

## 39. Product North Star

A successful round should cause players to spend as much time thinking about:

> "Why did they just do that?"

as:

> "What is the asset actually worth?"

That is the core identity of Whale.

The market is the game board.

Information is the resource.

Trades are the communication system.

Bluffing, inference, risk-taking, and social misdirection are what make it a party game.
