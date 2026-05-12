"""Helpers puros + orquestacion para `loader_partners.py`.

Funciones puras (testables offline, sin red):
- `dedup_key`: clave canonica `(cc, code_norm)` o `None` si el contact
  no es deduplicable por code.
- `classify_rank`: tupla `(customer_rank, supplier_rank)` ∈ {0,1}x{0,1}
  derivada de `type` + `clientRecord` + `supplierRecord`.
- `aggregate_ranks`: OR de dos pares de rangos cuando se mergea un dup.
- `parse_no_usar`: extrae marca `(NO USAR)` -> name limpio + active=False.
- `build_partner_vals`: dict listo para `res.partner.create()`/`write()`
  a partir de un contact Holded + ids de `country` y `state` ya resueltos.

`load_partners` orquesta el flujo dos-pasadas (canonicalizar + upsert)
con un `client` inyectado. Hace upsert idempotente via
`ext_id_upsert.upsert` y devuelve `PartnerStats`.

Decisiones de diseno (ver `migration-from-holded.md` seccion 5.1
"Partners" y el dump-analysis 2026-05-11):

- **Dedup por `code`** (CIF/NIF Holded), no por `vatnumber`: en el dump
  de inpr3mium solo 18/3.363 contacts tienen `vatnumber` mientras que
  3.173 tienen `code`. La cardinalidad de dups por code es real (188
  pares; ejemplos: mismo trabajador con 3 registros distintos en
  Holded). Mergeamos en un solo `res.partner` y enlazamos los demas
  ext_ids al mismo `res_id`.
- **Sin code o code='0'**: cada contact es su propio partner. ext_id
  unico `__holded__.contact_<id>`. No hay merge.
- **`mobile` no existe en `res.partner` Odoo 19** (gotcha registrado).
  Mapeamos Holded.mobile a `phone` si no hay phone, si no lo perdemos.
- **VAT field**: solo lo seteamos cuando `normalize_vat` devuelve un
  string con dos letras de pais + alfanumerico (formato VIES-able). En
  el resto guardamos el `code` original en `ref` para auditoria.
- **Unknown placeholder**: creamos una vez `__holded__.contact__unknown`
  con `name="Cliente historico no identificado"`. Los 1.149 docs con
  `contactId` no resoluble apuntaran aqui.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from holded_resolvers import (
    EXT_MODULE,
    UNKNOWN_CONTACT_XMLID,
    normalize_vat,
    partner_active_from_name,
)


PLACEHOLDER_CODES = {"", "0", "00", "000", "0000"}

# Sentinels textuales para detectar las notas inyectadas. Sobreviven la
# sanitizacion HTML de Odoo (a diferencia de los comentarios `<!-- -->`,
# que el cleaner descarta asimetricamente cuando aparecen al inicio del
# fragmento -- bug constatado al probar `<!-- start --><p>X</p><!-- end -->`
# y leer `<p>X</p><!-- end -->` tras el round-trip). Usar la frase humana
# como discriminador es robusto y a la vez legible.
HOLDED_CODE_NOTE_SENTINEL = "Código Holded (no validado como VAT)"
HOLDED_VAT_REJECTED_SENTINEL = "VAT rechazado por validación Odoo"


def _holded_code_note(code: str) -> str:
    """Nota HTML cuando un `code` Holded no se promociona a `vat` Odoo.

    Caso tipico: contact non-ES con `code` poblado (numero proveedor Amazon
    'W0185696B', tax id US 'EU372041333', texto plano 'SENDGRID'). El code
    queda en `ref` pero el campo no es visible en la vista standard de
    proveedor de `l10n_es_pymes` -- por eso lo replicamos en `comment`.
    """
    return (
        f"<p>{HOLDED_CODE_NOTE_SENTINEL}: "
        f"<code>{html.escape(code)}</code></p>"
    )


def _holded_vat_rejected_note(vat: str) -> str:
    """Nota HTML cuando Odoo rechaza el `vat` y lo dropamos via fallback.

    Caso tipico: cc=LU con `vatnumber='W0185696B'` -- `base_vat` valida
    el formato del pais (LU exige 8 digitos) y crashea. El vat original
    se preserva en la nota para auditoria; el `code` Holded sigue en `ref`.
    """
    return (
        f"<p>{HOLDED_VAT_REJECTED_SENTINEL} (conservado como referencia): "
        f"<code>{html.escape(vat)}</code></p>"
    )


def has_holded_note(comment: str | None) -> bool:
    """True si `comment` ya contiene cualquiera de las notas Holded."""
    if not comment:
        return False
    return (
        HOLDED_CODE_NOTE_SENTINEL in comment
        or HOLDED_VAT_REJECTED_SENTINEL in comment
    )


@dataclass
class PartnerStats:
    total: int = 0
    canonical_create: int = 0
    canonical_update: int = 0
    dup_link: int = 0           # contact dup que solo necesita un nuevo ext_id
    unique_create: int = 0      # sin code, no deduplicable
    unique_update: int = 0
    would_create: int = 0
    would_update: int = 0
    would_link: int = 0
    unknown_placeholder_created: bool = False
    no_country: int = 0
    no_state_es: int = 0        # contacts ES con province que no matcheo
    no_usar: int = 0
    vat_dropped: int = 0        # vat fallo validacion base_vat -> reintentado sin vat
    errors: int = 0
    error_details: list[tuple[str, str]] = field(default_factory=list)


def _upsert_with_vat_fallback(
    upsert_fn: Any,
    client: Any,
    xmlid: str,
    vals: dict,
    stats: PartnerStats,
    hid: str,
) -> tuple[int, str]:
    """Wrap upsert con reintento sin `vat` si base_vat valida y rechaza.

    Holded guarda lo que el usuario escribio en `vatnumber`, no garantiza
    formato VAT valido para non-ES (e.g., 'W0185696B' para LU rechazado
    por base_vat porque LU exige 8 digitos). Politica:
    1. Intentar con vat normal.
    2. Si excepcion menciona 'IVA' / 'VAT' / 'invalido' / 'expected', drop
       el campo vat y reintentar. La perdida es aceptable: el code
       original queda en `ref` para auditoria.
    """
    try:
        return upsert_fn(client, xmlid, "res.partner", vals, noupdate=True)
    except Exception as exc:
        msg = str(exc).lower()
        is_vat_error = ("vat" in msg or "iva" in msg) and "vat" in vals
        if not is_vat_error:
            raise
        # Drop vat y reintenta; inyectamos la nota explicando el rechazo
        # para que el operador pueda revisar el VAT original desde la UI.
        # Sobrescribimos `comment` directamente: el caller (build_partner_vals)
        # nunca pone una nota Holded cuando hay vat en vals, asi que cualquier
        # comment previo en retry_vals lo trajo el dump (improbable hoy).
        original_vat = vals.get("vat", "")
        retry_vals = {k: v for k, v in vals.items() if k != "vat"}
        if original_vat:
            retry_vals["comment"] = _holded_vat_rejected_note(original_vat)
        stats.vat_dropped += 1
        return upsert_fn(client, xmlid, "res.partner", retry_vals, noupdate=True)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def dedup_key(contact: dict) -> tuple[str, str] | None:
    """Devuelve `(cc, code_upper)` o `None` si el code no es deduplicable.

    Reglas:
    - code vacio o en PLACEHOLDER_CODES -> None (cada contact es unico).
    - cc puede ser '' (Holded permite billAddress sin pais).
    """
    code = (contact.get("code") or "").strip().upper()
    if not code or code in PLACEHOLDER_CODES:
        return None
    cc = ((contact.get("billAddress") or {}).get("countryCode") or "").strip().upper()
    return (cc, code)


def classify_rank(contact: dict) -> tuple[int, int]:
    """Devuelve `(customer_rank, supplier_rank)` con valores 0 o 1.

    Reglas (ver dump-analysis: type x records consistente):
    - `type=client` o `clientRecord` truthy -> customer_rank=1.
    - `type in {supplier, creditor}` o `supplierRecord` truthy -> supplier_rank=1.
    - `type=lead`: customer_rank=1 (los leads convierten a clientes).
    - resto (type='' o None, sin records): ambos 0.
    """
    ctype = (contact.get("type") or "").lower()
    has_client = bool(contact.get("clientRecord"))
    has_supplier = bool(contact.get("supplierRecord"))

    cust = 1 if (ctype in ("client", "lead") or has_client) else 0
    supp = 1 if (ctype in ("supplier", "creditor") or has_supplier) else 0
    return (cust, supp)


def aggregate_ranks(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    """OR logico de dos pares (customer_rank, supplier_rank)."""
    return (max(a[0], b[0]), max(a[1], b[1]))


def parse_no_usar(raw_name: Any) -> tuple[str, bool]:
    """Wrapper sobre `partner_active_from_name` para legibilidad en este modulo."""
    return partner_active_from_name(raw_name)


def _strip_diacritics(s: str) -> str:
    """Quita acentos: 'Guipúzcoa' -> 'Guipuzcoa'."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_province(raw: Any) -> str:
    """Normaliza un province name Holded para lookup en `res.country.state`.

    - strip + collapse spaces + casefold + strip diacritics.
    - El strip de acentos es necesario porque Holded suele venir SIN
      acentos ('vizcaya', 'guipuzcoa') mientras Odoo guarda CON acentos
      ('Vizcaya', 'Guipúzcoa').
    """
    if not raw:
        return ""
    return _strip_diacritics(re.sub(r"\s+", " ", str(raw)).strip()).casefold()


# Sinonimos extra para nombres de state Odoo que no se extraen
# automaticamente de su `name` parentizado/slash-separado. Mantener
# pequeno y revisable; si crece, mover a YAML.
STATE_NAME_EXTRA_ALIASES: dict[str, list[str]] = {
    # Holded usa 'Baleares'; Odoo l10n_es tiene 'Illes Balears (Islas
    # Baleares)' que produce aliases 'illes balears', 'islas baleares'
    # pero no 'baleares' suelto.
    "Illes Balears (Islas Baleares)": ["Baleares"],
}


def state_name_aliases(name: str) -> list[str]:
    """Genera todas las claves de busqueda normalizadas para un state Odoo.

    Maneja patrones de l10n_es:
    - 'A Coruña (La Coruña)' -> ['a coruña (la coruña)', 'a coruña', 'la coruña']
    - 'Araba/Álava' -> ['araba/álava', 'araba', 'álava']
    - 'Barcelona' -> ['barcelona']
    - Sinonimos manuales via `STATE_NAME_EXTRA_ALIASES`.

    Cada alias se pasa por `normalize_province` (strip diacritics +
    casefold).
    """
    aliases: set[str] = {name}
    # Parentesis: extraer el contenido y el resto sin parentesis
    m = re.match(r"^(.+?)\s*\((.+?)\)\s*$", name)
    if m:
        aliases.add(m.group(1).strip())
        aliases.add(m.group(2).strip())
    # Slash: cada lado por separado
    if "/" in name:
        for part in name.split("/"):
            part_clean = re.sub(r"\(.*\)", "", part).strip()
            if part_clean:
                aliases.add(part_clean)
    # Sinonimos manuales (e.g., Baleares)
    aliases.update(STATE_NAME_EXTRA_ALIASES.get(name, []))
    return [normalize_province(a) for a in aliases if a]


def build_partner_vals(
    contact: dict,
    *,
    country_id: int | None,
    state_id: int | None,
    customer_rank: int,
    supplier_rank: int,
) -> dict:
    """Mapea un contact Holded a vals de `res.partner` para Odoo 19.

    Campos NO seteados aqui (decidir en orquestador o post-load):
    - `category_id`: requiere mapeo de `groupId` Holded a categorias Odoo.
    - `property_payment_term_id` / `supplier`: pueden venir de Fase 5.0
      defaults; setear via override si Holded.defaults.dueDays difiere.
    """
    raw_name = contact.get("name") or ""
    name, active = parse_no_usar(raw_name)

    raw_vat = (contact.get("vatnumber") or "").strip()
    raw_code = (contact.get("code") or "").strip()
    cc = ((contact.get("billAddress") or {}).get("countryCode") or "").strip().upper()
    # Politica VAT (endurecida tras crash con Amazon EMEA LU):
    # - ES: derivar `vat` desde `code` si formato NIF/CIF (normalize_vat
    #   prepende 'ES'). Odoo l10n_es valida digito de control y la mayoria
    #   de codes ES en el dump son validos.
    # - non-ES: SOLO `vatnumber` explicito si Holded lo trae (18/3.363).
    #   El campo `code` para non-ES contiene cualquier cosa: numero de
    #   proveedor Amazon ('W0185696B'), tax id US estilo 'EU372041333',
    #   texto plano 'SENDGRID'. Si lo metemos como vat, `base_vat`
    #   valida el formato del pais y crashea (LU exige 8 digitos).
    if cc == "ES":
        vat_source = raw_vat or raw_code
    else:
        vat_source = raw_vat  # solo vatnumber explicito
    vat_norm = normalize_vat(vat_source, country=cc) if vat_source else None
    vat_val: str | None = None
    # Solo VAT si normalize_vat produjo algo con dos letras de pais Y
    # al menos un digito en el resto (descarta texto puro como 'SENDGRID').
    if (vat_norm and len(vat_norm) >= 4 and vat_norm[:2].isalpha()
            and any(ch.isdigit() for ch in vat_norm[2:])):
        vat_val = vat_norm

    ba = contact.get("billAddress") or {}
    is_person = bool(contact.get("isperson"))

    vals: dict[str, Any] = {
        "name": name or "(sin nombre)",
        "active": active,
        "company_type": "person" if is_person else "company",
        "is_company": not is_person,
        "customer_rank": customer_rank,
        "supplier_rank": supplier_rank,
    }
    if raw_code:
        vals["ref"] = raw_code
    if vat_val:
        vals["vat"] = vat_val
    # Si tenemos `code` Holded pero no lo promovemos a `vat`, replicamos el
    # code en `comment` para que sea visible en la UI (Notas internas). El
    # campo `ref` no aparece en la vista standard de proveedor de l10n_es_pymes.
    if raw_code and not vat_val:
        vals["comment"] = _holded_code_note(raw_code)
    email = (contact.get("email") or "").strip()
    if email:
        vals["email"] = email
    # `mobile` no existe en res.partner Odoo 19 -> degradar a phone
    # si phone esta vacio.
    phone = (contact.get("phone") or "").strip()
    mobile = (contact.get("mobile") or "").strip()
    final_phone = phone or mobile
    if final_phone:
        vals["phone"] = final_phone
    street = (ba.get("address") or "").strip()
    if street:
        vals["street"] = street
    city = (ba.get("city") or "").strip()
    if city:
        vals["city"] = city
    zip_ = (ba.get("postalCode") or "").strip()
    if zip_:
        vals["zip"] = zip_
    if country_id:
        vals["country_id"] = country_id
    if state_id:
        vals["state_id"] = state_id
    lang_holded = (contact.get("defaults") or {}).get("language")
    if lang_holded == "es":
        vals["lang"] = "es_ES"
    elif lang_holded == "ca":
        vals["lang"] = "ca_ES"
    elif lang_holded == "en":
        vals["lang"] = "en_US"
    return vals


# ---------------------------------------------------------------------------
# Orchestration (con OdooClient inyectado)
# ---------------------------------------------------------------------------


def iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def load_country_index(client: Any, country_codes: set[str]) -> dict[str, int]:
    """Devuelve `{country_code: id}` para los codigos ISO2 pedidos.

    Codes no encontrados quedan ausentes del dict (sin abortar; el
    orquestador deja country_id=False).
    """
    if not country_codes:
        return {}
    hits = client.call(
        "res.country",
        "search_read",
        [[("code", "in", sorted(country_codes))]],
        {"fields": ["code", "id"]},
    )
    return {h["code"]: h["id"] for h in hits}


def load_state_index(client: Any, country_id: int) -> dict[str, int]:
    """Devuelve `{normalized_alias: id}` para un pais (e.g., ES).

    Para cada state Odoo, indexa multiples aliases: nombre completo,
    parte antes/dentro de parentesis, y cada lado de un `X/Y`. Esto
    cubre los patrones bilingues de l10n_es ('A Coruña (La Coruña)',
    'Araba/Álava') resolviendo el province Holded en castellano +
    sin acentos.
    """
    hits = client.call(
        "res.country.state",
        "search_read",
        [[("country_id", "=", country_id)]],
        {"fields": ["name", "id"]},
    )
    index: dict[str, int] = {}
    for h in hits:
        for alias in state_name_aliases(h["name"]):
            # Si dos states comparten alias (no esperado en ES), el primero gana
            index.setdefault(alias, h["id"])
    return index


def search_ext_id(client: Any, xmlid: str) -> int | None:
    module, name = xmlid.split(".", 1)
    hits = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["res_id"], "limit": 1},
    )
    return hits[0]["res_id"] if hits else None


def link_ext_id(client: Any, xmlid: str, model: str, res_id: int) -> None:
    """Crea un ext_id `xmlid` apuntando a `(model, res_id)` si no existe."""
    module, name = xmlid.split(".", 1)
    existing = client.call(
        "ir.model.data",
        "search_read",
        [[("module", "=", module), ("name", "=", name)]],
        {"fields": ["id"], "limit": 1},
    )
    if existing:
        return
    client.call(
        "ir.model.data",
        "create",
        [{
            "module": module,
            "name": name,
            "model": model,
            "res_id": res_id,
            "noupdate": True,
        }],
    )


def ensure_unknown_placeholder(
    client: Any,
    stats: PartnerStats,
    dry_run: bool,
) -> int | None:
    """Crea (o reusa) el partner placeholder `__holded__.contact__unknown`.

    Devuelve el `res_id`, o `None` si dry_run y aun no existe (el caller
    no necesita un id real en dry-run).
    """
    existing = search_ext_id(client, UNKNOWN_CONTACT_XMLID)
    if existing:
        return existing
    if dry_run:
        stats.unknown_placeholder_created = True  # would_create
        return None
    pid = client.call(
        "res.partner",
        "create",
        [{
            "name": "Cliente historico no identificado",
            "active": True,
            "company_type": "company",
            "is_company": True,
            "customer_rank": 1,
            "supplier_rank": 0,
            "comment": (
                "<p>Placeholder para contacts Holded con contactId no "
                "resoluble (~1.149 docs). Generado por loader_partners.py "
                "en Fase 5.1 ETL.</p>"
            ),
        }],
    )
    link_ext_id(client, UNKNOWN_CONTACT_XMLID, "res.partner", pid)
    stats.unknown_placeholder_created = True
    return pid


def load_partners(
    client: Any,
    dump_dir: Path,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    report_dir: Path | None = None,
) -> PartnerStats:
    """Carga `contacts.jsonl` -> `res.partner` con dedup por (cc, code).

    Estrategia dos-pasadas:
    1. Pre-fetch: country index, ES state index, contar codes para
       elegir canonical por (cc, code) — el canonical es el PRIMER
       contact en orden de aparicion en JSONL con esa clave; los
       siguientes con misma clave se mergean (ranks OR'd) y solo
       reciben un ext_id pointing al canonical.
    2. Iterar de nuevo y emitir el upsert real (o would_X en dry-run).

    Returns:
        PartnerStats con conteos.
    """
    input_path = dump_dir / "contacts.jsonl"
    if not input_path.exists():
        raise FileNotFoundError(f"No existe: {input_path}")

    # Lazy import: solo para modo real.
    upsert = None
    if not dry_run:
        try:
            from ext_id_upsert import upsert as _upsert
            upsert = _upsert
        except ImportError as exc:
            raise RuntimeError(
                "ext_id_upsert no en PYTHONPATH. Anade "
                "`.claude/skills/odoo-functional-admin/scripts` al "
                "PYTHONPATH antes de correr en modo real."
            ) from exc

    records = list(iter_jsonl(input_path))
    if limit:
        records = records[:limit]

    stats = PartnerStats(total=len(records))

    # Pre-fetch country index para todos los cc presentes
    countries_needed = {
        ((r.get("billAddress") or {}).get("countryCode") or "").strip().upper()
        for r in records
    }
    countries_needed.discard("")
    country_index = load_country_index(client, countries_needed)
    state_index_by_country: dict[str, dict[str, int]] = {}

    # Placeholder unknown (no bloquea si dry_run y no existe)
    ensure_unknown_placeholder(client, stats, dry_run=dry_run)

    # Pasada 1: identificar canonicals y aggregate ranks por (cc, code)
    canonical_by_key: dict[tuple[str, str], str] = {}  # key -> holded_id canonical
    aggregated_ranks: dict[tuple[str, str], tuple[int, int]] = {}
    for r in records:
        key = dedup_key(r)
        rank = classify_rank(r)
        if key is None:
            continue
        if key not in canonical_by_key:
            canonical_by_key[key] = r["id"]
            aggregated_ranks[key] = rank
        else:
            aggregated_ranks[key] = aggregate_ranks(aggregated_ranks[key], rank)

    # Mapa holded_id -> res_id para los canonicals ya escritos
    canonical_res_id: dict[str, int] = {}

    rows: list[dict[str, Any]] = []

    # Pasada 2: emitir upserts
    for r in records:
        hid = r["id"]
        xmlid = f"{EXT_MODULE}.contact_{hid}"
        cc = ((r.get("billAddress") or {}).get("countryCode") or "").strip().upper()
        key = dedup_key(r)

        row: dict[str, Any] = {
            "holded_id": hid,
            "name": (r.get("name") or "")[:80],
            "code": r.get("code"),
            "cc": cc,
            "type": r.get("type"),
            "xmlid": xmlid,
            "status": "",
            "res_id": "",
            "error": "",
        }

        # Resolver country_id
        country_id = country_index.get(cc) if cc else None
        if cc and not country_id:
            stats.no_country += 1

        # Resolver state_id solo para ES (resto de paises rara vez tiene
        # state en Odoo res.country.state util; lo dejamos vacio para no
        # crear ruido).
        state_id = None
        province = ((r.get("billAddress") or {}).get("province") or "").strip()
        if cc == "ES" and province and country_id:
            if cc not in state_index_by_country:
                state_index_by_country[cc] = load_state_index(client, country_id)
            state_id = state_index_by_country[cc].get(normalize_province(province))
            if province and not state_id:
                stats.no_state_es += 1

        # NO USAR tracking
        if "NO USAR" in (r.get("name") or "").upper():
            stats.no_usar += 1

        # CASO A: contact tiene key dedup
        if key is not None:
            canonical_hid = canonical_by_key[key]
            cust, supp = aggregated_ranks[key]
            is_canonical = (hid == canonical_hid)

            if is_canonical:
                vals = build_partner_vals(
                    r,
                    country_id=country_id,
                    state_id=state_id,
                    customer_rank=cust,
                    supplier_rank=supp,
                )
                if dry_run:
                    existing = search_ext_id(client, xmlid)
                    if existing:
                        row["status"] = "would_update"
                        stats.would_update += 1
                    else:
                        row["status"] = "would_create"
                        stats.would_create += 1
                else:
                    res_id, action = _upsert_with_vat_fallback(
                        upsert, client, xmlid, vals, stats, hid,
                    )
                    canonical_res_id[hid] = res_id
                    row["res_id"] = res_id
                    if action == "created":
                        row["status"] = "canonical_create"
                        stats.canonical_create += 1
                    else:
                        row["status"] = "canonical_update"
                        stats.canonical_update += 1
            else:
                # Dup: solo link ext_id al canonical
                if dry_run:
                    existing = search_ext_id(client, xmlid)
                    if existing:
                        row["status"] = "would_update"  # dup ya linkado
                        stats.would_update += 1
                    else:
                        row["status"] = "would_link"
                        stats.would_link += 1
                else:
                    target_res_id = canonical_res_id.get(canonical_hid)
                    if not target_res_id:
                        # Defensa: buscar via ext_id del canonical
                        target_res_id = search_ext_id(
                            client, f"{EXT_MODULE}.contact_{canonical_hid}"
                        )
                    if target_res_id:
                        link_ext_id(client, xmlid, "res.partner", target_res_id)
                        row["status"] = "dup_link"
                        row["res_id"] = target_res_id
                        stats.dup_link += 1
                    else:
                        row["status"] = "error"
                        row["error"] = f"canonical {canonical_hid} no resoluble"
                        stats.errors += 1
                        stats.error_details.append((hid, row["error"]))
        else:
            # CASO B: sin key dedup -> unique partner
            rank = classify_rank(r)
            vals = build_partner_vals(
                r,
                country_id=country_id,
                state_id=state_id,
                customer_rank=rank[0],
                supplier_rank=rank[1],
            )
            if dry_run:
                existing = search_ext_id(client, xmlid)
                if existing:
                    row["status"] = "would_update"
                    stats.would_update += 1
                else:
                    row["status"] = "would_create"
                    stats.would_create += 1
            else:
                res_id, action = _upsert_with_vat_fallback(
                    upsert, client, xmlid, vals, stats, hid,
                )
                row["res_id"] = res_id
                if action == "created":
                    row["status"] = "unique_create"
                    stats.unique_create += 1
                else:
                    row["status"] = "unique_update"
                    stats.unique_update += 1

        rows.append(row)

    _write_report(rows, dump_dir, dry_run, report_dir)
    return stats


def _write_report(
    rows: list[dict],
    dump_dir: Path,
    dry_run: bool,
    report_dir: Path | None,
) -> None:
    if report_dir is None:
        report_dir = dump_dir / ".etl_reports"
    report_dir.mkdir(exist_ok=True)
    mode_tag = "dryrun" if dry_run else "run"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = report_dir / f"partners_{mode_tag}_{ts}.csv"
    if not rows:
        return
    fields_order = [
        "holded_id", "name", "code", "cc", "type",
        "xmlid", "status", "res_id", "error",
    ]
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields_order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"report: {out}", file=sys.stderr)


def print_summary(stats: PartnerStats, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "REAL"
    print(f"\n[partners {mode}]")
    print(f"  total contacts:           {stats.total}")
    if dry_run:
        print(f"  would_create:             {stats.would_create}")
        print(f"  would_update:             {stats.would_update}")
        print(f"  would_link (dups):        {stats.would_link}")
    else:
        print(f"  canonical_create:         {stats.canonical_create}")
        print(f"  canonical_update:         {stats.canonical_update}")
        print(f"  dup_link:                 {stats.dup_link}")
        print(f"  unique_create:            {stats.unique_create}")
        print(f"  unique_update:            {stats.unique_update}")
    print(f"  unknown placeholder:      {'ensured' if stats.unknown_placeholder_created else 'reused'}")
    print(f"  no_country (cc no match): {stats.no_country}")
    print(f"  no_state_es (prov no m.): {stats.no_state_es}")
    print(f"  no_usar inactive:         {stats.no_usar}")
    print(f"  errors:                   {stats.errors}")
    if stats.error_details:
        print("  primeros 10 errores:")
        for hid, reason in stats.error_details[:10]:
            print(f"    - {hid}: {reason}")
