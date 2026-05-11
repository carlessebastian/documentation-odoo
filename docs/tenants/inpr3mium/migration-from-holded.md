# Migración Holded → Odoo 19 — inpr3mium

**Estado: pre-diseño.** Estructura general decidida; el detalle ETL
y el cutover se concretan en Fase 5 del plan, una vez la instancia
Odoo esté arrancada y bootstrappeada (Fases 3-4).

## Contexto del origen (datos del análisis)

- **Holded URL**: https://farmapremium.holded.com (plan con API).
- **Volumen del cuadro de cuentas (export 2025)**: 333 cuentas
  activas, 70 prefijos de 4 dígitos. PGCE Pymes con analítica
  extendida por Holded (códigos de 11 dígitos: 4 base + 7 analítica).
- **Particularidades fiscales** (relevantes para mapeo):
  - Cuentas IRPF retenido (`4751*` x5): retenciones a profesionales,
    arrendamientos, retribución especie, vehículo.
  - Cuentas servicios profesionales recibidos (`62300710*` x12):
    asesoría laboral, contable, fiscal, secretaría consejo,
    protección datos, prevención riesgos, etc.
  - Cuentas IVA repercutido/soportado por % (`4720`, `4770`).
  - Capital social tripartito: FEDERACIO FARMACEUTICA, BIDAFARMA,
    CRUZFARMA. Préstamo de FEDEFARMA → cuenta `66231400002`.
  - Compras de packs (`60000400*`) y producción PLV (`6230074*`,
    `6240074*`).

## Origen: Holded

[Holded](https://www.holded.com/) es un SaaS español de gestión
empresarial (contabilidad, facturación, CRM, ERP ligero). Expone una
API REST documentada en <https://developers.holded.com/>.

Recursos relevantes para el ETL:

- **Contacts** (clientes y proveedores) → `res.partner`.
- **Products** → `product.product` / `product.template`.
- **Documents** (facturas emitidas, recibidas, presupuestos, albaranes)
  → `account.move` (`out_invoice`, `in_invoice`).
- **Payments / Treasury** → `account.payment`.
- **Accounts** (plan contable Holded) → mapeo a `account.account` del
  PGCE elegido en Odoo.
- **Taxes** → mapeo a impuestos `account.tax` de `l10n_es`.

## Scope (decidido)

**Histórico completo + año en curso**, con validación previa por
subset.

- [x] **Subset de validación**: ejercicios **2024 y 2025** completos.
      Estos dos años son los que se migran primero como prueba para
      verificar que el ETL produce balances cuadrados, partners
      coherentes y facturación correcta antes de cargar el resto.
- [ ] **Histórico completo**: tras validación OK, migrar todos los
      ejercicios anteriores disponibles en Holded.
- [ ] **Año en curso**: tras OK del histórico, traer el ejercicio
      activo hasta el día del cutover.

Justificación: el negocio tiene partes vinculadas (capital social
participado) y modelo 232; tener histórico contable completo en
Odoo facilita auditoría y reporting consolidado futuro con las
sociedades hermanas.

## Mapeo de modelos (borrador)

| Holded | Odoo | Mapeo / notas |
|--------|------|---------------|
| Contact (`type=client`) | `res.partner` con `customer_rank > 0` | Mapear `vat`, `email`, `phone`, dirección. Holded a veces mezcla persona/empresa: deduplicar por VAT. |
| Contact (`type=supplier`) | `res.partner` con `supplier_rank > 0` | Idem. Si un VAT es ambos, un solo partner con ambos ranks. |
| Product | `product.template` + `product.product` | Mapear `default_code`, `list_price`, `taxes_id` (al impuesto `l10n_es` correspondiente). |
| Invoice (cliente) | `account.move` (`out_invoice`) | `invoice_date`, `partner_id`, líneas → `account.move.line`. Estado: postear posteriormente, no en el create. |
| Bill (proveedor) | `account.move` (`in_invoice`) | Idem. |
| Payment | `account.payment` | Conciliación con la factura correspondiente. |
| Cuenta contable Holded | `account.account` | Mapear a PGCE español. |

## ETL — pasos previstos

1. **Export Holded** — usar la skill `holded-export` (read-only):

   ```bash
   # Preflight: cuantos contactos / docs / asientos hay
   python3 .claude/skills/holded-export/scripts/holded_inspect.py

   # Dump completo (todos los resources + PDFs originales escaneados)
   python3 .claude/skills/holded-export/scripts/holded_export.py \
     --output-dir docs/tenants/inpr3mium/holded-export/$(date +%F) \
     --include-pdfs

   # Validar manifest + counts
   python3 .claude/skills/holded-export/scripts/dump_summary.py \
     --dir docs/tenants/inpr3mium/holded-export/$(date +%F)
   ```

   Output: directorio `docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>/`
   con JSONL por resource, `numbering_series.json`, `contact_groups.json`,
   `manifest.json`, `errors.jsonl` y `pdfs/{invoice,purchase}/<id>.pdf`.
   El directorio está **gitignored** (datos personales/financieros).

2. **Transformación** — script Python que lee los JSONL, normaliza VATs
   (formato `ES...`), deduplica, mapea cuentas e impuestos, y escribe
   un dataset listo para Odoo.

3. **Carga en Odoo** — vía JSON-2 / `ext_id_upsert.py` (idempotente),
   un modelo a la vez en orden de dependencias: partners → productos →
   plan contable → asientos de apertura → (opcional) facturas
   históricas. Por hacer: posible 5ª skill `holded-to-odoo` si se
   complica.

4. **Validación** — conteo, cuadre de balance, spot-check con un
   partner real, primer cierre mensual.

La skill `holded-export` cubre el **lado lectura** de Fase 4.2.1 y
deja Fase 5 con el material listo para transformar. Solo emite GETs;
no puede modificar nada en la cuenta Holded.

## Cutover

- Fecha objetivo: **sin fecha fija**. Se decidirá cuando el agente
  esté maduro y la migración del subset 2024+2025 esté validada.
- Pasos del día D — a detallar tras validación.

## Particularidades a resolver durante el ETL

- **Códigos de cuenta de 11 dígitos en Holded** vs 4-8 dígitos en
  Odoo PGCE Pymes. Decidir: ¿colapsar al prefijo de 4-8 (perdiendo
  granularidad analítica) o crear `account.analytic.account` para
  preservar el desglose? Recomendación inicial: colapsar a `account.account`
  PGCE Pymes y mover la granularidad a tags analíticas vía
  `account.analytic.tag` (modelo `account.analytic.distribution`).
- **Capital social tripartito** (3 cuentas `100*`): preservar el
  desglose por socio como analítica o como cuentas separadas dentro
  del 100. Probable preservar.
- **Préstamo FEDEFARMA**: mapear a cuenta de pasivo a corto/largo
  plazo según vencimiento.
- **IRPF retenido**: las 5 cuentas `4751*` deben mapear a las cuentas
  estándar `4751` del PGCE Pymes con conceptos analíticos. Revisar
  con el módulo `l10n_es_aeat_mod111`.
- **Servicios extracomunitarios USA**: durante la migración del
  histórico, las facturas de proveedores USA deben llevar la posición
  fiscal "Servicios Extra-UE" para que el IVA se autoliquide
  correctamente en el 303.

## Riesgos

- API de Holded con rate limits o paginación inestable.
- Plan contable de Holded (con códigos de 11 dígitos) no mapeable 1:1
  con `l10n_es_pymes`. Decisión de granularidad analítica pendiente.
- IVA y cuotas redondeadas distinto entre los dos sistemas → cuadres
  céntimo arriba/abajo en saldos de apertura.
- IRPF retenido: 5 cuentas distintas en Holded → ¿mantener desglose o
  colapsar?

## Cuestiones abiertas (para resolver en Fase 5)

- ¿Cuántos contactos / productos / facturas/año hay aproximadamente?
  (orientativo para diseñar batch size del ETL).
- ¿Plan de Holded incluye API access? Confirmar antes de codificar.
- ¿Hay módulos de Holded usados que no tengan equivalente directo en
  Odoo (CRM con campos custom, proyectos, RRHH)?
- ¿Mantener Holded en read-only post-cutover durante el periodo legal
  de conservación, o exportar todo y dar de baja?
