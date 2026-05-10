# Posiciones fiscales y configuracion fiscal

## `account.fiscal.position`

Mapea impuestos y cuentas segun el contexto del cliente/proveedor.
Campos clave:

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Etiqueta. |
| `company_id` | Many2one(res.company) | Multi-company. |
| `auto_apply` | Boolean | True para deteccion automatica al asignar partner. |
| `vat_required` | Boolean | True = solo se aplica si el partner tiene VAT. |
| `country_id` | Many2one(res.country) | Pais del partner (NULL = cualquier). |
| `country_group_id` | Many2one(res.country.group) | Grupo de paises (UE, EFTA). |
| `state_ids` | Many2many(res.country.state) | Estados/provincias. |
| `zip_from` / `zip_to` | Char | Rango de codigos postales (Canarias, Ceuta). |
| `tax_ids` | One2many(account.fiscal.position.tax) | Mapeo origen->destino. |
| `account_ids` | One2many(account.fiscal.position.account) | Mapeo de cuentas. |
| `note` | Text | Nota interna. |

### Logica de auto-aplicacion

Cuando se asigna un partner a una factura/pedido, Odoo busca la primera
posicion fiscal que cumpla TODOS los criterios:

1. `auto_apply=True` y `company_id` coincide.
2. `vat_required=False` o partner tiene VAT.
3. Pais y/o country_group coinciden con el partner.
4. Estados/zip si estan especificados.

Si ninguna posicion cumple, no se aplica posicion (impuestos por defecto
del producto).

**Orden de prioridad**: cuanto mas especifico, mas prioritario. Una FP
con `country_id=ES` gana sobre una con `country_group_id=Europe` si el
partner es ES.

## `account.fiscal.position.tax`

Mapeo origen -> destino:

```python
{'tax_src_id': vat21_id,   # IVA 21% interior
 'tax_dest_id': vat0_eu_id} # IVA 0% intracomunitario
```

Si `tax_dest_id` es `False`, el impuesto se elimina (export sin IVA).

## `account.fiscal.position.account`

Mapeo de cuentas:

```python
{'account_src_id': account_700_id,   # Ventas mercaderias
 'account_dest_id': account_700_eu_id} # Ventas UE
```

Util para reporting separado de operaciones intracomunitarias.

## Presets espanoles canonicos

### 1. Regimen interior (default, no requiere FP)

Sin posicion fiscal. Impuestos por defecto: IVA 21% / 10% / 4% segun
producto.

### 2. Regimen intracomunitario (B2B UE con VAT)

```python
{
    'name': 'Regimen intracomunitario',
    'company_id': company_id,
    'auto_apply': True,
    'vat_required': True,
    'country_group_id': eu_group_id,  # Excluye ES
    'tax_ids': [
        (0, 0, {'tax_src_id': iva21_sale, 'tax_dest_id': iva0_intra_sale}),
        (0, 0, {'tax_src_id': iva10_sale, 'tax_dest_id': iva0_intra_sale}),
        (0, 0, {'tax_src_id': iva4_sale,  'tax_dest_id': iva0_intra_sale}),
        # Compras
        (0, 0, {'tax_src_id': iva21_purch, 'tax_dest_id': iva21_isp_purch}),
        (0, 0, {'tax_src_id': iva10_purch, 'tax_dest_id': iva10_isp_purch}),
    ],
}
```

### 3. Exportacion (B2B fuera UE)

```python
{
    'name': 'Exportacion',
    'auto_apply': True,
    'vat_required': False,
    'country_group_id': non_eu_group_id,
    'tax_ids': [
        (0, 0, {'tax_src_id': iva21_sale, 'tax_dest_id': iva0_export_sale}),
        # ... idem para 10 y 4
    ],
}
```

### 4. Recargo de Equivalencia (cliente espanol bajo RE)

```python
{
    'name': 'Recargo de Equivalencia',
    'auto_apply': False,  # Manual: se asigna al partner explicitamente
    'tax_ids': [
        # Reemplaza IVA simple por IVA + RE
        (0, 0, {'tax_src_id': iva21_sale, 'tax_dest_id': iva21_re_sale}),
        (0, 0, {'tax_src_id': iva10_sale, 'tax_dest_id': iva10_re_sale}),
        (0, 0, {'tax_src_id': iva4_sale,  'tax_dest_id': iva4_re_sale}),
    ],
}
```

Marcar el partner con `property_account_position_id = re_id`.

### 5. IVA de Caja

`l10n_es` provee impuestos `S_IVA21B_IC`, `S_IVA10B_IC`, etc. Crear FP
que mapea los normales a los `_IC`.

### 6. Canarias / Ceuta / Melilla (IGIC / IPSI)

Diferente de IVA peninsular. Usar `zip_from`/`zip_to` o directamente
`state_ids`. Requiere modulos OCA `l10n_es_igic`. Si no estan
instalados, deriva al skill `odoo-module-admin`.

## `res.country.group`

Grupos predefinidos relevantes:

| XML-ID | Significado |
|--------|-------------|
| `base.europe` | Espacio Economico Europeo (UE + Islandia + Liechtenstein + Noruega). |
| `base.eurozone_country_group` | Eurozona (subset de UE). |

Para B2B intra-UE excluyendo Espana: usar `base.europe` y filtrar el
pais del partner != ES en el dominio del FP, **o** crear un grupo
custom "EU sin Espana".

## Patron canonico

```bash
python3 scripts/fiscal_position_setup.py \
    --preset intra_eu \
    --company 2
```

El script:

1. Localiza el `res.country.group` europeo via XML-ID `base.europe`.
2. Localiza los impuestos `S_IVA21B`, `S_IVA10B`, `S_IVA4B` y sus
   contrapartes `S_IVA0_IC` (intracomunitario).
3. Crea o actualiza la `account.fiscal.position` con `auto_apply=True`,
   `vat_required=True`, `country_group_id=europe_id` y los mapeos.
4. Es idempotente sobre `(company_id, name)`.

## Errores frecuentes

- FP no se auto-aplica: comprobar que `auto_apply=True`, que el partner
  tiene VAT (si `vat_required`) y que el pais del partner coincide.
- IVA 0% intracomunitario aparece pero el modelo 349 no lo recoge:
  verificar que el impuesto destino tiene `tax_scope='service'` o
  `'consu'` correcto y que esta marcado para reporting AEAT.
- Doble FP aplicada: solo se aplica UNA. Si dos cumplen, gana la primera
  por `id` (orden de creacion). Reordena via campo `sequence` si existe.
