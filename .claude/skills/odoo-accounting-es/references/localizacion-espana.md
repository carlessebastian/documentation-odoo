# Localizacion espanola - PGCE, IVA, IRPF, RE, NIF

Resumen operativo de la fiscalidad espanola tal como la modelan los modulos
`l10n_es` (Odoo Enterprise) y los OCA equivalentes.

## PGCE 2008

Tres planes preconfigurados (modulo `l10n_es`):

| Plan | Modulo / variante | Cuando usarlo |
|------|-------------------|---------------|
| PYMES | `l10n_es` (default) | PYMES y autonomos |
| Completo | `l10n_es_full` | Empresas medianas/grandes |
| Asociaciones (no lucrativas) | `l10n_es_associations` | Asociaciones, fundaciones |

Estructura: 7 grupos, codigos de 3-7 digitos. Cuentas tipicas:

| Codigo | Cuenta |
|--------|--------|
| 430 | Clientes |
| 400 | Proveedores |
| 410 | Acreedores por prestaciones de servicios |
| 472 | HP IVA soportado |
| 477 | HP IVA repercutido |
| 4751 | HP acreedora por retenciones practicadas |
| 4752 | HP acreedora por IS |
| 4730 | HP retenciones y pagos a cuenta |
| 700-705 | Ventas |
| 600-602 | Compras |

Las cuentas se etiquetan (`account.account.tag`) para mapear a casillas de
modelos AEAT (303, 390, etc.).

## IVA - tipos vigentes (2026)

| Tipo | Concepto | XML-ID `l10n_es` |
|------|----------|------------------|
| 21% | General | `S_IVA21B`, `P_IVA21_BC` |
| 10% | Reducido (alimentos, hosteleria, transporte) | `S_IVA10B`, `P_IVA10_BC` |
| 4% | Superreducido (panadero, leche, libros, medicamentos) | `S_IVA4B`, `P_IVA4_BC` |
| 0% | Exenciones, exportaciones, intracomunitarias | `S_IVA0_E`, `S_IVA0_IC` |
| Exento | Operaciones exentas art. 20 LIVA | `S_IVA_EXE` |

### Casos especiales

- **Inversion del Sujeto Pasivo (ISP)**: art. 84.1.2 LIVA. El comprador
  autoliquida. XML-IDs `*_ISP_*`. Posicion fiscal "Inversion del Sujeto
  Pasivo".
- **Operaciones intracomunitarias (UE)**: factura a 0% IVA, IVA
  autorrepercutido por el comprador. Requiere VAT VIES valido. Posicion
  fiscal "Operaciones intracomunitarias".
- **Exportacion**: a 0% IVA, sin inversion. Posicion fiscal "Exportacion".
- **OSS / IOSS**: ventas a consumidores UE, requiere
  `l10n_es_aeat_mod369_oss`.

## IRPF - retenciones tipicas

| Tipo | Concepto | XML-ID |
|------|----------|--------|
| 7% | Profesionales nuevos (primeros 3 anos) | `P_IRPF7` |
| 15% | Profesionales general | `P_IRPF15` |
| 19% | Alquileres, intereses | `P_IRPF19` |
| 24% | No residentes (general) | `P_IRPF24` |
| 35% | Administradores no residentes | `P_IRPF35` |

Las retenciones IRPF se aplican como impuestos negativos en la linea de
factura. Se acumulan en cuenta 4751 y se declaran en modelos 111 (rendimientos
del trabajo y profesionales) y 115 (alquileres).

## Recargo de Equivalencia (RE)

Aplica a comerciantes minoristas en regimen especial. El proveedor
repercute IVA + RE; el minorista no presenta 303.

| IVA | RE | XML-ID `l10n_es` |
|-----|----|--------------------|
| 21% | 5,2% | `S_REQ52` |
| 10% | 1,4% | `S_REQ14` |
| 4% | 0,5% | `S_REQ05` |

Posicion fiscal: "Recargo de Equivalencia".

## Posiciones fiscales (`account.fiscal.position`)

Las mas usadas en `l10n_es`:

1. **Regimen Nacional** (default sin posicion explicita).
2. **Operaciones intracomunitarias** - mapea IVA 21/10/4 -> 0% intra-UE.
3. **Exportacion** - mapea IVA 21/10/4 -> 0% exportacion.
4. **Recargo de Equivalencia** - anade RE automaticamente.
5. **Inversion del Sujeto Pasivo** - cambia repartition para autoliquidacion.
6. **Criterio de Caja** - difiere devengo IVA hasta cobro/pago.
7. **REAGYP** - regimen especial agricultura, ganaderia y pesca.

Asignacion automatica: `auto_apply=True` + dominio por pais/grupo del
partner. Comprobar siempre que el partner intra-UE tenga
`fiscal_position_id` correcta antes de postear.

## Validacion NIF / CIF / NIE

### Formatos

| Tipo | Patron | Ejemplo |
|------|--------|---------|
| DNI | 8 digitos + letra control | `12345678Z` |
| NIE | X/Y/Z + 7 digitos + letra control | `X1234567L` |
| CIF | letra + 7 digitos + digito/letra control | `B12345678`, `A1234567A` |

Con prefijo VIES para intra-UE: `ES12345678Z`.

### Algoritmos de digito de control

**DNI/NIE**: tomar 8 digitos (NIE: X=0, Y=1, Z=2 + 7 digitos), modulo 23,
mapear a tabla `TRWAGMYFPDXBNJZSQVHLCKE`.

```python
TABLE = "TRWAGMYFPDXBNJZSQVHLCKE"
def dni_letter(num: int) -> str:
    return TABLE[num % 23]
```

**CIF**: algoritmo distinto segun primer caracter (A, B, C... determinan si
el digito de control es numerico o letra). Implementacion completa en
`scripts/verify_es_compliance.py`.

### VIES

Para operaciones intracomunitarias, validar VAT en
https://ec.europa.eu/taxation_customs/vies/. Odoo lo hace via boton "Check
VAT" (`partner.vies_valid` campo computado). Para batch:

```python
client.action("res.partner", [partner_id], "button_check_vat")
```

## `lang` del partner

El idioma del partner determina:
- Plantillas QWeb usadas para PDFs (factura, recordatorio, etc.).
- Mensajes en correos automaticos.

En Cataluna usar `ca_ES` si el cliente lo prefiere; sino `es_ES`. Verificar
que el modulo de idioma esta instalado: Settings > Translations > Languages.

```python
client.write("res.partner", [partner_id], {"lang": "ca_ES"})
```

## Numeracion de facturas

Veri*Factu y SII exigen **numeracion secuencial sin huecos** por diario.
Configurar en `account.journal`:

- `sequence_id` apunta a un `ir.sequence` con `implementation='no_gap'`.
- NO usar `implementation='standard'` en diarios de venta espanoles.

```python
seq = client.search_read("ir.sequence",
    [("code", "=", "account.move.out_invoice")], ["id", "implementation"])
```

Si hay huecos: rellenarlos creando facturas anuladas con el mismo numero
NO esta permitido. Hay que postear una factura "tecnica" o ajustar via
modulo `account_move_name_sequence` (OCA).

## Plan contable y empresa

Asegurarse de que `res.company` tenga:
- `country_id` = Espana.
- `account_fiscal_country_id` = Espana.
- `vat` con prefijo `ES`.
- `currency_id` = EUR.

Si la compania es catalana y maneja varias lenguas, configurar
`partner_id.lang` por defecto y plantillas multilingue.

## Referencia rapida: plantilla minima de factura ES

```python
{
    "move_type": "out_invoice",
    "partner_id": <id_cliente_con_NIF_valido>,
    "invoice_date": "2026-05-10",
    "invoice_date_due": "2026-06-09",
    "journal_id": <id_diario_ventas>,
    "ref": "<referencia_unica_idempotencia>",
    "fiscal_position_id": <id_segun_partner>,  # opcional pero recomendado
    "invoice_line_ids": [
        (0, 0, {
            "name": "Descripcion del servicio o producto",
            "quantity": 1.0,
            "price_unit": 100.00,
            "tax_ids": [(6, 0, [<id_S_IVA21B>])],
            "account_id": <opcional, normalmente del producto>,
        }),
    ],
}
```

Tras crear: validar con `scripts/verify_es_compliance.py`, luego
`action_post`, luego (si Veri*Factu activo) esperar al cron o forzar con
`scripts/send_verifactu.py`.
