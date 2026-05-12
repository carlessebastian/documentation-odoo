"""Tests offline para `_partners_lib.py`.

Cubren los helpers puros (dedup_key, classify_rank, aggregate_ranks,
parse_no_usar, normalize_province, build_partner_vals) y el flujo
`load_partners` contra un FakeOdoo en memoria que simula res.partner,
res.country, res.country.state, ir.model.data.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _partners_lib import (
    PartnerStats,
    _upsert_with_vat_fallback,
    aggregate_ranks,
    build_partner_vals,
    classify_rank,
    dedup_key,
    load_partners,
    normalize_province,
    parse_no_usar,
    state_name_aliases,
)


# ---------------------------------------------------------------------------
# Fake Odoo client
# ---------------------------------------------------------------------------


class FakeOdoo:
    """Stub minimo para load_partners.

    Tablas en memoria:
      - partners: {id: vals}
      - countries: {code: id}
      - states: {id: {name, country_id}}
      - imd: list of {module, name, model, res_id}
    """

    def __init__(self, countries: dict[str, int] | None = None,
                 states: list[dict] | None = None) -> None:
        self.partners: dict[int, dict] = {}
        self.countries: dict[str, int] = countries or {}
        self.states_list: list[dict] = states or []
        self.imd: list[dict] = []
        self.next_id = 100
        self.calls: list[tuple] = []

    def call(self, model, method, args=None, kwargs=None):
        self.calls.append((model, method, args, kwargs))
        args = args or []
        kwargs = kwargs or {}
        fields = kwargs.get("fields", [])

        if model == "res.country" and method == "search_read":
            domain = args[0]
            codes = next((t[2] for t in domain if t[0] == "code"), [])
            return [
                {"code": c, "id": self.countries[c]}
                for c in codes
                if c in self.countries
            ]

        if model == "res.country.state" and method == "search_read":
            domain = args[0]
            cid = next((t[2] for t in domain if t[0] == "country_id"), None)
            return [
                {f: s.get(f) for f in fields}
                for s in self.states_list
                if s["country_id"] == cid
            ]

        if model == "res.partner" and method == "create":
            vals = args[0]
            new_id = self.next_id
            self.next_id += 1
            self.partners[new_id] = dict(vals)
            return new_id

        if model == "res.partner" and method == "write":
            ids, vals = args
            for i in ids:
                self.partners[i].update(vals)
            return True

        if model == "ir.model.data" and method == "search_read":
            domain = args[0]
            mod = next(t[2] for t in domain if t[0] == "module")
            nm = next(t[2] for t in domain if t[0] == "name")
            for entry in self.imd:
                if entry["module"] == mod and entry["name"] == nm:
                    fields_req = kwargs.get("fields", ["res_id"])
                    return [{f: entry.get(f) for f in fields_req}]
            return []

        if model == "ir.model.data" and method == "create":
            vals = args[0]
            entry = {"id": self.next_id, **vals}
            self.imd.append(entry)
            self.next_id += 1
            return entry["id"]

        raise NotImplementedError(f"{model}.{method}({args!r}, {kwargs!r})")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _make_dump(tmp_path: Path, records: list[dict]) -> Path:
    dump_dir = tmp_path / "dump"
    dump_dir.mkdir()
    _write_jsonl(dump_dir / "contacts.jsonl", records)
    return dump_dir


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestDedupKey:
    def test_with_code_and_country(self):
        assert dedup_key({"code": "B12345674", "billAddress": {"countryCode": "ES"}}) == ("ES", "B12345674")

    def test_code_uppercased(self):
        assert dedup_key({"code": "b12345674", "billAddress": {"countryCode": "es"}}) == ("ES", "B12345674")

    def test_empty_code_returns_none(self):
        assert dedup_key({"code": "", "billAddress": {"countryCode": "ES"}}) is None

    def test_placeholder_zero_returns_none(self):
        assert dedup_key({"code": "0", "billAddress": {"countryCode": "ES"}}) is None
        assert dedup_key({"code": "0000", "billAddress": {"countryCode": "ES"}}) is None

    def test_missing_country_uses_empty_string(self):
        assert dedup_key({"code": "B12345674"}) == ("", "B12345674")
        assert dedup_key({"code": "B12345674", "billAddress": {}}) == ("", "B12345674")

    def test_code_none(self):
        assert dedup_key({"code": None, "billAddress": {"countryCode": "ES"}}) is None


class TestClassifyRank:
    def test_client_type(self):
        assert classify_rank({"type": "client"}) == (1, 0)

    def test_supplier_type(self):
        assert classify_rank({"type": "supplier"}) == (0, 1)

    def test_creditor_type(self):
        assert classify_rank({"type": "creditor"}) == (0, 1)

    def test_lead_type(self):
        assert classify_rank({"type": "lead"}) == (1, 0)

    def test_empty_type_no_records(self):
        assert classify_rank({"type": None}) == (0, 0)
        assert classify_rank({"type": ""}) == (0, 0)
        assert classify_rank({}) == (0, 0)

    def test_client_with_supplier_record(self):
        # type=client + supplierRecord populado -> ambos ranks
        assert classify_rank({
            "type": "client",
            "supplierRecord": {"num": 41000000001, "name": "X"},
        }) == (1, 1)

    def test_records_without_type(self):
        # type='' pero clientRecord truthy -> cust=1
        assert classify_rank({
            "type": "",
            "clientRecord": {"num": 43000001, "name": "X"},
        }) == (1, 0)

    def test_zero_records_not_truthy(self):
        # clientRecord=0 (Holded marca asi cuando no aplica) -> rank=0
        assert classify_rank({"type": "client", "clientRecord": 0}) == (1, 0)


class TestAggregateRanks:
    def test_or_logic(self):
        assert aggregate_ranks((1, 0), (0, 1)) == (1, 1)
        assert aggregate_ranks((0, 0), (1, 0)) == (1, 0)
        assert aggregate_ranks((1, 1), (1, 1)) == (1, 1)


class TestParseNoUsar:
    def test_no_usar_marker(self):
        name, active = parse_no_usar("GOOGLE IRELAND LIMITED (NO USAR)")
        assert active is False
        assert "NO USAR" not in name
        assert "GOOGLE" in name

    def test_clean_name(self):
        assert parse_no_usar("PULSO INFORMATICA S.L.U.") == ("PULSO INFORMATICA S.L.U.", True)

    def test_none(self):
        assert parse_no_usar(None) == ("", True)


class TestNormalizeProvince:
    def test_basic(self):
        assert normalize_province("Barcelona") == "barcelona"

    def test_whitespace(self):
        assert normalize_province("  Barcelona  ") == "barcelona"
        assert normalize_province("Barcelona   ") == "barcelona"

    def test_empty(self):
        assert normalize_province("") == ""
        assert normalize_province(None) == ""

    def test_strip_diacritics(self):
        # Holded suele venir sin acentos; Odoo con acentos
        assert normalize_province("Guipuzcoa") == "guipuzcoa"
        assert normalize_province("Guipúzcoa") == "guipuzcoa"
        assert normalize_province("Álava") == "alava"


class TestStateNameAliases:
    def test_plain(self):
        assert state_name_aliases("Barcelona") == ["barcelona"]

    def test_parenthesized(self):
        # 'Bizkaia (Vizcaya)' -> bizkaia (vizcaya), bizkaia, vizcaya
        aliases = state_name_aliases("Bizkaia (Vizcaya)")
        assert "vizcaya" in aliases
        assert "bizkaia" in aliases

    def test_slash(self):
        # 'Araba/Álava' -> araba/alava, araba, alava
        aliases = state_name_aliases("Araba/Álava")
        assert "araba" in aliases
        assert "alava" in aliases  # diacritics stripped

    def test_coruna_with_la(self):
        # 'A Coruña (La Coruña)' debe match 'la coruna' (Holded sin acento)
        aliases = state_name_aliases("A Coruña (La Coruña)")
        assert "la coruna" in aliases
        assert "a coruna" in aliases

    def test_baleares_extra_alias(self):
        # Holded usa 'Baleares'; Odoo 'Illes Balears (Islas Baleares)'.
        # El alias debe estar gracias a STATE_NAME_EXTRA_ALIASES.
        aliases = state_name_aliases("Illes Balears (Islas Baleares)")
        assert "baleares" in aliases


class TestBuildPartnerVals:
    def test_basic_es_company(self):
        contact = {
            "name": "PULSO INFORMATICA S.L.U.",
            "code": "B46318895",
            "vatnumber": "",
            "type": "creditor",
            "email": "info@pulso.com",
            "phone": "961234567",
            "mobile": "",
            "isperson": 0,
            "billAddress": {
                "address": "COLON, 86",
                "city": "Valencia",
                "postalCode": "46004",
                "countryCode": "ES",
            },
            "defaults": {"language": "es"},
        }
        vals = build_partner_vals(
            contact, country_id=68, state_id=None,
            customer_rank=0, supplier_rank=1,
        )
        assert vals["name"] == "PULSO INFORMATICA S.L.U."
        assert vals["ref"] == "B46318895"
        assert vals["vat"] == "ESB46318895"
        assert vals["email"] == "info@pulso.com"
        assert vals["phone"] == "961234567"
        assert vals["street"] == "COLON, 86"
        assert vals["city"] == "Valencia"
        assert vals["zip"] == "46004"
        assert vals["country_id"] == 68
        assert vals["customer_rank"] == 0
        assert vals["supplier_rank"] == 1
        assert vals["company_type"] == "company"
        assert vals["is_company"] is True
        assert vals["active"] is True
        assert vals["lang"] == "es_ES"

    def test_no_usar_sets_inactive(self):
        contact = {
            "name": "GOOGLE IRELAND LIMITED (NO USAR)",
            "code": "IE6388047V",
            "billAddress": {"countryCode": "IE"},
        }
        vals = build_partner_vals(contact, country_id=101, state_id=None,
                                  customer_rank=0, supplier_rank=1)
        assert vals["active"] is False
        assert "NO USAR" not in vals["name"]

    def test_isperson(self):
        contact = {"name": "Juan Perez", "isperson": 1, "code": "12345678Z",
                   "billAddress": {"countryCode": "ES"}}
        vals = build_partner_vals(contact, country_id=68, state_id=None,
                                  customer_rank=1, supplier_rank=0)
        assert vals["company_type"] == "person"
        assert vals["is_company"] is False

    def test_mobile_fallback_to_phone(self):
        contact = {"name": "X", "code": "B1", "mobile": "600111222",
                   "phone": "", "billAddress": {"countryCode": "ES"}}
        vals = build_partner_vals(contact, country_id=68, state_id=None,
                                  customer_rank=1, supplier_rank=0)
        # phone vacio + mobile populado -> phone = mobile
        assert vals["phone"] == "600111222"

    def test_phone_takes_precedence(self):
        contact = {"name": "X", "code": "B1", "mobile": "600111222",
                   "phone": "911111111", "billAddress": {"countryCode": "ES"}}
        vals = build_partner_vals(contact, country_id=68, state_id=None,
                                  customer_rank=1, supplier_rank=0)
        assert vals["phone"] == "911111111"

    def test_no_vat_when_code_is_text(self):
        # SENDGRID no es un VAT VIES-able
        contact = {"name": "Sendgrid", "code": "SENDGRID",
                   "billAddress": {"countryCode": "US"}}
        vals = build_partner_vals(contact, country_id=233, state_id=None,
                                  customer_rank=0, supplier_rank=1)
        assert "vat" not in vals
        assert vals["ref"] == "SENDGRID"

    def test_non_es_code_not_used_as_vat(self):
        # Regresion: Amazon EMEA LU con code='W0185696B' nos hizo crashear
        # contra base_vat (LU exige 8 digitos). Politica: para non-ES,
        # solo usar vatnumber explicito, nunca code.
        contact = {"name": "AMAZON WEB SERVICES EMEA SARL",
                   "code": "W0185696B", "vatnumber": "",
                   "billAddress": {"countryCode": "LU"}}
        vals = build_partner_vals(contact, country_id=133, state_id=None,
                                  customer_rank=0, supplier_rank=1)
        assert "vat" not in vals
        assert vals["ref"] == "W0185696B"  # code preservado en ref

    def test_non_es_uses_vatnumber_when_present(self):
        # Si Holded SI trae vatnumber para non-ES, lo usamos
        contact = {"name": "EU SUPPLIER", "code": "FOO",
                   "vatnumber": "DE123456789",
                   "billAddress": {"countryCode": "DE"}}
        vals = build_partner_vals(contact, country_id=57, state_id=None,
                                  customer_rank=0, supplier_rank=1)
        assert vals["vat"] == "DE123456789"

    def test_no_code_no_ref(self):
        contact = {"name": "Anonymous", "code": "",
                   "billAddress": {"countryCode": "ES"}}
        vals = build_partner_vals(contact, country_id=68, state_id=None,
                                  customer_rank=1, supplier_rank=0)
        assert "ref" not in vals
        assert "vat" not in vals

    def test_fallback_name(self):
        contact = {"name": "", "code": "B1", "billAddress": {"countryCode": "ES"}}
        vals = build_partner_vals(contact, country_id=68, state_id=None,
                                  customer_rank=0, supplier_rank=1)
        assert vals["name"] == "(sin nombre)"


# ---------------------------------------------------------------------------
# load_partners orchestration
# ---------------------------------------------------------------------------


class TestLoadPartnersDryRun:
    def test_all_unique_would_create(self, tmp_path):
        records = [
            {"id": "h1", "name": "A SL", "code": "B11111111", "type": "client",
             "billAddress": {"countryCode": "ES"}},
            {"id": "h2", "name": "B SL", "code": "B22222222", "type": "supplier",
             "billAddress": {"countryCode": "ES"}},
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        stats = load_partners(
            client, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )
        # 2 canonicals + 1 placeholder (no existe en dry-run)
        assert stats.total == 2
        assert stats.would_create == 2
        assert stats.would_link == 0
        assert stats.errors == 0
        assert stats.unknown_placeholder_created is True  # would_create
        # Placeholder NO debe haberse creado en partners (dry-run)
        assert client.partners == {}

    def test_dedup_two_dups_one_canonical(self, tmp_path):
        # Mismo code, dos contacts: cliente + proveedor
        records = [
            {"id": "h1", "name": "X SL", "code": "B11111111", "type": "client",
             "billAddress": {"countryCode": "ES"}},
            {"id": "h2", "name": "X SL", "code": "B11111111", "type": "supplier",
             "billAddress": {"countryCode": "ES"}},
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        stats = load_partners(
            client, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.total == 2
        assert stats.would_create == 1  # solo canonical
        assert stats.would_link == 1    # dup
        assert stats.errors == 0

    def test_no_country_warning(self, tmp_path):
        # Contact con countryCode no presente en Odoo
        records = [
            {"id": "h1", "name": "Z", "code": "X1", "type": "client",
             "billAddress": {"countryCode": "ZZ"}},  # ZZ no existe
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        stats = load_partners(
            client, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )
        assert stats.no_country == 1
        assert stats.errors == 0  # no es error, solo warning

    def test_unique_no_code(self, tmp_path):
        records = [
            {"id": "h1", "name": "Anonymous Test", "code": "", "type": "",
             "billAddress": {"countryCode": "ES"}},
            {"id": "h2", "name": "Other test", "code": "0", "type": "",
             "billAddress": {"countryCode": "ES"}},
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        stats = load_partners(
            client, dump_dir, dry_run=True,
            report_dir=tmp_path / "reports",
        )
        # Cada uno es unique (no dedup_key)
        assert stats.would_create == 2
        assert stats.would_link == 0


class TestUpsertWithVatFallback:
    def test_no_error_passes_through(self):
        calls = []

        def fake_upsert(c, xmlid, model, vals, noupdate=False):
            calls.append(vals)
            return (42, "created")

        stats = PartnerStats()
        rid, action = _upsert_with_vat_fallback(
            fake_upsert, None, "__holded__.contact_h1",
            {"name": "X", "vat": "ESB12345674"}, stats, "h1",
        )
        assert (rid, action) == (42, "created")
        assert stats.vat_dropped == 0
        assert calls[0] == {"name": "X", "vat": "ESB12345674"}

    def test_vat_error_retries_without_vat(self):
        attempts = []

        def fake_upsert(c, xmlid, model, vals, noupdate=False):
            attempts.append(dict(vals))
            if "vat" in vals:
                raise RuntimeError(
                    "Parece que el numero IVA [W0185696B] para contacto "
                    "[AMAZON] no es valido"
                )
            return (99, "created")

        stats = PartnerStats()
        rid, action = _upsert_with_vat_fallback(
            fake_upsert, None, "__holded__.contact_h2",
            {"name": "AMAZON", "vat": "LUW0185696B"}, stats, "h2",
        )
        assert (rid, action) == (99, "created")
        assert stats.vat_dropped == 1
        assert len(attempts) == 2
        assert "vat" in attempts[0]
        assert "vat" not in attempts[1]

    def test_non_vat_error_propagates(self):
        def fake_upsert(c, xmlid, model, vals, noupdate=False):
            raise RuntimeError("Database connection lost")

        stats = PartnerStats()
        with pytest.raises(RuntimeError, match="Database"):
            _upsert_with_vat_fallback(
                fake_upsert, None, "__holded__.contact_h3",
                {"name": "X"}, stats, "h3",
            )
        assert stats.vat_dropped == 0


class TestLoadPartnersReal:
    def test_real_creates_canonical_and_links_dup(self, tmp_path):
        records = [
            {"id": "h1", "name": "X SL", "code": "B11111111", "type": "client",
             "billAddress": {"countryCode": "ES"}},
            {"id": "h2", "name": "X SL alt", "code": "B11111111", "type": "supplier",
             "billAddress": {"countryCode": "ES"}},
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        # Inyectar fake upsert (ext_id_upsert no esta en sys.path)
        import sys
        import types
        fake_mod = types.ModuleType("ext_id_upsert")

        def fake_upsert(c, xmlid, model, vals, noupdate=False):
            module, name = xmlid.split(".", 1)
            existing = c.call("ir.model.data", "search_read",
                              [[("module", "=", module), ("name", "=", name)]],
                              {"fields": ["res_id", "model"]})
            if existing:
                rid = existing[0]["res_id"]
                c.call(model, "write", [[rid], vals])
                return rid, "updated"
            rid = c.call(model, "create", [vals])
            c.call("ir.model.data", "create",
                   [{"module": module, "name": name, "model": model,
                     "res_id": rid, "noupdate": noupdate}])
            return rid, "created"

        fake_mod.upsert = fake_upsert
        sys.modules["ext_id_upsert"] = fake_mod
        try:
            stats = load_partners(
                client, dump_dir, dry_run=False,
                report_dir=tmp_path / "reports",
            )
        finally:
            del sys.modules["ext_id_upsert"]

        assert stats.canonical_create == 1
        assert stats.dup_link == 1
        assert stats.errors == 0
        # Solo 1 partner real + 1 unknown placeholder = 2
        assert len(client.partners) == 2
        # Verificar que el partner canonical tiene ambos ranks
        canonical_pid = None
        for pid, vals in client.partners.items():
            if vals.get("ref") == "B11111111":
                canonical_pid = pid
                break
        assert canonical_pid is not None
        assert client.partners[canonical_pid]["customer_rank"] == 1
        assert client.partners[canonical_pid]["supplier_rank"] == 1
        # Verificar que existen 2 ext_ids contact_<id> pointing al mismo res_id
        contact_imds = [e for e in client.imd if e["name"].startswith("contact_h")]
        assert len(contact_imds) == 2
        assert all(e["res_id"] == canonical_pid for e in contact_imds)

    def test_real_unknown_placeholder_created_once(self, tmp_path):
        records = [
            {"id": "h1", "name": "X", "code": "B1", "type": "client",
             "billAddress": {"countryCode": "ES"}},
        ]
        dump_dir = _make_dump(tmp_path, records)
        client = FakeOdoo(countries={"ES": 68})

        import sys
        import types
        fake_mod = types.ModuleType("ext_id_upsert")

        def fake_upsert(c, xmlid, model, vals, noupdate=False):
            module, name = xmlid.split(".", 1)
            existing = c.call("ir.model.data", "search_read",
                              [[("module", "=", module), ("name", "=", name)]],
                              {"fields": ["res_id", "model"]})
            if existing:
                return existing[0]["res_id"], "updated"
            rid = c.call(model, "create", [vals])
            c.call("ir.model.data", "create",
                   [{"module": module, "name": name, "model": model,
                     "res_id": rid, "noupdate": noupdate}])
            return rid, "created"

        fake_mod.upsert = fake_upsert
        sys.modules["ext_id_upsert"] = fake_mod
        try:
            load_partners(client, dump_dir, dry_run=False,
                          report_dir=tmp_path / "reports")
        finally:
            del sys.modules["ext_id_upsert"]

        # Placeholder + 1 partner canonical = 2 partners
        assert len(client.partners) == 2
        unknown_imd = [e for e in client.imd if e["name"] == "contact__unknown"]
        assert len(unknown_imd) == 1
        unknown_pid = unknown_imd[0]["res_id"]
        assert client.partners[unknown_pid]["name"] == "Cliente historico no identificado"
