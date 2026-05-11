# Tenant memory — `<slug>`

Discoveries y decisiones específicas de este tenant durante el
bootstrap y migración. Es la versión versionada del conocimiento del
tenant — viaja con el repo, sobrevive resets de agent memory,
accesible para cualquier colaborador que clone el repo.

> **Convención**: al inicio de cualquier sesión que toque este
> tenant (`ODOO_AGENT_TENANT=<slug>`), leer este índice además de
> `profile.yaml` y `migration-from-<source>.md`. Esta regla está
> reforzada en el `CLAUDE.md` del repo.

## Índice

Cuando creemos archivos en esta carpeta, listarlos aquí con un
one-liner descriptivo. Sugerencias de archivos típicos según fase
de migración:

- `<source>-workspace.md` — identificación del workspace origen
  (Holded, Axional, etc.); equivalencias entre slug del agente y
  nombre del workspace externo.
- `<source>-tax-mapping.md` — mapeo concreto de impuestos del
  sistema origen a `account.tax` Odoo; subcuentas creadas; deuda
  técnica para ETL.
- `<source>-treasury-accounts.md` — mapeo cuentas de tesorería
  (bancos, tarjetas) origen → Odoo journals/accounts.
- `<source>-sequences.md` — counters de las secuencias del sistema
  origen en el momento del dump pre-cutover.
- `edi-obligations.md` — estado concreto de SII / Veri\*Factu /
  FacturaE para este tenant; razones de inclusión o no en
  expected_modules.
- `decisions-log.md` — decisiones tomadas durante bootstrap y
  migración con su razón. Ordenado del más reciente al más antiguo.

## Convención de actualización

Cuando aprenda algo nuevo sobre este tenant durante el bootstrap o
migración:

- Si es **específico de este tenant** (cuenta concreta, decisión
  tomada, particularidad fiscal) → añadir a un archivo de esta
  carpeta.
- Si es **patrón genérico** (cómo se comporta el sistema origen, qué
  cambió en Odoo 19, qué exige AEAT) → añadir a agent memory
  (`~/.claude/projects/.../memory/`), no aquí.

La distinción importa: el conocimiento genérico debe poder aplicarse
a otros tenants futuros sin contaminarse con datos de este.
