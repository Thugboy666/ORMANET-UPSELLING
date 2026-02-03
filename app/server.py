"""Local web server for Ormanet Upselling (no external dependencies)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from app.engine import (
    CAUSALI,
    ClientInfo,
    DEFAULT_AGGRESSIVITY,
    DEFAULT_BUFFER_RIC,
    DEFAULT_MAX_DISCOUNT,
    DEFAULT_ROUNDING,
    PricingParams,
    SessionLogger,
    UpsellRow,
    compute_upsell,
    export_excel,
    get_required_ric,
    load_json,
    map_macro_category,
    pick_listino_value,
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


@dataclass
class AppState:
    logger: SessionLogger
    clients: list[ClientInfo] = field(default_factory=list)
    stock: dict[str, Any] = field(default_factory=dict)
    field_mapping: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    histories: list[Path] = field(default_factory=list)
    current_order: Path | None = None
    causale: str | None = None
    selected_client_id: str | None = None
    upsell_rows: list[UpsellRow] = field(default_factory=list)
    pricing: PricingParams = field(default_factory=PricingParams)
    per_row_overrides: dict[str, dict] = field(default_factory=dict)
    trace: dict = field(default_factory=dict)
    validation: dict = field(default_factory=lambda: {"ok": True, "errors": []})
    warnings: list[str] = field(default_factory=list)
    copy_block: str = ""

    def reset_results(self) -> None:
        self.upsell_rows = []
        self.copy_block = ""
        self.trace = {}
        self.validation = {"ok": True, "errors": []}
        self.warnings = []
        self.per_row_overrides = {}

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


def list_orders() -> dict[str, list[str]]:
    storico = sorted([path.name for path in ORDERS_DIR.glob("STORICO-*.xlsx")])
    upsell = sorted([path.name for path in ORDERS_DIR.glob("UPSELL-*.xlsx")])
    return {"storico": storico, "upsell": upsell}


def build_copy_block(rows: list[UpsellRow], client: ClientInfo, order_name: str, causale: str) -> str:
    lines = [
        f"Cliente: {client.ragione_sociale} (ID: {client.client_id}, Listino: {client.listino})",
        f"Ordine: {order_name}",
        f"Causale: {causale}",
        "Righe Upsell:",
    ]
    for row in rows:
        lines.append(
            f"- {row.codice} | {row.descrizione} | {row.qty} | {row.prezzo_unit:.2f} | "
            f"Sconto% {row.applied_discount_percent:.2f} | Ric% {row.final_ric_percent:.2f} | "
            f"Ric min% {row.required_ric:.2f} | {row.totale:.2f} | Disp {row.disp} | "
            f"Disponibile dal {row.disponibile_dal or '-'} | Note {row.clamp_reason or '-'}"
        )
    return "\n".join(lines)


def serialize_rows(rows: list[UpsellRow]) -> list[dict[str, Any]]:
    return [
        {
            "codice": row.codice,
            "descrizione": row.descrizione,
            "qty": row.qty,
            "prezzo_unit": row.prezzo_unit,
            "listino_value": row.listino_value,
            "baseline_price": row.baseline_price,
            "applied_discount_percent": row.applied_discount_percent,
            "final_ric_percent": row.final_ric_percent,
            "required_ric": row.required_ric,
            "totale": row.totale,
            "disp": row.disp,
            "disponibile_dal": row.disponibile_dal or "",
            "clamp_reason": row.clamp_reason,
            "min_unit_price": row.min_unit_price,
        }
        for row in rows
    ]


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
                    "validation_ok": STATE.validation.get("ok", True),
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
                historical_items = load_orders(
                    STATE.histories, STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                current_items = load_orders(
                    [STATE.current_order], STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                STATE.per_row_overrides = {}
                STATE.pricing = PricingParams(
                    aggressivity=DEFAULT_AGGRESSIVITY,
                    aggressivity_mode="discount_from_baseline",
                    max_discount_percent=DEFAULT_MAX_DISCOUNT,
                    buffer_ric=DEFAULT_BUFFER_RIC,
                    rounding=DEFAULT_ROUNDING,
                )
                STATE.upsell_rows, STATE.trace, STATE.validation, STATE.warnings = compute_upsell(
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
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                STATE.copy_block = build_copy_block(
                    STATE.upsell_rows, client, order_name, STATE.causale or ""
                )
                self._send_json(
                    {
                        "ok": True,
                        "success": True,
                        "quote": serialize_rows(STATE.upsell_rows),
                        "trace": STATE.trace,
                        "warnings": STATE.warnings,
                        "validation": STATE.validation,
                        "copy_block": STATE.copy_block,
                        "pricing": {
                            "aggressivity": STATE.pricing.aggressivity,
                            "aggressivity_mode": STATE.pricing.aggressivity_mode,
                            "max_discount_percent": STATE.pricing.max_discount_percent,
                            "buffer_ric": STATE.pricing.buffer_ric,
                            "rounding": STATE.pricing.rounding,
                        },
                    }
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
                    rounding_value = global_params.get("rounding", STATE.pricing.rounding)
                    if rounding_value in ("NONE", "", None):
                        rounding_value = None
                    else:
                        rounding_value = float(rounding_value)
                    STATE.pricing = PricingParams(
                        aggressivity=float(global_params.get("aggressivity", STATE.pricing.aggressivity)),
                        aggressivity_mode=global_params.get(
                            "aggressivity_mode", STATE.pricing.aggressivity_mode
                        ),
                        max_discount_percent=float(
                            global_params.get("max_discount_percent", STATE.pricing.max_discount_percent)
                        ),
                        buffer_ric=float(global_params.get("buffer_ric", STATE.pricing.buffer_ric)),
                        rounding=rounding_value,
                    )
                if isinstance(overrides, dict):
                    STATE.per_row_overrides = overrides
                sconti = load_json(CONFIG_DIR / "sconti_2026.json")
                category_map = load_json(CONFIG_DIR / "category_map.json")
                historical_items = load_orders(
                    STATE.histories, STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                current_items = load_orders(
                    [STATE.current_order], STATE.logger, STATE.field_mapping.get("ORDINI", {})
                )
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                STATE.upsell_rows, STATE.trace, STATE.validation, STATE.warnings = compute_upsell(
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
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                STATE.copy_block = build_copy_block(
                    STATE.upsell_rows, client, order_name, STATE.causale or ""
                )
                self._send_json(
                    {
                        "ok": True,
                        "quote": serialize_rows(STATE.upsell_rows),
                        "trace": STATE.trace,
                        "warnings": STATE.warnings,
                        "validation": STATE.validation,
                        "copy_block": STATE.copy_block,
                    }
                )
            except Exception as exc:
                STATE.logger.error("Errore recalcolo upsell", error=str(exc))
                self._send_json(
                    {"ok": False, "error": f"Errore recalcolo: {exc}"},
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
                required_ric = get_required_ric(macro, client.listino, sconti)
                listino_value = pick_listino_value(stock_item, client.listino)
                min_unit_price = listino_value * (1 + required_ric / 100)
                self._send_json(
                    {
                        "ok": True,
                        "sku": sku,
                        "min_unit_price": min_unit_price,
                        "required_ric": required_ric,
                        "listino_value": listino_value,
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
