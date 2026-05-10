# Tenant: inpr3mium

**Inteligencia del negocio pr3mium S.L.** (NIF B65758682) — marca
comercial **farmapremium**. Sociedad con sede en **Carrer Coneixement
7, 08850 Gavà (Barcelona)**.

Sociedad participada por **FEDERACIO FARMACEUTICA**, **BIDAFARMA** y
**CRUZFARMA** (capital social), con préstamo de **FEDEFARMA**.

## Negocio

Doble actividad:

1. **Servicios de marketing y consultoría a farmacias** (core, mayor
   volumen). Implica IRPF en facturas (servicios profesionales),
   modelo 111 + 115.
2. **Producción y distribución de packs PLV** (Publicidad en Lugar de
   Venta — packs físicos publicitarios para farmacias). Volumen
   marginal pero presente: stock + logística.

Proveedores intracomunitarios UE (modelo 349) y extracomunitarios
USA (software/SaaS, autoliquidación ISP en 303). Sin exportación.
Régimen general de IVA (devengo, no caja).

## Estado

**Fase actual: pre-arranque.** La instancia Odoo 19 (doodba) no existe
todavía. El `profile.yaml` está completo en datos fiscales y de
identificación; falta:

- Fecha de cutover desde Holded.
- Una vez doodba esté arrancado: ejecutar `/onboard` y el bootstrap
  funcional (Fase 4 del plan).

## Datos confirmados (origen Holded)

| Campo | Valor |
|-------|-------|
| Razón social | Inteligencia del negocio pr3mium S.L. |
| Marca comercial | farmapremium |
| NIF | B65758682 |
| VAT intracom | ESB65758682 |
| Email facturación | facturas@inpr3mium.com |
| Teléfono | +34 902 811 511 |
| Web | https://inpr3mium.com |
| Holded URL | https://farmapremium.holded.com |
| Dirección | Carrer Coneixement 7, 08850 Gavà (Barcelona), ES |
| Plan contable | l10n_es.l10n_es_pymes (confirmado por análisis de cuadro de cuentas 2025) |
| Stack EDI | OCA (Community) |
| Bot user | `bot.contable@inpr3mium.com` |

## Flags fiscales activas

- **IRPF profesionales**: SÍ (cuentas 4751* y servicios 62300710*).
- **Intracomunitario UE**: SÍ (proveedores UE confirmados).
- **Servicios extracomunitarios**: SÍ (proveedores USA software).
- **Exportación**: NO.
- **Recargo de Equivalencia**: NO.
- **IVA Caja**: NO (régimen general por devengo).

## Próximos pasos

1. Provisionar host doodba (ver `docs/infra/doodba-bootstrap.md`
   cuando exista — Fase 3 del plan).
2. Crear bot user en Odoo (`bot.contable@inpr3mium.com`) + API key.
3. Ejecutar `/onboard` contra la instancia recién levantada.
4. Bootstrap funcional (Fase 4 del plan): instalación de módulos,
   plan contable, diarios, posiciones fiscales (intra-UE, ISP
   servicios extra-UE), retenciones IRPF.
5. Migración Holded — primero validación con 2024+2025, luego
   histórico completo + año en curso. Ver
   [`migration-from-holded.md`](migration-from-holded.md).
