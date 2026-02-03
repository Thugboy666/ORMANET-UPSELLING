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
    AGGRESSIVITA_STEPS,
    CAUSALI,
    ClientInfo,
    SessionLogger,
    UpsellRow,
    compute_upsell,
    export_excel,
    load_json,
)
from app.io_loaders import load_clients, load_orders, load_stock
from app.web_ui import HTML

BASE_DIR = Path(__file__).resolve().parents[1]
IMPORT_DIR = BASE_DIR / "import"
ORDERS_DIR = IMPORT_DIR / "ORDINI"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"


@dataclass
class AppState:
    logger: SessionLogger
    clients: list[ClientInfo] = field(default_factory=list)
    stock: dict[str, Any] = field(default_factory=dict)
    histories: list[Path] = field(default_factory=list)
    current_order: Path | None = None
    causale: str | None = None
    aggressivita: int = 0
    selected_client_id: str | None = None
    upsell_rows: list[UpsellRow] = field(default_factory=list)
    copy_block: str = ""

    def reset_results(self) -> None:
        self.upsell_rows = []
        self.copy_block = ""

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
            f"Ric% {row.required_ric:.2f} | {row.totale:.2f} | Disp {row.disp} | "
            f"Disponibile dal {row.disponibile_dal or '-'}"
        )
    return "\n".join(lines)


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
                    "aggressivita": STATE.aggressivita,
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
                STATE.clients = load_clients(clients_path, STATE.logger)
                STATE.stock = load_stock(stock_path, STATE.logger)
                self._send_json(
                    {"success": True, "message": "Clienti e stock caricati"},
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
            if aggressivita in AGGRESSIVITA_STEPS:
                STATE.aggressivita = aggressivita
                STATE.reset_results()
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
                historical_items = load_orders(STATE.histories, STATE.logger)
                current_items = load_orders([STATE.current_order], STATE.logger)
                client = STATE.selected_client()
                if client is None:
                    raise ValueError("Cliente non selezionato")
                STATE.upsell_rows = compute_upsell(
                    current_items=current_items,
                    historical_items=historical_items,
                    stock=STATE.stock,
                    client=client,
                    sconti=sconti,
                    category_map=category_map,
                    aggressivita=STATE.aggressivita,
                    causale=STATE.causale or CAUSALI[0],
                    logger=STATE.logger,
                )
                order_name = STATE.current_order.name if STATE.current_order else ""
                STATE.copy_block = build_copy_block(
                    STATE.upsell_rows, client, order_name, STATE.causale or ""
                )
                rows = [
                    {
                        "codice": row.codice,
                        "descrizione": row.descrizione,
                        "qty": f"{row.qty:.2f}",
                        "prezzo_unit": f"{row.prezzo_unit:.2f}",
                        "required_ric": f"{row.required_ric:.2f}",
                        "totale": f"{row.totale:.2f}",
                        "disp": f"{row.disp:.2f}",
                        "disponibile_dal": row.disponibile_dal or "",
                    }
                    for row in STATE.upsell_rows
                ]
                self._send_json({"success": True, "rows": rows, "copy_block": STATE.copy_block})
            except Exception as exc:
                STATE.logger.error("Errore calcolo upsell", error=str(exc))
                self._send_json(
                    {"success": False, "error": f"Errore calcolo: {exc}"},
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
