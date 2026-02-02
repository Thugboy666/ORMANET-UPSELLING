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
AGGRESSIVITA_STEPS = {
    0: 0.0,
    1: 2.0,
    2: 4.0,
    3: 6.0,
}


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


@dataclass
class OrderItem:
    marca: str
    categoria: str
    codice: str
    descrizione: str
    qty: float
    prezzo_unit: float


@dataclass
class UpsellRow:
    codice: str
    descrizione: str
    qty: float
    prezzo_unit: float
    required_ric: float
    totale: float
    disp: float
    disponibile_dal: str | None = None


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


def required_markup(macro: str, listino: str, sconti: dict) -> float:
    listino_key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    ric = sconti.get(macro, {}).get(listino_key, {}).get("ric", ABSOLUTE_MIN_MARKUP)
    return max(ABSOLUTE_MIN_MARKUP, float(ric))


def pick_price(item: OrderItem, stock: StockItem | None, listino: str) -> float:
    if item.prezzo_unit:
        return item.prezzo_unit
    if stock is None:
        return 0.0
    key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    if key == "RIV+10":
        return stock.listino_ri10
    if key == "DIST":
        return stock.listino_di
    return stock.listino_ri


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
    aggressivita: int,
    causale: str,
    logger: SessionLogger,
) -> list[UpsellRow]:
    suggestions: list[UpsellRow] = []
    historical_by_code = {item.codice: item for item in historical_items}
    current_by_code = {item.codice: item for item in current_items}

    def add_suggestion(item: OrderItem) -> None:
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
        required = required_markup(macro, client.listino, sconti)
        base_price = pick_price(item, stock_item, client.listino)
        if base_price <= 0:
            return
        cost_est = base_price / (1 + required / 100)
        max_discount = AGGRESSIVITA_STEPS.get(aggressivita, 0.0)
        discounted_price = base_price * (1 - max_discount / 100)
        min_price = cost_est * (1 + required / 100)
        final_price = max(discounted_price, min_price)
        final_price = round_up(final_price, 2)
        qty = max(1.0, item.qty)
        totale = round_up(final_price * qty, 2)
        suggestions.append(
            UpsellRow(
                codice=item.codice,
                descrizione=item.descrizione,
                qty=qty,
                prezzo_unit=final_price,
                required_ric=round_up(required, 2),
                totale=totale,
                disp=stock_item.disp,
                disponibile_dal=available_date,
            )
        )

    color_tokens = ["CYAN", "MAGENTA", "YELLOW"]
    for item in current_items:
        description = normalize_text(item.descrizione)
        if any(token in description for token in color_tokens):
            for hist_item in historical_items:
                if hist_item.marca == item.marca and "BLACK" in normalize_text(hist_item.descrizione):
                    add_suggestion(hist_item)
                    break

    for item in current_items:
        if len(suggestions) >= 3:
            break
        stock_item = stock.get(item.codice)
        if not stock_item or stock_item.disp <= item.qty:
            continue
        add_suggestion(item)

    if len(suggestions) < 3:
        for hist_item in historical_items:
            if len(suggestions) >= 3:
                break
            if hist_item.codice in current_by_code:
                continue
            if hist_item.codice not in historical_by_code:
                continue
            add_suggestion(hist_item)

    logger.info("Computed %s upsell rows", len(suggestions))
    return suggestions[:3]


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
        "Ric % richiesto",
        "Totale (ex VAT)",
        "Disp.",
        "Disponibile dal",
    ])
    for row in rows:
        ws.append([
            row.codice,
            row.descrizione,
            row.qty,
            row.prezzo_unit,
            row.required_ric,
            row.totale,
            row.disp,
            row.disponibile_dal or "",
        ])
    output_path = output_dir / "preventivo.xlsx"
    wb.save(output_path)
    return output_path
