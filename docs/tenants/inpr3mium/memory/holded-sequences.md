# Numbering sequences Holded → Odoo — inpr3mium

Counters de las secuencias de Holded en el momento del dump
**2026-05-11**, y la regla operativa para preservar correlatividad
AEAT en el cutover.

> Estos valores son **snapshots puntuales** — quedarán obsoletos al
> hacer el siguiente dump (cualquier factura nueva en Holded
> incrementa el counter). Re-leer `numbering_series.json` del dump
> más reciente antes del cutover Fase 5.5 para los valores definitivos.

## Counters en el dump 2026-05-11

Source: `docs/tenants/inpr3mium/holded-export/2026-05-11/numbering_series.json`.

### Ventas (sale)

| Holded format | Last counter | Journal Odoo equivalente |
|---|---:|---|
| `A-%%%%%%` (invoice) | 9098 | `A-` (id=7) |
| `AC-%%%%%%` (invoice abonos) | 1845 | `AC-` (id=13) |
| `AC-%%%%%%` (creditnote) | 1818 | `AC-` (mismo journal, decisión Fase 4.3) |
| `L-%%%%%%` (Laboratorios) | 1313 | `L-` |
| `FVU-%%%%%%` (Facturas especiales) | 14 | `FVU-` |
| `KD-%%%%%` (Facturas Kit Digital) | 163 | `KD-` |
| `AF-%%%%%` (Autofactura) | 14 | `AF-` |

### Compras (purchase)

| Holded format | Last counter | Journal Odoo equivalente |
|---|---:|---|
| `PB-%%%%%%` (Factura de Gastos) | 12017 | `PB-` (id=8) |
| `PI-%%%%%%` (Facturas compras Inmovilizado) | 361 | `PI-` |
| `PR%%%%%` (purchaserefund) | 71 | `PB-` con `refund_sequence=True` (id=8) |

## Regla para Fase 5.0 / 5.5 (cutover)

**Pre-cargar `ir.sequence.number_next`** de cada journal Odoo con el
counter del último dump pre-cutover **+1**. Si en el momento del
cutover el counter A- de Holded es 9098, Odoo debe arrancar en
`A-9099`.

**Crítico**: hacer esto **inmediatamente antes del cutover** (Fase
5.5), NO antes del subset de validación 5.3. Si se hace antes, los
moves de validación 5.3 consumirán huecos `A-9099`, `A-9100`... y al
borrarlos quedan huecos en la numeración (AEAT rechaza).

**Procedimiento**:

```python
# Pseudocódigo del paso del cutover
last_dump = read_json("holded-export/<CUTOVER_DATE>/numbering_series.json")
for journal_code, holded_counter in [("A-", 9098), ("AC-", 1845), ...]:
    sequence = env["ir.sequence"].search([
        ("code", "=", f"account.journal.{journal_code}"),
        ("company_id", "=", 1),
    ])
    sequence.number_next = holded_counter + 1
```

(El name exacto de `ir.sequence.code` para journals en Odoo 19 hay
que confirmarlo cuando llegue 5.5 — en Odoo 19 las secuencias de
journal cambiaron de modelo: ver gotchas en agent memory
`project_odoo19_doodba_gotchas`.)

## Decisión sobre AC- (validada por Fase 4.6 smoke test)

En Holded, AC- se usa para **dos types distintos**:
- `invoice` con monto negativo (abonos): counter 1845.
- `creditnote` (rectificativas formales): counter 1818.

Ambos comparten la misma secuencia `AC-%%%%%%`. En Odoo se mapean al
mismo `account.journal` "Abonos Ventas" (id=13, code=`AC-`,
type=`sale`), sin `refund_sequence`. La numeración resultante en Odoo
4.6 smoke test fue `AC-/2026/00001` correctamente independiente del
journal `A-` original — comportamiento validado para que la
correlatividad de las dos secuencias Holded se preserve en una sola
secuencia Odoo.

## Decisión sobre PR-

PR (purchaserefund Holded, 71 docs hasta 2026-05-11) tiene volumen
bajo. En lugar de crear un journal separado, se usa
`refund_sequence=True` en `PB-` (id=8). En Odoo el comportamiento es:
los `in_refund` posteados en PB- reciben prefijo PR- automáticamente.
El counter inicial será 72.
