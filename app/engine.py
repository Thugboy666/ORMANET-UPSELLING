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
    source_file: str | None = None
    source_row: int | None = None


@dataclass
class UpsellRow:
    codice: str
    descrizione: str
    qty: float
    prezzo_unit: float
    listino_value: float
    baseline_price: float
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


def get_required_ric(macro: str, listino: str, sconti: dict) -> float:
    listino_key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    ric = sconti.get(macro, {}).get(listino_key, {}).get("ric", ABSOLUTE_MIN_MARKUP)
    return max(ABSOLUTE_MIN_MARKUP, float(ric))


def pick_listino_value(stock: StockItem | None, listino: str) -> float:
    if stock is None:
        return 0.0
    key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    if key == "RIV+10":
        return stock.listino_ri10
    if key == "DIST":
        return stock.listino_di
    return stock.listino_ri


def compute_baseline_price(listino_value: float, required_ric: float, buffer_ric: float) -> float:
    baseline_ric = max(required_ric, required_ric + buffer_ric)
    return listino_value * (1 + baseline_ric / 100)


def aggressivity_to_discount_percent(aggressivity: float) -> float:
    return max(0.0, min(100.0, float(aggressivity)))


def apply_aggressivity(
    *,
    listino_value: float,
    required_ric: float,
    aggressivity: float,
    max_discount_percent: float,
    buffer_ric: float,
    mode: str,
    rounding: float | None,
    discount_override: float | None = None,
) -> tuple[float, float, float, float, str | None, float]:
    baseline_price = compute_baseline_price(listino_value, required_ric, buffer_ric)
    baseline_ric = (baseline_price / listino_value - 1) * 100 if listino_value else 0.0
    desired_discount = aggressivity_to_discount_percent(aggressivity)
    if discount_override is not None:
        desired_discount = float(discount_override)
    capped_discount = min(desired_discount, max_discount_percent)
    clamp_reason = None
    if desired_discount > max_discount_percent:
        clamp_reason = "MAX_DISCOUNT_CAP"

    floor_price = listino_value * (1 + required_ric / 100)
    final_price = baseline_price
    if mode == "target_ric_reduction":
        target_ric = max(required_ric, baseline_ric - capped_discount)
        if target_ric == required_ric and capped_discount > 0:
            clamp_reason = "MIN_RIC_FLOOR"
        final_price = listino_value * (1 + target_ric / 100)
    else:
        candidate_price = baseline_price * (1 - capped_discount / 100)
        if candidate_price < floor_price:
            final_price = floor_price
            if capped_discount > 0:
                clamp_reason = "MIN_RIC_FLOOR"
        else:
            final_price = candidate_price

    final_price = round_up_to_step(final_price, rounding)
    final_ric = (final_price / listino_value - 1) * 100 if listino_value else 0.0
    applied_discount = (
        (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
    )
    return (
        final_price,
        final_ric,
        applied_discount,
        baseline_price,
        clamp_reason,
        floor_price,
    )


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
        required = get_required_ric(macro, client.listino, sconti)
        listino_value = pick_listino_value(stock_item, client.listino)
        if listino_value <= 0:
            warnings.append(f"Listino mancante per {item.codice}")
            return
        override = overrides.get(item.codice, {})
        qty_override = override.get("qty")
        qty = max(1.0, float(qty_override)) if qty_override is not None else max(1.0, item.qty)
        discount_override = override.get("discount_override")
        unit_price_override = override.get("unit_price_override")
        clamp_reason = None

        (
            computed_price,
            final_ric,
            applied_discount,
            baseline_price,
            clamp_reason,
            floor_price,
        ) = apply_aggressivity(
            listino_value=listino_value,
            required_ric=required,
            aggressivity=pricing.aggressivity,
            max_discount_percent=pricing.max_discount_percent,
            buffer_ric=pricing.buffer_ric,
            mode=pricing.aggressivity_mode,
            rounding=pricing.rounding,
            discount_override=discount_override,
        )

        final_price = computed_price
        if unit_price_override is not None:
            final_price = float(unit_price_override)
            final_ric = (final_price / listino_value - 1) * 100 if listino_value else 0.0
            applied_discount = (
                (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
            )
            if final_price < floor_price:
                clamp_reason = "BELOW_MIN_PRICE"

        totale = round_up(final_price * qty, 2)
        suggestions.append(
            UpsellRow(
                codice=item.codice,
                descrizione=item.descrizione,
                qty=qty,
                prezzo_unit=final_price,
                listino_value=listino_value,
                baseline_price=baseline_price,
                applied_discount_percent=applied_discount,
                final_ric_percent=final_ric,
                clamp_reason=clamp_reason,
                min_unit_price=floor_price,
                required_ric=required,
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
                "listino_value": listino_value,
                "required_ric": required,
                "baseline_price": baseline_price,
                "buffer_ric": pricing.buffer_ric,
                "aggressivity": pricing.aggressivity,
                "aggressivity_mode": pricing.aggressivity_mode,
                "max_discount_percent": pricing.max_discount_percent,
                "discount_override": discount_override,
                "unit_price_override": unit_price_override,
                "applied_discount_percent": applied_discount,
                "floor_price": floor_price,
                "clamp_reason": clamp_reason,
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
        "Prezzo (ex VAT)",
        "Listino base",
        "Baseline prezzo",
        "Sconto applicato %",
        "Ric % finale",
        "Ric % richiesto",
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
            row.prezzo_unit,
            row.listino_value,
            row.baseline_price,
            row.applied_discount_percent,
            row.final_ric_percent,
            row.required_ric,
            row.totale,
            row.disp,
            row.disponibile_dal or "",
            row.clamp_reason or "",
        ])
    output_path = output_dir / "preventivo.xlsx"
    wb.save(output_path)
    return output_path
