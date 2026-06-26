# GRU953 Markdown — design-system notes

Foundation for the pywebview HTML/CSS/JS desktop app. Palette is **GRU953 Open
Spectrum**. All colour tokens live in `web/css/themes.css`; `styles.css` consumes
them only through `var(--x)`. This document is the variable contract plus a
component restyle spec for `styles.css` (which the orchestrator edits, not this task).

British English throughout. Sentence case for headings and buttons. Brand token is
always `GRU953` (never translated, even inside Bangla); GitHub handle `GRU-953`.

---

## A. Variable contract

Switching axes:

- `[data-mode="light"|"dark"]` switches neutrals + status colours.
- `[data-palette="indigo"|"violet"|"slate"]` switches accent (primary) colours.
  The three keys are historical and map to brand families:
  `indigo` = **GRU953 Teal** (default), `violet` = **GRU953 Indigo**,
  `slate` = **GRU953 Amber**. Keys are unchanged so stored user settings keep working.

### A.1 Mode-independent tokens (`:root`)

| Variable | Value | Purpose |
|---|---|---|
| `--space-1` | `4px` | half-step (tight gaps, icon padding) |
| `--space-2` | `8px` | base grid unit |
| `--space-3` | `16px` | default component padding / gap |
| `--space-4` | `24px` | section padding |
| `--space-5` | `32px` | view padding |
| `--space-6` | `48px` | large blocks / empty-state padding |
| `--space-7` | `64px` | hero / onboarding spacing |
| `--radius-sm` | `4px` | pills inner, small chips, swatches |
| `--radius-md` | `8px` | buttons, inputs, file rows, nav buttons |
| `--radius-lg` | `16px` | panels, cards, large fields |
| `--radius-xl` | `24px` | onboarding card, modal |
| `--font-ui` | `"DM Sans", "Segoe UI", system-ui, sans-serif` | UI text |
| `--font-bn` | `"Noto Sans Bengali", "DM Sans", sans-serif` | Bangla text/preview |
| `--font-mono` | `"JetBrains Mono", "Cascadia Code", "Consolas", monospace` | editor/code |
| `--sidebar-w` | `76px` | left nav rail width |
| `--ease` | `cubic-bezier(0.4,0,0.2,1)` | standard easing |
| `--dur-micro` | `150ms` | hover / state change |
| `--dur-std` | `250ms` | enter/leave, toasts |
| `--dur-entrance` | `400ms` | view / overlay entrance |
| `--focus-ring` | `#3A4A9E` (root default; re-set per mode) | focus-visible ring colour |

`--dur-micro/std/entrance` collapse to `0ms` under
`@media (prefers-reduced-motion: reduce)`.

### A.2 Mode-dependent tokens

| Variable | Light | Dark | Notes |
|---|---|---|---|
| `--bg` | `#F7F8F7` | `#10211D` | app background; dark never pure black |
| `--surface` | `#FFFFFF` | `#18302A` | panels, bars, cards |
| `--surface-2` | `#EEF1EF` | `#20403A` | hover, segmented track, code bg |
| `--surface-3` | `#DFE4E1` | `#2A5048` | nested chips, progress track, toast bg |
| `--border` | `#DFE4E1` | `#2E423B` | hairline dividers (elevation lvl 1) |
| `--border-2` | `#C6CEC9` | `#3A4F47` | stronger borders, dashed dropzone |
| `--text` | `#16201C` | `#E8EEEB` | body — 16.7:1 / 11.95:1 on surface |
| `--text-muted` | `#54605B` | `#9DA9A3` | secondary — 6.56:1 / 5.78:1 |
| `--text-faint` | `#7E8A84` | `#7E8A84` | hints/large only — >=3.37:1 / >=3:1 |
| `--shadow` | `0 8px 30px rgba(22,32,28,.12)` | `0 8px 30px rgba(0,0,0,.45)` | reserve for overlays only |
| `--overlay` | `rgba(22,32,28,.35)` | `rgba(6,15,12,.62)` | modal scrim |
| `--focus-ring` | `#3A4A9E` | `#97A3E0` | 7.43:1 / 6.86:1 on bg |
| `--ok` | `#18794D` | `#6FD0BC` | success text/icon — 5.41:1 / 7.64:1 |
| `--ok-bg` | `rgba(24,121,77,.10)` | `rgba(111,208,188,.14)` | success fill |
| `--err` | `#C8453B` | `#F3A48E` | error text/icon — 4.81:1 / 7.03:1 |
| `--err-bg` | `rgba(200,69,59,.09)` | `rgba(243,164,142,.14)` | error fill |
| `--warn` | `#9C6B12` | `#F4B53C` | warning text/icon — 4.64:1 / 7.71:1 |
| `--warn-bg` | `rgba(156,107,18,.10)` | `rgba(244,181,60,.14)` | warning fill |

### A.3 Palette (accent) tokens

| Variable | Teal `indigo` L / D | Indigo `violet` L / D | Amber `slate` L / D |
|---|---|---|---|
| `--primary` | `#0A6E5C` / `#14A88A` | `#3A4A9E` / `#97A3E0` | `#9C6B12` / `#F4B53C` |
| `--primary-hover` | `#074D40` / `#6FD0BC` | `#26336E` / `#C7CEEE` | `#7A5210` / `#E0990F` |
| `--accent` | `#3A4A9E` / `#97A3E0` | `#0A6E5C` / `#6FD0BC` | `#0A6E5C` / `#14A88A` |
| `--on-primary` | `#FFFFFF` / `#10211D` | `#FFFFFF` / `#10211D` | `#FFFFFF` / `#16201C` |
| `--primary-soft` | teal 12% / 18% | indigo 12% / 18% | amber 13% / 16% |

`--primary` carries text/icons on `--surface` at >=4.64:1 in every palette+mode.
`--on-primary` on a `--primary` fill is >=4.64:1 in every combination.

**Total distinct variable names defined: 42.**

---

## B. Component restyle spec for `styles.css`

Rules applied everywhere:

- **Spacing**: all padding/gap/margin from the `--space-*` scale (8px grid, 4px
  half-step). No arbitrary px for layout spacing.
- **Radii**: `--radius-sm` chips/pills, `--radius-md` controls/rows,
  `--radius-lg` panels/fields, `--radius-xl` modals.
- **Borders over shadows**: separate surfaces with `1px solid var(--border)`;
  `--border-2` for emphasis. Max 3 elevation levels — (1) hairline border,
  (2) border + `--surface-2/3` step, (3) `--shadow` reserved for overlays
  (toasts, onboarding, dropdowns). Never stack shadows on inline UI.
- **Focus**: every interactive element gets
  `:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }`
  (>=3:1 against its background). Never remove the outline without a replacement.
- **Touch targets**: every clickable control >=44x44px (pad up small icons).
- **Type**: body and inputs >=16px; micro-labels >=12px and only on `--text` or
  `--text-muted` (never `--text-faint` for essential text).
- **Motion**: transitions use `var(--ease)` with `--dur-micro` for hover/state and
  `--dur-std` for enter/leave. Wrap keyframe-driven entrances in
  `@media (prefers-reduced-motion: no-preference)`; provide a no-motion fallback.
- **States**: interactive controls define all 8 — rest, hover, active/pressed,
  focus-visible, disabled, loading/busy, selected/checked, error.

### Sidebar / nav rail
- Width `--sidebar-w`; `--surface` with right `1px solid var(--border)`.
- Brand mark 44x44 (`--radius-md`), `--primary` fill, `--on-primary` glyph.
- `.nav-btn` 48x48 (meets 44px), `--radius-md`, icon + 12px label.
  rest `--text-muted`; hover `--surface-2` + `--text`; active (current view)
  `--primary-soft` fill + `--primary` text plus a 3px `--primary` inset edge as a
  non-colour-only cue; focus-visible ring; disabled 45% + no pointer.

### Topbar
- 56px tall, `--surface`, bottom `1px solid var(--border)`, padding
  `0 var(--space-4)`, `--space-3` gaps. Title 17px/600 `--text`;
  subtitle 13px `--text-muted`. Right cluster pushed with `margin-left:auto`.
- Update banner: `--primary-soft` fill, `--primary` text, bottom `1px` `--primary`;
  link underlined `--primary`; dismiss is a >=44px ghost hit-area.

### Buttons (`.btn`, `.primary`, `.ghost`, `.icon`) — all 8 states, >=44px
- Base: `--font-ui` >=14px/500, padding `12px var(--space-3)` (min-height 44px),
  `--radius-md`, `1px solid var(--border-2)`, `--surface`, `--text`.
- hover `--surface-2`; active translateY/scale micro-press (`--dur-micro`);
  focus-visible ring; disabled 45% opacity + `not-allowed`;
  loading shows a spinner, keeps width, sets `aria-busy`;
  selected (toggle) uses `--primary-soft` + `--primary`; error variant `--err`.
- `.primary`: `--primary` fill + `--on-primary`; hover `--primary-hover`.
- `.ghost`: transparent → `--surface-2` on hover.
- `.icon`: square >=44x44, centre glyph.

### Segmented control (`.seg`)
- Track `--surface-2`, `--radius-md`, 4px inset padding. Each `button` >=44px tall,
  `--radius-sm`. Selected = `--primary` + `--on-primary`; rest `--text-muted`;
  hover `--text`; focus-visible ring on the segment; `role="radiogroup"` semantics.

### Panels / cards (`.panel`, `.palette-card`)
- `--surface`, `1px solid var(--border)`, `--radius-lg`. Head: padding
  `var(--space-3)`, bottom `1px var(--border)`, 14px/600 title, count chip in
  `--surface-2` `--radius-sm`. Body padding `var(--space-3)`, scrolls internally.
  Foot: top border, `--space-2` gaps, buttons stretch equally.

### Dropzone (`.dropzone`)
- `2px dashed var(--border-2)`, `--radius-lg`, padding `var(--space-4)`,
  `--text-muted`. hover/drag-over: border + text `--primary`, fill `--primary-soft`.
  Keyboard-openable (button semantics) with focus-visible ring. Icon decorative.

### File rows (progress + size)
- Row: flex, `--space-2` gap, padding `var(--space-2)`, `--radius-md`,
  transparent border. hover `--surface-2`; selected `--primary-soft` +
  `--primary` border; dragging 50% opacity. Icon tile 30x30 `--radius-sm`
  `--surface-3`. Name 14px `--text` (ellipsis); meta line shows size + steps in
  `--text-muted`. Remove `.fx` button is a >=44px hit-area, error-tinted on hover.
- Status glyph by class: `pending`→`--text-muted`, `doing`→`--primary`,
  `done`→`--ok`, `error`→`--err`, `warn`→`--warn` (icon + text, not colour alone).
- Progress: track 4px `--surface-3` `--radius-sm`; bar `--primary`, width
  transitions over `--dur-std`. Set `role="progressbar"` + aria-valuenow.

### Output / editor / preview
- Output tabs are a segmented control. Editor: `--font-mono` >=14px/1.65,
  `--bg`, no border, focus-visible ring on the textarea. Preview: `--font-ui`
  (Bangla preview `--font-bn`), 1.7 line-height; `code`/`pre` on `--surface-2`
  `--radius-md`; tables hairline `--border`; blockquote 3px `--primary` rule;
  links `--primary` (underline on hover/focus).

### Fields (`.field`, `.label`)
- `--surface`, `1px solid var(--border)`, `--radius-lg`, padding `var(--space-3)`,
  >=16px text. focus: `--primary` border + focus-visible ring; error: `--err`
  border + `--err-bg` tint + message in `--err`; disabled 45% on `--surface-2`.
  Label 12px/500 `--text-muted` above the control.

### Checkboxes (`.checkbox`)
- 18x18 box, `--radius-sm`, `accent-color: var(--primary)`; label `--text-muted`.
  Whole label is the >=44px click target. Checked = `--primary` fill + tick;
  focus-visible ring on the box; indeterminate uses a dash, not colour alone.

### Detect pill (`.detect-pill`)
- `--radius-sm`, padding `4px var(--space-3)`, `--surface-2` + `--text-muted`
  by default. `.bijoy` → `--ok-bg` + `--ok`; `.unicode_bn` → `--warn-bg` +
  `--warn`. Always pair an icon/text label with the colour.

### History (`.hist-item`, `.badge`)
- Card: `--surface`, `1px var(--border)`, `--radius-md`, `var(--space-3)` padding,
  `--space-2` bottom gap. Status tile uses `--ok-bg`/`--ok` or `--err-bg`/`--err`.
  Name 14px `--text`; sub-line `--text-muted`. `.badge` chip `--surface-2`
  `--radius-sm`. Whole row focusable if clickable.

### Settings + palette cards
- Settings rows split by `1px var(--border)`, `var(--space-4)` vertical padding,
  max-width ~640px. Palette grid 3 columns, `--space-3` gap. `.palette-card`:
  `2px solid var(--border)`, `--radius-lg`, `var(--space-3)` padding; hover
  `--border-2`; selected `--primary` border + a tick/label (not colour alone);
  focus-visible ring; swatches 26x26 `--radius-sm`. Cards are radio semantics.

### Toasts (`.toast`)
- Stack bottom-centre, `z-index` above content. `--surface-3`,
  `1px var(--border-2)`, `--radius-md`, `--shadow` (overlay tier), padding
  `12px var(--space-3)`, >=13px. Icon tinted `--ok`/`--err`/`--warn`. Entrance
  `rise` over `--dur-std`; respect reduced-motion. Auto-dismiss but pause on
  hover/focus; `role="status"` (polite) or `alert` for errors.

### Onboarding (`.onboard-*`)
- Backdrop `--overlay` + blur, entrance over `--dur-entrance`. Card `--surface`,
  `1px var(--border-2)`, `--radius-xl`, padding `var(--space-6)`, `--shadow`.
  Logo tile 52x52 `--radius-lg` `--primary`/`--on-primary`. Steps use
  `--primary-soft`/`--primary` icon tiles. Primary CTA full-width >=44px.
  Trap focus; Esc closes; honour reduced-motion.

### Language toggle (NEW control)
- A two-option segmented control (English | বাংলা) reusing `.seg` styling so it
  inherits all states. >=44px segments, `--radius-md` track on `--surface-2`,
  selected `--primary` + `--on-primary`. `role="radiogroup"`, each option a
  `role="radio"` with `aria-checked`; both label strings always rendered (never
  flag-only). The selected option also carries an explicit visible label change so
  the cue is not colour-only. Switching swaps the active app font between
  `--font-ui` and `--font-bn`. Sits in the topbar right cluster.

### The 4 designed states
- **Empty** (`.empty`): centred, `var(--space-6)` padding, decorative icon at
  ~0.6 opacity in `--text-faint`, headline `--text`, one-line guidance
  `--text-muted`, and a primary action where relevant. Never a bare blank panel.
- **Loading**: skeleton blocks on `--surface-2` with a shimmer gated behind
  `prefers-reduced-motion: no-preference` (static tint otherwise); or an inline
  spinner in `--primary` with `aria-busy="true"`. Preserve layout size to avoid
  shift.
- **Error**: `--err-bg` panel, `1px solid var(--err)`, `--err` heading + icon,
  plain-English cause in `--text`, and a retry button (`.btn` error/primary).
  `role="alert"`. Colour always paired with icon + text.
- **Offline**: a banner styled like the update banner but using `--warn-bg` /
  `--warn`, icon + "You are offline" text, and a note that local conversion still
  works. Persistent (not auto-dismissed) until connectivity returns;
  `role="status"`.

---

## C. Accessibility verification (WCAG 2.2 AA)

All text/background pairs were computed (sRGB relative luminance). Representative
ratios — every essential-text pair clears 4.5:1; large/non-essential clears 3:1:

- Light: text/surface 16.7, muted/surface 6.56, primary-text/surface 6.18,
  ok 5.41, err 4.81, warn 4.64, focus-ring/bg 7.43, faint/surface 3.59 (hint/large).
- Dark: text/surface 11.95, muted/surface 5.78, primary(teal500)/surface 4.68,
  ok 7.64, err 7.03, warn 7.71, focus-ring/bg 6.86, faint/surface 3.07 (hint/large).
- `--on-primary` on each palette's `--primary` fill: >=4.64:1 in all 6 combos.

`--text-faint` is reserved for decorative hints, large glyphs and disabled-state
captions — never for essential body copy — so its ~3:1 contrast is compliant for
its uses. Focus rings use brand Indigo, which exceeds the 3:1 non-text minimum
against every surface in both modes.
