---
name: odoo-accounting-es
description: |
  Usa este skill SOLO para operativa contable y fiscal espanola en Odoo 19
  Community self-hosted (Cataluna/UE): crear facturas
  (account.move out_invoice/in_invoice), postearlas (action_post),
  registrar pagos (account.payment.register), generar rectificativas
  (account.move.reversal), conciliar extractos, calcular IVA 21/10/4/0,
  IRPF y Recargo de Equivalencia, enviar SII / Veri*Factu / FacturaE,
  ejecutar modelos AEAT 303/347/349/390/111/115/130/369/232/720,
  cierres periodicos, reporting financiero. Activa aunque el usuario solo
  diga "factura", "asiento", "modelo 303", "AEAT", "SII", "Verifactu",
  "FACe", "PGCE", "balance", "P&L", "create invoice", "post invoice".

  DO NOT trigger for (handoff to sibling skills):
    - User / group / ACL / record-rule / multi-company configuration
      -> use skill `odoo-functional-admin`.
    - Journal / sequence / fiscal-position / tax-code creation as setup
      (vs daily use) -> use skill `odoo-functional-admin`.
    - Scheduled action (ir.cron) configuration -> `odoo-functional-admin`.
    - Module install / upgrade / uninstall, addons.yaml, repos.yaml,
      git-aggregator, doodba/Docker operations, odoo-bin -i/-u, restarting
      the Odoo container, pip dependencies of an addon
      -> use skill `odoo-module-admin`.

  No usar para tareas no-Odoo (frontend, devops generico, traducciones,
  matematicas, trivia).
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
| **Operativa diaria** | | |
| Crear factura cliente | `scripts/create_invoice.py` | `references/workflows.md`, `references/localizacion-espana.md` |
| Crear factura proveedor | `scripts/create_invoice.py --type in_invoice` | `references/workflows.md` |
| Postear factura | (incluido en `create_invoice.py --post`) o `scripts/odoo_client.py` accion `action_post` | `references/workflows.md` |
| Registrar cobro/pago | `scripts/register_payment.py` | `references/workflows.md` |
| Crear factura rectificativa | `scripts/credit_note.py --mode reverse\|modify` | `references/workflows.md` |
| Buscar cliente/proveedor | `scripts/partner_lookup.py` | `references/domain-syntax.md` |
| Asignar posicion fiscal / payment term en bulk a partners | `scripts/partner_fiscal_setup.py --criteria eu_with_vat\|non_eu_with_vat\|spain_only\|match_partner_ids --fiscal-position N --company N --confirm` | `references/localizacion-espana.md` |
| Buscar producto | `scripts/product_lookup.py` | `references/modelos-cheatsheet.md` |
| Buscar/listar impuestos | `scripts/tax_lookup.py` | `references/localizacion-espana.md` |
| Verificar cumplimiento ES | `scripts/verify_es_compliance.py` | `references/localizacion-espana.md`, `references/sii-verifactu-facturae.md` |
| **Tesoreria** | | |
| Aged receivables/payables | `scripts/aged_balance.py --type receivable\|payable` | `references/treasury.md` |
| Importar extracto bancario | `scripts/bank_statement_import.py --file ext.csv --journal-id N` | `references/treasury.md` |
| Conciliar extracto bancario | `scripts/bank_statement_reconcile.py --statement-id N` | `references/treasury.md` |
| Recordatorios de cobro (dunning) | `scripts/dunning.py --level 1\|2\|3` | `references/treasury.md` |
| KPIs tesoreria (DSO/DPO/CCC) | `scripts/dashboard_kpis.py --from YYYY-MM-DD --to YYYY-MM-DD` | `references/treasury.md` |
| **Volumen y automatizacion** | | |
| Importar facturas masivas CSV/Excel | `scripts/bulk_invoice_import.py --file ventas.csv` | `references/automation.md` |
| Generar factura recurrente | `scripts/recurring_invoice.py --template-id N --frequency monthly` | `references/automation.md` |
| Operacion en lote (post/payment/cancel/send) | `scripts/batch_operations.py --action post --domain '...'` | `references/automation.md` |
| **Cumplimiento ES extendido** | | |
| Libro IVA emitido/recibido | `scripts/vat_book.py --period 2026Q1` | `references/iva-extendido.md` |
| Calcular prorrata IVA | `scripts/vat_prorate.py --year 2026 --provisional 85` | `references/iva-extendido.md` |
| Modelos AEAT | `scripts/run_aeat_report.py --model 303\|369\|232\|720 --period ...` | `references/reports.md`, `references/iva-extendido.md` |
| **Cierre y reporting financiero** | | |
| Checklist pre-cierre periodico | `scripts/period_close_checklist.py --from ... --to ...` | `references/cierre-periodico.md` |
| Asiento de cierre 6/7 -> 129 | `scripts/closing_entries.py --year 2026 --dry-run` | `references/cierre-periodico.md` |
| P&L / Balance / Trial balance multi-periodo | `scripts/financial_reports.py --report pl\|balance\|trial` | `references/cierre-periodico.md` |
| **EDI AEAT** | | |
| Enviar a SII | `scripts/send_sii.py` | `references/sii-verifactu-facturae.md` |
| Enviar a Veri*Factu | `scripts/send_verifactu.py` | `references/sii-verifactu-facturae.md` |
| Generar PDF de factura | `scripts/report_invoice_pdf.py` | `references/reports.md` |
| **Multi-divisa** | | |
| Actualizar tipos de cambio ECB | `scripts/update_exchange_rates.py --scope daily` | `references/workflows.md` |
| **Lectura ad-hoc** | | |
| Lectura conversacional | Usa MCP server `odoo` si esta configurado, o `scripts/odoo_client.py` | `references/domain-syntax.md`, `references/mcp-setup.md` |

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
- `references/treasury.md` - aged receivables/payables, conciliacion
  bancaria (CAMT/OFX/CSV/N43), dunning, KPIs (DSO/DPO/CCC).
- `references/automation.md` - importacion masiva, recurrencia, bulk
  operations, idempotencia en lotes, performance.
- `references/iva-extendido.md` - libros IVA, prorrata, regularizacion
  bienes inversion, modelos 369/232/720.
- `references/cierre-periodico.md` - checklist mensual/trimestral/anual,
  asientos cierre/apertura, lock dates, distribucion de resultados.
- `references/mcp-setup.md` - como configurar un MCP server Odoo
  (`ivnvxd/mcp-server-odoo`) para usar el skill desde Claude Code o
  Claude Desktop, variables de entorno compartidas, permisos.

## Skills hermanos (handoff)

Si la peticion del usuario cae fuera del alcance contable/fiscal, delega al
skill hermano correspondiente; no intentes cubrirlo aqui.

| Si el usuario pide... | Usa el skill |
|-----------------------|--------------|
| Crear/modificar usuarios, grupos, ACLs, reglas de registro | `odoo-functional-admin` |
| Configurar diarios, secuencias, posiciones fiscales como *setup* | `odoo-functional-admin` |
| Configurar multi-company (holding y filiales) | `odoo-functional-admin` |
| Activar/desactivar `ir.cron` | `odoo-functional-admin` |
| Instalar / actualizar / desinstalar modulos | `odoo-module-admin` |
| Tocar `addons.yaml`, `repos.yaml`, git-aggregator, doodba | `odoo-module-admin` |
| Reiniciar el contenedor Odoo, ejecutar `odoo-bin -i/-u` | `odoo-module-admin` |
| Diagnosticar dependencias pip de un addon | `odoo-module-admin` |

La distincion clave: este skill *opera* facturas/asientos/cobros sobre una
configuracion ya instalada. Si el usuario quiere *configurar* la base
(usuarios, diarios, modulos), no es trabajo de este skill.

## Calidad y tests

El skill incluye una suite pytest en `tests/` que cubre las funciones
puras (validacion NIF/CIF/NIE, parsers de periodos, helpers). Ejecutar:

```bash
cd .claude/skills/odoo-accounting-es
python3 -m pytest tests/ -v
```

No requiere conexion Odoo ni `requests` (los modulos del skill importan
`requests` de forma diferida solo cuando se hacen llamadas RPC reales).
Ver `tests/README.md` para detalles de cobertura.

## Assets

- `assets/invoice_template.json` - payload minimo de ejemplo.
- `assets/tax_codes_es.csv` - mapa codigo AEAT <-> XML-ID Odoo `l10n_es`.
- `assets/modelos_aeat.csv` - casillas oficiales por modelo.

## Evals

`evals/evals.json` contiene 20 prompts (14 should-trigger + 6
should-not-trigger) para validar disparo correcto del skill. Ejecutar tras
cualquier cambio en la `description` del frontmatter.
