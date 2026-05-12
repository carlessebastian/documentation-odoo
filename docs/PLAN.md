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

- **Última actualización**: 2026-05-12 (Fase 5.1 — paso 0a/0b loaders
  **ejecutados en real**: 148 expensesaccount + 38 saleschannels →
  186 `account.account` con ext_id `__holded__.account_<accountNum>`
  creados; idempotencia verificada con 2ª pasada; snapshot
  `2026-05-12_fase-5.1-paso0.json`)
- **Última fase completada**: **Bloque D — Fase 5.1 paso 0 (subcuentas
  PGCE pre-load, ejecución real)**.

## Para retomar en una sesión nueva

Leer en este orden (regla en `CLAUDE.md`):

1. **`docs/PLAN.md`** — este archivo, fase actual y próximo paso.
2. **`docs/tenants/inpr3mium/profile.yaml`** — datos del tenant.
3. **`docs/tenants/inpr3mium/memory/MEMORY.md`** — índice 8 archivos
   con todo el conocimiento acumulado sobre inpr3mium (workspace
   farmapremium, tax mapping, treasury, sequences, EDI, decisions,
   dump-analysis 2026-05-11).
4. **`docs/tenants/inpr3mium/migration-from-holded.md`** — plan ETL.

Lo que la siguiente sesión necesita saber resumido aquí:

- **Estado funcional**: instancia local Odoo 19 con fundaciones
  financieras completas (Bloque D 5.0 cerrado) **+ diseño ETL
  detallado (5.1 redactado) + scaffolding `etl/` entregado**.
  `holded_resolvers.py` con 4 resolvers reales (no stubs) + cache +
  helpers puros; **65/65 tests offline verdes**;
  `tax_reclassification.yaml` esqueleto con schema comentado
  (rellena operador). 12 bank/sale/purchase journals operativos.
  Defaults company alineados con realidad inpr3mium
  (services-heavy: 21% S + 705000). Lista para arrancar 5.3
  (validación subset 2024+2025).
- **Próxima acción**: pre-trabajo para **Fase 5.3**:
  1. ~~Run real del paso 0a + 0b~~ ✅ ejecutado 2026-05-12. 186 ext_ids
     `__holded__.account_*` viven en Odoo (148 expense + 38 income).
     account_type heredado del padre PGCE (131 expense, 11 expense_other,
     6 expense_depreciation, 38 income). Distribución coherente con
     parents 60X/62X/63X/64X/65X/67X/68X/70X. Idempotencia probada.
  2. Sesión con operador para rellenar
     `docs/tenants/inpr3mium/etl/tax_reclassification.yaml` con
     reglas catch-all `p_iva_exento` (sample 100 docs aleatorios
     de los 2.306 — ver 5.1 sección "Riesgos #1"). **Bloquea
     loader 4 (purchases)**.
  3. Escribir loaders 1 (partners), 2 (products) consumiendo
     `HoldedResolvers`. Empezar con `loader_partners.py` (3.363 +
     1 unknown) en dry-run.
- **No aplicar** sequences pre-loading hasta cutover Fase 5.5.
- **Fase 5.1 (esta sesión, 2026-05-11)**: redactada sección "ETL Fase
  5.1 — Diseño detallado" en `migration-from-holded.md` (526 líneas
  añadidas, doc total 1.030). Cubre estrategia ext_id por resource,
  4 resolvers (partner/tax/journal/account) con caveats conocidos
  (1.149 contactId no resolubles → placeholder único; catch-all
  `p_iva_exento` con `tax_reclassification.yaml`; PR- vía
  `account.move.reversal`; subcuentas 11-dig autocreadas), orden de
  carga 11 pasos con dependencias, transformaciones por modelo con
  pseudocódigo (partners, products, account.move, account.payment,
  dailyledger filtrado, PDFs), validaciones post-load (SQL cuadre
  por journal/partners/IVA trimestral/conteos finales), decisión
  scripts ad-hoc en `docs/tenants/inpr3mium/etl/` (no skill nueva),
  6 riesgos con mitigación para 5.3. Entregables pendientes:
  scaffolding `etl/` + `tax_reclassification.yaml` con operador +
  pre-load dry-run subcuentas.
- **Fase 5.0 (esta sesión, 2026-05-11)**: 4 bank journals creados
  (Santander id=19/SAN, BBVA id=20/BBVA, Sabadell id=21/SAB, Qonto
  id=22/QON) cada uno con `account.account` 11-dig hijo de `572000`
  como `default_account_id`, `suspense_account_id=388`, y
  `res.partner.bank` con IBAN linkado vía
  `account.journal.bank_account_id`. 6 cuentas `521x` para tarjetas
  (3 personales + 3 TELETAC) creadas como `liability_current` sin
  journal. Payment term `15 Days` (id=2) seteado como default
  empresa para `property_payment_term_id`/`property_supplier_payment_term_id`
  vía `ir.default`. Defaults empresa actualizados: sale tax `21% S`
  (id=6), purchase tax `21% S` (id=8), income account `705000` (id=551).
  3 gotchas Odoo 19 añadidos a agent memory: `ir.property` eliminado
  (→ `company_dependent` + `ir.default`); `res.partner.bank.journal_id`
  es One2many (link vía `account.journal.bank_account_id`); ir.default
  + properties de empresa requieren `group_system` (escalación shell).
  Operaciones que requirieron `odoo shell`: `ir.default.create` x2 +
  `res.company.write` de los 3 defaults. BNK1 (id=12, account
  572001 id=694) placeholder de l10n_es_pymes queda activo sin
  movs — archivar tras confirmación. Cuentas omitidas: Visa
  Santander Carles, línea descuento Sabadell, TRASHOLDED, BBVA1,
  `55500000007`. Snapshot
  `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-5.0.json`.
- **Fase 4.7 (previa)**: commit `4587fabe9` cerrando Bloque C.
  Sello "inpr3mium lista para facturar en modo local" puesto.
- **Fase 4.6 (previa)**: **Bloque C — Fase 4.6 (smoke test
  contable)**. 3 moves posteados end-to-end sobre las taxes definitivas
  de Fase 4.5b: `out_invoice` A-/2026/00001 (1.210€, IVA repercutido
  21% → subcuenta `47700000021` ✅); `in_invoice` PB-/2026/05/0001
  (605€, IVA soportado 21% → subcuenta `47200000021` ✅); `out_refund`
  AC-/2026/00001 (1.210€, vía `account.move.reversal` con
  `reversed_entry_id=2`, prefijo `AC-` y journal_id=13 confirmados,
  numeración independiente del `A-`). 2 partners test creados (ESB
  ficticios con DC válido). Reporting cuadra: D=1.815 C=1.815 sobre 6
  cuentas (430 cliente, 705 ingreso, 477 IVA rep, 410 proveedor, 629
  gasto, 472 IVA sop). Snapshot
  `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.6.json`.
  Hallazgo (no bloqueante): los 3 journals usan formatos de
  `sequence` distintos por defecto en Odoo 19 — A- y AC- usan
  `CODE/YYYY/NNNNN` mientras que PB- usa `CODE/YYYY/MM/NNNN` (mes
  intercalado). Es comportamiento por defecto de `account.journal`
  por tipo (sale vs purchase) en Odoo 19; si fedefarma o futuras
  auditorías AEAT requieren formato uniforme, se ajustará vía
  `sequence_override_regex` en Fase 5. Para inpr3mium AEAT es
  agnóstico: lo que cuenta es que la numeración sea correlativa sin
  huecos dentro del año fiscal, y eso se cumple. **Cierra Bloque C
  excepto 4.7 (commit + bitácora)**.
- **Fase 4.5b (previa)**: **Bloque C — Fase 4.5b (mapeo de
  impuestos Holded → Odoo)**. Análisis cruzado del dump (12.212 docs)
  revela que inpr3mium realmente usa 17 tax keys (de las 103 del
  catálogo Holded). Hallazgo crítico: `s_iva_exento` (998 líneas) NO
  es exención Art.20 sino **ISP en ventas Art.84.Uno.2.g LIVA**
  (cliente principal BIDAFARMA). Aplicado: 14 subcuentas analíticas
  creadas (47200000021/121/010/004/000, 47700000021/010/004/000/121/221,
  47510000001/005/010) hijas de 472000/477000/475100; 16 taxes con
  `description` anotada `[holded: <key>]` para trazabilidad ETL; 34
  `account.tax.repartition.line.account_id` reescritos a las
  subcuentas; doble anotación ISP/intracom verificada en taxes
  `21% RC` (id=112), `21% EU S` (id=9), `21% EU G` (id=10); 27 taxes
  archivadas (6 SE/recargo equivalencia + 21 rates 2%/5%/7.5% no
  usados). Snapshot en
  `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.5b.json`.
  Mapeo completo documentado en `migration-from-holded.md` (sección
  "Mapeo de impuestos Holded → Odoo"). Casos heterogéneos
  documentados como deuda técnica para ETL Fase 5
  (`p_iva_exento` catch-all, 2 líneas anómalas).
- **Fase 4.4 (previa)**: **Bloque C — Fase 4.4 (bot tightening +
  record rules + snapshot)**. Fase 4.5 (EDI cert) **diferida**: sin
  obligación regulatoria hoy (SII no aplica, Veri\*Factu obligatorio
  desde 2027) y sin factura a Administración Pública pendiente. Se
  reabre cuando aparezca driver de negocio. Bot uid=8 reducido de
  `base.group_system` a perfil least-privilege: `base.group_user` +
  `base.group_erp_manager` + `base.group_multi_company` +
  `base.group_partner_manager` + `account.group_account_manager` +
  `analytic.group_analytic_accounting` (6 grupos). Validado: bot
  puede leer/escribir partners, account.move (draft), ir.rule,
  ir.model.data, ir.module.module, journals, fiscal positions,
  analytic plans. Únicas operaciones que pierde: instalar módulos y
  modificar `ir.config_parameter` (requieren `group_system` —
  escalación temporal via `odoo shell` cuando se necesite). Regla
  multi-company global de `res.partner`: Odoo core ya provee una con
  dominio más sofisticado (id=2, maneja `partner_share` +
  `parent_of`), no se crea ninguna nueva. Snapshot en
  `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.4.json` (1
  company, 2 users, 12 journals, 29 fiscal positions, 2 analytic
  plans, 13 record rules en modelos críticos, 75 modules
  installed). Parchados 5 scripts del agente con bugs Odoo 19:
  `groups_id`→`group_ids` (group_assign, audit_admin_state,
  _drift, user_provision), `account.journal.sequence_id` y
  `res.groups.category_id` removidos (audit_admin_state). 4 gotchas
  Odoo 19 nuevos en memoria.
- **Fase 4.3 (previa)**: **Bloque C — Fase 4.3 (diarios,
  secuencias, posiciones fiscales)**. 8 `account.journal` configurados
  en company_id=1 preservando continuidad Holded: 6 sale (A-, AC-,
  AF-, KD-, FVU-, L-) + 2 purchase (PB-, PI-). INV stock → A-, FACTU
  stock → PB-. PB- con `refund_sequence=True` (69 purchaserefund PR-
  bajo volumen). AC- como diario separado (no refund_sequence en A-)
  porque Holded usa AC- tanto para creditnote como para rectificativas
  positivas. Posiciones fiscales: `l10n_es_pymes` ya creó las 4
  necesarias (Intra-community, Extra-community, Equivalence surcharge,
  ISP) + 10 IRPF withholding — sin crear nada nuevo. Plan analítico
  "Granularidad gasto" (id=2) creado para futura migración. Script
  `journal_setup.py` parchado para Odoo 19 (eliminado `sequence_id` y
  `ir.sequence`; en Odoo 19+ el `code` del journal es directamente el
  prefijo). Detalle completo en `migration-from-holded.md` sección
  "Configuración Odoo aplicada en Fase 4.3".
- **Fase 4.2.2 (previa)**: **Bloque C — Fase 4.2.2 (dump real de
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
- **Próximo paso**: con paso 0 cerrado, quedan dos bloques antes de
  arrancar **Fase 5.3** (validación subset 2024+2025):
  1. **`tax_reclassification.yaml`** con operador: 100 docs aleatorios
     de los 2.306 con `p_iva_exento` para validar reglas de
     reclasificación por país/proveedor (heurísticas SaaS extra-UE
     vs Cheque Dejeuner / Quirón / RENFE / renting). Sin esto, el
     loader 4 (purchases) no puede correr limpio. **Bloqueante**.
  2. **Loaders 1 (partners) y 2 (products)** en dry-run consumiendo
     `HoldedResolvers`. Empezar con `loader_partners.py` (3.363 +
     1 unknown). Pueden avanzar en paralelo al #1.

  Fase 4.5a (EDI cert) sigue diferida sin driver de negocio. Fase
  5.2 cerrada anticipadamente en 4.2.1.

  ---

  Plan 4.6 (ejecutado en 2026-05-11, conservado como referencia):
  1. Crear `res.partner` de prueba (cliente español ficticio con NIF
     válido formato `ESB...`).
  2. Crear `account.move` `out_invoice` en diario `A-` (id=7) con 1
     línea de servicio + IVA 21% (`s_iva21b`). Verificar que la
     posición fiscal `ES Domestic` se aplica automáticamente.
  3. `action_post()` → comprobar que `name` recibe el prefijo `A-` y
     se crea `account.move.line` por cada partida (base + IVA +
     contrapartida cliente).
  4. Crear `account.move` `in_invoice` en diario `PB-` (id=8) con
     proveedor español y línea de gasto + IVA 21% soportado
     (`p_iva21_bc`).
  5. `action_post()` ídem.
  6. Verificar reporting básico: balance refleja deuda cliente +
     deuda con proveedor; estado de resultados muestra ingreso +
     gasto.
  7. Probar rectificativa (out_refund) en diario `AC-` (id=13) con
     `move_type='out_refund'` y `reversed_entry_id` apuntando a la
     factura del paso 2 — validar que el numero `AC-...` se genera
     independiente del `A-...`.
  8. Limpiar (`unlink` de los 4 moves + 1 partner test) o dejar como
     "smoke test reference" según convenga. Probablemente dejar todo
     y resetear en Fase 5 cuando se cargue el histórico real.
  9. Snapshot `2026-MM-DD_fase-4.6.json` documentando estado
     post-smoke.

  Si el paso 7 falla por que Odoo no acepta crear out_refund en
  journal distinto al de la factura original, replantear la decisión
  AC-separado vs refund_sequence en A- (documentada en
  `migration-from-holded.md`).
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

- ✅ **4.3** Diarios + posiciones fiscales + plan analítico (2026-05-11).
  8 `account.journal` creados/renombrados en company_id=1 preservando
  prefijos de Holded para auditoría AEAT: 6 sale (A-, AC-, AF-, KD-,
  FVU-, L-) + 2 purchase (PB-, PI-). Stock INV→A-, FACTU→PB-. Decisión
  `AC-` como diario separado (no `refund_sequence` en `A-`) porque
  Holded mezcla creditnote + rectificativas de aumento en AC-. `PB-`
  con `refund_sequence=True` para PR- (69 purchaserefund). Posiciones
  fiscales: `l10n_es_pymes` ya creó las 4 esenciales + 10 IRPF — sin
  acción RPC. Plan analítico "Granularidad gasto" (id=2) creado para
  Fase 5. Script `journal_setup.py` parchado para Odoo 19 (gotcha:
  `account.journal.sequence_id` desapareció — el `code` es el prefijo,
  `refund_sequence` es boolean). `account.analytic.plan` ya no tiene
  `company_id` (cross-company en Odoo 19). Bot escalado con
  `analytic.group_analytic_accounting`.
- ✅ **4.4** Bot tightening + record rules + snapshot (2026-05-11).
  Bot uid=8 reducido a 6 grupos least-privilege
  (`base.group_user` + `base.group_erp_manager` +
  `base.group_multi_company` + `base.group_partner_manager` +
  `account.group_account_manager` +
  `analytic.group_analytic_accounting`). Regla multi-company global
  de `res.partner` ya provista por Odoo core (id=2, dominio
  con `partner_share` + `parent_of` — más sofisticado que el del
  runbook). Snapshot manual en
  `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.4.json`. 5
  scripts del agente parchados para Odoo 19 (`groups_id` → `group_ids`,
  `category_id` y `sequence_id` removidos). 4 gotchas nuevos en
  memoria. Trade-offs aceptados: bot no puede escribir
  `ir.config_parameter` ni instalar módulos (requiere `group_system`,
  escalación temporal via shell cuando se necesite).
- 🔵 **4.5a** **DIFERIDA — no bloqueante para inpr3mium**. EDI:
  certificado digital + entornos test/prod en módulos AEAT. Razón:
  inpr3mium NO está obligada a SII (no es gran empresa ni REDEME), y
  Veri\*Factu no es obligatorio hasta 2027 (memoria
  `project_tenant_edi_obligations.md`). El módulo `l10n_es_facturae`
  está instalado pero solo se usa si el operador tiene que facturar a
  Administración Pública (FACe) — no es el caso hoy. Pendiente
  operativo aislado: el operador descarga certificado FNMT-CERES con
  DNI electrónico y lo importa cuando se acerque 2027 o cuando facture
  a un organismo público. Decisión: **saltamos 4.5a hasta que haya un
  driver de negocio real** (factura a Admin Pública o aproximación
  2027). NO bloquea 4.6, 4.7 ni Fase 5.
- ✅ **4.5b** Mapeo de impuestos Holded → Odoo (2026-05-11). Cruzado
  dump del 2026-05-11 contra catálogo Holded: 17 keys realmente usadas
  de las 103 disponibles. Aplicado: 14 subcuentas analíticas creadas
  (47200000021/121/010/004/000, 47700000021/010/004/000/121/221,
  47510000001/005/010); 16 taxes mapeadas y anotadas con
  `description [holded: <key>]`; 34 `account.tax.repartition.line`
  rewired a las subcuentas; doble anotación ISP/intracom verificada
  en taxes `21% RC` (id=112), `21% EU S` (id=9), `21% EU G` (id=10);
  27 taxes archivadas (RE + tipos 2%/5%/7.5%). Hallazgo crítico:
  `s_iva_exento` (998 líneas, BIDAFARMA) es ISP venta Art.84.Uno.2.g,
  NO Art.20 → mapeada a `0% RC` (id=109). Snapshot
  `2026-05-11_fase-4.5b.json`. Detalle completo en
  `migration-from-holded.md` sección "Mapeo de impuestos".
- ✅ **4.6** Smoke test contable (2026-05-11). 3 moves end-to-end
  posteados sobre las taxes Fase 4.5b: `out_invoice` A-/2026/00001
  (1.210€, IVA 21% → subcuenta `47700000021` ✅), `in_invoice`
  PB-/2026/05/0001 (605€, IVA 21% → subcuenta `47200000021` ✅),
  `out_refund` AC-/2026/00001 (1.210€) vía
  `account.move.reversal` con `reversed_entry_id=2`, prefijo `AC-`
  y `journal_id=13` verificados — confirmación de que la
  numeración del refund es independiente del A- original.
  2 partners ES creados (`ESB12345674` cliente,
  `ESB87654323` proveedor; DC verificado). Reporting cuadra:
  D=1.815 C=1.815 sobre 6 cuentas. Pipeline `account.move` →
  `action_post()` → `account.move.line` con subcuentas correctas =
  OK. Sin SII test (4.5a diferida). Snapshot
  `2026-05-11_fase-4.6.json`.
- ✅ **4.7** Checkpoint y commit con bitácora del bootstrap
  (2026-05-11, commit `4587fabe9`). Sello "inpr3mium lista para
  facturar en modo local" puesto. Bloque C completo. Pasamos a
  Bloque D.

### Fase 5 — Migración de datos desde Holded

**Objetivo**: importar maestros y, según scope acordado, histórico
completo + año en curso. Validación previa con subset 2024-2025.

- ✅ **5.0** **Fundaciones financieras pre-ETL** (ejecutado
  2026-05-11). Resultado: 4 bank journals + 6 cuentas 521x +
  payment term default + defaults company actualizados. Pre-loading
  de `ir.sequence.number_next` (5.0.2) DIFERIDO al cutover 5.5.
  Snapshot `2026-05-11_fase-5.0.json`. Plan original conservado
  abajo como referencia:

  **5.0.1 — Bank journals** (4 reales + 1 línea crédito):
  Crear `account.journal` tipo `bank` para cada cuenta Holded
  productiva, con `res.partner.bank` IBAN asociado y subcuenta
  analítica del grupo `5720XXXXXXX` replicando la granularidad
  Holded (mismo patrón que Fase 4.5b con IVA: respetar 11 dígitos
  para continuidad con el histórico). Mapeo treasury Holded →
  journal Odoo:

  | Treasury Holded | Tipo | IBAN | Holded acct (PGCE 11d) | Acción Odoo |
  |---|---|---|---|---|
  | Santander | bank | ES15 0049 3764 3127 1410 9882 | `<pendiente>` | journal + `res.partner.bank` + subcuenta |
  | Banco Sabadell | bank | ES14 0081 0646 3700 0123 4632 | `<pendiente>` | idem |
  | Qonto | bank | ES21 6888 0001 6002 2535 0289 | `<pendiente>` | idem |
  | BBVA | bank | ES65 0182 8682 2602 0012 8502 | `<pendiente>` | idem |
  | Linea descuento Sabadell | bank | — | `<pendiente, prob. 52X>` | journal con cuenta `5208`/`5209` (deudas C/P por desc. efectos) |
  | Visa BBVA Carles | card | — | n/a | `account.journal` cash o cuenta `552`/`555` socio |
  | Visa Santander Carles | card | — | n/a | idem |
  | Visa Sabadell Carles | card | — | n/a | idem |
  | Sabadell Geraldine MC | card | — | n/a | idem (titular distinto) |
  | BBVA1 | bank | — | `<pendiente>` | revisar dailyledger; archivar si sin movs |
  | TRASHOLDED | bank | — | n/a (técnica) | **omitir**: equivale a `account.journal.suspense_account_id` Odoo |
  | `55500000007` | "bank" | — | `55500000007` | **NO es journal**: cuenta PGCE 555 "Partidas pendientes de aplicación" — registrar como `account.account` puro |

  **Decisión arquitectónica** (consistente con Fase 4.5b): replicar
  el patrón de 11 dígitos de Holded como subcuentas hijas de las
  cuentas PGCE Pymes raíz (`572000`, `552000`, `555000`). Mantener
  esto preserva continuidad con todos los asientos del histórico al
  cargar.

  **Heurística confirmada en dailyledger**: la posición 5-8 del
  código Holded `5720XXXX___` parece corresponder al **código de
  entidad bancaria** del Banco de España (4 dígitos): `0049`
  Santander, `0182` BBVA, `0081` Sabadell, `6888` Qonto. Sufijos
  `__XX` distinguirían cuenta dentro del banco. Validar con el
  operador antes de aplicar.

  **5.0.2 — Sequence pre-loading**: cargar
  `ir.sequence.number_next` de cada `account.journal` con los
  counters del dump +1, para no romper correlatividad AEAT:

  | Journal Odoo | Holded counter | `number_next` a setear |
  |---|---:|---:|
  | A- (id=7) | 9098 | 9099 |
  | AC- (id=13) | 1845 | 1846 |
  | L- | 1313 | 1314 |
  | FVU- | 14 | 15 |
  | KD- | 163 | 164 |
  | AF- | 14 | 15 |
  | PB- (id=8) | 12017 | 12018 |
  | PI- | 361 | 362 |
  | PB- refund_sequence (PR-) | 71 | 72 |

  **Crítico**: hacer esto **inmediatamente antes del cutover**
  (Fase 5.5), no antes del subset de validación (5.3). Si se hace
  antes, los moves de validación 5.3 consumirán los huecos `A-9099`,
  `A-9100`... y al borrarlos para cargar el histórico real quedarán
  huecos en la numeración (AEAT rechaza).

  **5.0.3 — Payment terms y defaults de empresa**:
  - Activar `account.payment.term` "15 Days" (id=2) como default de
    `res.company` (`property_payment_term_id`).
  - Confirmar default `account.tax` venta=`21% S` (id=6) y
    compra=`21% S` (id=8) ya en `account.fiscal.position` ES Domestic.
  - Default `account.account` ventas: decidir entre `705000 Services
    rendered` (servicios) vs `700000 Merchandise sold` (mercaderías)
    o ambas con tax_unit propio. inpr3mium = mix
    (consultoría + paquetes PLV) → ambas activas, default `705000`.

  **5.0.4 — Snapshot 5.0**: persistir mapeo treasury→journal en
  `docs/tenants/inpr3mium/snapshots/<YYYY-MM-DD>_fase-5.0.json`
  para que el ETL Fase 5.1+ resuelva `payment.treasury_id` →
  `account.payment.journal_id`.

  **Bloqueante para arrancar 5.0**: tabla `treasury_name → cuenta
  Holded 11 dig` la tiene el operador en Holded > Contabilidad >
  Plan contable (o en la propia configuración de cada cuenta de
  tesorería). Pendiente de pasarla.

- ✅ **5.1** **Diseño ETL detallado** (ejecutado 2026-05-11). Sección
  "ETL Fase 5.1 — Diseño detallado" añadida a
  `migration-from-holded.md` (526 líneas). Cubre estrategia ext_id,
  4 resolvers (partner/tax/journal/account), orden de carga 11
  pasos con dependencias, transformaciones por modelo con
  pseudocódigo, validaciones SQL post-load, decisión scripts
  ad-hoc en `docs/tenants/inpr3mium/etl/` (no skill nueva), 6
  riesgos con mitigación. Entregables siguientes (pre-trabajo
  5.3): `tax_reclassification.yaml` con operador + scaffolding
  `etl/` + pre-load dry-run subcuentas.
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
15. ✅ Fase 4.3 (8 diarios + posiciones fiscales validadas + plan
    analítico; script journal_setup.py parchado para Odoo 19)
16. ✅ Fase 4.4 (bot tightening + snapshot; 5 scripts del agente
    parchados Odoo 19)
17. 🔵 Fase 4.5a (EDI cert) — **DIFERIDA**, sin driver de negocio
    (inpr3mium no usa SII; Veri\*Factu obligatorio solo desde 2027).
    Volveremos cuando se acerque 2027 o si surge factura a Admin
    Pública.
18. ✅ Fase 4.5b (mapeo impuestos Holded → Odoo: 14 subcuentas
    creadas, 16 taxes mapeadas con anotación `[holded: <key>]`,
    27 taxes archivadas, doble anotación ISP/intracom verificada)
19. ✅ Fase 4.6 (smoke test contable: 3 moves end-to-end posteados
    sobre subcuentas correctas + balance cuadrado + refund AC-
    independiente del A- via `account.move.reversal`)
20. ✅ Fase 4.7 (commit `4587fabe9` cerrando Bloque C; sello
    "inpr3mium lista para facturar en modo local" puesto)

### Bloque D — Migración de datos

20. ✅ Fase 5.0 (fundaciones financieras pre-ETL: 4 bank journals
    Santander/BBVA/Sabadell/Qonto + 6 cuentas 521x tarjetas +
    payment term 15 Days default + tax/income defaults company.
    Sequence pre-loading diferido a cutover 5.5)
21. ✅ Fase 5.1 (diseño ETL Holded → Odoo redactado en
    `migration-from-holded.md`: ext_id strategy + 4 resolvers +
    11-step load order + transformaciones por modelo + validaciones
    SQL + 6 riesgos. Implementación en `docs/tenants/inpr3mium/etl/`)
22. ⏸ Fase 5.3 (validación con 2024+2025; pre-trabajo:
    `tax_reclassification.yaml` con operador + scaffolding loaders +
    pre-load dry-run paso 0)
23. ⏸ Fase 5.4 (histórico completo + año en curso)
24. ⏸ Fase 5.5 (cutover día D)

### Bloque E — Futuro

25. ⏸ Fase 6 (fedefarma) — diferida.

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
| 2026-05-11 | Bloque C Fase 4.5 (diferida) | Decisión: saltar 4.5 (EDI cert) sin acción operativa hoy. Motivo: inpr3mium no es gran empresa ni REDEME (no obligada a SII), Veri\*Factu no es obligatorio hasta 2027, y no factura a Administración Pública (único caso que activaría FACe/FacturaE de forma inmediata). Coste de instalar el certificado FNMT hoy = 0 valor de negocio. Cuando aparezca un driver real (cliente AAPP o se acerque 2027), volvemos a abrir 4.5 — el módulo `l10n_es_facturae` ya está instalado, solo falta importar el .p12 y configurar entornos. Avance al runbook: pasamos directos a 4.6 (smoke test contable sin SII). |
| 2026-05-11 | Bloque C Fase 4.4 | Bot uid=8 tightenado: quitado `base.group_system`, dejados 6 grupos least-privilege (`base.group_user` + `base.group_erp_manager` + `base.group_multi_company` + `base.group_partner_manager` + `account.group_account_manager` + `analytic.group_analytic_accounting`). Validado vía RPC: bot puede CRUD partners, draft account.move, ir.rule, leer ir.model.data + ir.module.module + journals + fiscal positions + analytic plans. Pierde `ir.config_parameter` y instalar módulos (acepta escalación temporal). Regla multi-company global de `res.partner` ya existe en Odoo core (id=2, dominio con `partner_share` + `parent_of` — más correcto que el del runbook). Snapshot manual en `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.4.json` (1 company / 2 users / 12 journals / 29 FPs / 2 analytic plans / 13 record rules sobre modelos críticos / 75 modules installed). 5 scripts del agente parchados para Odoo 19: `groups_id`→`group_ids` (group_assign, audit_admin_state, _drift, user_provision), `res.groups.category_id` removido (audit_admin_state), `account.journal.sequence_id` removido (audit_admin_state). 4 gotchas Odoo 19 nuevos en memoria: cambios grupos requieren restart worker HTTP; perfil mínimo bot post-tightening; el runbook .claude/skills/CLAUDE.md está desactualizado al prescribir un perfil demasiado restrictivo; bugs históricos en scripts. |
| 2026-05-11 | Bloque C Fase 4.5b | Mapeo impuestos Holded → Odoo. Cruzado `products[].taxes` de los 12.212 docs del dump contra catálogo Holded: 17 keys realmente usadas de las 103 disponibles. Hallazgo crítico: `s_iva_exento` (998 líneas, cliente principal BIDAFARMA) es **ISP en ventas Art.84.Uno.2.g LIVA**, NO exención Art.20 — descripción literal de las facturas lo confirma; mapeada a `0% RC` (id=109). Aplicado vía RPC: 14 subcuentas analíticas creadas hijas de 472000/477000/475100 (47200000021/121/010/004/000, 47700000021/010/004/000/121/221, 47510000001/005/010) replicando granularidad Holded; 16 taxes mapeadas y anotadas con `description [holded: <key>]` para trazabilidad ETL; 34 `account.tax.repartition.line.account_id` rewired a las subcuentas; doble anotación ISP/intracom verificada en `21% RC` (id=112, p_iva_invsuj), `21% EU S` (id=9, p_iva_adqintras_21), `21% EU G` (id=10, p_iva_adqintrab_21) — Odoo modela el devengado+soportado simultáneo con 2 repartition_lines (+input 100% / -mirror 100%) que sustituyen el `type:group` + `items:[_1,_2]` de Holded; 27 taxes archivadas (6 SE recargo equivalencia + 21 rates 2%/5%/7.5% no usados). Tags AEAT (casillas modelo 303) no se tocaron — vienen correctas de l10n_es_pymes. Casos heterogéneos documentados como deuda técnica para ETL Fase 5: `p_iva_exento` (2.306 docs catch-all: ISP extra-UE no detectada + Art.20 + renting), 2 líneas anómalas con `s_ret_19` en purchases. Snapshot `2026-05-11_fase-4.5b.json` (14 subcuentas + 16 taxes mapeadas + 27 archived + stats). Detalle completo en `migration-from-holded.md` sección "Mapeo de impuestos Holded → Odoo". |
| 2026-05-11 | Bloque D Fase 5.0 (planificación) | Audit cruzado dump↔UI Holded reveló brechas pre-ETL. Documentada nueva Fase 5.0 "Fundaciones financieras": (a) crear 4 bank journals reales (Santander/Sabadell/Qonto/BBVA) + 1 línea crédito Sabadell + cuentas auxiliares para 4 tarjetas (BBVA/Santander/Sabadell Carles + Sabadell Geraldine MC); (b) replicar granularidad 11-dig de Holded como subcuentas hijas de `572000`/`552000`/`555000` (consistente con Fase 4.5b para IVA); (c) pre-cargar `ir.sequence.number_next` con counters Holded +1 inmediatamente antes del cutover Fase 5.5; (d) activar `15 Days` como payment term default. Heurística detectada en dailyledger: posiciones 5-8 del código Holded 11-dig parecen código entidad BdE (`0049` Santander, `0182` BBVA, `0081` Sabadell, `6888` Qonto) — pendiente validar con operador. 3 cuentas Holded a omitir: TRASHOLDED (suspense técnica → `account.journal.suspense_account_id` Odoo), `55500000007` (NO es journal, es cuenta PGCE 555 "Partidas pendientes de aplicación"), BBVA1 (revisar y archivar si 0 movs). Memoria nueva: `feedback_dump_audit_flow_over_balances.md` (auditar estructura, no saldos puntuales que cambian al re-dumpear). Bloqueante: tabla `treasury_name → cuenta Holded 11d` pendiente de pasar el operador. |
| 2026-05-11 | Bloque D Fase 5.1 (loaders paso 0) | Loaders paso 0a + 0b entregados con shared `_loader_common.py`. `loader_expenseaccounts.py` y `loader_saleschannels.py` son thin wrappers (~60 lineas cada uno) que llaman a `load_accounts(client, dump_dir, source, dry_run=...)`. Logica compartida: lee JSONL `{id, name, accountNum, color}`, deriva padre PGCE via `derive_pgce_parent`, lookup batch de `account_type` del padre en una sola call, upsert via `ext_id_upsert.upsert` con xml-id `__holded__.account_<accountNum>` para idempotencia, CSV report en `<dump_dir>/.etl_reports/<source>_<mode>_<ts>.csv` con `{accountNum, name, parent_code, parent_type, ext_id, status, error, res_id}`. Bug detectado pre-run: `derive_pgce_parent` solo cubria 21 prefijos explicitos, dump real tenia 26 prefijos distintos en `expensesaccount` (incluye 630, 640, 650, 662, 670, 678, 680, 681, 693, 694 no listados) + 7090 en `saleschannels`. Refactor: solo dejar reglas explicitas para casos NO-trivialmente-`<3digits>000` (5720, 521, 472, 477, 4751); chapters 6/7 caen al fallback generico `<first3>000`. Tests actualizados: 65 -> 84 verdes. Nuevo `tests/test_loader_common.py` con FakeOdoo en memoria cubre dry-run (4 escenarios: all-create, existing-ext_id-update, unresolvable-parent, parent-missing-in-odoo) + CSV emission + saleschannels source + limit -> 95 tests verdes total. **Dry-run real contra Odoo local**: 148/148 expensesaccount + 38/38 saleschannels = 186/186 sin errores (todos los padres PGCE Pymes existen en la DB). Pendiente: run real (pospuesto a inicio Fase 5.3 con supervision operador). |
| 2026-05-11 | Bloque D Fase 5.1 (scaffolding) | Entregado scaffolding `docs/tenants/inpr3mium/etl/`: `holded_resolvers.py` con 4 resolvers reales (no stubs) — `resolve_partner` (cache por VAT + ext_id + placeholder `__holded__.contact__unknown`), `resolve_tax` (lookup `[holded: <key>]` + reglas `tax_reclassification.yaml` con prioridad country > partner_in > doc_type > default), `resolve_journal` (mapa prefijo→code Odoo hardcoded para 8 journals; rechaza PR-), `resolve_account` (lookup 11-dig + autocreate hijo de PGCE parent via `derive_pgce_parent`). 5 helpers puros (`normalize_vat` con heurística ES, `parse_journal_prefix` como tokenizer agnóstico, `derive_pgce_parent` por longest-prefix-match sobre 17 reglas PGCE, `partner_active_from_name` strip `(NO USAR)`, `iso_from_unix`). `ResolverStats` dataclass para telemetría. `tests/conftest.py` + `tests/test_holded_resolvers.py` (12 clases, **65 tests offline verdes en 0.04s**). README con tabla de estado de los 11 loaders + convenciones CLI uniformes (`--dump-dir`, `--dry-run`, `--limit`, `--resume`, `--batch-size`). `tax_reclassification.yaml` con schema comentado (default_tax_id, by_partner_country, by_partner_in, by_doc_type) y dos bloques esqueleto (p_iva_exento + s_ret_19) listos para que el operador rellene en bloque #1 del pre-trabajo 5.3. Siguiente: redactar `tax_reclassification.yaml` real con operador + escribir 11 loaders + `validate_etl.py`. |
| 2026-05-11 | Bloque C Fase 4.7 | Commit `4587fabe9` cerrando Bloque C: smoke test 4.6 + snapshot persistidos. Sello "inpr3mium lista para facturar en modo local" puesto. Próximo: Bloque D (Fase 5 — migración desde Holded). Fase 5.2 ya se cerró anticipadamente en 4.2.1 (skill `holded-export`). |
| 2026-05-11 | Bloque C Fase 4.6 | Smoke test contable end-to-end. 3 moves posteados sobre las taxes definitivas de 4.5b: out_invoice `A-/2026/00001` (1.210€, base 1.000 + IVA 21% repercutido a subcuenta `47700000021` ✅), in_invoice `PB-/2026/05/0001` (605€, base 500 + IVA 21% soportado a subcuenta `47200000021` ✅), out_refund `AC-/2026/00001` (1.210€) vía `account.move.reversal` con `reversed_entry_id=2`, prefijo `AC-` y `journal_id=13` confirmados — la numeración del refund es independiente del A- original. 2 partners ES test creados con DC válido (ESB12345674 cliente, ESB87654323 proveedor). Reporting cuadra: D=1.815 C=1.815 sobre 6 cuentas (430 cliente, 705 ingreso, 477 IVA rep, 410 proveedor, 629 gasto, 472 IVA sop). Snapshot `2026-05-11_fase-4.6.json` (2.2 KB). Hallazgo no bloqueante: Odoo 19 usa formato `CODE/YYYY/NNNNN` para journals tipo sale (A-, AC-) y `CODE/YYYY/MM/NNNN` para purchase (PB-, mes intercalado) por defecto. Comportamiento estándar; auditoría AEAT solo exige correlatividad sin huecos dentro del año, que se cumple. Si se necesitara homogeneizar para fedefarma, hacerlo vía `sequence_override_regex`. Cierra Bloque C salvo 4.7 (commit). |
| 2026-05-11 | Bloque D Fase 5.1 | Diseño ETL Holded → Odoo redactado en `migration-from-holded.md` (sección "ETL Fase 5.1 — Diseño detallado", 526 líneas añadidas, doc total 1.030). Estrategia ext_id por resource (`__holded__.contact_<id>`, `__holded__.<doctype>_<id>`, etc.) reusando `ext_id_upsert.py`. 4 resolvers puros: `resolve_partner` (VAT normalizado → fuzzy → ext_id → placeholder único para 1.149 contactId no resolubles), `resolve_tax` (description `[holded: <key>]` + `tax_reclassification.yaml` para catch-alls), `resolve_journal` (lookup por prefijo `docNumber`; PR- vía `account.move.reversal`), `resolve_account` (subcuentas 11-dig autocreadas hijas de PGCE — 148 expensesaccount + 38 saleschannels en paso 0). Orden de carga 11 pasos con dependencias estrictas: 0a/0b accounts → 1 partners → 2 products → 3 invoices → 4 purchases → 5 creditnotes → 6 purchaserefunds → 7 payments → 8 dailyledger filtrado (sólo manuales) → 9 PDFs → 10 validate. Transformaciones por modelo documentadas campo Holded → campo Odoo con pseudocódigo (partners, products, account.move, account.payment, dailyledger filtrado por heurística doc-counterpart, PDFs → `ir.attachment`). Validaciones post-load: 4 queries SQL (cuadre por journal vs jq sobre dump, balance partners 430/410, cuadre IVA trimestral vs 303 presentado, conteos finales por modelo). Decisión arquitectónica: scripts ad-hoc en `docs/tenants/inpr3mium/etl/` (11 loaders + resolvers + validate), no skill nueva — fedefarma usa Axional, no reusable cross-tenant; si en 5.3 los scripts resultan limpios se promueve a skill `holded-to-odoo` en 5.4. 6 riesgos identificados con mitigación: (1) catch-all `p_iva_exento` 2.306 docs → spot-check 100 random con operador en 5.3; (2) 1.149 contactId no resolubles → placeholder único aceptado; (3) decimal mismatch ±0.02€/línea antes de abortar; (4) dailyledger heurística filtrado → dry-run con CSV de clasificación para revisión manual; (5) sequences pre-loading vs 5.3 → política BORRAR moves 2024-2025 antes de 5.4; (6) saleschannels no en `documents.*.jsonl` → confirmar campo `channelId` en 5.3. Entregables pendientes pre-5.3: `tax_reclassification.yaml` con operador + scaffolding `etl/` + pre-load dry-run paso 0. |
| 2026-05-11 | Bloque D Fase 5.0 | Fundaciones financieras pre-ETL ejecutadas. **4 bank journals** creados con cuenta 11-dig hija de `572000` + IBAN: Santander (j=19/SAN, acc=712/57200004901, rb=2, IBAN ES1500493764312714109882), BBVA (j=20/BBVA, acc=713/57200018201, rb=3, ES6501828682260200128502), Sabadell (j=21/SAB, acc=714/57200008101, rb=4, ES1400810646370001234632), Qonto (j=22/QON, acc=715/57200688801, rb=5, ES2168880001600225350289). Cada journal con `default_account_id` = subcuenta 11-dig, `suspense_account_id=388`, `bank_account_id` enlazado al IBAN. **6 cuentas `521x`** para tarjetas (account_type=liability_current, sin journal): 52100000014 BBVA Carles (id=716), 52100000006 Sabadell Carles (id=717), 52100000017 Geraldine MC (id=718), 52100000015 TELETAC J.T. (719), 52100000016 TELETAC J.R. (720), 52100000018 TELETAC H.S. (721). **Payment term default** `15 Days` (id=2) seteado para `property_payment_term_id` y `property_supplier_payment_term_id` vía `ir.default` (ids 13 y 14). Verificado: partner nuevo en company=1 hereda ambos defaults. **Defaults empresa** actualizados de `l10n_es_pymes` (21% G + 700000 mercaderías) a inpr3mium real (services-heavy): `account_sale_tax_id=6` (21% S), `account_purchase_tax_id=8` (21% S), `income_account_id=551` (705000 Services rendered). **3 gotchas Odoo 19 nuevos en agent memory `project_odoo19_doodba_gotchas`**: (1) `ir.property` eliminado — propiedades ahora vía `company_dependent=True` + `ir.default` para defaults empresa; (2) `res.partner.bank.journal_id` es One2many reverse (no Many2one) — link vía `account.journal.bank_account_id`; (3) `ir.default` + properties de res.company requieren `base.group_system` (bot least-privilege escala temporalmente vía `odoo shell`). Operaciones que requirieron escalación shell: `ir.default.create` x2 + `res.company.write` defaults. **Diferido a cutover 5.5**: pre-loading de `ir.sequence.number_next` con counters Holded +1 (5.0.2) para evitar quemar números en validación 5.3. Tenant memory actualizada: `holded-treasury-accounts.md` (ids y journal codes finales), `decisions-log.md` (entrada 5.0 ejecutada). Snapshot `docs/tenants/inpr3mium/snapshots/2026-05-11_fase-5.0.json` (4 banks + 6 cards + omits + ir_defaults + company_defaults + BNK1 legacy). Pendientes: archivar BNK1 (id=12) placeholder l10n_es_pymes (572001 id=694) tras confirmación operador; investigar `57200002100` (8 movs "COBRO EFECTOS", probable BBVA1 histórico). Próximo: **Fase 5.1** (diseño ETL detallado). |
| 2026-05-12 | Bloque D Fase 5.1 (paso 0 ejecutado) | Run real de los loaders paso 0a + 0b contra Odoo local (DB `inpr3mium_dev`). Resultado: 148/148 expensesaccount + 38/38 saleschannels = **186 `account.account` creados** con ext_id `__holded__.account_<accountNum>` y `account_type` heredado del padre PGCE Pymes (`derive_pgce_parent`). Distribución resultante: 131 expense + 11 expense_other + 6 expense_depreciation (chapter 6) + 38 income (chapter 7). Idempotencia probada con 2ª pasada: 148 updated, 0 errors. CSV reports en `holded-export/2026-05-11/.etl_reports/{expensesaccount,saleschannels}_run_20260512_*.csv`. Snapshot `docs/tenants/inpr3mium/snapshots/2026-05-12_fase-5.1-paso0.json`. Próximos bloques pre-5.3 (paralelos): (1) `tax_reclassification.yaml` con operador — bloquea loader 4 purchases; (2) loaders 1 (partners 3.363+1) y 2 (products) en dry-run. |
| 2026-05-11 | Bloque C Fase 4.3 | Diarios + posiciones fiscales + plan analítico. 8 `account.journal` configurados preservando prefijos Holded para auditoría AEAT: 6 sale (A-, AC-, AF-, KD-, FVU-, L-) + 2 purchase (PB-, PI-). Renombrados stock INV→A- y FACTU→PB-. PB- con `refund_sequence=True` para PR- (69 purchaserefund). AC- como diario separado (no `refund_sequence` en A-) porque Holded mezcla creditnote + rectificativas de aumento en AC-. Posiciones fiscales: `l10n_es_pymes` ya creó las 4 esenciales (Intra-community, Extra-community, Equivalence surcharge, ISP) + 10 IRPF withholding — 0 RPC. Plan analítico "Granularidad gasto" (id=2) creado para granularidad futura de las 148 cuentas Holded. Gotchas Odoo 19 nuevos: (1) `account.journal.sequence_id` y `ir.sequence` por journal desaparecieron — `code` es el prefijo, `refund_sequence` boolean para abonos; (2) `account.analytic.plan` ya no tiene `company_id` (cross-company); (3) bot necesita `analytic.group_analytic_accounting` para gestionar `account.analytic.plan`. Script `journal_setup.py` parchado para Odoo 19. |
| 2026-05-12 | Lateral (no roadmap) | Side-asset creado: `docs/architecture/` (mapas internos de Odoo, una capa por archivo, carga selectiva). Andamio: `README.md` + `_template.md` + `00-index.md` con grafo Mermaid de 10 capas y tabla de triggers. Primera capa real: `6-accounting.md` (draft, 194 líneas) cubre `account.move`/`account.move.line`/`journal`/`tax`/`fiscal_position`/`payment` + 7 gotchas linkeados a memory + diagrama del flujo create→post→reconcile. Pensada para precargarse antes de Fase 5.3 (loaders 3-7 del ETL). Estado de las capas en `00-index.md`, NO en este PLAN. CLAUDE.md raíz actualizado con la regla de carga selectiva. `Próximo paso` no cambia. |

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
