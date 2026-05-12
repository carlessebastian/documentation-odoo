"""Resolvers Holded -> Odoo para el ETL inpr3mium (Fase 5.1).

Cuatro resolvers (partner, tax, journal, account) que mapean ids/keys
del dump Holded a ids reales del Odoo destino. Cada uno idempotente
y cacheado en memoria por instancia.

Las funciones a nivel de modulo (`normalize_vat`, `parse_journal_prefix`,
`derive_pgce_parent`, `partner_active_from_name`, `iso_from_unix`) son
puras y testables sin red — los tests offline solo cubren estas. La
clase `HoldedResolvers` requiere un `OdooClient` con sesion activa
contra el destino.

Diseno completo: `../migration-from-holded.md` seccion "ETL Fase 5.1
-- Diseno detallado -> Resolvers".
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Helpers puros (testables offline)
# ---------------------------------------------------------------------------

# Mapeo prefijo Holded -> account.journal.code Odoo (ids en snapshot 5.0)
JOURNAL_PREFIX_TO_CODE: dict[str, str] = {
    "A-": "A-",
    "AC-": "AC-",
    "L-": "L-",
    "FVU-": "FVU-",
    "KD-": "KD-",
    "AF-": "AF-",
    "PB-": "PB-",
    "PI-": "PI-",
    # PR- (in_refund) se genera por refund_sequence de PB-: NO se resuelve aqui.
}

# Mapeo prefijo 11-dig Holded -> codigo padre PGCE Pymes Odoo. El padre
# debe existir antes de invocar resolve_account (Fases 4.5b y 5.0
# crearon 47200/47700/47510 y 57200/52100; pasos 0a/0b de 5.1 crearan
# subcuentas 6XX/70X bajo sus padres del fallback generico).
#
# Solo listamos prefijos cuyo padre NO es trivialmente `<3digits>000`
# (e.g., IRPF 4751 -> 475100, no 475000). Para chapters 6 y 7
# (gastos/ingresos), `derive_pgce_parent` aplica fallback generico
# `<first3>000` cubriendo cualquier prefijo PGCE futuro sin necesidad
# de mantener una lista.
PGCE_PARENT_RULES: list[tuple[str, str]] = [
    # prefix      parent_code
    ("5720", "572000"),  # bancos productivos (Fase 5.0)
    ("521",  "521000"),  # tarjetas decorativas (Fase 5.0)
    ("472",  "472000"),  # HP IVA soportado (Fase 4.5b)
    ("477",  "477000"),  # HP IVA repercutido (Fase 4.5b)
    ("4751", "475100"),  # HP IRPF (Fase 4.5b) - NO termina en 000
]
# Chapters donde aplica el fallback generico `<first3>000` si no hay
# regla especifica. Mantener restringido para evitar autocrear
# subcuentas bajo padres semanticamente incorrectos en chapters
# 1XX/2XX/3XX/4XX/5XX que tienen sus propios casos especiales.
PGCE_FALLBACK_CHAPTERS: tuple[str, ...] = ("6", "7")

NO_USAR_RE = re.compile(r"\s*\(NO\s*USAR\)\s*", re.IGNORECASE)
VAT_CLEAN_RE = re.compile(r"[\s.\-_/]+")
JOURNAL_PREFIX_RE = re.compile(r"^([A-Z]+-)")


def normalize_vat(raw: Any, country: str | None = None) -> str | None:
    """Normaliza un VAT al formato `<CC><digits/letters>`.

    - Strip + upper, elimina espacios y separadores comunes.
    - Si `country` viene informado y el valor no empieza por dos letras,
      antepone `country` (mayusculas).
    - Para Espana, si despues de limpiar quedan solo digitos+letra de
      control validos, antepone `ES`.
    - Devuelve `None` si el input es falsy o queda vacio tras limpiar.
    """
    if not raw:
        return None
    s = VAT_CLEAN_RE.sub("", str(raw)).upper()
    if not s:
        return None
    # Ya viene con prefijo pais (dos letras + algo)
    if len(s) >= 3 and s[:2].isalpha():
        return s
    cc = (country or "").strip().upper()
    if cc and len(cc) == 2 and cc.isalpha():
        return cc + s
    # Heuristica ES: 8-9 char, todo digitos o digitos+letra de control
    if 8 <= len(s) <= 9 and re.fullmatch(r"[0-9A-Z]+", s):
        return "ES" + s
    return s  # devolvemos limpio aunque sin pais; loader decide aceptar/loggear


def parse_journal_prefix(doc_number: Any) -> str | None:
    """Extrae el prefijo `XX-` o `XXX-` de un docNumber Holded.

    Ejemplos:
        "A-2024-0001" -> "A-"
        "PB-1234" -> "PB-"
        "FVU-25-7" -> "FVU-"
        "123" -> None
    """
    if not doc_number:
        return None
    m = JOURNAL_PREFIX_RE.match(str(doc_number).strip().upper())
    return m.group(1) if m else None


def derive_pgce_parent(holded_code: Any) -> str | None:
    """Dada una cuenta 11-dig Holded, devuelve el codigo PGCE padre.

    Resolucion en dos pasos:
    1. Match contra `PGCE_PARENT_RULES` por prefijo mas largo. Cubre
       padres con codigo NO trivial (5720, 472, 477, 4751, 521).
    2. Fallback `<first3>000` si el primer digito esta en
       `PGCE_FALLBACK_CHAPTERS` (6, 7). Cubre cualquier subcuenta
       Holded de gastos o ingresos sin necesidad de listar prefijos
       explicitos.

    Devuelve `None` si el input no es numerico de 4-11 digitos o si
    ninguna regla casa.
    """
    if not holded_code:
        return None
    s = str(holded_code).strip()
    if not re.fullmatch(r"\d{4,11}", s):
        return None
    for prefix, parent in sorted(PGCE_PARENT_RULES, key=lambda r: -len(r[0])):
        if s.startswith(prefix):
            return parent
    if len(s) >= 3 and s[0] in PGCE_FALLBACK_CHAPTERS:
        return s[:3] + "000"
    return None


def partner_active_from_name(raw_name: Any) -> tuple[str, bool]:
    """Devuelve (`name_limpio`, `active_bool`).

    Si el nombre contiene `(NO USAR)` (Holded marca asi contactos
    bloqueados), strip la marca y devuelve `active=False`.
    """
    if raw_name is None:
        return ("", True)
    s = str(raw_name)
    if NO_USAR_RE.search(s):
        cleaned = NO_USAR_RE.sub(" ", s).strip()
        return (re.sub(r"\s+", " ", cleaned), False)
    return (s.strip(), True)


def iso_from_unix(ts: Any) -> str | None:
    """Convierte un timestamp unix (s) a `YYYY-MM-DD` en zona Europe/Madrid.

    Holded guarda fechas como medianoche local (Madrid). Si interpretamos
    en UTC, un timestamp como 1546210800 (2018-12-31 00:00 CET / 2018-12-30
    23:00 UTC) se convertiria a "2018-12-30" — fiscal year incorrecto para
    facturas de diciembre. Forzamos Europe/Madrid para preservar la fecha
    visible en la UI Holded.

    Tolera None/0/"" -> None.
    """
    if ts is None or ts == "" or ts == 0:
        return None
    try:
        n = float(ts)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Madrid")
    except Exception:
        # Fallback defensivo: usar UTC si tzdata no disponible
        tz = dt.timezone.utc
    return dt.datetime.fromtimestamp(n, tz=tz).date().isoformat()


# ---------------------------------------------------------------------------
# Resolvers (requieren OdooClient)
# ---------------------------------------------------------------------------

UNKNOWN_CONTACT_XMLID = "__holded__.contact__unknown"
EXT_MODULE = "__holded__"


@dataclass
class ResolverStats:
    partner_hits: int = 0
    partner_creates: int = 0
    partner_unknown: int = 0
    tax_hits: int = 0
    tax_reclassified: int = 0
    tax_aborts: int = 0
    journal_hits: int = 0
    account_hits: int = 0
    account_creates: int = 0
    account_aborts: int = 0


@dataclass
class HoldedResolvers:
    """Resolvers cacheados Holded -> Odoo.

    Constructor:
        client: instancia de `OdooClient` (de odoo-functional-admin).
        tax_rules: dict cargado desde `tax_reclassification.yaml`. Si
            None, se usa `{}` (ningun catch-all se reclasifica;
            unicamente lookup directo por `[holded: <key>]`).
        treasury_to_journal: dict `{treasuryId_holded: journal_id_odoo}`
            del snapshot 5.0. Usado por `loader_payments`, NO por los
            resolvers; lo guardamos aqui para compartir cache entre
            loaders.
    """

    client: Any  # OdooClient
    tax_rules: dict = field(default_factory=dict)
    treasury_to_journal: dict = field(default_factory=dict)

    _partner_cache: dict[str, int] = field(default_factory=dict)
    _partner_vat_cache: dict[str, int] = field(default_factory=dict)
    _tax_cache: dict[tuple, int] = field(default_factory=dict)
    _journal_cache: dict[str, int] = field(default_factory=dict)
    _account_cache: dict[str, int] = field(default_factory=dict)
    _unknown_partner_id: int | None = None
    stats: ResolverStats = field(default_factory=ResolverStats)

    # -- partner --------------------------------------------------------

    def resolve_partner(self, contact: dict) -> int:
        """Devuelve `res.partner.id` para un contact Holded.

        Politica (5.1):
        1. Lookup por VAT normalizado si presente.
        2. Lookup por ext_id `__holded__.contact_<id>`.
        3. Si nada, crear con ext_id; si `contact.id` ausente, devolver
           partner placeholder unico `__holded__.contact__unknown`.
        """
        cid = contact.get("id")
        xmlid = f"{EXT_MODULE}.contact_{cid}" if cid else None

        if xmlid and xmlid in self._partner_cache:
            self.stats.partner_hits += 1
            return self._partner_cache[xmlid]

        vat = normalize_vat(
            contact.get("vatnumber"),
            country=(contact.get("billAddress") or {}).get("country"),
        )
        if vat and vat in self._partner_vat_cache:
            pid = self._partner_vat_cache[vat]
            if xmlid:
                self._link_xmlid(xmlid, "res.partner", pid)
                self._partner_cache[xmlid] = pid
            self.stats.partner_hits += 1
            return pid

        # Por VAT en Odoo
        if vat:
            hits = self.client.call(
                "res.partner",
                "search_read",
                [[("vat", "=", vat)]],
                {"fields": ["id"], "limit": 1},
            )
            if hits:
                pid = hits[0]["id"]
                self._partner_vat_cache[vat] = pid
                if xmlid:
                    self._link_xmlid(xmlid, "res.partner", pid)
                    self._partner_cache[xmlid] = pid
                self.stats.partner_hits += 1
                return pid

        # Por ext_id Odoo
        if xmlid:
            pid = self._search_xmlid(xmlid)
            if pid:
                self._partner_cache[xmlid] = pid
                if vat:
                    self._partner_vat_cache[vat] = pid
                self.stats.partner_hits += 1
                return pid

        # No hay id Holded -> placeholder unico
        if not cid:
            self.stats.partner_unknown += 1
            return self._get_unknown_partner()

        # Crear nuevo. El loader_partners.py se encarga del build de vals;
        # aqui solo expone el lookup. Si el caller llega a este punto sin
        # haber creado todavia, devolver -1 para que el loader cree.
        return -1  # convencion: caller debe build_vals + create

    def _get_unknown_partner(self) -> int:
        if self._unknown_partner_id is not None:
            return self._unknown_partner_id
        pid = self._search_xmlid(UNKNOWN_CONTACT_XMLID)
        if pid:
            self._unknown_partner_id = pid
            return pid
        # Crear placeholder. Caller (loader_partners) deberia haberlo
        # creado en paso 1; si no, lo creamos aqui defensivamente.
        pid = self.client.call(
            "res.partner",
            "create",
            [{"name": "Cliente historico no identificado", "active": True}],
        )
        self._link_xmlid(UNKNOWN_CONTACT_XMLID, "res.partner", pid)
        self._unknown_partner_id = pid
        return pid

    # -- tax ------------------------------------------------------------

    def resolve_tax(self, tax_key: Any, ctx: dict | None = None) -> int:
        """Devuelve `account.tax.id` para una key Holded.

        ctx esperado: `{doc_type, partner_country, line_account_hint,
                        partner_name}`.

        1. Lookup directo por description `[holded: <key>]` (Fase 4.5b).
        2. Si la key esta en `tax_rules` (catch-all), aplicar regla.
        3. Si no, ABORT (devuelve -1 y el caller debe abortar batch).
        """
        if not tax_key:
            self.stats.tax_aborts += 1
            return -1
        key = str(tax_key).strip()
        ctx = ctx or {}
        cache_key = (key, ctx.get("doc_type"), ctx.get("partner_country"))
        if cache_key in self._tax_cache:
            self.stats.tax_hits += 1
            return self._tax_cache[cache_key]

        # 1. Reclasificacion por regla (si aplica)
        rule = (self.tax_rules or {}).get(key)
        if rule:
            mapped = self._apply_tax_rule(rule, ctx)
            if mapped > 0:
                self._tax_cache[cache_key] = mapped
                self.stats.tax_reclassified += 1
                return mapped

        # 2. Lookup directo
        hits = self.client.call(
            "account.tax",
            "search_read",
            [[("description", "ilike", f"[holded: {key}]")]],
            {"fields": ["id"], "limit": 2},
        )
        if len(hits) == 1:
            tid = hits[0]["id"]
            self._tax_cache[cache_key] = tid
            self.stats.tax_hits += 1
            return tid

        self.stats.tax_aborts += 1
        return -1  # caller decide abort batch

    def _apply_tax_rule(self, rule: dict, ctx: dict) -> int:
        """Aplica una entrada de `tax_reclassification.yaml`.

        Estructura esperada de `rule`:
            { default_tax_id: int,
              by_partner_country: { "US": tax_id, ... },
              by_partner_in: { "list_name": [tax_id, "Nombre proveedor", ...] },
              by_doc_type: { "purchase": tax_id, ... } }

        Devuelve `account.tax.id` o -1.
        """
        pc = (ctx.get("partner_country") or "").upper()
        pname = (ctx.get("partner_name") or "").upper()
        dtype = (ctx.get("doc_type") or "").lower()

        by_country = rule.get("by_partner_country") or {}
        if pc and pc in by_country:
            return int(by_country[pc])

        for _list_name, entry in (rule.get("by_partner_in") or {}).items():
            tax_id = int(entry[0])
            for needle in entry[1:]:
                if needle.upper() in pname:
                    return tax_id

        by_doc = rule.get("by_doc_type") or {}
        if dtype and dtype in by_doc:
            return int(by_doc[dtype])

        return int(rule.get("default_tax_id", -1))

    # -- journal --------------------------------------------------------

    def resolve_journal(self, doc_type: str, doc_number: Any) -> int:
        """Devuelve `account.journal.id` a partir del prefijo del docNumber.

        Si doc_type == 'purchaserefund' el caller NO debe usar este
        resolver: la creacion va por `account.move.reversal`. Aqui
        devolvemos -1 para sealar la condicion.
        """
        if doc_type == "purchaserefund":
            return -1
        prefix = parse_journal_prefix(doc_number)
        if not prefix:
            return -1
        code = JOURNAL_PREFIX_TO_CODE.get(prefix)
        if not code:
            return -1
        if code in self._journal_cache:
            self.stats.journal_hits += 1
            return self._journal_cache[code]
        hits = self.client.call(
            "account.journal",
            "search_read",
            [[("code", "=", code)]],
            {"fields": ["id"], "limit": 1},
        )
        if not hits:
            return -1
        jid = hits[0]["id"]
        self._journal_cache[code] = jid
        self.stats.journal_hits += 1
        return jid

    # -- account --------------------------------------------------------

    def resolve_account(
        self,
        holded_acct: Any,
        ctx: dict | None = None,
        autocreate: bool = True,
    ) -> int:
        """Devuelve `account.account.id` para una cuenta 11-dig Holded.

        - Si existe `code` exacto en Odoo, return.
        - Si no, y `autocreate=True`, crea como hija del PGCE parent
          (segun `derive_pgce_parent`) con account_type heredado del
          padre. ext_id `__holded__.account_<code>`.
        - Si no hay parent mapeable -> ABORT (devuelve -1).
        """
        if not holded_acct:
            return -1
        code = str(holded_acct).strip()
        if code in self._account_cache:
            self.stats.account_hits += 1
            return self._account_cache[code]

        hits = self.client.call(
            "account.account",
            "search_read",
            [[("code", "=", code)]],
            {"fields": ["id", "account_type"], "limit": 1},
        )
        if hits:
            aid = hits[0]["id"]
            self._account_cache[code] = aid
            self.stats.account_hits += 1
            return aid

        if not autocreate:
            return -1

        parent_code = derive_pgce_parent(code)
        if not parent_code:
            self.stats.account_aborts += 1
            return -1

        parent_hits = self.client.call(
            "account.account",
            "search_read",
            [[("code", "=", parent_code)]],
            {"fields": ["id", "account_type", "name"], "limit": 1},
        )
        if not parent_hits:
            self.stats.account_aborts += 1
            return -1
        parent = parent_hits[0]

        # Nombre defensivo: el loader real (0a/0b) pasara el name
        # descriptivo via override. resolve_account es fallback runtime
        # para cuentas que aparezcan en items y no esten precargadas.
        name = (ctx or {}).get("name") or f"{parent['name']} - {code}"
        aid = self.client.call(
            "account.account",
            "create",
            [
                {
                    "code": code,
                    "name": name,
                    "account_type": parent["account_type"],
                }
            ],
        )
        self._link_xmlid(f"{EXT_MODULE}.account_{code}", "account.account", aid)
        self._account_cache[code] = aid
        self.stats.account_creates += 1
        return aid

    # -- ext_id helpers -------------------------------------------------

    def _search_xmlid(self, xmlid: str) -> int | None:
        module, name = xmlid.split(".", 1)
        hits = self.client.call(
            "ir.model.data",
            "search_read",
            [[("module", "=", module), ("name", "=", name)]],
            {"fields": ["res_id"], "limit": 1},
        )
        return hits[0]["res_id"] if hits else None

    def _link_xmlid(self, xmlid: str, model: str, res_id: int) -> None:
        module, name = xmlid.split(".", 1)
        existing = self.client.call(
            "ir.model.data",
            "search_read",
            [[("module", "=", module), ("name", "=", name)]],
            {"fields": ["id"], "limit": 1},
        )
        if existing:
            return
        self.client.call(
            "ir.model.data",
            "create",
            [
                {
                    "module": module,
                    "name": name,
                    "model": model,
                    "res_id": res_id,
                    "noupdate": True,
                }
            ],
        )
