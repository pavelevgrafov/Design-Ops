# Asset production — distinctive visuals (v5.1, CR-08)

Assets carry the direction's imagery axis. Rules are strict because assets
are where slop and legal risk concentrate.

## Default language and raster slots

Typography and CSS/SVG are the DEFAULT visual language. Raster generation
happens ONLY for slots declared in the manifest: hero, product, team, OG.
Anything else = composed (SVG patterns, CSS textures, duotone treatments of
licensed photos). No image generation available → raster slots become
typography-compositional solutions, recorded as `typography_only`
(degradation matrix).

## Sourcing ladder (in order)

1. **Generate** with a prompt derived from the final direction's imagery axis
   + consistency anchors (palette constants, treatment, grain/line/lens recipe).
2. **Compose** programmatically: SVG patterns, CSS-drawn textures, generated
   noise/mesh (NOT blobs — ban-list), duotone treatments of licensed photos.
3. **License** real stock only with a licensing path; record source + license.
   Never hotlink.
4. **Never**: placeholder services (unsplash/picsum/placehold...), hotlinked
   images, watermarked previews, "we'll replace it later" assets.

## The mini-gate (CR-08) [K2.23]

1. Per raster slot: generate **3–4 candidates** from one prompt scaffold
   (prompts + seeds versioned in `asset-manifest.yaml` → `candidates`).
2. Interactive: the orchestrator shows candidates for a ONE-CLICK pick
   (gate template 6). Autonomous: AI pick marked `provisional`, included in
   the return confirmation.
3. Promote the pick to `picked`/`file`; losers stay on disk until delivery
   (regrets happen), then are cleaned.

## Auto-generated assets (no human involvement) [K2.25]

- **Favicon** and **OG image** (1200×630) are generated automatically from
  tokens + the visual-system template. They are part of D14 like any slot.

## AI disclosure (CR-08) [K2.26]

Every AI-generated image in the product gets a disclosure mechanism per the
visual system (badge, caption, or a credits line), `slots[].disclosure: true`.
Basis: EU AI Act transparency duty for deployers in scope, in force from
2026-08-02. At prototype stage a credits line suffices; flag it in the
delivery report.

## Consistency groups

Slots sharing a visual family get ONE consistency anchor: fixed palette subset
+ fixed treatment recipe. Generate the set in one session from one scaffold;
a set that looks like 5 different artists fails at K3 (coherence diagnostic).

## Distinctive budget

quick ≤ 1, standard ≤ 3 distinctive assets. Everything else is supporting and
must be quiet. A page where every asset screams has no signature — it's noise.
Distinctive assets must appear BEYOND the hero (checked in D19).

## Technical bar (all machine-checked in K3, D14)

- Local files only; ≤300 KB each; formats webp/avif/png/svg (mp4 for motion).
- Real `alt` text per slot (not the slot id, not "image").
- Dimensions declared (width/height or aspect-ratio) — this is what prevents
  CLS deterministically.
- srcset for hero images.

## Motion assets

Signature motion (if the direction has one) = one memorable behavior,
implemented in CSS/JS with `prefers-reduced-motion` respected. Motion that
fights reading is a defect, not a flourish.

## Handoff checklist (to K3)

- [ ] every slot: candidates recorded, pick recorded, file local, ≤300KB,
      alt written, dims declared
- [ ] favicon + OG exist
- [ ] consistency anchors documented per group
- [ ] distinctive budget respected; distinctive assets beyond the hero
- [ ] AI-generated slots have `disclosure: true` and the mechanism exists
- [ ] manifest `oversize_files` empty
