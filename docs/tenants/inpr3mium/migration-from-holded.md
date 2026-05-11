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

## ETL Fase 5.1 — Diseño detallado (2026-05-11)

Diseño operativo del pipeline Holded → Odoo basado en el dump real
(Fase 4.2.2) y las fundaciones ya aplicadas (Fases 4.3, 4.5b, 5.0).
Esta sección **supersede** el esqueleto inicial "ETL — pasos previstos"
de más arriba, que se conserva como referencia histórica del scope
borrador.

### Preconditions asumidas

Cuando se ejecute el ETL la instancia Odoo destino tiene:

- Plan contable `l10n_es_pymes` con 14 subcuentas IVA + 6 cuentas 521x
  tarjetas + 4 cuentas `5720...` bancos productivos.
- 12 `account.journal` (8 Fase 4.3 + 4 bank Fase 5.0).
- 29 `account.fiscal.position` (Fase 4.4 snapshot).
- 16 `account.tax` con `description` anotada `[holded: <key>]` y 34
  `repartition_line.account_id` apuntando a las subcuentas analíticas.
- Defaults empresa: `21% S` sale + purchase, income `705000`, payment
  term `15 Days`, snapshot `treasury_id → journal_id` disponible en
  `snapshots/2026-05-11_fase-5.0.json`.
- Plan analítico id=2 "Granularidad gasto" creado (vacío) para preservar
  granularidad 11-dig en cuentas analíticas.

### Estrategia general

**Idempotencia por ext_id**. Cada record Holded importado se persiste
en `ir.model.data` con un XML-ID derivado del id Holded, vía
`ext_id_upsert.py` (skill `odoo-functional-admin`). Esquema:

| Resource Holded | XML-ID Odoo |
|---|---|
| `contacts[i]` | `__holded__.contact_<contactId>` |
| `products[i]` | `__holded__.product_<productId>` |
| `services[i]` | `__holded__.service_<serviceId>` |
| `expensesaccount[i]` + `saleschannels[i]` | `__holded__.account_<accountNum_11d>` |
| `treasuries[i]` | (ya mapeado en snapshot 5.0; no se importa) |
| `documents.<type>[i]` | `__holded__.<type>_<docId>` |
| `payments[i]` | `__holded__.payment_<paymentId>` |
| `dailyledger[i]` | `__holded__.ledger_<entryId>` |

Permite reejecutar el ETL N veces (5.3 subset → 5.4 histórico → 5.5
cutover) sin duplicar.

**Batch y reanudación**. 12.212 documents + 7.489 PDFs + 708 payments +
2.250 ledger entries. Procesar en batches de 100 docs por loader
(límite RPC práctico). Cada batch escribe `etl-state/<run-id>/cursor.json`
con `{loader, last_id_processed, batch_n}`. Si falla, se relanza desde
el cursor. Tiempo estimado total ~2-3 h (dominado por upload de PDFs).

**Modo `--dry-run`**. Cada loader valida resolución de FKs sin escribir.
Crítico para 5.3 (validación subset). Genera report `dry_run_<loader>.csv`
con `{record_id, fk_resolution_status, missing_deps}`.

### Resolvers

4 funciones puras en `holded_resolvers.py` (a crear en
`docs/tenants/inpr3mium/etl/`). Cada una idempotente y testeable sin
red.

#### `resolve_partner(contact: dict) -> int`

1. Si `contact.vatnumber` no vacío → normalizar (`strip()`, `upper()`,
   prepend `ES` si solo dígitos+letra control válidos) → buscar
   `res.partner` por `vat`. Si hit, return.
2. Si no, buscar por `ir.model.data` xml-id `contact_<id>`.
3. Si no, crear con ext_id `__holded__.contact_<id>` y los vals de la
   tabla "Transformaciones → Partners" más abajo.
4. Si `name` contiene `"(NO USAR)"`: crear con `active=False`.

**Caveat 1.149 invoices `contactId` no resoluble** (33.5% del histórico):
política decidida en 5.1 → crear partner placeholder único
`__holded__.contact__unknown` ("Cliente histórico no identificado"),
todos los docs sin contact apuntan ahí. Pérdida de detalle aceptada
(info ya perdida en Holded). Impacto AEAT 347: ninguno (el placeholder
agrupado no supera el umbral 3.005,06€ contra ningún cliente real).

#### `resolve_tax(tax_key: str, ctx: dict) -> int`

`ctx` lleva `{doc_type, partner_country, line_account_hint}` para
resolver catch-alls.

1. Lookup directo: `account.tax` con `description LIKE '%[holded: <key>]%'`
   (anotación Fase 4.5b). Si hit único, return.
2. Si el `key` es ambiguo, aplicar `tax_reclassification.yaml`
   (deuda técnica documentada en 4.5b "Casos heterogéneos"):

   - `p_iva_exento` (2.306 docs, catch-all):
     - `partner_country ∈ {US, AU, HK, CN, UK_post_brexit}` y categoría
       SaaS → **revisar**: Odoo `21% RC` (id=112) modela ISP nacional;
       para servicios extra-UE corresponde tax distinto. Marcar como
       reclasificación pendiente y aplicar `0% EXEMPT OP` (id=95)
       temporalmente con flag `etl_review=True` en la `move.narration`.
     - `partner ∈ {Cheque Dejeuner, Quirón, RENFE, ARVAL, LEASE PLAN}`
       → mantener `0% EXEMPT OP` (id=95) → exento Art.20 LIVA real.
     - Fallback: `0% EXEMPT OP` + flag review.
   - `s_ret_19` en `doc_type ∈ {purchase, purchaserefund}` (2 líneas):
     → mapear a `19% WH L` (id=159) — es retención de capital
     mobiliario captada con clave de ventas por error en Holded.

3. Si key no existe en catálogo Holded → **ABORT batch** con error
   explícito. No inventar tax silenciosamente.

#### `resolve_journal(doc_type: str, doc_code: str) -> int`

Lookup en `account.journal` por `code` extraído del prefijo de
`docNumber`:

| Prefijo Holded | Journal Odoo | id |
|---|---|---:|
| `A-` | `A-` (sale) | 7 |
| `AC-` | `AC-` (sale) | 13 |
| `L-` | `L-` (sale) | 17 |
| `FVU-` | `FVU-` (sale) | 16 |
| `KD-` | `KD-` (sale) | 15 |
| `AF-` | `AF-` (sale) | 14 |
| `PB-` | `PB-` (purchase, `refund_sequence=True`) | 8 |
| `PI-` | `PI-` (purchase) | 18 |
| `PR-` (auto-derivado en `in_refund` de `PB-`) | (no se setea: `account.move.reversal`) | — |

**Excepción `purchaserefund`** (PR-): NO crear `account.move`
directamente. Usar `account.move.reversal.action_reverse()` sobre el
`PB-` original (resuelto vía `reversed_entry_id` por ext_id Holded del
purchase referenciado en `purchaserefund.relatedDocs`). Si el doc PR
no tiene relación a un PB- previo, crear `account.move` tipo
`in_refund` en `PB-` y consumirá `refund_sequence` PR-NNN.

#### `resolve_account(holded_acct: str | None, fallback_ctx: dict) -> int`

1. Si `holded_acct` es un código 11-dig: buscar `account.account.code`
   exacto. Si hit, return.
2. Si no existe (caso esperado para 148 expensesaccount + 38
   saleschannels que se cargan en paso 0), crear como hijo del prefijo
   PGCE raíz `code[:3] → padre`:

   | Prefijo 11-dig | Padre PGCE | account_type | Ya creado en |
   |---|---|---|---|
   | `5720XXXXXXX` | 572000 | asset_current | Fase 5.0 |
   | `521XXXXXXXX` | 521000 | liability_current | Fase 5.0 |
   | `47200000XXX` | 472000 | asset_current | Fase 4.5b |
   | `47700000XXX` | 477000 | liability_current | Fase 4.5b |
   | `47510000XXX` | 475100 | liability_current | Fase 4.5b |
   | `60XXXXXXXXX..62XXXXXXXXX..69XXXXXXXXX` | 6XX000 | expense | Fase 5.1 paso 0a |
   | `7000XXXXXXX` | 700000 | income | Fase 5.1 paso 0b |
   | `7050XXXXXXX` | 705000 | income | Fase 5.1 paso 0b |
   | `7080XXXXXXX` | 708000 | income | Fase 5.1 paso 0b |

3. Si no hay padre PGCE estándar mapeable → ABORT con error
   (`tax_reclassification.yaml` debe extenderse antes de continuar).

### Orden de carga

Dependencias estrictas, cada paso es batch independiente con commit
propio. Si un paso falla, los anteriores no se revierten (el ext_id
permite reanudar limpiamente).

| # | Loader | Modelo Odoo | Volumen | Dependencias |
|---|---|---|---:|---|
| 0a | `loader_expenseaccounts.py` | `account.account` (subcuentas 6XX) | 148 | l10n_es_pymes |
| 0b | `loader_saleschannels.py` | `account.account` (subcuentas 70X) | 38 | l10n_es_pymes |
| 1 | `loader_partners.py` | `res.partner` | 3.363 + 1 unknown | — |
| 2 | `loader_products.py` | `product.template` + `product.product` | 2.009 | 1, 0a, 0b, taxes |
| 3 | `loader_invoices.py` | `account.move` (out_invoice) posted | 3.430 | 1, 2 |
| 4 | `loader_purchases.py` | `account.move` (in_invoice) posted | 7.998 | 1, 0a |
| 5 | `loader_creditnotes.py` | `account.move` (out_refund) posted | 678 | 3 |
| 6 | `loader_purchaserefunds.py` | `account.move` (in_refund) posted | 69 | 4 |
| 7 | `loader_payments.py` | `account.payment` reconciled | 701 (708 − 7 excluidos) | 3, 4, 5, 6 |
| 8 | `loader_dailyledger.py` | `account.move` (entry) | ~800-1.500 (filtrado) | 0a, 0b |
| 9 | `loader_attachments.py` | `ir.attachment` (PDFs) | 7.489 | 3, 4 |
| 10 | `validate_etl.py` | — | — | 1-9 |

**Notas de orden**:

- **Paso 0 antes que todo**: las subcuentas 6XX/70X deben existir antes
  de cargar líneas de docs con esos códigos. Idempotente — el segundo
  run no crea duplicados.
- **Paso 8 (dailyledger) filtrado**: NO cargar entries cuya
  contrapartida ya está creada por loaders 3-6. Heurística: si el entry
  tiene `documentId` resoluble a un doc ya cargado, SKIP. Lo que queda
  son aperturas/cierres anuales, remesas, pagarés, ajustes manuales.
  Volumen estimado 800-1.500 de los 2.250 (ver "Riesgos" para
  mitigación).
- **Paso 9 (PDFs) opcional en 5.3**: en validación subset 2024+2025
  saltar PDFs (ahorra ~200 MB upload). Activar en 5.4 (histórico
  completo). En 5.5 cutover, PDFs del año corriente se han adjuntado ya.

### Transformaciones por modelo

#### Partners (`contacts.jsonl` → `res.partner`)

| Holded | Odoo | Notas |
|---|---|---|
| `id` | ext_id `contact_<id>` | |
| `name` | `name` | Strip `"(NO USAR)"` y `active=False` si presente |
| `vatnumber` | `vat` | Normalizar: `ES` + dígitos+control; si `country!=ES` usar prefijo país |
| `code` | `ref` | Código interno Holded |
| `tradeName` | `commercial_partner_id.name` | Solo si difiere de `name` |
| `email` | `email` | |
| `mobile`, `phone` | `mobile`, `phone` | |
| `billAddress.address` | `street` | |
| `billAddress.city` | `city` | |
| `billAddress.postalCode` | `zip` | |
| `billAddress.country` | `country_id` | Resolver `res.country` por ISO2 |
| `billAddress.province` | `state_id` | Lookup `res.country.state` por name (ES) |
| `type` | `customer_rank` / `supplier_rank` | `client`→cust=1; `supplier`→supp=1; si VAT aparece en ambos → ambos=1 |
| `groupId` | `category_id` (m2m) | Solo si grupo Holded tiene equivalente en `res.partner.category` |

Dedup por VAT: si dos contacts Holded comparten VAT (cliente+proveedor
con NIF), una sola `res.partner` con ambos ranks. El segundo contact
queda apuntando vía ext_id al mismo `res.partner.id`.

#### Productos (`products.jsonl` + `services.jsonl` → `product.template`)

| Holded | Odoo | Notas |
|---|---|---|
| `id` | ext_id `product_<id>` / `service_<id>` | |
| `name` | `name` | |
| `sku` | `default_code` | |
| `barcode` | `barcode` | |
| `price` | `list_price` | |
| `cost` | `standard_price` | |
| `tax` (key) | `taxes_id` | `resolve_tax(tax, {doc_type: 'sale'})` |
| `purchaseTax` (key) | `supplier_taxes_id` | `resolve_tax(purchaseTax, {doc_type: 'purchase'})` |
| `accountNum` | `property_account_income_id` (services) / `property_account_expense_id` | `resolve_account(accountNum, ctx)`. **Importante en Odoo 19**: estos son `company_dependent`, se setean vía `ir.default` no como write directo |
| `categoryId` | `categ_id` | Lookup `product.category` por name (crear si falta) |
| `type` | `type` | `service` (services) o `consu` (products físicos); `consu` por defecto en Odoo 19 |

#### `account.move` (invoice/purchase/creditnote/purchaserefund)

Loop por doc:

```python
move_vals = {
    'move_type': {
        'invoice': 'out_invoice',
        'purchase': 'in_invoice',
        'creditnote': 'out_refund',
        'purchaserefund': 'in_refund',
    }[doc.type],
    'partner_id': resolve_partner(doc.contact),
    'invoice_date': iso_from_unix(doc.date),
    'invoice_date_due': iso_from_unix(doc.dueDate) if doc.dueDate else False,
    'journal_id': resolve_journal(doc.type, doc.docNumber),
    'ref': doc.docNumber,            # núm original Holded (auditoría)
    'narration': doc.description,
    'invoice_payment_term_id': resolve_payment_term(doc.paymentTerms),
    # fiscal_position_id se autoaplica vía partner.country + l10n_es_pymes
    'invoice_line_ids': [(0, 0, build_line(item, doc)) for item in doc.items],
}

# build_line(item, doc):
{
    'name': item.name,
    'quantity': item.units,
    'price_unit': item.subtotal / item.units if item.units else 0.0,
    'discount': item.discount or 0.0,
    'product_id': resolve_product(item.productId) if item.productId else False,
    'account_id': resolve_account(
        item.account                                   # 1ª prioridad: cuenta línea
        or (item.channelId and channel.accountNum)     # 2ª: cuenta saleschannel
        or product.accountNum,                         # 3ª: cuenta producto
        ctx={'doc_type': doc.type},
    ),
    'tax_ids': [(6, 0, [resolve_tax(item.tax, ctx)])],
    'analytic_distribution': (
        {channel_analytic_id: 100.0} if item.channelId else False
    ),
}
```

**Casos especiales**:

- **out_refund (creditnote)**: si `doc.related_invoice_id` resoluble en
  invoices ya cargadas → setear `reversed_entry_id = move_invoice_id`.
  Refund standalone si no.
- **in_refund (purchaserefund)**: via `account.move.reversal.action_reverse()`
  sobre el PB- original. Journal `PB-` con `refund_sequence=True` da
  prefijo `PR-` automático.
- **`name` vs `ref`**: `name` lo asigna Odoo desde `journal.sequence`;
  `ref = doc.docNumber` preserva el código Holded original para
  auditoría. Tras pre-loading de secuencias (Fase 5.5), `name == ref`
  para el período post-cutover.
- **Decimal mismatch IVA**: si `|doc.tax_total - move.amount_tax| > 0.02€`
  por línea tras `action_post()`, abortar batch y log. Causa probable:
  `account.tax.rounding_method` distinto entre Holded
  (`round_globally`) y Odoo default (`round_per_line`). Mitigación
  evaluar en 5.3 con sample.
- **Post inmediato vs deferred**: postear en el mismo batch tras crear,
  no diferir. Si `action_post()` falla, rollback de ese doc y registrar
  en `etl-state/<run-id>/failed_moves.jsonl` con la excepción para
  revisión manual.

#### `account.payment` (`payments.jsonl`)

```python
payment_vals = {
    'partner_id': resolve_partner(payment.contact),
    'amount': abs(payment.amount),
    'date': iso_from_unix(payment.date),
    'journal_id': SNAPSHOT_5_0['treasury_to_journal'][payment.treasuryId],
    'payment_type': 'inbound' if payment.amount > 0 else 'outbound',
    'partner_type': 'customer' if payment.contact_type == 'client' else 'supplier',
    'ref': payment.description,
}
# reconciliación posterior:
if payment.docs:
    payment.reconciled_invoice_ids = [
        (4, resolve_move(d.id)) for d in payment.docs
    ]
```

Caveats:

- **26 pagos sin `treasuryId`** → loggear y asignar a journal "Banco
  Suspense" (crear si falta) con flag `etl_review=True`.
- **7 pagos en `treasury 55500000007`** → NO `account.payment`; crear
  `account.move` tipo `entry` con contrapartida `555 Partidas pendientes
  de aplicación`. Cuenta 555 se crea en paso 0 si no existe.
- **`paymentMethod` vacío** (gotcha del dump): default `manual`. Cruzar
  con `documents.<type>.paymentMethod` si está informado. SEPA DD se
  resuelve en 5.4 vía `remittances.jsonl` (módulo OCA diferido).

#### `dailyledger` (entries manuales) → `account.move` tipo entry

Pre-filtrado obligatorio: descartar entries cuya contrapartida ya está
creada por loaders 3-6.

Heurística:

```python
def is_doc_counterpart(entry):
    # Si todas las líneas del entry tocan cuentas 430x/410x con partner
    # resoluble y el `description` matchea un docNumber ya cargado en
    # account_move.ref, es contrapartida de un doc.
    for line in entry.lines:
        if line.account_code.startswith(('430', '410')):
            ref_match = re.search(r'(A-|PB-|AC-|...|)\d+', entry.description)
            if ref_match and move_exists_by_ref(ref_match.group()):
                return True
    return False
```

Lo que queda (~800-1.500 entries):

- **Aperturas anuales** (1 enero × 8 años ≈ 50 entries cada): contrapartida
  `129x` (resultado pendiente aplicación). Journal "Apertura" (crear).
- **Cierres anuales** (31 diciembre): contrapartida `129x`. Journal "Cierre".
- **Remesas SEPA outbound**: cargo masivo banco. Journal del banco
  emisor (resuelto vía snapshot 5.0).
- **Pagarés**: entries con cuenta `401`/`411`. Journal "Miscellaneous".
- **Ajustes IVA/IRPF trimestral**: contrapartida `4750`/`4751`.

Loader genera report `dailyledger_classification.csv` pre-load con
`{entry_id, classification, filter_status}` para revisión humana antes
de aplicar.

#### PDFs → `ir.attachment`

```python
attachment_vals = {
    'name': f'{doc.docNumber}.pdf',
    'res_model': 'account.move',
    'res_id': move_id,
    'type': 'binary',
    'datas': b64encode(read_bytes(f'pdfs/{doc.type}/{doc.id}.pdf')),
    'mimetype': 'application/pdf',
}
```

Solo aplica a docs con PDF original escaneado:

| Tipo | PDFs disponibles | Estrategia |
|---|---:|---|
| invoice (2018-2026) | 3.430 | adjuntar todos |
| purchase (2022+) | 4.059 | adjuntar todos |
| purchase (2018-2021) | 0 | sin PDF — solo move desde dailyledger asientos manuales |

### Validaciones post-load

Tras cada loader (no solo al final), queries de cuadre que deben pasar.

#### Cuadre por journal vs dump

```sql
SELECT j.code, COUNT(am.id) AS n, SUM(am.amount_total) AS total
FROM account_move am
JOIN account_journal j ON j.id = am.journal_id
WHERE am.state = 'posted' AND am.create_uid IN (SELECT id FROM res_users WHERE login = 'bot.contable')
GROUP BY j.code ORDER BY j.code;
```

vs

```bash
jq -s 'group_by(.type) | map({type: .[0].type, n: length,
       total: ([.[].total] | add | floor)})' \
   docs/tenants/inpr3mium/holded-export/2026-05-11/documents.*.jsonl
```

Tolerancia: 0€ exacto (módulo redondeo céntimo declarado).

#### Balance partners (430/410)

```sql
SELECT p.name, SUM(aml.debit - aml.credit) AS balance
FROM account_move_line aml
JOIN account_move am ON am.id = aml.move_id
JOIN account_account a ON a.id = aml.account_id
JOIN res_partner p ON p.id = aml.partner_id
WHERE a.code IN ('430000', '410000') AND am.state = 'posted'
GROUP BY p.id, p.name
HAVING ABS(SUM(aml.debit - aml.credit)) > 0.01
ORDER BY balance DESC LIMIT 50;
```

Spot-check: BIDAFARMA, UNNEFAR, P&G con balance ~0 al final del
histórico salvo facturas vivas del año en curso. Si un cliente
histórico aparece con balance no-0 → falta `account.payment` o pago
reconciliado mal.

#### Cuadre IVA por trimestre vs modelo 303 presentado

```sql
SELECT EXTRACT(YEAR FROM am.date) AS y,
       EXTRACT(QUARTER FROM am.date) AS q,
       a.code, ROUND(SUM(aml.debit), 2) AS d, ROUND(SUM(aml.credit), 2) AS c
FROM account_move_line aml
JOIN account_move am ON am.id = aml.move_id
JOIN account_account a ON a.id = aml.account_id
WHERE (a.code LIKE '472%' OR a.code LIKE '477%' OR a.code LIKE '4751%')
  AND am.state = 'posted'
GROUP BY y, q, a.code ORDER BY y, q, a.code;
```

Spot-check Q1 2024 vs PDF del 303 presentado: tolerancia ±5€ por
casilla (redondeo + algún ajuste manual).

#### Conteo final

| Modelo Odoo | Esperado | Aserción |
|---|---:|---|
| `res.partner` con ext_id `contact_*` | 3.363 + 1 unknown | `count == 3.364` |
| `product.template` con ext_id `product_*` o `service_*` | 2.009 | `count == 2.009` |
| `account.move` out_invoice posted | 3.430 | exacto |
| `account.move` in_invoice posted | 7.998 | exacto |
| `account.move` out_refund posted | 678 | exacto |
| `account.move` in_refund posted | 69 | exacto |
| `account.payment` con `state=posted` | 701 | 708 − 7 excluidos (treasury 555) |
| `account.move` type entry (manual) | 800-1.500 | rango |
| `ir.attachment` res_model=account.move | 7.489 | exacto (si 9 ejecutado) |

### Implementación

**Decisión 5.1**: scripts ad-hoc en `docs/tenants/inpr3mium/etl/`, no
nueva skill. Justificación:

- fedefarma migra desde Axional, no Holded → no reusable cross-tenant.
- Los loaders dependen de decisiones concretas inpr3mium (regla
  catch-all `p_iva_exento`, sales channels específicos) → bundle
  reutilizable sería over-engineering.
- Si en 5.3 los scripts resultan limpios y un futuro tenant Holded
  aparece, se promueve a skill `holded-to-odoo` en 5.4.

Estructura:

```
docs/tenants/inpr3mium/etl/
├── holded_resolvers.py        # 4 resolvers + cache
├── tax_reclassification.yaml  # reglas heurísticas catch-alls
├── loader_expenseaccounts.py  # paso 0a
├── loader_saleschannels.py    # paso 0b
├── loader_partners.py         # paso 1
├── loader_products.py         # paso 2
├── loader_invoices.py         # paso 3
├── loader_purchases.py        # paso 4
├── loader_creditnotes.py      # paso 5
├── loader_purchaserefunds.py  # paso 6
├── loader_payments.py         # paso 7
├── loader_dailyledger.py      # paso 8
├── loader_attachments.py      # paso 9
├── validate_etl.py            # paso 10
└── README.md                  # cómo lanzar + estado actual
```

Cada loader: `argparse` con `--dump-dir`, `--dry-run`, `--limit N`,
`--resume`. Reusa `OdooClient` del `odoo_client.py` (skill
`odoo-functional-admin`) vía `sys.path` injection o copia local.
`ext_id_upsert` reutilizado para idempotencia.

### Riesgos identificados en 5.1

1. **Catch-all `p_iva_exento`** (2.306 docs) requiere reclasificación
   por proveedor. Riesgo: modelo 303 histórico mal cuadrado. **Mitigación**:
   aplicar `tax_reclassification.yaml` en 5.3 subset 2024-2025, spot-check
   100 docs aleatorios con operador antes de 5.4 histórico.
2. **1.149 invoices con `contactId` no resoluble** (33.5%): partner
   placeholder único acepta pérdida de detalle. Sin impacto AEAT 347.
3. **Decimal mismatch IVA Holded↔Odoo**: tolerancia ±0.02€/línea antes
   de abortar. Si >50 líneas/batch con mismatch, revisar
   `account.tax.rounding_method` global. Decisión inicial: mantener
   `round_per_line` (Odoo default). Validar en 5.3.
4. **`dailyledger` heurística de filtrado** puede dejar duplicados o
   saltar aperturas. **Mitigación**: dry-run produce
   `dailyledger_classification.csv` (entries clasificados como
   contrapartida-de-doc vs manual). Operador revisa manualmente antes
   de cargar.
5. **Sequences pre-loading vs subset 5.3**: si 5.3 carga subset sin
   pre-loading, los moves de validación consumirán `A-1`, `A-2`...
   (Odoo default). **Política**: tras 5.3, BORRAR todos los moves con
   `ext_id LIKE '__holded__.invoice_%'` antes de 5.4. Cuando 5.5
   ejecute el pre-loading, las secuencias arrancan limpias desde el
   counter Holded+1.
6. **Saleschannels no aparecen en `documents.*.jsonl`** (gotcha 4.2.2):
   la asignación canal↔línea vive en `product.channelId` o
   `line.channelId`. Confirmar en 5.3 leyendo un sample de docs JSONL
   crudo si el campo se preserva en el dump.

### Entregables de Fase 5.1

- [x] Esta sección redactada (single source of truth diseño ETL).
- [ ] `holded_resolvers.py` esqueleto + tests offline (a crear en 5.3).
- [ ] `tax_reclassification.yaml` con reglas heurísticas
  `p_iva_exento` (redactar con operador antes de 5.3).
- [ ] Pre-loading subcuentas (paso 0a + 0b) — dry-run validado contra
  dump 2026-05-11 antes de 5.3.

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
