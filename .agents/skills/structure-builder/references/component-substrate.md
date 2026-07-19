# Component Substrate — neutral shadcn/ui (K1, v5.1)

How to make shadcn/ui a legitimate *neutral* skeleton substrate.

## Setup

1. Scaffold via the webapp-building toolchain (never raw `npx shadcn` init
   outside it).
2. Install only the primitives the key screens actually use — typical set:
   `button input textarea select checkbox radio switch tabs accordion dialog
   dropdown-menu popover tooltip card table badge avatar skeleton alert
   form navigation-menu sheet separator`.
3. Neutralize `globals.css` tokens to the gray-graphite ramp:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 0 0% 7%;
  --muted: 0 0% 94%;
  --muted-foreground: 0 0% 32%;
  --border: 0 0% 87%;
  --input: 0 0% 87%;
  --ring: 0 0% 45%;
  --primary: 215 12% 42%;        /* neutral blue-gray: affordance only */
  --primary-foreground: 0 0% 100%;
  --secondary: 0 0% 94%;
  --secondary-foreground: 0 0% 12%;
  --accent: 0 0% 94%;
  --accent-foreground: 0 0% 12%;
  --destructive: 0 0% 35%;       /* still gray — semantics via icon+text */
  --radius: 0.375rem;            /* shadcn default, untouched */
}
```

4. System font stack only: `font-sans` maps to
   `ui-sans-serif, system-ui, sans-serif` — no webfonts in K1.
5. Do NOT tune radius, shadows, spacing scale, or add dark mode in K1.
   All of that is K2 token work.

## Usage rules

- Compose screens from primitives; no bespoke styled components. If a needed
  block has no primitive, build it from unstyled semantic HTML + Tailwind
  layout utilities (flex/grid/spacing) — no color, no decoration.
- The `skeleton` component = loading states; a literal gray box +
  `data-asset-slot="..."` = future imagery.
- Icons in K1: allowed only where they carry meaning without text (close,
  menu); no icon-per-label decoration (also a K2 ban-list item).
- Keep all interactive primitives functional — Gate 1 reviewers click things.
  Dead controls read as broken structure, not neutral design.

## Why not hand-rolled neutral CSS for apps

Accessible keyboard/focus/ARIA behavior is the load-bearing part of a
skeleton review; hand-rolling it costs more than it saves, and K2 re-skins
shadcn via CSS variables without touching components.

## Exit checklist (feeds skeleton-manifest)

- [ ] tokens neutralized as above, no other color values anywhere
- [ ] system font stack only
- [ ] every required_state implemented via state/mocks
- [ ] marker `not_approved_visual_design` rendered on every screen
- [ ] no custom CSS beyond layout utilities
