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

- **Última actualización**: 2026-05-12 (Fase 5.1 SALES **97.6%
  cerrada**: 4.009 / 4.108 posted. Sesión de decisiones del
  operador sobre los 105 draft pendientes ejecutada: (1) 63
  status=0 Holded → dejar draft; (2) 5 status=3 review →
  posteadas; (3) AC-001135 overlap → renombrado `-bis` +
  posteado; (4) L-000719/720 dup losers → renombrados `-bis` +
  posteados; (5) 6 R- → journal R- nuevo creado + recargados +
  posteados. **Convención `-bis` para duplicados** documentada en
  agent memory + runbook. Limitación Odoo 19 (rechaza total<0) y
  estrategia journal ACC- documentadas en agent memory
  cross-tenant + runbook §5.7 + Apéndice F. **280 tests offline
  verdes**.)
- **Última fase completada**: **Bloque D — Fase 5.1 SALES cerrada
  al 97.6% (4.009 posted)**.

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
  financieras completas (Bloque D 5.0 cerrado) + diseño ETL
  detallado (5.1 redactado) + scaffolding `etl/` + **paso 0 + loader
  1 partners ejecutados en producción**. Estado Odoo:
  - 186 `account.account` Holded (148 expense + 38 income) con
    ext_id `__holded__.account_<accountNum>`.
  - 3.173 `res.partner` únicos + 190 dup_link + 1 placeholder
    `__holded__.contact__unknown` (id=16). 3.364 ext_ids
    `__holded__.contact_*`.
  - 306 partners con nota Holded visible en `res.partner.comment`
    ("Notas internas") — 150 "Código Holded" (non-ES con code no
    promovible a VAT) + 156 "VAT rechazado" (vat rechazado por
    `base_vat`, conservado como referencia). Capa 1 en
    `build_partner_vals` + Capa 2 en `_upsert_with_vat_fallback`,
    detección por sentinel textual.
  - 12 bank/sale/purchase journals operativos. Defaults company
    alineados con realidad inpr3mium (services-heavy: 21% S +
    705000).
  - **146/146 tests offline verdes** (etl/tests).
  - `holded_resolvers.py` con 4 resolvers reales + cache + helpers
    puros listos para los loaders 2-9.
  - `tax_reclassification.yaml` esqueleto con schema comentado
    (rellena operador en bloque #1 de pre-trabajo 5.3).
- **Próxima acción**: pre-trabajo para **Fase 5.3**:
  1. ~~Run real del paso 0a + 0b~~ ✅ ejecutado 2026-05-12. 186 ext_ids
     `__holded__.account_*` viven en Odoo (148 expense + 38 income).
  2. ~~Loader 1 partners~~ ✅ ejecutado 2026-05-12. 3.173
     `res.partner` únicos + 190 dup_link + 1 placeholder unknown.
     Política dedup `(countryCode, code)` con 188 codes dup
     consolidados. 2.687 partners con VAT, 6 marcados active=False
     por marca `(NO USAR)`. Estructura de campos validada (incluye
     gotcha `res.partner.mobile` no existe en Odoo 19 → degradar a
     `phone`).
  2.b ~~Notas Holded en `res.partner.comment`~~ ✅ ejecutado
     2026-05-12. 306 partners con nota visible en UI (150 "Código
     Holded" non-ES + 156 "VAT rechazado" capa 2). Patrón
     reutilizable para loaders 2-9: detección por sentinel textual
     (no HTML comment marker — Odoo sanitiza asimétricamente);
     `_holded_code_note()`, `_holded_vat_rejected_note()`,
     `has_holded_note()` en `_partners_lib.py`.
  3. Sesión con operador para rellenar
     `docs/tenants/inpr3mium/etl/tax_reclassification.yaml` con
     reglas catch-all `p_iva_exento` (sample 100 docs aleatorios
     de los 2.306 — ver 5.1 sección "Riesgos #1"). **Bloquea
     loader 4 (purchases)**.
  4. ~~Escribir loader 2 products + services~~ ✅ entregado
     2026-05-12. `_products_lib.py` + `loader_products.py` +
     `tests/test_products_lib.py` (30 tests verdes; 176 totales etl/).
  5. ~~Dry-run + run real loader 2~~ ✅ ejecutado 2026-05-12. 2.009
     `product.template` (1.569 type=consu + 440 type=service) con
     ext_ids `__holded__.{product|service}_<id>`. Tax resolution
     100% (s_iva_21/10/4/exento todos resueltos por mapeo Fase
     4.5b; 33 records sin tax cargados sin `taxes_id`). 583 sin
     income account y 102 sin expense account: aceptable, caen a
     defaults company. **ACL fix**: bot necesitaba
     `product.group_product_manager` (id=26) para crear
     `product.template` — añadido y mantenido permanente durante
     la migración. Race condition feliz entre run principal y un
     segundo run accidental cubrió los 543 records pre-ACL-fix sin
     huecos. Idempotencia validada (--limit 5: 10 updates, 0
     creates, 0 errors). Snapshot
     `2026-05-12_fase-5.1-loader-products.json`.
  6. Sesión con operador para rellenar
     `tax_reclassification.yaml` (bloquea loader 4 purchases). Sigue
     pendiente.
  7. ~~Loader 3 invoices~~ + ~~patch name=docNumber~~ ✅ ejecutado
     2026-05-12. **3.422 out_invoice draft** con `name = ref =
     docNumber` (e.g. A-007566, AC-001842, L-000547). 2 dup losers
     (L-000719/720) con name='/' + narration warn (política
     defensiva ante constraint unique(name, journal)). 8 skipped
     (2 status=2 + 6 R-). 3 bug-fixes incorporados: tz
     Europe/Madrid en `iso_from_unix`, fallback default income
     `705000` para 12 docs sin productId+saleschannel huérfano,
     detección automática de duplicados. Snapshot
     `2026-05-12_fase-5.1-loader-invoices.json`.
  8. ~~Loader 5 creditnotes~~ ✅ ejecutado 2026-05-12. **678
     out_refund draft** con ext_id `__holded__.creditnote_<id>`.
     232 con `reversed_entry_id` linkado al invoice original (de
     233 con `from.docType='invoice'` — 1 huérfano). 445
     standalone refunds (rectificativas sin enlace). 5 status=3
     (review) cargados en draft con narration warn — política:
     `--post` NUNCA postea status=3. Estructura reusa indices y
     resolvers del loader 3 vía import.
  9. ~~Loader 9 PDFs invoice~~ ✅ ejecutado 2026-05-12.
     **3.422 `ir.attachment` PDF (142.3 MB)** enlazados al
     `account.move` correspondiente vía ext_id, naming
     `<docNumber>.pdf` (A-007566.pdf, AC-001842.pdf, ...). 8
     skip_no_move (los 2 cancelled + 6 R- que loader 3 saltó,
     consistente). 0 errors. PDFs purchase (4.059 / 801 MB)
     diferidos hasta loader 4. Snapshot
     `2026-05-12_fase-5.1-loader-creditnotes-pdfs.json`.
  10. **Pendiente**: revisión visual operador de muestreo aleatorio
      (10-20 docs invoices + creditnotes de distintos journals +
      periodos) y luego postear con `--post` para invoices y
      creditnotes status=1. Operador decide qué hacer con los 6
      docs R- (~10k€ total) y los 5 status=3 (review).
  11. **Runbook completo**: `docs/tenants/inpr3mium/runbook-migration-holded.md`
      con preflight + 11 loaders + bug-fixes + recovery scenarios.
      Permite repetir Fase 5.1 desde cero a la primera (pedido
      explícito operador).
  12. ~~Loader 7 payments (MVP: invoice + creditnote)~~ ✅
      ejecutado 2026-05-12. **107 `account.payment` draft creados**
      (35 inbound cobros + 72 outbound pagos) con ext_id
      `__holded__.payment_<id>`. Filtrado: 113 docs `documentType in
      {invoice, creditnote}` - 6 `skip_bank_unmapped` (bankId `55500000007`
      es cuenta PGCE 555 "Partidas pendientes", no journal). 595 skip
      `documentType in {trans, payroll, entry, purchase(MVP)}` (out of
      scope — son asientos manuales o bloqueados). 0 errors. Bug-fix:
      `account.payment` Odoo 19 no tiene campo `ref` → holded_id va a
      `memo` con marker `[holded:<id>]`. NO reconciliado (diferido a
      cutover 5.5). Tests offline: 27 nuevos. Snapshot actualizado.
  13. Loader 4 (purchases 7.998 + purchaserefund 69). Bloqueado
      por sesión operador del paso 6 (tax_reclassification.yaml).
      Tras loader 4: re-ejecutar loader 7 con `--include-purchases`
      para los 24 payments de purchase pendientes.
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
- **Próximo paso**: con paso 0 + loader 1 cerrados, queda escribir
  los loaders restantes en orden 5.1 antes de arrancar Fase 5.3
  (validación subset 2024+2025):
  1. **`tax_reclassification.yaml`** con operador: 100 docs aleatorios
     de los 2.306 con `p_iva_exento`. **Bloqueante para loader 4
     purchases**.
  2. **Loader 2 products** (`products.jsonl` + `services.jsonl` →
     `product.template`): 1.569 + 440 records. Consume
     `HoldedResolvers.resolve_tax` para mapear `tax`/`purchaseTax` y
     `resolve_account` para `accountNum`. Gotcha Odoo 19: las
     property_account_*_id son `company_dependent`, requieren
     `ir.default` no write directo.
  3. **Loaders 3-9** (account.move, payments, dailyledger, PDFs) +
     **10 validate** según diseño 5.1 en `migration-from-holded.md`.

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

### Track paralelo — Evaluación Edition (Community vs Enterprise)

No bloquea ninguna fase del roadmap principal. Arranca cuando Fase 5.3
esté cerrada. Plan completo en
[`docs/tenants/inpr3mium/edition-evaluation-plan.md`](tenants/inpr3mium/edition-evaluation-plan.md).

- ⏸ Fase E.0 (pre-flight: confirmar criterios + timebox + camino comercial + verificar disponibilidad módulos EE 19.0)
- ⏸ Fase E.1 (spin-up doodba paralelo `inpr3mium-ee` puerto 19169)
- ⏸ Fase E.2 (clone CE → EE: pg_dump+restore + filestore rsync + activar license)
- ⏸ Fase E.3 (instalar `accountant` + `account_reports` + `l10n_es_reports` + decidir EDI; desinstalar `account_financial_report` OCA redundante)
- ⏸ Fase E.4 (evaluación 4 sem contra criterios C1-C10)
- ⏸ Fase E.5 (decisión + actualizar `profile.yaml` + `_template`)
- ⏸ Fase E.6 (wind-down perdedor + cutover ganador)

**Driver**: proyección fedefarma fin de 2026 con ~50 usuarios cambia
el cálculo de coste (~16-19 k€/año Enterprise vs self-port mis_builder
+ sepa_credit_transfer en CE). Decidir antes de comprometer fedefarma.

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
| 2026-05-12 | Bloque D Fase 5.1 (loader 1 partners ejecutado) | Run real `loader_partners.py` contra Odoo local. 3.363 contacts Holded → **3.173 `res.partner` únicos** (2.976 canonical_create + 192 unique_create + 5 updates de runs prev fallidos) + **190 `dup_link`** (contacts comparten code → ext_id apunta al canonical) + **1 placeholder `__holded__.contact__unknown`** (id=16, "Cliente historico no identificado"). 3.364 ext_ids `__holded__.contact_*` totales. Estado Odoo: 3.177 res.partner total (incl. 7 pre-existentes), 6 active=False por marca `(NO USAR)`, 2.687 con VAT, 3.022 country=ES, distribución cust_only=2.244 / supp_only=793 / both=30 / neither=110. 0 no_country + 0 no_state_es tras tunear `state_name_aliases` (parentizado + slash + sinonimo Baleares→Illes Balears) y `normalize_province` (strip diacritics). Bug-fix mid-run: política VAT endurecida — para non-ES solo usa `vatnumber` explicito, nunca `code` (Amazon EMEA con code='W0185696B' LU crashea `base_vat` que exige 8 digitos); además `_upsert_with_vat_fallback` reintenta sin vat si Odoo aún rechaza. Gotcha Odoo 19 descubierto: `res.partner.mobile` no existe — degradar a `phone` si phone vacío. Tests offline: 95 prev + 35 `_partners_lib` + 11 cambios = **141 verdes**. Snapshot `2026-05-12_fase-5.1-loader-partners.json`. CSV reports en `holded-export/2026-05-11/.etl_reports/partners_run_*.csv`. Idempotencia probada con `--limit 10` (10 updates, 0 creates, 0 errors). Próximo: loader 2 products (1.569 + 440 services). |
| 2026-05-12 | Bloque D Fase 5.1 (paso 0 ejecutado) | Run real de los loaders paso 0a + 0b contra Odoo local (DB `inpr3mium_dev`). Resultado: 148/148 expensesaccount + 38/38 saleschannels = **186 `account.account` creados** con ext_id `__holded__.account_<accountNum>` y `account_type` heredado del padre PGCE Pymes (`derive_pgce_parent`). Distribución resultante: 131 expense + 11 expense_other + 6 expense_depreciation (chapter 6) + 38 income (chapter 7). Idempotencia probada con 2ª pasada: 148 updated, 0 errors. CSV reports en `holded-export/2026-05-11/.etl_reports/{expensesaccount,saleschannels}_run_20260512_*.csv`. Snapshot `docs/tenants/inpr3mium/snapshots/2026-05-12_fase-5.1-paso0.json`. Próximos bloques pre-5.3 (paralelos): (1) `tax_reclassification.yaml` con operador — bloquea loader 4 purchases; (2) loaders 1 (partners 3.363+1) y 2 (products) en dry-run. |
| 2026-05-11 | Bloque C Fase 4.3 | Diarios + posiciones fiscales + plan analítico. 8 `account.journal` configurados preservando prefijos Holded para auditoría AEAT: 6 sale (A-, AC-, AF-, KD-, FVU-, L-) + 2 purchase (PB-, PI-). Renombrados stock INV→A- y FACTU→PB-. PB- con `refund_sequence=True` para PR- (69 purchaserefund). AC- como diario separado (no `refund_sequence` en A-) porque Holded mezcla creditnote + rectificativas de aumento en AC-. Posiciones fiscales: `l10n_es_pymes` ya creó las 4 esenciales (Intra-community, Extra-community, Equivalence surcharge, ISP) + 10 IRPF withholding — 0 RPC. Plan analítico "Granularidad gasto" (id=2) creado para granularidad futura de las 148 cuentas Holded. Gotchas Odoo 19 nuevos: (1) `account.journal.sequence_id` y `ir.sequence` por journal desaparecieron — `code` es el prefijo, `refund_sequence` boolean para abonos; (2) `account.analytic.plan` ya no tiene `company_id` (cross-company); (3) bot necesita `analytic.group_analytic_accounting` para gestionar `account.analytic.plan`. Script `journal_setup.py` parchado para Odoo 19. |
| 2026-05-12 | Bloque D Fase 5.1 (cierre sesión decisiones draft) | **Sesión decisiones operador sobre 105 draft pendientes** (no automatizables, requieren contexto semántico). 5 decisiones: **(1) 63 docs status=0 Holded → dejar draft** (respeta estado origen, operador postea/cancela en UI cuando revise). **(2) 5 status=3 review** (AC-001793/4/5/6/800, ~5.184€) → posteados directamente vía `action_post` (operador revisó + aprobó). **(3) AC-001135 overlap** (1 doc): docNumber duplicado en `invoice.jsonl` 520€ posted + `creditnote.jsonl` 726€ draft (chocaba con unique(name, journal_id) al postear); renombrado a `AC-001135-bis` + posteado. **(4) L-000719/720 dup losers**: 2 pares de facturas reales con mismo docNumber en fechas distintas (bug Holded original); inicialmente posteados con names L-001314/L-001315 asignados desde sequence Odoo (rompía promesa "name=docNumber Holded literal"); button_draft + renombrados a `L-000719-bis` y `L-000720-bis` + reposteados (huecos L-001314/01315 quedan en sequence pero aceptables: Odoo no fuerza correlatividad y son año fiscal 2019 cerrado). **(5) 6 R- históricos** (prefijo legacy "Rectificativas" 2018-2020, abandonado por Holded tras unificar AC-): journal `R-` nuevo creado (id=24, code=R-, type=sale, name="R- Rectificativas históricas Holded"); script ad-hoc inline crea los 6 docs (4 out_refund con flip signos + 2 out_invoice positivos), name=docNumber Holded literal, ref=docNumber, narration explicativa, PDFs originales adjuntos, posteados. **Documentación creada/actualizada**: (a) agent memory `project_odoo19_negative_amount_constraint.md` con gotcha cross-tenant (Odoo 19 rechaza total<0 + estrategia journal aislado) — aplicable a fedefarma/Axional y futuros tenants; (b) runbook §5.7 con procedimiento completo conversión ACC-; (c) runbook Apéndice F con 5 decisiones operativas (status=0/status=3/dup `-bis`/prefix sin journal/search filters); (d) decisions-log tenant con cita literal + razonamiento por decisión; (e) snapshot `2026-05-12_post-conversion-final.json` ampliado. **Estado final SALES**: 2.638 out_invoice posted + 1.371 out_refund posted = **4.009 posted / 4.108 totales (97.6%)**. 99 draft restantes (63 status=0 + 30 ACC- status=0 + 6 misc) son intencionales por política. Próximo: tax_reclassification.yaml → desbloquea loader 4 purchases. |
| 2026-05-12 | Bloque D Fase 5.1 (conversión journal ACC-) | **Conversión 776 docs con total<0 a journal ACC-** (decisión operador 2026-05-12: "Generar una serie 'Propia' tipo ACC- para que estén aislados"). Contexto: tras `--post` de invoices, Odoo 19 rechazó 720 docs con "No puede validar una factura con un importe total negativo" — son rectificativas de abono que Holded almacenó en `invoice.jsonl` con totales negativos en vez de en `creditnote.jsonl`. 26 más eran caso inverso (rectificativas de aumento en `creditnote.jsonl`). Total 776 docs problemáticos: 705 AC- + 41 A- + 3 L- + 1 FVU- + 26 AC-creditnote. **Solución implementada**: (1) Journal ACC- creado (id=23, code=ACC-, type=sale). (2) Patch `_invoices_lib.py` + `_creditnotes_lib.py` con detección automática `total<0` → flip `move_type` + `journal_id=ACC-` + flip signo `quantity` líneas + `name=False` (sequence Odoo asigna). (3) Pre-conversion: snapshot inventario (776 docs + 750 attachment_ids). (4) Detach PDFs (res_id=0 para evitar borrado en cascada). (5) Borrar 776 moves + ext_ids `ir.model.data`. (6) Re-run loader 3 + loader 5 con lógica de conversión: 750 out_refund + 26 out_invoice creados en ACC-. (7) Re-asignar 750 PDFs al new move_id (0 huérfanos). (8) `--post`: 720 out_refund + 23 out_invoice posted (33 quedan draft: 30 status=0 Holded + 1 AC-001135 overlap docNumber + 2 misc). **Names finales**: ACC-/2026/NNNNN (out_invoice) y RACC-/2026/NNNNN (out_refund — Odoo añade `R` automáticamente para refunds en journal sale). `ref` preserva docNumber Holded literal (`AC-001806`, etc.) — buscable nativamente en barra de búsqueda Odoo. `narration` con marker `CONVERTIDO out_<X> -> out_<Y>` buscable con `narration ilike`. **Estado global final SALES**: 2.633 out_invoice posted + 1.364 out_refund posted = 3.997 posted / 4.102 totales (97.4%). Pendiente operador: 5 status=3 review + 63 status=0 Holded + 1 overlap AC-001135. Snapshot `2026-05-12_post-conversion-final.json`. Decisión documentada en decisions-log. |
| 2026-05-12 | Bloque D Fase 5.1 (loader 7 payments MVP) | **Loader 7 payments**: `_payments_lib.py` (~340 lineas) + `loader_payments.py` (CLI) + `tests/test_payments_lib.py` (27 tests). Filtrado MVP: solo `documentType in {'invoice', 'creditnote'}` (113 docs de 708) que enlazan a moves cargados por loaders 3/5. Out of scope MVP: 'purchase' (24, bloqueado por loader 4), 'trans' (440), 'payroll' (105), 'entry' (26) = 571 asientos manuales no son account.payment. Bug-fix mid-run: **`account.payment` Odoo 19 NO tiene campo `ref`** (es del move generado por el payment) → `holded_id` va a `memo` con marker `[holded:<id>]`. Mapeo `BANK_TO_JOURNAL` hardcoded del snapshot Fase 5.0 (4 bancos productivos SAN/BBVA/SAB/QON → journal_ids 19/20/21/22). **Resultado real**: 107 `account.payment` draft creados (35 inbound cobros + 72 outbound pagos), 6 skip_bank_unmapped (bankId `616e8642d8426e21406558bb` = cuenta PGCE 555 "Partidas pendientes de aplicación", no journal), 0 errors. Ext_id `__holded__.payment_<id>`. State=draft, NO reconciliado (diferido a Fase 5.5 cutover). Flag `--include-purchases` listo para usar tras loader 4. Tests cubren: derive_payment_type (signo amount → inbound/outbound), derive_partner_type (doctype → customer/supplier), _xmlid_for_target, build_payment_vals (sin ref, memo con holded_id), 7 escenarios de skip end-to-end, real con FakeOdoo, constantes BANK_TO_JOURNAL=4. Total tests etl/: **280 verdes** (253 + 27). CSV report en `.etl_reports/payments_run_*.csv`. |
| 2026-05-12 | Bloque D Fase 5.1 (loaders 3 patch + 5 + 9 + runbook) | **Sesión de cierre Fase 5.1 invoices/refunds + documentación**. (1) **Patch loader 3 `name=docNumber`**: política operador "documentos importados no pueden cambiar número de factura, estrategia de subida una vez se cierre un trimestre" → setear `account.move.name = doc.docNumber` literal antes del post (e.g. A-007566, AC-001842, L-000547). Odoo respeta name explícito en action_post. Preserva correlatividad AEAT histórica; facturas post-cutover usarán secuencia Odoo distinta (formato `A-/YYYY/NNNNN`) — convivencia aceptada por el operador. **Detección duplicados docNumber**: dump tiene 2 pares reales (L-000719 x2, L-000720 x2, contactos distintos) — bug Holded original que viola constraint AEAT. Política defensiva: el doc del par con `date` más reciente preserva name=docNumber; los otros quedan name='/' (Odoo asignará sequence si se postean) + nota visible en narration explicando el duplicado. Constraint unique(name, journal_id, company_id) no se viola. 4 facturas afectadas (2 pares). Re-run completo (~17 min): 3.421 updated_draft, 2 dup_name_dropped, 0 errors. Verificación: 3.420 con name explícito = docNumber, 0 con name='/', 2 con name=False (losers). 1 caso aislado (L-000837, id=913) terminó en state=cancel por artifact de runs múltiples — restaurado a draft con button_draft + name manual. (2) **Loader 5 creditnotes**: 678 docs `documents/creditnote.jsonl` (todos prefix AC-) → 678 `account.move` out_refund draft con ext_id `__holded__.creditnote_<id>`. Ejecutado limpio a la primera tras reusar masivamente helpers de `_invoices_lib` (imports: `iter_jsonl`, `_build_line`, `build_index_by_id`, `lookup_*`, `parse_doc_prefix`, `search_ext_id`). Específico de refunds: `move_type='out_refund'`, `journal=AC-` (id=13), `reversed_entry_id` set si `doc.from.docType='invoice'` y `from.id` resoluble vía ext_id `__holded__.invoice_<id>`. Resultado: 232 con reversed_entry_id linkado (de 233 from-links — 1 huérfano), 445 standalone refunds. 5 docs con status=3 (review) cargados como draft con narration warn — política conservadora: `--post` NUNCA postea status=3 (operador decide caso por caso). 0 errors. 15 tests offline nuevos. (3) **Loader 9 PDFs**: nuevo `_pdfs_lib.py` + `loader_pdfs.py` que itera `pdfs/<doctype>/<holded_id>.pdf` y crea `ir.attachment` (type=binary, mimetype=application/pdf) enlazado al `account.move` via ext_id `__holded__.<doctype>_<holded_id>`. Naming `<docNumber>.pdf` (legible UI, no holded_id). 4 doctypes soportados (invoice/purchase/creditnote/purchaserefund). Idempotente (skip si attachment con mismo res_id+name ya existe). Protección tamaño (skip > 50 MB). 14 tests offline. Run real invoice PDFs (3.430 archivos, ~143 MB) en curso, ETA ~20 min. (4) **Runbook completo** `docs/tenants/inpr3mium/runbook-migration-holded.md` (~12 KB, 5 secciones + 5 apéndices): preflight (env, ACLs bot, default income, dump), 11 loaders paso a paso con comando + resultado esperado + gotchas conocidos, política numeración + duplicados + filtros aplicados, validación SQL post-load, lifecycle draft→posted, recovery scenarios (tz bug, name='/', wipe completo, dump nuevo), mapa ext_ids `__holded__.*`, tabla resolvers, comandos copy-paste, tiempos estimados, referencia snapshots. Pedido explícito operador "documenta todo para que la migración se pueda re-ejecutar a la primera". (5) **Tests**: 253 totales etl/ (224 + 1 patch + 14 PDFs + 15 creditnotes - 1 deprecated). Decisions-log entradas nuevas: política name=docNumber, status=3 review. Próximo: esperar loader 9 + revisión visual operador + postear. |
| 2026-05-12 | Bloque D Fase 5.1 (loader 3 invoices — ejecutado) | Loader 3 entregado + ejecutado en producción. `_invoices_lib.py` (~480 lineas) + `loader_invoices.py` (CLI ~80 lineas) + `tests/test_invoices_lib.py` (43 tests). Carga `documents/invoice.jsonl` (3.430 docs) -> `account.move` out_invoice. **Resultado**: 3.422 out_invoice draft creados con ext_id `__holded__.invoice_<id>` (12 created en re-run + 3.409 updated_draft del 1er run + 1 skip_existing_posted del smoke previo). **8 docs skipped** documentados: 2 status=2 (cancelados Holded: A-008947 VADEFARMA 1.992€, L-001308 SORIA NATURAL 2.315€) + 6 R- (sin journal mapeado: R-000004..009, ~25k€ total, mix +/-). **Cuadre con dump por journal**: 1697A-/722AC-/14AF-/11FVU-/163KD-/815L-, diffs en céntimos por redondeo decimal (AC- -0.11€ sobre 722 docs; A- diff de 1.210,57€ explicado por factura smoke Fase 4.6 preexistente; resto < 0.10€). Total Odoo 17.400.355,34€ vs dump 17.399.144,78€ (diff = smoke). **2 bug-fixes mid-run**: (1) **`iso_from_unix` cambió de UTC a Europe/Madrid** — Holded guarda timestamps como medianoche local; en UTC un timestamp 1546210800 = 2018-12-31 00:00 CET / 2018-12-30 23:00 UTC se interpretaba como "2018-12-30" cambiando el fiscal year de muchas facturas de diciembre. Fix aplicado en `holded_resolvers.py` con ZoneInfo + 2 tests parametrizados (winter UTC+1, summer UTC+2); afecta a TODOS los loaders. (2) **Fallback default income `705000`** cuando item sin productId Y saleschannel huerfano → Odoo abortaba con "Missing required account on accountable line"; 12 docs afectados; fix lookup `account.account.code='705000'` al iniciar el orquestador, aplicado en `_build_line` solo si NI product NI account resoluble. **State final**: todos draft (sin --post). **Decisiones de diseño**: SALES_PREFIXES = {A-, AC-, AF-, KD-, FVU-, L-} hardcoded; `should_skip_doc()` centraliza filtros antes de RPCs; idempotencia (existing draft → rewrite con (5,0,0)+lines; existing posted → skip); `ref = docNumber` para auditoría AEAT; `narration` desde `desc + notes` excluyendo si == ref. Tests offline: 220 prev + 1 fallback nuevo = **221 verdes** (incluye 2 tz_madrid + 42 test_invoices_lib). CSV reports en `holded-export/2026-05-11/.etl_reports/invoices_run_20260512_*.csv`. Snapshot `docs/tenants/inpr3mium/snapshots/2026-05-12_fase-5.1-loader-invoices.json`. Próximo: revisión visual operador + postear; loader 5 creditnotes (678 docs reusa estructura). |
| 2026-05-12 | Bloque D Fase 5.1 (loader 2 products+services — ejecutado) | Run real loader_products.py contra Odoo local. Resultado: **2.009 `product.template` creados** con ext_ids `__holded__.{product|service}_<id>` — 1.569 type=consu (products) + 440 type=service. Verificacion final: `product.template total=2.012` (3 pre-existing l10n_es_pymes); 2.009 con `taxes_id` resuelto via mapeo Fase 4.5b (s_iva_21 1.964, s_iva_10 5, s_iva_4 3, s_iva_exento 4 → id=109 ISP, 33 cargados sin taxes_id). **ACL fix mid-run**: bot uid=8 (least-privilege post Fase 4.4) carecia de `product.group_product_manager` (id=26) — error "Se permite esta operacion para los grupos siguientes: Products/Create"; solucionado con `c.call('res.users','write',[[8],{'group_ids':[(4,26)]}])`. Bot ahora con 7 grupos (`[1,2,5,9,23,26,33]`). Decision: mantener grupo 26 permanente durante migracion; tightenear post-cutover. **Race condition feliz**: un segundo run accidental (que se mato a los segundos) creo los 543 records que el run principal fallo en su primera tanda pre-ACL-fix → net result 0 huecos, 2.009 cargados completos. **Hallazgos de calidad del dump**: (1) 583 sin income account = 477 records sin `salesChannelId` (135 products + 342 services, mayoria del catalogo Holded) + 106 con `salesChannelId` huerfano (no existe en `saleschannels.jsonl`); (2) **102 products sin expense account: TODOS apuntan al mismo id huerfano `610138c76362411c8a4bd586`** (no existe en `expensesaccount.jsonl` que tiene 148 entradas distintas) — dato perdido del dump, aceptable; (3) 56 SKU colisiones (default_code no es unique en Odoo). **Idempotencia validada**: re-run con --limit 5 → 10 updates, 0 creates, 0 errors. **CSV reports** en `.etl_reports/products_run_*.csv` con columnas `kind,holded_id,name,sku,tax_key,tax_id,income_account_id,expense_account_id,xmlid,status,res_id,error`. Snapshot `docs/tenants/inpr3mium/snapshots/2026-05-12_fase-5.1-loader-products.json`. Siguiente: sesion con operador para `tax_reclassification.yaml` (bloquea loader 4) + escribir loader 3 (invoices). |
| 2026-05-12 | Bloque D Fase 5.1 (loader 2 products+services — offline) | Loader 2 entregado: `_products_lib.py` (~440 lineas) + `loader_products.py` (CLI ~100 lineas) + `tests/test_products_lib.py` (30 tests, 176 totales etl/ verdes). Cubre `products.jsonl` (1.569, kind=`consu`) + `services.jsonl` (440, kind=`service`) → `product.template`. Ext_id `__holded__.product_<id>` / `__holded__.service_<id>`. Resolvers usados: `resolve_tax` ctx=`{doc_type:sale}` (lookup directo `[holded: <key>]` — los s_iva_21/10/4/exento ya mapeados en Fase 4.5b), `resolve_account(autocreate=False)` para income (via `salesChannelId`→`accountNum` lookup en `saleschannels.jsonl`) y expense (via `expAccountId`→`accountNum` lookup en `expensesaccount.jsonl`, solo products con expAccountId = 102/1.569). Decisiones de diseño documentadas en docstring: (1) schema real usa `taxes` array, no `tax` single como decía el doc — 1.536 products tienen 1 sola key (s_iva_21), 33 tienen 0; (2) **products sin tax cargan sin `taxes_id`** (no abortan); (3) **multi-tax aborta el record** (no mergeamos N keys); (4) `purchaseTax` no existe en el dump — `supplier_taxes_id` lo derivará loader_purchases desde `item.tax`; (5) `categoryId` siempre vacío → skip; (6) variants `attributes` (688 products) cargan plano, no expandidos a `product.product` con `product.attribute.line`; (7) `hasStock`/`stock` ignorado — Fase 5.4 lo cargará; (8) income/expense accounts escritos directamente en `create` (Odoo 19 maneja `company_dependent` per-record). Soporte de `--dry-run` + `--limit` consistente con loader_partners. CSV report en `<dump>/.etl_reports/products_{mode}_<ts>.csv` con `{kind, holded_id, name, sku, tax_key, tax_id, income_account_id, expense_account_id, status, error}`. ProductStats trackea: total_products/services, would_create/update, product/service_create/update, no_tax, tax_unresolved, multi_tax, no_income_account, no_expense_account, sku_collision, errors. Tests cubren: `extract_tax_key` (single/empty/multi/strip), `index_by_id`, `build_product_vals` (10 casos), `build_service_vals` (2), 8 escenarios end-to-end con FakeOdoo (basic dry-run, tax_unresolved aborts, no_tax OK, multi_tax aborts, income missing, expense resolved, limit, sku_collision) + 1 real con upsert mockeado. Pendiente: ejecutar dry-run real contra Odoo local + run real (no bloqueado — no depende de tax_reclassification.yaml). |
| 2026-05-12 | Bloque D Fase 5.1 (loader 1 partners — notas Holded en UI) | Side-fix: el `ref` de Holded no es visible en la vista de proveedor de `l10n_es_pymes`. Inyectamos el code original (o el VAT rechazado) en `res.partner.comment` (Notas internas) para que el operador pueda auditar desde la UI. **Capa 1** en `build_partner_vals`: si `raw_code` poblado y no se promueve a `vat`, escribe `<p>Código Holded (no validado como VAT): <code>X</code></p>`. **Capa 2** en `_upsert_with_vat_fallback`: si Odoo rechaza el vat y caemos al retry sin vat, escribe `<p>VAT rechazado por validación Odoo (conservado como referencia): <code>X</code></p>`. Detección por sentinel textual (`Código Holded`/`VAT rechazado`) — descartado markers HTML comment porque Odoo sanitiza el field y stripa asimétricamente el comment de apertura (bug reproducible: `<!-- A --><p>X</p><!-- B -->` round-trip → `<p>X</p><!-- B -->`). Re-run loader (3.363 contacts, 2.979 + 194 updates, 0 errors): **306 partners con nota Holded** (150 "Código Holded" + 156 "VAT rechazado"). Script one-shot `retrofit_holded_code_note.py` cubre el caso A (ref+novat) para partners ya cargados antes de los cambios; idempotente vía `has_holded_note()`. Tests offline: 146/146 verdes (cambios: -4 marker tests, +4 has_holded_note tests, +1 test_es_with_valid_code_no_comment, +1 test_vat_error_retries_without_vat extendido). Próximo paso del roadmap no cambia: loader 2 products. |
| 2026-05-12 | Lateral (no roadmap) | Side-asset creado: `docs/architecture/` (mapas internos de Odoo, una capa por archivo, carga selectiva). Andamio: `README.md` + `_template.md` + `00-index.md` con grafo Mermaid de 10 capas y tabla de triggers. Primera capa real: `6-accounting.md` (draft, 194 líneas) cubre `account.move`/`account.move.line`/`journal`/`tax`/`fiscal_position`/`payment` + 7 gotchas linkeados a memory + diagrama del flujo create→post→reconcile. Pensada para precargarse antes de Fase 5.3 (loaders 3-7 del ETL). Estado de las capas en `00-index.md`, NO en este PLAN. CLAUDE.md raíz actualizado con la regla de carga selectiva. `Próximo paso` no cambia. |
| 2026-05-12 | Track paralelo — eval Edition | Conversación operador sobre proyección a fedefarma (~50 users fin 2026) revela que el driver original "API access" no diferencia Community vs Enterprise (misma superficie RPC en ambas). Drivers reales a esa escala: reporting estatutario PGCE (P&L/Balance), Studio para customización no-code, multi-empresa con consolidación, Documents/Sign nativos. Coste anual proyectado total (inpr3mium 3 + fedefarma 50 users): ~16-19 k€/año a precio público. Decisión: NO comprometerse aún, ejecutar A/B paralelo en local (dos doodba separados, BBDD CE clonada a EE) con timebox 4-6 semanas tras cierre Fase 5.3. Plan completo en `docs/tenants/inpr3mium/edition-evaluation-plan.md` (250+ líneas: 11 secciones, criterios C1-C10 con pesos, 6 fases E.0-E.6, anexos para license activation y mapping OCA→EE, 7 preguntas abiertas para operador). Añadido al índice de `docs/tenants/inpr3mium/memory/MEMORY.md` y al roadmap como track paralelo no bloqueante. La migración Holded → Odoo continúa sin interrupción sobre Community. Pendiente operador: responder 7 preguntas de sección 10 antes de Fase E.0. |

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
