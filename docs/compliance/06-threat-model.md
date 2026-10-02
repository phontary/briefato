# 06 — Threat Model (STRIDE) für Briefato

Status: Architektur-Mapping **verifiziert** am 2026-10-02 gegen `/workspace/briefato`; Risikobewertung
ist fachliche Einschätzung (**muss bestätigt werden**). Scope: Portal, SQLite, ein Container auf
einem geteilten Host, Caddy, Stripe, Modell-Provider, Backups, Key-Management und der **betreibende
Agent (SYSADMIN)**.

Quellen: Art. 32 DSGVO, https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02);
MDCG/BSI-Methodik orientiert; DSK Orientierungshilfe KI-Systeme, https://www.datenschutzkonferenz-online.de/media/oh/DSK-OH_KI-Systeme.pdf (abgerufen 2026-10-02).

## 0. Systemübersicht und Trust Boundaries

```
Browser ──TLS──► Caddy (Host, 443, tls internal, crowdsec_protect)
                   │  (reverse_proxy 127.0.0.1:8085)
                   ▼
              briefato-Container (python:3.12-slim, uid 10001, mem 512m, no-new-privileges)
                   ├─ FastAPI (main.py, routes/**)  ── Session/Cookie, CSRF
                   ├─ SQLAlchemy sync  ─► SQLite/WAL  (/data/briefato.db, Volume)
                   ├─ security.py (argon2, Fernet field key, audit)
                   └─ pipeline/** ──HTTPS──► Modell-Provider (EU / sonst Drittland)
                   └─ billing/** ──HTTPS──► Stripe (Checkout/Portal/Webhook)
Host "phontary" (48 Container) ── cron/systemd ─► verschlüsseltes Off-host-Backup
Operator-Agent (SYSADMIN) ──SSH/Docker──► Host & Repo   ⚠ privilegiertester Pfad
```

**Assets:** (A1) klinischer Text/Briefe, (A2) Patienten-PII inkl. Versicherungsnr., (A3) Feld-Key
`BRIEFATO_FIELD_KEY`, (A4) Session-/CSRF-Tokens, (A5) Passwort-Hashes, (A6) Stripe-Keys/Webhook-Secret,
(A7) SQLite-Datei + Backups, (A8) Verfügbarkeit des Dienstes, (A9) Audit-Log.

## 1. Spoofing

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| S1 | Credential Stuffing / Brute-Force gegen `/anmelden` | H | H | Rate-Limit/Throttling `login_max_attempts=10`, `login_window_minutes=15` | Config vorhanden, **Code fehlt (T20)** |
| S2 | Session-Hijack (Cookie-Klau) | M | H | Token serverseitig gehasht, `revoked_at`/`expires_at`; Cookie-Flags | `security.py`, Flags **offen** |
| S3 | Kein MFA | H | H | MFA für Konto + `/admin` | **fehlt** |
| S4 | Login als Admin über `/admin` (sqladmin) | M | H | `users.is_admin`-Gate | vorhanden; kein MFA |
| S5 | Schwache/`dev-secret-change-me`-Secrets in Prod | M | H | `is_prod` erzwingt Feld-Key; `secret_key` aus env | `config.py`/`security.py`; Deploy-Check offen |

## 2. Tampering

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| T1 | Manipulation der SQLite-Datei durch Host-Zugriff | M | H | Datei nur im Container-Volume; Host-Zugriff eingeschränkt; Backups verschlüsselt | `deploy/docker-compose.yml` (Volume `/mnt/fast/docker/briefato/data`) |
| T2 | Gefälschter Stripe-Webhook (`/webhooks/stripe`) | M | M | Signaturprüfung + Idempotenz | Vertrag `billing.handle_webhook(payload, sig_header)`; **Stub** |
| T3 | Manipulation des Audit-Logs | M | M | Log-Append; **keine Hash-Chain** | `audit_events`; Integrität **offen** |
| T4 | Manipulation am Modell-Output vor Speicherung | L | M | Output nur server-seitig; Restore lokal (`Pseudonymizer.restore`) | Vertrag |

## 3. Repudiation

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| R1 | Abstreiten einer Freigabe/Löschung | M | M | `letters.approved_at`, `audit_events`, `updated_at` | Schema vorhanden |
| R2 | Audit-Lücken (Events nicht geschrieben) | M | M | zentraler `security.audit()`-Helper | vorhanden; Disziplin offen |
| R3 | Kein Nachweis genaue Generierung | H | L | Tabelle `generations` je Aufruf | Schema vorhanden |

## 4. Information Disclosure (Kernrisiko)

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| I1 | **Cross-Tenant-Leak** (Objektzugriff auf fremde `user_id`) | M | **H** | jede Query `user_id`-gescoped; Testsuite verlangt 404/403 | D8; **Tests fehlen** |
| I2 | Modell-Provider sieht Patientenbezug | M | H | **Pseudonymisierung vor jedem Call** | D4; **nicht implementiert (T5)** |
| I3 | Klartext auf Platte (DB, Backups) | M | H | Fernet auf `dictation_enc`/`content_enc`/`notes_enc`; Backups verschlüsselt | `security.py` umgesetzt; Backups **geplant** |
| I4 | Feld-Key-Leak (env/pass) | M | H | Key out of repo (`.gitignore` deckt `.env`); **keine Rotation** | `config.py`; Rotation **fehlt** |
| I5 | Container-Ausbruch auf **geteiltem Host** (48 Container) | L | H | `no-new-privileges`, non-root uid 10001, keine Docker-Socket-Mount | `docker-compose.yml`/`Dockerfile` |
| I6 | PII in Logs/Fehlermeldungen | M | M | `letters.error` ist Text; Provider-Fehler können Kontext enthalten | **zu prüfen** |
| I7 | Backup-Leak off-host | M | H | Verschlüsselung + Zugriffskontrolle | **geplant (M12)** |
| I8 | IP in `audit_events`/`auth_sessions` | M | L | Kürzung/Short-TTL | **fehlt (T11)** |
| I9 | Fehlerantworten verraten Existenz fremder IDs | M | L | einheitliche 404 | nicht verifiziert |

## 5. Denial of Service

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| D1 | **Swap-Exhaustion des Hosts** (7268/8191 MB belegt) | **H** | M | Container-Swap aus (`memswap_limit`), S5-Fix | `docs/01-architecture.md §3`; **offen T18** |
| D2 | LLM-Kosten-Abuse (Quota umgehen) | M | M | `subscriptions.letters_quota/used`, Quota-Enforcement | Vertrag; **Stub** |
| D3 | Riesiges Diktat / Endlos-Input | M | M | Input-Längenlimit, `max_tokens`, `llm_timeout_s=180` | teilweise in `providers.py` (Vertrag) |
| D4 | Bot-Traffic auf Landing/Login | H | L | CrowdSec `import crowdsec_protect`, Caddy | Host-Ebene; Schutzgrad prüfen |

## 6. Elevation of Privilege

| ID | Bedrohung | L | I | Mitigation | Beleg/Status |
|---|---|---|---|---|---|
| E1 | Rechteausweitung über `/admin` | M | H | `is_admin`-Check | vorhanden; MFA fehlt |
| E2 | **Betreibender Agent (SYSADMIN)** mit SSH/Docker-Rechte auf Host & Repo | M | **H** | Least Privilege, getrennte Credentials, nur Deployment, **kein echter Patientendaten-Zugriff für den Agent**; Secrets via `pass`, nie im Chat | **Richtlinie muss bestätigt werden** |
| E3 | Git-History leakt Secrets/Patientendaten | L | H | `.gitignore` (`.env`, `*.db`, `*.pem`, `*.key`); „no real patient data in repo“ | `README.md`/`.gitignore` |
| E4 | Compromised Dev-Abhängigkeit | M | H | gepinnte `app/requirements.txt` | offen: kein SCA/Scan |

## 7. Modell-Provider-spezifische Risiken

| ID | Bedrohung | L | I | Mitigation | Status |
|---|---|---|---|---|---|
| M1 | Provider trainiert auf Kundendaten | M | H | „No-Training“-Klausel + AVV + Pseudonymisierung | **offen M1** |
| M2 | Drittlandzugriff (DeepSeek) | M | H | EU-Provider wählen | **offen (09)** |
| M3 | Sub-Prozessoren des Providers unbekannt | M | M | Sub-Processor-Liste verlangen | **offen** |
| M4 | Prompt-Injection aus Diktat-Text | L | M | Systemprompt trennt Instruktion/Daten; Output nur lokal verwendet | Vertrag `prompts.system_prompt` |
| M5 | Modell-Output enthält erfundene Fakten (Halluzination) | M | M | Mitglied gibt jeden Brief frei; kein Diagnose-Anspruch | `08-mdr-boundary.md` |

## 8. Restrisiken (bewusst getragen, bis Gegenmaßnahme greift)

1. **Pseudonymisierung ist noch nicht implementiert** → aktuell ginge bei einem Live-Call Klartext
   an den Provider. **Blocker.**
2. **Kein MFA** auf Konten/Admin.
3. **Keine Key-Rotation** für den Feld-Key.
4. **Kein Restore-Test** → Verfügbarkeitszusage nicht belegt.
5. **Geteilter Host + Swap-Druck** → Verfügbarkeit.
6. **Betreibender Agent** hat tiefe Host-Rechte → Insider-Risiko.
7. **Kein unabhängiger Pen-Test.**

## 9. Monitoring-Hooks (an Art. 32 Abs. 1 lit. d DSGVO)

| Hook | Quelle | Alarm |
|---|---|---|
| Login-Fehlserien | `audit_events.event='auth.login'`, `ip` | Schwelle → Sperre/Alert |
| Cross-Tenant-Versuche | 404/403 auf `/app/**` | Mustererkennung |
| LLM-Kostenausreißer | `generations.cost_usd`, `tokens_*` | Tagesbudget |
| Webhook-Fehler | `billing.handle_webhook` Rückgabe | Alarm bei Signaturfehlern |
| Health | `/healthz` via Docker HEALTHCHECK + Healthchecks | Down-Alert |
| Host-Ressourcen | swap/load/mem | S5-Blocker-Verfolgung |
| Backup-Erfolg | cron-Job-Log | fehlendes Backup |
| Caddy/CrowdSec | Host-Logs | Blocking-Statistik |

## 10. Offene Punkte

- **offen:** Cross-Tenant-Testsuite (D8) tatsächlich grün belegen.
- **offen:** Secret-Hygiene im Prod-Deploy (kein Dev-Default).
- **offen:** Cookie-Flags verifizieren (`main.py`/`routes`).
- **muss bestätigt werden:** Regelwerk für den betreibenden Agenten (kein Patientendatenzugriff,
  Secrets nur aus `pass`).
- **offen:** SCA/Dependency-Scan und Versionierung.
