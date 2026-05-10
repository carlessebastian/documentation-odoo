# SII / Veri*Factu / FacturaE - los tres regimenes EDI espanoles

Tres sistemas distintos, requisitos distintos, modulos distintos. Esta guia
explica cuando aplica cada uno y como manejar los errores frecuentes.

## Mapa de decision

```
?Empresa con facturacion > 6 M EUR, REDEME o grupo IVA?
  -> SII (obligatorio, alta frecuencia)
?Empresa o autonomo no obligado a SII?
  -> Veri*Factu (obligatorio desde 1-ene-2026 PYMES, 1-jul-2026 autonomos)
?Factura B2G (a Administracion Publica espanola)?
  -> FacturaE + envio a FACe (obligatorio independientemente del anterior)
?Sede en Pais Vasco?
  -> TicketBAI (en lugar de Veri*Factu)
```

## SII (Suministro Inmediato de Informacion)

Sistema online de la AEAT que recibe los registros de facturacion
emitidas/recibidas/bienes de inversion casi en tiempo real.

### Quien

Obligatorio para:
- Empresas con facturacion > 6.010.121,04 EUR (ano anterior).
- Inscritos en REDEME (Registro de Devolucion Mensual).
- Grupos de IVA.
- Voluntariamente: cualquier sujeto pasivo IVA.

Plazo: **4 dias naturales** desde emision/recepcion (8 si recibida via
intermediario).

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_edi_sii` | Enterprise (oficial) |
| `l10n_es_aeat_sii_oca` | OCA `l10n-spain` (Community) |
| `l10n_es_aeat_sii_cash_basis` | OCA, criterio de caja |
| `l10n_es_aeat_sii_oss` | OCA + OSS |

### Configuracion minima

1. Certificado AEAT (FNMT o equivalente) instalado en `l10n_es_aeat`.
2. `res.company.l10n_es_edi_sii_test_env` = True para sandbox.
3. Cron `Send pending SII documents` activo (en Enterprise: cada 24h por
   defecto; en OCA: configurable).

### Envio manual

Enterprise:
```python
client.action("account.move", [invoice_id], "l10n_es_edi_sii_send_invoices")
```

OCA:
```python
client.action("account.move", [invoice_id], "send_sii")  # nombre puede variar
```

El skill `send_sii.py` detecta el modulo y llama al metodo correcto.

### Errores AEAT comunes

| Codigo | Significado | Accion |
|--------|-------------|--------|
| `1102` | NIF receptor no identificado | Validar VAT VIES |
| `1103` | Factura sin destinatario | Para extranjeros, mapear `IDType` 02-07 |
| `1117` | Importe negativo no permitido | Usar `account.move.reversal` |
| `1130` | Fecha fuera de plazo | Solo para regularizar (declarar fuera de plazo) |
| `1142` | Tipo impositivo invalido | Comprobar `account.tax.amount` |
| `4102` | Anulacion sin original | La factura original debe haberse enviado primero |

## Veri*Factu (RD 1007/2023)

Sistema antifraude que exige que cada factura genere un **registro
encadenado e inalterable** firmado y enviado a la AEAT (modo Veri*Factu) o
conservado localmente (modo "no Veri*Factu" con software certificado).

### Quien

Obligatorio para:
- PYMES desde **1 enero 2026**.
- Autonomos desde **1 julio 2026**.
- Excepciones: ya en SII, sede en territorio foral (Pais Vasco -> TicketBAI;
  Navarra; foral) o factura via FacturaE B2G.

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_edi_verifactu` | Enterprise (Odoo certificado AEAT) |
| `l10n_es_verifactu_oca` | OCA (estado a mayo 2026: rama 18.0 estable; rama 19.0 en migracion activa) |

**Importante para Odoo 19 Community**: si el modulo OCA 19.0 aun no esta
estable, opciones:
1. Esperar a la migracion (ver issues de `OCA/l10n-spain`).
2. Backportar manualmente desde 18.0.
3. Pasarse temporalmente a SII voluntario (mas complejo, mas restrictivo).

### Pre-checks antes de postear con Veri*Factu activo

- [ ] Diario `l10n_es_verifactu_enabled = True`.
- [ ] Certificado AEAT cargado en Settings > Veri*Factu.
- [ ] Numeracion secuencial sin huecos (`ir.sequence.implementation='no_gap'`).
- [ ] No mezclar facturas Veri*Factu y no-Veri*Factu en el mismo diario.
- [ ] POS espanol (`l10n_es_pos`) **desinstalado** si vas a vender por TPV
      con Veri*Factu (incompatibilidad documentada).

### Encadenamiento

Cada `account.move` posteado tiene `l10n_es_edi_verifactu_chain_index` (si
Enterprise) o equivalente OCA. La cadena se verifica con hash del registro
anterior; un fallo rompe la secuencia y obliga a "reanudar cadena".

### QR code

Tras postear, Odoo genera `l10n_es_edi_verifactu_qr_code` (PNG base64) que
debe imprimirse en la factura. Las plantillas QWeb de `l10n_es_edi_verifactu`
ya lo incluyen.

### Modo test

Veri*Factu permite envios de prueba al endpoint de la AEAT preproduccion.
Activar en `res.company.l10n_es_edi_verifactu_test_env = True`. Recomendado
para validar antes del 1-ene-2026.

### Declaracion Responsable

Odoo, al ser proveedor de software de facturacion, presenta su propia
"Declaracion Responsable" (PDF disponible en
`content/applications/finance/fiscal_localizations/spain/declaracion_responsable.pdf`).
Esto **no exime** al cliente final de su propia responsabilidad fiscal.

## FacturaE (Factura-e XML) y FACe

XML-firma de facturas, obligatorio para B2G (Administraciones Publicas
espanolas) desde 2015. Tambien usado en algunos sectores B2B.

### Quien

- B2G: cualquier proveedor de Administraciones Publicas (Estado, CCAA,
  ayuntamientos), salvo facturas < 5.000 EUR (algunos casos exentos).
- B2B: voluntario hoy; con la Ley Crea y Crece sera obligatorio en
  funcion del tamano (calendario en revision a may-2026).

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_edi_facturae` | Enterprise |
| `l10n_es_edi_facturae_adm_centers` | Enterprise (centros administrativos FACe) |
| `l10n_es_facturae`, `l10n_es_facturae_face` | OCA |

### Generar XML

```python
client.action("account.move", [invoice_id], "l10n_es_edi_facturae_generate")
```

El XML se adjunta como `ir.attachment` con mime `application/xml`.

### Centros administrativos FACe

Cada Administracion Publica espanola tiene 3 codigos DIR3 obligatorios:

| Rol | Significado |
|-----|-------------|
| `02` Receptor | Departamento que recibe la factura |
| `03` Pagador | Departamento que paga |
| `01` Fiscal | Oficina contable que la registra |

En el partner cliente (la Administracion), configurar `child_ids` con
`type='facturae_admin_center'` y los tres codigos. Sin esto, FACe rechaza
el XML.

### Envio a FACe

- **Manual via portal**: descargar XML de Odoo, subir a https://face.gob.es.
- **Programatico via FACe API**: requiere certificado y puede usar el
  modulo OCA `l10n_es_facturae_face` o llamadas SOAP custom.
- **Herramienta de escritorio AEAT**:
  https://www.facturae.gob.es/formato/Paginas/descarga-aplicacion-escritorio.aspx

## TicketBAI (Pais Vasco)

Equivalente vasco a Veri*Factu, gestionado por las Diputaciones Forales.

### Modulos Odoo

| Modulo | Origen |
|--------|--------|
| `l10n_es_edi_TBAI` | Enterprise |
| (OCA tiene equivalentes parciales) | |

Configuracion analoga a Veri*Factu (certificado, modo test, cron 24h).
Genera QR especifico TicketBAI.

Si la compania es catalana pero factura a vascos: NO requiere TicketBAI
para emisor; requiere Veri*Factu/SII segun le toque.

## Patron de detección en scripts

```python
def detect_edi_provider(client):
    modules = client.search_read("ir.module.module",
        [("name", "in", [
            "l10n_es_edi_sii", "l10n_es_aeat_sii_oca",
            "l10n_es_edi_verifactu", "l10n_es_verifactu_oca",
            "l10n_es_edi_facturae", "l10n_es_facturae",
            "l10n_es_edi_TBAI",
        ]), ("state", "=", "installed")],
        ["name"])
    return {m["name"] for m in modules}
```

Los scripts `send_sii.py` y `send_verifactu.py` usan este patron.

## Resumen: que verificar antes de "ir a produccion"

1. **Modulo correcto instalado** (Enterprise vs OCA).
2. **Certificado AEAT** valido y no caducado.
3. **Modo test desactivado** (`*_test_env = False`).
4. **Cron de envio activo** y revisado.
5. **Numeracion secuencial sin huecos** en todos los diarios de venta.
6. **Plantilla QWeb** muestra QR (Veri*Factu/TicketBAI) o sello (FacturaE).
7. **Declaracion Responsable** presentada (Veri*Factu).
8. **Pruebas E2E** en sandbox: emitir, anular, rectificar, intracomunitaria,
   exportacion, RE.

Todo esto puede automatizarse con `scripts/verify_es_compliance.py`
ampliado a verificar configuracion global.
