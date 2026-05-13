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
- [Treasury accounts](holded-treasury-accounts.md) — Fase 5.0 aplicada: 4 bank journals (SAN/BBVA/SAB/QON) + 6 cuentas 521x tarjetas + IBANs; ids reales y BNK1 legacy
- [Numbering sequences](holded-sequences.md) — counters del dump 2026-05-11 + regla pre-loading cutover
- [EDI obligations](edi-obligations.md) — NO SII (no es gran empresa), Veri\*Factu post-2027, sin FACe hoy
- [Dump analysis 2026-05-11](dump-analysis-2026-05-11.md) — volumen, concentración (BIDAFARMA+UNNEFAR+P&G=48%), distribución temporal 2018-2026, top clientes/proveedores, sales channels, expensesaccount, limitaciones dailyledger (solo manuales)
- [Decisions log](decisions-log.md) — decisiones tomadas durante el bootstrap con su razón
- [Edition evaluation plan](../edition-evaluation-plan.md) — plan A/B Community vs Enterprise (track paralelo a la migración; arranca post Fase 5.3; criterios C1-C10 + 6 fases E.0-E.6 + coste eval ~93-186€)
- [Runbook migración Holded → Odoo](../runbook-migration-holded.md) — procedimiento ejecutable paso a paso para repetir Fase 5.1 desde cero; preflight + 11 loaders + bug-fixes incorporados + recovery scenarios (incl. **Apéndice G**: subida PDFs creditnote faltantes — 680 SALES sin PDF detectados 2026-05-13)

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
