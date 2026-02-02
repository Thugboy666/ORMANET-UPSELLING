"""XLSX loading helpers for Ormanet Upselling."""

from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from engine import ClientInfo, OrderItem, SessionLogger, StockItem


def load_clients(path: Path, logger: SessionLogger) -> list[ClientInfo]:
    wb = load_workbook(filename=path, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    header_map = {name: idx for idx, name in enumerate(headers)}

    clients: list[ClientInfo] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        client_id = str(row[header_map.get("ID", 0)] or "").strip()
        ragione_sociale = str(row[header_map.get("Ragione sociale", 1)] or "").strip()
        listino = str(row[header_map.get("Listino", 0)] or "").strip()
        categoria = str(row[header_map.get("Categoria", 0)] or "").strip()
        if not client_id or not ragione_sociale:
            continue
        clients.append(ClientInfo(client_id, ragione_sociale, listino, categoria))
    logger.info("Loaded %s clients", len(clients))
    return clients


def load_stock(path: Path, logger: SessionLogger) -> dict[str, StockItem]:
    wb = load_workbook(filename=path, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    header_map = {name: idx for idx, name in enumerate(headers)}
    stock: dict[str, StockItem] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        codice = str(row[header_map.get("Codice", 0)] or "").strip()
        if not codice:
            continue
        stock[codice] = StockItem(
            categoria=str(row[header_map.get("Categoria", 0)] or "").strip(),
            marca=str(row[header_map.get("Marca", 0)] or "").strip(),
            codice=codice,
            descrizione=str(row[header_map.get("Descrizione", 0)] or "").strip(),
            disp=float(row[header_map.get("Disp.", 0)] or 0),
            disp_in_arrivo=float(row[header_map.get("Disp. in Arrivo", 0)] or 0),
            giacenza=float(row[header_map.get("Giacenza", 0)] or 0),
            data_arrivo=str(row[header_map.get("Data evasione/arrivo", 0)] or "").strip(),
            listino_ri10=float(row[header_map.get("Listino RI+10%", 0)] or 0),
            listino_ri=float(row[header_map.get("Listino RI", 0)] or 0),
            listino_di=float(row[header_map.get("Listino DI", 0)] or 0),
        )
    logger.info("Loaded %s stock items", len(stock))
    return stock


def load_orders(paths: list[Path], logger: SessionLogger) -> list[OrderItem]:
    items: list[OrderItem] = []
    for path in paths:
        wb = load_workbook(filename=path, data_only=True)
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        header_map = {name: idx for idx, name in enumerate(headers)}
        for row in ws.iter_rows(min_row=2, values_only=True):
            codice = str(row[header_map.get("Cod.", 0)] or "").strip()
            if not codice:
                continue
            items.append(
                OrderItem(
                    marca=str(row[header_map.get("Marca", 0)] or "").strip(),
                    categoria=str(row[header_map.get("Categoria", 0)] or "").strip(),
                    codice=codice,
                    descrizione=str(row[header_map.get("Descrizione", 0)] or "").strip(),
                    qty=float(row[header_map.get("Qty", 0)] or 0),
                    prezzo_unit=float(row[header_map.get("Prezzo (unit, ex VAT)", 0)] or 0),
                )
            )
    logger.info("Loaded %s order items", len(items))
    return items
