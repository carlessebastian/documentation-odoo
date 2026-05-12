# Decisions log — inpr3mium

Decisiones tomadas durante el bootstrap (Fase 4) y planificación de
migración (Fase 5) con su razón y aplicabilidad. Ordenado del más
reciente al más antiguo. Las entradas se mantienen aunque la
decisión cambie — solo se añade una nueva entrada superior con la
revisión.

---

## 2026-05-12 — Fase 5.1 paso 0: subcuentas Holded cargadas en Odoo

**Hecho**: loaders 0a (`expensesaccount`) y 0b (`saleschannels`)
ejecutados en real contra `inpr3mium_dev`. 186 `account.account`
creados con ext_id `__holded__.account_<accountNum>`:

- **148 cuentas 6XX** (expense): 131 `expense` + 11 `expense_other` +
  6 `expense_depreciation`. Padre PGCE derivado por `derive_pgce_parent`
  (fallback `<first3>000` cubre 60X/62X/63X/64X/65X/66X/67X/68X).
- **38 cuentas 70X** (income): todas `account_type=income` heredado del
  PGCE Pymes `700000`/`705000`/`709000` correspondiente.

**Por qué importa para próximas fases**: el `resolve_account` de
`holded_resolvers.py` ahora encuentra las 11-dig directas. Cualquier
loader downstream (especialmente 3 invoices, 4 purchases, 8
dailyledger) puede asumir que `__holded__.account_<accountNum>`
resuelve sin autocreate para los `accountNum` presentes en
`expensesaccount.jsonl`/`saleschannels.jsonl` del dump 2026-05-11.
Solo se autocrearán las 11-dig que aparezcan en líneas de dailyledger
pero no estén en ninguno de los dos catálogos (caso esperado:
movimientos contra cuentas 4XX/5XX/47X — ya manejadas por Fase 4.5b /
5.0 / PGCE base).

**Reproducibilidad**: idempotencia probada con 2ª pasada inmediata
(148 updated, 0 errors). CSV reports en
`holded-export/2026-05-11/.etl_reports/`. Snapshot completo en
`snapshots/2026-05-12_fase-5.1-paso0.json`.

**Cómo afecta a la regla "no aplicar sequences pre-loading hasta
cutover Fase 5.5"**: no la afecta. Las subcuentas no consumen
`ir.sequence`; solo se materializan vía xml-id.

---

## 2026-05-11 — Fase 5.1: scripts ETL ad-hoc en `etl/`, no skill nueva

**Decisión**: los 11 loaders + `holded_resolvers.py` + `validate_etl.py`
viven en `docs/tenants/inpr3mium/etl/`, no como cuarta skill
`holded-to-odoo`.

**Razón**: fedefarma migra desde Axional (no Holded) → no reusable
cross-tenant. Los loaders dependen de decisiones concretas inpr3mium
(catch-all `p_iva_exento`, sales channels específicos) → bundle
reutilizable sería over-engineering. Si en 5.3 los scripts resultan
limpios y un futuro tenant Holded aparece, se promueve a skill
`holded-to-odoo` en 5.4.

**Aplicación**: scaffolding entregado 2026-05-11 con
`holded_resolvers.py` real (4 resolvers + 5 helpers puros + cache +
`ResolverStats`), tests offline 65/65 verdes, schema esqueleto
`tax_reclassification.yaml` y README. Loaders pendientes.

---

## 2026-05-11 — Fase 5.0 ejecutada: 4 bancos + 6 tarjetas + payment term + defaults

**Decisión**: aplicar 5.0 sin pre-loading de `ir.sequence.number_next`
(diferido a cutover 5.5). BNK1 placeholder de `l10n_es_pymes` queda
activo sin archivar.

**Razón**: el pre-loading consume números si el subset 2024-2025 (5.3)
añade moves antes del cutover — los huecos quedan en la numeración
AEAT. BNK1 no estorba mientras no tenga movimientos; archivarlo
requiere validar que no es default de pagos en módulos third-party.

**Defaults company aplicados**: `account_sale_tax_id=6` (21% S),
`account_purchase_tax_id=8` (21% S), `income_account_id=551` (705000
Services rendered). Sustituyen los defaults de `l10n_es_pymes` que
apuntaban a 21% G y 700000 (mercaderías) — inpr3mium es
services-heavy.

**Payment term default**: `15 Days` (id=2) para `property_payment_term_id`
y `property_supplier_payment_term_id` vía `ir.default` con `company_id=1`.

---

## 2026-05-11 — Fase 5.0: replicar granularidad 11-dig de Holded en `account.account`

**Decisión**: las cuentas analíticas creadas en Odoo para inpr3mium
mantienen el código de 11 dígitos de Holded (`57200004901`,
`52100000014`, etc.) como hijas de las cuentas PGCE Pymes raíz
(`572000`, `521000`, etc.).

**Razón**: continuidad con el histórico. Los asientos de los 12.212
documentos Holded referencian cuentas a 11 dígitos; replicar la misma
codificación elimina la fricción de mapeo en el ETL y permite
cuadrar contra extractos AEAT/banco históricos.

**Aplicación**: aplica solo a inpr3mium (y a otros tenants que migren
desde Holded). Tenants greenfield usan PGCE Pymes 6-dig directamente.

---

## 2026-05-11 — Fase 4.5b: BIDAFARMA `s_iva_exento` → `0% RC` (ISP), no exención

**Decisión**: mapear el key Holded `s_iva_exento` a `account.tax`
Odoo `0% RC` (id=109, sale, ISP), NO a `0% EXEMPT Art.20` (id=69).

**Razón**: las descripciones literales en las 998 líneas con este key
referencian explícitamente el "artículo 84 Uno 2º letra g)" — es
Inversión del Sujeto Pasivo en ventas, no exención. El nombre del
key engañaba.

**Detalle completo**: [holded-tax-mapping.md](holded-tax-mapping.md)
sección "Hallazgo crítico".

---

## 2026-05-11 — Fase 4.5: EDI cert diferido sin driver

**Decisión**: posponer Fase 4.5a (instalar certificado FNMT y
configurar entornos AEAT test/prod) sin fecha cerrada.

**Razón**: inpr3mium no necesita SII, Veri\*Factu llega 2027, no
factura a Admin Pública. Coste de instalar hoy = 0 valor.

**Triggers para reabrir**: ver [edi-obligations.md](edi-obligations.md).

---

## 2026-05-11 — Fase 4.4: bot least-privilege (sin `group_system`)

**Decisión**: el bot del agente (`bot.contable@inpr3mium.com`, uid=8)
opera con 6 grupos least-privilege:
`base.group_user + base.group_erp_manager + base.group_multi_company + base.group_partner_manager + account.group_account_manager + analytic.group_analytic_accounting`.

**Razón**: principio de mínimo privilegio. El bot no puede:
- Instalar/desinstalar módulos (requiere `group_system`).
- Modificar `ir.config_parameter` (idem).

Para esas operaciones se escalan temporalmente vía `odoo shell` con
acceso SSH.

**Aplicación**: confirmado en Fase 4.4. Las operaciones de
`odoo-module-admin` que requieren `group_system` se documentan como
"escalación temporal" en el runbook.

---

## 2026-05-11 — Fase 4.3: AC- como diario separado, no `refund_sequence` en A-

**Decisión**: crear el journal `AC-` (id=13, sale) como journal
separado del `A-` (id=7), en lugar de usar `refund_sequence=True` en
A- para que los abonos reciban prefijo AC-.

**Razón**: en Holded la serie AC- contiene tanto:
- `creditnote` (rectificativas formales): 1818 docs.
- `invoice` con importe negativo (abonos manuales): 1845 docs.

`refund_sequence` en Odoo SOLO se aplica a `out_refund` automáticos
generados desde un `out_invoice` original. Los abonos manuales que
Holded genera como `invoice` negativo no encajan en ese flujo —
necesitan un journal de tipo `sale` autónomo.

**Validación**: smoke test Fase 4.6 confirmó que
`account.move.reversal` genera AC-/2026/00001 correctamente
independiente de A-/2026/00001, con `reversed_entry_id` linkado.

---

## 2026-05-11 — Fase 4.3: PB- con `refund_sequence=True` para PR-

**Decisión**: el journal `PB-` (purchase, id=8) usa
`refund_sequence=True` — los `in_refund` automáticos generan prefijo
`PR-`.

**Razón**: PR (purchaserefund Holded) tiene volumen bajo (71 docs
hasta 2026-05-11). Justifica fusión con PB- en lugar de un journal
separado. Diferencia con AC-: aquí Holded NO mezcla types, todos los
PR son refunds reales.

---

## 2026-05-11 — Fase 4.0: PGCE Pymes, no Full

**Decisión**: usar `l10n_es.l10n_es_pymes` como chart template
(646 cuentas), no `l10n_es.l10n_es_full`.

**Razón**: análisis del cuadro de cuentas Holded de inpr3mium muestra
que se usan ~150 cuentas distintas — muy por debajo de las 2.000+ del
plan Full. Pymes es suficiente y más manejable.

**Aplicación**: confirmado al cargar el chart template (Fase 4.2).

---

## 2026-05-11 — Fase 4.0: `l10n_es_aeat_sii_oca` removido de `expected_modules`

**Decisión**: eliminar SII del scope de inpr3mium completamente (no
solo diferido).

**Razón**: ver [edi-obligations.md](edi-obligations.md). No es gran
empresa ni REDEME.

**Contraste**: `fedefarma` SÍ lo incluirá cuando se inicialice ese
tenant.
