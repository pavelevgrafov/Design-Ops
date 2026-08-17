# Decisions

Load-bearing choices for this toolkit: what was chosen, why, and what would reverse it.
One entry per decision, newest first. A decision is only listed here once it constrains
future work — routine implementation notes belong in the code.

---

## 2026-08-17 — Design intent is declared at the source, never extracted from the render

**Chosen.** The semantic layer this toolkit checks (`D.39`, `check-semantic-layer.py`) is
something a design system must *declare*: a layer of names over a layer of values, where
`color.accent → palette.amber.700` is written down before anything renders. The toolkit
will not gain a mode that reconstructs that layer by reading a finished page.

**Rejected.** Extraction from a rendered site — the approach taken by tools such as
[design-oracle](https://github.com/jomvick/design-oracle), which opens a page with
Playwright and emits "the complete design system" as tokens, a Tailwind config and a
`DESIGN.md`.

**Why.** Intent is not present in rendered CSS. That `#8a5a1f` means *accent* and that
`1.5rem` is *one step of the scale* is nowhere in the output — only in the decision that
produced it. Any extractor therefore does one of two things:

- **borrows** the intent from class names (`hero`, `pricing`, `faq`), which works only
  when the source site already had a semantic layer and exposed it in markup — and
  collapses on utility classes or hashed CSS modules, i.e. on most current sites;
- **guesses** it. Read directly from `backend/analyzer/` in the repo above: "UX patterns"
  is substring search over raw HTML (`"dark" in html` yields *Dark Mode, 60% confidence*),
  the confidence figures are hand-written constants rather than measurements, and the
  "Design DNA" style classifier sums fixed weights — a bluish primary colour scores +2
  toward "Modern SaaS".

Both failure modes produce a document that looks like a design system and does not
constrain anything. This is the sibling of the defect class named in `silent-rot`
("the check exists, but it is not the one that runs"): here, **the extraction exists, but
what it extracts is not the thing**.

**Consequence.** The toolkit's direction stays reversed relative to extraction: it takes a
declared system and verifies that the rendered page conforms to it. Nothing is guessed —
two records are compared and both are known. That is why a pass rate over these checks is
a meaningful number: it measures conformance to something declared, not agreement with
something inferred.

**What would reverse this.** A method that recovers intent from a render without borrowing
or guessing it — for example, a hybrid where the machine extracts only what is genuinely
in the CSS (unique colours by frequency, the spacing scale, type sizes) and a human names
10–15 of those values once, after which the machine propagates the names. That confines
the uncertainty to one short, visible step instead of hiding it behind a confidence
percentage. Worth building only if reading a reference site becomes an actual requirement.

Full analysis: `Research/reports/2026-08-17-design-oracle.md`.
