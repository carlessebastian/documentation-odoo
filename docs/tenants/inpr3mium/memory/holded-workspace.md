# Workspace Holded — inpr3mium

## Identificación del workspace

El workspace de Holded que contiene la contabilidad de **Inteligencia
del negocio pr3mium S.L.** (`ESB65758682`) se llama
**`farmapremium`** en la UI de Holded (sidebar, abajo izquierda).

El nombre del workspace **no coincide** con el legal name del tenant.
Es importante recordarlo al verificar contra capturas de UI: una
captura puede mostrar `farmapremium` en la sidebar mientras la
contabilidad subyacente es la de inpr3mium. Confirmación: los IBANes
de las cuentas bancarias visibles en la UI (`ES15 0049 3764...` para
Santander, etc.) coinciden 1:1 con el dump
`docs/tenants/inpr3mium/holded-export/2026-05-11/treasuries.jsonl`.

## Estado del workspace

En la captura de 2026-05-11 la suscripción Holded muestra:

- "Equipo PRO ha expirado / Prueba finalizada".
- A pesar de eso, la API key continúa funcionando para lectura — el
  dump completo (969 MB, 12.212 documentos, 7.489 PDFs) se exportó
  sin problemas con scope read-only.

Implicación: para Fase 5 (carga histórica) no es necesario reactivar
el plan PRO, mientras el dump capture el estado pre-cutover.

## Tenant slug en el agente

El slug del agente es **`inpr3mium`** (el legal name simplificado),
NO `farmapremium`. Esto se decidió cuando se creó la estructura
multi-tenant (Fase 1.2). Para mantener consistencia:

- `ODOO_AGENT_TENANT=inpr3mium`
- `docs/tenants/inpr3mium/...`
- BD Odoo: `inpr3mium_dev` (local), `inpr3mium_prod` (futuro)

Si en algún momento se abre un workspace Holded distinto para
otra sociedad bajo el mismo paraguas (ej. `inpr3mium-eu` separada),
se creará un tenant slug separado en el agente — un workspace
Holded ↔ un tenant del agente.
