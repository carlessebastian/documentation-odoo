# EDI obligations — inpr3mium

Estado de obligaciones EDI/AEAT específico para **inpr3mium**. Se
decide a partir de las reglas genéricas que viven en agent memory
(`project_edi_obligation_rules` — SII solo gran empresa/REDEME,
Veri\*Factu obligatorio desde 2027, FacturaE solo si factura a
Admin Pública).

## SII — NO aplica

**inpr3mium NO está obligada a SII (Suministro Inmediato de
Información del IVA)**. Razones:

- Facturación muy por debajo del umbral de 6.010.121,04 €/año (gran
  empresa).
- Sociedad única, no es grupo de IVA (REGE).
- No inscrita en REDEME (devolución mensual del IVA).

No tiene sentido optar voluntariamente — añadiría carga operativa
sin valor de negocio.

**Acción aplicada**: `l10n_es_aeat_sii_oca` **eliminado** de
`expected_modules` en `profile.yaml` (no diferido — completamente
removido del scope para este tenant).

## Veri*Factu — aplicable desde 2027

Veri\*Factu (RD 1007/2023) será obligatorio para inpr3mium desde
**2027**. Hasta entonces, no es bloqueante para go-live.

Cuando se acerque 2027:

1. Instalar `l10n_es_aeat_verifactu_oca` (módulo OCA, ya identificado
   y diferido en `profile.yaml.deferred_modules.revisit_on=2026-Q4`).
2. Configurar el certificado FNMT del representante legal.
3. Reabrir Fase 4.5a (actualmente diferida — ver
   [decisions-log](decisions-log.md)).

## FacturaE / FACe — instalado pero no usado

`l10n_es_facturae` está instalado (Fase 4.1) pero **no se usa hoy**:

- inpr3mium no factura a Administración Pública.
- No hay clientes que exijan FacturaE como formato de intercambio.

Queda como capacidad latente. Activarlo si:

- Aparece un cliente AAPP (entonces hay que configurar el certificado
  + entornos test/prod de FACe).
- Aparece un cliente B2B que exija FacturaE por contrato.

## Cierre Fase 4.5a — diferida

Fase 4.5a (instalación del certificado EDI + configuración entornos
AEAT) está **diferida** en `docs/PLAN.md`. Decisión tomada
2026-05-11: sin SII, sin Veri\*Factu inmediato, sin facturación a
AAPP — no hay driver de negocio para invertir esfuerzo hoy.

Triggers para reabrir 4.5a:

- Aproximación a fecha límite Veri\*Factu (revisar Q4 2026).
- Aparición de factura a Administración Pública.
- Cambio de régimen fiscal (paso a REDEME, crecimiento que supere
  umbral SII).
