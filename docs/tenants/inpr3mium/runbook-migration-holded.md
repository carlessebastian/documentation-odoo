# Runbook — Migración Holded → Odoo (inpr3mium)

> **Objetivo**: poder volver a ejecutar la migración Holded → Odoo
> desde cero, idealmente *a la primera*, partiendo de una DB Odoo
> recién bootstrappeada (Bloque C cerrado: Fases 4.0-4.7) + un dump
> reciente de Holded.
>
> Este documento es el "manual de operaciones" de Fase 5.1. Cuenta
> el **qué, por qué y cómo** de cada paso, con los gotchas
> encontrados durante la ejecución original (2026-05-12). Los
> snapshots `.json` en `snapshots/` registran el estado puntual; el
> `PLAN.md` registra el histórico cronológico; este archivo es el
> procedimiento ejecutable.
>
> **Audiencia**: yo mismo (Carles) o cualquier otro operador
> técnico que necesite reproducir la migración (test paralelo a
> Enterprise eval, sustitución de la DB por incidente, migración
> de un tenant clone, etc.).

---

## TL;DR — orden de ejecución

```
Pre-requisitos: Bloque C cerrado (Fases 4.0-4.7) + dump Holded reciente
0. Pre-flight: env vars, ACLs, default income account, JOURNAL ACC- (§5.7)
1. Loader paso 0a: expensesaccount.jsonl → account.account (148 cuentas)
2. Loader paso 0b: saleschannels.jsonl → account.account (38 cuentas)
3. Loader 1: contacts.jsonl → res.partner (3.363 → 3.173 únicos)
   3.b Retrofit notas Holded en res.partner.comment (UI auditoría)
4. Loader 2: products.jsonl + services.jsonl → product.template (2.009)
5. Loader 3: documents/invoice.jsonl → account.move out_invoice (3.422)
   5.7 Conversión automática total<0 → journal ACC- (776 docs)
6. Loader 5: documents/creditnote.jsonl → account.move out_refund (678)
7. [Bloqueado por operador] tax_reclassification.yaml
8. Loader 4: documents/purchase.jsonl → account.move in_invoice (TBD)
9. Loader 9: pdfs/* → ir.attachment enlazado a account.move
10. Loader 7: payments.jsonl → account.payment (107 MVP)
11. Postear todos los moves (--post)
12. Reconciliación final SQL
```

---

## 0. Pre-flight

### 0.1 Variables de entorno

```bash
# .env del repo (.env raíz)
ODOO_AGENT_TENANT=inpr3mium
ODOO_URL=http://localhost:19069
ODOO_DB=inpr3mium_dev
ODOO_USER=bot.contable@inpr3mium.com
ODOO_API_KEY=<api_key_bot>
HOLDED_DUMP_DIR=docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>
```

Antes de cualquier loader:

```bash
set -a && source .env && set +a
export PYTHONPATH=.claude/skills/odoo-functional-admin/scripts:.
```

### 0.2 ACLs del bot

El bot `bot.contable@inpr3mium.com` (uid=8) queda tightenneado en
Fase 4.4 con **6 grupos least-privilege**:

```
1   base.group_user
2   base.group_erp_manager
5   base.group_multi_company
9   base.group_partner_manager
23  account.group_account_manager
33  analytic.group_analytic_accounting
```

Para esta migración **necesita 1 grupo extra**:

```
26  product.group_product_manager  ← AÑADIR
```

Aplicar:

```python
# odoo shell o RPC
client.call("res.users", "write", [[8], {"group_ids": [(4, 26)]}])
```

Sin este grupo, **loader 2 (products) falla** con:
> "Se permite esta operación para los grupos siguientes: Products/Create"

Decisión documentada en
[`memory/decisions-log.md`](memory/decisions-log.md): mantener el
grupo durante toda la migración; tightenear post-cutover con
`(3, 26)`.

### 0.3 Default income account 705000

El **loader 3 invoices** requiere que exista `account.account` con
`code='705000'` para servir de fallback en líneas sin productId y
con saleschannel huérfano (12 docs del dump inpr3mium afectados).

Verificación:

```python
client.call("account.account", "search_read",
    [[("code", "=", "705000")]], {"fields": ["id", "name"], "limit": 1})
```

Debe devolver `[{"id": 551, "name": "Services rendered"}]`. Esa
cuenta la creó `l10n_es_pymes` al cargar el chart template (Fase 4.2)
y Fase 5.0 la fijó como `income_account_id` default de la company.
Si por algún motivo no existe, abortar y revisar Fase 5.0.

### 0.4 Dump Holded actualizado

El dump debe estar bajo
`docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>/`. Estructura
esperada:

```
<YYYY-MM-DD>/
├── manifest.json
├── contacts.jsonl          (3.363 contacts)
├── products.jsonl          (1.569)
├── services.jsonl          (440)
├── expensesaccount.jsonl   (148)
├── saleschannels.jsonl     (38)
├── taxes.jsonl             (103)
├── treasuries.jsonl        (12)
├── warehouses.jsonl        (1)
├── remittances.jsonl       (85)
├── payments.jsonl          (708)
├── dailyledger.jsonl       (2.250 chunks por año)
├── documents/
│   ├── invoice.jsonl       (3.430)
│   ├── creditnote.jsonl    (678)
│   ├── purchase.jsonl      (7.998)
│   ├── purchaserefund.jsonl (69)
│   ├── proform.jsonl       (34)
│   └── estimate.jsonl      (3)
└── pdfs/
    ├── invoice/           (3.430 PDFs, ~143 MB)
    └── purchase/          (4.059 PDFs, ~801 MB)
```

Re-generarlo con la skill `holded-export` (Fase 4.2.2) si el
existente está obsoleto.

### 0.5 Fases prerequisito completadas

Antes de ejecutar cualquier loader:

- ✅ Fase 4.0-4.4: company + bot + chart_template + journals.
- ✅ Fase 4.5b: 16 taxes Holded mapeadas con
  `description = "...[holded: <key>]"`.
- ✅ Fase 5.0: 4 bank journals + 6 cuentas 521x + payment term
  default + defaults company.

---

## 1. Loader paso 0a: expensesaccount.jsonl → account.account

**Propósito**: crear 148 subcuentas hijas de PGCE chapter 6
(gastos) usando los `accountNum` 11-dig de Holded como `code`.

**Ext_id**: `__holded__.account_<accountNum>` (e.g.
`__holded__.account_62100720021`).

**Comando**:

```bash
cd docs/tenants/inpr3mium/etl

# dry-run primero
python3 loader_expenseaccounts.py --dry-run

# real
python3 loader_expenseaccounts.py
```

**Resultado esperado**: 148 cuentas creadas, 0 errores.
`account_type` heredado del padre PGCE (e.g. parent `621000` →
type=`expense`). Distribución dump real: 131 expense + 11
expense_other + 6 expense_depreciation.

**Idempotencia**: re-run → 148 `updated`, 0 `created`, 0 errors.

---

## 2. Loader paso 0b: saleschannels.jsonl → account.account

**Propósito**: 38 subcuentas hijas de PGCE chapter 7 (ingresos).
Misma lógica que paso 0a.

**Comando**:

```bash
python3 loader_saleschannels.py --dry-run
python3 loader_saleschannels.py
```

**Resultado**: 38 cuentas income, 0 errores.

**Importante**: el dump tiene 38 saleschannels, pero los items de
invoice.jsonl referencian **85 saleschannel ids únicos** → 47
huérfanos (canales borrados en Holded antes del dump). Los huérfanos
NO se cargan aquí (no están en el JSONL); el loader 3 los maneja
caso por caso (fallback al default income).

---

## 3. Loader 1: contacts.jsonl → res.partner

**Propósito**: 3.363 contactos Holded → 3.173 `res.partner` únicos
Odoo (mergeados por `(countryCode, code)` cuando comparten CIF/NIF)
+ 1 placeholder `__holded__.contact__unknown` (para docs futuros con
contactId no resoluble).

**Ext_id**: `__holded__.contact_<holded_id>` (uno por contact, incluso
los dups apuntan al mismo res_id que el canonical).

**Comando**:

```bash
python3 loader_partners.py --dry-run
python3 loader_partners.py
```

**Resultado esperado**:
- ~2.976 canonical_create + 192 unique_create
- 190 dup_link (contactos que comparten code se mergean)
- 1 placeholder unknown
- 0 errors
- ~6 partners marcados `active=False` por marca `(NO USAR)` en name
- ~2.687 partners con VAT, ~3.022 con country=ES

**Gotchas conocidos**:
- `res.partner.mobile` **no existe en Odoo 19** → degradar a `phone`
  si `phone` vacío. Ya implementado.
- VAT non-ES: solo seteamos si Holded trae `vatnumber` explícito.
  Para non-ES, NUNCA usamos `code` como vat (Amazon EMEA con
  code='W0185696B' LU crashea `base_vat`). Ya implementado:
  `_upsert_with_vat_fallback` reintenta sin vat si Odoo rechaza.

### 3.b Retrofit notas Holded en res.partner.comment

Tras loader 1, **150 partners non-ES con `code`** quedan con `ref`
populado pero sin VAT — el `ref` no es visible en la vista standard
de proveedor de `l10n_es_pymes`. Y los partners con VAT rechazado
por `base_vat` (caso fallback) pierden completamente la traza del
VAT original.

Solución: inyectar nota visible en `comment` (Notas internas).

**Importante**: el loader actual lo hace inline si te ejecutas desde
cero (Capa 1 en `build_partner_vals` + Capa 2 en
`_upsert_with_vat_fallback`). Si tienes partners cargados ANTES de
ese fix, retrofit:

```bash
python3 retrofit_holded_code_note.py
```

Cubre el caso A (ref poblado + no vat) para partners ya existentes.
Idempotente vía detección sentinel textual (`Código Holded` /
`VAT rechazado`).

**Resultado esperado**: 306 partners con nota visible (150 "Código
Holded" + 156 "VAT rechazado").

---

## 4. Loader 2: products.jsonl + services.jsonl → product.template

**Propósito**: 1.569 products (`type=consu`) + 440 services
(`type=service`) → 2.009 `product.template` en Odoo.

**Ext_id**: `__holded__.product_<id>` o `__holded__.service_<id>`.

**Comando**:

```bash
python3 loader_products.py --dry-run
python3 loader_products.py
```

**Resultado esperado**: 1.569 product_create + 440 service_create,
0 errors.

**Gotchas**:
- **ACL bot**: requiere `product.group_product_manager` (id=26).
  Ver §0.2.
- Schema real usa `taxes` array (no `tax` single como decía la doc
  vieja). 1.964 records con tax único (`s_iva_21`), 33 sin tax,
  0 multi-tax.
- `categoryId` siempre vacío en el dump → skip.
- `attributes` (688 products con variants): cargamos plano sin
  expandir a `product.product`. Suficiente para nuestro uso.
- `stock` ignorado en este paso (Fase 5.4).
- Solo 102 products tienen `expAccountId`, y **TODOS apuntan al
  mismo id huérfano** `610138c76362411c8a4bd586` → no recuperable.
  Aceptable: caen al default expense de la company.
- 583 sin income account (= 477 sin `salesChannelId` + 106 huérfanos):
  caen al default `705000` (id=551). Aceptable.

---

## 5. Loader 3: documents/invoice.jsonl → account.move out_invoice

**Propósito**: 3.430 facturas Holded → **3.422 `account.move`
out_invoice** (state=draft) en Odoo, preservando numeración Holded.

**Ext_id**: `__holded__.invoice_<holded_id>`.

**Comando**:

```bash
# Dry-run primero (recomendado: revisar CSV antes de escribir)
python3 loader_invoices.py --dry-run

# Real, sin postear (default — postear tras revisión visual)
python3 loader_invoices.py
```

### 5.1 Política de numeración (CRÍTICO)

**Decisión operador 2026-05-12**: "Todo aquello que se importa NO
puede modificarse el número de factura. Seguiremos una estrategia
de subida una vez se cierre un trimestre".

**Implementación**: el loader setea `account.move.name = doc.docNumber`
literal (e.g. `A-007566`, `AC-001842`, `L-000547`). Cuando se postee,
Odoo respeta `name` explícito (no lo sobrescribe desde sequence).
Las facturas Odoo post-cutover usarán el sequence normal y
generarán nombres distintos al formato Holded (e.g.
`A-/2026/00001`).

Esto preserva la **correlatividad AEAT** con los libros históricos
de Holded.

### 5.2 Filtros aplicados

El loader **salta** automáticamente:

| Filtro | Cantidad inpr3mium | Acción |
|---|---|---|
| `status == 2` (cancelado lógico Holded) | 2 docs | skip + report |
| Prefijo `R-` (sin journal mapeado) | 6 docs | skip + report |
| `contact` vacío | 0 docs | skip defensivo |

Los R- son rarezas históricas (2018-2020, BIDAFARMA / FED.FARMACEUTICA
/ UNNEFAR, ~25k€ mix +/-). **Decidir con el operador** si recrearlos
manualmente o ignorar.

### 5.3 Duplicados de docNumber (EDGE CASE)

El dump inpr3mium tiene **2 pares duplicados confirmados**:
`L-000719` (2 facturas) y `L-000720` (2 facturas), contactos
distintos. Es un bug de datos Holded original (viola constraint
AEAT).

**Estrategia loader** (ya implementada): el doc del par con `date`
**más reciente** mantiene `name=docNumber`; los otros quedan con
`name='/'` y nota explicativa en `narration`. Preserva los 4 docs
sin violar unique(name, journal).

Si se carga un dump NUEVO con más duplicados, el loader los
detecta automáticamente (pre-pass `docs_by_num`).

### 5.4 Bug-fixes incorporados (críticos para repetición)

1. **`iso_from_unix` usa Europe/Madrid** (no UTC). Holded guarda
   timestamps como medianoche local; en UTC bajaba 1 día las
   facturas de medianoche CET → fiscal year incorrecto. Fix
   `holded_resolvers.iso_from_unix` con ZoneInfo.

2. **Default income fallback (`705000`)**. 12 docs tienen items
   sin productId Y con saleschannel huérfano → Odoo aborta con
   "Missing required account on accountable line". Fix en
   `_invoices_lib._build_line`: si NI product NI account
   resoluble → `account_id = id(705000)`.

### 5.5 Validación post-load

```sql
-- Conteos por journal
SELECT j.code, COUNT(*), SUM(am.amount_untaxed), SUM(am.amount_tax),
       SUM(am.amount_total)
FROM account_move am
JOIN account_journal j ON j.id = am.journal_id
WHERE am.move_type = 'out_invoice' AND am.ref IS NOT NULL
GROUP BY j.code
ORDER BY j.code;
```

**Cuadre con dump** (script Python en `snapshots/<date>_loader-invoices.json`):
agrega dump por prefijo, compara totales por journal. Diferencias
esperadas: **< 1€ por journal** (redondeo decimal en operaciones
de IVA sobre +700 docs).

Si la diferencia es **> 10€** por journal → investigar (probable:
items con tax key mal mapeada en Fase 4.5b).

### 5.6 Lifecycle: draft → posted

El loader deja todo en `draft`. **NO postear hasta**:

1. Revisión visual operador: muestreo aleatorio (10-20 facturas) en
   `Facturación > Clientes > Facturas` filtrando por journal y año.
   Verificar:
   - Partner correcto.
   - Líneas con producto + cuenta + tax.
   - Totales = dump Holded.
   - Adjunto PDF (cargado por loader 9).
2. SQL de cuadre §5.5 OK.
3. Confirmación operador.

Postear cuando OK:

```bash
python3 loader_invoices.py --post
```

`--post` re-procesa todos los docs: los ya draft con name=ref
hacen `action_post()` (Odoo respeta el name explícito); los
posted se saltan. Decimal mismatch > 0.02€/factura tras post →
warning en CSV.

### 5.7 Conversión automática total<0 → journal ACC- (CRÍTICO)

**El gotcha más importante de toda la migración**. Léelo entero
antes de ejecutar loaders 3/5/4.

#### El problema

Odoo 19 **rechaza** `action_post()` sobre `account.move` cuando
`amount_total < 0`:

> *"No puede validar una factura con un importe total negativo.
> En su lugar, debe crear una factura rectificativa."*

Constraint **nuevo en Odoo 19**, simétrico para todos los
`move_type`: `out_invoice`, `out_refund`, `in_invoice`, `in_refund`.

**Filosofía Odoo**: el `move_type` codifica el signo
(out_invoice = venta = positivo a cobrar; out_refund = devolución =
positivo a reembolsar). El `amount_total` siempre debe ser ≥ 0.

**Filosofía Holded** (y muchos sistemas legacy): tipo único
("Abonos Ventas") + signo del total para distinguir aumento vs
abono. Modelo incompatible.

#### Dimensión del problema en inpr3mium (validado 2026-05-12)

| Origen JSONL | Docs con `total<0` | Significado Holded |
|---|---:|---|
| `invoice.jsonl` | 750 | rectificativas de abono mal clasificadas (705 AC- + 41 A- + 3 L- + 1 FVU-) → semánticamente `out_refund` |
| `creditnote.jsonl` | 26 | rectificativas de aumento → semánticamente `out_invoice` |
| **Total a convertir** | **776** | — |

Sin esta conversión, **el 19% de las facturas histórias se quedarían
en estado draft** sin poder postear → AEAT incompleta.

#### Estrategia: journal ACC- aislado (decisión operador 2026-05-12)

> *"Mantendría consistente el rename de todos los que tengan conflicto.
> Podríamos generar una serie 'Propia' (tipo ACC-) así no entran en
> conflicto con los que tenemos y además los tenemos aislados."*

**Crear journal nuevo `ACC-`** (Conversiones carga histórica
Holded) que aislará los 776 docs convertidos. Beneficios:

- **Filtro único**: `journal_id = ACC-` lista los 100% convertidos.
- **Sin colisiones**: ACC- es serie nueva, no choca con A-/AC-/L-
  históricos.
- **Búsqueda por número Holded**: `ref = docNumber` original
  (`AC-001806`, etc.) buscable nativamente en la barra de Odoo —
  encuentras el doc aunque su nombre Odoo sea `RACC-/2026/00001`.
- **PDFs preservados**: el binario original (`AC-001806.pdf` desde
  Holded) se re-asigna al nuevo move.

#### Implementación en los loaders

`_invoices_lib.py` y `_creditnotes_lib.py` detectan `doc.total<0`
y aplican automáticamente:

```python
# Pseudocódigo en _process_doc
if doc.total < 0 and acc_journal_id:
    convert = True
    journal_id = acc_journal_id           # ACC- (id=23)
    final_move_type = 'out_refund' if origin == 'invoice' else 'out_invoice'
    # En _build_line:
    item['units'] = -float(item['units'])  # flip signo
    # En header:
    vals['name'] = False                   # Odoo asigna sequence ACC-
    vals['ref']  = doc.docNumber           # preserva Holded original
    vals['narration'] += '<strong>CONVERTIDO ...</strong>'
```

#### Resultado en Odoo tras conversión

| Campo | Valor |
|---|---|
| `journal_id` | ACC- (id=23) |
| `move_type` | `out_refund` (si origen era `invoice` con total<0) o `out_invoice` (si origen era `creditnote` con total<0) |
| `name` | Sequence Odoo: `ACC-/YYYY/NNNNN` para out_invoice; `RACC-/YYYY/NNNNN` para out_refund (Odoo añade `R` automáticamente) |
| `ref` | `docNumber` Holded literal (`AC-001806`, `A-007431`...) |
| `amount_total` | Positivo (signo flipeado correctamente) |
| `narration` | Marker textual buscable: `"CONVERTIDO out_<X> -> out_<Y>"` + docNumber origen |
| `ir.attachment` PDF | Re-asignado al nuevo `res_id` |

#### Procedimiento operativo (si tienes que repetirlo)

Si **arrancas migración desde cero** con dump nuevo:

1. Crear journal ACC- ANTES del primer post (forma parte del
   pre-flight §0):

   ```python
   ac = client.call("account.journal","search_read",
       [[("code","=","AC-")]], {"fields":["id","company_id"]})[0]
   client.call("account.journal","create",[{
       "name": "ACC- Conversiones carga histórica Holded",
       "code": "ACC-",
       "type": "sale",
       "company_id": ac["company_id"][0],
   }])
   ```

2. Loaders 3 y 5 ya tienen la lógica integrada — detectan
   `total<0` y crean automáticamente en ACC- con todos los flips.

3. **Post normal** con `loader_invoices.py --post` y
   `loader_creditnotes.py --post`. Los nuevos en ACC- se postean
   sin problema (amounts positivos tras flip).

Si **ya cargaste con loader sin la lógica de conversión** (caso
inpr3mium 2026-05-12 antes del fix):

```python
# 1. Snapshot inventario
problems = client.call("account.move","search_read",
    [[("state","=","draft"),
      "|", "&", ("move_type","=","out_invoice"), ("amount_total","<",0),
      "&", ("move_type","=","out_refund"), ("amount_total","<",0)]],
    {"fields":["id"]})
problem_ids = [m["id"] for m in problems]

# 2. Capturar attachment_ids enlazados (para re-asignar después)
atts = client.call("ir.attachment","search_read",
    [[("res_model","=","account.move"),("res_id","in",problem_ids),
      ("mimetype","=","application/pdf")]], {"fields":["id","res_id"]})

# 3. Detach: res_id=0 para evitar borrado en cascada
att_ids = [a["id"] for a in atts]
client.call("ir.attachment","write",[att_ids,{"res_id": 0}])

# 4. Borrar moves problemáticos + ext_ids
client.call("account.move","unlink",[problem_ids])
imd_ids = client.call("ir.model.data","search",
    [[("module","=","__holded__"),("model","=","account.move"),
      ("res_id","in",problem_ids)]])
client.call("ir.model.data","unlink",[imd_ids])

# 5. Re-run loader 3 + loader 5 (con lógica de conversión integrada)
# 6. Re-asignar attachments al new move_id (lookup via ext_id)
# 7. --post
```

#### Caveats

- **Decimal mismatch warnings cosméticos**: el check del loader
  compara `|doc.tax - move.amount_tax|` con signo directo; las
  conversiones disparan warning (signo flipeado). Los amounts
  ABSOLUTOS sí cuadran. Ignorable hasta que el loader use `abs()`
  para conversiones.

- **Overlaps docNumber entre invoice y creditnote** (caso inpr3mium:
  13 pares): el `name=False` + sequence ACC- los resuelve para los
  del journal ACC-. Los **no convertidos** (positivos) que comparten
  docNumber con uno convertido pueden chocar al postear si los dos
  intentan name=docNumber literal en journal AC- — caso AC-001135 en
  inpr3mium: 1 doc no se pudo postear (1/13 problema). Tratamiento
  manual operador.

- **status=0 Holded (drafts en origen)**: política conservadora —
  cargar como draft Odoo y NO postear automáticamente. Operador
  decide caso por caso (63 docs en inpr3mium).

#### Búsqueda en UI Odoo para auditoría

| Necesidad | Filtro |
|---|---|
| Ver las 776 convertidas | `Diario = ACC-` |
| Encontrar una factura por número Holded original | Buscar libre: `AC-001806` (busca en `ref`) |
| Listar solo refunds convertidos | filtro avanzado: `Narración contiene CONVERTIDO out_invoice` |
| Listar solo invoices convertidos | `Narración contiene CONVERTIDO out_refund` |
| Ver el PDF original | Click clip 📎 del chatter → `AC-XXXX.pdf` |

#### Memoria del agente (cross-tenant)

Este gotcha y estrategia están en agent memory
`~/.claude/projects/.../memory/project_odoo19_negative_amount_constraint.md`
— aplicable a cualquier futuro tenant (e.g. fedefarma desde
Axional) que tenga el mismo patrón.

---

## 6. Loader 5: documents/creditnote.jsonl → out_refund

*(Pendiente de implementar, esperado tras loader 3 ejecutado OK).*

**Diferencias con loader 3**:
- `move_type = 'out_refund'`.
- Si `doc.related_invoice_id` resoluble en invoices ya cargadas →
  setear `reversed_entry_id = move_invoice_id`.
- Si standalone → refund sin reversed_entry (Odoo lo permite).
- Journal AC- (`refund_sequence=False` — AC- es journal separado en
  Fase 4.3, no usa sequence inversa de A-).

**Volumen esperado**: 678 docs.

---

## 7. tax_reclassification.yaml (BLOQUEA loader 4)

**Pendiente sesión operador**. La factura de compra tiene un
catch-all `p_iva_exento` (2.306 docs) que mezcla **3 casos**:

1. ISP extra-UE no detectada por Holded
2. Exención Art.20 LIVA real
3. Renting / leasing exento técnico

Sin clasificación, todos caerían al mismo tax Odoo → modelo 303
incorrecto.

**Procedimiento**: sesión 1h con operador, sampling de 100 docs
aleatorios de `documents/purchase.jsonl` con `taxes=['p_iva_exento']`.
Clasificar por:
- `partner_country` (US/UK/CH... → ISP extra-UE)
- `partner_name` (Wolters Kluwer / SAP → renting)
- `doc_type` / descripción

Rellenar `etl/tax_reclassification.yaml` con la estructura ya en
sklíntico. Loader 4 consumirá el yaml automáticamente.

---

## 8. Loader 4: documents/purchase.jsonl → in_invoice

*(Bloqueado por §7).*

7.998 purchases + 69 purchaserefund. Estructura similar a loader 3.

**Diferencia clave**: `purchaserefund` se carga via
`account.move.reversal.action_reverse()` sobre el PB- original (no
create directo). Genera prefijo PR- automáticamente vía
`refund_sequence=True` en journal PB- (Fase 4.3).

---

## 9. Loader 9: pdfs/* → ir.attachment

**Propósito**: adjuntar el PDF original Holded a cada `account.move`
correspondiente. Cumple requisito legal de conservar la "factura
tal como se emitió/recibió" para auditoría AEAT.

**Ext_id resolution**: por cada PDF `<holded_id>.pdf` lookup
`ir.model.data.name='<doctype>_<holded_id>'` → res_id del move.

**Comando**:

```bash
# Dry-run primero
python3 loader_pdfs.py --doctype invoice --dry-run

# Real, todos los doctypes
python3 loader_pdfs.py
```

Doctypes soportados: `invoice`, `purchase`, `creditnote`,
`purchaserefund`. Skip si subdir vacío.

**Resultado esperado inpr3mium**:
- `invoice`: 3.430 PDFs (~143 MB), ~3.422 attachments creados
  (3.430 - 8 skipped por loader 3 sin move correspondiente).
- `purchase`: 4.059 PDFs (~801 MB), ~3.939 sin move (purchases sin
  PDF, son asientos manuales). Net: ~120 con move + PDF.

**Tamaño total filestore**: ~944 MB nuevos. Verificar espacio en
`/var/lib/odoo/filestore/<db>/`.

**Idempotencia**: re-run → 0 created, N skipped_existing.

**Naming del attachment**: `<docnumber>.pdf` (e.g. `A-007566.pdf`)
en lugar del id Holded — más legible en el chatter.

---

## 10. Loader 7: payments.jsonl → account.payment

*(Pendiente de implementar)*.

708 pagos. Mapeo `doc.bankId` → `account.journal` (treasury) via
snapshot Fase 5.0. Enlazar al move correspondiente vía
`reconciled_invoice_ids` si el pago aparece en `doc.paymentsDetail`
de algún invoice.jsonl.

---

## 11. Postear todos los moves

Cuando loaders 3-9 estén OK y operador haya validado:

```bash
# Por loader:
python3 loader_invoices.py --post
python3 loader_creditnotes.py --post
python3 loader_purchases.py --post
python3 loader_payments.py --post
```

Cada loader, al postear, valida decimal mismatch (`> 0.02€` →
warning; `> 1€` → abort batch).

---

## 12. Reconciliación final SQL

Tras postear:

```sql
-- Cuadre por journal × año × tax
SELECT
  j.code,
  EXTRACT(YEAR FROM am.invoice_date) AS year,
  t.id AS tax_id,
  t.name,
  SUM(aml.balance) AS balance,
  COUNT(DISTINCT am.id) AS moves
FROM account_move_line aml
JOIN account_move am ON am.id = aml.move_id
JOIN account_journal j ON j.id = am.journal_id
LEFT JOIN account_tax t ON t.id = ANY(
  SELECT account_tax_id FROM account_move_line_account_tax_rel
  WHERE account_move_line_id = aml.id
)
WHERE am.state = 'posted'
GROUP BY j.code, year, t.id, t.name
ORDER BY j.code, year, t.id;
```

**Cuadre vs dump**: script `validate_etl.py` (pendiente) compara
contra `documents/*.jsonl` agrupado del dump y emite CSV con diffs.

---

## Apéndice A: Mapa de ext_ids `__holded__.*`

| Ext_id pattern | Origen | Modelo Odoo | Loader |
|---|---|---|---|
| `account_<accountNum>` | expensesaccount + saleschannels | account.account | 0a + 0b |
| `contact_<id>` | contacts.jsonl | res.partner | 1 |
| `contact__unknown` | placeholder | res.partner | 1 |
| `product_<id>` | products.jsonl | product.template | 2 |
| `service_<id>` | services.jsonl | product.template | 2 |
| `invoice_<id>` | documents/invoice.jsonl | account.move (out_invoice) | 3 |
| `creditnote_<id>` | documents/creditnote.jsonl | account.move (out_refund) | 5 |
| `purchase_<id>` | documents/purchase.jsonl | account.move (in_invoice) | 4 |
| `purchaserefund_<id>` | documents/purchaserefund.jsonl | account.move (in_refund) | 4.b |
| `payment_<id>` | payments.jsonl | account.payment | 7 |

Todos con `module=__holded__`. `noupdate=True` para no perderlos al
actualizar módulos custom (no tenemos custom módulo `__holded__` —
es un ghost module name).

---

## Apéndice B: Resolvers compartidos (`holded_resolvers.py`)

| Resolver | Input | Output | Caveats |
|---|---|---|---|
| `normalize_vat(raw, country)` | string | string `<CC><digits>` o None | Heurística ES (8-9 chars + control digit); non-ES exige `country` param |
| `parse_journal_prefix(docNum)` | "A-007566" | "A-" o None | Mayúsculas; soporta `XXX-` (FVU-) |
| `derive_pgce_parent(code_11d)` | "62100720021" | "621000" | Reglas explícitas para 5720/521/472/477/4751; fallback `<first3>000` para chapters 6/7 |
| `iso_from_unix(ts)` | unix int/float/string | "YYYY-MM-DD" o None | **Europe/Madrid** (no UTC) — crítico para fiscal year boundary |
| `partner_active_from_name(name)` | string | (clean_name, active_bool) | Strip `(NO USAR)` |
| `HoldedResolvers.resolve_partner(contact)` | dict | partner_id o -1 (caller crea) | Cache por VAT + ext_id |
| `HoldedResolvers.resolve_tax(key, ctx)` | "s_iva_21" | account.tax.id o -1 | Lookup `[holded: <key>]` en description (Fase 4.5b); `tax_rules` para catch-alls |
| `HoldedResolvers.resolve_journal(doc_type, docNum)` | tipo, número | account.journal.id o -1 | Por prefijo XX-; `purchaserefund` → -1 (va por reversal) |
| `HoldedResolvers.resolve_account(code, autocreate=True)` | "70500130001" | account.account.id o -1 | autocreate como hijo del PGCE parent si autocreate=True |

---

## Apéndice C: Comandos completos paso a paso (copy-paste)

```bash
# 0. Pre-flight
cd /Users/carles/Documents/code/odoo-agent
set -a && source .env && set +a
export PYTHONPATH=.claude/skills/odoo-functional-admin/scripts:.
cd docs/tenants/inpr3mium/etl

# Verificar ACL bot
python3 -c "from odoo_client import OdooClient; c=OdooClient(); print(c.call('res.users','read',[[8]],{'fields':['group_ids']}))"
# Debe incluir 26 (product.group_product_manager). Si no:
python3 -c "from odoo_client import OdooClient; c=OdooClient(); c.call('res.users','write',[[8],{'group_ids':[(4,26)]}]); print('OK')"

# 1. Loader paso 0a
python3 loader_expenseaccounts.py --dry-run
python3 loader_expenseaccounts.py

# 2. Loader paso 0b
python3 loader_saleschannels.py --dry-run
python3 loader_saleschannels.py

# 3. Loader 1 partners
python3 loader_partners.py --dry-run
python3 loader_partners.py
# (3.b retrofit solo si cargas previas sin las notas)
# python3 retrofit_holded_code_note.py

# 4. Loader 2 products
python3 loader_products.py --dry-run
python3 loader_products.py

# 5. Loader 3 invoices (sin postear)
python3 loader_invoices.py --dry-run
python3 loader_invoices.py

# 9. Loader 9 PDFs (después de loaders 3-5)
python3 loader_pdfs.py --doctype invoice --dry-run
python3 loader_pdfs.py --doctype invoice

# Revisión visual operador en UI Odoo
# ...

# Postear cuando todo OK
python3 loader_invoices.py --post
```

**Tiempo estimado total** (instancia local, dump completo):
- Paso 0a/0b: ~30s cada uno
- Loader 1 partners: ~5 min
- Loader 2 products: ~10 min
- Loader 3 invoices: ~25 min (3.422 docs × ~0.5s)
- Loader 9 PDFs invoice: ~5 min (3.422 attachments × 50-100KB)
- Resto pendiente.

---

## Apéndice D: Recovery scenarios

### D.1 "Cargué con el bug de tz UTC, las fechas están 1 día antes"

Re-run `loader_invoices.py` (sin --post). El loader detecta existing
draft y reescribe el header con la fecha correcta. Los moves
posted no se tocan (skip_existing_posted). Si tienes posted con la
fecha mala: button_draft manual + re-run.

### D.2 "Cargué con name='/', necesito name=docNumber"

Idempotente. Re-run del loader: hace write `name=docNumber` en
todos los draft. Posted no se tocan.

### D.3 "Quiero borrar TODO lo cargado de Holded y empezar de cero"

```python
# Backup primero!
client.call("account.move", "search", [[("ref", "like", "%-%"),
                                         ("move_type", "in", ["out_invoice","out_refund","in_invoice","in_refund"])]])
# Inspeccionar conteo; si OK:
ids = client.call("account.move", "search", [[
    ("id", "in", [imd.res_id for imd in client.call("ir.model.data", "search_read",
        [[("module","=","__holded__"),("model","=","account.move")]], {"fields":["res_id"]})])
]])
client.call("account.move", "button_draft", [ids])  # si hay posted
client.call("account.move", "button_cancel", [ids])
client.call("account.move", "unlink", [ids])
# Borrar ir.model.data
client.call("ir.model.data", "unlink", [client.call("ir.model.data","search",
    [[("module","=","__holded__"),("model","=","account.move")]])])
```

**Cuidado**: si hay payments enlazados, unlink falla. Borrar payments
primero. Y si has presentado AEAT con esos moves... NO los borres.

### D.4 "El dump cambió entre runs, los IDs son distintos"

Holded ids son ULIDs estables. Si re-exportas, debería dar los
mismos. Si por algún motivo cambian (¿cambio de workspace?), los
ext_ids `__holded__.contact_<old_id>` y `<new_id>` serán distintos
y el loader creará duplicados. Recovery: borrar ext_ids `__holded__.*`
y empezar de cero con el dump nuevo.

---

## Apéndice E: Snapshots de referencia

| Snapshot | Fase | Lo que valida |
|---|---|---|
| `2026-05-11_fase-4.4.json` | Bot least-priv | 6 grupos, 0 admin |
| `2026-05-11_fase-4.5b.json` | Tax mapping | 16 taxes con `[holded: <key>]` |
| `2026-05-11_fase-4.6.json` | Smoke contable | 3 moves de prueba cuadran |
| `2026-05-11_fase-5.0.json` | Fundaciones | 4 bank journals + 6 cuentas 521x + defaults |
| `2026-05-12_fase-5.1-paso0.json` | Paso 0a/0b | 186 account.account ext_id |
| `2026-05-12_fase-5.1-loader-partners.json` | Loader 1 | 3.173 partners únicos |
| `2026-05-12_fase-5.1-loader-products.json` | Loader 2 | 2.009 product.template |
| `2026-05-12_fase-5.1-loader-invoices.json` | Loader 3 | 3.422 out_invoice + cuadre dump |
| `2026-05-12_fase-5.1-loader-creditnotes-pdfs.json` | Loader 5 + 9 + 7 | 678 out_refund + 3.422 PDFs + 107 payments |
| `2026-05-12_pre-conversion-inventory.json` | Pre-conversión ACC- | 776 docs problemáticos + attachment_ids |
| `2026-05-12_post-conversion-final.json` | Post-conversión ACC- | 776 docs convertidos en ACC- + cuadre |

Si una ejecución futura difiere de estos snapshots, investigar
(probable: dump más reciente trae datos nuevos).

---

## Apéndice F: Decisiones operativas sobre draft pendientes

Tras la migración completa de SALES (sales+refunds), quedan **99
docs draft** que requieren decisión semántica humana (no
automatizables). Estas son las decisiones tomadas con el operador
inpr3mium 2026-05-12 — referencia para futuros tenants ante el
mismo patrón.

### F.1 — docs con `status=0` Holded (drafts en origen)

**Política**: dejar draft en Odoo. Respeta el estado origen. El
operador los postea/cancela caso por caso desde UI cuando los
revise.

Aplica a:
- 63 docs `out_invoice` en journals A-/AC-/L-/FVU-/KD-/AF- (varios)
- 30 docs `out_refund` en ACC- (los convertidos que eran
  `status=0` en Holded)

### F.2 — docs con `status=3` Holded (en revisión)

**Política**: postear si el operador revisa y aprueba. 5 docs
inpr3mium (AC-001793/4/5/6/800) — todos posteados tras OK
operador.

Implementación: lookup por `ref` + `action_post` directo.

### F.3 — docs con `docNumber` duplicado en origen (convención `-bis`)

**Política**: el doc con `date` más reciente preserva
`name=docNumber` Holded literal; los demás se renombran con sufijo
`-bis` (segundo), `-ter` (tercero), etc. `ref` mantiene siempre el
docNumber original para auditoría.

Casos inpr3mium:
- **AC-001135**: docNumber duplicado entre `invoice.jsonl` (520€
  out_invoice posted) y `creditnote.jsonl` (726€ out_refund draft).
  El out_refund se renombró a `AC-001135-bis` y posteó.
- **L-000719, L-000720**: 2 pares de facturas reales con mismo
  docNumber emitidas en fechas distintas (bug Holded). Los losers
  se renombraron a `L-000719-bis`, `L-000720-bis` y postearon.

**IMPORTANTE**: si dejas los losers postearse sin renombrar
explícitamente, **Odoo asigna nombres nuevos del sequence del
journal** (e.g. L-001314, L-001315) — números que NO existían en
Holded. Eso rompe la promesa "name = docNumber Holded literal" y
contamina la auditoría. **Siempre renombrar antes de postear.**

Recovery si ya pasó:

```python
# button_draft → write name → action_post
c.call("account.move","button_draft",[[move_id]])
c.call("account.move","write",[[move_id],{"name": "<docNumber>-bis"}])
c.call("account.move","action_post",[[move_id]])
```

Quedan huecos en el sequence (números reservados que no se usan).
Aceptable: Odoo no fuerza correlatividad; AEAT solo exige
correlatividad dentro del período fiscal del modelo presentado.

### F.4 — prefijos sin journal mapeado (caso R-)

**Política**: crear journal nuevo en Odoo + recargar los docs
ad-hoc (no rentable patch de loader si son pocos docs).

Caso inpr3mium R-: 6 docs históricos (2018-2020) con prefijo
"Rectificativas" abandonado por Holded tras unificar en AC-.

Procedimiento ad-hoc:

```python
# 1. Crear journal R-
ac = c.call("account.journal","search_read",[[("code","=","AC-")]],
            {"fields":["company_id"]})[0]
r_jid = c.call("account.journal","create",[{
    "name": "R- Rectificativas históricas Holded",
    "code": "R-", "type": "sale",
    "company_id": ac["company_id"][0],
}])

# 2. Cargar los docs del dump filtrando por prefix R-:
#    - total >= 0 → out_invoice en journal R-
#    - total < 0  → out_refund en journal R- (flip signo lines)
#    - name = docNumber literal, ref = docNumber
#    - adjuntar PDF si existe en pdfs/invoice/<holded_id>.pdf
#    - postear si status=1
```

Script completo de inpr3mium en
`docs/tenants/inpr3mium/snapshots/` (búsqueda por commit con
"R- Rectificativas históricas").

### F.5 — Tabla rápida de search filters

| Necesidad | Filtro Odoo |
|---|---|
| Ver los 776 docs convertidos por signo invertido | `Diario = ACC-` |
| Ver los 6 R- históricos | `Diario = R-` |
| Encontrar un doc por número Holded original | Búsqueda libre con el docNumber (ej. `AC-001806`) — busca en `ref` |
| Listar todos los `-bis` (duplicados Holded) | `Número contiene -bis` |
| Listar refunds convertidos desde invoices | `Narración contiene CONVERTIDO out_invoice` |
| Listar invoices convertidos desde refunds | `Narración contiene CONVERTIDO out_refund` |
| Ver el PDF original Holded | Click 📎 del chatter de la factura |
