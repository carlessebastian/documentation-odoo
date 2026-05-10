---
description: Ejecuta el cierre mensual ES (compliance, libros IVA, P&L, balance, modelos AEAT)
argument-hint: <YYYY-MM> [--company N]
allowed-tools: Skill, Bash, Read
---

# /cierre-mensual

Orquesta el cierre mensual de un ejercicio espanol en Odoo 19. Ejecuta
la secuencia canonica con confirmaciones entre pasos. Para el cierre
**anual** (asientos 6/7 -> 129 -> 121), usa `/cierre-anual` (no
implementado todavia).

## Argumentos

- `$1` (obligatorio): periodo en formato `YYYY-MM`, p.ej. `2026-04`.
- `$2` (opcional): `--company <N>` para limitar a una compania
  concreta. Sin este flag, se usa la company por defecto del bot
  (`self.env.company`).

`ARGUMENTS = $ARGUMENTS`

## Procedimiento

Sigue estos pasos en orden. **Detente y pide confirmacion al usuario
entre fases marcadas como CHECKPOINT** mostrando un resumen de lo que
viene. No avances al siguiente paso si el actual reporto errores
(scripts devuelven exit no-cero).

### Fase 0: Validacion y contexto

1. Parsea `$1` como `YYYY-MM`. Si no es valido, aborta con un mensaje
   claro pidiendo el formato correcto.
2. Calcula `from_date = YYYY-MM-01` y `to_date = ultimo dia del mes`.
3. Determina si es:
   - Ultimo mes de un trimestre (marzo / junio / septiembre / diciembre)
     -> habra que ejecutar libro IVA + 303 + 349.
   - Ultimo mes del anyo (diciembre) -> avisar al usuario que tras este
     cierre toca el anual con `closing_entries.py` (NO lo ejecutes
     aqui).
   - Mes intermedio -> solo compliance + reports financieros.
4. Verifica variables de entorno (`ODOO_URL`, `ODOO_DB`,
   `ODOO_API_KEY`). Si faltan, aborta.
5. **CHECKPOINT 1**: muestra al usuario:
   - Periodo: `from_date` -- `to_date`
   - Tipo: mes intermedio / fin de trimestre / fin de anyo
   - Lista de pasos que vas a ejecutar
   - Pide "ok" para continuar.

### Fase 1: Compliance ES sobre todas las facturas posteadas

Invoca el skill `odoo-accounting-es`. Usa el script
`verify_es_compliance.py` sobre el dominio
`[('state','=','posted'), ('invoice_date','>=',from_date), ('invoice_date','<=',to_date)]`.

Si reporta facturas no conformes (NIF malo, falta posicion fiscal,
codigos IVA incorrectos, etc.), **DETENTE**. El cierre no debe avanzar
con facturas no conformes. Lista las facturas problematicas al usuario
y sugiere corregirlas con los scripts pertinentes.

### Fase 2: Period close checklist

Ejecuta `period_close_checklist.py --from $from_date --to $to_date`.

El script comprueba:
- Asientos en draft fuera del periodo.
- Conciliaciones bancarias pendientes.
- Lock dates coherentes.
- Contadores de facturacion sin huecos (no_gap).

Reporta resultados al usuario. Si hay warnings, pide decision (continuar
o pausar para corregir).

### Fase 3: Libros IVA emitido y recibido

Si es **fin de trimestre** o el usuario tiene IVA mensual (los grandes
contribuyentes lo tienen), ejecuta:

```
scripts/vat_book.py --period <trimestre o mes>
```

donde `<trimestre>` se calcula de `YYYY-MM`:
- `YYYY-03` -> `YYYYQ1`
- `YYYY-06` -> `YYYYQ2`
- `YYYY-09` -> `YYYYQ3`
- `YYYY-12` -> `YYYYQ4`

Para meses no fin-de-trimestre, salta esta fase a menos que el usuario
diga explicitamente que quiere libros mensuales.

### Fase 4: Reporting financiero

Ejecuta en paralelo:

```
scripts/financial_reports.py --report pl --from $from_date --to $to_date
scripts/financial_reports.py --report balance --as-of $to_date
scripts/financial_reports.py --report trial --from $from_date --to $to_date
```

Muestra al usuario un resumen de cada uno (totales, no el detalle).

### Fase 5: Modelos AEAT (solo fin de trimestre)

**CHECKPOINT 2**: solo si es fin de trimestre. Pregunta al usuario:
"Generar modelos AEAT 303 y 349 ahora? (Y/n)".

Si confirma:

```
scripts/run_aeat_report.py --model 303 --period YYYYQ<n>
scripts/run_aeat_report.py --model 349 --period YYYYQ<n>
```

Para fin de anyo (diciembre), anyade adicionalmente:

```
scripts/run_aeat_report.py --model 390 --period $YYYY
```

Genera los ficheros pero **NO los presenta** a la AEAT. La presentacion
es un paso humano explicito.

### Fase 6: Envios EDI pendientes (SII / Veri*Factu)

Si los modulos `l10n_es_aeat_sii_oca` o `l10n_es_verifactu_oca` estan
instalados (compruebalo con `module_status.py` del skill
`odoo-module-admin`), ejecuta:

```
scripts/send_sii.py            # si SII activo
scripts/send_verifactu.py      # si Veri*Factu activo
```

Reporta facturas con error de envio. Si las hay, deriva al usuario
para revision manual (no reintentes ciegamente).

### Fase 7: Resumen final

Produce un resumen markdown al usuario con:

- Periodo cerrado: `from_date` -- `to_date`
- Compliance: PASS / FAIL (n facturas no conformes)
- Lock dates aplicados: si / no (recomendado aplicar lock manual tras
  presentar AEAT)
- Modelos AEAT generados: lista con paths a los ficheros .csv/.xml
- Envios EDI: ok / pendientes
- **Siguiente paso recomendado**:
  - Mes intermedio: nada urgente.
  - Fin de trimestre: presentar 303/349 en AEAT y aplicar `tax_lock_date`.
  - Fin de anyo: ejecutar `/cierre-anual` (o `closing_entries.py
    --year YYYY` directamente).

## Reglas

- **Idempotente**: si el usuario re-ejecuta `/cierre-mensual 2026-04`,
  no debe romper nada. Los scripts subyacentes detectan operaciones ya
  hechas.
- **Nunca aplica `fiscalyear_lock_date` o `tax_lock_date`
  automaticamente**. Lock dates son un paso legal humano.
- **Nunca presenta a AEAT automaticamente**. Solo genera los ficheros.
- Si cualquier fase falla con exit no-cero, **detente y reporta**. No
  continues silenciosamente.
- Todas las invocaciones de scripts van a traves del skill
  `odoo-accounting-es` (los scripts viven en
  `.claude/skills/odoo-accounting-es/scripts/`). Si el skill no esta
  cargado, cargalo antes de empezar.
