# Decisions log — inpr3mium

Decisiones tomadas durante el bootstrap (Fase 4) y planificación de
migración (Fase 5) con su razón y aplicabilidad. Ordenado del más
reciente al más antiguo. Las entradas se mantienen aunque la
decisión cambie — solo se añade una nueva entrada superior con la
revisión.

---

## 2026-05-13 — Fase 5.1 cierre: cobertura PDF SALES incompleta (creditnotes faltantes)

**Contexto**: el operador detectó visualmente que algunas facturas a
clientes (especialmente rectificativas tras el cierre 5.1) no tenían
PDF en el chatter. Auditoría completa post-loader 9:

| Bucket | Moves | Con PDF | Sin PDF |
|---|---:|---:|---:|
| out_invoice (todos) | 2.701 | 2.674 | 27 |
| out_refund (todos) | 1.407 | 754 | 653 |
| **TOTAL SALES** | **4.108** | **3.428** | **680** |

**Causa raíz única**: el dump `2026-05-11` se generó con
`--pdf-doc-types invoice,purchase` (default del skill `holded-export`
en ese momento). Por tanto el dump no incluye `pdfs/creditnote/`
ni `pdfs/purchaserefund/`. Loader 9 procesó lo que había
(`pdfs/invoice/`) y reportó `0 errors` porque su lógica es
"itera lo que encuentres" — no comprueba cobertura.

**Distribución de los 680**:
- 653 out_refund en journal AC- (loader 5 creditnotes): ext_id
  `creditnote_<id>`, sin contraparte en dump.
- 26 out_invoice en journal ACC- (operaciones flip total>0 cuyo
  origen Holded es creditnote, posteadas en cierre 5.1 status=3): mismo
  problema, ext_id `creditnote_<id>`.
- 1 doc smoke test Fase 4.6 (id=2): irrelevante.

**Verificado OK** (no necesitan acción):
- L-000719-bis, L-000720-bis: tienen PDF (loader 9 procesó tras rename).
- 6 R- históricos (R-000004..009): tienen PDF (ad-hoc script adjuntó).
- 720 ACC- out_refund posted + 30 draft con ext_id `invoice_*`:
  tienen PDF (vinieron de `pdfs/invoice/`, el res_id no cambió al
  flipear el `move_type` así que el ir.attachment quedó válido).

**Decisión**: subir los PDFs faltantes en una sesión dedicada,
sin re-tocar el resto del dump. Procedimiento documentado en
[runbook §Apéndice G](../runbook-migration-holded.md#apéndice-g-recovery--pdfs-creditnotepurchaserefund-faltantes)
(5 pasos: re-dump creditnote PDFs → verificar → dry-run → run real
→ re-auditar). `purchaserefund` se difiere a cuando se ejecute
loader 4 (mismo dump del cutover, no este 2026-05-11).

**Pitfall genérico** (cross-tenant) registrado en agent memory:
todo dump Holded futuro debe lanzar `--pdf-doc-types` con los
**cuatro doctypes que generan account.move en Odoo**
(`invoice,purchase,creditnote,purchaserefund`), no solo los dos
"obvios". Además, `loader_pdfs.py` necesita una assertion de
cobertura post-load que falle si quedan moves SALES/PURCHASE
sin attachment cuando se esperaba que tuvieran (track futuro,
no bloqueante para inpr3mium).

**No aplicable** (descartado tras inspección): no se trata de un
bug del loader 9 ni de un problema de ext_id. Es estrictamente
falta de input en el dump.

---

## 2026-05-12 — Fase 5.1 cierre: decisiones sobre los draft pendientes

**Contexto**: tras la conversión a ACC- quedaban 105 docs draft que
requerían decisión semántica del operador (no automatizable). El
operador decidió caso por caso:

### Decisión 1 — 63 docs `out_invoice` con status=0 Holded → **dejar draft**

Eran facturas en estado borrador en Holded en el momento del dump
(probablemente trabajos en curso del operador). Política: respetar
el estado origen. No postear automáticamente. Si en el futuro
quieren postearlas, lo harán manualmente desde UI Odoo caso por caso.

### Decisión 2 — 5 docs status=3 (review Holded) → **postear**

AC-001793, AC-001794, AC-001795, AC-001796, AC-001800 (~5.184€
total). El operador revisó y aprobó. Posteados directamente vía
`action_post` por id. Quedaron con name de su journal asignado
(ACC- o AC-).

### Decisión 3 — AC-001135 overlap docNumber → **renombrar -bis y postear**

Bug original Holded: el docNumber AC-001135 aparece DOS veces en el
dump con holded_ids distintos (en `invoice.jsonl` 520€ y en
`creditnote.jsonl` 726€). Uno se posteó normalmente como out_invoice
en journal AC-. El otro (out_refund) chocaba al postear por
`unique(name, journal_id)`.

**Solución**: renombrar el segundo a `AC-001135-bis` (manteniendo
`ref='AC-001135'` para auditoría) y postear.

### Decisión 4 — 2 dup losers L-000719/L-000720 → **renombrar -bis y postear**

Bug original Holded: 2 pares de facturas REALES con mismo docNumber
emitidas en fechas distintas (agosto vs octubre 2019, contactos
distintos, totales distintos). Política previa: el doc con `date`
más reciente preserva name; los otros quedaban draft con name=False
+ narration warn.

Al hacer `--post` masivo, los dup losers se postearon con names
nuevos asignados desde el sequence del journal L-: **L-001314** y
**L-001315** — números que NUNCA existieron en Holded. Operador
rechazó esto:

**Solución**: button_draft → renombrar a `L-000719-bis` y
`L-000720-bis` → re-postear. Los names L-001314/L-001315 quedaron
como "huecos" en el sequence Odoo del journal L- (Odoo no fuerza
correlatividad; AEAT solo importa correlatividad dentro del
período fiscal del modelo, y estos huecos son del año 2019 ya
cerrado).

**Convención `-bis`**: cualquier doc con docNumber duplicado en
origen se renombra con sufijo `-bis` (variante latina "segunda
vez"). Si hubiera triplicados, `-bis`, `-ter`, etc. Mantiene ref =
docNumber original para auditoría.

### Decisión 5 — 6 docs prefix R- → **recrear en journal R- nuevo**

6 docs históricos (2018-2020) con prefix `R-` (Rectificativas)
que el operador Holded abandonó tras unificar todo en AC-. 4 con
total<0 (abonos), 2 con total>0 (facturas).

Loader 3 los saltaba con `skip_unmapped_prefix` porque no había
journal R- en Odoo.

**Solución**: crear journal **R- "Rectificativas históricas Holded"**
(id=24, code=R-, type=sale) y recargar los 6 docs ad-hoc (script
inline, no rentable patch de loader para 6 docs):

- Los 4 con total<0 → `out_refund` en journal R- con signos
  flipeados.
- Los 2 con total>0 → `out_invoice` en journal R-.
- `name = docNumber` Holded literal (R-000004, R-000005, ...,
  R-000009).
- `ref = docNumber`.
- `narration` con marker explicativo: "Doc histórico R- Holded
  prefix legacy (rectificativas antes de unificación AC-)".
- PDF original adjunto (4 de los 6 tienen PDF en
  `pdfs/invoice/<holded_id>.pdf`).
- Todos posteados directamente.

Net contable: -4.903€ (los 4 de 2020 son 2 pares espejo que se
anulan; los 2 de 2018 son abonos legítimos por -4.903€).

### Estado final tras todas las decisiones

| | Posted | Draft | Total |
|---|---:|---:|---:|
| out_invoice | 2.638 | 63 | 2.701 |
| out_refund | 1.371 | 36 | 1.407 |
| **TOTAL SALES** | **4.009** | **99** | **4.108** |

**97.6% posted**. Los 99 draft restantes son los 63 status=0
Holded (intencional, Decisión 1) + 30 ACC- status=0 + 6 misc (ya
documentados).

---

## 2026-05-12 — Fase 5.1 conversión total<0: journal ACC- aislado

**Decisión (operador 2026-05-12)**: crear un journal nuevo `ACC-`
("Conversiones carga histórica Holded") para los 776 docs Holded con
`total<0` que Odoo 19 rechaza postear en `out_invoice` (constraint nuevo
Odoo 19: "No puede validar una factura con un importe total negativo").

**Razón**: el dump Holded tiene 776 docs donde el `move_type` no coincide
con el signo del total:
- 750 docs en `invoice.jsonl` con `total<0` → semánticamente son
  rectificativas de abono (out_refund Odoo): 705 AC- + 41 A- + 3 L-
  + 1 FVU-.
- 26 docs en `creditnote.jsonl` con `total<0` → semánticamente son
  rectificativas de aumento (out_invoice Odoo).

Es un bug de modelado de Holded que usa el mismo prefix AC- para dos
casos contables opuestos, distinguidos solo por el signo del total.

**Implementación**:
- Journal ACC- nuevo (id=23, type=sale, code=ACC-).
- Loaders 3/5 con flag `--negative-as-refund` (implícito por defecto):
  cuando `doc.total<0`, flip `move_type` + `journal_id=ACC-` +
  flipear signo de `quantity` en líneas + `name=False`.
- `name` final: Odoo asigna `ACC-/YYYY/NNNNN` para out_invoice y
  `RACC-/YYYY/NNNNN` para out_refund (el `R` lo añade Odoo
  automáticamente por defecto en out_refund de journal sale; aceptable,
  el journal sigue siendo único filtro).
- `ref = docNumber` Holded literal (`AC-001806`, etc.) — campo buscable
  en la barra de búsqueda standard de Odoo.
- `narration` con marker textual `"CONVERTIDO out_invoice -> out_refund"`
  o inverso + docNumber original, buscable con `narration ilike`.
- PDFs originales preservados: detach (res_id=0) antes de borrar moves
  problemáticos, re-asignar al new_move_id tras recarga.

**Resultado real (2026-05-12)**:
- 776 docs creados en journal ACC- (750 out_refund + 26 out_invoice).
- 743 posted (23 out_invoice + 720 out_refund).
- 33 draft: 30 status=0 Holded + 1 AC-001135 (overlap docNumber con
  out_invoice ya posted del mismo Holded) + 2 misc.
- 750 PDFs originales preservados y vinculados.

**Búsqueda para auditoría**:
- `journal_id = 23` → 776 hits (todas las conversiones)
- `ref = AC-001806` → encuentra el doc independientemente de su `name`
  Odoo (RACC-/2026/00001 en este caso)
- `narration ilike CONVERTIDO out_invoice` → 750 hits
- `narration ilike CONVERTIDO out_refund` → 26 hits

---

## 2026-05-12 — Fase 5.1 loader 3 patch: `name = doc.docNumber` literal en account.move

**Decisión**: setear `account.move.name = doc.docNumber` literal antes
de postear, NO dejar que Odoo lo genere desde el sequence del journal.

**Razón** (operador, 2026-05-12, sobre captura UI):

> "Todo aquello que se importa no puede modificarse el número de
> factura. Seguiremos una estrategia de subida una vez se cierre
> un trimestre."

Postear sin name explícito → Odoo asigna `A-/2026/00001`, `A-/2026/00002`...
desde la secuencia del journal, **ignorando el docNumber Holded**.
Resultado: se pierde la correlatividad AEAT con los libros históricos
de Holded; auditoría futura no puede cruzar `A-/2026/00001` con
`A-007566` sin tabla externa.

**Aplicación**:
- `build_invoice_header_vals(..., use_holded_number=True)` (default
  True) setea `vals["name"] = docNumber`.
- Build header `build_refund_header_vals` igual para creditnotes.
- En `_process_doc` el write path incluye `name` en write_vals; Odoo
  lo acepta en draft.
- Al action_post, Odoo respeta `name` explícito (no lo sobrescribe).

**Convivencia**: facturas post-cutover (operación normal Odoo) usarán
sequence Odoo y generarán nombres distintos (`A-/2026/NNNNN`). El
operador acepta la convivencia. Lo importante es:
1. Histórico: identidad 1:1 con Holded (auditoría AEAT clean).
2. Nuevas: identidad 1:1 con Odoo (libros nuevos clean).

**Duplicate handling**: 2 pares L-000719/L-000720 en el dump (bug
datos Holded original). Estrategia defensiva: el doc del par con
`date` más reciente preserva name=docNumber; los otros quedan
`name='/'` (al postear, Odoo asignará nombre del sequence Odoo,
**distinto** del Holded). Anotado en narration. Preserva los 4 docs
sin violar `unique(name, journal_id, company_id)`.

---

## 2026-05-12 — Fase 5.1 loader 5: `status=3` Holded (review) carga draft, nunca postea

**Decisión**: 5 docs `creditnote.jsonl` con `status=3` en Holded
("en revisión" según análisis manual) se cargan como `account.move`
draft pero NUNCA se postean por `--post`.

**Razón**: `status=3` parece ser estado de aprobación pendiente del
responsable contable Holded. Postear automáticamente puede llevar a
inconsistencia (estaban "pendientes" en Holded por algo). Política
conservadora: cargar el dato (preserva auditoría), no postear,
operador decide caso por caso vía UI Odoo (`Confirmar` manual o
cancelar).

**Aplicación**: en `_creditnotes_lib._process_doc`, el bloque post
filtra explícitamente `doc.status == STATUS_POSTED (=1)`. Status=3 +
`--post` flag → log + no post + `narration` warn ya visible.

**Docs afectados**: AC-001793 (-726), AC-001794 (-1051.24), AC-001795
(1051.24), AC-001796 (1051.24), AC-001800 (-726). Todos
FED.FARMACEUTICA / GRUPO BIDAFARMA en oct/nov 2026. Operador revisar
si:
- Anularlos (cancel) si era una propuesta abandonada.
- Postearlos manualmente si la revisión los aprueba.

---

## 2026-05-12 — Fase 5.1 loader 3: `iso_from_unix` interpreta timestamps Holded en Europe/Madrid, no UTC

**Decisión**: cambiar `iso_from_unix` en `holded_resolvers.py` para usar
`ZoneInfo("Europe/Madrid")` al convertir timestamps Holded → `YYYY-MM-DD`.

**Razón**: Holded guarda fechas como **medianoche local** (Madrid),
no como medianoche UTC. Verificado en el dump:
- `1546210800` → factura A-007566 con docNumber visible "31/12/2018"
  en Holded. En UTC = 2018-12-30 23:00. Interpretar como UTC nos
  daba `invoice_date='2018-12-30'` — **fiscal year incorrecto** para
  todas las facturas de diciembre con fecha de fin de mes/año.
- `1561932000` → "01/07/2019" en Holded. En UTC = 2019-06-30 22:00
  (CEST verano UTC+2). Mismo problema.

Sin el fix, las facturas con `date` a medianoche CET caerían 1 día
antes en Odoo, contaminando el modelo 303 trimestral y el cierre
anual.

**Aplicación**: `iso_from_unix` usa `ZoneInfo("Europe/Madrid")` para
calcular `.date()`. Si `tzdata` no disponible, fallback defensivo a
UTC con warning implícito. Tests añadidos: `test_madrid_midnight_winter`
y `test_madrid_midnight_summer`.

**Alcance**: afecta a TODOS los loaders que usen `iso_from_unix`
(invoices, creditnotes, purchases, payments, dailyledger). Loaders 1
(partners) y 2 (products) no la usan (no tienen campos date Holded).

**Impacto en cargas previas**: ninguna — partners y products no
tienen fechas. La primera carga afectada es loader 3.

---

## 2026-05-12 — Fase 5.1 loader 3: fallback default income `705000` para items huérfanos

**Decisión**: cuando una línea Holded NO tiene `productId` Y su
`saleschannel` es huérfano (no existe en `saleschannels.jsonl`),
forzar `account_id = account.account.code='705000'` (id=551,
"Services rendered", set como default empresa en Fase 5.0).

**Razón**: 12/3.430 docs (`L-000547` y similares) fallaban con
`"Missing required account on accountable line"`. La causa: items
"ad-hoc" con descripción libre (e.g. "Campaña Nov/Dic.Nac.Pfizer
Polase 4 eur.") sin productId Holded y apuntando a saleschannels
borrados. Sin ninguna pista para inferir cuenta, Odoo aborta el
move entero.

**Aplicación**: lookup `account.account.code='705000'` al inicio
del orquestador (1 RPC). En `_build_line` el fallback solo se aplica
si **ambos** product_id y account_id son None. Las 6.198 lines con
saleschannel huerfano que SÍ tienen productId siguen cayendo al
`product.property_account_income_id` (sin cambio).

**Riesgo aceptado**: las 12 líneas problemáticas se imputan a
"Services rendered" (705) por defecto, aunque su descripción sugiere
gastos de promoción tipo "Campaña". El operador puede reclasificar
manualmente vía UI por batches si quiere precisión analítica. No es
una factura de cliente — está dentro de un doc out_invoice (e.g.
factura a FED.FARMACEUTICA) con descuentos parciales en líneas
ad-hoc. La cuenta es solo para imputación contable interna.

---

## 2026-05-12 — Fase 5.1 loader 3: invoices cargan en `draft`, post diferido

**Decisión**: el loader 3 carga todas las invoices con
`state='draft'`. El flag `--post` está disponible pero NO se usa
por defecto.

**Razón**: 6.198 líneas (40%) tienen saleschannel huérfano y caen
al default empresa (`705000`). Si posteamos sin revisión, el
balance contable por cuenta queda distorsionado vs Holded. Postear
tras:
1. Muestreo aleatorio operador (10-20 facturas de distintos
   journals y periodos) — verificar mapeos de cuenta/tax.
2. Reconciliación SQL por journal × año × cuenta vs dailyledger
   Holded.
3. Tras OK: `--post` en batch (los 3.422 docs con status=1).

**Aplicación**: PLAN.md paso 8 documenta esta revisión como
bloqueante antes de postear. `--post` posterga decimal mismatch
warnings — si > 0.02€ por doc tras post, log; si > 1€ aborta batch.

---

## 2026-05-12 — Fase 5.1 loader 2: bot añade `product.group_product_manager` permanente

**Decisión**: añadir el grupo `product.group_product_manager` (id=26)
al bot uid=8 de forma permanente durante toda la fase de migración,
en lugar de hacer escalación temporal por loader.

**Razón**: el bot quedó tightenneado en Fase 4.4 a 6 grupos
least-privilege que NO incluyen permisos CRUD sobre `product.template`.
El loader 2 fallaba con "Se permite esta operación para los grupos
siguientes: Products/Create" (ACL `product.template.manager` id=317
requiere group 26). Loaders siguientes (3 invoices, 4 purchases,
9 PDFs como `ir.attachment` sobre product.template) podrían volver a
tocar product.template indirectamente. Hacer add/remove cada vez es
ruido sin valor.

**Aplicación**: write `(4, 26)` sobre `res.users[8].group_ids`. Bot
ahora con 7 grupos: `[1, 2, 5, 9, 23, 26, 33]`. Tightenear post-cutover
con `(3, 26)`. Documentar en snapshot de cierre Fase 5.

**Gotcha**: el cambio de grupo se aplica inmediatamente sin necesidad
de re-login (Odoo lee grupos por request). Run principal del loader,
que estaba autenticado antes del cambio, pudo continuar OK tras el
write.

---

## 2026-05-12 — Fase 5.1 loader 2: aceptar pérdida de income/expense accounts del dump

**Decisión**: aceptar que **583 records cargan sin
`property_account_income_id`** y **102 products sin
`property_account_expense_id`** — caen al default de la company
(income=`705000`/id=551 set en Fase 5.0; expense=fallback de Odoo).

**Razón**: análisis del dump revela tres categorías:
1. **477 records sin `salesChannelId`** (135 products + 342
   services): el operador en Holded nunca asignó canal de venta.
   No es recuperable; representa el comportamiento "default income"
   en Holded también.
2. **106 records con `salesChannelId` huérfano** (9 products + 97
   services): apuntan a IDs de sales channels que NO están en
   `saleschannels.jsonl` (38 entries). Sales channels borrados en
   Holded antes del dump; dato perdido.
3. **102 products con expAccountId huérfano**: TODOS apuntan al
   mismo id `610138c76362411c8a4bd586` que no existe en
   `expensesaccount.jsonl` (148 entries). Probablemente una
   "Expense account" especial de Holded borrada históricamente.

**Aplicación**: el loader marca estos en stats (`no_income_account`,
`no_expense_account`) pero NO aborta el record. El product/service
se crea sin la property; Odoo aplica el default company al usarse
en una line. Para los loaders de facturas/compras (3, 4): cuando
construyan `account.move.line`, si `product_id.property_account_*`
no está, también caerán al default — comportamiento equivalente al
que tenían en Holded.

**Riesgo**: el reporting analítico por cuenta dejará agrupados todos
estos products en el default. Mitigación: si en 5.4 el operador
quiere desambiguar, puede asignar income account a mano vía UI por
batches (solo 1.034 candidatos = 477 + 106 sin SC × forSale=true).

---

## 2026-05-12 — Notas Holded inyectadas en `res.partner.comment` para auditoría UI

**Problema observado**: tras el loader 1, el operador inspeccionó la
ficha de proveedor de `AMAZON WEB SERVICES EMEA SARL` (id=25) en Odoo
y no vio rastro del code/VAT original que tenía en Holded. La vista
standard de proveedor de `l10n_es_pymes` no muestra `res.partner.ref`
(donde guardamos el `code` Holded), y los partners cuyo VAT fue
rechazado por `base_vat` (caso Capa 2 del fallback) ni siquiera tenían
ref poblado — toda la traza del VAT original se había perdido.

**Decisión**: inyectar la información en `res.partner.comment`
("Notas internas") siempre que el `code` o el `vatnumber` Holded no
acaben en el campo `vat` de Odoo. Es el campo visible más
accesible sin tocar vistas, y es semánticamente correcto (es
metadata del contacto, no un campo estructurado).

**Dos puntos de inyección**:

1. **Capa 1** en `build_partner_vals` (`_partners_lib.py`): cuando
   `raw_code` está poblado pero no se promueve a `vat_val` (típico
   caso non-ES con code='SENDGRID'/'EU372...'/etc.), añade
   `<p>Código Holded (no validado como VAT): <code>X</code></p>`.
2. **Capa 2** en `_upsert_with_vat_fallback`: cuando Odoo rechaza el
   `vat` y reintentamos sin él (Amazon EMEA LU con `vatnumber='W0185696B'`
   contra base_vat que exige 8 dígitos), añade
   `<p>VAT rechazado por validación Odoo (conservado como referencia): <code>X</code></p>`.

**Resultado final** (tras re-run del loader): 306 partners con nota
Holded — **150 "Código Holded"** (mayormente non-ES con code populated)
+ **156 "VAT rechazado"** (mayormente ES con CIF/NIF que falla DC +
algunos non-ES con vatnumber mal formateado).

**Detección por sentinel textual, no por HTML comment marker**:
intentamos primero envolver las notas en `<!-- holded.code:start --><p>X</p><!-- holded.code:end -->`
pero Odoo sanitiza el field `comment` (es `Html` con cleaner activado)
y stripa **asimétricamente** los comments: el de apertura desaparece,
el de cierre persiste. Reproducción confirmada en este Odoo:
`<!-- A --><p>X</p><!-- B -->` → round-trip a Odoo → leído como
`<p>X</p><!-- B -->`. Cambiamos la detección a substring del texto
humano (`"Código Holded (no validado como VAT)"` y
`"VAT rechazado por validación Odoo"`) — robusto frente a
sanitización y a la vez legible.

**Política de re-runs**: el loader sobreescribe `comment` cada vez
que el contact entra en una de las dos condiciones (determinístico,
mismo input → mismo output). Notas manuales del operador en partners
con código Holded **serán pisadas** en re-runs del loader; aceptable
mientras estemos en fase de migración. Tras el cutover Fase 5.5 el
loader no debería re-ejecutarse en producción.

**Retro-fix**: `retrofit_holded_code_note.py` cubre solo el caso A
(partners con `ref` truthy AND `vat` falsy AND ext_id
`__holded__.contact_*` AND `comment` sin sentinel). Es one-shot e
idempotente vía `has_holded_note()`; tras el re-run del loader queda
sin nada que hacer (305/305 skipped). Conservado por si aparecen
nuevos partners ref-only que el loader no procesa (improbable, pero
defensivo).

---

## 2026-05-12 — Fase 5.1 loader 1: partners Holded cargados en Odoo

**Hecho**: `loader_partners.py` ejecutado en real contra `inpr3mium_dev`.
3.363 contacts Holded materializados como **3.173 `res.partner`
únicos** + **1 placeholder `__holded__.contact__unknown`** (res_id=16,
"Cliente historico no identificado") al que apuntarán los ~1.149
docs con `contactId` no resoluble. 3.364 ext_ids
`__holded__.contact_*` registrados; 190 de ellos son contacts
duplicados que enlazan al partner canonical (aggregate de
`customer_rank` + `supplier_rank` con OR lógico).

**Política dedup**: clave `(countryCode, code.upper())`. El campo
`code` (CIF/NIF) está populado en 3.173/3.363 contactos vs solo 18
con `vatnumber` — dedup por `code` es lo correcto en este dump. 188
codes con duplicados consolidados en un solo partner. Codes
placeholder (`""`, `"0"`, `"00"`...) caen a `unique_partner` (cada
contact = un partner propio).

**Política VAT** (endurecida tras crash mid-run con Amazon EMEA LU):
- ES → deriva `vat` desde `code` con prefijo `ES`. Odoo l10n_es
  valida dígito de control; la mayoría de codes ES en el dump son
  válidos.
- non-ES → solo usar `vatnumber` explícito si Holded lo trae (18
  contactos). Nunca el `code` (que para non-ES contiene cualquier
  cosa: tax id Amazon `W0185696B`, `EU372041333`, `SENDGRID`).
- Si Odoo aún rechaza por `base_vat`, `_upsert_with_vat_fallback`
  reintenta sin `vat` y cuenta `stats.vat_dropped` (0 en este run).

**Resolución país/estado** (state_name_aliases): indexa los 52
estados ES por nombre completo + parte parentizada + cada lado de
slash `X/Y` + sinónimo manual `Baleares` → `Illes Balears (Islas
Baleares)`. `normalize_province` strip diacritics + casefold. Tras
estos tunings: 0/2.572 provinces ES sin match (antes 806).

**Estado Odoo post-load**:
- `res.partner` total: 3.177 (3.169 nuevos + 7 pre-existentes + 1
  placeholder)
- 7 `active=False`: 6 contactos Holded con marca `(NO USAR)` en el
  nombre + 1 baseline.
- 2.687 con VAT (todos ES + 17 non-ES explícitos), 3.022 country=ES.
- Distribución ranks: cust_only=2.244 / supp_only=793 / both=30 /
  neither=110 (los 110 son contactos `type=''` o `lead` sin
  `clientRecord`/`supplierRecord` populados — leads no convertidos
  + la propia empresa cuyo contact en Holded no tiene rank).

**Cómo afecta a `resolve_partner` para loaders downstream
(invoices, purchases, etc.)**: ahora `resolve_partner({"id": <hid>})`
hace lookup directo por ext_id `__holded__.contact_<hid>` y resuelve
en O(1) cache. Los 1.149 docs con `contactId` ausente / no
resoluble apuntarán al placeholder unknown (id=16) sin abortar el
batch.

**Reproducibilidad**: idempotencia probada con `--limit 10` segundo
pase (10 updates, 0 creates, 0 errors). Snapshot completo en
`snapshots/2026-05-12_fase-5.1-loader-partners.json`.

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
