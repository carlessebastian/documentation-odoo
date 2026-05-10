# docs/

Notas propias del proyecto. **No** son la documentación de Odoo upstream
(esa vive en `vendor/odoo-docs/`); aquí se recoge contexto que el agente
necesita y que no es derivable del código.

Estructura:

- `onboarding.md` — playbook de primer arranque del agente.
- `infra/` — runbooks de la infraestructura: doodba, despliegue,
  backups, secretos, hosts. Compartidos entre tenants.
- `tenants/<slug>/` — un perfil por despliegue. Cada tenant tiene su
  propio `profile.yaml` (NIF, plan contable, diarios, posiciones
  fiscales, módulos esperados) y notas específicas. La sesión activa
  se selecciona con `ODOO_AGENT_TENANT=<slug>` en `.env`. Ver
  `tenants/README.md` y `tenants/_template/`.
- `decisions/` — ADRs cortos para decisiones que afectan al agente
  (qué módulos OCA preferir, qué stack de EDI, etc.).

Convenciones:

- Todo en Markdown, archivos cortos, un tema por archivo.
- Si un dato es sensible (API keys, VATs reales, contraseñas), va en
  `.env` o en un gestor de secretos, **nunca** en este directorio.
- Si una nota se vuelve estable y operativa, considera moverla al
  `references/` del skill correspondiente en `.claude/skills/`.
