# Dump analysis — inpr3mium @ 2026-05-11

Análisis ejecutivo del dump completo de Holded (`holded-export/2026-05-11/`)
para informar el diseño de ETL (Fase 5.1+) y dimensionar cargas. Este
archivo es un **snapshot en el tiempo** — los volúmenes cambian con
cada nuevo dump.

## Volumen por resource

| Resource | Items | Notas |
|---|---:|---|
| contacts | 3.363 | Solo 536 únicos aparecen en docs (16%). El resto declarados sin actividad. |
| products | 1.569 | Catálogo amplio, PLV/marketing |
| services | 440 | Servicios profesionales |
| expensesaccount | 148 | Plan contable de gasto Holded; solo 31 con uso real en dailyledger |
| treasuries | 12 | 4 bancos productivos + 4 tarjetas + 4 omitir |
| taxes | 103 | Solo 17 keys reales en docs (ver `holded-tax-mapping.md`) |
| saleschannels | 38 | Líneas de producto/canales con código contable 70X |
| payments | 708 | Pagos en banco; solo Santander/Qonto/Sabadell tienen volumen real |
| remittances | 85 | SEPA inbound (recibos domiciliados desde clientes) |
| numbering_series | 10 | 7 ventas + 3 compras |
| documents.invoice | 3.430 | A-, L-, FVU-, KD-, AF- + abonos AC- |
| documents.purchase | 7.998 | PB-, PI- |
| documents.creditnote | 678 | Rectificativas formales (AC-) |
| documents.purchaserefund | 69 | PR- |
| documents.proform | 34 | Proformas |
| documents.estimate | 3 | Presupuestos (apenas usado) |
| documents.{salesorder,salesreceipt,waybill,purchaseorder} | 0 | NO usados — Holded los ofrece, inpr3mium no |
| dailyledger | 2.250 | **Solo asientos manuales + aperturas** (ver "limitaciones") |
| **Total docs** | **12.212** | Histórico 2018-2026 |
| **PDFs descargados** | **7.489** | 3.430 invoice + 4.059 purchase. 3.939 purchases sin PDF (asientos manuales) |

## Distribución temporal

Volumen anual estable. inpr3mium opera desde **2018** sin huecos.

### Invoices (3.430 ventas)

| Año | N | Año | N |
|---|---:|---|---:|
| 2018 | 418 | 2023 | 384 |
| 2019 | 414 | 2024 | 339 |
| 2020 | 553 (peak) | 2025 | 362 |
| 2021 | 484 | 2026 | 166 (parcial, hasta mayo) |
| 2022 | 310 | | |

### Purchases (7.998 compras)

Volumen ~1.000/año estable 2018-2024 (ratio purchase:invoice ≈ 2:1).
**2025 baja a 841** (señal a investigar — puede ser cambio de modelo
operativo, asesoría externa que dejó de facturar mensualmente, etc.).

### Creditnotes (678)

Empiezan a registrarse en 2022 (80 docs). Antes posiblemente se usaban
como invoice negativo. Pico 2023 (206), tendencia decreciente.

### purchaserefund (PR-)

Bajo volumen total (69 docs en 8 años). Justifica decisión Fase 4.3:
`refund_sequence=True` en `PB-` en lugar de journal separado.

## Concentración de clientes — pareto extremo

**148 clientes únicos** generan los 3.430 invoices (de 2.362 declarados;
2.214 nunca facturaron). Top concentración:

| Cliente | Docs | % de invoices |
|---|---:|---:|
| _(contactId no resoluble)_ | 1.149 | 33.5% |
| GRUPO BIDAFARMA S.C.A.S.G. | 807 | 23.5% |
| UNNEFAR S.COOP. | 717 | 20.9% |
| PROCTER GAMBLE ESPAÑA S.A.U. | 135 | 3.9% |
| VADEFARMA S.L. | 106 | 3.1% |

**Top 3 (BIDAFARMA + UNNEFAR + P&G) = 1.659 docs (48% del total).**

Implicaciones para Fase 5:

- 1.149 docs con `contactId` no resoluble (33.5%) — son facturas donde
  el contacto se borró o nunca se creó como contact en Holded.
  **Hipótesis**: facturas one-off a clientes ad-hoc. Investigar en
  Fase 5.1 antes del ETL.
- BIDAFARMA es el cliente que justifica el peso del ISP (`s_iva_exento`
  = ISP Art.84, 998 líneas — ver `holded-tax-mapping.md`).
- Justifica priorizar la migración del histórico de los top 5
  clientes como subset de validación 5.3.

## Proveedores — base SaaS internacional

**388 proveedores únicos** generan los 7.998 purchases (de 811
declarados). Top:

| Proveedor | Docs | Notas |
|---|---:|---|
| DURAN SINDREU S.L.P. | 451 | Asesoría fiscal/legal mensual |
| _(no resoluble)_ | 308 | A investigar |
| ATLASSIAN PTY LTD | 289 | SaaS Australia (Jira/Confluence) — `p_iva_adqintras_*` |
| ZENDESK, INC. | 269 | SaaS USA — `p_iva_exento` extra-UE |
| ARTYPLAN S.L. | 248 | Imprenta PLV |
| CHEQUE DEJEUNER S.A. | 212 | Cheques restaurante / formación |
| GOOGLE IRELAND LIMITED (NO USAR) | 196 | Marcado deprecado por operador |
| MOLDTRANS S.L. | 178 | Transporte |
| ACKSTORM S.L. | 172 | Servicios IT |
| SENDGRID (NO USAR) | 152 | Marcado deprecado |
| BANCO SANTANDER S.A | 152 | Cargos/comisiones bancarias |
| VONAGE BUSINESS INC (NEXMO) | 139 | SaaS comunicaciones |
| ADOBE SYSTEMS SOFTWARE IRELAND LTD | 138 | SaaS intracom UE |
| RENFE OPERADORA | 127 | Billetes tren |
| GODADDY | 123 | Dominios |

**Patrones a manejar en ETL**:

- Partners con sufijo `"(NO USAR)"` (GOOGLE, SENDGRID, posiblemente
  otros) → partners deprecados/duplicados. Crear como `active=False`
  en Odoo o consolidar con el nuevo nombre.
- Mix intra-UE (Atlassian Australia es extra-UE, Adobe/Google Ireland
  intra-UE, Zendesk USA extra-UE) — fiscal positions auto-apply de
  Odoo deberían encargarse, pero validar con sample en 5.3.

## Distribución geográfica de contactos

| País | N | Régimen IVA típico |
|---|---:|---|
| España | 3.205 (95.3%) | Doméstico 21/10/4 + ISP / IRPF |
| Estados Unidos | 62 | Extra-UE servicios (`0% Exempt`) |
| Irlanda | 17 | Intra-UE servicios (`21% EU S`) |
| Alemania | 12 | Intra-UE |
| Australia | 8 | Extra-UE (Atlassian) |
| Hong Kong | 7 | Extra-UE |
| Francia | 6 | Intra-UE |
| Reino Unido | 5 | Post-Brexit: extra-UE servicios |
| China | 5 | Extra-UE |
| Otros (Luxemburgo, Países Bajos, Estonia, Suiza) | 11 | Intra-UE / Suiza extra |
| Sin país | 12 | A inferir |

**94.6% con NIF/VAT informado** — calidad alta de partner master data,
buena base para ETL sin re-validación masiva.

## Pagos por banco (treasury_id real)

Aporta evidencia clave para Fase 5.0.1 (priorización de bank journals):

| Treasury | N pagos | Net amount moved | Status |
|---|---:|---:|---|
| Santander | 365 | -27.050€ | **Banco principal de pago** |
| Qonto | 216 | +19.794€ | **Banco principal de cobro** (cuotas/SaaS) |
| Banco Sabadell | 87 | +22.513€ | Operativo secundario |
| (sin bankId / vacío) | 26 | 0€ | Pagos sin asignar a banco |
| BBVA | 7 | -16.121€ | Esporádico (operaciones grandes) |
| 55500000007 | 7 | -1€ | NO bank real (cuenta 555 pendientes) |

Observación: el conteo por *pagos* difiere de los movimientos contables
en dailyledger (BBVA 7 pagos vs 130 movs en dailyledger porque
dailyledger incluye apuntes manuales sin pago Holded asociado).

## Remesas (SEPA inbound)

85 remesas, todas `type=inbound` (cobro domiciliado a clientes).
Treasury principal: Santander (83 remesas), Banco Sabadell (2).

Implica que **inpr3mium emite remesas SEPA Core Direct Debit**. Para
Odoo Fase 5+: necesita módulo OCA `account_banking_sepa_direct_debit`
+ mandatos por cliente (`account.payment.method`). Actualmente
**diferido** en `profile.yaml.deferred_modules` — reabrir cuando se
arranque la operativa real post-cutover.

## Sales channels (38 canales)

Cada sales channel tiene un código contable de **11 dígitos** que
empieza por `7080011XXXX`, `7080013XXXX`, `7000011XXXX`, etc. (cuentas
del grupo 70 PGCE). Refleja la **segmentación analítica de ingresos**
por línea de servicio:

- `7000011XXXX` (familia 700) — productos físicos / mercaderías.
- `7050013XXXX` (familia 705) — servicios prestados.
- `7080011XXXX` (familia 708) — devoluciones y ajustes.

Top channels representativos:

- CUOTA MENSUAL FARMAPREMIUM (70000111001) — producto principal.
- CUOTA CANAL BIDA (70000113006) — específico BIDAFARMA.
- COSTE VARIABLE PUNTOS (70000111002).
- CUOTA INTEGRACION FARMATIC/NIXFARMA (130002/3).
- GESTIÓN CLIENTES KIT DIGITAL (113005).
- Múltiples variantes FREE TRIAL (70800XXXXXX) — ingresos cero por
  contrapartida (descuentos otorgados durante trial).

**Implicación para Fase 5**: el ETL necesita una tabla de mapeo
`saleschannel.accountNum → account.account Odoo` con 38 entradas.
Estos 38 codes 11-dig deben replicarse como subcuentas de 700/705/708
en Odoo (mismo patrón que IVA/bancos en 4.5b — ver `decisions-log.md`).

Cobertura: los 38 channels NO aparecen referenciados en
`documents.*.jsonl` con campo `channelId` (Holded los usa solo en
`products[].channelId` o `lines[].channelId`). Validar en 5.1 cómo
recuperar la asignación canal↔línea de doc durante el ETL.

## expensesaccount (148 cuentas) — uso real

Distribución por prefijo:

| Prefijo PGCE | Concepto | N cuentas |
|---|---|---:|
| 621 | Arrendamientos y cánones | 39 |
| 627 | Publicidad y propaganda | 23 |
| 623 | Servicios profesionales independientes | 18 |
| 640 | Sueldos y salarios | 9 |
| 629 | Otros servicios | 7 |
| 622 | Reparaciones y conservación | 7 |
| 626 | Servicios bancarios | 6 |
| 600 | Compras de mercaderías | 6 |
| 642 | Seguridad Social a cargo empresa | 3 |
| 680/681 | Amortizaciones | 6 |
| 678 | Gastos excepcionales | 3 |
| 631 | Tributos | 3 |
| 649 | Otros gastos sociales | 2 |
| 630 | Tributos beneficios | 2 |
| Otros | varios | 14 |

**De las 148 cuentas declaradas, solo 31 aparecen en dailyledger** —
porque dailyledger no contiene los asientos automáticos de cada doc
purchase (ver siguiente sección). El uso real se inferirá durante el
ETL leyendo `lines[].purchase.account` de cada doc.

## Limitaciones del dump

### `dailyledger.jsonl` solo contiene 2.250 asientos

A pesar de ser 8+ años de operación con 12.212 documentos, dailyledger
exporta **solo 2.250 entries**. Análisis de las top 30 cuentas en
dailyledger:

- Cuentas `28010000100`, `28170000100`, `12900000000` (apertura
  ejercicio): 450+ movs. Esto son los asientos de **cierre/apertura
  anuales** (~9 años × ~50 cuentas = ~450 entries).
- Cuentas tesorería `5720XXXX01` (bancos): 285 movs combinados.
- Cuentas IVA `472/477/4751`: 100+ movs.
- Cuentas proveedor concretas `41000000XXX`: ~10-20 movs cada una
  para los proveedores con financiación / pagaré.

**Hipótesis confirmada**: `dailyledger` es el equivalente Holded del
"libro diario manual" — contiene aperturas, cierres, ajustes,
remesas, gestión de pagarés, traspasos entre bancos. **NO contiene
los asientos generados automáticamente desde documentos**, esos se
calculan en runtime desde `documents.*.jsonl`.

**Implicación para Fase 5**: el ETL debe procesar AMBOS streams:

1. `documents.*.jsonl` → `account.move` generado a partir de cada
   factura/abono/compra (regla estándar).
2. `dailyledger.jsonl` → `account.move` adicional para asientos
   manuales (aperturas, cierres, ajustes contables, remesas SEPA,
   pagarés).

Sin esto el balance no cuadrará — las aperturas anuales son
imprescindibles para reflejar saldos pendientes year-over-year.

### Campos no expuestos por la API

`taxes.jsonl` no expone el campo "Cuenta" del tax — solo visible en
UI Holded (ver `holded-tax-mapping.md` + agent memory
`project_holded_tax_gotchas.md`).

`payments.jsonl` no expone `paymentMethod` ni `type` — campos vacíos
en todos los pagos (probablemente la API no los devuelve, o no se
usan). En su lugar el `documentType` siempre es `"trans"` (transfer
manual). Para clasificar pagos por método (transfer/card/cash) en el
ETL habrá que cruzar con `documents.*.jsonl.paymentMethod`.

## Resumen de bloqueantes nuevos para Fase 5

1. **Investigar 1.149 invoices y 308 purchases con `contactId` no
   resoluble** antes del ETL — decisión: ¿crear contact placeholder
   "Cliente histórico no identificado" o intentar fuzzy-match contra
   `contactName` literal en el doc?
2. **Asientos manuales del dailyledger** (2.250) requieren un loader
   separado en el ETL. Definir mapeo:
   - Aperturas/cierres anuales → `account.move` tipo `entry` con
     contrapartida 129x.
   - Remesas SEPA → puede integrarse con el módulo
     `account_banking_sepa_direct_debit` o cargarse como
     `account.move` puro.
   - Ajustes manuales → `account.move` con contrapartida según
     descripción.
3. **38 sales channels** requieren replicar subcuentas analíticas de
   ingresos 700/705/708 en Odoo (sigue patrón Fase 4.5b para IVA).
4. **Partners "(NO USAR)"** — política: archivar (`active=False`)
   tras consolidar history al partner activo equivalente.
5. **148 expensesaccount con solo 31 con uso confirmado** — decisión:
   ¿migrar todas como subcuentas de 6XX o solo las usadas? Sugerido:
   migrar todas para preservar consistencia con extractos AEAT
   futuros, marcar las 117 sin uso como `deprecated=True` en notas.
