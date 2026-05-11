# Migración Holded → Odoo 19 — inpr3mium

**Estado: pre-diseño.** Estructura general decidida; el detalle ETL
y el cutover se concretan en Fase 5 del plan, una vez la instancia
Odoo esté arrancada y bootstrappeada (Fases 3-4).

## Contexto del origen (datos del análisis)

- **Holded URL**: https://farmapremium.holded.com (plan con API).
- **Volumen del cuadro de cuentas (export 2025)**: 333 cuentas
  activas, 70 prefijos de 4 dígitos. PGCE Pymes con analítica
  extendida por Holded (códigos de 11 dígitos: 4 base + 7 analítica).
- **Particularidades fiscales** (relevantes para mapeo):
  - Cuentas IRPF retenido (`4751*` x5): retenciones a profesionales,
    arrendamientos, retribución especie, vehículo.
  - Cuentas servicios profesionales recibidos (`62300710*` x12):
    asesoría laboral, contable, fiscal, secretaría consejo,
    protección datos, prevención riesgos, etc.
  - Cuentas IVA repercutido/soportado por % (`4720`, `4770`).
  - Capital social tripartito: FEDERACIO FARMACEUTICA, BIDAFARMA,
    CRUZFARMA. Préstamo de FEDEFARMA → cuenta `66231400002`.
  - Compras de packs (`60000400*`) y producción PLV (`6230074*`,
    `6240074*`).

## Origen: Holded

[Holded](https://www.holded.com/) es un SaaS español de gestión
empresarial (contabilidad, facturación, CRM, ERP ligero). Expone una
API REST documentada en <https://developers.holded.com/>.

Recursos relevantes para el ETL:

- **Contacts** (clientes y proveedores) → `res.partner`.
- **Products** → `product.product` / `product.template`.
- **Documents** (facturas emitidas, recibidas, presupuestos, albaranes)
  → `account.move` (`out_invoice`, `in_invoice`).
- **Payments / Treasury** → `account.payment`.
- **Accounts** (plan contable Holded) → mapeo a `account.account` del
  PGCE elegido en Odoo.
- **Taxes** → mapeo a impuestos `account.tax` de `l10n_es`.

## Scope (decidido)

**Histórico completo + año en curso**, con validación previa por
subset.

- [x] **Subset de validación**: ejercicios **2024 y 2025** completos.
      Estos dos años son los que se migran primero como prueba para
      verificar que el ETL produce balances cuadrados, partners
      coherentes y facturación correcta antes de cargar el resto.
- [ ] **Histórico completo**: tras validación OK, migrar todos los
      ejercicios anteriores disponibles en Holded.
- [ ] **Año en curso**: tras OK del histórico, traer el ejercicio
      activo hasta el día del cutover.

Justificación: el negocio tiene partes vinculadas (capital social
participado) y modelo 232; tener histórico contable completo en
Odoo facilita auditoría y reporting consolidado futuro con las
sociedades hermanas.

## Mapeo de modelos (borrador)

| Holded | Odoo | Mapeo / notas |
|--------|------|---------------|
| Contact (`type=client`) | `res.partner` con `customer_rank > 0` | Mapear `vat`, `email`, `phone`, dirección. Holded a veces mezcla persona/empresa: deduplicar por VAT. |
| Contact (`type=supplier`) | `res.partner` con `supplier_rank > 0` | Idem. Si un VAT es ambos, un solo partner con ambos ranks. |
| Product | `product.template` + `product.product` | Mapear `default_code`, `list_price`, `taxes_id` (al impuesto `l10n_es` correspondiente). |
| Invoice (cliente) | `account.move` (`out_invoice`) | `invoice_date`, `partner_id`, líneas → `account.move.line`. Estado: postear posteriormente, no en el create. |
| Bill (proveedor) | `account.move` (`in_invoice`) | Idem. |
| Payment | `account.payment` | Conciliación con la factura correspondiente. |
| Cuenta contable Holded | `account.account` | Mapear a PGCE español. |

## ETL — pasos previstos

1. **Export Holded** — usar la skill `holded-export` (read-only):

   ```bash
   # Preflight: cuantos contactos / docs / asientos hay
   python3 .claude/skills/holded-export/scripts/holded_inspect.py

   # Dump completo (todos los resources + PDFs originales escaneados)
   python3 .claude/skills/holded-export/scripts/holded_export.py \
     --output-dir docs/tenants/inpr3mium/holded-export/$(date +%F) \
     --include-pdfs

   # Validar manifest + counts
   python3 .claude/skills/holded-export/scripts/dump_summary.py \
     --dir docs/tenants/inpr3mium/holded-export/$(date +%F)
   ```

   Output: directorio `docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>/`
   con JSONL por resource, `numbering_series.json`, `contact_groups.json`,
   `manifest.json`, `errors.jsonl` y `pdfs/{invoice,purchase}/<id>.pdf`.
   El directorio está **gitignored** (datos personales/financieros).

2. **Transformación** — script Python que lee los JSONL, normaliza VATs
   (formato `ES...`), deduplica, mapea cuentas e impuestos, y escribe
   un dataset listo para Odoo.

3. **Carga en Odoo** — vía JSON-2 / `ext_id_upsert.py` (idempotente),
   un modelo a la vez en orden de dependencias: partners → productos →
   plan contable → asientos de apertura → (opcional) facturas
   históricas. Por hacer: posible 5ª skill `holded-to-odoo` si se
   complica.

4. **Validación** — conteo, cuadre de balance, spot-check con un
   partner real, primer cierre mensual.

La skill `holded-export` cubre el **lado lectura** de Fase 4.2.1 y
deja Fase 5 con el material listo para transformar. Solo emite GETs;
no puede modificar nada en la cuenta Holded.

## Cutover

- Fecha objetivo: **sin fecha fija**. Se decidirá cuando el agente
  esté maduro y la migración del subset 2024+2025 esté validada.
- Pasos del día D — a detallar tras validación.

## Hallazgos del dump del 2026-05-11 (Fase 4.2.2)

Dump real ejecutado en `holded-export/2026-05-11/` (969 MB total,
gitignored). Datos extraídos directamente de la cuenta para informar
Fase 4.3.

### Volúmenes reales (histórico completo 2018-2026)

| Resource | Items | Notas |
|---|---:|---|
| contacts | 3.363 | partners (clientes + proveedores) |
| products | 1.569 | productos físicos |
| services | 440 | servicios |
| expensesaccount | 148 | cuentas de gasto (códigos 11 dígitos) |
| taxes | 103 | impuestos (IVA/IRPF/RE + intracom + ISP) |
| payments | 708 | pagos registrados |
| treasuries | 12 | cuentas de tesorería |
| saleschannels | 38 | canales de venta |
| remittances | 85 | remesas SEPA |
| numbering_series | 16 | series de numeración (6 invoice + 2 purchase + 8 resto) |
| documents.invoice | **3.430** | facturas emitidas — todas con PDF generado por Holded |
| documents.creditnote | 678 | abonos emitidos |
| documents.purchase | **7.998** | facturas recibidas (gastos) — 4.059 con PDF original escaneado, 3.939 sin PDF (asientos manuales) |
| documents.purchaserefund | 69 | abonos recibidos |
| documents.proform | 34 | facturas proforma |
| documents.estimate | 3 | presupuestos |
| documents.{salesreceipt,salesorder,waybill,purchaseorder} | 0 | inpr3mium no usa estos flujos |
| dailyledger | 2.250 | asientos contables completos 2018-2026 (chunkeados por años) |
| **PDFs descargados** | **7.489** | 3.430 invoice (142.6 MB) + 4.059 purchase (801.4 MB) |

### PDFs de purchase: corte en 2022

3.939 de las 7.998 facturas recibidas (`purchase`) no tienen PDF
original. Verificado por el operador en Holded UI: estos documentos
**fueron importados como histórico contable** cuando inpr3mium
migró a Holded a inicios de 2022, sin adjuntar las facturas
escaneadas. El corte es nítido por año:

| Año | Con PDF | Sin PDF |
|---:|---:|---:|
| 2018-2021 | 1 | 3.933 |
| 2022 | 992 | 6 (anomalías sueltas) |
| 2023+ | 2.793 | 0 |

Implicación para la migración:

- **2018-2021**: cargar solo los asientos contables (de `dailyledger`),
  sin facturas individuales. Los 3.933 records de `documents.purchase`
  son redundantes con `dailyledger` para ese período. **No crear
  `account.move` individual** por cada uno — bastaría con los
  asientos del libro diario.
- **2022+**: cargar `account.move` con PDF adjunto en
  `ir.attachment` (4.059 PDFs para los purchase, 3.430 para invoice).
  Las 6 anomalías de 2022 cargarlas como move sin adjunto.

### Secuencias de numeración (`numbering_series.json`)

Holded usa placeholders `%%%%%%` para el contador y `[YY]` para el
año. Mapeo a `ir.sequence` de Odoo (prefijo + padding del número):

| Tipo Holded | Nombre Holded | Prefijo | Padding | `ir.sequence` Odoo |
|---|---|---|---|---|
| invoice | Facturas de Ventas | `A-` | 6 | `A-%(range_year)s-NNNNNN`* |
| invoice | Facturas de Ventas Abonos | `AC-` | 6 | sequence dedicada |
| invoice | Autofactura | `AF-` | 5 | sequence dedicada |
| invoice | Facturas Kit Digital | `KD-` | 5 | sequence dedicada |
| invoice | Facturas especiales | `FVU-` | 6 | sequence dedicada |
| invoice | Laboratorios | `L-` | 6 | sequence dedicada |
| creditnote | Línea CN | `AC-` | 6 | **misma sequence que Abonos** |
| purchase | Factura de Gastos | `PB-` | 6 | sequence dedicada |
| purchase | Facturas compras Inmovilizado | `PI-` | 6 | sequence dedicada |
| purchaserefund | Predeterminada | `PR` | 5 | sequence dedicada |
| salesreceipt/salesorder/proform/waybill/estimate/purchaseorder | varios `[YY]NNNN` | `T/SO/PRO/A/E/O` | 4 | sequences con prefijo de año |

*Decidir en 4.3: ¿preservamos los códigos antiguos (continuidad
histórica para auditoría AEAT) o reseteamos contadores en Odoo? Las
ventas son `A-XXXXXX` (no `A-YYYY-XXXXXX`), así que el padding sí, el
año no. → Crear `ir.sequence` con `prefix="A-"`, `padding=6`, NO
`use_date_range`.

→ 6 sequences distintas solo para `invoice` (≠ habitual: 1 por
diario). Implica **6 diarios** o **1 diario + selector** durante la
carga del histórico. Decisión 4.3.

### Mapeo de impuestos (`taxes.jsonl`)

Holded expone los taxes con `key` canónica que mapea limpio:

| Holded key | Holded amount | Odoo (l10n_es) | scope |
|---|---|---|---|
| `s_iva_21` | 21 | `s_iva21b` | sales |
| `s_iva_10` | 10 | `s_iva10b` | sales |
| `s_iva_4` | 4 | `s_iva4b` | sales |
| `s_iva_0` | 0 | `s_iva0_e` | sales |
| `p_iva_21` | 21 | `p_iva21_bc` | purchases |
| `p_iva_10` | 10 | `p_iva10_bc` | purchases |
| `p_iva_4` | 4 | `p_iva4_bc` | purchases |
| `p_iva_bi_21` | 21 | `p_iva21_ibc` (bien inversión) | purchases |
| `s_iva_exento` / `p_iva_exento` | 0 | `s_iva0_e` / `p_iva0_e` | exento art.20 |

Holded tiene además `IVA 12%`, `IVA 5%`, `IVA 7,5%`, `IVA 2%` (vigentes
ES temporales 2023-2024 para electricidad/alimentos). Mapearlos al
mismo `l10n_es` con la `amount` correspondiente — Odoo los tendrá si
`l10n_es` está actualizado, si no crear manualmente.

Recargo Equivalencia, ISP, Adq.Intracom. UE: `l10n_es` los cubre.
Confirmar matching por `key` durante el ETL.

### Cuentas de gasto (`expensesaccount.jsonl`)

148 cuentas, todas con `accountNum` de **11 dígitos**. Distribución
por prefijo de 3 dígitos:

| Prefijo | n cuentas | Grupo PGCE |
|---|---|---|
| `621` | 39 | Arrendamientos y cánones |
| `627` | 23 | Servicios bancarios y similares (incluye comisiones) |
| `623` | 18 | Servicios profesionales independientes |
| `640` | 9 | Sueldos y salarios |
| `629` | 7 | Otros servicios |
| `622` | 7 | Reparaciones y conservación |
| `626` | 6 | Servicios bancarios |
| `600` | 6 | Compras de mercaderías |

Confirma decisión histórica de **colapsar a prefijo 4-7 dígitos**
PGCE Pymes y mover granularidad (proveedor/centro de coste/contrato)
a `account.analytic.account`. La granularidad real está en el `name`
de la cuenta (ej. "ALQUILER FACTORIAL", "AMAZON AWS"), no en el código.

## Configuración Odoo aplicada (Fase 4.3, 2026-05-11)

### Diarios

8 `account.journal` configurados en company_id=1 — uno por cada
secuencia identificada en Holded, para preservar continuidad de
numeración bajo auditoría AEAT:

| id | code | type | name | refund_seq | hash | Origen |
|---:|---|---|---|---|---|---|
| 7 | `A-` | sale | Facturas Ventas | False | False | renombrado desde INV stock |
| 13 | `AC-` | sale | Abonos Ventas | False | False | nuevo (out_refund + rectificativas aumento) |
| 14 | `AF-` | sale | Autofacturas | False | False | nuevo (self-billing) |
| 15 | `KD-` | sale | Facturas Kit Digital | False | False | nuevo (subvención) |
| 16 | `FVU-` | sale | Facturas Especiales | False | False | nuevo |
| 17 | `L-` | sale | Facturas Laboratorios | False | False | nuevo |
| 8 | `PB-` | purchase | Facturas Gastos | True | False | renombrado desde FACTU stock |
| 18 | `PI-` | purchase | Facturas Inmovilizado | False | False | nuevo (activo fijo) |

**Decisión `AC-` como diario separado** (no como `refund_sequence`
dentro de `A-`): Holded trata `AC-` como serie independiente, incluye
tanto `creditnote` (negativo) como invoices tipo "Abonos" (rectificativas
de aumento, positivas). Si fuera `refund_sequence=True` en `A-`, solo
los `out_refund` recibirían prefijo `AC-`; las rectificativas de
aumento (que en Odoo son `out_invoice` con referencia al original)
quedarían con prefijo `A-`, rompiendo continuidad. UX cost asumido:
al rectificar facturas hay que cambiar journal_id manualmente durante
la ETL.

**Decisión `PB-` con `refund_sequence=True`**: 69 `purchaserefund` en
Holded numerados con prefijo `PR`. Cantidad baja y siempre negativos
→ `refund_sequence=True` natural en Odoo. Durante ETL, primer
`in_refund` posteado se nombra manualmente como `PR-00001` y Odoo
auto-continúa.

`restrict_mode_hash_table=False` en todos: activar es irreversible y
sellar moves debe esperar al post-cutover.

### Posiciones fiscales

`l10n_es_pymes` ya creó las nativas que necesitamos. No se crea
ninguna manualmente:

| Holded → Odoo `account.fiscal.position` | Auto-apply | Uso |
|---|---|---|
| Nacional (default) | `ES Domestic` (id=3) | auto | IVA 21/10/4 estándar interno |
| `Adq.Intracom.*` (compras UE B2B) | `Intra-community` (id=5) | auto, vat_required | inversión sujeto pasivo intracom |
| `s_iva_exento` UE B2C | `EU private` (id=4) | auto | UE consumidor final |
| `s_iva_0_export` USA / extra-UE | `Extra-community` (id=6) | auto | servicios extra-UE |
| `RE Recargo` | `Equivalence surcharge` (id=8) | manual | clientes en RE |
| `ISP nacional` | `National Reverse charge` (id=24) | manual | ISP servicios nacionales |
| `IRPF s_iva_re_*` | `Personal income tax withholding *%` (id=10-22) | manual | profesionales / arrendamientos |
| DUA importaciones | `DUA` (id=27) | manual | importaciones extra-UE de bienes |

Confirmar match exacto durante ETL leyendo `taxes.jsonl` de Holded por
`key` y resolviendo al template de l10n_es por `amount` + `type_tax_use`.

### Plan analítico

Creado `account.analytic.plan` id=2 "Granularidad gasto" (cross-company,
`default_applicability=optional`). Vacío por ahora: durante Fase 5 ETL
se cargarán las cuentas analíticas (`account.analytic.account`) que
preserven la granularidad de las 148 cuentas Holded de 11 dígitos al
colapsar al PGCE Pymes de 4-7 dígitos.

Bot user uid=8 escalado con grupo `analytic.group_analytic_accounting`
para poder gestionar el modelo `account.analytic.plan` vía RPC.

## Mapeo de impuestos Holded → Odoo (Fase 4.5b, 2026-05-11)

### Resumen ejecutivo

- Holded tiene 103 taxes en catálogo; **inpr3mium realmente usa 17**
  (extraído cruzando `products[].taxes` de los 12.212 docs del dump).
- El resto (Bienes usados, Recargo de Equivalencia, IVA 7.5%/12%/5%/2%,
  Importación, Intracom UE en ventas, etc.) **nunca se han utilizado**.
- Hallazgo crítico: `s_iva_exento` (998 líneas) NO es exención Art.20.
  Es **Inversión del Sujeto Pasivo en ventas (Art. 84.Uno.2.g LIVA)**,
  facturado mayoritariamente a GRUPO BIDAFARMA. La descripción literal
  de las facturas lo confirma. En Odoo se mapea a `0% RC` (id=109).
- Holded marca cuentas analíticas tipo `47700000021`, `47200000021`,
  etc. (4 base + 7 analítica). Replicamos esa granularidad creando 14
  subcuentas hijas de `477000`, `472000`, `475100`. Justificación:
  trazabilidad continuity con extractos Holded para Fase 5.

### Tabla de uso real en docs (cross-check del dump)

| Scope | tax key | n líneas | n docs |
|-------|---------|---------:|-------:|
| ventas  | `s_iva_21`              | 15 938 | 3 383 |
| ventas  | `s_iva_exento`          | 998    |    84 (BIDAFARMA → ISP Art.84) |
| ventas  | `s_iva_10`              | 18     |    17 |
| ventas  | `s_iva_4`               | 6      |     6 |
| ventas  | `s_ret_19_prestamos`    | 2      |     2 |
| compras | `p_iva_21`              | 5 913  | 3 968 |
| compras | `p_iva_invsuj`          | 2 749  | 2 595 |
| compras | `p_iva_exento`          | 2 306  | 2 146 (catch-all heterogéneo) |
| compras | `p_iva_adqintras_21`    | 814    |   577 |
| compras | `p_iva_10`              | 762    |   727 |
| compras | `p_ret_19`              | 95     |    95 (préstamos) |
| compras | `p_retrent_19`          | 71     |    71 (alquileres) |
| compras | `p_ret_15`              | 59     |    58 (IRPF profesionales) |
| compras | `p_iva_4`               | 22     |    21 |
| compras | `p_iva_adqintrab_21`    | 3      |     3 |
| compras | `p_ret_7`               | 2      |     2 |
| compras | `s_ret_19` (anómalo)    | 2      |     2 (error captura Holded — ETL Fase 5) |

### Subcuentas creadas en `account.account`

Padres ya existentes: `472000` (input VAT), `477000` (output VAT),
`475100` (HP retenciones acreedora).

| Code | Name | account_type | id |
|------|------|---|----|
| 47200000000 | HP IVA soportado exento | asset_current | 702 |
| 47200000004 | HP IVA soportado 4% | asset_current | 701 |
| 47200000010 | HP IVA soportado 10% | asset_current | 700 |
| 47200000021 | HP IVA soportado 21% | asset_current | 698 |
| 47200000121 | HP IVA soportado servicios intracom 21% | asset_current | 699 |
| 47510000001 | HP Acreedora retenciones IRPF | liability_current | 709 |
| 47510000005 | HP Acreedora retenciones préstamos (cap. mobiliario) | liability_current | 710 |
| 47510000010 | HP Acreedora retenciones alquileres (cap. inmobiliario) | liability_current | 711 |
| 47700000000 | HP IVA repercutido exento | liability_current | 706 |
| 47700000004 | HP IVA repercutido 4% | liability_current | 705 |
| 47700000010 | HP IVA repercutido 10% | liability_current | 704 |
| 47700000021 | HP IVA repercutido 21% | liability_current | 703 |
| 47700000121 | HP IVA repercutido ISP servicios intracom 21% | liability_current | 707 |
| 47700000221 | HP IVA repercutido Inv. Sujeto Pasivo 21% | liability_current | 708 |

### Mapeo Holded.key → Odoo.account_tax

Las 16 taxes mapeadas tienen `description` anotada con `[holded: <key>]`
para trazabilidad — el script de ETL (Fase 5) resuelve `tax_id` por
substring de la `key`.

#### Ventas

| Holded key | Odoo tax | id | Cuenta repartición (tax) | Notas |
|---|---|---:|---|---|
| `s_iva_21`           | 21% S          |   6 | 47700000021 | mainstream |
| `s_iva_10`           | 10% S          |  92 | 47700000010 | residual |
| `s_iva_4`            | 4% S           |  87 | 47700000004 | residual |
| `s_iva_exento`       | 0% RC          | 109 | (sin cuenta — solo tag ISP) | **ISP Art.84.Uno.2.g** — no exención Art.20 |
| `s_ret_19_prestamos` | 19% WHI (sale) | 125 | 279 (HP deudora 4730 genérica) | marginal — 2 líneas |

#### Compras

| Holded key | Odoo tax | id | Cuenta(s) repartición | Notas |
|---|---|---:|---|---|
| `p_iva_21`            | 21% S      |   8 | 47200000021 | mainstream |
| `p_iva_invsuj`        | 21% RC     | 112 | +input 47200000021 / −espejo 47700000221 | **ISP compras** (alquileres B + no-establecidos), 2.749 líneas |
| `p_iva_exento`        | 0% EXEMPT OP |  95 | 47200000000 | catch-all — reclasificar individual en ETL Fase 5 |
| `p_iva_adqintras_21`  | 21% EU S   |   9 | +input 47200000121 / −espejo 47700000121 | adq. intracom. servicios (Google, AWS, SaaS UE) |
| `p_iva_10`            | 10% S      |  64 | 47200000010 | |
| `p_iva_4`             | 4% S       |  55 | 47200000004 | residual |
| `p_iva_adqintrab_21`  | 21% EU G   |  10 | +input 47200000000 / −espejo 47700000000 | adq. intracom. bienes (3 líneas) |
| `p_ret_19`            | 19% WH L   | 159 | 47510000005 | préstamos / capital mobiliario |
| `p_retrent_19`        | 19% WH lease | 131 | 47510000010 | alquileres / capital inmobiliario |
| `p_ret_15`            | 15% WHI    | 148 | 47510000001 | profesionales |
| `p_ret_7`             | 7% WHI     | 133 | 47510000001 | profesionales recién dados de alta |

### Taxes archivadas (27, no usadas por inpr3mium)

Para limpiar el formulario de facturas. Listado por categoría:

- **Recargo de Equivalencia (RE)** — 6 sale: `0% SE`, `0.26% SE`,
  `0.5% SE`, `1% SE`, `1.4% SE`, `5.2% SE`. inpr3mium no factura a
  clientes en RE.
- **Tipos no-estándar (2%, 5%, 7.5%)** — 21 entre sale + purchase
  (`2% G/S`, `2% EU G/S`, `2% EX G/S`, `2% ND`, `5% EU IG`, `5% EX IG`,
  `5% IG`, `7.5% G/S`, `7.5% EU G/S`, `7.5% EX G/S`, `7.5% ND`).
  Rates COVID/transitorios que inpr3mium no aplicó.

Se conservan activos los Withholding (IRPF) en todos los porcentajes
(1/2/7/9/15/18/19/19.5/20/21/24/35%) por si en el futuro aplica algún
caso distinto al actual.

### Doble anotación / Reverse charge en Odoo

Holded modela ISP/intracom con `type:"group"` + `items:[key_1, key_2]`
(dos asientos espejo simultáneos). En Odoo se modela con UNA `account.tax`
que tiene múltiples `account.tax.repartition.line`:

- `21% RC` (id=112) — para `p_iva_invsuj`. Tax lines: +100% a
  `47200000021` (input deducible) y −100% a `47700000221`
  (output devengado como sujeto pasivo). Saldo neto = 0; ambos lados
  pasan al 303 vía tags AEAT distintos.
- `21% EU S` (id=9) — para `p_iva_adqintras_21`. Idem con cuentas
  `47200000121` / `47700000121`.
- `21% EU G` (id=10) — para `p_iva_adqintrab_21`. Idem con cuentas
  `47200000000` / `47700000000`.

Las **tags AEAT** (casillas modelo 303) que vienen con `l10n_es_pymes`
NO se han tocado. Cada repartition line ya apunta a las casillas
correctas (tax tags `[33,34,35,...]`, `[62,63,66,67]`, `[90,91,104,105]`, etc.).
La granularidad analítica de cuentas es ortogonal a las tags 303.

### Casos heterogéneos para resolver en ETL Fase 5

1. **`p_iva_exento` (2.306 docs)** — mezcla:
   - Servicios extra-UE no-detectados como ISP (Nexmo, Zendesk,
     Atlassian) → reclasificar a `21% RC` con `p_iva_invsuj` equivalente.
   - Cheques restaurante (Deujener), prevención (Quirón), transporte
     viajeros → mantener exento Art.20.
   - Renting (Arval, Lease Plan) → revisar IVA implícito en factura.
2. **`s_ret_19` (2 líneas en compras)** — clave de ventas usada en
   purchases. Normalizar al cargar.
3. **`s_iva_exento` con líneas no-Bidafarma** — verificar manualmente
   si todas son ISP Art.84 o hay algún caso real de Art.20.

### Snapshot

`docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.5b.json` con el
estado final post-mapeo: 14 cuentas creadas, 16 taxes con `description`
anotada, 34 repartition lines rewired, 27 taxes archivadas. Total
final: 127 active / 41 inactive.

## Particularidades a resolver durante el ETL

- **Códigos de cuenta de 11 dígitos en Holded** vs 4-8 dígitos en
  Odoo PGCE Pymes. Decidir: ¿colapsar al prefijo de 4-8 (perdiendo
  granularidad analítica) o crear `account.analytic.account` para
  preservar el desglose? Recomendación inicial: colapsar a `account.account`
  PGCE Pymes y mover la granularidad a tags analíticas vía
  `account.analytic.tag` (modelo `account.analytic.distribution`).
- **Capital social tripartito** (3 cuentas `100*`): preservar el
  desglose por socio como analítica o como cuentas separadas dentro
  del 100. Probable preservar.
- **Préstamo FEDEFARMA**: mapear a cuenta de pasivo a corto/largo
  plazo según vencimiento.
- **IRPF retenido**: las 5 cuentas `4751*` deben mapear a las cuentas
  estándar `4751` del PGCE Pymes con conceptos analíticos. Revisar
  con el módulo `l10n_es_aeat_mod111`.
- **Servicios extracomunitarios USA**: durante la migración del
  histórico, las facturas de proveedores USA deben llevar la posición
  fiscal "Servicios Extra-UE" para que el IVA se autoliquide
  correctamente en el 303.

## Riesgos

- API de Holded con rate limits o paginación inestable.
- Plan contable de Holded (con códigos de 11 dígitos) no mapeable 1:1
  con `l10n_es_pymes`. Decisión de granularidad analítica pendiente.
- IVA y cuotas redondeadas distinto entre los dos sistemas → cuadres
  céntimo arriba/abajo en saldos de apertura.
- IRPF retenido: 5 cuentas distintas en Holded → ¿mantener desglose o
  colapsar?

## Cuestiones abiertas (para resolver en Fase 5)

- ¿Cuántos contactos / productos / facturas/año hay aproximadamente?
  (orientativo para diseñar batch size del ETL).
- ¿Plan de Holded incluye API access? Confirmar antes de codificar.
- ¿Hay módulos de Holded usados que no tengan equivalente directo en
  Odoo (CRM con campos custom, proyectos, RRHH)?
- ¿Mantener Holded en read-only post-cutover durante el periodo legal
  de conservación, o exportar todo y dar de baja?
