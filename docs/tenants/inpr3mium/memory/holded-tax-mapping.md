# Tax mapping Holded → Odoo — inpr3mium

Resultado del análisis cruzado del dump del 2026-05-11 contra el
catálogo Holded y el `account.tax` lineup de Odoo
(post-`l10n_es_pymes`). Aplicado en **Fase 4.5b** vía RPC. Snapshot:
`docs/tenants/inpr3mium/snapshots/2026-05-11_fase-4.5b.json`.

> Para el **patrón genérico** de cómo Holded modela impuestos
> engañosos (keys que no describen el concepto fiscal real, catch-alls
> sospechosos), ver agent memory `project_holded_tax_gotchas`. Este
> archivo solo contiene la evidencia y decisiones específicas de
> inpr3mium.

## Universo realmente usado

Del catálogo Holded de **103 tax keys**, inpr3mium solo usa **17 keys
de verdad** (cross-reference de `products[].taxes` en los 12.212
documentos del dump). Las 86 restantes son del catálogo por defecto
y nunca se aplicaron a una línea real. Esto justifica archivar las
27 taxes no usadas en Odoo (RE recargo equivalencia + tipos 2/5/7.5%
no aplicables).

## Hallazgo crítico — BIDAFARMA = ISP, no exención

El key `s_iva_exento` aparece en **998 líneas** (~5% de las ventas),
mayoritariamente facturas al **GRUPO BIDAFARMA**. El nombre del key
sugiere "exención Art.20", pero las descripciones literales en
`products[].desc` y las notas dicen:

> "FACTURA EXENTA DE IVA según prevé el artículo 84 Uno 2º letra g)
> de la ley del IVA"

Es **Inversión del Sujeto Pasivo en ventas**, no exención. Mapeo:

- `s_iva_exento` → Odoo `0% RC` (id=109), **no** `0% EXEMPT Art.20`
  (id=69).

Confundir los dos rompe la casilla del modelo 303. Saberlo a tiempo
en Fase 4.5b evitó cargar 998 líneas en la casilla equivocada al
hacer el histórico.

## Subcuentas analíticas creadas

Replicando la granularidad 11-dig de Holded como hijas de las cuentas
PGCE Pymes raíz, para que los `account.move.line` toquen el mismo
nivel de detalle que tiene el histórico Holded:

**Sobre `472000` Input VAT** (5 subcuentas):
- `47200000021` HP IVA soportado 21%
- `47200000121` HP IVA soportado servicios intracom 21%
- `47200000010` HP IVA soportado 10%
- `47200000004` HP IVA soportado 4%
- `47200000000` HP IVA soportado (genérica)

**Sobre `477000` Output VAT** (6 subcuentas):
- `47700000021` HP IVA repercutido 21%
- `47700000010` HP IVA repercutido 10%
- `47700000004` HP IVA repercutido 4%
- `47700000000` HP IVA repercutido (genérica)
- `47700000121` HP IVA repercutido ISP servicios intracom 21%
- `47700000221` HP IVA repercutido Inversión Sujeto Pasivo 21%

**Sobre `475100` Withholdings** (3 subcuentas):
- `47510000001` HP retenciones IRPF 1%
- `47510000005` HP retenciones IRPF 5%
- `47510000010` HP retenciones IRPF 10%

**Total: 14 subcuentas.** Si en Fase 5 se descubren tipos adicionales
en el histórico (ej. IRPF 15% para profesionales, IRPF 7% para
nuevos profesionales), se añadirán siguiendo el mismo patrón.

## Taxes Odoo anotadas

16 `account.tax` recibieron `description = "[holded: <key>]"` para
que el ETL Fase 5 pueda resolver el tax_id desde la key Holded vía
substring match. Las 5 más relevantes para el smoke test de Fase 4.6
y para arranque de Fase 5:

| Odoo tax id | Name | Holded key | Subcuenta repartition |
|---:|---|---|---|
| 6 | 21% S (sale) | `s_iva_21` | `47700000021` |
| 8 | 21% S (purchase) | `p_iva_21` | `47200000021` |
| 109 | 0% RC (sale) | `s_iva_exento` (BIDAFARMA ISP) | n/a (sin VAT line) |
| 112 | 21% RC (purchase) | `p_iva_invsuj` | input `47200000021` + mirror `47700000221` |
| 9, 10 | 21% EU S / EU G (purchase) | `p_iva_adqintras_21` / `p_iva_adqintrab_21` | doble repartition intracom |

Verificado en Fase 4.6: los `account.move.line` resultantes tocan las
subcuentas correctas (no las padres genéricas `477000`/`472000`).

## Deuda técnica para ETL Fase 5

Casos heterogéneos que NO son mapeables 1:1 y requieren reclasificación
caso-por-caso al cargar el histórico:

### `p_iva_exento` (2.306 docs, catch-all)

Mezcla varios escenarios:
- Servicios extra-UE NO detectados como ISP por el operador Holded
  (deberían ser `0% Exempt OP` con país no-UE).
- Sanitarios y servicios médicos auténticos Art.20 (`0% EXEMPT Art.20`).
- Cheques restaurante / formación (Art.20 también).
- Renting Arval / Lease Plan (no debería ser exento, error operativo
  Holded — IVA 21% soportado o ISP según contrato).
- Algunos errores puros (deberían ser 21% pero el operador eligió
  exento).

Decisión: mapear default a `0% Exempt OP` (id=95) y dejar log de
docs reclassified durante el ETL para revisión del operador.

### 2 líneas anómalas con `s_ret_19` en purchases

El key `s_ret_*` es de retenciones en **ventas** (IRPF que el cliente
retiene). Encontrarlas en `purchase` documents es un error de tipeo
del operador Holded. Reclasificar manualmente al cargar.

### `p_iva_invsuj` (ISP genérico)

Confirmado que en inpr3mium se usa correctamente como ISP nacional
(no intracom). Pero validar al cargar que las contrapartidas tienen
NIF ES (no UE) — si no, recategorizar como `p_iva_adqintras_*`.

## Taxes archivadas

27 taxes archivadas para reducir ruido en el formulario de factura:

- 6 RE (Recargo de Equivalencia): inpr3mium es B2B servicios, RE no aplica.
- 21 rates no estándar: 2%, 5%, 7.5% — no se usan en España general
  y nunca aparecen en el dump.
