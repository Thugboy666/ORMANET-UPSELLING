"""Local web server for Ormanet Upselling (no external dependencies)."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from app.engine import (
    ABSOLUTE_MIN_MARKUP,
    CAUSALI,
    ClientInfo,
    DEFAULT_AGGRESSIVITY,
    DEFAULT_BUFFER_RIC,
    DEFAULT_MAX_DISCOUNT,
    DEFAULT_ROUNDING,
    OrderItem,
    PricingRow,
    PricingParams,
    SessionLogger,
    UpsellRow,
    compute_alt_suggestions,
    compute_upsell,
    export_excel,
    get_fixed_discount,
    load_json,
    map_macro_category,
    normalize_sku,
    resolve_ric_values,
)
from app.io_loaders import (
    DEFAULT_FIELD_MAPPING,
    DataError,
    MappingError,
    match_mapping,
    normalize_mapping,
    REQUIRED_FIELDS,
    STOCK_LISTINO_FIELDS,
    read_headers,
    load_clients,
    load_orders,
    load_stock,
)
from app.web_ui import HTML

BASE_DIR = Path(__file__).resolve().parents[1]
IMPORT_DIR = BASE_DIR / "import"
ORDERS_DIR = IMPORT_DIR / "ORDINI"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
MAPPING_PATH = CONFIG_DIR / "field_mapping.json"
RIC_OVERRIDES_PATH = CONFIG_DIR / "ric_overrides.json"
RIC_ITEM_EXCEPTIONS_PATH = CONFIG_DIR / "ric_item_exceptions.json"
ALT_SUGGESTION_LIMIT = 3


@dataclass
class AppState:
    logger: SessionLogger
    clients: list[ClientInfo] = field(default_factory=list)
    stock: dict[str, Any] = field(default_factory=dict)
    field_mapping: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    histories: list[Path] = field(default_factory=list)
    current_order: Path | None = None
    causale: str | None = CAUSALI[0]
    selected_client_id: str | None = None
    upsell_rows: list[UpsellRow] = field(default_factory=list)
    pricing_rows: list[PricingRow] = field(default_factory=list)
    pricing: PricingParams = field(default_factory=PricingParams)
    per_row_overrides: dict[str, dict] = field(default_factory=dict)
    trace: dict = field(default_factory=dict)
    validation: dict = field(default_factory=lambda: {"ok": True, "errors": []})
    warnings: list[str] = field(default_factory=list)
    copy_block: str = ""
    ric_overrides: dict[str, dict] = field(default_factory=dict)
    ric_override_errors: list[str] = field(default_factory=list)
    ric_item_exceptions: list[dict[str, Any]] = field(default_factory=list)
    alt_mode: bool = False
    alt_suggestions: list[dict[str, Any]] = field(default_factory=list)
    extra_rows: list[OrderItem] = field(default_factory=list)
    stock_alt_count: int = 0

    def reset_results(self) -> None:
        self.upsell_rows = []
        self.pricing_rows = []
        self.copy_block = ""
        self.trace = {}
        self.validation = {"ok": True, "errors": []}
        self.warnings = []
        self.per_row_overrides = {}
        self.alt_suggestions = []
        self.extra_rows = []

    def ready_to_compute(self) -> bool:
        return (
            bool(self.clients)
            and bool(self.stock)
            and len(self.histories) == 4
            and self.current_order is not None
            and self.causale in CAUSALI
            and self.selected_client_id is not None
        )

    def selected_client(self) -> ClientInfo | None:
        for client in self.clients:
            if client.client_id == self.selected_client_id:
                return client
        return None


STATE = AppState(logger=SessionLogger(LOGS_DIR))


def load_mapping_file() -> dict[str, dict[str, list[str]]]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not MAPPING_PATH.exists():
        save_mapping_file(DEFAULT_FIELD_MAPPING)
        return normalize_mapping(DEFAULT_FIELD_MAPPING)
    with MAPPING_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_mapping(data)
    return data


def save_mapping_file(mapping: dict[str, dict[str, list[str]]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with MAPPING_PATH.open("w", encoding="utf-8") as handle:
        json.dump(mapping, handle, ensure_ascii=False, indent=2)


def validate_mapping(mapping: Any) -> None:
    if not isinstance(mapping, dict):
        raise ValueError("Mapping non valido: formato non valido")
    for mapping_type, default_fields in DEFAULT_FIELD_MAPPING.items():
        section = mapping.get(mapping_type)
        if not isinstance(section, dict):
            raise ValueError(f"Mapping non valido: sezione {mapping_type} mancante")
        for field_name in default_fields:
            aliases = section.get(field_name)
            if not isinstance(aliases, list):
                raise ValueError(f"Mapping non valido: {mapping_type}.{field_name} non valido")
            if not all(isinstance(alias, str) for alias in aliases):
                raise ValueError(f"Mapping non valido: {mapping_type}.{field_name} alias non validi")


STATE.field_mapping = load_mapping_file()


def load_ric_overrides() -> dict[str, dict]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not RIC_OVERRIDES_PATH.exists():
        data = {"overrides": {}}
        save_ric_overrides(data)
        return data["overrides"]
    with RIC_OVERRIDES_PATH.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return raw.get("overrides", {})


def save_ric_overrides(payload: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with RIC_OVERRIDES_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def validate_ric_overrides(sconti: dict, overrides: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    for macro, listini in overrides.items():
        for listino_key, values in listini.items():
            defaults = sconti.get(macro, {}).get(listino_key)
            if not defaults:
                errors.append(f"Override non valida: {macro}/{listino_key} non trovato in SCONTI 2026")
                continue
            ric_exact = float(defaults.get("ric", 0.0))
            ric_floor_min = max(ABSOLUTE_MIN_MARKUP, ric_exact)
            ric_floor = float(values.get("ric_floor", ric_floor_min))
            ric_base = float(values.get("ric_base", ric_floor))
            if ric_floor < ric_floor_min:
                errors.append(
                    f"Override {macro}/{listino_key}: RIC {ric_floor:.2f}% sotto il minimo {ric_floor_min:.2f}%"
                )
            if ric_base < ric_floor:
                errors.append(
                    f"Override {macro}/{listino_key}: RIC.BASE {ric_base:.2f}% < RIC {ric_floor:.2f}%"
                )
    return errors


STATE.ric_overrides = load_ric_overrides()


def load_ric_item_exceptions() -> list[dict[str, Any]]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not RIC_ITEM_EXCEPTIONS_PATH.exists():
        payload = {"version": 1, "updated_at": datetime.utcnow().isoformat(), "items": []}
        save_ric_item_exceptions(payload["items"])
        return payload["items"]
    with RIC_ITEM_EXCEPTIONS_PATH.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []
    return items


def save_ric_item_exceptions(items: list[dict[str, Any]]) -> None:
    payload = {"version": 1, "updated_at": datetime.utcnow().isoformat(), "items": items}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with RIC_ITEM_EXCEPTIONS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def normalize_item_exception_scope(scope: str) -> str:
    value = str(scope or "all").upper().strip()
    value = value.replace("+", "")
    if value in ("", "ALL"):
        return "all"
    if value == "RIV10":
        return "RIV10"
    if value in ("RIV", "DIST"):
        return value
    return "all"


def normalize_item_exception_entry(entry: dict[str, Any]) -> dict[str, Any]:
    sku = normalize_sku(str(entry.get("sku", "")))
    scope = normalize_item_exception_scope(entry.get("scope", "all"))
    return {
        "sku": sku,
        "scope": scope,
        "ric_base_override": float(entry.get("ric_base_override", 0.0)),
        "note": str(entry.get("note", "")),
    }


def find_stock_item_by_sku(sku: str) -> Any | None:
    normalized = normalize_sku(sku)
    for code, item in STATE.stock.items():
        if normalize_sku(code) == normalized:
            return item
    return None


def listino_label_from_scope(scope: str) -> str:
    if scope == "RIV10":
        return "LISTINO RI+10%"
    if scope == "DIST":
        return "LISTINO DI"
    return "LISTINO RI"


def validate_item_exception(entry: dict[str, Any]) -> tuple[bool, str | None]:
    ric_base = float(entry.get("ric_base_override", 0.0))
    if ric_base < ABSOLUTE_MIN_MARKUP:
        return False, "RIC.BASE override deve essere ≥ 11%."
    sku = entry.get("sku", "")
    scope = entry.get("scope", "all")
    stock_item = find_stock_item_by_sku(str(sku))
    if not stock_item:
        return True, None
    try:
        sconti = load_json(CONFIG_DIR / "sconti_2026.json")
        category_map = load_json(CONFIG_DIR / "category_map.json")
        macro = map_macro_category(stock_item.categoria, category_map, STATE.logger)
        if macro == "UNKNOWN":
            return True, None
        listino_keys = ["RIV", "RIV+10", "DIST"] if scope == "all" else []
        if scope == "RIV10":
            listino_keys = ["RIV+10"]
        if scope == "RIV":
            listino_keys = ["RIV"]
        if scope == "DIST":
            listino_keys = ["DIST"]
        floors = []
        for listino_key in listino_keys:
            ric_values = resolve_ric_values(
                macro=macro,
                listino=listino_label_from_scope("RIV10" if listino_key == "RIV+10" else listino_key),
                sconti=sconti,
                ric_overrides=STATE.ric_overrides,
                item_exceptions=None,
                sku=sku,
            )
            floors.append(float(ric_values["ric_floor"]))
        floor_required = max(floors) if floors else ABSOLUTE_MIN_MARKUP
        if ric_base < floor_required:
            return False, f"RIC.BASE override {ric_base:.2f}% sotto il RIC minimo {floor_required:.2f}%."
    except Exception:
        return True, None
    return True, None


STATE.ric_item_exceptions = load_ric_item_exceptions()


def refresh_ric_override_errors() -> None:
    try:
        sconti = load_json(CONFIG_DIR / "sconti_2026.json")
    except Exception:
        STATE.ric_override_errors = ["Errore caricamento SCONTI 2026"]
        return
    STATE.ric_override_errors = validate_ric_overrides(sconti, STATE.ric_overrides)


refresh_ric_override_errors()


def list_orders() -> dict[str, list[str]]:
    storico = sorted([path.name for path in ORDERS_DIR.glob("STORICO-*.xlsx")])
    upsell = sorted([path.name for path in ORDERS_DIR.glob("UPSELL-*.xlsx")])
    return {"storico": storico, "upsell": upsell}


def load_current_items(logger: SessionLogger) -> list[OrderItem]:
    if STATE.current_order is None:
        return []
    items = load_orders([STATE.current_order], logger, STATE.field_mapping.get("ORDINI", {}))
    existing_codes = {item.codice for item in items}
    for extra in STATE.extra_rows:
        if extra.codice in existing_codes:
            continue
        items.append(extra)
    return items


def build_pricing_limits(pricing_rows: list[PricingRow], trace: dict) -> dict[str, float | None]:
    if not pricing_rows:
        rows = trace.get("rows", []) if isinstance(trace, dict) else []
        if not rows:
            return {
                "max_discount_real_min": None,
                "max_discount_real_max": None,
                "buffer_ric_example": None,
            }
        max_discounts = [
            float(row.get("max_discount_real_pct", row.get("max_discount_real", 0.0)))
            for row in rows
        ]
        buffer_values = [float(row.get("buffer_ric", 0.0)) for row in rows]
        return {
            "max_discount_real_min": min(max_discounts),
            "max_discount_real_max": max(max_discounts),
            "buffer_ric_example": buffer_values[0] if buffer_values else None,
        }
    caps = [row.sconto_cap for row in pricing_rows]
    return {
        "max_discount_real_min": min(caps) if caps else None,
        "max_discount_real_max": max(caps) if caps else None,
        "buffer_ric_example": None,
    }


def build_ric_table(sconti: dict, overrides: dict[str, dict]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for macro, listini in sconti.items():
        for listino_key, values in listini.items():
            ric_base_default = values.get("ric_base")
            ric_floor_default = values.get("ric")
            if ric_base_default is None:
                continue
            ric_floor_min = max(ABSOLUTE_MIN_MARKUP, float(ric_floor_default))
            override = overrides.get(macro, {}).get(listino_key, {})
            ric_base = float(override.get("ric_base", ric_base_default))
            ric_floor = float(override.get("ric_floor", ric_floor_default))
            source = "override" if override else "default"
            note = override.get("note", "")
            rows.append(
                {
                    "categoria": macro,
                    "listino": listino_key,
                    "ric_base": ric_base,
                    "ric_floor": ric_floor,
                    "ric_base_default": ric_base_default,
                    "ric_floor_default": ric_floor_default,
                    "ric_floor_min": ric_floor_min,
                    "source": source,
                    "note": note,
                    "note_default": "",
                }
            )
    return rows


def build_ric_example(trace: dict) -> str:
    rows = trace.get("rows", []) if isinstance(trace, dict) else []
    if not rows:
        return "Esempio: LM 0,00 – RIC.BASE 0% -> 0,00; RIC minimo 0% -> 0,00; sconto massimo consentito ~ 0,0%."
    row = rows[0]
    lm = float(row.get("lm", 0.0))
    ric_base = float(row.get("ric_base", 0.0))
    ric_floor = float(row.get("ric_floor", 0.0))
    baseline = float(row.get("baseline_price", 0.0))
    floor = float(row.get("floor_price", 0.0))
    max_discount = float(row.get("max_discount_real_pct", row.get("max_discount_real", 0.0)))
    return (
        f"Esempio: LM {lm:.2f} – RIC.BASE {ric_base:.0f}% -> {baseline:.2f}; "
        f"RIC minimo {ric_floor:.0f}% -> {floor:.2f}; sconto massimo consentito ~ {max_discount:.1f}%."
    )


def build_copy_block(rows: list[UpsellRow], client: ClientInfo, order_name: str, causale: str) -> str:
    def format_optional(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "-"

    lines = [
        f"Cliente: {client.ragione_sociale} (ID: {client.client_id}, Listino: {client.listino})",
        f"Ordine: {order_name}",
        f"Causale: {causale}",
        "Righe Upsell:",
    ]
    for row in rows:
        note = row.note or row.clamp_reason or "-"
        lines.append(
            f"- {row.codice} | {row.descrizione} | {row.qty} | LM {row.lm:.2f} | "
            f"Sconto% {row.desired_discount_pct:.2f} | Prezzo {row.prezzo_unit:.2f} | "
            f"Ric% {row.final_ric_percent:.2f} | "
            f"Ric min% {format_optional(row.required_ric)} | {row.totale:.2f} | Disp {row.disp} | "
            f"Disponibile dal {row.disponibile_dal or '-'} | Note {note}"
        )
    return "\n".join(lines)


def serialize_alt_suggestions(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "codice": row.codice,
            "descrizione": row.descrizione,
            "categoria": row.categoria,
            "marca": row.marca,
            "prezzo_alt": row.prezzo_alt,
            "qty": row.qty,
        }
        for row in rows
    ]


def serialize_rows(rows: list[UpsellRow]) -> list[dict[str, Any]]:
    return [
        {
            "codice": row.codice,
            "descrizione": row.descrizione,
            "qty": row.qty,
            "prezzo_unit": row.prezzo_unit,
            "lm": row.lm,
            "prezzo_alt": row.prezzo_alt,
            "alt_available": row.alt_available,
            "alt_selected": row.alt_selected,
            "macro_categoria": row.macro_categoria,
            "fixed_discount_percent": row.fixed_discount_percent,
            "ric_base": row.ric_base,
            "ric_base_source": row.ric_base_source,
            "ric_floor_source": row.ric_floor_source,
            "item_exception_hit": row.item_exception_hit,
            "customer_base_price": row.customer_base_price,
            "max_discount_real": row.max_discount_real,
            "max_discount_real_pct": row.max_discount_real_pct,
            "max_discount_effective": row.max_discount_effective,
            "max_discount_effective_pct": row.max_discount_effective_pct,
            "desired_discount_pct": row.desired_discount_pct,
            "applied_discount_pct": row.applied_discount_pct,
            "final_ric_percent": row.final_ric_percent,
            "required_ric": row.required_ric,
            "totale": row.totale,
            "disp": row.disp,
            "disponibile_dal": row.disponibile_dal or "",
            "clamp_reason": row.clamp_reason,
            "note": row.note,
            "min_unit_price": row.min_unit_price,
        }
        for row in rows
    ]


def serialize_pricing_rows(rows: list[PricingRow]) -> list[dict[str, Any]]:
    return [
        {
            "codice": row.codice,
            "descrizione": row.descrizione,
            "categoria": row.categoria,
            "lm": row.lm,
            "ric_base": row.ric_base,
            "ric_min": row.ric_min,
            "sconto_fisso": row.sconto_fisso,
            "prezzo_base": row.prezzo_base,
            "prezzo_min": row.prezzo_min,
            "sconto_richiesto": row.sconto_richiesto,
            "sconto_cap": row.sconto_cap,
            "sconto_effettivo": row.sconto_effettivo,
            "prezzo_finale": row.prezzo_finale,
            "ric_effettivo": row.ric_effettivo,
            "fonte_cap": row.fonte_cap,
        }
        for row in rows
    ]


def build_quote_payload(order_name: str) -> dict[str, Any]:
    pricing_limits = build_pricing_limits(STATE.pricing_rows, STATE.trace)
    allowed_cap = pricing_limits.get("max_discount_real_min")
    if pricing_limits.get("buffer_ric_example") is not None:
        STATE.pricing.buffer_ric = float(pricing_limits["buffer_ric_example"])
    client = STATE.selected_client()
    if client is None:
        raise ValueError("Cliente non selezionato")
    STATE.copy_block = build_copy_block(STATE.upsell_rows, client, order_name, STATE.causale or "")
    rows = STATE.upsell_rows
    non_alt_rows = [row for row in rows if not row.alt_selected]
    alt_rows = [row for row in rows if row.alt_selected]
    totals_lines = len(rows)
    total_qty = sum(row.qty for row in rows)
    subtotal_final_exvat = sum(row.prezzo_unit * row.qty for row in rows)
    subtotal_alt_exvat = sum(row.prezzo_unit * row.qty for row in alt_rows)
    subtotal_non_alt_final_exvat = sum(row.prezzo_unit * row.qty for row in non_alt_rows)
    subtotal_baseline_exvat = sum(row.customer_base_price * row.qty for row in non_alt_rows)
    savings_vs_baseline_exvat = (
        subtotal_baseline_exvat - subtotal_non_alt_final_exvat if non_alt_rows else None
    )
    non_alt_ric_values = [row.final_ric_percent for row in non_alt_rows]
    min_final_ric_non_alt = min(non_alt_ric_values) if non_alt_ric_values else None
    max_final_ric_non_alt = max(non_alt_ric_values) if non_alt_ric_values else None
    avg_final_ric_non_alt = (
        sum(row.final_ric_percent * row.qty for row in non_alt_rows)
        / sum(row.qty for row in non_alt_rows)
        if non_alt_rows
        else None
    )
    summary_warnings: list[str] = []
    if abs(subtotal_final_exvat - (subtotal_alt_exvat + subtotal_non_alt_final_exvat)) > 0.01:
        summary_warnings.append(
            "⚠ Controllo: totale imponibile non coerente con la somma ALT + NON-ALT."
        )
    numeric_checks = {
        "totale_imponibile": subtotal_final_exvat,
        "totale_alt": subtotal_alt_exvat,
        "totale_non_alt": subtotal_non_alt_final_exvat,
        "baseline_non_alt": subtotal_baseline_exvat,
        "pezzi": total_qty,
    }
    if any((not math.isfinite(value)) for value in numeric_checks.values()):
        summary_warnings.append(
            "⚠ Controllo: valori incoerenti rilevati (verifica prezzi/qty)."
        )
    if any(value < -0.01 for value in numeric_checks.values()):
        summary_warnings.append(
            "⚠ Controllo: valori negativi inattesi rilevati (verifica prezzi/qty)."
        )
    ric_checks = [min_final_ric_non_alt, max_final_ric_non_alt, avg_final_ric_non_alt]
    if any(value is not None and not math.isfinite(value) for value in ric_checks):
        summary_warnings.append(
            "⚠ Controllo: margini NON-ALT incoerenti (verifica prezzi/qty)."
        )
    discrepancies: list[dict[str, Any]] = []
    for row in non_alt_rows:
        if row.min_unit_price is not None and row.prezzo_unit < row.min_unit_price:
            discrepancies.append(
                {
                    "type": "MIN_RIC_FLOOR",
                    "sku": row.codice,
                    "message": (
                        f"{row.codice}: prezzo {row.prezzo_unit:.2f} sotto minimo "
                        f"{row.min_unit_price:.2f} (RIC {row.required_ric:.2f}%)."
                    ),
                }
            )
    for row in rows:
        if row.alt_selected and not row.alt_available:
            discrepancies.append(
                {
                    "type": "ALT_MISSING",
                    "sku": row.codice,
                    "message": f"{row.codice}: ALT selezionato ma PREZZO_ALT assente.",
                }
            )
    has_blocking_issues = bool(discrepancies)
    response = {
        "ok": True,
        "success": True,
        "quote": serialize_rows(rows),
        "pricing_rows": serialize_pricing_rows(STATE.pricing_rows),
        "trace": STATE.trace,
        "warnings": STATE.warnings,
        "validation": STATE.validation,
        "ric_override_errors": STATE.ric_override_errors,
        "copy_block": STATE.copy_block,
        "totals": {
            "lines_count": totals_lines,
            "total_qty": total_qty,
            "subtotal_final_exvat": subtotal_final_exvat,
            "subtotal_alt_exvat": subtotal_alt_exvat,
            "subtotal_non_alt_final_exvat": subtotal_non_alt_final_exvat,
            "subtotal_baseline_non_alt_exvat": subtotal_baseline_exvat if non_alt_rows else None,
            "savings_vs_baseline_non_alt_exvat": savings_vs_baseline_exvat,
            "min_final_ric_non_alt": min_final_ric_non_alt,
            "avg_final_ric_non_alt": avg_final_ric_non_alt,
            "max_final_ric_non_alt": max_final_ric_non_alt,
        },
        "discrepancies": discrepancies,
        "summary_warnings": summary_warnings,
        "has_blocking_issues": has_blocking_issues,
        "pricing": {
            "aggressivity": STATE.pricing.aggressivity,
            "aggressivity_mode": STATE.pricing.aggressivity_mode,
            "max_discount_percent": STATE.pricing.max_discount_percent,
            "buffer_ric": STATE.pricing.buffer_ric,
            "rounding": STATE.pricing.rounding,
        },
        "pricing_limits": pricing_limits,
        "global_max_sconto_allowed_pct": allowed_cap,
        "alt_mode": STATE.alt_mode,
        "alt_suggestions": serialize_alt_suggestions(STATE.alt_suggestions),
    }
    return response


def compute_and_update(
    *,
    historical_items: list[OrderItem],
    current_items: list[OrderItem],
    sconti: dict,
    category_map: dict,
    client: ClientInfo,
) -> None:
    (
        STATE.upsell_rows,
        STATE.pricing_rows,
        STATE.trace,
        STATE.validation,
        STATE.warnings,
    ) = compute_upsell(
        current_items=current_items,
        historical_items=historical_items,
        stock=STATE.stock,
        client=client,
        sconti=sconti,
        category_map=category_map,
        pricing=STATE.pricing,
        causale=STATE.causale or CAUSALI[0],
        logger=STATE.logger,
        overrides=STATE.per_row_overrides,
        ric_overrides=STATE.ric_overrides,
        item_exceptions=STATE.ric_item_exceptions,
    )
    if STATE.alt_mode and STATE.stock_alt_count > 0:
        STATE.alt_suggestions = compute_alt_suggestions(
            stock_items=STATE.stock,
            storico_items=historical_items,
            current_rows=STATE.upsell_rows,
            category_map=category_map,
            logger=STATE.logger,
            limit=ALT_SUGGESTION_LIMIT,
        )
        STATE.logger.info("Suggerimenti ALT generati: %s", len(STATE.alt_suggestions))
    else:
        STATE.alt_suggestions = []


class RequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/api/status":
            refresh_ric_override_errors()
            orders = list_orders()
            histories_selected = [path.name for path in STATE.histories]
            histories_count = len(histories_selected)
            self._send_json(
                {
                    "clients_loaded": bool(STATE.clients),
                    "stock_loaded": bool(STATE.stock),
                    "histories_loaded": histories_count == 4,
                    "histories_selected_count": histories_count,
                    "histories_selected": histories_selected,
                    "histories_ok": histories_count == 4,
                    "order_loaded": STATE.current_order is not None,
                    "causale_set": STATE.causale in CAUSALI,
                    "client_selected": STATE.selected_client_id is not None,
                    "ready_to_compute": STATE.ready_to_compute(),
                    "has_results": bool(STATE.upsell_rows),
                    "clients": [
                        {
                            "value": client.client_id,
                            "label": f"{client.client_id} - {client.ragione_sociale}",
                        }
                        for client in STATE.clients
                    ],
                    "upsell_orders": [{"value": name, "label": name} for name in orders["upsell"]],
                    "storico_orders": [{"value": name, "label": name} for name in orders["storico"]],
                    "selected_client": STATE.selected_client_id or "",
                    "selected_order": STATE.current_order.name if STATE.current_order else "",
                    "selected_histories": histories_selected,
                    "causale": STATE.causale or "",
                    "pricing": {
                        "aggressivity": STATE.pricing.aggressivity,
                        "aggressivity_mode": STATE.pricing.aggressivity_mode,
                        "max_discount_percent": STATE.pricing.max_discount_percent,
                        "buffer_ric": STATE.pricing.buffer_ric,
                        "rounding": STATE.pricing.rounding,
                    },
                    "alt_mode": STATE.alt_mode,
                    "alt_available_count": STATE.stock_alt_count,
                    "validation_ok": STATE.validation.get("ok", True),
                    "ric_overrides_ok": len(STATE.ric_override_errors) == 0,
                    "ric_override_errors": STATE.ric_override_errors,
                }
            )
            return

        payload = self._read_json()
        if self.path == "/api/load":
            try:
                STATE.reset_results()
                clients_path = IMPORT_DIR / "CLIENTI.xlsx"
                stock_path = IMPORT_DIR / "STOCK.xlsx"
                if not clients_path.exists() or not stock_path.exists():
                    missing = []
                    if not clients_path.exists():
                        missing.append("CLIENTI.xlsx")
                    if not stock_path.exists():
                        missing.append("STOCK.xlsx")
                    self._send_json(
                        {
                            "success": False,
                            "error": f"File mancanti: {', '.join(missing)}",
                        },
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                STATE.clients = load_clients(
                    clients_path, STATE.logger, STATE.field_mapping.get("CLIENTI", {})
                )
                STATE.stock = load_stock(
                    stock_path, STATE.logger, STATE.field_mapping.get("STOCK", {})
                )
                STATE.stock_alt_count = sum(
                    1
                    for item in STATE.stock.values()
                    if item.prezzo_alt is not None and item.prezzo_alt > 0
                )
                STATE.logger.info(
                    "Prodotti altovendenti trovati: %s",
                    STATE.stock_alt_count,
                )
                self._send_json(
                    {"success": True, "message": "Clienti e stock caricati"},
                )
            except (MappingError, DataError) as exc:
                STATE.logger.error("Errore mapping", error_type="mapping_error", details=exc.details)
                self._send_json(
                    {
                        "ok": False,
                        "error": "mapping_or_data_error",
                        "message": str(exc),
                        "details": exc.details,
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:
                STATE.logger.error("Errore caricamento default", error=str(exc))
                self._send_json(
                    {"success": False, "error": f"Errore caricamento: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/select_client":
            client_id = payload.get("client_id", "")
            if client_id:
                STATE.selected_client_id = client_id
            self._send_json({"success": True})
            return

        if self.path == "/api/set_order":
            order_name = payload.get("order_name", "")
            if order_name:
                order_path = ORDERS_DIR / order_name
                STATE.current_order = order_path if order_path.exists() else None
                STATE.reset_results()
            self._send_json({"success": True})
            return

        if self.path == "/api/set_histories":
            histories = payload.get("histories", payload.get("files", []))
            if isinstance(histories, str):
                histories = [histories]
            if not isinstance(histories, list):
                histories = []
            cleaned: list[str] = []
            invalid_names: list[str] = []
            for name in histories:
                if not isinstance(name, str) or not name:
                    continue
                candidate = Path(name)
                if candidate.is_absolute() or ".." in candidate.parts or candidate.name != name:
                    invalid_names.append(name)
                    continue
                cleaned.append(candidate.name)
            if invalid_names:
                self._send_json(
                    {
                        "ok": False,
                        "error": "invalid_names",
                        "invalid": invalid_names,
                        "received": histories,
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if len(cleaned) > 4:
                self._send_json(
                    {
                        "ok": False,
                        "error": "too_many_files",
                        "max": 4,
                        "count": len(cleaned),
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            paths = [ORDERS_DIR / name for name in cleaned]
            missing = [path.name for path in paths if not path.exists()]
            if missing:
                self._send_json(
                    {
                        "ok": False,
                        "error": "missing_files",
                        "missing": missing,
                        "received": cleaned,
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            STATE.histories = paths
            STATE.reset_results()
            self._send_json(
                {
                    "ok": True,
                    "selected": cleaned,
                    "count": len(cleaned),
                }
            )
            return

        if self.path == "/api/set_causale":
            causale = payload.get("causale")
            if causale in CAUSALI:
                STATE.causale = causale
                STATE.reset_results()
            self._send_json({"success": True})
            return

        if self.path == "/api/set_alt_mode":
            STATE.alt_mode = bool(payload.get("alt_mode"))
            if not STATE.alt_mode:
                for override in STATE.per_row_overrides.values():
                    override.pop("alt_selected", None)
            self._send_json({"ok": True, "alt_mode": STATE.alt_mode})
            return

        if self.path == "/api/set_aggressivita":
            aggressivita = payload.get("aggressivita", 0)
            try:
                STATE.pricing.aggressivity = float(aggressivita)
                STATE.reset_results()
            except (TypeError, ValueError):
                pass
            self._send_json({"success": True})
            return

        if self.path == "/api/compute":
            if not STATE.ready_to_compute():
                self._send_json(
                    {
                        "success": False,
                        "error": "Completa clienti, stock, 4 storici, ordine upsell, causale e cliente.",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                category_map = load_json(CONFIG_DIR / "category_map.json")
                refresh_ric_override_errors()
                historical_items = load_orders(
                    STATE.histories, STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                STATE.per_row_overrides = {}
                STATE.extra_rows = []
                STATE.pricing = PricingParams(
                    aggressivity=DEFAULT_AGGRESSIVITY,
                    aggressivity_mode="discount_from_baseline",
                    max_discount_percent=None,
                    buffer_ric=DEFAULT_BUFFER_RIC,
                    rounding=DEFAULT_ROUNDING,
                )
                current_items = load_current_items(STATE.logger)
                compute_and_update(
                    historical_items=historical_items,
                    current_items=current_items,
                    sconti=sconti,
                    category_map=category_map,
                    client=client,
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                self._send_json(build_quote_payload(order_name))
            except (MappingError, DataError) as exc:
                STATE.logger.error("Errore mapping", error_type="mapping_error", details=exc.details)
                self._send_json(
                    {
                        "ok": False,
                        "error": "mapping_or_data_error",
                        "message": str(exc),
                        "details": exc.details,
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:
                STATE.logger.error("Errore calcolo upsell", error=str(exc))
                self._send_json(
                    {"success": False, "error": f"Errore calcolo: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/recalc":
            if not STATE.ready_to_compute():
                self._send_json(
                    {
                        "ok": False,
                        "error": "Completa clienti, stock, 4 storici, ordine upsell, causale e cliente.",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                global_params = payload.get("global_params", {})
                overrides = payload.get("per_row_overrides", {})
                if isinstance(global_params, dict):
                    alt_mode = global_params.get("alt_mode")
                    if alt_mode is not None:
                        STATE.alt_mode = bool(alt_mode)
                        if not STATE.alt_mode:
                            for override in STATE.per_row_overrides.values():
                                override.pop("alt_selected", None)
                    rounding_value = global_params.get("rounding", STATE.pricing.rounding)
                    if rounding_value in ("NONE", "", None):
                        rounding_value = None
                    else:
                        rounding_value = float(rounding_value)
                    raw_max_discount = global_params.get("max_discount_percent")
                    max_discount_value = None if raw_max_discount in ("", None) else float(raw_max_discount)
                    STATE.pricing = PricingParams(
                        aggressivity=float(global_params.get("aggressivity", STATE.pricing.aggressivity)),
                        aggressivity_mode=global_params.get(
                            "aggressivity_mode", STATE.pricing.aggressivity_mode
                        ),
                        max_discount_percent=max_discount_value,
                        buffer_ric=float(global_params.get("buffer_ric", STATE.pricing.buffer_ric)),
                        rounding=rounding_value,
                    )
                if isinstance(overrides, dict):
                    STATE.per_row_overrides = overrides
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                category_map = load_json(CONFIG_DIR / "category_map.json")
                refresh_ric_override_errors()
                historical_items = load_orders(
                    STATE.histories, STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                current_items = load_current_items(STATE.logger)
                compute_and_update(
                    historical_items=historical_items,
                    current_items=current_items,
                    sconti=sconti,
                    category_map=category_map,
                    client=client,
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                payload = build_quote_payload(order_name)
                payload.pop("pricing", None)
                payload.pop("success", None)
                self._send_json(payload)
            except Exception as exc:
                STATE.logger.error("Errore recalcolo upsell", error=str(exc))
                self._send_json(
                    {"ok": False, "error": f"Errore recalcolo: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/alt/add":
            if not STATE.ready_to_compute():
                self._send_json(
                    {"ok": False, "error": "Dati non pronti."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            sku = str(payload.get("sku", "")).strip()
            qty = payload.get("qty", 1)
            if not sku:
                self._send_json(
                    {"ok": False, "error": "SKU mancante."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            stock_item = STATE.stock.get(sku)
            if not stock_item or stock_item.prezzo_alt is None or stock_item.prezzo_alt <= 0:
                self._send_json(
                    {"ok": False, "error": "PREZZO_ALT non disponibile per questo SKU."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            current_items = load_current_items(STATE.logger)
            if any(item.codice == sku for item in current_items):
                self._send_json(
                    {"ok": False, "error": "SKU già presente nel preventivo."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                qty_value = max(1.0, float(qty))
            except (TypeError, ValueError):
                qty_value = 1.0
            STATE.extra_rows.append(
                OrderItem(
                    marca=stock_item.marca,
                    categoria=stock_item.categoria,
                    codice=stock_item.codice,
                    descrizione=stock_item.descrizione,
                    qty=qty_value,
                    prezzo_unit=0.0,
                    lm=stock_item.lm,
                    source_file="ALT",
                    source_row=None,
                )
            )
            override = STATE.per_row_overrides.get(sku, {})
            override["qty"] = qty_value
            override["alt_selected"] = True
            STATE.per_row_overrides[sku] = override
            try:
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                category_map = load_json(CONFIG_DIR / "category_map.json")
                historical_items = load_orders(
                    STATE.histories, STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                current_items = load_current_items(STATE.logger)
                compute_and_update(
                    historical_items=historical_items,
                    current_items=current_items,
                    sconti=sconti,
                    category_map=category_map,
                    client=client,
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                self._send_json(build_quote_payload(order_name))
            except Exception as exc:
                STATE.logger.error("Errore aggiunta ALT", error=str(exc))
                self._send_json(
                    {"ok": False, "error": f"Errore aggiunta ALT: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/min_price":
            if not STATE.ready_to_compute():
                self._send_json(
                    {"ok": False, "error": "Dati non pronti."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            sku = payload.get("sku")
            if not sku:
                self._send_json(
                    {"ok": False, "error": "SKU mancante."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            stock_item = STATE.stock.get(str(sku))
            if not stock_item:
                self._send_json(
                    {"ok": False, "error": "SKU non trovato."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            try:
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                category_map = load_json(CONFIG_DIR / "category_map.json")
                macro = map_macro_category(stock_item.categoria, category_map, STATE.logger)
                if macro == "UNKNOWN":
                    raise ValueError("Categoria non riconosciuta")
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                ric_values = resolve_ric_values(
                    macro=macro,
                    listino=client.listino,
                    sconti=sconti,
                    ric_overrides=STATE.ric_overrides,
                    item_exceptions=STATE.ric_item_exceptions,
                    sku=sku,
                )
                ric_floor = float(ric_values["ric_floor"])
                ric_base = float(ric_values["ric_base"])
                ric_base_source = str(ric_values["ric_base_source"])
                ric_floor_source = str(ric_values["ric_floor_source"])
                item_exception_hit = bool(ric_values["item_exception_hit"])
                if stock_item.lm <= 0:
                    raise ValueError("LM mancante")
                fixed_discount = get_fixed_discount(macro, client.listino, sconti)
                baseline_price = stock_item.lm * (1 + ric_base / 100)
                min_unit_price = stock_item.lm * (1 + ric_floor / 100)
                max_discount_real = (
                    1 - (min_unit_price / baseline_price) if baseline_price else 0.0
                ) * 100
                self._send_json(
                    {
                        "ok": True,
                        "sku": sku,
                        "min_unit_price": min_unit_price,
                        "required_ric": ric_floor,
                        "lm": stock_item.lm,
                        "fixed_discount_percent": fixed_discount,
                        "customer_base_price": baseline_price,
                        "ric_base": ric_base,
                        "ric_base_source": ric_base_source,
                        "ric_floor_source": ric_floor_source,
                        "item_exception_hit": item_exception_hit,
                        "max_discount_real_pct": max_discount_real,
                    }
                )
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"Errore calcolo: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/export":
            if not STATE.upsell_rows:
                self._send_json(
                    {"success": False, "error": "Nessuna riga da esportare."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if STATE.ric_override_errors:
                self._send_json(
                    {
                        "success": False,
                        "error": "Override RIC non valide: correggi prima dell'export.",
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            if not STATE.validation.get("ok", True):
                self._send_json(
                    {"success": False, "error": "Correggi le righe con errore prima dell'export."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                order_name = STATE.current_order.name if STATE.current_order else ""
                output_path = export_excel(STATE.upsell_rows, client, order_name, OUTPUT_DIR)
                self._send_json(
                    {"success": True, "message": f"Export completato: {output_path}"},
                )
            except Exception as exc:
                STATE.logger.error("Errore export", error=str(exc))
                self._send_json(
                    {"success": False, "error": f"Errore export: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/open_output":
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                if os.name == "nt":
                    os.startfile(OUTPUT_DIR)  # noqa: S606 - Windows only
                else:
                    subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
            except Exception as exc:
                STATE.logger.error("Errore apertura output", error=str(exc))
            self._send_json({"success": True})
            return

        if self.path == "/api/mapping/get":
            self._send_json({"ok": True, "mapping": STATE.field_mapping})
            return

        if self.path == "/api/mapping/load":
            try:
                STATE.field_mapping = load_mapping_file()
                self._send_json({"ok": True, "mapping": STATE.field_mapping})
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": "invalid_mapping", "message": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )
            return

        if self.path == "/api/mapping/save":
            incoming = payload.get("mapping", payload)
            try:
                validate_mapping(incoming)
                STATE.field_mapping = incoming
                save_mapping_file(incoming)
                self._send_json({"ok": True, "mapping": STATE.field_mapping})
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": "invalid_mapping", "message": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )
            return

        if self.path == "/api/mapping/reset":
            STATE.field_mapping = normalize_mapping(DEFAULT_FIELD_MAPPING)
            save_mapping_file(STATE.field_mapping)
            self._send_json({"ok": True, "mapping": STATE.field_mapping})
            return

        if self.path == "/api/mapping/test":
            incoming = payload.get("mapping")
            mapping = STATE.field_mapping
            if incoming is not None:
                try:
                    validate_mapping(incoming)
                    mapping = incoming
                except Exception as exc:
                    self._send_json(
                        {"ok": False, "error": "invalid_mapping", "message": str(exc)},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
            results: dict[str, Any] = {"ORDINI": [], "STOCK": [], "CLIENTI": []}
            missing_files: list[str] = []

            order_files = [path for path in STATE.histories if path is not None]
            if STATE.current_order is not None:
                order_files.append(STATE.current_order)
            if not order_files:
                order_files = list(ORDERS_DIR.glob("*.xlsx"))[:1]
            if not order_files:
                missing_files.append("ORDINI/*.xlsx")

            for path in order_files:
                if not path.exists():
                    missing_files.append(path.name)
                    continue
                headers = read_headers(path)
                matches, _ = match_mapping(headers, mapping.get("ORDINI", {}))
                missing_required = [
                    field for field in REQUIRED_FIELDS["ORDINI"] if not matches.get(field)
                ]
                results["ORDINI"].append(
                    {
                        "file": path.name,
                        "matches": matches,
                        "missing_required": missing_required,
                    }
                )

            clients_path = IMPORT_DIR / "CLIENTI.xlsx"
            if clients_path.exists():
                headers = read_headers(clients_path)
                matches, _ = match_mapping(headers, mapping.get("CLIENTI", {}))
                missing_required = [
                    field for field in REQUIRED_FIELDS["CLIENTI"] if not matches.get(field)
                ]
                results["CLIENTI"].append(
                    {
                        "file": clients_path.name,
                        "matches": matches,
                        "missing_required": missing_required,
                    }
                )
            else:
                missing_files.append("CLIENTI.xlsx")

            stock_path = IMPORT_DIR / "STOCK.xlsx"
            if stock_path.exists():
                headers = read_headers(stock_path)
                matches, _ = match_mapping(headers, mapping.get("STOCK", {}))
                missing_required = [
                    field for field in REQUIRED_FIELDS["STOCK"] if not matches.get(field)
                ]
                has_listino = any(matches.get(field) for field in STOCK_LISTINO_FIELDS)
                if not has_listino:
                    missing_required.append("listino_ri|listino_ri10|listino_di")
                results["STOCK"].append(
                    {
                        "file": stock_path.name,
                        "matches": matches,
                        "missing_required": missing_required,
                    }
                )
            else:
                missing_files.append("STOCK.xlsx")

            if missing_files:
                self._send_json(
                    {"ok": False, "error": "missing_files", "missing": missing_files, "results": results},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            self._send_json({"ok": True, "results": results})
            return

        if self.path == "/api/ric/get_overrides":
            try:
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                refresh_ric_override_errors()
                rows = build_ric_table(sconti, STATE.ric_overrides)
                example = build_ric_example(STATE.trace)
                self._send_json(
                    {
                        "ok": True,
                        "rows": rows,
                        "example": example,
                        "override_errors": STATE.ric_override_errors,
                    }
                )
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"Errore caricamento RIC: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/ric/item_exceptions/list":
            items = sorted(
                STATE.ric_item_exceptions,
                key=lambda item: (normalize_sku(str(item.get("sku", ""))), str(item.get("scope", ""))),
            )
            self._send_json({"ok": True, "items": items})
            return

        if self.path == "/api/ric/item_exceptions/add":
            incoming = normalize_item_exception_entry(payload)
            if not incoming.get("sku"):
                self._send_json(
                    {"ok": False, "error": "SKU mancante."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            valid, error = validate_item_exception(incoming)
            if not valid:
                self._send_json({"ok": False, "error": error}, status=HTTPStatus.BAD_REQUEST)
                return
            key = (incoming["sku"], incoming["scope"])
            if any(
                normalize_sku(str(item.get("sku", ""))) == key[0] and str(item.get("scope")) == key[1]
                for item in STATE.ric_item_exceptions
            ):
                self._send_json(
                    {"ok": False, "error": "Eccezione già presente per questo SKU e scope."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            STATE.ric_item_exceptions.append(incoming)
            save_ric_item_exceptions(STATE.ric_item_exceptions)
            warning = None
            if find_stock_item_by_sku(incoming["sku"]) is None:
                warning = "SKU non trovato nei dati caricati: eccezione salvata comunque."
            self._send_json({"ok": True, "items": STATE.ric_item_exceptions, "warning": warning})
            return

        if self.path == "/api/ric/item_exceptions/update":
            incoming = normalize_item_exception_entry(payload)
            original_sku = normalize_sku(str(payload.get("original_sku", incoming.get("sku", ""))))
            original_scope = normalize_item_exception_scope(
                payload.get("original_scope", incoming.get("scope", "all"))
            )
            if not incoming.get("sku"):
                self._send_json(
                    {"ok": False, "error": "SKU mancante."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            valid, error = validate_item_exception(incoming)
            if not valid:
                self._send_json({"ok": False, "error": error}, status=HTTPStatus.BAD_REQUEST)
                return
            updated = False
            for idx, item in enumerate(STATE.ric_item_exceptions):
                if normalize_sku(str(item.get("sku", ""))) == original_sku and str(
                    item.get("scope", "")
                ) == original_scope:
                    STATE.ric_item_exceptions[idx] = incoming
                    updated = True
                    break
            if not updated:
                self._send_json(
                    {"ok": False, "error": "Eccezione non trovata."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            save_ric_item_exceptions(STATE.ric_item_exceptions)
            self._send_json({"ok": True, "items": STATE.ric_item_exceptions})
            return

        if self.path == "/api/ric/item_exceptions/delete":
            sku = normalize_sku(str(payload.get("sku", "")))
            scope = normalize_item_exception_scope(payload.get("scope", "all"))
            if not sku:
                self._send_json(
                    {"ok": False, "error": "SKU mancante."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            before = len(STATE.ric_item_exceptions)
            STATE.ric_item_exceptions = [
                item
                for item in STATE.ric_item_exceptions
                if not (
                    normalize_sku(str(item.get("sku", ""))) == sku
                    and str(item.get("scope", "")) == scope
                )
            ]
            if len(STATE.ric_item_exceptions) == before:
                self._send_json(
                    {"ok": False, "error": "Eccezione non trovata."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return
            save_ric_item_exceptions(STATE.ric_item_exceptions)
            self._send_json({"ok": True, "items": STATE.ric_item_exceptions})
            return

        if self.path == "/api/ric/item_exceptions/reset_all":
            STATE.ric_item_exceptions = []
            save_ric_item_exceptions(STATE.ric_item_exceptions)
            self._send_json({"ok": True, "items": STATE.ric_item_exceptions})
            return

        if self.path == "/api/ric/save_overrides":
            incoming = payload.get("overrides", [])
            if not isinstance(incoming, list):
                self._send_json(
                    {"ok": False, "error": "Formato override non valido"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                new_overrides: dict[str, dict] = {}
                for row in incoming:
                    macro = row.get("categoria")
                    listino = row.get("listino")
                    if not macro or not listino:
                        continue
                    new_overrides.setdefault(macro, {})[listino] = {
                        "ric_base": float(row.get("ric_base")),
                        "ric_floor": float(row.get("ric_floor")),
                        "note": row.get("note", ""),
                    }
                errors = validate_ric_overrides(sconti, new_overrides)
                if errors:
                    self._send_json(
                        {"ok": False, "error": "override_invalid", "details": errors},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                STATE.ric_overrides = new_overrides
                save_ric_overrides({"overrides": STATE.ric_overrides})
                refresh_ric_override_errors()
                self._send_json({"ok": True, "overrides": STATE.ric_overrides})
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"Errore salvataggio RIC: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        if self.path == "/api/ric/reset_overrides":
            try:
                macro = payload.get("categoria")
                listino = payload.get("listino")
                if macro and listino:
                    if macro in STATE.ric_overrides:
                        STATE.ric_overrides.get(macro, {}).pop(listino, None)
                        if not STATE.ric_overrides.get(macro):
                            STATE.ric_overrides.pop(macro, None)
                elif macro:
                    STATE.ric_overrides.pop(macro, None)
                else:
                    STATE.ric_overrides = {}
                save_ric_overrides({"overrides": STATE.ric_overrides})
                refresh_ric_override_errors()
                self._send_json({"ok": True, "overrides": STATE.ric_overrides})
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": f"Errore reset RIC: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def run() -> None:
    host = "127.0.0.1"
    port = 8765
    server = HTTPServer((host, port), RequestHandler)
    STATE.logger.info("Server avviato su http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        STATE.logger.info("Server fermato")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise
