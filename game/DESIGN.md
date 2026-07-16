# Kindred Atlas — Design Document

## What this is

A creature-collecting, world-trading browser game where you **befriend spirit-creatures
by negotiating with them**, earn money by **haggling in markets**, and unlock content by
gaining **cultural fluency** in London, the USA, Japan and India. Every mechanic doubles
as an incidental real-world lesson.

---

## 1. Legal distinctiveness (why this doesn't look like Palworld or Pokémon)

This is an original work. Beyond that, the design deliberately avoids the specific
elements at issue in creature-collector IP disputes (including the patent claims in
*Nintendo/The Pokémon Company v. Pocketpair*):

| Common genre element | What those games do | What Kindred Atlas does |
|---|---|---|
| Acquiring creatures | Throw a capture item (ball/sphere) at a weakened creature | **No capture at all.** Creatures join voluntarily after a dialogue-based negotiation. Nothing is thrown; there is no capture device, no capture success bar, no weakening-then-catching loop |
| Riding / mounting | Ride creatures for traversal | **No riding or mounting** of any kind |
| Combat | Battle creatures against each other; guns (Palworld) | **No combat whatsoever.** The core verbs are talk, trade, travel |
| Creature designs | Stylized "pocket monster" designs | Original abstract folk-spirit designs (a teacup sprite, a paper-lantern spirit, a monsoon wisp…) drawn as simple geometric canvas art. No design references or resemblances to any existing creature IP |
| Names & terminology | "Pokémon", "Pals", "Poké Ball", "Pal Sphere" | Original vocabulary: "Kindred", "field notes", "fluency". No "Pal-", "Poké-", "-mon" morphemes |
| Creature storage/deployment | Ball-based storage and release | Companions simply walk with you; they are never stored in or released from an object |
| Base-building / factory automation (Palworld) | Pals staff automated bases | No base building. Companions gather trade goods passively — a merchant-caravan trope far older than any of these games |

All art is procedurally drawn geometry, all text is original, and the mechanical heart
of the game (negotiation dialogue + market haggling + cultural etiquette) has no
counterpart in either franchise.

## 2. The Rory Sutherland layer ("psycho-logic")

Sutherland's core insight — *value is psychological, not logical* — **is** the game's economy:

- **Framing / provenance**: goods sell for more with a story attached. The "Provenance
  Story Cards" upgrade makes high price-anchors credible, teaching that narrative is a
  value-multiplier.
- **Costly signaling**: the Tailored Suit works in negotiations *because* it's expensive.
- **Distance creates value**: goods sell 1.6× outside their home country — the player
  discovers arbitrage (and why trade routes exist) by playing, not by being told.
- **Perceived value beats intrinsic value**: fluency raises prices — the same tea is worth
  more when the seller is trusted.
- **"The opposite of a good idea can be another good idea"**: the whole game is Palworld
  inverted — capture becomes conversation — which is itself the Sutherland move.

## 3. Incidental learning

Nothing is taught in a tutorial; everything is taught by consequence, then captured in
the journal ("Field Notes") for later reading:

- **Negotiation (Chris Voss, *Never Split the Difference*)**: mirroring, labeling,
  calibrated How/What questions, the accusation audit, "that's right" vs "you're right",
  the late-night FM DJ voice, never split the difference, strategic silence. Each is the
  *winning move* in a creature negotiation or market haggle.
- **Charisma (Charlie Houpert, Charisma on Command)**: conviction through pace, pause and
  downward tone; warmth + confidence; why hedging words leak doubt.
- **Cultural fluency**: 16 etiquette scenarios (4 per country) covering queueing, rounds
  and understatement (London); tipping, small talk and directness (USA); bowing, meishi
  ritual and no-tipping (Japan); bazaar haggling, chai-first hospitality and the head
  wobble (India). Correct answers pay out; wrong answers still teach.
- **Money sense**: earn → save → invest in upgrades that compound your earning power.

## 4. Intuitive travel

- Press **M** anywhere, or walk into the airport — one click flies you to any country.
- Each destination card shows your fluency, creatures remaining, and whether your cargo
  sells at a premium there, so the *reason* to travel is on the button that does it.

## 5. Tech

Zero-dependency vanilla JS + HTML5 canvas. Open `index.html` in any browser. Progress
saves to localStorage automatically.
