"""Core computation engine for Ormanet Upselling (no GUI)."""

from __future__ import annotations

import json
import logging
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

VAT_RATE = 0.22
ABSOLUTE_MIN_MARKUP = 11.0

LISTINO_MAP = {
    "LISTINO RI+10%": "RIV+10",
    "LISTINO RI": "RIV",
    "LISTINO DI": "DIST",
}

CAUSALI = ["DISPONIBILE", "IN ARRIVO", "PROGRAMMATO"]
DEFAULT_AGGRESSIVITY = 0.0
DEFAULT_BUFFER_RIC = 2.0
DEFAULT_MAX_DISCOUNT = 10.0
DEFAULT_ROUNDING = 0.01
AGGRESSIVITY_MODES = ("discount_from_baseline", "target_ric_reduction")


@dataclass
class ClientInfo:
    client_id: str
    ragione_sociale: str
    listino: str
    categoria: str


@dataclass
class StockItem:
    categoria: str
    marca: str
    codice: str
    descrizione: str
    disp: float
    disp_in_arrivo: float
    giacenza: float
    data_arrivo: str
    listino_ri10: float
    listino_ri: float
    listino_di: float
    lm: float
    source_file: str | None = None
    source_row: int | None = None


@dataclass
class OrderItem:
    marca: str
    categoria: str
    codice: str
    descrizione: str
    qty: float
    prezzo_unit: float
    lm: float
    source_file: str | None = None
    source_row: int | None = None


@dataclass
class UpsellRow:
    codice: str
    descrizione: str
    qty: float
    prezzo_unit: float
    lm: float
    macro_categoria: str
    fixed_discount_percent: float
    customer_base_price: float
    max_discount_real: float
    desired_discount_percent: float
    applied_discount_percent: float
    final_ric_percent: float
    clamp_reason: str | None
    min_unit_price: float
    required_ric: float
    totale: float
    disp: float
    disponibile_dal: str | None = None


@dataclass
class PricingParams:
    aggressivity: float = DEFAULT_AGGRESSIVITY
    aggressivity_mode: str = AGGRESSIVITY_MODES[0]
    max_discount_percent: float = DEFAULT_MAX_DISCOUNT
    buffer_ric: float = DEFAULT_BUFFER_RIC
    rounding: float | None = DEFAULT_ROUNDING


class SessionLogger:
    """Structured logging with session support."""

    def __init__(self, logs_dir: Path) -> None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = uuid.uuid4().hex
        self.logger = logging.getLogger("ormanets")
        self.logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(logs_dir / "app.log", maxBytes=500_000, backupCount=3)
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.errors_path = logs_dir / "errors.jsonl"

    def info(self, message: str, *args: object) -> None:
        self.logger.info("[%s] %s", self.session_id, message % args if args else message)

    def error(self, message: str, **extra: object) -> None:
        self.logger.error("[%s] %s", self.session_id, message)
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "message": message,
            "extra": extra,
        }
        with self.errors_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    text = value.upper().strip()
    text = re.sub(r"[\s/_-]+", " ", text)
    text = (
        text.replace("À", "A")
        .replace("È", "E")
        .replace("É", "E")
        .replace("Ì", "I")
        .replace("Ò", "O")
        .replace("Ù", "U")
    )
    return text


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def round_up(value: float, decimals: int = 2) -> float:
    if decimals < 0:
        return value
    factor = 10**decimals
    return math.ceil(value * factor) / factor


def round_up_to_step(value: float, step: float | None) -> float:
    if step is None or step <= 0:
        return value
    factor = 1 / step
    return math.ceil(value * factor) / factor


def map_macro_category(raw_category: str, mapping: dict, logger: SessionLogger) -> str:
    normalized = normalize_text(raw_category)
    for macro, rules in mapping.items():
        for rule in rules:
            if normalize_text(rule) in normalized:
                return macro
    token_map = {
        "BATTER": "BATTERIE",
        "CANCELL": "CANCELLERIA",
        "CARTA": "CARTA",
        "ROTOL": "ROTOLI TERMICI",
        "REMAN": "REMAN",
        "ORIG": "ORIGINALI",
        "STORAGE": "STORAGE",
        "TIMBR": "TIMBRI",
    }
    for token, macro in token_map.items():
        if token in normalized:
            return macro
    logger.error("Categoria non riconosciuta", categoria=raw_category)
    return "UNKNOWN"


def get_ric_params(
    macro: str, listino: str, sconti: dict, ric_overrides: dict[str, dict] | None = None
) -> tuple[float, float, str]:
    listino_key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    defaults = sconti.get(macro, {}).get(listino_key, {})
    if "ric_base" not in defaults:
        raise ValueError(f"RIC.BASE mancante per {macro}/{listino_key}")
    ric_exact = float(defaults.get("ric", ABSOLUTE_MIN_MARKUP))
    ric_floor = max(ABSOLUTE_MIN_MARKUP, ric_exact)
    ric_base = float(defaults.get("ric_base"))
    source = "default"
    if ric_overrides:
        override = ric_overrides.get(macro, {}).get(listino_key)
        if override:
            ric_floor = max(ric_floor, float(override.get("ric_floor", ric_floor)))
            ric_base = float(override.get("ric_base", ric_base))
            source = "override"
    return ric_floor, ric_base, source


def get_fixed_discount(macro: str, listino: str, sconti: dict) -> float:
    listino_key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    discount = sconti.get(macro, {}).get(listino_key, {}).get("discount", 0.0)
    return float(discount)


def resolve_lm(stock_item: StockItem | None, order_item: OrderItem | None) -> tuple[float, str | None]:
    stock_lm = stock_item.lm if stock_item and stock_item.lm > 0 else 0.0
    order_lm = order_item.lm if order_item and order_item.lm > 0 else 0.0
    if stock_lm > 0:
        return stock_lm, "stock"
    if order_lm > 0:
        return order_lm, "order"
    return 0.0, None


def pick_listino_value(stock: StockItem | None, listino: str) -> float:
    if stock is None:
        return 0.0
    key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    if key == "RIV+10":
        return stock.listino_ri10
    if key == "DIST":
        return stock.listino_di
    return stock.listino_ri


def aggressivity_to_discount_percent(aggressivity: float) -> float:
    return max(0.0, min(100.0, float(aggressivity)))


def apply_pricing_pipeline(
    *,
    lm: float,
    ric_base: float,
    ric_floor: float,
    aggressivity: float,
    max_discount_percent: float | None,
    rounding: float | None,
    discount_override: float | None = None,
) -> tuple[dict, str | None]:
    baseline_price = lm * (1 + ric_base / 100)
    floor_price = lm * (1 + ric_floor / 100)
    max_discount_real = 1 - (floor_price / baseline_price) if baseline_price else 0.0
    max_discount_real = max(0.0, max_discount_real)
    max_discount_ui = max_discount_percent if max_discount_percent is not None else max_discount_real * 100
    max_discount_effective = min(max_discount_real * 100, float(max_discount_ui))

    aggressivity_value = aggressivity_to_discount_percent(aggressivity)
    desired_discount_percent = (aggressivity_value / 100) * max_discount_effective
    if discount_override is not None:
        desired_discount_percent = float(discount_override)
    candidate_price = baseline_price * (1 - desired_discount_percent / 100)
    clamp_reason = None
    if candidate_price < floor_price:
        candidate_price = floor_price
        clamp_reason = "MIN_RIC_FLOOR"

    final_price = round_up_to_step(candidate_price, rounding)
    if final_price < floor_price:
        final_price = round_up_to_step(floor_price, rounding)
        clamp_reason = "MIN_RIC_FLOOR"

    final_ric = (final_price / lm - 1) * 100 if lm else 0.0
    applied_discount = (
        (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
    )
    payload = {
        "baseline_price": baseline_price,
        "floor_price": floor_price,
        "max_discount_real": max_discount_real * 100,
        "max_discount_effective": max_discount_effective,
        "desired_discount_percent": desired_discount_percent,
        "candidate_price": candidate_price,
        "final_price": final_price,
        "final_ric": final_ric,
        "applied_discount": applied_discount,
    }
    return payload, clamp_reason


def is_available(stock_item: StockItem, causale: str) -> tuple[bool, str | None]:
    if causale == "PROGRAMMATO":
        if stock_item.disp > 0:
            return True, None
        if stock_item.disp_in_arrivo > 0 and stock_item.data_arrivo:
            return True, stock_item.data_arrivo
        return False, None
    if causale == "IN ARRIVO":
        return stock_item.disp > 0, None
    return stock_item.disp > 0, None


def compute_upsell(
    current_items: list[OrderItem],
    historical_items: list[OrderItem],
    stock: dict[str, StockItem],
    client: ClientInfo,
    sconti: dict,
    category_map: dict,
    pricing: PricingParams,
    causale: str,
    logger: SessionLogger,
    overrides: dict[str, dict] | None = None,
    ric_overrides: dict[str, dict] | None = None,
) -> tuple[list[UpsellRow], dict, dict, list[str]]:
    suggestions: list[UpsellRow] = []
    trace_rows: list[dict] = []
    warnings: list[str] = []
    overrides = overrides or {}
    historical_by_code: dict[str, list[OrderItem]] = {}
    for item in historical_items:
        historical_by_code.setdefault(item.codice, []).append(item)
    current_by_code = {item.codice: item for item in current_items}

    def add_suggestion(item: OrderItem, reason: str) -> None:
        if item.codice in {row.codice for row in suggestions}:
            return
        stock_item = stock.get(item.codice)
        if not stock_item:
            return
        available, available_date = is_available(stock_item, causale)
        if not available:
            return
        macro = map_macro_category(item.categoria, category_map, logger)
        if macro == "UNKNOWN":
            raise ValueError(f"Categoria non riconosciuta: {item.categoria}")
        ric_floor, ric_base, ric_source = get_ric_params(
            macro, client.listino, sconti, ric_overrides
        )
        fixed_discount = get_fixed_discount(macro, client.listino, sconti)
        lm_value, lm_source = resolve_lm(stock_item, item)
        if lm_value <= 0:
            warnings.append(f"LM mancante per SKU {item.codice}")
            return
        pricing_payload, clamp_reason = apply_pricing_pipeline(
            lm=lm_value,
            ric_base=ric_base,
            ric_floor=ric_floor,
            aggressivity=pricing.aggressivity,
            max_discount_percent=pricing.max_discount_percent,
            rounding=pricing.rounding,
        )
        baseline_price = pricing_payload["baseline_price"]
        floor_price = pricing_payload["floor_price"]
        max_discount_real = pricing_payload["max_discount_real"]
        max_discount_effective = pricing_payload["max_discount_effective"]
        desired_discount = pricing_payload["desired_discount_percent"]
        candidate_price = pricing_payload["candidate_price"]
        computed_price = pricing_payload["final_price"]
        final_ric = pricing_payload["final_ric"]
        applied_discount = pricing_payload["applied_discount"]
        buffer_ric = ric_base - ric_floor
        override = overrides.get(item.codice, {})
        qty_override = override.get("qty")
        qty = max(1.0, float(qty_override)) if qty_override is not None else max(1.0, item.qty)
        discount_override = override.get("discount_override")
        unit_price_override = override.get("unit_price_override")
        if discount_override is not None:
            pricing_payload, clamp_reason = apply_pricing_pipeline(
                lm=lm_value,
                ric_base=ric_base,
                ric_floor=ric_floor,
                aggressivity=pricing.aggressivity,
                max_discount_percent=pricing.max_discount_percent,
                rounding=pricing.rounding,
                discount_override=discount_override,
            )
            desired_discount = pricing_payload["desired_discount_percent"]
            computed_price = pricing_payload["final_price"]
            final_ric = pricing_payload["final_ric"]
            applied_discount = pricing_payload["applied_discount"]
            candidate_price = pricing_payload["candidate_price"]

        final_price = computed_price
        if unit_price_override is not None:
            final_price = float(unit_price_override)
            if final_price < floor_price:
                final_price = floor_price
                clamp_reason = "MIN_RIC_FLOOR"
            final_price = round_up_to_step(final_price, pricing.rounding)
            if final_price < floor_price:
                final_price = round_up_to_step(floor_price, pricing.rounding)
                clamp_reason = "MIN_RIC_FLOOR"
            final_ric = (final_price / lm_value - 1) * 100 if lm_value else 0.0
            applied_discount = (
                (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
            )

        totale = round_up(final_price * qty, 2)
        suggestions.append(
            UpsellRow(
                codice=item.codice,
                descrizione=item.descrizione,
                qty=qty,
                prezzo_unit=final_price,
                lm=lm_value,
                macro_categoria=macro,
                fixed_discount_percent=fixed_discount,
                customer_base_price=baseline_price,
                max_discount_real=max_discount_real,
                desired_discount_percent=desired_discount,
                applied_discount_percent=applied_discount,
                final_ric_percent=final_ric,
                clamp_reason=clamp_reason,
                min_unit_price=floor_price,
                required_ric=ric_floor,
                totale=totale,
                disp=stock_item.disp,
                disponibile_dal=available_date,
            )
        )
        trace_rows.append(
            {
                "sku": item.codice,
                "categoria": item.categoria,
                "macro_categoria": macro,
                "selection_reason": reason,
                "available": available,
                "available_date": available_date,
                "listino_key": LISTINO_MAP.get(client.listino.upper().strip(), "RIV"),
                "lm": lm_value,
                "lm_source": lm_source,
                "fixed_discount_percent": fixed_discount,
                "ric_base": ric_base,
                "ric_floor": ric_floor,
                "ric_source": ric_source,
                "baseline_price": baseline_price,
                "floor_price": floor_price,
                "max_discount_real": max_discount_real,
                "max_discount_effective": max_discount_effective,
                "buffer_ric": buffer_ric,
                "aggressivity": pricing.aggressivity,
                "aggressivity_mode": pricing.aggressivity_mode,
                "max_discount_percent": pricing.max_discount_percent,
                "discount_override": discount_override,
                "unit_price_override": unit_price_override,
                "desired_discount_percent": desired_discount,
                "capped_discount_percent": max_discount_effective,
                "applied_discount_percent": applied_discount,
                "clamp_reason": clamp_reason,
                "candidate_price": candidate_price,
                "final_price": final_price,
                "final_ric_percent": final_ric,
                "qty": qty,
                "stock_source": {
                    "file": stock_item.source_file,
                    "row": stock_item.source_row,
                },
                "order_source": {
                    "file": item.source_file,
                    "row": item.source_row,
                },
                "history_occurrences": len(historical_by_code.get(item.codice, [])),
                "formula": (
                    f"Baseline = LM * (1 + {ric_base:.2f}%) = {baseline_price:.2f}; "
                    f"Floor = LM * (1 + {ric_floor:.2f}%) = {floor_price:.2f}; "
                    f"Prezzo finale = max(Baseline * (1 - {desired_discount:.2f}%), Floor)"
                ),
            }
        )

    color_tokens = ["CYAN", "MAGENTA", "YELLOW"]
    for item in current_items:
        description = normalize_text(item.descrizione)
        if any(token in description for token in color_tokens):
            for hist_item in historical_items:
                if hist_item.marca == item.marca and "BLACK" in normalize_text(hist_item.descrizione):
                    add_suggestion(hist_item, "color_match_black")
                    break

    for item in current_items:
        if len(suggestions) >= 3:
            break
        stock_item = stock.get(item.codice)
        if not stock_item or stock_item.disp <= item.qty:
            continue
        add_suggestion(item, "current_stock_available")

    if len(suggestions) < 3:
        for hist_item in historical_items:
            if len(suggestions) >= 3:
                break
            if hist_item.codice in current_by_code:
                continue
            if hist_item.codice not in historical_by_code:
                continue
            add_suggestion(hist_item, "historical_fallback")

    errors: list[dict] = []
    for row in suggestions:
        if row.prezzo_unit < row.min_unit_price:
            errors.append(
                {
                    "sku": row.codice,
                    "min_unit_price": row.min_unit_price,
                    "provided_price": row.prezzo_unit,
                    "required_ric": row.required_ric,
                }
            )

    trace = {
        "global": {
            "client_id": client.client_id,
            "ragione_sociale": client.ragione_sociale,
            "listino": client.listino,
            "listino_key": LISTINO_MAP.get(client.listino.upper().strip(), "RIV"),
            "causale": causale,
            "pricing": {
                "aggressivity": pricing.aggressivity,
                "aggressivity_mode": pricing.aggressivity_mode,
                "max_discount_percent": pricing.max_discount_percent,
                "buffer_ric": pricing.buffer_ric,
                "rounding": pricing.rounding,
            },
        },
        "rows": trace_rows,
    }
    logger.info("Computed %s upsell rows", len(suggestions))
    validation = {"ok": len(errors) == 0, "errors": errors}
    return suggestions[:3], trace, validation, warnings


def export_excel(rows: list[UpsellRow], client: ClientInfo, order_file: str, output_dir: Path) -> Path:
    from openpyxl import Workbook

    output_dir.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Preventivo"
    ws.append([
        "Cliente",
        client.ragione_sociale,
        "Listino",
        client.listino,
        "Ordine",
        order_file,
    ])
    ws.append([])
    ws.append([
        "Codice",
        "Descrizione",
        "Qty",
        "LM",
        "Sconto fisso (%)",
        "Prezzo baseline (RIC.BASE)",
        "Sconto commerciale (%)",
        "Prezzo finale (ex VAT)",
        "Ric % finale",
        "Ric % minimo (RIC.)",
        "Prezzo minimo (RIC.)",
        "Totale (ex VAT)",
        "Disp.",
        "Disponibile dal",
        "Note",
    ])
    for row in rows:
        ws.append([
            row.codice,
            row.descrizione,
            row.qty,
            row.lm,
            row.fixed_discount_percent,
            row.customer_base_price,
            row.desired_discount_percent,
            row.prezzo_unit,
            row.final_ric_percent,
            row.required_ric,
            row.min_unit_price,
            row.totale,
            row.disp,
            row.disponibile_dal or "",
            row.clamp_reason or "",
        ])
    output_path = output_dir / "preventivo.xlsx"
    wb.save(output_path)
    return output_path
