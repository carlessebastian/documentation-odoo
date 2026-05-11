# Plan de desarrollo — odoo-agent

Roadmap canónico del proyecto. **Single source of truth para el estado
de la implementación.** Permite pausar y retomar sesiones sin perder
contexto entre conversaciones de Claude Code.

> **Convención de actualización**: tras completar cada paso, actualizar:
> - Sello "Última actualización" (sección **Estado actual**)
> - "Última fase completada" + "Próximo paso"
> - Marcar `[x]` en el bloque correspondiente
> - Añadir una línea al **Histórico de cambios** al final
>
> El agente debe leer este archivo al inicio de cada sesión que toque el
> proyecto. La regla está reforzada en memoria.

---

## Estado actual

- **Última actualización**: 2026-05-11 (Fase 4.2.2 cerrada)
- **Última fase completada**: **Bloque C — Fase 4.2.2 (dump real de
  Holded — histórico completo 2018-2026)**. Dump en
  `docs/tenants/inpr3mium/holded-export/2026-05-11/`: **969 MB**, 23
  resources, 3.363 contactos + 1.569 productos + **12.212 documentos**
  (3.430 invoice + 7.998 purchase + 678 creditnote + 69 purchaserefund
  + 34 proform + 3 estimate) + 2.250 asientos contables + **7.489
  PDFs** (3.430 invoice 142.6 MB + 4.059 purchase 801.4 MB; 3.939
  purchases sin PDF original = asientos manuales). errors.jsonl: 0
  líneas. 4 bugs del cliente descubiertos y corregidos durante el
  proceso: (1) paginación sin `page_size` capaba a 500 items en
  contacts/products/payments; (2) paths `/warehouse` y
  `/expensesaccount` no existen — los reales son `/warehouses` y
  `/expensesaccounts` (plurales); (3) `dailyledger` requiere ventanas
  ≤ 1 año, ahora chunkea automáticamente por años; (4) `/documents`
  sin filtro `starttmp`/`endtmp` devuelve SOLO el año en curso —
  detectado tras dump inicial parcial (solo 490 docs / 2026), ahora
  chunkea por años con defaults sensatos (2018-01-01 → now+1d).
  68/68 tests offline OK tras los fixes. `migration-from-holded.md`
  actualizado con volúmenes reales + 3 tablas (sequences, mapeo IVA,
  cuentas de gasto). Input directo para Fase 4.3.
- **Fase 4.2.1 (previa)**: skill `holded-export` MVP creada con:
  - `SKILL.md` con triggers ("exportar holded", "dump holded",
    "facturas recibidas escaneadas", ...) y garantía read-only.
  - Cliente HTTP `holded_client.py` con whitelist de 28 endpoints GET,
    backoff 429/5xx (respeta `Retry-After`), masking de API key en logs.
    Garantía read-only verificada por test
    (`test_no_write_verbs_in_public_api`).
  - `scrape_holded_docs.py` vendorizó 59 `.md` de
    `developers.holded.com/reference` en `references/holded-api/`.
  - `holded_inspect.py` (preflight), `holded_export.py` (dump JSONL +
    PDFs originales escaneados via `getdocumentpdf` base64, idempotente
    y resumible), `dump_summary.py` (post-mortem).
  - Tests offline: 68/68 ok.
  - `.env.example` con `HOLDED_API_KEY` + `HOLDED_API_BASE`.
  - `.gitignore` excluye `docs/tenants/*/holded-export/`.
  - Decisión: la skill se llama **`holded-export`** (no
    `odoo-data-migration` como reservaba el plan original). Una skill
    por origen externo; `fedefarma` tendrá `axional-export`.
- **Próximo paso**: abrir **Fase 4.3** (diarios, secuencias,
  posiciones fiscales) informada por el dump de Holded:
  - 6 secuencias de invoice distintas en Holded (A-, AC-, AF-, KD-,
    FVU-, L-) → decidir 6 diarios separados o 1 con selector.
  - Mapeo de IVA: usar campo `key` de Holded (ej. `s_iva_21`) como
    join contra `l10n_es` (ej. `s_iva21b`).
  - 148 cuentas de gasto de 11 dígitos → colapsar a PGCE Pymes 4-7
    dígitos + analítica para granularidad.
  - Posiciones fiscales: intracomunitario UE (clave `Adq.Intracom.*`
    presente en taxes), ISP servicios extra-UE, RE (varios `s_iva_re_*`
    en el dump).
  Detalle completo en `docs/tenants/inpr3mium/migration-from-holded.md`
  sección "Hallazgos del dump del 2026-05-11".
- **Tenant activo**: `inpr3mium`. Instancia Odoo 19 viva en
  `~/Documents/code/odoo-instances/inpr3mium-local` (Docker local).
  Secrets en `~/Documents/code/odoo-instances/inpr3mium-local.SECRETS.txt`.

---

## Contexto

El agente nació como fork de `odoo/documentation` 19.0; se reestructuró
y se convirtió en un agente Claude Code multi-tenant para administrar
instancias self-hosted Odoo 19 Community con doodba. El primer cliente
real es `inpr3mium`, que migra desde Holded. Cliente futuro previsto:
`fedefarma` (migra desde Axional). Las skills son agnósticas al
tenant; los datos por cliente viven en `docs/tenants/<slug>/`.

Plan original con todo el detalle:
`~/.claude/plans/bien-ahora-planifiquemos-cuales-snazzy-duckling.md`
(referencia histórica; este archivo es la versión vigente).

---

## Fases del proyecto

### Fase 1 — Limpieza + arquitectura multi-tenant *(prerrequisito)*

**Objetivo**: el agente deja de mencionar empresas ficticias y aprende
a leer un perfil de tenant desde disco vía `ODOO_AGENT_TENANT`.

- ✅ **1.1** Auditar y eliminar referencias a empresas ficticias
  (24 archivos: skills, references, evals, tests, scripts, assets,
  memoria). Sustituidas por placeholders `<TENANT_NAME>` /
  `<TENANT_VAT>` en runbooks y por "Acme Holdings/Iberia/Foods S.L."
  en ejemplos narrativos. Renombrado
  `ikigai_company_tree.json` → `company_tree.example.json`.
- ✅ **1.2** Estructura `docs/tenants/{README.md, _template/, inpr3mium/}`
  con schema completo de `profile.yaml` (legal_name, NIF, plan
  contable, EDI stack, flags fiscales, companies, expected_modules,
  source_system, migration). Activación vía env var
  `ODOO_AGENT_TENANT`.

### Fase 2 — Onboarding del agente *(prioridad declarada por usuario)*

**Objetivo**: con `.env` lleno y `profile.yaml` definido, en un solo
comando el agente confirma que puede operar contra el Odoo real.

- ✅ **2.1** `.env.example` en raíz con todas las env vars agrupadas
  y comentadas.
- ✅ **2.2** `docs/onboarding.md` con playbook de primer arranque
  (6 pasos: bot user, configurar tenant, llenar `.env`, lanzar
  `/onboard`, resolver rojos, empezar a operar).
- ✅ **2.3** Slash-command `/onboard` en `.claude/commands/onboard.md`
  con 10 checks no destructivos (profile leído, env RPC, RPC reachable,
  API key, bot ≠ admin, grupos, empresa, módulos esperados, SSH a
  doodba, tests offline).

### Fase 3 — Provisión doodba *(manual, dentro de `docs/infra/`)*

**Objetivo**: documentar el provisioning del entorno (fuera del scope
ejecutable del agente, pero el agente lo necesita).

- ✅ **3** `docs/infra/{README.md, doodba-bootstrap.md, secrets.md}`
  creados. `doodba-bootstrap.md` cubre Modo A (Docker local en
  Mac/Linux: copier, repos.yaml, addons.yaml, gitaggregate, docker
  compose, crear DB, crear bot user, configurar `.env`, validar con
  `/onboard`) y Modo B (gcloud Compute Engine: arquitectura, IP
  estática, VM, traefik+Let's Encrypt, backups, migración A→B).
  `secrets.md` define qué se versiona, qué no, dónde vive cada
  secreto, política de rotación y acceso al certificado AEAT.

### Fase 4 — Bootstrap funcional de inpr3mium en Odoo 19

**Objetivo**: con doodba arrancado y DB vacía, dejar la instancia
**lista para facturar** en español. Es el primer uso real del agente.

- ✅ **4.1** Instalación de módulos completada (12/12 `expected_modules`
  con state=installed, 75 módulos totales en DB). Aprendizajes: 3 repos
  OCA "ocultos" hubo que añadir (`reporting-engine`, `server-ux`,
  `community-data-files`); `addons.yaml` debe listar TODA la cadena
  transitiva (doodba `addons init` no sigue `depends`); 5 pip pkgs
  añadidos a `pip.txt` (`pycountry`, `xmlsig`, `xlsxwriter`, `xlrd`,
  `schwifty==2024.4.0`); workaround `PGDATABASE=devel` con
  `docker compose run --rm -e PGDATABASE=<db>`; chown filestore para
  alinear UID entre `exec` y `run --rm`. Todo capturado en memoria
  `project_odoo19_doodba_gotchas.md` y runbook
  `.claude/skills/CLAUDE.md`.

- ✅ **4.0** `profile.yaml` de inpr3mium relleno. Decisiones tomadas:
  PGCE Pymes (justificado por análisis del cuadro de cuentas Holded),
  EDI stack OCA, sociedad única, sector servicios profesionales con
  packs PLV marginales, flags fiscales (IRPF profesionales,
  intracomunitario UE, servicios extra-UE USA), bot user
  `bot.contable@inpr3mium.com`, años fiscales 2024-2026, scope
  migración histórico completo con validación 24-25.
- ✅ **4.2** Empresa, idiomas y chart template completados.
  Idiomas: `es_ES + ca_ES` activos. Company id=1 con todos los datos
  del profile (nombre legal, VAT, Spain/Barcelona, contacto). Chart
  `es_pymes` cargado (646 cuentas PGCE Pymes). Bot reconfigurado (tz
  Europe/Madrid + grupos account/partner manager). `web.base.url.freeze`
  activado.
- ✅ **4.2.1** **Skill `holded-export` MVP (solo lectura Holded)**.
  Creada como 4ª skill del agente, read-only (solo verbos HTTP GET,
  whitelist de 28 endpoints, masking de API key, test que asserta
  ausencia de métodos de escritura). Outputs entregados:
  - `SKILL.md` con frontmatter read-only + triggers + workflow.
  - `scripts/holded_client.py` cliente HTTP con backoff 429/5xx,
    paginación heterogénea (page=N para `dailyledger`, lista única
    para el resto), helpers `iter_*` por resource y `download_pdf`
    para originales escaneados.
  - `scripts/scrape_holded_docs.py` vendorizó 59 `.md` en
    `references/holded-api/` (376 KB offline, sha256 indexado).
  - `scripts/holded_inspect.py` (preflight counts),
    `scripts/holded_export.py` (dump completo a JSONL + PDFs + manifest,
    idempotente y resumible), `scripts/dump_summary.py` (post-mortem).
  - 4 `references/*.md` (api-overview, endpoint-coverage,
    pdf-attachments, dump-layout).
  - Tests offline: 68/68 ok (incluido `test_no_write_verbs`).
  - `.env.example` con `HOLDED_API_KEY` + `HOLDED_API_BASE`.
  - `.gitignore` excluye `docs/tenants/*/holded-export/`.
  - **Sin escritura a Odoo** (Fase 5).
  - **Pendiente operativo**: ejecutar el dump real contra inpr3mium
    cuando el operador configure `HOLDED_API_KEY` en `.env`.
- ✅ **4.2.2** **Dump real de Holded ejecutado** (2026-05-11).
  Output en `docs/tenants/inpr3mium/holded-export/2026-05-11/` (43.4
  MB, gitignored). Detalle de hallazgos en
  `migration-from-holded.md`. Durante el dump se detectaron y
  arreglaron 3 bugs del cliente (paginación, paths plurales,
  chunking dailyledger por años). 68/68 tests offline OK.

  **Plan de ejecución original** (mantenido como referencia):

  **Pre-requisitos** (confirmar antes de empezar):
  - `HOLDED_API_KEY` presente en `.env` y rotada (no la compartida
    en chat el 2026-05-11).
  - `ODOO_AGENT_TENANT=inpr3mium` en `.env` (resuelve el output dir).
  - `docs/tenants/inpr3mium/holded-export/` está gitignored
    (verificado en `.gitignore`).
  - 1-2 GB libres en disco (estimación: ~500 MB JSONL + ~150-300 MB
    PDFs para una empresa media; ajustar tras inspect).

  **Paso 1 — Smoke test de conectividad** (no toca disco):

  ```bash
  python3 .claude/skills/holded-export/scripts/holded_export.py \
    --output-dir /tmp/holded-smoke \
    --resources numbering_series \
    --no-pdfs --no-confirm \
    --limit 1
  ```

  Verifica: el script termina con exit 0, crea
  `/tmp/holded-smoke/numbering_series.json` con datos reales, sin
  `errors.jsonl`. Borrar tras la prueba (`rm -rf /tmp/holded-smoke`).
  Si falla con `401/403`: la API key está mal o no tiene scope para
  invoicing. Si falla con `429` repetido: Holded está limitando;
  reintentar más tarde.

  **Paso 2 — Inspect (dimensionado)**:

  ```bash
  python3 .claude/skills/holded-export/scripts/holded_inspect.py
  ```

  Output esperado: tabla con counts por resource. Anotar
  aproximadamente: nº de contactos, nº de docs por type (especial
  atención a `purchase` e `invoice`), nº de asientos en
  `dailyledger`. Esto define el tiempo y disco que necesitará el
  dump completo.

  **Paso 3 — Confirmar plan con el operador** (texto a mostrar):

  ```
  Plan del dump:
    - Output:    docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>/
    - Resources: todos (contactos, productos, docs por type,
                 dailyledger, taxes, treasury, numbering_series, ...)
    - Doc types: todos los 10 (invoice, purchase, creditnote, ...)
    - Fechas:    sin filtro (histórico completo)
    - PDFs:      sí (invoice + purchase originales escaneados)
    - Tiempo:    ~N min según counts de inspect
    - Tamaño:    ~M MB estimado
  ```

  **Paso 4 — Dump completo**:

  ```bash
  python3 .claude/skills/holded-export/scripts/holded_export.py \
    --output-dir docs/tenants/inpr3mium/holded-export/$(date +%F) \
    --include-pdfs \
    --no-confirm   # si el plan ya está acordado interactivamente
  ```

  Notas:
  - Si se corta a mitad: relanzar con `--resume` (mismo
    `--output-dir`). El manifest se actualiza tras cerrar cada
    resource, así que como mucho se rehace un resource.
  - Para limitar a 2024-2025 primero (subset de validación —
    recomendado para el primer pase si hay >5 años de histórico):
    añadir `--start-date 2024-01-01 --end-date 2025-12-31`.

  **Paso 5 — Validar el dump**:

  ```bash
  python3 .claude/skills/holded-export/scripts/dump_summary.py \
    --dir docs/tenants/inpr3mium/holded-export/$(date +%F)
  ```

  Exit code 0 = OK. Exit code 1 = warnings (revisar). Verificar:
  - `errors.jsonl` vacío o con razones documentadas.
  - PDFs no-cero en `pdfs/invoice/` y `pdfs/purchase/`.
  - Items en manifest ≈ items en disco para cada `.jsonl`.

  **Paso 6 — Inspección humana para alimentar Fase 4.3**:

  Examinar manualmente (NO programáticamente):

  ```bash
  jq . docs/tenants/inpr3mium/holded-export/$(date +%F)/numbering_series.json
  jq . docs/tenants/inpr3mium/holded-export/$(date +%F)/taxes.jsonl | head
  jq -r '.code' docs/tenants/inpr3mium/holded-export/$(date +%F)/expensesaccount.jsonl | sort -u | head -20
  ```

  Anotar en `docs/tenants/inpr3mium/migration-from-holded.md` (sección
  "Particularidades a resolver durante el ETL"):
  - Formato real de secuencias por type (ej. `FAC-{YYYY}-NNNN`,
    `COMP-2024-001`, etc.). Crítico para `ir.sequence` en 4.3.
  - Lista de tipos de IVA realmente usados (21/10/4/0, IRPF
    profesionales, RE) → mapeo a `account.tax` de `l10n_es`.
  - Códigos de cuenta más usados (sample top-20) → mapeo PGCE Pymes.

  **Paso 7 — Commit del bloque 4.2.1 + 4.2.2**:

  ```bash
  git add .claude/skills/holded-export/ .env.example .gitignore \
          CLAUDE.md .claude/skills/CLAUDE.md docs/PLAN.md \
          docs/tenants/inpr3mium/migration-from-holded.md
  git status   # confirmar que NO se commitea docs/tenants/.../holded-export/
  ```

  Mensaje sugerido (estilo existente):
  ```
  [ADD] holded-export: skill read-only + dump inicial de inpr3mium

  - Skill `holded-export` (4ª del agente): cliente HTTP solo-GET,
    whitelist de 28 endpoints, scraper de doc, exporter idempotente.
  - 68/68 tests offline ok (incluye test_no_write_verbs).
  - 59 .md vendorizados de developers.holded.com/reference.
  - Dump real de inpr3mium ejecutado: <N> contactos, <N> facturas
    emitidas, <N> recibidas (con <N> PDFs originales escaneados),
    <N> asientos en dailyledger.
  ```

  Tras esto, Fase 4.2.2 se marca ✅ y pasamos a **Fase 4.3**.

- ⏸ **4.3** Plan contable, diarios (incluidos COMI / COMX / QONT del
  profile), secuencias con prefijo de año, posiciones fiscales
  (intracom UE, ISP servicios extra-UE). **Informado por el dump de
  Holded de 4.2.1 + 4.2.2** — preservar continuidad de numeración y
  mapear cuentas/diarios reales en uso.
- ⏸ **4.4** Bot user + permisos + record rules + `audit_admin_state`.
- ⏸ **4.5** EDI: certificado digital + entornos test/prod en módulos
  AEAT. Pasos manuales documentados en `edi-setup.md`.
- ⏸ **4.6** Smoke test contable: primera factura + SII test +
  reporting.
- ⏸ **4.7** Checkpoint y commit con bitácora del bootstrap.

### Fase 5 — Migración de datos desde Holded

**Objetivo**: importar maestros y, según scope acordado, histórico
completo + año en curso. Validación previa con subset 2024-2025.

- ⏸ **5.1** Diseño ETL detallado en `migration-from-holded.md`
  (ya con esqueleto; detalle pendiente). El esqueleto debe basarse en
  el dump real obtenido en 4.2.1.
- ✅ **5.2** *(decisión tomada anticipadamente en Fase 4.2.1)* — Sí
  se abre una skill dedicada. Renombrada de `odoo-data-migration` a
  **`holded-export`** (una skill por origen externo: más simple
  trigger-wise). Inicialmente solo lado lectura (4.2.1); la carga a
  Odoo (create/write vía RPC) se hará en 5.3+ con scripts ad-hoc o
  con una skill futura `holded-to-odoo`. Para `fedefarma` vendrá una
  skill paralela `axional-export`.
- ⏸ **5.3** Validación con subset 2024+2025: ETL + cuadre balance +
  conteo partners.
- ⏸ **5.4** Histórico completo + año en curso tras OK del subset.
- ⏸ **5.5** Cutover día D: corte limpio en Holded, saldos apertura,
  primer asiento operativo en Odoo.

### Fase 6 — Generalización para fedefarma *(diferida)*

**Objetivo**: usar el agente con un segundo tenant migrando desde
Axional. No tocar hasta que `inpr3mium` esté en producción.

- ⏸ **6** `docs/tenants/fedefarma/{profile.yaml,
  migration-from-axional.md}`. Reusar las 3 skills Odoo + crear una
  skill paralela `axional-export` (gemela de `holded-export` para
  Axional).

---

## Bloques (orden de ejecución)

### Bloque A — Agente listo (sin instancia real) ✅

1. ✅ Fase 1.1 (limpieza Ikigai → genérico)
2. ✅ Fase 1.2 (estructura multi-tenant + template)
3. ✅ Fase 2.1 + 2.2 (`.env.example` + `docs/onboarding.md`)
4. ✅ Fase 2.3 (`/onboard` slash-command)
5. ✅ Fase 4.0 (rellenar `profile.yaml` de inpr3mium con decisiones
   reales)
6. ✅ Pausa: commit + push (`76ab81904` + commit del profile pendiente
   ahora).

### Bloque B — Provisionar y arrancar (manual + agente)

7. ✅ **Fase 3** — `docs/infra/doodba-bootstrap.md` con Modo A
   (local) y Modo B (gcloud) + `secrets.md`.
8. ✅ Provisión real del entorno (Modo A: Docker local) — ejecutada
   por el agente acompañando al usuario. Doodba copier 9.5.0 +
   Odoo 19.0 + Postgres 16. 8 repos OCA pinneados a 19.0
   sincronizados con gitaggregate. Stack levantado, DB
   `inpr3mium_dev` creada con `--load-language=es_ES` (CLI, no
   wizard porque PGDATABASE=devel hardcoded en devel.yaml).
9. ✅ Bot user + API key creados (uid=8) vía `odoo shell`. Bot
   promovido temporalmente a `base.group_system` para Bloque C
   (auditar `ir.module.module`); tightening de ACL pendiente.
10. ✅ `.env` del agente configurado (`ODOO_URL=http://localhost:19069`,
    `ODOO_FORCE_XMLRPC=1` mientras `_json2` no esté arreglado).
    `/onboard` ejecutado: 5 verde, 3 amarillo, 1 rojo (módulos sin
    instalar, esperado). Agente operativo contra Odoo 19 real.

### Bloque C — Bootstrap funcional (primer uso real del agente)

11. ✅ Fase 4.1 (instalación de módulos)
12. ✅ Fase 4.2 (empresa + idiomas + chart template)
13. ✅ Fase 4.2.1 (skill `holded-export` MVP solo-lectura)
14. ✅ Fase 4.2.2 (dump real de Holded de inpr3mium ejecutado;
    3 bugs del cliente arreglados durante el proceso; hallazgos
    documentados en `migration-from-holded.md`)
15. ⏸ Fase 4.3 (diarios, secuencias, posiciones fiscales — informado
    por el dump de 4.2.2)
16. ⏸ Fase 4.4 (bot user + permisos + record rules)
17. ⏸ Fase 4.5 (EDI: certificado + entornos)
18. ⏸ Fase 4.6 (smoke test: primera factura)
19. ⏸ Fase 4.7 (commit + bitácora)

### Bloque D — Migración de datos

20. ⏸ Fase 5.1 (diseño ETL Holded → Odoo, basado en el dump de 4.2.2)
21. ⏸ Fase 5.3 (validación con 2024+2025; lado escritura: scripts
    ad-hoc o nueva skill `holded-to-odoo`)
22. ⏸ Fase 5.4 (histórico completo + año en curso)
23. ⏸ Fase 5.5 (cutover día D)

### Bloque E — Futuro

24. ⏸ Fase 6 (fedefarma) — diferida.

---

## Histórico de cambios

| Fecha | Bloque/Fase | Cambio |
|-------|-------------|--------|
| 2026-05-10 | Bloque A pasos 1-4 | Limpieza Ikigai → multi-tenant + onboarding + /onboard. Commit `76ab81904`. |
| 2026-05-10 | Bloque A paso 5 (Fase 4.0) | `profile.yaml` de inpr3mium relleno con datos reales (NIF, plan, flags, dirección). README + migration plan actualizados. Commit `79f1acded`. |
| 2026-05-10 | Bloque B paso 7 (Fase 3) | Runbook `doodba-bootstrap.md` con Modo A (Docker local) + Modo B (gcloud). Añadidos `infra/README.md` y `infra/secrets.md`. |
| 2026-05-10 | Lateral (no roadmap) | `docs/infra/scaling.md` — guía de buenas prácticas de escalado Odoo 19 (workers, gevent, cron dedicado, Nginx, PG bajo carga, filestore externo, multi-nodo, `queue_job`, monitorización). Agnóstica al tenant; referencia para `fedefarma`. `Próximo paso` no cambia. |
| 2026-05-10 | Bloque B pasos 8-10 | Modo A ejecutado end-to-end: doodba 9.5.0 + Odoo 19 + PG16 corriendo, DB `inpr3mium_dev`, bot uid=8 con API key, `.env` configurado. `/onboard`: 5🟢 3🟡 1🔴 — agente conectado. Bloqueantes para Bloque C identificados (bug `_json2`, campos renombrados Odoo 19, 6 módulos OCA missing). |
| 2026-05-11 | Bloque C pre-flight | Auditoría OCA 19.0 de los 6 módulos missing vía `oca-module-scout` (paralelo). Solo `l10n_es_facturae` (19.0.1.0.0) está disponible. `l10n_es_aeat_sii_oca` eliminado del profile (inpr3mium no es gran empresa; fedefarma sí lo necesitará — memoria guardada). `mod232`, `verifactu_oca` (obligatorio 2027, no 2026), `mis_builder`, `sepa_credit_transfer`, `sepa_direct_debit` movidos a nuevo bloque `deferred_modules` con razón y `revisit_on`. Template de tenant actualizado con la convención. Commit `ddfde7ddb`. |
| 2026-05-11 | Bloque C Fase 4.1 | Install de los 12 `expected_modules` completado (state=installed). Camino largo: descubrir 3 repos OCA faltantes (`reporting-engine`, `server-ux`, `community-data-files`), 9 módulos adicionales en `addons.yaml` para cerrar closure de `depends`, 5 pip pkgs en `pip.txt`, `invoke img-build` para rebuild image, chown del filestore (UID mismatch `exec` vs `run --rm`). DB final: 75 módulos installed, 0 colgados. Gotchas en memoria, runbook actualizado, profile/addons.yaml/pip.txt persistidos. |
| 2026-05-11 | Restructura plan | Insertada Fase 4.2.1 entre 4.2 y 4.3: skill `odoo-data-migration` MVP solo-lectura para dumpear Holded antes de configurar diarios/secuencias. Decisión diferida en Fase 5.2 (`¿abrir cuarto skill?`) resuelta anticipadamente: SÍ, ahora en 4.2.1 lado-lectura; 5.3 completa lado-escritura. Numeración del Bloque C/D ajustada. Commit `99e0e7ea0`. |
| 2026-05-11 | Bloque C Fase 4.2 | Company id=1 reconfigurada con datos legales reales (Inteligencia del negocio pr3mium S.L., NIF, Spain/Barcelona, dirección y contacto). Chart `es_pymes` cargado (51 generic_coa → 646 PGCE Pymes). Idiomas es_ES + ca_ES activos. Bot tz Europe/Madrid + grupos account/partner manager (group_system conservado para 4.3). `web.base.url.freeze=True`. Gotchas nuevos: chart template codes en Odoo 19 son strings cortos (`es_pymes`), no XML-IDs; `try_loading` via XML-RPC tiene bug en arg posicional — usar `odoo shell`. |
| 2026-05-11 | Bloque C Fase 4.2.1 | Skill `holded-export` creada (renombrada desde `odoo-data-migration` para mejor encaje multi-origen: una skill por origen externo). Cliente HTTP read-only con whitelist de 28 endpoints GET, backoff 429/5xx, masking de API key, test que asserta ausencia de verbos de escritura. Scraper vendoriza 59 `.md` de developers.holded.com (376 KB offline). Scripts `inspect/export/dump_summary` end-to-end. 68/68 tests offline ok. `.env.example` ampliado con `HOLDED_API_KEY` + `HOLDED_API_BASE`. `.gitignore` excluye `docs/tenants/*/holded-export/`. Dump real pendiente de configuración local de la API key. |
| 2026-05-11 | Bloque C Fase 4.2.2 (preparado) | API key de Holded rotada por el operador tras incidente menor (key compartida en chat → revocada en Holded → Settings → Developers, generada nueva, persistida en `.env` local). Skill lista para ejecutar el dump. Plan de ejecución documentado paso a paso en `Fase 4.2.2` (7 pasos: smoke test → inspect → confirmar plan → dump completo → validar → inspección humana → commit). Próxima sesión puede retomar leyendo solo `docs/PLAN.md`. |
| 2026-05-11 | Bloque C Fase 4.2.2 (ejecutada — 1er pase) | Primer dump de inpr3mium: 43.4 MB / 490 docs / 439 PDFs. Operador detectó que SOLO contenía datos de 2026: el endpoint `/documents` de Holded SIN filtro de fechas devuelve únicamente el año en curso. 4º bug encontrado. |
| 2026-05-11 | Bloque C Fase 4.2.2 (ejecutada — histórico completo) | Dump real definitivo: **969 MB** en `docs/tenants/inpr3mium/holded-export/2026-05-11/` (gitignored). 3.363 contactos + 1.569 productos + 440 servicios + 148 cuentas de gasto + 103 taxes + 708 pagos + 12 tesorerías + 85 remesas + 38 saleschannels + 16 numbering series + **12.212 documentos** (3.430 invoice + 678 creditnote + 7.998 purchase + 69 purchaserefund + 34 proform + 3 estimate) + 2.250 asientos contables (histórico 2018-2026 chunkeado por años) + **7.489 PDFs** (3.430 invoice 142.6 MB + 4.059 purchase 801.4 MB; 3.939 purchases sin PDF = asientos manuales). errors.jsonl: 0 líneas. 4 bugs del cliente arreglados durante el proceso: (1) `paginate()` sin `page_size` capaba a 500 items; (2) paths `/warehouse` y `/expensesaccount` devuelven HTML SPA — reales `/warehouses` y `/expensesaccounts` plurales; (3) `dailyledger` ventana ≤ 1 año, chunking auto por años; (4) `/documents` sin starttmp/endtmp devuelve solo año en curso, ahora chunking auto por años con defaults sensatos (2018-01-01 → now). 68/68 tests offline OK. `migration-from-holded.md` actualizado con volúmenes reales + 3 tablas (sequences, mapeo IVA, cuentas de gasto). Próximo: Fase 4.3. |

---

## Notas operativas

- **Multi-tenant**: cada cliente/sociedad tiene su perfil bajo
  `docs/tenants/<slug>/`. El tenant activo se selecciona con la env
  var `ODOO_AGENT_TENANT`.
- **Skills agnósticas**: las 4 skills (`odoo-accounting-es`,
  `odoo-functional-admin`, `odoo-module-admin`, `holded-export`) no
  contienen datos específicos del cliente — todo viene del
  `profile.yaml` (skills Odoo) o de variables de entorno (`holded-export`).
- **Vendor docs**: la documentación oficial de Odoo está en
  `vendor/odoo-docs/` como referencia de solo lectura. Buscar ahí con
  Grep/Read antes de WebFetch.
- **Política de commit**: tras cada paso completado, commit con
  mensaje siguiendo el estilo `[TAG] área: descripción`. Tags
  habituales: `[ADD]`, `[IMP]`, `[FIX]`, `[REF]`, `[I18N]`.
