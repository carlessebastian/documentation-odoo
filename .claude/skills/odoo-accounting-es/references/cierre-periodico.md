# Cierre periodico - mensual, trimestral, anual

Procedimientos y checklists para cerrar correctamente cada periodo
contable en Odoo, con foco Espana.

## Cierre mensual (recomendable)

Aunque no es obligatorio en Espana, cerrar mensualmente facilita el
trimestral. Pasos:

1. **Postear todos los borradores del mes** (facturas, asientos manuales).
2. **Conciliar bancos** (todas las lineas del extracto del mes).
3. **Verificar saldo de cuentas tesoreria** = saldos bancarios reales.
4. **Provisiones**: nominas pendientes, IVA pendiente, suministros.
5. **Reconciliar partner balances**: facturas vs pagos.
6. **Bloquear con `tax_lock_date`** = ultimo dia del mes.

## Cierre trimestral

Igual que mensual + obligaciones AEAT del trimestre:

1. Cierre mensual del ultimo mes del trimestre.
2. Validar SII/Verifactu al dia (todas las facturas enviadas, sin
   errores pendientes).
3. Generar libros IVA del trimestre.
4. Generar **Modelo 303** (IVA), revisar casillas, presentar.
5. Generar **Modelo 349** si hay operaciones intracomunitarias.
6. Generar **Modelo 369** si hay OSS.
7. Generar **Modelo 111/115/130** segun corresponda.
8. Pagar/domiciliar antes del 20 del mes siguiente.
9. Bloquear con `tax_lock_date` y `purchase_lock_date` /
   `sale_lock_date` si procede.

## Cierre anual

### Operaciones contables

1. **Amortizaciones**: ejecutar todos los asientos de amortizacion
   pendientes (`account.asset.depreciation` o `account.asset.line`).
2. **Periodificaciones**: ingresos/gastos diferidos (cuentas 480, 485,
   567).
3. **Provisiones**: insolvencias (cuenta 4900), garantias (4995),
   bajas inventario.
4. **Variacion de existencias**: ajustar cuenta 610-619.
5. **Tipos de cambio definitivos** al 31-dic para saldos en divisas
   (revaluacion).
6. **Regularizacion IVA**: prorrata definitiva, bienes inversion.
7. **Calculo IS**: provisionar Impuesto sobre Sociedades estimado.
8. **Asiento de regularizacion**: cerrar cuentas 6xx y 7xx contra 129
   (Resultado del ejercicio).

### Asientos de cierre y apertura

Tradicionalmente en Espana se hacen 2 asientos en el ultimo dia y
primer dia del ano siguiente:

| Asiento | Que hace |
|---------|----------|
| **Cierre** | Cuentas 6xx y 7xx -> 129. Cuentas patrimoniales mantienen saldo |
| **Apertura** | (No siempre se hace) Reabrir cuentas patrimoniales con su saldo |

En Odoo, el motor `account.report` y el ledger continuan funcionando
sin necesidad de asientos de cierre/apertura formales. Sin embargo,
**el balance de comprobacion final** debe reflejar:

- Cuentas de explotacion (6xx, 7xx) a cero o apuntadas a 129.
- Cuenta 129 con el resultado del ejercicio.
- Cuentas patrimoniales (1xx, 2xx, 3xx, 4xx, 5xx) con su saldo de
  cierre.

### Distribucion de resultados (ano siguiente, abril-junio)

Tras la Junta General que aprueba cuentas:

1. Asiento: 129 -> 121 (perdidas) o 129 -> 113 (reservas) o 129 -> 526
   (dividendos) segun acuerdo.
2. Pago de dividendos con retencion 19%.
3. Modelo 200 (IS) en julio (ejercicios coincidentes con ano natural).

### Modelos AEAT post-cierre

| Mes | Modelo | Concepto |
|-----|--------|----------|
| Enero ano N+1 | 390 | Resumen anual IVA |
| Enero N+1 | 180 | Resumen anual retenciones alquileres |
| Enero N+1 | 190 | Resumen anual retenciones trabajo/profesionales |
| Febrero N+1 | 347 | Operaciones >3.005 EUR |
| Marzo N+1 | 720 | Bienes en el extranjero (si aplica) |
| Marzo N+1 | 184 | Imputacion de rentas (sociedades civiles) |
| Julio N+1 | 200 | Impuesto sobre Sociedades |
| Noviembre N+1 | 232 | Operaciones vinculadas |

## Lock dates

Configurar en `res.company` con escalado:

```
1. Tras cerrar mes: tax_lock_date = ultimo dia del mes
2. Tras cerrar trimestre y modelos: actualizar tax_lock_date
3. Tras cierre anual y modelo 200: fiscalyear_lock_date = 31-dic
```

**No saltarse esto**: el lock date es la unica garantia de que nadie
modificara movimientos ya declarados. Quitarlo temporalmente requiere
permiso de admin contable.

## Reportes anuales clave

### Cuentas anuales (Mercantil)

Empresas obligadas a depositar en Registro Mercantil (todas las
sociedades) presentan en abril-mayo:

| Documento | Modulo Odoo |
|-----------|-------------|
| Balance | `account.report` "Balance Sheet" |
| Cuenta de PyG | `account.report` "Profit and Loss" |
| Estado cambios patrimonio neto | Manual o OCA |
| Estado flujos efectivo | Manual o `mis_builder` |
| Memoria | Externa al ERP |

### Formato XBRL para Registro

`l10n_es_aeat_pyme_xbrl` (OCA) genera el XBRL para deposito.
Alternativamente, exportar PDF de los informes y rellenar manualmente
los modelos PYME/Normal del Registro Mercantil.

## Checklist de cierre anual (ejecutable)

El script `period_close_checklist.py` valida:

- [ ] Sin facturas en draft con fecha del periodo.
- [ ] Sin asientos en draft del periodo.
- [ ] Todos los extractos bancarios importados y conciliados.
- [ ] SII/Verifactu sin errores pendientes.
- [ ] Cuentas 4xx (HP, partners) sin saldos sospechosos.
- [ ] Saldos de tesoreria conciliados con bancos.
- [ ] Sin diferencias de divisa pendientes.
- [ ] Amortizaciones del periodo postedas.
- [ ] Lock dates apropiados configurados.

## Reapertura ejercicio (excepcional)

Si se descubre un error tras `fiscalyear_lock_date`:

1. Modificar `fiscalyear_lock_date` (admin).
2. Crear el asiento correctivo con fecha del ejercicio.
3. Restaurar lock date.
4. Si afecta IVA ya declarado: presentar modelo 303
   complementario/sustitutivo (`tipo_declaracion='C'` o `'S'`).
5. Documentar el motivo y el asiento en chatter.

## Diferencias relevantes Odoo vs PGCE manual

| Concepto | Odoo | PGCE manual |
|----------|------|-------------|
| Asiento de cierre 6/7 -> 129 | Implicito en motor reportes | Asiento explicito ultimo dia |
| Asiento apertura | No necesario | Asiento explicito 1 enero |
| Ano fiscal | `account.fiscal.year` (puede no coincidir natural) | Casi siempre natural |
| Periodo contable | Deducido de `date` | Periodos formales 1-12 + cierre |
| Numeracion asientos | Por diario, por ano | Tradicionalmente unificada |

## Buenas practicas

1. **Una cuenta = una funcion**: no usar la misma cuenta para conceptos
   distintos. Crear sub-cuentas (codigos largos) si es necesario.
2. **Conciliar pronto, no tarde**: cuanto mas reciente la operacion, mas
   facil identificar discrepancias.
3. **Lock dates incrementales**: avanzar siempre, nunca retroceder
   (excepto correcciones excepcionales).
4. **Mantener narrativa**: usar `narration` y chatter para documentar
   ajustes complejos.
5. **Backups antes del cierre anual**: snapshot de la DB antes de
   ejecutar regularizacion final.
