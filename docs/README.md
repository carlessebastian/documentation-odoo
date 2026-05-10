# docs/

Notas propias del proyecto. **No** son la documentación de Odoo upstream
(esa vive en `vendor/odoo-docs/`); aquí se recoge contexto que el agente
necesita y que no es derivable del código.

Estructura prevista (se crea bajo demanda):

- `infra/` — runbooks de la infraestructura: doodba, despliegue, backups,
  variables de entorno, claves SSH/API, hosts.
- `ikigai/` — contexto de las empresas (holding **Ikigai Magi S.L.** y
  filiales **Camomilla Blu**, **Kura Terra**, **Omotenashi Hama**): VATs,
  diarios, posiciones fiscales, particularidades fiscales por sociedad.
- `migration/` — plan y bitácora de la migración del sistema actual a
  Odoo 19.
- `decisions/` — ADRs cortos para decisiones que afectan al agente
  (qué módulos OCA preferir, qué stack de EDI, etc.).

Convenciones:

- Todo en Markdown, archivos cortos, un tema por archivo.
- Si un dato es sensible (API keys, VATs reales, contraseñas), va en
  `.env` o en un gestor de secretos, **nunca** en este directorio.
- Si una nota se vuelve estable y operativa, considera moverla al
  `references/` del skill correspondiente en `.claude/skills/`.
