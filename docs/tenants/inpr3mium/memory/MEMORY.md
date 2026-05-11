# Tenant memory — inpr3mium

Discoveries y decisiones específicas de **inpr3mium** durante la migración
desde Holded. Es la versión versionada del conocimiento del tenant —
viaja con el repo, sobrevive resets de agent memory, accesible para
cualquier colaborador que clone el repo.

> **Convención**: al inicio de cualquier sesión que toque inpr3mium
> (`ODOO_AGENT_TENANT=inpr3mium`), leer este índice además de
> `profile.yaml` y `migration-from-holded.md`. Esta regla está
> reforzada en el `CLAUDE.md` del repo.

## Índice

- [Workspace Holded](holded-workspace.md) — `farmapremium` ≠ legal name; equivalencias y gotchas de identificación
- [Tax mapping Holded → Odoo](holded-tax-mapping.md) — 17 keys reales de 103 catálogo; BIDAFARMA = ISP Art.84; 14 subcuentas; deuda técnica ETL
- [Treasury accounts](holded-treasury-accounts.md) — 4 bancos (5720XXXX01) + 3 tarjetas Carles (521x) + 3 TELETAC (521x) + omits
- [Numbering sequences](holded-sequences.md) — counters del dump 2026-05-11 + regla pre-loading cutover
- [EDI obligations](edi-obligations.md) — NO SII (no es gran empresa), Veri\*Factu post-2027, sin FACe hoy
- [Decisions log](decisions-log.md) — decisiones tomadas durante el bootstrap con su razón

## Convención de actualización

Cuando aprenda algo nuevo sobre inpr3mium durante el bootstrap o la
migración:

- Si es **específico de inpr3mium** (cuenta concreta, decisión tomada,
  particularidad fiscal) → añadir a un archivo de esta carpeta.
- Si es **patrón genérico** (cómo se comporta Holded como sistema, qué
  cambió en Odoo 19, qué exige AEAT) → añadir a agent memory
  (`~/.claude/projects/.../memory/`), no aquí.

La distinción importa: el conocimiento genérico debe poder aplicarse a
`fedefarma` y futuros tenants sin contaminarse con datos de inpr3mium.
