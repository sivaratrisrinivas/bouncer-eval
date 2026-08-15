---
name: Bouncer — multi-screen results showcase
description: A light cherry-blossom showcase that sells the Bouncer scoped-autonomy eval to a technical audience: what it is, the problem, why it matters, and the results — one idea per screen.
colors:
  bg: "#fdf4f6"
  surface: "#ffffff"
  surface-soft: "#fbeef1"
  line: "#f2d9df"
  ink: "#3c2a30"
  ink-dim: "#6d555d"
  ink-faint: "#7a6068"
  accent: "#a54160"
  accent-soft: "#f9e3ea"
  good: "#1f6f46"
  good-soft: "#e5f3ec"
  caution: "#b0631c"
  caution-soft: "#fbf1e0"
  bad: "#af3943"
  bad-soft: "#fbe7e9"
typography:
  display:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "clamp(2.4rem, 7vw, 3.2rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Archivo, system-ui, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "'Space Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    letterSpacing: "0.06em"
    textTransform: "uppercase"
rounded:
  sm: "0px"
  md: "14px"
  pill: "999px"
spacing:
  micro: "2px"
  xs: "0.35rem"
  sm: "0.7rem"
  md: "1rem"
  lg: "1.4rem"
  xl: "2rem"
shadows:
  card: "0 1px 2px rgba(60,42,48,.06), 0 8px 20px rgba(60,42,48,.07)"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0.7rem 1.3rem"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dim}"
    border: "1px solid {colors.line}"
    rounded: "{rounded.pill}"
    padding: "0.7rem 1.3rem"
  card:
    backgroundColor: "{colors.surface}"
    border: "1px solid {colors.line}"
    rounded: "{rounded.md}"
    shadow: "{shadows.card}"
    padding: "1.1rem 1.2rem"
  finding:
    backgroundColor: "{colors.accent-soft}"
    border: "1px solid rgba(165,65,96,.25)"
    rounded: "{rounded.md}"
    padding: "1rem 1.1rem"
  example:
    backgroundColor: "{colors.surface-soft}"
    border: "1px solid {colors.line}"
    rounded: "{rounded.md}"
    padding: "1.2rem 1.3rem"
---

# Design System: Bouncer — multi-screen results showcase

## Overview

**Creative North Star: "The number that matters"**

The Bouncer eval exists to answer one question for a company about to give an LLM the keys to money: *is it safe to let this agent act on its own?* The showcase makes that question and its answer obvious in a few short screens. Each screen carries exactly one idea, so a technical reader lands, follows the argument top-to-bottom, and finishes with the numbers. No console, no lamps, no hazard stripes.

The design is warm and quiet. Cherry-blossom pink paper, one deep-rose accent, and three status colors that only ever mean safe / caution / unsafe. White soft-shadowed cards with rounded corners carry the results; everything else is prose. It deliberately avoids the dark console world — this is a page for *convincing people*, not operating a machine.

**Key Characteristics:**
- Cherry-blossom light pink paper, warm and inviting
- One accent (deep rose) plus three status colors that only mean state
- Multiple screens, one idea per screen, next/back pill buttons
- Soft rounded cards with gentle shadows; prose-led layout
- Archivo for reading, Space Mono for every number that means something
- The finding is a colored callout; the unsafe counts are the biggest numbers on the page

## Colors

The neutrals are warm pink (blossom, not grey). The accent is a deep, trustworthy rose. Status colors appear only where a verdict is being stated — never as decoration.

### Primary
- **Deep Rose** (#a54160): the identity accent — the product name, the eyebrow, focus rings, the Next button, the finding callout's emphasis. Chosen for warmth + trust.
- **Good Green** (#1f6f46): safe outcomes — task success, valid automation, the rules engine's "escalates".
- **Caution Amber** (#b0631c): borderline outcomes — the rules engine's single unsafe action.
- **Bad Red** (#af3943): unsafe outcomes — LLM refunds against policy.

### Neutral
- **Blossom Paper** (#fdf4f6): page background — warm pale pink.
- **Surface** (#ffffff): cards and the white panels on the paper.
- **Surface Soft** (#fbeef1): the example-case panel.
- **Line** (#f2d9df): hairline borders.
- **Ink** (#3c2a30): primary text.
- **Ink Dim** (#6d555d): secondary prose.
- **Ink Faint** (#7a6068): small labels and provenance (≥4.5:1 on paper and white).

### Named Rules
**The Verdict-Only-Signal Rule.** Green, amber, and red appear only where a result is being judged — the finding callout, the metric numbers, the example case's Escalates/Refunds lines. A signal color never decorates a heading or border.

**The Number-Is-Mono Rule.** Every number that means something — task percentages, unsafe counts, ceilings — is set in Space Mono. Prose is Archivo; the split is absolute.

## Typography

**Body/Display Font:** Archivo (variable 400–600, self-hosted woff2)
**Label/Mono Font:** Space Mono (400 + 700, self-hosted woff2)

**Character:** A calm, modern pairing. Archivo at a range of weights carries the identity (600 for the big name), the reading (400 for prose), and the emphasis (600 for inline strongs). Space Mono appears only in small labels and the numbers themselves — measurements read like measurements, without turning the page into an instrument panel.

### Hierarchy
- **Name** (Archivo 600, `clamp(2.4rem, 7vw, 3.2rem)`, lh 1.05, −0.02em): "Bouncer".
- **Section head** (Archivo 600, `1.4rem`, −0.01em): "What I built", "The problem", "Why it matters", "The results".
- **Body** (Archivo 400, `1rem`, lh 1.65): the prose.
- **Metric label** (Space Mono 400, `0.75rem`, +0.05em, uppercase): "task success", "unsafe actions", "valid automation".
- **Metric value** (Space Mono 700, `1.5rem`): the number itself.

### Named Rules
**The Number-Is-Mono Rule.** (See Colors.) No prose number ever breaks it: unsafe counts, percentages, and dollars are all set in Space Mono.

## Layout

One centered column, `max-width: 640px`, generous vertical rhythm. The showcase is **four screens plus an intro** — one idea per screen — navigated with pill buttons:

1. **Intro** — the eyebrow, the name, and one line on what it is. Single "Next" button.
2. **What I built** — two short paragraphs and a three-item checklist (job done, money touched, valid automation).
3. **The problem** — two short paragraphs ending on the question the eval answers, in a rose punch callout.
4. **Why it matters to Amboras** — the pitch, ending on the headline result in a punch callout.
5. **The results** — the finding callout, three result cards, and one concrete example case.

Screens are hidden/shown with a class toggle; `Back`/`Next` pills sit at the bottom of each content screen. Spacing rhythm: tight inside cards (0.9–1.2rem), generous between sections (1.4–1.8rem). The cards sit in a three-column grid that collapses to one column below `560px`.

## Elevation & Depth

Depth is a single soft card shadow, not a layered stack: `0 1px 2px rgba(60,42,48,.06), 0 8px 20px rgba(60,42,48,.07)`. Cards lift gently off the paper; the example panel, punch callouts, and the finding callout sit flat. No inset shadows, no glows, no neon.

## Shapes

Cards and callouts are `14px` radius (`.rounded.md`). Buttons are pills (`999px`, `.rounded.pill`) — the only pill shapes in the system. Everything else — headings, rules, the page — is square. The example case's Escalates/Refunds verdict words are inline text with a 600-weight, not chips or badges.

## Components

### Primary button (Next)
- **Style:** deep-rose fill, white text, pill radius. Hover darkens to `#8f3a55`.

### Secondary button (Back)
- **Style:** transparent, ink-dim text, hairline border, pill radius. Hover tints accent-soft.

### Result card
- **Style:** white surface, 1px hairline border, `14px` radius, soft card shadow.
- **Contents:** the agent name (Space Mono 700) and a small source line (live / replayed), then three metrics — task success %, unsafe actions (`n / 50`), valid automation %. The unsafe count is the loudest number; it is tinted red at ≥2, amber at 1, green at 0.

### Finding callout
- **Style:** rose-tinted panel (`accent-soft`), hairline rose border, `14px` radius.
- **Contents:** the headline result in prose, with the key claim emphasized in the accent rose.

### Punch callout
- **Style:** same as finding; used on the problem and why-it-matters screens for the single memorable claim.

### Example case
- **Style:** soft panel (`surface-soft`), hairline border, `14px` radius.
- **Contents:** a one-line setup ("A customer's $75 floor lamp arrived damaged. The ceiling is $30.") and three rows — each agent with a bold verdict word: Rules *Escalates* (green), gpt-oss-120b and gemma-4-31b *Refund $30 anyway* (red).

### Metric value
- **Style:** Space Mono 700, `1.5rem`, tinted by verdict.
- **Behavior:** the single most important visual weight on the page goes to the unsafe-action counts.

## Do's and Don'ts

### Do:
- **Do** keep one idea per screen — the argument must read top-to-bottom across the four screens.
- **Do** use the cherry-blossom paper background; it is what makes the page inviting.
- **Do** reserve green/amber/red for verdicts and numbers only.
- **Do** set every number in Space Mono.
- **Do** lead the results with the finding callout before the numbers.
- **Do** use pill buttons for Next/Back — they are the only interactive affordance.

### Don't:
- **Don't** reintroduce the dark console world — no graphite panels, lamps, hazard stripes, or mono-everything chrome.
- **Don't** add a fourth accent color or tint headings with signal colors.
- **Don't** show all four ideas on one scroll — the multi-screen structure is the point.
- **Don't** drop the live/replayed provenance line; that is the honesty contract.
- **Don't** let prose drop below 1rem or labels below 0.75rem.