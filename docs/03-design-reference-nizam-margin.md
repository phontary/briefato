# Design reference — "margin" by @nizamdesign, applied to Briefato

Source: X post by Nizam (@nizamdesign), 2026-10-01 — *"Pixels, pills and profit: an editorial design
system for finance software"* (23 s video, 1600×1200). Frames extracted by the agent from the HLS
segments of the post (see `artifacts/nizam/`) and reviewed visually on 2026-10-02.

## What the reference actually looks like (observed, not guessed)

- **Canvas + sheet:** warm off-white page background (~`#F2F1EF`) holding ONE large white rounded
  "app sheet" (~24 px radius) with a soft, wide shadow. Everything lives inside that sheet.
- **Sidebar (~230 px):** logo mark (orange square + wordmark) top; a search field with a `⌘K` hint;
  icon + label nav items; a grey group label ("Analyze"); the **active item is a dark filled pill**
  (`#1F1F1F`, white text); bottom block: Notifications (orange count badge), Settings, Help, and a
  user card (avatar, name, role).
- **Page head:** breadcrumb (`Jobs › #5819`), a very large sans headline ("Job #5819", "Forecast",
  "Why labor is leaking") with a status chip (amber "● At risk"), one muted meta line, and two
  top-right actions — a light outline pill ("Share") and a **solid dark pill** (primary action).
- **Controls:** rounded-full pills and segmented controls (`Cost | Hours`), small iOS-style toggles,
  hairline borders (~`#E7E5E2`), 12–16 px card radii, generous whitespace, almost no drop shadows
  inside the sheet.
- **Numbers as heroes:** `12.3%`, `$1.84M`, `35.2%` at display size, with a muted caption line and a
  small delta (`▲ +1.5 pts`) next to it. Four KPI cells in a single row, divided by hairlines.
- **Data-viz vocabulary:** horizontal estimate-vs-actual bars with a hatched "over" segment; dotted
  lollipop strips for distributions (estimated vs actual rows); area + line forecast with a dashed
  target line and a legend of four thin line samples; small hatched mini-bars for ranked lists.
- **Ranked breakdowns:** four columns (Cause / Branch / Job type / Technician), each a list of rows
  "label — value" with a hatched bar under the label; the selected row is a white card with border.
- **AI/insight surfaces:** an amber tinted card ("✨ Margin noticed" + explanation + dark
  "Update template" pill) and a "Suggested fix" card with a soft gradient/mesh image.
- **Narrative section:** "What happened" — a horizontal 5-step timeline (dots on a hairline, date
  above, label + numbers below).
- **Palette:** near-black text `#111`, muted grey `#6B6B6B`, white cards, one blue accent (~`#2E5BFF`),
  magenta/red for cost overrun (~`#D6336C`), green for improvement (~`#2FA36B`), amber for warnings
  (~`#F0A030`), orange brand mark. Colour is **semantic only** — never decorative.
- **Typography:** one modern grotesque throughout (looks like Inter/Söhne class), tight tracking on
  display sizes, small caps-free labels, ~13 px captions. No serif, no italics.
- **Mood:** calm, high-trust, editorial; dense data but never crowded; the eye is led by size and
  weight, not by colour.

## Verdict for Briefato: adopt the language, not the screens

The reference is a **finance/ops analytics** product; Briefato is a **document** product. Copying its
screens would be wrong, but its design language is entirely reproducible with our current stack
(hand-rolled CSS + Jinja + HTMX, no npm) and would lift the whole product:

| Reference pattern | Briefato equivalent |
|---|---|
| App sheet + warm canvas | same: one white sheet on `#F2F1EF`, portal + auth pages |
| Dark pill active nav, grouped labels | same sidebar; groups "Praxis" (Übersicht, Patienten, Briefe, Suche), "Konto" (Konto, Abrechnung) |
| Big headline + status chip + meta line | letter title + status chip (`Entwurf / Erzeugt / Freigegeben`) + "Patient/in · Datum · Arztbrief" |
| KPI strip with hairlines | Briefe diesen Monat · Kontingent (Rest) · Wartet auf Freigabe · Ø Zeit pro Brief |
| Estimate-vs-actual bars | **Diktat vs. Brief**: lines added/removed, length, sections filled |
| Ranked breakdown columns | Patienten-Aktivität · Briefarten · Kostenträger |
| Dotted lollipop strip | Briefe pro Woche (one dot per letter) |
| Amber "✨ Margin noticed" card | **amber "Prüfen" card**: "3 Angaben fehlen — Diagnose/Befund nicht im Diktat erwähnt", "Freigabe ausstehend" |
| "What happened" 5-step timeline | **Patienten-/Brief-Verlauf**: Diktat → erzeugt → bearbeitet → freigegeben → exportiert |
| Segmented control | Kosten | Zeit in the letter editor |
| Dark primary pill | "Brief erzeugen", "Freigeben" |

Not applicable: forecast chart (no forecasting yet), leak drill-down, toggles-as-scenarios.

## Honest caveats

1. The reference is a **showcase** (invented data, designer-grade spacing with likely Tailwind +
   custom type). Some of the polish is many designer-hours; we can get ~90 % of the *impression* with
   the tokens + components above.
2. It needs a **self-hosted webfont** (Inter) to hit that exact typographic feel — allowed (no CDN),
   ~100 KB, one more asset in `landing/assets` + `static/fonts`.
3. Our screens must look good **empty** (a fresh account has 0 letters); the reference never shows an
   empty state, so empty states need explicit design work.
4. Accessibility gains too: the reference's contrast and focus treatment are strong; our current CSS
   already meets AA, this keeps that.

## Proposed restyle plan (if approved)

1. **B1 (½ day):** new token set (`tokens.css`: canvas/sheet/surface, 3-tone text scale, semantic
   colours, radii 12/16/24, shadows, type scale) + component CSS (pill, chip, segmented, card,
   KPI strip, bar/list rows, timeline) — as a style-guide page `/styleguide` rendered from real
   components.
2. **B2 (1–2 days):** apply to the portal shell + dashboard + patients + letter editor (the editor
   becomes two columns: Diktat left, generated letter as the sheet's hero right, dark pill primary).
3. **B3 (½–1 day):** landing page in the same language (keeps its honest copy, gets the sheet/typo/
   chip treatment).
4. **B4 (½ day):** in-product data-viz (KPI strip, per-week dots, Verlauf timeline, Diktat-vs-Brief
   bars) from our real data — no chart library, inline SVG.

Not started; this note is decision support for Mohamed (he asked whether the look is achievable —
answer: yes, this is CSS + markup, no architecture change).
