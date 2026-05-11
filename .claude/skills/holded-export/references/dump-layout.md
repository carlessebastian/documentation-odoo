# Layout del dump

```
<output-dir>/
├── manifest.json               # Indice principal
├── errors.jsonl                # 1 linea por error (resource, doc_id, error, ts)
├── contacts.jsonl              # res.partner candidates
├── products.jsonl
├── services.jsonl
├── warehouses.jsonl
├── treasuries.jsonl
├── expensesaccount.jsonl
├── taxes.jsonl
├── saleschannels.jsonl
├── payments.jsonl
├── remittances.jsonl
├── contact_groups.json         # No JSONL (objeto/array unico)
├── numbering_series.json       # dict { docType: series_data }
├── documents/
│   ├── invoice.jsonl
│   ├── purchase.jsonl
│   ├── creditnote.jsonl
│   ├── salesorder.jsonl
│   ├── proform.jsonl
│   ├── waybill.jsonl
│   ├── estimate.jsonl
│   ├── salesreceipt.jsonl
│   ├── purchaseorder.jsonl
│   └── purchaserefund.jsonl
├── dailyledger.jsonl           # asientos contables, page=N
└── pdfs/
    ├── purchase/<id>.pdf       # ORIGINAL escaneado si existe
    └── invoice/<id>.pdf        # PDF generado
```

## `manifest.json` — schema

```json
{
  "version": 1,
  "created_at": "2026-05-11T12:34:56+00:00",
  "updated_at": "2026-05-11T13:02:11+00:00",
  "args": {
    "resources": ["contacts", "products", "documents", "..."],
    "doc_types": ["invoice", "purchase", "..."],
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "include_pdfs": true,
    "pdf_doc_types": ["invoice", "purchase"],
    "limit": null
  },
  "resources": {
    "contacts": {
      "items": 342,
      "elapsed_s": 1.245,
      "status": "ok",
      "path": "contacts.jsonl",
      "bytes": 218456,
      "sha256": "8c..."
    },
    "documents.invoice": {
      "items": 1208,
      "elapsed_s": 12.4,
      "status": "ok",
      "path": "documents/invoice.jsonl",
      "bytes": 1843201,
      "sha256": "ab..."
    },
    "dailyledger": { "...": "..." }
  },
  "pdfs": {
    "invoice": { "downloaded": 1208, "no_pdf": 0, "errors": 0 },
    "purchase": { "downloaded": 487, "no_pdf": 12, "errors": 1 },
    "_summary": { "downloaded": 1695, "skipped": 0, "errors": 1, "no_pdf": 12 }
  }
}
```

## JSONL

Una linea = un objeto JSON. UTF-8, sin BOM, terminador `\n`.

Bash util:

```bash
# Cuenta items
wc -l < contacts.jsonl

# Extrae VATs unicos
jq -r .vat contacts.jsonl | sort -u | wc -l

# Sample de un documento
head -1 documents/invoice.jsonl | jq .

# Suma por estado de cobro
jq -r .status documents/invoice.jsonl | sort | uniq -c
```

## Idempotencia / resume

- `manifest.json` se reescribe (atomicamente) tras cerrar **cada**
  resource — no al final del proceso.
- Con `--resume`, el exporter consulta el manifest existente y salta
  los resources con `status: ok`.
- Con `--force`, sobrescribe sin consultar.
- Los PDFs se saltan individualmente si `pdfs/<type>/<id>.pdf` existe
  con tamanyo > 0.

## Validacion

```bash
python3 scripts/dump_summary.py --dir <output-dir>
```

Reporta:

- Items por resource (manifest vs lineas reales en disco).
- Tamanyo total.
- PDFs por tipo y empty PDFs.
- Numero de lineas en `errors.jsonl`.
- Warnings cuando manifest y disco no cuadran.

Exit code 0 si todo OK, 1 si hay warnings.

## Persistencia segura

- `docs/tenants/<slug>/holded-export/` debe estar en `.gitignore`
  del repo: contiene datos personales (VATs, direcciones,
  facturas) y financieros. **Solo los hashes** del manifest pueden
  commitearse para auditoria.
- Para entornos compartidos, mover el dump a almacenamiento cifrado
  (gestor de secretos, drive del operador).
