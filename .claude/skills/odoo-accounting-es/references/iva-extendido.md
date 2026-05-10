# IVA extendido - libros, prorrata, regularizacion, modelos avanzados

Cubre obligaciones IVA mas alla del 303/390 estandar: libros registro,
prorrata, regularizacion bienes inversion, modelos 369 (OSS), 232
(operaciones vinculadas), 720 (bienes en el extranjero).

## Libros registro de IVA

### Obligacion legal

Todos los sujetos pasivos IVA (excepto regimen simplificado) deben llevar:

| Libro | Contenido |
|-------|-----------|
| **Facturas Emitidas** | Toda factura emitida (out_invoice + out_refund) |
| **Facturas Recibidas** | Toda factura recibida (in_invoice + in_refund) |
| **Bienes de Inversion** | Adquisiciones >3.005,06 EUR amortizables |
| **Determinadas operaciones intracomunitarias** | Movimientos UE temporales |

Para sujetos en SII, **el SII sustituye** la obligacion de libros
papel/Excel.

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_vat_book` | OCA - libro emitido + recibido + bienes inversion |
| `l10n_es_aeat_sii_oca` | OCA - genera libros via SII |
| `account_invoice_supplier_ref_unique` | OCA - garantiza unicidad ref proveedor (requisito libro) |

### Estructura del libro emitido

Columnas obligatorias:

1. Numero correlativo de la anotacion
2. Fecha factura
3. Fecha operacion (si distinta)
4. Numero factura
5. NIF y nombre del cliente
6. Base imponible
7. Tipo IVA
8. Cuota IVA repercutida
9. Total factura
10. Tipo y cuota recargo equivalencia (si aplica)
11. Indicador rectificativa, sustitutiva, etc.

### Generacion programatica (OCA)

```python
book_id = client.create("l10n.es.vat.book", {
    "name": "VAT Book Q1 2026",
    "company_id": 1,
    "year": 2026,
    "period_type": "1T",
})
client.action("l10n.es.vat.book", [book_id], "calculate")
client.action("l10n.es.vat.book", [book_id], "confirm")

# Exportar a XLSX:
result = client.call("l10n.es.vat.book", "export_xlsx", [[book_id]])
```

El script `vat_book.py` automatiza esto y soporta filtros por trimestre/
ano/mes.

## Prorrata IVA

### Cuando aplica

Cuando una empresa realiza simultaneamente operaciones con derecho a
deduccion (sujetas y no exentas) y operaciones sin derecho a deduccion
(exentas, fuera de IVA), el IVA soportado solo es deducible
parcialmente.

### Tipos de prorrata

| Tipo | Cuando | Calculo |
|------|--------|---------|
| **General** | Por defecto | (Operaciones con derecho deduccion / Operaciones totales) * 100 |
| **Especial** | Voluntaria u obligatoria si general difiere >10% | Diferencia entre uso exclusivo y comun |

### Prorrata provisional vs definitiva

- **Provisional** (durante el ano): aplica el % del ano anterior.
- **Definitiva** (4T o regularizacion): se calcula con datos reales del
  ano y se ajusta la diferencia en el modelo 303 del 4T (casillas
  44-46).

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_vat_prorate` | OCA |
| `l10n_es_aeat_mod303_oca` | Soporta casillas de prorrata |

### Patron de calculo

```python
# Operaciones del ano con/sin derecho a deduccion
# (suma de account.move.line agrupada por tax_tag)
domain = [("date", ">=", "2026-01-01"), ("date", "<=", "2026-12-31"),
          ("parent_state", "=", "posted")]
totals_with = client.call("account.move.line", "read_group",
    [domain + [("tax_ids.tag_ids.name", "=", "+sujeto deducible")],
     ["balance:sum"], []])
totals_without = client.call("account.move.line", "read_group",
    [domain + [("tax_ids.tag_ids.name", "=", "+exento")],
     ["balance:sum"], []])

prorrata = totals_with[0]["balance"] / (
    totals_with[0]["balance"] + totals_without[0]["balance"]
) * 100
```

El script `vat_prorate.py` lo hace y devuelve el % final + delta
respecto al provisional aplicado.

## Regularizacion de bienes de inversion

Bienes de inversion (>3.005,06 EUR) regularizan el IVA deducido durante
**4 anos** (5 para inmuebles): cada ano se compara la prorrata definitiva
del ejercicio con la del ano de adquisicion; si difiere >10%, se ajusta
1/4 (o 1/5).

### Calculo simplificado

```
Regularizacion ano N = (P0 - PN) * IVA_inicial / N_periodos
  donde:
    P0 = % deduccion al adquirir
    PN = % deduccion ano N
    N_periodos = 4 (muebles) o 5 (inmuebles)
```

Se imputa en el modelo 303 del 4T del ano de regularizacion.

### Patron Odoo

Los bienes con `account.asset` (Enterprise) o `account_asset_management`
(OCA) tienen historico de prorrata aplicada. El skill no automatiza la
regularizacion (requiere logica fiscal compleja); proporciona helpers
para extraer los datos necesarios:

```python
assets = client.search_read("account.asset",
    [("state", "=", "open"),
     ("acquisition_date", ">=", str(year - 4))],
    ["id", "name", "value", "acquisition_date",
     "value_residual", "tax_amount"])
```

## Modelo 369 - Ventanilla Unica (OSS / IOSS)

### Cuando aplica

Empresas que realizan ventas a distancia B2C (consumidor final) en otros
paises UE por encima del umbral anual de 10.000 EUR.

### Variantes

- **OSS UE**: ventas intra-UE de bienes/servicios B2C.
- **OSS no UE**: servicios prestados por empresas no establecidas en UE.
- **IOSS**: importaciones <150 EUR.

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_eu_oss` | Estandar (Enterprise) |
| `l10n_es_aeat_mod369` | OCA |

### Configuracion clave

1. Activar el modulo `l10n_eu_oss`.
2. Configurar `account.fiscal.position` "OSS - Pais X" para cada pais
   destino (con sus cuentas e impuestos UE).
3. Asignar la posicion fiscal automaticamente segun pais del partner B2C.
4. Generar 369 trimestralmente y declarar el IVA por pais.

### Generacion programatica

`run_aeat_report.py --model 369 --period 2026Q1` (extension del script).

## Modelo 232 - Operaciones vinculadas

Declaracion anual (noviembre) de:

- Operaciones con personas/entidades vinculadas (matriz, filial,
  administradores, conyuges) por importe > 250.000 EUR/ano.
- Operaciones con paraisos fiscales sin minimo.
- Determinadas operaciones especificas (cesion de uso de bienes,
  tenencia de valores).

### Modulos

`l10n_es_aeat_mod232` (OCA). Requiere marcar partners vinculados con
campo custom o tag.

## Modelo 720 - Bienes en el extranjero

Declaracion informativa anual (marzo) de bienes y derechos en el
extranjero por valor > 50.000 EUR en cada bloque (cuentas, valores,
inmuebles).

### Modulos

`l10n_es_aeat_mod720` (OCA). Atencion: tras sentencia TJUE C-788/19
(2022), el regimen sancionador fue declarado contrario a UE; el modelo
sigue obligatorio pero las multas se relajaron.

## Combinaciones tipicas y orden de ejecucion

### Cierre trimestral (final de Q)

1. Validar que SII/Verifactu este al dia (todas las facturas enviadas).
2. Generar libros IVA del trimestre.
3. Generar 303 del trimestre.
4. Generar 349 (intracomunitario, mensual o trimestral segun volumen).
5. Generar 369 si aplica.
6. Pagar via NRC (numero de referencia completo) antes del 20 del mes
   siguiente al fin de trimestre.

### Cierre anual

1. Operaciones rutinarias del 4T.
2. Calcular prorrata definitiva, ajustar 303 del 4T.
3. Regularizar bienes de inversion adquiridos >= 4 anos.
4. Generar **390** (resumen anual IVA) - enero ano N+1.
5. Generar **347** (operaciones >3.005 EUR) - febrero ano N+1.
6. Generar **232** (operaciones vinculadas) - noviembre ano N+1.
7. Generar **720** (bienes extranjero) - marzo ano N+1, si aplica.

## Errores frecuentes y caveats

1. **VAT VIES caducado**: clientes intra-UE deben tener VAT validado
   periodicamente. Sin VAT VIES valido, la operacion va al 21% IVA en
   vez de 0%.
2. **Prorrata mal aplicada**: si Odoo no tiene tags fiscales correctos
   en cuentas/impuestos, los importes del modelo 303 saldran mal.
   Verificar `account.account.tag` antes de cada cierre.
3. **Bienes inversion no marcados**: si no se marca `is_capital_good`
   (o tag equivalente), no entran en libro de bienes inversion ni en
   regularizacion.
4. **Modelo 720 - umbral**: 50.000 EUR es **por bloque, no total**. Una
   empresa con 40.000 en cuentas + 40.000 en valores NO declara aunque
   sume 80.000.
5. **Modelo 232 - vinculacion**: Odoo no detecta vinculacion
   automaticamente; hay que marcarla manualmente o via tag.
