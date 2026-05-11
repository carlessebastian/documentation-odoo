# PDFs y adjuntos en Holded

## El workaround

Holded NO expone un endpoint dedicado para "descargar los adjuntos
originales que el usuario subio a un documento". El unico camino es:

```
GET /api/invoicing/v1/documents/{docType}/{documentId}/pdf
key: <HOLDED_API_KEY>
```

Devuelve:

```json
{
  "status": 1,
  "data": "<base64 del PDF>"
}
```

El cliente decodifica `data` con `base64.b64decode` y devuelve los
bytes. Si `status != 1` o `data` viene vacio, devolvemos `b""`.

Endpoint validado en `references/holded-api/getdocumentpdf.md`.

## Que PDF devuelve exactamente

Depende del docType:

| docType | Que devuelve |
|---|---|
| `invoice`, `creditnote`, `salesreceipt`, `salesorder`, `estimate`, `proform`, `waybill`, `purchaseorder` | PDF **generado por Holded** (plantilla del usuario). |
| `purchase`, `purchaserefund` | Si el usuario subio el original (via app movil, OCR, drag-and-drop), devuelve **el PDF original escaneado**. Si no, devuelve un PDF generado. |

**Importante para la migracion a Odoo**: para facturas recibidas
escaneadas (originales que requiere la AEAT por compliance), este es
el unico canal automatizado para recuperarlas.

## Limitacion: 1 adjunto por documento

Si el usuario subio multiples archivos a un mismo documento (PDF
principal + foto + Excel), la API solo expone el **principal**. Los
adjuntos secundarios son **inaccesibles via API publica**. Documentado
empiricamente por la comunidad — Holded no ha publicado una solucion.

Si esto es bloqueante para tu auditoria, las opciones son:

1. Antes del cutover, descargar manualmente desde la UI los
   adjuntos secundarios criticos.
2. Mantener Holded en read-only post-cutover hasta cumplir el plazo
   legal de conservacion.

## Algoritmo de descarga del exporter

`holded_export.py` con `--include-pdfs`:

1. Tras cerrar `documents/<type>.jsonl`, abre el fichero.
2. Por cada linea (un doc) extrae `id` o `_id`.
3. Si `pdfs/<type>/<id>.pdf` ya existe y tiene tamanyo > 0 y
   `--resume`, salta.
4. Llama `client.download_pdf(type, id)`.
5. Si devuelve bytes, los escribe atomicamente
   (`tmp` -> `os.replace`).
6. Si devuelve `b""`, registra en el manifest como `no_pdf` (es
   normal — algunos docs no tienen PDF asociado).
7. Si la llamada lanza `HoldedError`, registra el error en
   `errors.jsonl` y continua.

Por defecto solo bajamos PDFs de `invoice` y `purchase`. Para incluir
otros: `--pdf-doc-types invoice,purchase,creditnote`.

## Numero estimado de PDFs

Antes del primer dump, ejecuta `holded_inspect.py` para ver los
counts de documents por type. Multiplica:

- `purchase` (facturas recibidas) — todas tendran al menos el PDF
  generado, y las que vienen de la app movil tendran el ORIGINAL
  escaneado. Promedio reportado: ~50-200 KB cada uno.
- `invoice` (facturas emitidas) — PDFs generados por Holded, ~80-150
  KB cada uno.

Para una empresa media (~1000 facturas emitidas + ~500 recibidas al
anyo), un dump anual de PDFs ronda **150-300 MB**.
