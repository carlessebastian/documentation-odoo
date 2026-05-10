# Migración Holded → Odoo 19 — inpr3mium

**Estado: pendiente de diseño.** Este archivo se completa en Fase 5
del plan, una vez la instancia Odoo esté arrancada y bootstrappeada
(Fases 3-4). Aquí van las decisiones y el plan ETL.

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

## Scope (a decidir con el usuario)

Tres niveles. Recomendación inicial: **mínimo**.

- [ ] **Mínimo**: maestros (partners, productos) + plan contable
      ajustado + saldos de apertura del cutover. Operativa nueva en
      Odoo desde día 1.
- [ ] **Año en curso**: lo anterior + facturas y pagos del ejercicio
      en curso, para tener libros completos en Odoo. Más trabajo;
      útil si el cutover no es a 1 de enero.
- [ ] **Histórico completo**: lo anterior + ejercicios cerrados
      anteriores. Generalmente no se recomienda — los ejercicios
      cerrados quedan en Holded (read-only) durante el periodo legal
      de conservación.

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

1. **Export Holded** — usar la API REST, paginando, persistir en JSON
   plano en `docs/tenants/inpr3mium/migrations/<YYYY-MM-DD>/`.
2. **Transformación** — script Python que lee el JSON, normaliza VATs
   (formato `ES...`), deduplica, mapea cuentas e impuestos, y escribe
   un dataset listo para Odoo.
3. **Carga en Odoo** — vía JSON-2 / `ext_id_upsert.py` (idempotente),
   un modelo a la vez en orden de dependencias: partners → productos →
   plan contable → asientos de apertura → (opcional) facturas
   históricas.
4. **Validación** — conteo, cuadre de balance, spot-check con un
   partner real, primer cierre mensual.

Si el ETL crece más allá de un par de scripts, considerar abrir un
cuarto skill `odoo-data-migration`. Decisión diferida al momento.

## Cutover

- Fecha objetivo: **`<TODO>`** (idealmente fin de mes o trimestre).
- Pasos del día D — a detallar.

## Riesgos

- API de Holded con rate limits o paginación inestable.
- Plan contable de Holded no mapeable 1:1 con el `l10n_es` elegido.
- IVA y cuotas redondeadas distinto entre los dos sistemas → cuadres
  céntimo arriba/abajo.
- IRPF retenido en facturas: revisar mapeo de cuentas.

## Cuestiones abiertas

- ¿Carles tiene Holded en plan API o necesita exportar manualmente?
- ¿Cuántos contactos / productos / facturas/año hay aproximadamente?
- ¿Hay módulos de Holded usados que no tengan equivalente directo en
  Odoo (p.ej. CRM con campos custom, proyectos, RRHH)?
