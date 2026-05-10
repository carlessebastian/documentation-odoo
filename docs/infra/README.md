# docs/infra/

Runbooks y notas de la infraestructura que el agente necesita pero
**no provisiona** (las skills `odoo-module-admin` operan vía SSH +
docker exec sobre una instancia ya existente).

## Contenido

- [`doodba-bootstrap.md`](doodba-bootstrap.md) — provisión del entorno
  doodba en dos modos: **local Docker** (tests, desarrollo) y
  **gcloud** (producción futura).
- [`secrets.md`](secrets.md) — política de gestión de secretos
  (API keys, contraseñas, certificados digitales). Qué va en `.env`,
  qué no se versiona, dónde se almacena la copia maestra.

## Convención

Estos runbooks son **read-only** para el agente. El usuario los
ejecuta manualmente o asistido por el agente con confirmación paso a
paso. Las skills no modifican estos archivos automáticamente.

Cuando se haga un provisioning real, dejar **bitácora** en el tenant
correspondiente:
- `docs/tenants/<slug>/bootstrap-log.md` — fecha, comandos
  ejecutados, incidencias.

Así, en sesiones futuras el agente puede leer la bitácora y conocer
el estado real (vs. el teórico del runbook).
