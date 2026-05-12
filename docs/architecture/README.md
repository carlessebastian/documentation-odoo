# docs/architecture/

Mapas estructurales propios del agente sobre cómo funciona Odoo 19
por dentro. **No es documentación de Odoo para humanos** — es la
mental map que el agente carga *selectivamente* cuando una tarea
requiere razonar sobre la arquitectura interna (ORM, security,
RPC, accounting...) más allá de lo que cubren las skills
operacionales.

## Cuándo se carga

El agente **no** carga esta carpeta al inicio de cada sesión. Solo
cuando una tarea operativa va a tocar un área y necesita el modelo
mental completo. Punto de entrada: [`00-index.md`](00-index.md)
(grafo de capas + tabla de estado + tabla de triggers de carga).

Ejemplos:

- "voy a crear miles de `account.move` por RPC" → carga `6-accounting.md`.
- "el bot no ve los registros que debería" → cargará `3-security.md`.
- "`_json2` 422 / sesión expirada" → cargará `4-web-rpc.md`.

## Cómo se construye una capa nueva

Protocolo de 4 pasos (detalle en el plan
`~/.claude/plans/vamos-a-crear-una-cosmic-spark.md`):

1. **Encuadre** — pregunta operativa + decisiones del agente que
   dependen + capas vecinas.
2. **Cobertura desde `vendor/odoo-docs/`** — referencias canónicas
   (paths, sin copiar contenido).
3. **Fuente adicional** — agent memory → código fuente
   (`../odoo-19-source/`, pedir clone al operador) → internet
   (último recurso).
4. **Escritura** — usar [`_template.md`](_template.md).

Restricciones:

- **≤ 200 líneas** por archivo (es contexto de carga, no manual).
- **Mermaid embebido** en bloque ` ```mermaid` (renderiza en GitHub).
- **Cero duplicación**: si un concepto vive en `vendor/odoo-docs/`
  o en agent memory, **linkear, no copiar**.
- **No documentar el código del agente** — eso es trabajo de cada
  `SKILL.md`. Aquí solo se documenta Odoo.

## Relación con otras fuentes

| Fuente | Rol |
|---|---|
| `vendor/odoo-docs/` | Doc oficial de Odoo. Material denso de referencia. Esta carpeta linkea ahí. |
| `~/.claude/projects/.../memory/` | Gotchas, patrones, feedback del operador. Esta carpeta linkea ahí. |
| `.claude/skills/*/SKILL.md` | Operativa (*cómo* hacer X). Esta carpeta es estructural (*qué pasa por dentro* cuando haces X). |
| `docs/PLAN.md` | Estado de la migración del tenant activo. **No** trackea las capas de arquitectura. |

## Estado de las capas: vive en `00-index.md`, no en `PLAN.md`

`docs/PLAN.md` es fuente de verdad del **roadmap de migración**
(Fase 5.0, 5.1, ...). El estado de las capas de arquitectura
(qué existe, en qué grado de madurez) vive exclusivamente en
[`00-index.md`](00-index.md). Esto evita mezclar dos planos:
preguntas como "¿cómo voy de la migración?" se responden con
`PLAN.md`; "¿qué capas hemos documentado?" con `00-index.md`.

Cuando una capa se construye o avanza, se anota en `PLAN.md`
como **side-note de una línea** ("*+ side-asset: capa N draft,
ver `00-index.md`*"), nunca como entrada del roadmap.

## ¿Hace falta una skill `odoo-architecture`?

Hoy **no**. Las 4 skills operativas existentes
(`odoo-accounting-es`, `odoo-functional-admin`,
`odoo-module-admin`, `holded-export`) apuntan a la capa
relevante desde su propio `SKILL.md`. Crear una skill solo si
descubrimos que el agente sistemáticamente no consulta estas
capas cuando debería (señal: errores que la doc habría
prevenido). Revisar tras 2-3 capas reales construidas.
