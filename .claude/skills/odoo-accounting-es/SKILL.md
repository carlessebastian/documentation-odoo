---
name: odoo-accounting-es
description: |
  Usa este skill siempre que el usuario trabaje con Odoo 19 Community
  self-hosted para contabilidad y facturacion espanolas (Cataluna/UE):
  crear facturas (account.move out_invoice/in_invoice), postearlas
  (action_post), registrar pagos via account.payment.register, generar
  rectificativas (account.move.reversal), conciliar extractos, calcular
  IVA 21/10/4/0, IRPF y Recargo de Equivalencia, enviar a la AEAT por SII
  o Veri*Factu, generar FacturaE para FACe, o ejecutar modelos AEAT
  303/347/349/390/111/115/130. Activa el skill aunque el usuario solo
  mencione "factura", "asiento", "modelo 303", "AEAT", "SII", "Verifactu",
  "FACe", "PGCE", "Odoo", "ERP", "balance", "P&L" o "create invoice".
license: MIT
allowed-tools:
  - Read
  - Bash(python3:*)
  - Bash(uv:*)
  - mcp__odoo__*
---

# Skill: Odoo 19 Community + contabilidad y facturacion espanola

Este skill convierte a Claude en contable para una instancia self-hosted de
Odoo 19 Community en Espana (con foco Cataluna/UE). Asume modulos
instalados: `account`, `l10n_es`, mas la localizacion EDI de Enterprise
(`l10n_es_edi_sii`, `l10n_es_edi_verifactu`, `l10n_es_edi_facturae`) **o**
las equivalentes OCA (`l10n_es_aeat_sii_oca`, `l10n_es_verifactu_oca`,
`l10n_es_facturae`, `l10n_es_aeat_mod303/347/349/390`).

## Variables de entorno requeridas

| Variable | Proposito |
|----------|-----------|
| `ODOO_URL` | URL base, p.ej. `https://odoo.miempresa.cat` |
| `ODOO_DB` | Nombre de la base, p.ej. `miempresa_prod` |
| `ODOO_USER` | Login del usuario bot (solo necesario para fallback XML-RPC) |
| `ODOO_API_KEY` | API key generada en *Mi perfil > Seguridad > API Keys* |
| `ODOO_FORCE_XMLRPC` | (Opcional) `1` para forzar XML-RPC aunque la version sea >= 19 |

Si falta cualquier variable obligatoria, **detente y pidela al usuario antes
de ejecutar nada**. Nunca hardcodees credenciales en commits.

## Tabla de despacho: peticion -> script -> reference

| El usuario pide... | Ejecuta | Antes lee |
|--------------------|---------|-----------|
| Crear factura cliente | `scripts/create_invoice.py` | `references/workflows.md`, `references/localizacion-espana.md` |
| Crear factura proveedor | `scripts/create_invoice.py --type in_invoice` | `references/workflows.md` |
| Postear factura | (incluido en `create_invoice.py --post`) o `scripts/odoo_client.py` accion `action_post` | `references/workflows.md` |
| Registrar cobro/pago | `scripts/register_payment.py` | `references/workflows.md` |
| Crear factura rectificativa | `scripts/credit_note.py --mode reverse|modify` | `references/workflows.md` |
| Buscar cliente/proveedor | `scripts/partner_lookup.py` | `references/domain-syntax.md` |
| Buscar producto | `scripts/product_lookup.py` | `references/modelos-cheatsheet.md` |
| Buscar/listar impuestos | `scripts/tax_lookup.py` | `references/localizacion-espana.md` |
| Verificar cumplimiento ES | `scripts/verify_es_compliance.py` | `references/localizacion-espana.md`, `references/sii-verifactu-facturae.md` |
| Enviar a SII | `scripts/send_sii.py` | `references/sii-verifactu-facturae.md` |
| Enviar a Veri*Factu | `scripts/send_verifactu.py` | `references/sii-verifactu-facturae.md` |
| Generar PDF de factura | `scripts/report_invoice_pdf.py` | `references/reports.md` |
| Modelo 303/347/349/390 | `scripts/run_aeat_report.py --model 303 --period 2026Q1` | `references/reports.md` |
| Lectura conversacional ad-hoc | Usa MCP server `odoo` si esta configurado, o `scripts/odoo_client.py` | `references/domain-syntax.md` |

## Checklist de cumplimiento espanol antes de `action_post`

Ejecuta `scripts/verify_es_compliance.py --invoice-id <id>` o, si validas a
mano, comprueba:

- [ ] `partner_id.vat` en formato espanol valido (`ES` + DNI/NIF/CIF/NIE,
      con digito de control correcto). Si es intra-UE: VIES vivo.
- [ ] `partner_id.country_id` y `partner_id.lang` (`es_ES` o `ca_ES`).
- [ ] `fiscal_position_id` adecuada: nacional, intra-UE, exportacion,
      Recargo de Equivalencia, IVA de Caja, REAGYP, ISP.
- [ ] Cada `invoice_line_ids` con `tax_ids` y `type_tax_use='sale'` (o
      `purchase` para `in_invoice`). Codigos tipicos: `S_IVA21B`,
      `S_IVA10B`, `S_IVA4B`, `S_IVA0_E`, `P_IRPF15`.
- [ ] `journal_id.type='sale'` (o `purchase`).
- [ ] Si Veri*Factu activo: `journal_id` habilitado y certificado AEAT
      configurado (Settings > Veri*Factu > Manage certificates).
- [ ] `invoice_date` no cae en periodo bloqueado (`fiscalyear_lock_date`,
      `tax_lock_date`).
- [ ] Numeracion del diario sin huecos (Veri*Factu lo exige).

Si algo falla: **no postear**, devolver al usuario la lista de
incumplimientos y proponer remediacion concreta.

## Patrones de manejo de errores Odoo

Las llamadas RPC pueden devolver:

| Excepcion | Causa tipica | Accion del skill |
|-----------|--------------|------------------|
| `UserError` | Validacion de negocio (cuenta no configurada, asiento desbalanceado) | Mostrar el `faultString` al usuario y proponer correccion |
| `ValidationError` | Restriccion del modelo | Igual que `UserError` |
| `AccessError` | Permisos insuficientes del usuario bot | Pedir al admin que revise `ir.model.access.csv` o reglas de registro |
| `MissingError` | ID inexistente o eliminado | Reintentar busqueda; si no aparece, abortar |
| `xmlrpc.client.Fault` o `requests.HTTPError` 5xx | Caida de Odoo / red | Reintento con backoff exponencial (max 3 intentos) |

Los scripts del skill envuelven estos errores en `OdooError` (ver
`scripts/_common.py`) con el mensaje de negocio pelado. Nunca silencies un
`UserError`: significa que Odoo ha rechazado la operacion por una razon
contable concreta.

## Reglas de parada (siempre pedir confirmacion al usuario)

1. **Importes > 1.000 EUR** sin diario o terminos de pago especificados.
2. **Facturas con fecha en periodo bloqueado** (`fiscalyear_lock_date`,
   `tax_lock_date`, `purchase_lock_date`, `sale_lock_date`): rechazar y
   explicar.
3. **Veri*Factu activo sin certificado configurado**: rechazar y enlazar
   a `references/sii-verifactu-facturae.md`.
4. **Borrar (`unlink`) o anular (`button_cancel`)** un `account.move` ya
   posteado: pedir confirmacion explicita; preferir `account.move.reversal`.
5. **Cualquier escritura sobre asientos del periodo cerrado del IVA**: nunca
   sin confirmacion.

## Flujo recomendado de uso

1. **Lectura primero**: si el usuario hace una pregunta abierta, prefiere
   el MCP server `odoo` (si esta configurado, tools `mcp__odoo__*`) o
   `scripts/odoo_client.py` para `search_read`.
2. **Validar antes de escribir**: `verify_es_compliance.py` sobre el
   borrador o sobre el partner.
3. **Crear/actualizar idempotente**: los scripts buscan por `ref` +
   `partner_id` antes de crear; reutiliza el mismo `ref` para reintentos
   seguros.
4. **Postear**: con `action_post` (incluido en `create_invoice.py --post`).
5. **EDI asincrono**: SII y Veri*Factu se envian via cron en Odoo. Para
   forzar entrega inmediata usa `send_sii.py` o `send_verifactu.py`.
6. **Tras postear**: si Veri*Factu/SII falla, leer
   `references/sii-verifactu-facturae.md` para errores `[1103]`, `[3000]`
   y otros codigos AEAT.

## Punteros a las references (carga bajo demanda)

- `references/modelos-cheatsheet.md` - todos los modelos relevantes con
  campos, estados y metodos.
- `references/workflows.md` - recetas paso a paso (factura, pago, abono,
  conciliacion, multi-divisa, lock dates).
- `references/localizacion-espana.md` - PGCE, IVA, IRPF, RE, posiciones
  fiscales, validacion NIF/CIF/NIE, VIES.
- `references/sii-verifactu-facturae.md` - los tres regimenes EDI, modulos
  Enterprise vs OCA, certificados, errores AEAT comunes.
- `references/reports.md` - motor `account.report`, modelos AEAT, exportes
  BOE, generacion PDF.
- `references/domain-syntax.md` - dominios Odoo, operadores,
  `read_group`, paginacion, optimistic locking.

## Assets

- `assets/invoice_template.json` - payload minimo de ejemplo.
- `assets/tax_codes_es.csv` - mapa codigo AEAT <-> XML-ID Odoo `l10n_es`.
- `assets/modelos_aeat.csv` - casillas oficiales por modelo.

## Evals

`evals/evals.json` contiene 20 prompts (14 should-trigger + 6
should-not-trigger) para validar disparo correcto del skill. Ejecutar tras
cualquier cambio en la `description` del frontmatter.
