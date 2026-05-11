# Treasury accounts Holded → Odoo — inpr3mium

Mapeo cuentas de tesorería específicas de inpr3mium, derivado del
análisis del dump 2026-05-11 (`treasuries.jsonl` cruzado contra
`dailyledger.jsonl`).

> Para el **patrón genérico** de cómo Holded modela tarjetas
> (treasury card decorativo + cuenta 521x donde se acumula la deuda),
> ver agent memory `project_holded_treasury_card_pattern`. Este
> archivo solo contiene los mapeos concretos de inpr3mium.

## Bancos (4) — creados en Fase 5.0 (2026-05-11)

Heurística confirmada por el operador: la cuenta Holded
`5720XXXXXXX` (11 dig) sigue el patrón `5720 + 4-dig código BdE + 01`.

| Treasury | Cuenta 11d | BdE | IBAN | Acct id | Journal id | Code | partner.bank id |
|---|---|---|---|---:|---:|---|---:|
| BBVA | `57200018201` | `0182` | ES65 0182 8682 2602 0012 8502 | 713 | 20 | BBVA | 3 |
| Banco Sabadell | `57200008101` | `0081` | ES14 0081 0646 3700 0123 4632 | 714 | 21 | SAB | 4 |
| Santander | `57200004901` | `0049` | ES15 0049 3764 3127 1410 9882 | 712 | 19 | SAN | 2 |
| Qonto | `57200688801` | `6888` | ES21 6888 0001 6002 2535 0289 | 715 | 22 | QON | 5 |

Estructura aplicada por cada banco: (a) `account.account` 11-dig hija
de `572000` con `account_type='asset_cash'`; (b) `account.journal`
type=`bank` con `default_account_id` y `suspense_account_id=388`; (c)
`res.partner.bank` con IBAN sobre `res.company.partner_id=1`,
enlazado vía `account.journal.bank_account_id` (NO vía
`res.partner.bank.journal_id` — es one2many reverse, ver agent
memory `project_odoo19_doodba_gotchas`).

**Legacy**: BNK1 (id=12, account 572001 id=694) placeholder de
`l10n_es_pymes` queda activo sin movimientos — archivar tras
confirmación operador.

## Tarjetas — creadas en Fase 5.0 como `account.account` 521x (sin journal)

Las tarjetas en Holded son treasury decorativo (saldo 0 en UI). El
flujo real va por cuentas `521xxxxxxx` con `account_type=liability_current`.
Identificación por descripciones literales en dailyledger:

| Treasury Holded UI | Cuenta `521` | Acct id | Descripción literal |
|---|---|---:|---|
| Visa BBVA Carles | `52100000014` | 716 | "LIQUIDACION VISA BBVA C.S." |
| Visa Sabadell Carles | `52100000006` | 717 | "TARJETA B.S. C.S. DICIEMBRE" |
| Sabadell Geraldine MC | `52100000017` | 718 | "TARJETA G.G. B.S. DICIEMBRE" |
| Visa Santander Carles | — | — | sin movimientos en dailyledger → **omitida** |

Plus **3 tarjetas TELETAC** (peajes) NO presentes en UI Holded pero
con movimientos en dailyledger — tarjetas por conductor:

| Cuenta `521` | Acct id | Descripción literal | Conductor |
|---|---:|---|---|
| `52100000015` | 719 | "LIQUIDACION TELETAC DICIEMBRE J.T." | J.T. |
| `52100000016` | 720 | "LIQUIDACION TELETAC DICIEMBRE J.R." | J.R. |
| `52100000018` | 721 | "LIQUIDACION TELETAC DICIEMBRE H.S." | H.S. |

Total tarjetas creadas como `account.account 521x` en Odoo: **6**.

## Cuentas a omitir

| Treasury Holded | Razón |
|---|---|
| Visa Santander Carles | Sin movimientos en dailyledger; tarjeta declarada pero nunca usada |
| Linea descuento Sabadell | Sin movimientos (confirmado por operador 2026-05-11) |
| TRASHOLDED | Suspense técnica Holded ("Cuenta no conectada"). Equivale a `account.journal.suspense_account_id` en Odoo — no crear journal |
| BBVA1 | Sin movimientos visibles, probablemente duplicado o histórico. Revisar definitivamente al cargar histórico antes de archivar |
| `55500000007` | NO es treasury real: el nombre es código PGCE 555 "Partidas pendientes de aplicación". Mapear como `account.account` puro, no journal |

## Anomalías en dailyledger

Cuentas `5720` que aparecen en asientos pero no encajan en el patrón
`5720XXXX01`:

- `57200002100` (8 movs, "COBRO EFECTOS"): pos 5-8 = `0021`, NO es
  código BdE estándar. Hipótesis: cuenta histórica antes de la
  reorganización del plan contable Holded. Posiblemente BBVA1 o una
  cuenta migrada. Investigar al cargar histórico.
- `57200000000` (5 movs, "Traspaso Bancos"): cuenta padre genérica
  `572000`. Es la cuenta raíz, usada para asientos internos de
  traspaso entre bancos. En Odoo mapea a `account.account` `572000`
  directamente, no es journal.
