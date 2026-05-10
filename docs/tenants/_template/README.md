# Tenant: `<slug>`

Plantilla de tenant. Copia este directorio a `docs/tenants/<slug>/` y
sustituye los archivos `*.example` por sus versiones reales:

```bash
TENANT=miempresa
cp -r docs/tenants/_template docs/tenants/$TENANT
mv docs/tenants/$TENANT/profile.yaml.example \
   docs/tenants/$TENANT/profile.yaml
mv docs/tenants/$TENANT/migration-plan.md.example \
   docs/tenants/$TENANT/migration-plan.md
```

Después rellena `profile.yaml` con los datos reales del cliente y
ajusta `migration-plan.md` según el origen (Odoo, Holded, otro ERP, o
greenfield sin migración).

## Mínimo viable de un tenant

- `profile.yaml` con `slug`, `legal_name`, `vat`, `chart_template`,
  `edi_stack`, `companies`, `expected_modules`. Sin esto, `/onboard` no
  puede validar el estado de la instancia.
- `migration-plan.md` (o un nombre más específico tipo
  `migration-from-holded.md`, `migration-from-axional.md`) describiendo
  qué se importa y cómo. Si es greenfield, basta con una línea.
- `README.md` (este archivo) describiendo brevemente quién es el cliente
  y particularidades fiscales relevantes (RE, IVA Caja, intracom UE,
  exportación, etc.).

## Notas operativas

A medida que se opere con el tenant, añadir aquí archivos cortos:

- `bootstrap-log.md` — bitácora de la instalación inicial (fechas,
  módulos instalados, incidencias).
- `edi-setup.md` — pasos manuales que se hicieron para SII /
  Veri\*Factu / FacturaE (cargar certificado, etc.).
- `cierres/YYYY-MM.md` — bitácora de cada cierre mensual.
- Cualquier otra cosa del tenant que el agente vaya a necesitar
  recordar entre sesiones.
