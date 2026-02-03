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
    prezzo_alt: float | None = None
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
    prezzo_alt: float | None
    alt_available: bool
    alt_selected: bool
    macro_categoria: str
    fixed_discount_percent: float
    ric_base: float
    ric_base_source: str
    ric_floor_source: str
    item_exception_hit: bool
    customer_base_price: float
    max_discount_real: float
    max_discount_real_pct: float
    max_discount_effective: float
    max_discount_effective_pct: float
    desired_discount_pct: float
    applied_discount_pct: float
    final_ric_percent: float
    clamp_reason: str | None
    min_unit_price: float | None
    required_ric: float | None
    totale: float
    disp: float
    disponibile_dal: str | None = None
    note: str | None = None


@dataclass
class AltSuggestion:
    codice: str
    descrizione: str
    categoria: str
    marca: str
    prezzo_alt: float
    qty: float = 1.0


@dataclass
class PricingRow:
    codice: str
    descrizione: str
    categoria: str
    lm: float
    ric_base: float
    ric_min: float
    sconto_fisso: float
    prezzo_base: float
    prezzo_min: float
    sconto_richiesto: float
    sconto_cap: float
    sconto_effettivo: float
    prezzo_finale: float
    ric_effettivo: float
    fonte_cap: str | None


@dataclass
class PricingParams:
    aggressivity: float = DEFAULT_AGGRESSIVITY
    aggressivity_mode: str = AGGRESSIVITY_MODES[0]
    max_discount_percent: float | None = DEFAULT_MAX_DISCOUNT
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


def normalize_sku(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = re.sub(r"\s+", " ", text)
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


def resolve_ric_values(
    *,
    macro: str,
    listino: str,
    sconti: dict,
    ric_overrides: dict[str, dict] | None = None,
    item_exceptions: list[dict] | None = None,
    sku: str | None = None,
) -> dict[str, object]:
    listino_key = LISTINO_MAP.get(listino.upper().strip(), "RIV")
    listino_scope = "RIV10" if listino_key == "RIV+10" else listino_key
    defaults = sconti.get(macro, {}).get(listino_key, {})
    ric_exact = float(defaults.get("ric", ABSOLUTE_MIN_MARKUP))
    ric_floor_default = max(ABSOLUTE_MIN_MARKUP, ric_exact)
    ric_floor = ric_floor_default
    ric_floor_source = "default"
    category_override = ric_overrides.get(macro, {}).get(listino_key) if ric_overrides else None
    if category_override:
        override_floor = float(category_override.get("ric_floor", ric_floor))
        if override_floor > ric_floor:
            ric_floor = override_floor
            ric_floor_source = "category_override"
    ric_base_default = defaults.get("ric_base")
    if ric_base_default is None:
        ric_base_default = ric_floor_default
    ric_base_default = float(ric_base_default)
    category_base = None
    if category_override:
        category_base = max(ric_floor, float(category_override.get("ric_base", ric_base_default)))

    item_base = None
    item_exception_hit = False
    if item_exceptions and sku:
        normalized_sku = normalize_sku(sku)
        scoped_items = []
        for entry in item_exceptions:
            if normalize_sku(str(entry.get("sku", ""))) != normalized_sku:
                continue
            scope = str(entry.get("scope", "all")).upper()
            scope = scope.replace("+", "")
            if scope == "ALL":
                scope = "ALL"
            if scope in ("ALL", listino_scope):
                scoped_items.append(entry)
        scoped_items.sort(key=lambda item: 0 if str(item.get("scope", "")).upper() in ("ALL", "all") else 1)
        if scoped_items:
            item_exception_hit = True
            item_base = float(scoped_items[-1].get("ric_base_override", 0.0))

    candidates = [ric_floor, ric_base_default]
    if category_base is not None:
        candidates.append(category_base)
    if item_base is not None:
        candidates.append(item_base)
    ric_base = max(candidates)

    ric_base_source = "default"
    if item_base is not None and item_base >= ric_base:
        ric_base_source = "item_exception"
    elif category_base is not None and category_base >= ric_base:
        ric_base_source = "category_override"

    return {
        "listino_key": listino_key,
        "ric_floor": ric_floor,
        "ric_base": ric_base,
        "ric_floor_source": ric_floor_source,
        "ric_base_source": ric_base_source,
        "item_exception_hit": item_exception_hit,
    }


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
    max_discount_real_pct = max_discount_real * 100
    aggressivity_value = aggressivity_to_discount_percent(aggressivity)
    max_discount_ui = max_discount_percent if max_discount_percent is not None else max_discount_real_pct
    max_discount_ui = max(0.0, float(max_discount_ui))
    requested_discount_pct = (aggressivity_value / 100) * max_discount_ui
    effective_discount_pct = min(requested_discount_pct, max_discount_real_pct)
    if discount_override is not None:
        requested_discount_pct = float(discount_override)
        effective_discount_pct = min(requested_discount_pct, max_discount_real_pct)
    candidate_price = baseline_price * (1 - effective_discount_pct / 100)
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
        "max_discount_real": max_discount_real,
        "max_discount_real_pct": max_discount_real_pct,
        "max_discount_effective": max_discount_real_pct / 100,
        "max_discount_effective_pct": max_discount_real_pct,
        "desired_discount_pct": requested_discount_pct,
        "effective_discount_pct": effective_discount_pct,
        "candidate_price": candidate_price,
        "final_price": final_price,
        "final_ric": final_ric,
        "applied_discount_pct": applied_discount,
    }
    return payload, clamp_reason


def build_pricing_row(
    *,
    codice: str,
    descrizione: str,
    categoria: str,
    lm: float,
    ric_base: float,
    ric_min: float,
    sconto_fisso: float,
    max_discount_percent: float | None,
    aggressivity: float,
    listino: str,
    logger: SessionLogger,
    requested_discount_override: float | None = None,
) -> PricingRow:
    prezzo_base = lm * (1 + ric_base / 100)
    prezzo_min = lm * (1 + ric_min / 100)
    cap_riga_percent = (
        max(0.0, (prezzo_base - prezzo_min) / prezzo_base * 100) if prezzo_base else 0.0
    )
    aggressivity_value = aggressivity_to_discount_percent(aggressivity)
    if requested_discount_override is not None:
        sconto_richiesto = float(requested_discount_override)
    else:
        max_discount_ui = max_discount_percent if max_discount_percent is not None else cap_riga_percent
        max_discount_ui = max(0.0, float(max_discount_ui))
        sconto_richiesto = max_discount_ui * (aggressivity_value / 100)
    sconto_effettivo = min(sconto_richiesto, cap_riga_percent)
    prezzo_finale = prezzo_base * (1 - sconto_effettivo / 100)
    ric_effettivo = ((prezzo_finale / lm) - 1) * 100 if lm else 0.0
    fonte_cap = "ric_min" if cap_riga_percent + 1e-9 < sconto_richiesto else None
    logger.info(
        "Pricing row %s | cat=%s | listino=%s | LM=%.2f | ric_base=%.2f | ric_min=%.2f | cap=%.2f | richiesto=%.2f | effettivo=%.2f",
        codice,
        categoria,
        listino,
        lm,
        ric_base,
        ric_min,
        cap_riga_percent,
        sconto_richiesto,
        sconto_effettivo,
    )
    if fonte_cap:
        logger.info(
            "Pricing row clamp %s: cap %.2f < richiesto %.2f (fonte %s)",
            codice,
            cap_riga_percent,
            sconto_richiesto,
            fonte_cap,
        )
    return PricingRow(
        codice=codice,
        descrizione=descrizione,
        categoria=categoria,
        lm=lm,
        ric_base=ric_base,
        ric_min=ric_min,
        sconto_fisso=sconto_fisso,
        prezzo_base=prezzo_base,
        prezzo_min=prezzo_min,
        sconto_richiesto=sconto_richiesto,
        sconto_cap=cap_riga_percent,
        sconto_effettivo=sconto_effettivo,
        prezzo_finale=prezzo_finale,
        ric_effettivo=ric_effettivo,
        fonte_cap=fonte_cap,
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


def compute_alt_suggestions(
    stock_items: dict[str, StockItem],
    storico_items: list[OrderItem],
    current_rows: list[UpsellRow],
    category_map: dict,
    logger: SessionLogger,
    limit: int = 3,
) -> list[AltSuggestion]:
    suggestions: list[AltSuggestion] = []
    if limit <= 0:
        return suggestions
    current_codes = {row.codice for row in current_rows}
    storico_codes = {item.codice for item in storico_items}
    category_counts: dict[str, int] = {}
    brand_counts: dict[str, int] = {}
    for item in storico_items:
        macro = map_macro_category(item.categoria, category_map, logger)
        if macro != "UNKNOWN":
            category_counts[macro] = category_counts.get(macro, 0) + 1
        if item.marca:
            brand_counts[item.marca] = brand_counts.get(item.marca, 0) + 1
    top_categories = {
        key
        for key, _ in sorted(category_counts.items(), key=lambda entry: entry[1], reverse=True)[:5]
    }
    top_brands = {
        key
        for key, _ in sorted(brand_counts.items(), key=lambda entry: entry[1], reverse=True)[:5]
    }

    scored_items: list[tuple[int, float, StockItem]] = []
    for item in stock_items.values():
        if item.codice in current_codes or item.codice in storico_codes:
            continue
        if item.prezzo_alt is None or item.prezzo_alt <= 0:
            continue
        macro = map_macro_category(item.categoria, category_map, logger)
        if macro == "UNKNOWN":
            continue
        score = 0
        if macro in top_categories:
            score += 2
        if item.marca in top_brands:
            score += 1
        availability = float(item.disp) + float(item.disp_in_arrivo)
        scored_items.append((score, availability, item))

    scored_items.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    for score, availability, item in scored_items[:limit]:
        _ = score, availability
        suggestions.append(
            AltSuggestion(
                codice=item.codice,
                descrizione=item.descrizione,
                categoria=item.categoria,
                marca=item.marca,
                prezzo_alt=float(item.prezzo_alt),
                qty=1.0,
            )
        )
    return suggestions


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
    item_exceptions: list[dict] | None = None,
) -> tuple[list[UpsellRow], list[PricingRow], dict, dict, list[str]]:
    suggestions: list[UpsellRow] = []
    pricing_rows: list[PricingRow] = []
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
        ric_values = resolve_ric_values(
            macro=macro,
            listino=client.listino,
            sconti=sconti,
            ric_overrides=ric_overrides,
            item_exceptions=item_exceptions,
            sku=item.codice,
        )
        ric_floor = float(ric_values["ric_floor"])
        ric_base = float(ric_values["ric_base"])
        ric_floor_source = str(ric_values["ric_floor_source"])
        ric_base_source = str(ric_values["ric_base_source"])
        item_exception_hit = bool(ric_values["item_exception_hit"])
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
        max_discount_real_pct = pricing_payload["max_discount_real_pct"]
        max_discount_effective = pricing_payload["max_discount_effective"]
        max_discount_effective_pct = pricing_payload["max_discount_effective_pct"]
        desired_discount_pct = pricing_payload["desired_discount_pct"]
        effective_discount_pct = pricing_payload["effective_discount_pct"]
        candidate_price = pricing_payload["candidate_price"]
        computed_price = pricing_payload["final_price"]
        final_ric = pricing_payload["final_ric"]
        applied_discount_pct = pricing_payload["applied_discount_pct"]
        buffer_ric = ric_base - ric_floor
        override = overrides.get(item.codice, {})
        qty_override = override.get("qty")
        qty = max(1.0, float(qty_override)) if qty_override is not None else max(1.0, item.qty)
        discount_override = override.get("discount_override")
        unit_price_override = override.get("unit_price_override")
        lock_override = bool(override.get("lock"))
        alt_selected = bool(override.get("alt_selected"))
        alt_price = stock_item.prezzo_alt if stock_item and stock_item.prezzo_alt is not None else None
        alt_available = alt_price is not None and alt_price > 0
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
            desired_discount_pct = pricing_payload["desired_discount_pct"]
            effective_discount_pct = pricing_payload["effective_discount_pct"]
            computed_price = pricing_payload["final_price"]
            final_ric = pricing_payload["final_ric"]
            applied_discount_pct = pricing_payload["applied_discount_pct"]
            candidate_price = pricing_payload["candidate_price"]

        final_price = computed_price
        note = None
        min_unit_price = floor_price
        required_ric = ric_floor
        if alt_selected and not alt_available:
            note = "ALT non disponibile"
        if alt_selected and alt_available and not lock_override:
            final_price = round_up_to_step(float(alt_price), pricing.rounding)
            applied_discount_pct = (
                (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
            )
            applied_discount_pct = max(0.0, min(100.0, applied_discount_pct))
            desired_discount_pct = applied_discount_pct
            effective_discount_pct = applied_discount_pct
            final_ric = (final_price / lm_value - 1) * 100 if lm_value else 0.0
            clamp_reason = "ALT_LOCKED"
            min_unit_price = None
            required_ric = None
            note = "ALT: prezzo promo fisso (non scontabile)"
        if unit_price_override is not None:
            clamp_reason = None
            min_unit_price = floor_price
            required_ric = ric_floor
            final_price = float(unit_price_override)
            if final_price < floor_price:
                final_price = floor_price
                clamp_reason = "MIN_RIC_FLOOR"
            final_price = round_up_to_step(final_price, pricing.rounding)
            if final_price < floor_price:
                final_price = round_up_to_step(floor_price, pricing.rounding)
                clamp_reason = "MIN_RIC_FLOOR"
            final_ric = (final_price / lm_value - 1) * 100 if lm_value else 0.0
            applied_discount_pct = (
                (baseline_price - final_price) / baseline_price * 100 if baseline_price else 0.0
            )
            note = None

        totale = round_up(final_price * qty, 2)
        suggestions.append(
            UpsellRow(
                codice=item.codice,
                descrizione=item.descrizione,
                qty=qty,
                prezzo_unit=final_price,
                lm=lm_value,
                prezzo_alt=alt_price,
                alt_available=alt_available,
                alt_selected=alt_selected,
                macro_categoria=macro,
                fixed_discount_percent=fixed_discount,
                ric_base=ric_base,
                ric_base_source=ric_base_source,
                ric_floor_source=ric_floor_source,
                item_exception_hit=item_exception_hit,
                customer_base_price=baseline_price,
                max_discount_real=max_discount_real,
                max_discount_real_pct=max_discount_real_pct,
                max_discount_effective=max_discount_effective,
                max_discount_effective_pct=max_discount_effective_pct,
                desired_discount_pct=desired_discount_pct,
                applied_discount_pct=applied_discount_pct,
                final_ric_percent=final_ric,
                clamp_reason=clamp_reason,
                min_unit_price=min_unit_price,
                required_ric=required_ric,
                totale=totale,
                disp=stock_item.disp,
                disponibile_dal=available_date,
                note=note,
            )
        )
        pricing_rows.append(
            build_pricing_row(
                codice=item.codice,
                descrizione=item.descrizione,
                categoria=macro,
                lm=lm_value,
                ric_base=ric_base,
                ric_min=ric_floor,
                sconto_fisso=fixed_discount,
                max_discount_percent=pricing.max_discount_percent,
                aggressivity=pricing.aggressivity,
                listino=client.listino,
                logger=logger,
                requested_discount_override=discount_override,
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
                "ric_base_source": ric_base_source,
                "ric_floor_source": ric_floor_source,
                "item_exception_hit": item_exception_hit,
                "baseline_price": baseline_price,
                "floor_price": floor_price,
                "max_discount_real": max_discount_real,
                "max_discount_real_pct": max_discount_real_pct,
                "max_discount_effective": max_discount_effective,
                "max_discount_effective_pct": max_discount_effective_pct,
                "buffer_ric": buffer_ric,
                "aggressivity": pricing.aggressivity,
                "aggressivity_mode": pricing.aggressivity_mode,
                "max_discount_percent": pricing.max_discount_percent,
                "discount_override": discount_override,
                "unit_price_override": unit_price_override,
                "desired_discount_pct": desired_discount_pct,
                "effective_discount_pct": effective_discount_pct,
                "capped_discount_pct": max_discount_effective_pct,
                "applied_discount_pct": applied_discount_pct,
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
                    f"Prezzo finale = max(Baseline * (1 - {effective_discount_pct:.2f}%), Floor)"
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
        if row.min_unit_price is not None and row.prezzo_unit < row.min_unit_price:
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
    return suggestions[:3], pricing_rows[:3], trace, validation, warnings


def self_test_pricing_rows() -> None:
    logger = SessionLogger(Path("logs"))
    sconti = {
        "CAT-A": {"RIV": {"ric": 11, "ric_base": 20, "discount": 0}},
        "CAT-B": {"RIV": {"ric": 17, "ric_base": 20, "discount": 0}},
        "CAT-C": {"RIV": {"ric": 25, "ric_base": 35, "discount": 0}},
    }
    ric_overrides: dict[str, dict] = {}
    listino = "LISTINO RI"
    items = [
        {"codice": "TEST-1", "descrizione": "Riga A", "categoria": "CAT-A", "lm": 100.0},
        {"codice": "TEST-2", "descrizione": "Riga B", "categoria": "CAT-B", "lm": 120.0},
        {"codice": "TEST-3", "descrizione": "Riga C", "categoria": "CAT-C", "lm": 80.0},
    ]
    max_sconto = 7.0
    aggressivita = 100.0
    rows: list[PricingRow] = []
    for item in items:
        ric_values = resolve_ric_values(
            macro=item["categoria"],
            listino=listino,
            sconti=sconti,
            ric_overrides=ric_overrides,
        )
        rows.append(
            build_pricing_row(
                codice=item["codice"],
                descrizione=item["descrizione"],
                categoria=item["categoria"],
                lm=item["lm"],
                ric_base=float(ric_values["ric_base"]),
                ric_min=float(ric_values["ric_floor"]),
                sconto_fisso=0.0,
                max_discount_percent=max_sconto,
                aggressivity=aggressivita,
                listino=listino,
                logger=logger,
            )
        )
    print("=== SELF TEST PRICING ===")
    for row in rows:
        print(
            f"{row.codice} | cap={row.sconto_cap:.2f}% | richiesto={row.sconto_richiesto:.2f}% | "
            f"effettivo={row.sconto_effettivo:.2f}% | prezzo_finale={row.prezzo_finale:.2f}"
        )
    has_full = any(abs(row.sconto_effettivo - 7.0) < 0.05 for row in rows)
    has_clamped = any(2.0 <= row.sconto_effettivo <= 3.0 for row in rows)
    print(f"Check: almeno una riga a 7% -> {has_full}")
    print(f"Check: almeno una riga clamp ~2-3% -> {has_clamped}")


if __name__ == "__main__":
    self_test_pricing_rows()


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
            row.desired_discount_pct,
            row.prezzo_unit,
            row.final_ric_percent,
            row.required_ric,
            row.min_unit_price,
            row.totale,
            row.disp,
            row.disponibile_dal or "",
            row.note or row.clamp_reason or "",
        ])
    output_path = output_dir / "preventivo.xlsx"
    wb.save(output_path)
    return output_path
