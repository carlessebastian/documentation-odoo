# docs/infra/

Runbooks y notas de la infraestructura que el agente necesita pero
**no provisiona** (las skills `odoo-module-admin` operan vía SSH +
docker exec sobre una instancia ya existente).

## Contenido

- [`doodba-bootstrap.md`](doodba-bootstrap.md) — provisión del entorno
  doodba en dos modos: **local Docker** (tests, desarrollo) y
  **gcloud** (producción futura). Versión teórica original.
- [`local-deployment-guide.md`](local-deployment-guide.md) — **guía
  corregida y probada** para Modo A (Docker local). Reemplaza la
  sección Modo A de `doodba-bootstrap.md` cuando haya divergencia.
  Incorpora las 10 correcciones descubiertas durante el primer
  despliegue real (`inpr3mium-local`, 2026-05-10): copier
  no-interactivo, `.empty` bug en macOS, creación de DB vía CLI,
  cambios de modelo en Odoo 19, etc.
- [`secrets.md`](secrets.md) — política de gestión de secretos
  (API keys, contraseñas, certificados digitales). Qué va en `.env`,
  qué no se versiona, dónde se almacena la copia maestra.
- [`scaling.md`](scaling.md) — buenas prácticas de escalado de Odoo 19
  (workers, gevent, cron dedicado, Nginx + X-Sendfile, PostgreSQL,
  filestore externo, multi-nodo, OCA `queue_job`, monitorización).
  Agnóstica al tenant: referencia para dimensionar `fedefarma` y
  cualquier despliegue futuro que crezca en carga.

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
