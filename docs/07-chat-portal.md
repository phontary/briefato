# Briefato — Chat-Portal (`/app/chat`)

Owner: `WORKSTREAM-CHAT-PORTAL`. Status: implemented, staging-verified (tables, routes, UI,
tests, CDP screenshots). This document is the design record and the interface contract for
the chat entry; `docs/02-spec-interfaces.md` remains the frozen overall contract.

## 1. What changed and why

The previous entry to writing a document was the step-by-step wizard at `/app/neu`. The owner
asked for a **conventional chat portal** instead: one centred input box, a changing line above
it that names what the machine can produce, the surroundings fading as soon as the cursor is
in the box, and the system figuring out the document type on its own — with at most one short
clarifying question. Follow-up messages continue the discussion about **the same case**, so a
letter evolves instead of a new one being produced per message.

Decision (recorded): **`/app/chat` is the primary in-app entry.**
- The sidebar CTA *"Neuer Brief"* and the dashboard CTAs point at `/app/chat`.
- The wizard stays fully available at `/app/neu` as the alternative entry (sidebar
  *"Assistent"*, and a *"Schritt für Schritt statt Chat"* link on the chat page). Nothing in
  the wizard was deleted or re-routed.
- `/app` (dashboard) does not host chat itself; it links to it. Keeping the dashboard as a KPI
  overview and the chat as a separate page keeps both pages honest and testable.

## 2. Architecture — no agent runtime

There is **no agent, no tool calls, no model memory, no external session**. One member turn is
at most one `POST /chat/completions` from the frozen pipeline (plus the deterministic rule
check and at most one repair retry inside `pipeline.generate`; a >5-source input can fan out
inside the pipeline — that is the pipeline's documented behaviour, unchanged here). The thread
state lives in **our database** and this portal assembles the prompt from it.

```
browser ── POST /app/chat ──► routes/chat.py
                                │  persist user message (Fernet)
                                │
                                ├─ new case ─► brain.triage.triage(free text)
                                │     ├─ genuinely ambiguous ─► persist ONE question + candidates
                                │     └─ confident ─► create Letter(draft) ─► pipeline.generate_letter
                                │
                                └─ thread has a letter ─► follow-up:
                                       regenerate the SAME Letter (letter_id unchanged),
                                       instructions passed through the pipeline `extra` slot
                                ▼
                          render app/chat.html (full page; plain form POST, no HTMX needed)
```

Only one route can create a letter for a case (the first generating turn); every later turn
folds the pipeline's transient result back onto that same `letters` row via the existing
`letters._fold_pipeline_letters` helper.

## 3. Data model (new tables in `app/briefato/models.py`)

| Table | Columns |
|---|---|
| `chat_threads` | `id` (32 hex), `user_id` FK→users (CASCADE, indexed), `patient_id` FK→patients (SET NULL), `letter_id` FK→letters (SET NULL), `title`, `doc_type`, `status` (`open` \| `active` \| `done`), `created_at`, `updated_at` |
| `chat_messages` | `id`, `thread_id` FK→chat_threads (CASCADE, indexed), `user_id` FK→users (CASCADE, indexed), `role` (`user` \| `assistant`), `kind` (`dictation` \| `followup` \| `choice` \| `question` \| `letter` \| `note` \| `error`), `content_enc` (Fernet), `meta_json` (JSON, non-patient metadata only), `created_at` |

* `chat_thread.letter_id` is the anchor of the "one case = one document" rule.
* `content_enc` is always a Fernet token (dictation, follow-up instruction, generated letter).
* `meta_json` carries only non-patient data: document type + label, hard/soft counts, rule ids
  and messages, matched template titles/scores, model, tokens, cost, `letter_id`.
* Both tables are created by the existing `init_db()` (`Base.metadata.create_all`); adding them
  is backward-compatible — no column on an existing table was touched.

## 4. Route / API contract (owned by `routes/chat.py`)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/app/chat` | Idle chat page (centred composer, rotating capability line, recent cases). `?patient_id=` preselects a patient. |
| `GET` | `/app/chat?thread={id}` | Reopen a persisted case and render the whole discussion. A foreign id → **404**. |
| `POST` | `/app/chat` | One chat turn. Fields: `csrf_token`, `message` (free text), optional `thread_id`, optional `patient_id`, optional `doc_type` (explicit override from "Weitere Optionen"). |
| `POST` | `/app/chat/wahl` | Answer to the single clarifying question. Fields: `csrf_token`, `thread_id`, `doc_type` (candidate value), optional `patient_id`. Creates the letter for that type. |

Behaviour of `POST /app/chat`:

1. No `thread_id` → a new `chat_threads` row is created (`chat.case_opened` audit event).
2. `thread_id` set and the thread already carries a `letter_id` → **follow-up**: the same
   letter is regenerated; the accumulated follow-up instructions are passed as the pipeline's
   `extra` prompt block. No new `Letter` row.
3. `thread_id` set but no letter yet → the new message is triaged again in the same thread.
4. Triage (`briefato.brain.triage.triage`):
   * confident, or a long substantive dictation → the documented default / routed type is used
     and the letter is generated immediately;
   * genuinely ambiguous (confidence < 0.55 **and** input < 200 chars — i.e. an order without
     clinical material) → exactly one assistant question `"Welche Dokumentart soll es sein?"`
     with the 2–3 candidate document types as buttons; **no letter is created**, the thread
     stays `status="question"`.
5. An explicit `doc_type` from "Weitere Optionen" bypasses the ambiguity question.

Errors: a pipeline failure appends an assistant `error` message with a plain German sentence
and marks the letter `failed`; the HTTP status stays 200 so the thread survives. Missing
message → 400. Foreign thread / patient → **404** (never a silent fallback). All POSTs require
the double-submit CSRF token (403 otherwise).

## 5. UI behaviour

* **Centred composer** (`[data-chat-composer]`): a real `<form method="post" action="/app/chat">`
  with a labelled `<textarea name="message">` (label `for`, visible focus), a patient select
  (defaults to the most recent patient) and a *Senden* button. With JS disabled it is a plain
  form POST; with JS, **Enter sends**, **Shift+Enter** inserts a newline.
* **Rotating capability line** (`[data-chat-cap]`): eleven German sentences, one per product
  (Arztbrief, Attest, Befund, Entlassbrief, OP-Bericht, Entlassmedikationsplan, Pflegebericht,
  Zusammenfassung, Verlegungsbericht, Ablehnungsbogen, KV-Nachweis). Rendered server-side with
  the first sentence `is-active` (visible without JS); `app.js` cycles them every **2.5 s**,
  **pauses when the member types**, and stays static under `prefers-reduced-motion: reduce`.
* **Focus mode**: `focusin` on the composer adds `is-chat-focus` to `<body>`; the surrounding
  chrome (`.topbar`, `.shell-nav`, `.breadcrumbs`, `.chat-page-head`, `.chat-aside`) fades to
  `opacity:0; visibility:hidden` and the capability line hides. `focusout` (leaving the
  composer) or **Escape** restores them. Transitions are disabled under reduced motion.
* **Result bubble**: the plain-text letter with a primary **Text kopieren** button, the
  rule-check line (`X harte, Y weiche Hinweise` / `Regeln geprüft (R1–R67)`), any soft
  `R-REFERENZ` note under *"Aus Referenz ergänzt – bitte prüfen"*, the used templates, and a
  link to the letter in the editor (`/app/briefe/{id}`). DOCX stays an optional secondary item
  under *"Weitere Optionen"*.
* The header shows the detected document type, model and token counts (from the pipeline's
  runtime `last_check`, no schema change).

## 6. Privacy

* Pseudonymisation happens **before every model call** inside the frozen pipeline
  (`Pseudonymizer` + the in-code leak assertion on the patient-derived payload). The chat
  portal does not add a second model path: it only calls `pipeline.generate_letter`.
* Clinical text is stored Fernet-encrypted; the portal never returns an `_enc` value raw.
* Every query is scoped by `user_id`; a foreign thread/patient/letter answers 404.
* No real patient data exists anywhere in the repository or in tests.

## 7. Tests

`app/tests/test_chat_portal.py` (offline, mock provider, temporary DB):

* chat page renders idle composer + 11 capability sentences + labelled textarea;
* login required, CSRF required;
* CSS/JS carry the focus-fade and rotating-line contract (`is-chat-focus`,
  `.chat-cap-sentence`, `2500`, `prefReducedMotion`);
* a dictation produces a letter with the correct triage type (`operationsbericht`) and one
  `Letter` row;
* an ambiguous input produces **exactly one** clarifying question with three candidate buttons
  and **no** letter; the question is persisted and shown on reopen;
* choosing a candidate creates the letter; a follow-up refines the **same** `letter_id` and
  does not create a second letter;
* tenant isolation: a foreign thread/letter/patient → 404;
* pseudonymisation asserted before the provider call: a spy provider never receives the raw
  patient name and does receive `{{LAST_NAME}}` / `{{FIRST_NAME}}`;
* no inline `style=`/`<script>` in the chat templates; `/app/neu` still works.

## 8. Reproducible self-check

```bash
cd /workspace/briefato
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_chat_portal.py -q   # chat only
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests -q                       # whole suite

# staging visual pass (shared Chromium over CDP) -> artifacts/c0*.png
.venv/bin/python tools/cdp_chat_shot.py recon
.venv/bin/python tools/cdp_chat_shot.py shots
```

## 9. Deviations / open points

* The composer carries a small patient select (letters must be bound to a patient). It sits in
  the composer bar, so it does not count as "surroundings" and stays visible in focus mode.
* "One model call per turn" is the portal's contract; the frozen pipeline still fans out for
  >5 sources and retries once on hard rule findings. The chat portal does not change that.
* Follow-up instructions are passed as the pipeline's `extra` block (chronological; the last
  one is operative). The document type chosen by triage is pinned per thread, so a follow-up
  body text cannot re-route the case.
* No HTMX in the chat flow: turns are plain full-page form POSTs (simplest, works without JS,
  least bug surface). HTMX remains used elsewhere in the portal.
* Real-model verification (DeepSeek `deepseek-flash`) is done on staging via
  `tools/cdp_chat_shot.py shots`: one dictation through the chat, letter generated, follow-up
  shortens it — see `artifacts/c03-chat-letter-1440.png` and `c04-chat-followup-1440.png`.

## 10. Evidence (staging, real DeepSeek `deepseek-flash`)

Deployed as Portainer stack 69 (`deploy/sync-to-host.sh && deploy/deploy-staging.sh`), then
captured with the shared Chromium over CDP (`tools/cdp_chat_shot.py`):

| File | Shows |
|---|---|
| `artifacts/c01-chat-idle-1440.png` | idle chat, 1440: centred composer, the rotating capability line above it, the patient select, "Ihre Fälle" |
| `artifacts/c02-chat-focus-1440.png` | focused composer, 1440: surroundings faded (sidebar/topbar/header hidden), capability line hidden, focus ring on the box |
| `artifacts/c03-chat-letter-1440.png` | a real case in the chat: the dictation bubble + the generated OP-Bericht bubble (badge `OP-Bericht`, model, tokens, **Text kopieren**, **Im Editor öffnen**, rule-check line, templates) |
| `artifacts/c04-chat-followup-1440.png` | the whole persisted case (full page): dictation → letter → follow-up `kuerzer` → refined letter, **both letter bubbles sharing one `letter_id`** |
| `artifacts/c05-chat-idle-390.png`, `c06-chat-focus-390.png`, `c07-chat-thread-390.png` | the same three states at 390 px |

Capture notes (this Chromium quirk is why `tools/cdp_chat_shot.py` sets them explicitly):
`--force-device-scale-factor=0.5` doubles the emulated viewport (request half, `deviceScaleFactor: 2`),
a stale HTTP cache serves the previous `app.js`/`app.css` (`Network.setCacheDisabled`), CSS
transitions do not advance in the unrendered page (the focus shot is taken under
`prefers-reduced-motion: reduce`, where our CSS applies the fade instantly), and full-page
captures resize the viewport instead of using a clip.
