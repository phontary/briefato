# Briefato portal (`WORKSTREAM-PORTAL`)

FastAPI + Jinja2 + HTMX application serving the member-facing portal, the method pages and
the template library, against the frozen contract in `docs/02-spec-interfaces.md` (§4 template
blocks, §5 route map, §7 design system) and the real workflow in `brain/`.

The product output is **plain text, copy-paste ready** (no markdown, no category labels, no
intro/closing, `Diagnosen:` last). The primary action on a generated letter is **Text kopieren**;
a DOCX with letterhead is an **optional secondary** export.

Owner of these paths: `app/briefato/main.py`, `app/briefato/routes/**`,
`app/briefato/templates/**`, `app/briefato/static/**`, `app/tests/test_portal_method.py`, this
README. The foundation (`config`, `db`, `models`, `security`), the `pipeline`/`billing` packages
and the `brain/**` method are owned by other workstreams and are imported read-only.

## Reproducible self-check

```bash
cd /workspace/briefato

# full test suite (offline, mock LLM, temporary DB)
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests -q

# the wizard suite on its own
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_wizard.py -q

# the chat-portal suite on its own
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_chat_portal.py -q

# boot the real app and walk the new routes (session-based curl matrix)
BRIEFATO_DATA_DIR=/tmp/bd BRIEFATO_LLM_MOCK=true BRIEFATO_SECRET_KEY=dev \
  .venv/bin/python -m uvicorn briefato.main:app --app-dir app --port 8097 &
J=/tmp/bd/cookies.txt; B=http://127.0.0.1:8097
curl -s -c $J -o /dev/null $B/anmelden; T=$(awk '$6=="briefato_csrf"{print $7}' $J)
curl -s -b $J -c $J -o /dev/null -d "csrf_token=$T" -d "email=a@ex.de" \
  -d "password=geheim-1234" -d "full_name=Dr. A" $B/registrieren
for u in /app /app/neu /app/methode /app/vorlagen /app/vorlagen/Atherom.md /admin/vorlagen-vorschlaege; do
  printf '%s  %s\n' "$(curl -s -b $J -o /dev/null -w '%{http_code}' $B$u)" "$u"
done
# choose a type in the wizard and print the step heading + progress
curl -s -b $J -c $J -X POST $B/app/neu --data-urlencode "csrf_token=$T" \
  --data-urlencode 'wiz_state={}' --data 'wiz_step=0' --data 'wtype=entlassbrief' \
  | grep -oE 'Schritt [0-9]+ von [0-9]+|data-wizard-heading>[^<]*'
```

## Layout

| Path | What |
|---|---|
| `main.py` | app factory, CSRF/security-header middleware, exception handlers, router wiring, sqladmin mount, `ensure_library_tables()` |
| `routes/deps.py` | template env, `render()` helper, CSRF guard, auth dependencies, tenant-scoped getters, flash codes |
| `routes/public.py` | `/`, `/preise`, `/impressum`, `/datenschutz`, `/agb`, `/healthz`, `/assets/*` |
| `routes/auth.py` | register, login (+ throttling), logout, password forgot/reset |
| `routes/portal.py` | `/app` dashboard, `/app/suche` full-text search |
| `routes/patients.py` | patient CRUD + archive |
| `routes/letters.py` | letter draft → generate (doc-type + method metadata) → edit → approve → DOCX export → delete |
| `routes/chat.py` | **chat portal `/app/chat`** — composer, one rotating capability line, triage-driven turn, one clarifying question, persisted per-case thread whose follow-ups refine the SAME letter |
| `routes/wizard.py` | sequential type-dependent wizard at `/app/neu` (+ `/app/neu/erzeugen`, `/app/neu/ergebnis/{id}`) |
| `routes/methode.py` | `/app/methode`, `/app/methode/regeln`, `/app/vorlagen[/…]`, proposal flow |
| `routes/admin_vorlagen.py` | `/admin/vorlagen-vorschlaege` review (admin-only), registered before the sqladmin mount |
| `routes/brain_bridge.py` | adapter to `briefato.brain` (triage/retrieval/rule_checker/loader) with a German-safe portal fallback |
| `routes/library_models.py` | the **only** portal-owned table: `template_proposals` |
| `templates/` | `base.html` (blocks `title`, `head`, `content`, `scripts`), `app_base.html`, `app/chat.html` + `app/chat/_stream.html`, `app/methode.html`, `app/vorlagen/*`, `app/admin/*`, editor `app/briefe/_editor.html` |
| `static/css/{tokens,app}.css` | design system + method/library components + the chat portal (`.chat`, `.chat-composer`, `.is-chat-focus`) |
| `static/js/{htmx.min.js,app.js}` | HTMX 2.0.11 vendored; `app.js` adds clipboard copy, the wizard fade and `initChat()` (focus fade, rotating line, Enter-to-send) |

## Method integration

- `routes/brain_bridge.py` calls the parallel brain workstream's API when importable —
  `triage.detect`/`triage.triage`, `triage.TYPES`/`doc_type_options()`, `retrieval.search`/
  `retrieval.retrieve`, `rule_checker.check`, `brain_loader` — and normalises results into stable
  dicts. If the package is missing or raises, it falls back to a **portal-side preliminary
  implementation** built from the brain's own data files (`regelwerk.md`, `manifest.json`,
  `dokumenttypen/*.md`) and reports the source in the UI. A broken brain never produces a stack
  trace in the portal: the editor degrades to a German message (`method_message()`).
- `briefato.pipeline` is imported before `briefato.brain` inside the bridge to keep the
  brain↔pipeline dependency graph acyclic.

## Chat portal (`/app/chat`) — the primary flow

The step-by-step wizard entry was replaced by a conventional chat portal, per the owner's
direction. One centred composer with a single changing capability line above it; the
surroundings fade while the cursor is in the box. Full design + route/DB contract:
`docs/07-chat-portal.md`.

- **Entry decision**: the sidebar CTA *"Neuer Brief"*, the dashboard CTAs and the empty state
  point at `/app/chat`. The wizard stays reachable at `/app/neu` (sidebar *"Assistent"*, and a
  *"Schritt für Schritt statt Chat"* link on the chat page). Nothing was deleted.
- **Self-triage**: the free text goes to `briefato.brain.triage.triage`. A confident result (or
  a long, substantive dictation) generates immediately; a genuinely ambiguous, short order
  (confidence < 0.55 and < 200 chars) yields **exactly one** short question plus 2–3 candidate
  document types as buttons. No letter is created before the answer.
- **One case = one document**: `chat_threads.letter_id` anchors the case. A follow-up message
  regenerates the **same** `letters` row (via `letters._fold_pipeline_letters`); the accumulated
  follow-up instructions are passed as the pipeline's `extra` prompt block. No duplicate letter
  per message.
- **No agent runtime**: one member turn is at most one `POST /chat/completions` from the frozen
  pipeline (plus its rule check and at most one repair retry). No tools, no model memory; the
  thread lives in `chat_threads` / `chat_messages` (Fernet-encrypted content, non-patient
  metadata only) and the portal assembles the prompt.
- **Result bubble**: plain text + `Text kopieren`, the rule-check line (hard/soft), any soft
  `R-REFERENZ` note under *"Aus Referenz ergänzt – bitte prüfen"*, the used templates and a link
  to the letter in the editor. DOCX stays optional under *"Weitere Optionen"*.
- **Accessible**: a real `<form>` with a labelled `<textarea>`; Enter sends, Shift+Enter makes a
  newline; it works as a plain form POST with JS disabled. Focus/rotation respect
  `prefers-reduced-motion`.
- **Focus mode**: `is-chat-focus` on `<body>` fades nav/topbar/breadcrumbs/header/aside and
  hides the capability line; blur or Escape restores them.

## Wizard (`/app/neu`) — the alternative entry

One question per step, document-type-dependent, with a fade between steps and an explicit
summary confirm before anything is generated.

- **Step 1** asks *"Was möchten Sie schreiben?"* with one card per type: Aufnahmebogen,
  Stationärer Entlassbrief, Verlegungsbericht, Ambulanter Brief, OP-Bericht, Zusammenfassung,
  Entlassmedikationsplan, Pflegebericht-Integration, Ablehnungsbogen. Each card carries a
  one-line plain-German "when to use it".
- **Steps 2..n are type-dependent**, built by `routes/wizard.py:build_steps()`:
  - Entlassbrief / Aufnahmebogen / Verlegungsbericht → patient → Aufnahme-Anamnese & KU →
    repeating **Quelle hinzufügen** (label dropdown + textarea, count shown) → summary;
    Verlegung adds an optional Zielklinik (else `XXX`, per kernel rule K7.6).
  - OP-Bericht → patient → OP-Datum → Indikation → Zugang & Kernbefund → Maßnahmen →
    Drainagen + toggle **Standarddetails aus Referenz ergänzen** → Quellen → summary.
  - Ambulant → patient → Aufnahme-/Entlasskontext → Befund → Quellen → summary.
  - Zusammenfassung → patient → one textarea → summary (no sources step).
  - Entlassmedikationsplan → patient → aktueller Plan → Änderungen → summary.
  - Pflegebericht → patient → Pflegeberichte → Klinik → summary.
  - Ablehnungsbogen → patient → abgelehnte Maßnahme → Dringlichkeit/Begründung → summary.
- **State** is carried in a single hidden `wiz_state` JSON field re-posted on every step;
  widgets only carry the current step's answer, which the route merges in. Back/forward
  therefore never loses entered data, and no session store or schema change is needed.
- **Transitions**: `.wizard-step` fades in (`@keyframes wizard-in`, 180 ms); `app.js` adds
  `.wizard-step--leaving` and re-submits with the clicked submitter via `requestSubmit`, so
  the button's `name=action` value survives. Both the animation and the transition are
  disabled under `@media (prefers-reduced-motion: reduce)`.
- **Keyboard**: focus moves to the step heading (`tabindex="-1" data-wizard-heading`), Enter
  continues on text/select/date steps (Weiter is the first submit button), Esc triggers the
  `[data-wizard-back]` button, focus rings are visible.
- **Progress** shows `Schritt X von N` with a `<progress>` bar (no inline styles).
- **Summary** lists Typ, Patient/in, the answered fields and the source count; only its
  confirm form posts to `/app/neu/erzeugen` — the **only** route that creates a letter.
- **Result** (rendered inline after generation and at `GET /app/neu/ergebnis/{id}`): plain
  text with the primary **Text kopieren** button, the Regel-Check panel, Verwendete Vorlagen,
  and (when the pipeline returns them) enrichments under **"Aus Referenz ergänzt – bitte
  prüfen"** with their source. The Letter row is saved as before, so it appears in
  `/app/briefe` and keeps history; the split editor stays available at `/app/briefe/{id}`.
- **Sources → engine**: answers and sources are composed as `Label:\n<text>` blocks, which
  the pipeline's segmenter recognises; >5 sources therefore fan out in the engine. The OP
  toggle maps to the pipeline's `enrich` kwarg when the pipeline accepts it (passed only
  after `inspect.signature`; unknown kwargs are never sent).

## Design pass ("margin" language)

- `tokens.css`: warm canvas `#F2F1EF`, a single white **sheet**, one accent (clinic teal),
  radii 12/16/24, layered soft shadows incl. a sheet shadow, a larger type scale, and a
  dark-pill nav token (`--nav-active-bg`). Dark mode via `prefers-color-scheme` and
  `[data-theme="dark"]` is kept.
- `app.css`: content column widened to `--container: 87.5rem` (1400 px) with a 72ch prose
  measure; the app shell is one white rounded sheet with a soft shadow; sidebar active item is
  a dark pill with grouped labels ("Praxis", "Konto"); KPI strip with hairline dividers
  (dashboard); chips; segmented-control/`list-row`/`enrichment` components; wizard styles.
- Applies to dashboard, lists, editor, methode, vorlagen, account, search and auth (sheet
  card) because the shared classes are restyled. No CDN, HTMX stays vendored, no inline
  styles/scripts (the strict portal CSP keeps working).

## Editor (`/app/briefe/{id}`)

- Left: dictation + **Dokumenttyp** selector (`Automatisch erkennen` default; shows the detected
  type and reason). The explicit choice is persisted on the frozen `letters.template_id` column
  (written after the pipeline fold so the pipeline default cannot overwrite it).
- Right: plain-text reading pane (`#text-result`) with a prominent **Text kopieren** button
  (clipboard + success feedback, `data-copy-target`), **Freigeben** as the primary approval, and
  the DOCX download demoted to an optional secondary menu item.
- **Regel-Check**: green `Regeln geprüft (R1–R67)` when clean, otherwise an amber list of
  concrete findings (rule id + one-line German explanation). Never hidden.
- **Verwendete Vorlagen**: matched Musterbriefe (title + score) with links, or
  `Keine Vorlage gefunden` + a **Vorlage vorschlagen** button.

## Template library (`/app/vorlagen`)

- Browse/search over `brain/musterbriefe/manifest.json` (152 templates), grouped by subject.
- Detail view renders the template file (from `brain_loader`/`BRIEFATO_MUSTERBRIEFE_DIR`/manifest
  `source`). `licence_risk == "review"` templates are marked **nur intern – Referenz**.
- The three scrub-pending templates (`Cholezystolithiasis.md`, `Acne-inversa.md`,
  `Struma_nodosa_Hyperthyreose.md`) are listed as **gesperrt (Prüfung ausstehend)** and are not
  reachable — their detail route returns 404 and they are excluded from retrieval.

## Governance

- `template_proposals` (id, user_id, diagnosis, proposed_sections JSON, note, status
  pending|approved|rejected, review_note, reviewed_at, reviewed_by, created_at, updated_at) is
  created by `routes/library_models.py` via `ensure_library_tables()` at startup.
- `/app/vorlagen/vorschlaege` lists a member's own proposals (scoped by `user_id`);
  `/admin/vorlagen-vorschlaege` is admin-only and can approve/reject. **Approving only flips the
  status and writes an audit event** (`template_proposal.approved`/`.rejected`) — it never writes
  into the read-only `brain/` archive.
- Member rules (`/app/methode`, "Meine Regeln") are stored in
  `user.letterhead_json['custom_rules']` (no schema change). The portal forwards `letterhead_json`
  to the pipeline; the brain's prompt assembly consumes `custom_rules` **after the Kern**. The
  hard Kern rules cannot be overridden.

## Tenant isolation

Every query filters on `user_id` of the session user. Objects fetched by id go through
`get_patient_or_404` / `get_letter_or_404` (404 for foreign ids); proposals are scoped to the
member and cross-checked in `app/tests/test_portal_method.py` (another member cannot read your
proposals and a non-admin gets 403 on the review page).

## Security

- Session cookie `HttpOnly`, `SameSite=Lax`, `Secure` in prod; CSRF double-submit token on every
  POST (403 on failure).
- Security headers on every response (CSP without `unsafe-inline` for portal pages, nosniff,
  `Referrer-Policy`, `X-Frame-Options: DENY`); custom 404/403/500 pages.
- `/admin/vorlagen-vorschlaege` is registered **before** the sqladmin mount so the exact path is
  served by the portal (admin-only) rather than by the generic sub-application.

## Notes / deviations

- **No new dependency** — the method UI uses the standard library plus the already-pinned deps, so
  no `app/requirements.portal.txt` was created.
- **Extensions to the frozen contracts (no contract item changed):** three new routes are added —
  `GET/POST /app/neu`, `POST /app/neu/erzeugen`, `GET /app/neu/ergebnis/{letter_id}` — with three
  new templates (`app/neu.html`, `app/_wizard_field.html`, `app/neu/ergebnis.html`). The chat
  portal adds `GET/POST /app/chat` and `POST /app/chat/wahl` (`routes/chat.py`,
  `templates/app/chat.html`, `templates/app/chat/_stream.html`) plus two new **tables**
  (`chat_threads`, `chat_messages` in `models.py` — additive, `init_db()` creates them).
  `routes/deps.py` gains `get_thread_or_404`. The legacy create form `/app/briefe/neu` and the
  split editor `/app/briefe/{id}` are unchanged and still reachable; the dashboard/list CTAs now
  point at `/app/chat`. `routes/deps.py` gains one Jinja global (`doc_type_label`) so lists can
  show the real document type stored in `template_id`.
- **Pipeline call**: `routes/wizard.py` calls the frozen `pipeline.generate.generate_letter` with
  `kind=<brain document type>`. Enrichment/fan-out keyword arguments are passed **only** when
  `inspect.signature` shows them (today: `enrich`; `sources`/`structured`/`doc_type`/`wizard` are
  sent only if the pipeline ever accepts them, plus a `**kwargs` monkeypatch). If the signature
  rejects a keyword, the call falls back to the frozen signature; the portal never breaks.
- **Source → routing interaction (brain behaviour, not worked around):** the engine's segmenter
  reads the source stack from the dictation, so sources must be in it; the brain's triage, however,
  yields `explicit="arztbrief"` to a stronger dictation order. A source labelled literally
  `OP-Bericht`/`Pflegebericht` on an Entlassbrief can therefore shift the brain's routing. Reported
  as a deviation; fixing it belongs to the brain/pipeline workstreams.
- **Enrichments are runtime-only**: the frozen schema has no column for them, so they are rendered
  on the result page right after generation (where the pipeline result object is still in hand).
  The durable `GET /app/neu/ergebnis/{letter_id}` view shows the saved letter without them.
- **Design pass**: the existing single accent (clinic teal) is kept rather than switching hue; no
  webfont is added (no CDN) — the reference's Inter feel is approximated with the system stack.
- **Packaging gap (not owned here):** `app/Dockerfile` copies only `app/` and `landing/`; the
  `brain/` directory and the `musterbriefe` source are not in the image. Deployed, the method
  pages therefore degrade to the German "Methode nicht eingebunden / Volltext nicht verfügbar"
  state until the brain/deploy workstream packages `brain/` (and points at the source archive).
