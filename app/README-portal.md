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

# boot the real app and walk the new routes (session-based curl matrix)
BRIEFATO_DATA_DIR=/tmp/bd BRIEFATO_LLM_MOCK=true BRIEFATO_SECRET_KEY=dev \
  .venv/bin/python -m uvicorn briefato.main:app --app-dir app --port 8097 &
J=/tmp/bd/cookies.txt; B=http://127.0.0.1:8097
curl -s -c $J -o /dev/null $B/anmelden; T=$(awk '$6=="briefato_csrf"{print $7}' $J)
curl -s -b $J -c $J -o /dev/null -d "csrf_token=$T" -d "email=a@ex.de" \
  -d "password=geheim-1234" -d "full_name=Dr. A" $B/registrieren
for u in /app/methode /app/vorlagen /app/vorlagen/Atherom.md /admin/vorlagen-vorschlaege; do
  printf '%s  %s\n' "$(curl -s -b $J -o /dev/null -w '%{http_code}' $B$u)" "$u"
done
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
| `routes/methode.py` | `/app/methode`, `/app/methode/regeln`, `/app/vorlagen[/…]`, proposal flow |
| `routes/admin_vorlagen.py` | `/admin/vorlagen-vorschlaege` review (admin-only), registered before the sqladmin mount |
| `routes/brain_bridge.py` | adapter to `briefato.brain` (triage/retrieval/rule_checker/loader) with a German-safe portal fallback |
| `routes/library_models.py` | the **only** portal-owned table: `template_proposals` |
| `templates/` | `base.html` (blocks `title`, `head`, `content`, `scripts`), `app_base.html`, `app/methode.html`, `app/vorlagen/*`, `app/admin/*`, editor `app/briefe/_editor.html` |
| `static/css/{tokens,app}.css` | design system + method/library components |
| `static/js/{htmx.min.js,app.js}` | HTMX 2.0.11 vendored; `app.js` adds the clipboard copy handler |

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
- **Packaging gap (not owned here):** `app/Dockerfile` copies only `app/` and `landing/`; the
  `brain/` directory and the `musterbriefe` source are not in the image. Deployed, the method
  pages therefore degrade to the German "Methode nicht eingebunden / Volltext nicht verfügbar"
  state until the brain/deploy workstream packages `brain/` (and points at the source archive).
