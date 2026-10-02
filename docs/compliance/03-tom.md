# 03 — Technische und organisatorische Maßnahmen (Art. 32 DSGVO)

Status: Code-Mapping **verifiziert** am 2026-10-02 gegen `/workspace/briefato`; Liste der
**fehlenden** Maßnahmen ehrlich als `offen`/`missing` geführt.
Grundlage: Art. 32 DSGVO, https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02)
(Text gegengeprüft: https://gdpr-info.eu/art-32-gdpr/ , abgerufen 2026-10-02);
§ 22 Abs. 2 BDSG, https://www.gesetze-im-internet.de/bdsg_2018/__22.html (abgerufen 2026-10-02);
DSK Orientierungshilfe TOM für KI-Systeme, https://www.datenschutzkonferenz-online.de/media/oh/DSK-OH_KI-Systeme.pdf (abgerufen 2026-10-02).

Legende Status: **umgesetzt** = Code vorhanden und gelesen · **geplant** = Vertrag/Spez spezifiziert,
Umsetzung ausstehend · **fehlt** = noch nicht begonnen.

## 1. Vertraulichkeit

| # | Maßnahme | Status | Beleg / Code-Artefakt | Restrisiko / offen |
|---|---|---|---|---|
| T1 | **Passwort-Hashing** mit Argon2id | umgesetzt | `app/briefato/security.py` → `_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)`, `hash_password`/`verify_password` | — |
| T2 | **Serverseitige Sessions** mit gehashtem Token | umgesetzt | `security.py` `new_session_token`/`hash_token` (SHA-256), Tabelle `auth_sessions.token_hash`; `current_user` prüft `revoked_at`/`expires_at` | Cookie-Flags (Secure/HttpOnly/SameSite) im Portal-Code zu verifizieren (nicht im Repo-Ausschnitt) |
| T3 | **CSRF-Schutz** | umgesetzt | `security.py` `new_csrf_token`/`check_csrf` (itsdangerous, Double-Submit + Signaturprüfung) | Token-Lebensdauer = `session_ttl_hours` (14 Tage) — Verkürzung erwägen |
| T4 | **Feldverschlüsselung** klinischer Texte (Fernet/AES-128-CBC+HMAC) | umgesetzt | `security.py` `encrypt_field`/`decrypt_field`/`_fernet`; Spalten `letters.dictation_enc`, `letters.content_enc`, `patients.notes_enc` | **keine Key-Rotation** (T16); Key-Herkunft `BRIEFATO_FIELD_KEY` über env/pass |
| T5 | **Pseudonymisierung vor Modellaufruf** | **geplant** | Vertrag: `docs/02-spec-interfaces.md §6` `Pseudonymizer` (FIELDS = last_name, first_name, birth_date, insurance_number, street, zip, city, phone, email), Tokens `{{TOKEN_n}}`; Implementierung = Stub (`pipeline/generate.py` wirft `NotImplementedError`) | **Noch nicht implementiert** — WORKSTREAM-PIPELINE. Muss vor jeder echten Verarbeitung stehen. |
| T6 | **Mandantentrennung** (Tenant-Scoping) | umgesetzt (Schema) / geplant (Adversarial-Test) | jede Tabelle trägt `user_id` (`models.py`); D8 verlangt Testsuite für Cross-Tenant-404/403 | Testsuite noch nicht im Repo — **offen** |
| T7 | **Transportverschlüsselung (TLS)** | umgesetzt (Staging) / geplant (Public) | `deploy/caddy-briefato.caddyfile` (`tls internal`, `import common`, `import crowdsec_protect`); Port nur loopback `127.0.0.1:8085` | **Offen:** echtes Let's-Encrypt-Zertifikat erst mit öffentlicher Domain (M8); `import common` (Sicherheits-Header) auf Host verifizieren |
| T8 | **Least Privilege im Container** | umgesetzt | `app/Dockerfile` (User `briefato` uid 10001, kein Root); `deploy/docker-compose.yml` (`no-new-privileges:true`, `mem_limit: 512m`) | — |
| T9 | **Geheimhaltungsverpflichtung** (§ 203 Abs. 4 StGB) | **geplant** | vertraglich (siehe `02-avv-checklist.md §3`) | fehlt noch formal |
| T10 | **Zugriffsbeschränkung / Admin-Panel** | umgesetzt / Risiko offen | `/admin` (sqladmin) nur für `users.is_admin` | Adminzugang ohne MFA — hohes Restrisiko (T15) |
| T11 | **IP-Kürzung / Datensparsamkeit** in Logs & Audit | **fehlt** | `audit_events.ip`, `auth_sessions.ip` voll gespeichert | Kürzung (z. B. letztes Oktett) ist DSK-Empfehlung (Datensparsamkeit) — offen |

## 2. Integrität

| # | Maßnahme | Status | Beleg | Restrisiko |
|---|---|---|---|---|
| T12 | **Audit-Log** (§ 22 Abs. 2 Nr. 2 BDSG) | umgesetzt | Tabelle `audit_events` + Helper `security.audit()`; Events z. B. `auth.login` | Logs unverschlüsselt; Integrität nicht kryptografisch gesichert (kein Hash-Chain) — offen |
| T13 | **Approval-Workflow** (Freigabe sperrt Brief) | geplant | Vertrag: `letters.status` `draft…approved`, `approved_at`; Route `POST /app/briefe/{id}/freigeben` | noch nicht implementiert |
| T14 | **Idempotente Stripe-Webhooks** | geplant | Vertrag `billing.handle_webhook(...)` → `{"handled": bool}` | Stub |

## 3. Verfügbarkeit & Belastbarkeit

| # | Maßnahme | Status | Beleg | Restrisiko |
|---|---|---|---|---|
| T15 | **Backup der Portal-DB** | geplant | Architektur S1/S5: cron/systemd-Backup der DB | Restore-Test **fehlt** |
| T16 | **Verschlüsseltes Off-host-Backup + Restore-Test** | geplant | Architektur S5; „encrypted and one copy leaves the host“ (D7) | **M12** — noch nicht durchgeführt/protokolliert |
| T17 | **Healthcheck/Neustart** | umgesetzt | `Dockerfile` HEALTHCHECK auf `/healthz`; `restart: unless-stopped` | — |
| T18 | **Swap/Stabilität des Hosts** | **fehlt** | `docs/01-architecture.md §3` — Swap 7268/8191 MB, 48 Container | S5-Blocker; kann Verfügbarkeit beeinträchtigen |
| T19 | **WAL-Modus SQLite** | umgesetzt | Architektur D3 (SQLite/WAL) | — |

## 4. Regelmäßige Prüfung/Evaluierung (Art. 32 Abs. 1 lit. d)

| # | Maßnahme | Status | Beleg | Restrisiko |
|---|---|---|---|---|
| T20 | **Rate Limits / Login-Throttling** | **geplant** | Config: `login_max_attempts=10`, `login_window_minutes=15` — **kein Code** | Brute-Force offen |
| T21 | **Security-Header** | **muss verifiziert werden** | Host-Caddy `import common` | Header-Set nicht im Repo einsehbar |
| T22 | **CrowdSec / IPS** | umgesetzt (Host) | `import crowdsec_protect` in Caddyfile | Abdeckung/Regeln auf Host prüfen |
| T23 | **Pen-Test / unabhängiger Angriffstest** | **fehlt** | — | vor Beta empfohlen |
| T24 | **Monitoring/Alerting** | geplant | Healthchecks (S5) | — |
| T25 | **Testabdeckung / CI** | teilweise | `app/tests/test_foundation.py`, `.pytest_cache` | Pipeline-/Billing-Tests fehlen (Stub-Phase) |

## 5. KI-spezifische TOM (DSK-Orientierungshilfe KI-Systeme)

| # | Maßnahme | Status | Beleg |
|---|---|---|---|
| T26 | **Kein Training auf Kundendaten** | **muss vertraglich bestätigt werden** | Provider-Briefing `09`; Pseudonymisierung D4 |
| T27 | **Datenminimierung im Prompt** (nur nötiger Text, keine IDs) | geplant | `Pseudonymizer.mask()` (Vertrag) |
| T28 | **Reproduzierbarkeit/Nachvollziehbarkeit** je Generierung | umgesetzt (Schema) | Tabelle `generations` (`provider`, `model`, `tokens_*`, `pseudonymised`, `latency_ms`, `status`, `error`) |
| T29 | **menschliche Letztentscheidung** (Mitglied gibt jeden Brief frei) | geplant | Approval-Workflow (T13), `08-mdr-boundary.md` |
| T30 | **AI-Literacy** (KI-VO Art. 4, seit 02.02.2025) | **fehlt** | Schulungsnachweis für Betreiber/Support zu erstellen |

KI-VO Art. 4: https://artificialintelligenceact.eu/article/4/ (abgerufen 2026-10-02);
KI-VO Zeitachse: https://artificialintelligenceact.eu/implementation-timeline/ (abgerufen 2026-10-02).

## 6. Ehrliche Zusammenfassung: was fehlt

**Vor jeder Verarbeitung echter Patientendaten zwingend:**
1. Pseudonymisierung **implementiert und getestet** (T5) — derzeit nur Vertrag.
2. Adversarial-Tenant-Test grün (T6).
3. Rate-Limits/Login-Throttling (T20).
4. Verschlüsseltes Off-host-Backup + **durchgeführter Restore-Test** (T16, M12).
5. AVV-Kette geschlossen (T9, Sub-Prozessoren).

**Für die Beta empfohlen:**
6. MFA für Konten und Admin (derzeit **fehlt**).
7. Key-Rotation für `BRIEFATO_FIELD_KEY` (derzeit **keine**).
8. Unabhängiger Pen-Test (T23).
9. Security-Header verifizieren (T21) und Swap-Problem lösen (T18).
10. IP-Kürzung in Logs/Audit (T11) und AI-Literacy-Nachweis (T30).
