# Ban-list — machine-linted AI-slop patterns (v6.0)

These are the statistically overused outputs that read as "AI made this".
All are linted by `scripts/lint-ban-list.sh` (specs, CSS, components) and
checked again in K3 (D11). Bans are about *defaultness*, not morality: a
listed item needs explicit written justification tied to the direction to be
allowed. Every section carries an evidence `source:` into the knowledge
vault — a rule without a note does not exist (knowledge/README.md).

## 1. Type defaults

source: knowledge/design-ops-eval-corpus, knowledge/laws-of-ux

- **Inter, Roboto, Arial, Space Grotesk — banned in FIRST position** of any
  font stack (as fallbacks they are tolerable, but prefer better). These four
  are the modal answer of every model to "pick a font". First position =
  identity; identity must be chosen.
- Lint matches the first font in each `font-family` declaration only — not
  the fallback tail.
- Also flagged: "Inter for body + Inter for display" single-family laziness
  when the direction claims a type voice.

## 2. Color/gradient defaults

source: knowledge/design-ops-eval-corpus

- **Indigo→purple gradients** (`#6366f1→#a855f7` family, `from-indigo-* to-purple-*`,
  any near-neighbor hue pair 230°→280°): the AI gradient. Banned outright.
- "Blue = trust" default SaaS palette without a direction-level reason.
- Gradient on body text. Gradient as a substitute for a color decision.

## 3. Surface defaults

source: knowledge/design-ops-eval-corpus, knowledge/nng

- **Glassmorphism**: `backdrop-filter: blur`, `bg-white/10` + border-white/20
  cards. Banned unless the direction's surface axis explicitly argues it
  (e.g. OS-native product) — and then it must be real material, not decoration.

## 4. Composition defaults

source: knowledge/design-ops-eval-corpus

- **Bento "hero + 3 identical cards"**: hero, then exactly three same-size
  feature cards with icon+title+text. The single most emitted layout of
  2023–2025. Grid variety is fine; THIS pattern is banned.
- Perfectly centered everything on every section.
- Identical section rhythm repeated 5+ times (eyebrow + H2 + 3 cards).

## 5. Imagery/decoration defaults

source: knowledge/hodent-gamers-brain, knowledge/gorshkov-memory

- **Blobs**: organic SVG blob backgrounds, blob image masks, gradient blobs.
- **Icon-per-label**: every feature gets a decorative line icon that adds no
  information. Icons allowed where they carry meaning (nav, actions, status).
- Abstract 3D shapes floating in purple space.
- Fake dashboard screenshots with Lorem charts, fake logo clouds.
- Emoji as UI icons.

## 6. Copy defaults (checked here because they ship with visuals)

source: knowledge/nng, knowledge/paul-elder-critical-thinking

- "Elevate your workflow", "Seamless experience", "Supercharge", "Unlock the
  power of", "🚀" in hero copy. Marketing-slop phrases that models emit when
  the brief is vague — the fix is real copy from K1, not better adjectives.

## 7. Dark patterns (ethics — banned outright, no ALLOW: possible)

source: knowledge/gorshkov-dopamine

Unlike §1–§6 (defaultness), these are manipulative mechanics and are
forbidden in any direction, justified or not:

- **False urgency / false scarcity**: countdown timers that reset, "only 2
  left" that isn't inventory-driven.
- **Hidden price**: costs revealed only at the last step; drip pricing.
- **Confirm-shaming**: decline links worded to shame ("No, I don't want to
  save money").
- **Clicks for clicks**: reward loops with no user value (streak for the
  sake of streak, variable-reward bait on actions that carry no benefit).

Ethical mechanics replace them: competence confirmation ("saved you 3
hours"), transparent rules, support-in-flow instead of pressure
(source: knowledge/gorshkov-dopamine).

## Justification protocol

To use a banned item deliberately: write the justification in the direction
doc ("why THIS product needs glass: it is a macOS companion app"), reference
the axis that demands it, and mark the line `ALLOW:` so the lint invocation
can allowlist it. Unjustified hits = automatic fail.

## Maintenance

The ban-list is a snapshot of 2024–2026 slop. Each project MAY append entries
("what does the category overdo?"), never remove base entries. Review date:
with each pipeline version bump.

## v7.0 — tiered enforcement (spec; wiring in phases 2–4)

The v6.0 sections above stay Tier 1 (blocking) as they are. The v7.0 rule
base adds a tier split so the lint stops shouting about everything:

- **Tier 1 (blocking)** — statistical-default markers: indigo-600/slate-900
  defaults, indigo→purple hero gradients, first-position Inter/Roboto/
  Arial/Space Grotesk, cards inside cards, dark-pattern mechanics.
  source: knowledge/ai-look-catalog
- **Tier 2 (warning)** — generates a report line, never blocks: glassmorphism
  with no content under the glass, gradient text on metrics, bounce/elastic
  on everything, a frame where an offset already groups, hierarchy steps
  below the 1.25× jump, line-length over 75ch.
  source: knowledge/ai-look-catalog, knowledge/text-hierarchy-tiers,
  knowledge/crap-framework, knowledge/modular-type-scale,
  knowledge/spacing-8pt-grid
- **Tier 3 (reference only)** — loaded on demand, never linted: full 21-law
  and 10-heuristic tables, dark-theme rule set.
  source: knowledge/ux-laws-21, knowledge/nielsen-heuristics-checklist,
  knowledge/dark-theme-rules
