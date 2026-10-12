# Tushare Data Platform Design System

## Product intent

- Audience: data engineers, quantitative developers, and platform operators.
- Primary jobs: browse API metadata, configure collection requests, submit background sync jobs, and inspect execution history.
- Voice: technical, restrained, precise, and operational.
- Visual genre: modern-minimal data platform.
- Macrostructure: Resource Index + Reference Canvas — a searchable catalog leads into a focused API specification surface.
- Navigation: N3 side rail on desktop, drawer navigation on compact screens.
- Theme: Neutral Graphite — warm-neutral surfaces, graphite text, and one restrained green interaction accent.
- Theme modes: Light, Dark, and System share semantic tokens; dark surfaces stay green-tinted graphite rather than pure black or neon.
- Enrichment: none. The product UI itself carries the visual identity.

## Composition

The desktop layout uses a compact 220px side rail and a flexible content canvas. The 52px header carries location and global tools without behaving like enterprise navigation. API discovery is a dedicated, searchable resource index; selecting an API opens a full-width reference canvas instead of preserving a permanent second sidebar. Detail sections use rules, spacing, and typography rather than stacked cards.

At widths below 960px, the rail becomes a drawer. Panels stack into a single column, controls expand to the available width, and tables remain horizontally scrollable rather than compressing data into unreadable cells.

## Typography

- Display and page titles: Segoe UI Variable Display, 600.
- Interface and body copy: Segoe UI Variable Text, 400–600.
- API names, identifiers, counts, and machine values: Cascadia Code / platform monospace, 400–600.
- Page title: 28–36px / 1.15 depending on available width.
- Section title: 14–16px / 1.4.
- Body: 13–14px / 1.6.
- Supporting text: 11–13px / 1.5.
- Labels remain sentence case; uppercase is reserved for short status codes only.

## Color

All implementation colors are semantic OKLCH tokens in `frontend/tokens.css`.

- Paper layers create hierarchy through small lightness changes, not shadows.
- Graphite provides the primary dark surface and strongest text.
- Low-saturation green is reserved for primary actions, active navigation, success, links, and focus.
- Success, warning, and error colors communicate state only.
- Borders are quiet but persistent so tables and forms remain legible.

## Spacing and shape

- Base spacing unit: 4px.
- Common control spacing: 8px, 12px, 16px, 24px, 32px.
- Form controls and primary actions use a 44px target; compact navigation controls remain visually dense while preserving clear focus states.
- Controls use 6px radius; larger panels use 10px radius.
- Surfaces are separated primarily by rules and spacing. Nested cards are avoided.

## Motion

- Motion exists only for feedback, state indication, and spatial continuity.
- Button press: 120ms transform.
- Hover and selected-state color changes: 160–180ms.
- Page content entrance: one 240ms opacity and 4px translation.
- Drawers and dialogs use the component library's focus-safe transitions.
- `prefers-reduced-motion: reduce` disables nonessential motion.
- Focus feedback is immediate and never animated.

## Interaction rules

- One primary action per local context.
- Sync actions expose loading and disable repeated submission.
- Destructive or risky modes are explicitly labelled; APPEND warns that it is not idempotent.
- Keyboard focus uses a visible two-layer ring.
- Empty, loading, error, disabled, hover, active, and selected states must remain distinguishable.
- Data tables do not animate rows; operational data should remain spatially stable.

## Exports

### CSS tokens

Canonical implementation: `frontend/tokens.css`.

### Tailwind theme mapping

```css
@theme {
  --color-paper: var(--color-paper);
  --color-ink: var(--color-ink);
  --color-accent: var(--color-accent);
  --font-sans: var(--font-body);
  --font-display: var(--font-display);
  --font-mono: var(--font-mono);
  --radius-control: var(--radius-control);
  --radius-panel: var(--radius-panel);
}
```

### DTCG token shape

```json
{
  "color": {
    "paper": { "$type": "color", "$value": "oklch(0.995 0 0)" },
    "ink": { "$type": "color", "$value": "oklch(0.205 0.008 150)" },
    "accent": { "$type": "color", "$value": "oklch(0.49 0.12 151)" }
  },
  "dimension": {
    "space-4": { "$type": "dimension", "$value": "16px" },
    "control-height": { "$type": "dimension", "$value": "44px" },
    "rail-width": { "$type": "dimension", "$value": "220px" }
  }
}
```

### shadcn-compatible variables

```css
:root {
  --background: var(--color-paper);
  --foreground: var(--color-ink);
  --card: var(--color-paper-raised);
  --card-foreground: var(--color-ink);
  --primary: var(--color-accent);
  --primary-foreground: var(--color-accent-ink);
  --border: var(--color-rule);
  --ring: var(--color-focus);
  --radius: var(--radius-control);
}
```
