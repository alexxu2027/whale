# Design references: the open-outcry pit

Whale's visual theme moves from the fantasy auction house to the **open-outcry trading pit**: the Chicago futures and options floors (CBOT, CME, CBOE) where hundreds of traders stood in tiered rings, shouted bids and offers, and traded with anyone across the pit. Figgie, which Jane Street uses to teach trading, was designed to simulate exactly this.

This file collects facts and sources to design from, so the look comes from the real thing rather than from generic "game UI" defaults. Everything below is sourced; items still to confirm are listed at the end.

## 1. The space

- **The pit is a raised octagon.** Steps go *up* on the outside and *down* on the inside, so it reads like an amphitheater and hundreds of traders can see and hear each other. ([Wikipedia: Chicago Board of Trade](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade))
- **Where you stood meant something.** Different steps and sides traded different contract months, so position in the ring was information. (Widely described; see the documentaries in §6.)
- **The pulpit.** A raised platform at each pit where a reporter watched trading, wrote price changes on paper with timestamps, and a colleague relayed them by teletype to "quotation central". ([Wikipedia: CBOT](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade); [American Archive of Public Broadcasting, "There's Cash in Your Future"](https://americanarchive.org/catalog/cpb-aacip-aed58a9e223))
- **Price boards on the walls.** Early on, banks of **blackboards** with board markers in tan jackets chalking prices that arrived by Morse ticker, covering CBOT's own markets and others (Minneapolis grain, Memphis soybean oil, New York and New Orleans cotton). Later, flip boards and amber LED walls. ([American Archive](https://americanarchive.org/catalog/cpb-aacip-aed58a9e223))
- **The building.** The CBOT Building (Holabird & Root, 1930) is Art Deco, crowned by a 31-foot statue of Ceres with a deliberately featureless face. The exchange's logo is a stylized pit. ([Wikipedia: CBOT](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade))
- **The end.** CBOT eliminated open outcry in agricultural products in 2015. ([Wikipedia: CBOT](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade)) The look is historical, which keeps it distinctive.

## 2. The people: jackets and badges

- **Jackets were white until the 1960s**, then became loud and distinctive so traders and the firms they worked for could be spotted across the pit. Chicago's PECO Inc. made most of them from 1919 on. ([Wikipedia: Trading jacket](https://en.wikipedia.org/wiki/Trading_jacket))
- **Jacket color signalled firm or role.** "A trading coat was one of the most important visual clues about how a person fit in." ([Clifton Linton, "My trading floor coat"](https://cliftonlinton.substack.com/p/my-trading-floor-coat))
- **A jacket could be a whole identity.** Linton wore a one-dollar orange, red, white and blue polyester plaid from a church bazaar; livestock traders admired it and it became how people knew him. (Same source.)
- **Badges.** Each trader wore an identification badge with a short code (often three or four letters); that code also appeared on the paperwork for each trade. ([Wikipedia: Trading jacket](https://en.wikipedia.org/wiki/Trading_jacket))

## 3. The gestures: hand signals

Introduced at the CME in the early 1970s "to rein in the chaos" when "shouting, pushing, and occasional fistfights were all part of the game". ([StoneX](https://futures.stonex.com/blog/trading-floor-hand-signals-the-sign-language-of-futures-trading))

- **Buy:** hands up, **palms facing in** toward the body.
- **Sell:** hands up, **palms facing out**, away from the body.
- **Price** (last digit only): 1–5 fingers straight up; 6–9 the same shapes held **sideways**, parallel to the floor; 0 a closed fist.
- **Quantity:** the number shape touched to the **chin** for 1–9; to the **forehead** for tens; for hundreds, flashed near the forehead and then a closed fist touched to it.
- Signals also carried contract months and option combinations, and rules varied by exchange.

Sources: [StoneX](https://futures.stonex.com/blog/trading-floor-hand-signals-the-sign-language-of-futures-trading), [StoneX hand signals chart](https://futures.stonex.com/futures-options-101/hand-signals), [Wikipedia: Hand signaling (open outcry)](https://en.wikipedia.org/wiki/Hand_signaling_(open_outcry)), [Business Insider: counting down from 10](https://www.businessinsider.in/how-to-count-down-from-10-using-trader-hand-signals/articleshow/28202029.cms).

## 4. The paper

- **Trading cards.** Traders recorded each trade by hand on trading cards, in non-erasable ink, with the time of execution to the nearest minute and the hour written at the top. ([CME advisory on pit recordkeeping](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/CBOT-RA0911-4.html))
- **Order tickets.** Customer orders arriving on the floor were written on order tickets with a timestamp. (Same source.)
- **Carbon copies everywhere.** Order tickets and trading cards came in duplicate or triplicate; a trade checker confirmed side, price and time, kept one copy, and the rest went to clearing.
- **The floor at the close.** At the CME (1985–1992), "one could not walk from the pit to a booth or to an exit without swashbuckling through piles of paper — sometimes more than an ankle deep." ([Benzinga, "No More Paper"](https://benzinga.com/z/8042193))

## 4b. How information reached the pit

- **Booths and phones.** Brokerage booths ringed the pits, with telephones and terminals. Clerks took customer orders by phone. ([Strike: Floor trading](https://www.strike.money/stock-market/floor-trading))
- **Runners carried paper.** The booth wrote an order slip and a runner carried it down to the floor broker in the pit. ([Strike](https://www.strike.money/stock-market/floor-trading); [5paisa: Trading floor](https://www.5paisa.com/finschool/finance-dictionary/trading-floor/))
- **Or it was flashed.** Clerks on the top step of the pit flashed orders with hand signals to the booths and back; if a phone clerk missed the signals, a runner went instead. ([Donald MacKenzie, LRB, "Zero is a clenched fist"](https://www.lrb.co.uk/v29/n21/donald-mackenzie/zero-is-a-clenched-fist))
- **News arrived late and by phone.** On the NYSE floor, a specialist often learned of news through "non-timely messages, telephoned from the offices of other firms to their own floor personnel." ([SEC Historical Society, 1973 memo](https://www.sechistorical.org/collection/papers/1970/1973_0926_NYSENewsT.pdf))
- **The runner was information.** Only brokers on the top step could see a runner arrive; when those brokers suddenly got busy, traders lower down noticed and acted. ([5paisa](https://www.5paisa.com/finschool/finance-dictionary/trading-floor/))

For Whale: a player's clue arrives as a phone message from their desk (a "While You Were Out" slip) or a runner's note. Mid-round public news can arrive the same way, and a visible runner heading to a booth can itself be a tell.

## 5. The sound and the feel

- Hundreds of people shouting prices at once; hand signals existed because voices alone failed.
- Physical: pushing, height on the steps, eye contact, recognising a jacket across the ring.
- Everyone sees every trade. Open outcry was transparent by design. Information leaked through *who* was buying, which is exactly Whale's core question ("why did they just do that?").

## 6. Photography and film to study

Study these for composition, color and density. They are copyrighted: reference only, never copy or embed.

- **Andreas Gursky, *Chicago, Board of Trade* (1997), *II* (1999), *III* (2009).** Seen from high above, traders become an ocean of colored jackets around banks of monitors; *II* uses double exposure for motion. ([Wikipedia: II](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade_II), [Wikipedia: 1997](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade_(photograph)), [Wikipedia: III](https://en.wikipedia.org/wiki/Chicago_Board_of_Trade_III))
- **Stanley Kubrick for *Look*, 1949, "Chicago: City of Contrasts".** Includes floor traders at the CBOT, shot noir and high contrast. Archive at the Library of Congress (Look Magazine Photograph Collection). ([Open Culture](https://www.openculture.com/2014/10/young-stanley-kubricks-noirish-pictures-of-chicago-1949.html), [Flashbak](https://flashbak.com/1949-chicago-stanley-kubrick-23645/))
- **Documentaries.** *Open Outcry* (2001, Jon Else, CME floor in long real-time shots; [TCM](https://tcm.com/tcmdb/title/471983/open-outcry)) and *Floored* (James Allen Smith, a former floor trader, on the end of the pits; [Hedge Fund Law Blog](https://hedgefundlawblog.com/?p=3078)).
- **Archive footage.** National Film Board of Canada stock shot of the CME floor with hand signals (1998). ([NFB](https://archives.nfb.ca/stockshot/56581/))

## 7. Mapping the pit onto Whale

| Pit | Whale |
|---|---|
| The octagonal pit, steps up outside and down inside | The trading screen: players on the rim, the market in the middle |
| Badge code on every jacket and trade card | Each player picks a 3–4 letter badge; it labels their quotes, trades and reveal card |
| Jacket colors identify firms | Each player has a jacket color (and pattern) as their identity |
| Palms in to buy, palms out to sell | Buy and sell icons and buttons; replaces green and red |
| Price and quantity hand shapes | Possible flourish on a player's current quote; not required for play |
| Pulpit reporter writing timestamped prices | The trade feed, written as the pulpit's tape |
| Chalked price boards on the walls | The price ladder, as the board |
| Trading cards in ink, with time and counterparty | Your fills; the reveal shows your stack of cards |
| Paper ankle-deep by the close | Ambient motif: the floor fills with discarded tickets as the round goes on |
| Ticker | Event announcements (open, halt, last 30 seconds) |
| "Everyone sees every trade" | Already true in Whale's feed; lean into it |

The auction-house layer (items, appraisals) needs a decision: keep a light version (the "contract" being traded is still a mystery lot) or replace it with commodity contracts (for example, December wheat). The math doesn't change either way.

## 8. To confirm before using

- **Pit phrasing for bids and offers.** Commonly described as "price *for* size" for a bid ("6 for 10") and "size *at* price" for an offer ("10 at 7"); not yet confirmed in a source.
- **Trading card layout.** Whether buy and sell cards used different colors, and the printed fields. Not found yet; Getty or archive photos of cards would settle it.
- **Badge format.** Typical length and style of badge codes.
- **Pit floor plan.** A real plan or overhead photo of one pit (steps, sides, pulpit placement).
