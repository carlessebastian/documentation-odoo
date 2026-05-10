# Tenant: inpr3mium

**Inteligencia del Negocio Pr3mium S.L.** — sociedad única con sede en
Cataluña/UE. Migra desde **Holded** (SaaS contable/CRM español) a Odoo
19 Community self-hosted con doodba.

## Estado

**Fase actual: pre-arranque.** La instancia Odoo 19 (doodba) no existe
todavía. El profile.yaml está como esqueleto — los campos marcados con
`<TODO>` necesitan los datos reales del usuario antes de poder ejecutar
nada contra Odoo.

Próximos pasos:
1. Rellenar `profile.yaml` con datos reales (NIF, plan contable
   elegido, EDI stack, particularidades fiscales). Ver
   `Fase 4.0` del plan en
   `~/.claude/plans/bien-ahora-planifiquemos-cuales-snazzy-duckling.md`.
2. Provisionar host doodba (ver `docs/infra/doodba-bootstrap.md`
   cuando exista).
3. Ejecutar `/onboard` contra la instancia recién levantada.
4. Ejecutar el bootstrap funcional (Fase 4 del plan).
5. Diseñar y ejecutar la migración Holded (Fase 5 del plan).

## Particularidades a confirmar con el usuario

- Plan contable: `l10n_es.l10n_es_full` vs `l10n_es.l10n_es_pymes`.
- Stack EDI: OCA por defecto en Community, salvo razón para usar
  Enterprise.
- ¿Recargo de Equivalencia? (poco probable en consultoría/servicios,
  típico en retail).
- ¿IVA Caja? (criterio de caja en lugar de devengo).
- ¿Operaciones intracomunitarias? ¿Exportación fuera UE?
- ¿IRPF en facturas emitidas (autónomos profesionales)?
- Cuentas bancarias y BICs principales.
- Año fiscal inicial.

## Migración desde Holded

Ver [`migration-from-holded.md`](migration-from-holded.md). Todavía
sin diseñar — la API de Holded y el scope de migración se concretan en
Fase 5 del plan.
