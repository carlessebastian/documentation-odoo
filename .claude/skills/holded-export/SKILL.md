---
name: holded-export
description: |
  Usa este skill SOLO para EXPORTAR (read-only) datos desde una cuenta
  Holded (https://holded.com) hacia un dump local versionable, como
  paso previo a una migracion a Odoo. Cubre: descarga de contactos,
  productos, servicios, almacenes, impuestos, cuentas de gasto, series
  de numeracion, cuentas de tesoreria, pagos, grupos de contactos,
  canales de venta, remesas, documentos (facturas emitidas/recibidas,
  abonos, presupuestos, albaranes, pedidos), asientos contables
  (`dailyledger`), y descarga de PDFs originales escaneados de facturas
  recibidas via `/documents/{type}/{id}/pdf`. Output: JSONL +
  `pdfs/<type>/<id>.pdf` + `manifest.json` en
  `docs/tenants/<slug>/holded-export/<YYYY-MM-DD>/`. Idempotente y
  resumible. Activa este skill aunque el usuario solo diga "exportar
  holded", "dump holded", "migrar de holded", "holded api", "facturas
  recibidas escaneadas holded", "developers.holded.com", "scrape doc
  holded", "snapshot holded".

  Esta skill es READ-ONLY sobre Holded: solo usa verbos HTTP GET. No
  puede crear, modificar ni borrar nada en la cuenta origen. La
  superficie publica del cliente (`HoldedClient.get`,
  `HoldedClient.download_pdf`) hace cumplir esa garantia y los tests
  la verifican.

  DO NOT trigger for (handoff a skills hermanas):
    - Cargar los datos exportados en Odoo (create/write via RPC) ->
      eso es Fase 5 del plan, fuera del scope de esta skill. Hoy se
      hace inspeccion manual del dump + scripts ad-hoc.
    - Instalar / actualizar / desinstalar modulos Odoo, gestionar
      addons.yaml/repos.yaml, gitaggregate, doodba -> use skill
      `odoo-module-admin`.
    - Crear/modificar usuarios, grupos, ACLs, diarios, secuencias,
      posiciones fiscales en Odoo -> use skill `odoo-functional-admin`.
    - Postear facturas, registrar pagos, enviar SII/Verifactu, modelos
      AEAT -> use skill `odoo-accounting-es`.

  No usar para otros origenes (Axional, A3, ContaPlus, SAP). Cuando
  llegue fedefarma vendra una skill paralela `axional-export`.
license: MIT
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash(python3:*)
  - Bash(curl:*)
  - WebFetch
metadata:
  version: "0.1.0"
  target_source: "holded.com"
  target_api: "https://developers.holded.com/"
  output_layout: "docs/tenants/<slug>/holded-export/<YYYY-MM-DD>/"
---

# Skill: export read-only de Holded -> dump local

Este skill convierte a Claude en exportador de datos desde una cuenta
Holded (SaaS espanyol de ERP/contabilidad) hacia un dump local
versionable, pensado como insumo de una migracion posterior a Odoo 19.
Es **read-only sobre Holded**: solo emite peticiones HTTP `GET`.

## Garantia de read-only (contrato)

1. El cliente `holded_client.py` solo expone `get(endpoint, params)` y
   `download_pdf(doc_type, doc_id)`. No hay `post`, `put`, `patch` ni
   `delete`. `test_holded_client.py::test_no_write_verbs_in_public_api`
   verifica que la superficie publica solo contiene metodos GET.
2. **Lista blanca de endpoints**. El cliente solo permite GETs a paths
   que matcheen el set de patrones cargado en
   `holded_client.ALLOWED_ENDPOINTS`. Cualquier path fuera -> excepcion.
3. **`allowed-tools`** del frontmatter NO incluye `Bash(sh:*)` ni
   shells genericas que pudieran llamar a la API fuera del cliente.
4. **Sin webhooks**: Holded permite crear webhooks via API; ese
   endpoint NO esta en la lista blanca.
5. **Secretos**: `HOLDED_API_KEY` vive solo en `.env` local. El cliente
   enmascara la clave al loggear cualquier request.

Si en algun momento futuro hace falta escritura, sera una skill
distinta (`holded-import` o similar), nunca esta.

## Variables de entorno requeridas

| Variable | Proposito |
|----------|-----------|
| `HOLDED_API_KEY` | API key de Holded (Settings -> Developers en la UI) |
| `ODOO_AGENT_TENANT` | Slug del tenant activo (para resolver el directorio de salida) |
| `HOLDED_API_BASE` | (Opcional) Override del base URL. Default `https://api.holded.com` |

Si falta `HOLDED_API_KEY`, **detente y pidela al usuario antes de
ejecutar nada**. No ejecutar con valores hardcodeados ni con la clave
en argumentos de linea de comando (queda en `ps`).

## Tabla de despacho

| El usuario pide... | Ejecuta | Antes lee |
|--------------------|---------|-----------|
| **Inspeccion** | | |
| Dimensionar la cuenta Holded antes del dump | `scripts/holded_inspect.py` | `references/api-overview.md` |
| Validar un manifest ya generado | `scripts/dump_summary.py --dir <path>` | `references/dump-layout.md` |
| **Doc local** | | |
| Vendorizar / refrescar la doc de developers.holded.com | `scripts/scrape_holded_docs.py --output references/holded-api/` | `references/api-overview.md` |
| **Dump** | | |
| Dump completo (todos los resources) | `scripts/holded_export.py --output-dir docs/tenants/$ODOO_AGENT_TENANT/holded-export/$(date +%F) --include-pdfs` | `references/dump-layout.md` |
| Solo numbering_series (desbloquear Fase 4.3) | `scripts/holded_export.py --resources numbering_series --no-pdfs` | `references/endpoint-coverage.md` |
| Solo asientos contables | `scripts/holded_export.py --resources dailyledger --start-date 2024-01-01 --end-date 2025-12-31` | `references/endpoint-coverage.md` |
| Solo PDFs de facturas recibidas | `scripts/holded_export.py --resources documents.purchase --include-pdfs` | `references/pdf-attachments.md` |
| Reanudar un dump interrumpido | `scripts/holded_export.py --output-dir <existing> --resume` | `references/dump-layout.md` |

## Reglas de seguridad que debes cumplir SIEMPRE

1. **Antes de cualquier dump grande**, ejecuta `holded_inspect.py` para
   dimensionar (cuantos contactos, docs por tipo, asientos). Muestra al
   usuario el plan antes de empezar.
2. **Nunca pases `HOLDED_API_KEY` por linea de comandos**. Va por env
   var (los scripts hacen `require_env("HOLDED_API_KEY")`).
3. **Respeta el rate limit**. El cliente hace backoff exponencial sobre
   429/5xx, max 3 reintentos, respetando `Retry-After`. Si Holded
   devuelve 429 sostenido, detente y pide al usuario que reintente mas
   tarde.
4. **PDFs**: la API expone solo 1 PDF por documento. Documenta al
   usuario que si el original tenia multiples adjuntos (PDF + foto +
   Excel), solo se baja el "principal". Los secundarios son
   inaccesibles via API publica.
5. **Idempotencia**. El dump escribe `manifest.json` por resource. Si
   el usuario re-ejecuta con `--resume`, salta lo ya descargado segun
   el manifest. NUNCA sobrescribas un dump sin `--force` explicito.
6. **Datos sensibles**. El dump contiene datos fiscales y personales.
   Aviso explicito al usuario: **el directorio de salida NO se commitea
   tal cual**. `docs/tenants/<slug>/holded-export/` ya esta en
   `.gitignore` del repo (verificar antes del primer dump). Lo que se
   commitea es el `manifest.json` redactado (sin payloads) si el
   usuario lo decide explicitamente.

## Workflow: dump completo de un tenant

1. Confirma que `.env` tiene `HOLDED_API_KEY` y `ODOO_AGENT_TENANT`.
   Si no, detente y pide al usuario.
2. Si es la primera vez en este repo, ejecuta `scrape_holded_docs.py`
   una vez para vendorizar la doc en `references/holded-api/`.
3. Ejecuta `holded_inspect.py`. Muestra al usuario el resumen:
   contactos, docs por tipo, asientos, PDFs estimados, tamanyo
   aproximado del dump.
4. **Detente y pide confirmacion** mostrando el plan: directorio de
   salida, resources incluidos, fecha cubierta, si incluye PDFs.
5. Ejecuta `holded_export.py --output-dir <ruta> --include-pdfs`.
   El script:
   1. Crea el directorio si no existe.
   2. Por cada resource, abre el JSONL en `mode=w` (o `mode=a` con
      `--resume`), itera la paginacion y escribe linea-a-linea.
   3. Por cada documento `purchase`/`invoice`, descarga el PDF y lo
      escribe atomicamente a `pdfs/<type>/<id>.pdf`.
   4. Cierra el manifest con counts y sha256 por fichero.
6. Tras terminar, ejecuta `dump_summary.py --dir <ruta>` y muestra el
   resumen. Si `errors.jsonl` tiene contenido, llamar la atencion del
   usuario.
7. Apunta el dump en `docs/tenants/<slug>/holded-export/INDEX.md`
   (manual o via summary).

## Workflow: refresh de la doc Holded

1. Ejecuta `scrape_holded_docs.py --output
   .claude/skills/holded-export/references/holded-api/`.
2. Compara el diff con git: `git diff
   .claude/skills/holded-export/references/holded-api/`. Si hay cambios
   en endpoints, **actualiza** `references/endpoint-coverage.md` y la
   lista blanca de `holded_client.ALLOWED_ENDPOINTS`.
3. Commit con mensaje `[IMP] holded-export: refresh doc vendorizada
   (<fecha>)`.

## Skills hermanas (handoff)

| Si el usuario pide... | Usa el skill |
|-----------------------|--------------|
| Cargar el dump en Odoo (create/write via RPC) | Fase 5 — ad-hoc por ahora. Posible skill futura `holded-to-odoo` |
| Instalar modulos OCA Odoo | `odoo-module-admin` |
| Crear usuarios, diarios, secuencias en Odoo | `odoo-functional-admin` |
| Postear facturas, modelos AEAT, SII | `odoo-accounting-es` |
| Exportar desde Axional (fedefarma) | (skill futura `axional-export`) |

Caso fronterizo: "exporta Holded y monta los diarios en Odoo segun el
formato real". Este skill hace el export; **deriva** la configuracion
de diarios a `odoo-functional-admin` una vez tienes el dump.

## Punteros a las references

- `references/api-overview.md` — auth (header `key`), base URLs
  (`api.holded.com/api/{invoicing|accounting}/v1`), paginacion
  heterogenea (page numeric, sin paginacion), rate limits no
  documentados.
- `references/endpoint-coverage.md` — tabla de endpoints implementados,
  parametros aceptados, mapeo a modelos Odoo equivalentes.
- `references/pdf-attachments.md` — workaround
  `GET /documents/{type}/{id}/pdf`, limitacion 1 PDF por documento,
  diferencia entre PDF generado por Holded (emitidas) y PDF original
  escaneado (recibidas via app OCR).
- `references/dump-layout.md` — estructura del directorio de salida,
  esquema del `manifest.json`, formato JSONL, hash sha256 por fichero.
- `references/holded-api/` — corpus vendorizado de
  developers.holded.com (output del scraper, ~100+ .md offline).

## Calidad y tests

```bash
cd .claude/skills/holded-export
python3 -m pytest tests/ -v
```

Cubre helpers puros y mocks del transporte HTTP: paginacion, backoff
sobre 429, parsing del manifest, **assert de que la superficie publica
del cliente no expone metodos de escritura** (`test_no_write_verbs`).
No ejecuta HTTP real; las llamadas se mockean.

## Evals

`evals/evals.json` lista should-trigger / should-not-trigger / handoff.
