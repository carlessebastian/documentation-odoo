# Plan de desarrollo — odoo-agent

Roadmap canónico del proyecto. **Single source of truth para el estado
de la implementación.** Permite pausar y retomar sesiones sin perder
contexto entre conversaciones de Claude Code.

> **Convención de actualización**: tras completar cada paso, actualizar:
> - Sello "Última actualización" (sección **Estado actual**)
> - "Última fase completada" + "Próximo paso"
> - Marcar `[x]` en el bloque correspondiente
> - Añadir una línea al **Histórico de cambios** al final
>
> El agente debe leer este archivo al inicio de cada sesión que toque el
> proyecto. La regla está reforzada en memoria.

---

## Estado actual

- **Última actualización**: 2026-05-10
- **Última fase completada**: Fase 3 — runbook
  `docs/infra/doodba-bootstrap.md` redactado en dos modos: **Modo A
  (Docker local)** completo con pasos detallados para arranque
  inmediato; **Modo B (gcloud Compute Engine)** como referencia para
  producción futura. Añadidos `docs/infra/README.md` y
  `docs/infra/secrets.md` (política de gestión de secretos).
- **Próximo paso**: **Bloque B paso 8** — el **usuario** ejecuta el
  Modo A del runbook contra Docker local (provisionar doodba, crear
  DB `inpr3mium_dev`, crear bot user + API key). Tarea manual, sin
  intervención del agente. Cuando termine, pasos 9-10 (configurar
  `.env` + ejecutar `/onboard` para validar conectividad).
- **Tenant activo**: `inpr3mium` (Inteligencia del negocio pr3mium S.L.
  / farmapremium). La instancia Odoo 19 todavía no existe.

---

## Contexto

El agente nació como fork de `odoo/documentation` 19.0; se reestructuró
y se convirtió en un agente Claude Code multi-tenant para administrar
instancias self-hosted Odoo 19 Community con doodba. El primer cliente
real es `inpr3mium`, que migra desde Holded. Cliente futuro previsto:
`fedefarma` (migra desde Axional). Las skills son agnósticas al
tenant; los datos por cliente viven en `docs/tenants/<slug>/`.

Plan original con todo el detalle:
`~/.claude/plans/bien-ahora-planifiquemos-cuales-snazzy-duckling.md`
(referencia histórica; este archivo es la versión vigente).

---

## Fases del proyecto

### Fase 1 — Limpieza + arquitectura multi-tenant *(prerrequisito)*

**Objetivo**: el agente deja de mencionar empresas ficticias y aprende
a leer un perfil de tenant desde disco vía `ODOO_AGENT_TENANT`.

- ✅ **1.1** Auditar y eliminar referencias a empresas ficticias
  (24 archivos: skills, references, evals, tests, scripts, assets,
  memoria). Sustituidas por placeholders `<TENANT_NAME>` /
  `<TENANT_VAT>` en runbooks y por "Acme Holdings/Iberia/Foods S.L."
  en ejemplos narrativos. Renombrado
  `ikigai_company_tree.json` → `company_tree.example.json`.
- ✅ **1.2** Estructura `docs/tenants/{README.md, _template/, inpr3mium/}`
  con schema completo de `profile.yaml` (legal_name, NIF, plan
  contable, EDI stack, flags fiscales, companies, expected_modules,
  source_system, migration). Activación vía env var
  `ODOO_AGENT_TENANT`.

### Fase 2 — Onboarding del agente *(prioridad declarada por usuario)*

**Objetivo**: con `.env` lleno y `profile.yaml` definido, en un solo
comando el agente confirma que puede operar contra el Odoo real.

- ✅ **2.1** `.env.example` en raíz con todas las env vars agrupadas
  y comentadas.
- ✅ **2.2** `docs/onboarding.md` con playbook de primer arranque
  (6 pasos: bot user, configurar tenant, llenar `.env`, lanzar
  `/onboard`, resolver rojos, empezar a operar).
- ✅ **2.3** Slash-command `/onboard` en `.claude/commands/onboard.md`
  con 10 checks no destructivos (profile leído, env RPC, RPC reachable,
  API key, bot ≠ admin, grupos, empresa, módulos esperados, SSH a
  doodba, tests offline).

### Fase 3 — Provisión doodba *(manual, dentro de `docs/infra/`)*

**Objetivo**: documentar el provisioning del entorno (fuera del scope
ejecutable del agente, pero el agente lo necesita).

- ✅ **3** `docs/infra/{README.md, doodba-bootstrap.md, secrets.md}`
  creados. `doodba-bootstrap.md` cubre Modo A (Docker local en
  Mac/Linux: copier, repos.yaml, addons.yaml, gitaggregate, docker
  compose, crear DB, crear bot user, configurar `.env`, validar con
  `/onboard`) y Modo B (gcloud Compute Engine: arquitectura, IP
  estática, VM, traefik+Let's Encrypt, backups, migración A→B).
  `secrets.md` define qué se versiona, qué no, dónde vive cada
  secreto, política de rotación y acceso al certificado AEAT.

### Fase 4 — Bootstrap funcional de inpr3mium en Odoo 19

**Objetivo**: con doodba arrancado y DB vacía, dejar la instancia
**lista para facturar** en español. Es el primer uso real del agente.

- ✅ **4.0** `profile.yaml` de inpr3mium relleno. Decisiones tomadas:
  PGCE Pymes (justificado por análisis del cuadro de cuentas Holded),
  EDI stack OCA, sociedad única, sector servicios profesionales con
  packs PLV marginales, flags fiscales (IRPF profesionales,
  intracomunitario UE, servicios extra-UE USA), bot user
  `bot.contable@inpr3mium.com`, años fiscales 2024-2026, scope
  migración histórico completo con validación 24-25.
- ⏸ **4.1** Instalación de módulos vía `odoo-module-admin`
  (`repos_aggregate`, `addons_pull`, `module_install` con la lista
  `expected_modules` del profile).
- ⏸ **4.2** Empresa, idiomas y settings vía `odoo-functional-admin`
  (`language_install --langs es_ES,ca_ES`, `settings_param`,
  `subsidiary_bootstrap` con datos del profile).
- ⏸ **4.3** Plan contable, diarios (incluidos COMI / COMX / QONT del
  profile), secuencias con prefijo de año, posiciones fiscales
  (intracom UE, ISP servicios extra-UE).
- ⏸ **4.4** Bot user + permisos + record rules + `audit_admin_state`.
- ⏸ **4.5** EDI: certificado digital + entornos test/prod en módulos
  AEAT. Pasos manuales documentados en `edi-setup.md`.
- ⏸ **4.6** Smoke test contable: primera factura + SII test +
  reporting.
- ⏸ **4.7** Checkpoint y commit con bitácora del bootstrap.

### Fase 5 — Migración de datos desde Holded

**Objetivo**: importar maestros y, según scope acordado, histórico
completo + año en curso. Validación previa con subset 2024-2025.

- ⏸ **5.1** Diseño ETL detallado en `migration-from-holded.md`
  (ya con esqueleto; detalle pendiente).
- ⏸ **5.2** Decisión diferida: ¿abrir un cuarto skill
  `odoo-data-migration`? (no abrir hasta primera prueba real).
- ⏸ **5.3** Validación con subset 2024+2025: ETL + cuadre balance +
  conteo partners.
- ⏸ **5.4** Histórico completo + año en curso tras OK del subset.
- ⏸ **5.5** Cutover día D: corte limpio en Holded, saldos apertura,
  primer asiento operativo en Odoo.

### Fase 6 — Generalización para fedefarma *(diferida)*

**Objetivo**: usar el agente con un segundo tenant migrando desde
Axional. No tocar hasta que `inpr3mium` esté en producción.

- ⏸ **6** `docs/tenants/fedefarma/{profile.yaml,
  migration-from-axional.md}`. Reusar todas las skills tal cual.
  Posible justificación para abrir el skill `odoo-data-migration`.

---

## Bloques (orden de ejecución)

### Bloque A — Agente listo (sin instancia real) ✅

1. ✅ Fase 1.1 (limpieza Ikigai → genérico)
2. ✅ Fase 1.2 (estructura multi-tenant + template)
3. ✅ Fase 2.1 + 2.2 (`.env.example` + `docs/onboarding.md`)
4. ✅ Fase 2.3 (`/onboard` slash-command)
5. ✅ Fase 4.0 (rellenar `profile.yaml` de inpr3mium con decisiones
   reales)
6. ✅ Pausa: commit + push (`76ab81904` + commit del profile pendiente
   ahora).

### Bloque B — Provisionar y arrancar (manual + agente)

7. ✅ **Fase 3** — `docs/infra/doodba-bootstrap.md` con Modo A
   (local) y Modo B (gcloud) + `secrets.md`.
8. 🔄 Provisión real del entorno (Modo A: Docker local) — manual del
   usuario, ~30-60 min. *(siguiente paso, sin intervención del
   agente)*.
9. ⏸ Crear bot user + API key en la DB recién creada (paso A.6 del
   runbook).
10. ⏸ Configurar `.env` del agente (paso A.7) y ejecutar `/onboard`
    contra la instancia local → verde en conectividad, módulos en
    rojo (DB vacía, esperado).

### Bloque C — Bootstrap funcional (primer uso real del agente)

11. ⏸ Fase 4.1 (instalación de módulos)
12. ⏸ Fase 4.2 (empresa + idiomas + settings)
13. ⏸ Fase 4.3 (diarios, secuencias, posiciones fiscales)
14. ⏸ Fase 4.4 (bot user + permisos + record rules)
15. ⏸ Fase 4.5 (EDI: certificado + entornos)
16. ⏸ Fase 4.6 (smoke test: primera factura)
17. ⏸ Fase 4.7 (commit + bitácora)

### Bloque D — Migración de datos

18. ⏸ Fase 5.1 (diseño ETL Holded → Odoo)
19. ⏸ Fase 5.3 (validación con 2024+2025)
20. ⏸ Fase 5.4 (histórico completo + año en curso)
21. ⏸ Fase 5.5 (cutover día D)

### Bloque E — Futuro

22. ⏸ Fase 6 (fedefarma) — diferida.

---

## Histórico de cambios

| Fecha | Bloque/Fase | Cambio |
|-------|-------------|--------|
| 2026-05-10 | Bloque A pasos 1-4 | Limpieza Ikigai → multi-tenant + onboarding + /onboard. Commit `76ab81904`. |
| 2026-05-10 | Bloque A paso 5 (Fase 4.0) | `profile.yaml` de inpr3mium relleno con datos reales (NIF, plan, flags, dirección). README + migration plan actualizados. Commit `79f1acded`. |
| 2026-05-10 | Bloque B paso 7 (Fase 3) | Runbook `doodba-bootstrap.md` con Modo A (Docker local) + Modo B (gcloud). Añadidos `infra/README.md` y `infra/secrets.md`. |

---

## Notas operativas

- **Multi-tenant**: cada cliente/sociedad tiene su perfil bajo
  `docs/tenants/<slug>/`. El tenant activo se selecciona con la env
  var `ODOO_AGENT_TENANT`.
- **Skills agnósticas**: las 3 skills (`odoo-accounting-es`,
  `odoo-functional-admin`, `odoo-module-admin`) no contienen datos
  específicos del cliente — todo viene del `profile.yaml`.
- **Vendor docs**: la documentación oficial de Odoo está en
  `vendor/odoo-docs/` como referencia de solo lectura. Buscar ahí con
  Grep/Read antes de WebFetch.
- **Política de commit**: tras cada paso completado, commit con
  mensaje siguiendo el estilo `[TAG] área: descripción`. Tags
  habituales: `[ADD]`, `[IMP]`, `[FIX]`, `[REF]`, `[I18N]`.
