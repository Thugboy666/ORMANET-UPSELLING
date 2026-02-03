"""HTML UI for the local web interface."""

from __future__ import annotations


HTML = """
<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ORMANET UPSELLING</title>
    <style>
      :root {
        --orange: #ff7a00;
        --black: #1c1c1c;
        --white: #ffffff;
        --gray: #f4f4f4;
      }
      body {
        font-family: "Segoe UI", Arial, sans-serif;
        margin: 0;
        background: var(--gray);
        color: var(--black);
      }
      header {
        background: var(--orange);
        color: var(--black);
        padding: 16px 24px;
        font-size: 22px;
        font-weight: bold;
      }
      .container {
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 16px;
        padding: 16px 24px;
      }
      .panel {
        background: var(--white);
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      }
      .panel h3 {
        margin-top: 0;
        color: var(--orange);
      }
      .status-list {
        list-style: none;
        padding: 0;
      }
      .status-list li {
        margin-bottom: 8px;
        font-size: 14px;
      }
      .status-ok {
        color: #0a7d2c;
        font-weight: 600;
      }
      .status-missing {
        color: #b10000;
        font-weight: 600;
      }
      label {
        display: block;
        margin-top: 12px;
        font-size: 13px;
        font-weight: 600;
      }
      select, button {
        margin-top: 6px;
        width: 100%;
        padding: 8px;
        border-radius: 6px;
        border: 1px solid #ddd;
      }
      .history-list {
        margin-top: 6px;
        border: 1px solid #ddd;
        border-radius: 6px;
        padding: 8px;
        max-height: 160px;
        overflow-y: auto;
        background: #fffaf5;
      }
      .history-item {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        font-size: 13px;
      }
      .history-item input {
        margin: 0;
      }
      .history-meta {
        margin-top: 4px;
        font-size: 12px;
        color: #444;
      }
      .history-help {
        color: #6b6b6b;
      }
      button {
        background: var(--orange);
        color: var(--black);
        font-weight: 600;
        cursor: pointer;
      }
      button.secondary {
        background: #ffffff;
      }
      button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      .actions {
        display: grid;
        gap: 8px;
        margin-top: 16px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        background: var(--white);
      }
      th, td {
        border-bottom: 1px solid #e5e5e5;
        padding: 8px;
        text-align: left;
        font-size: 14px;
      }
      th {
        background: #fff4e8;
      }
      .error {
        color: #b10000;
        font-weight: 600;
        margin-top: 8px;
      }
      .info {
        color: #555;
        margin-top: 6px;
      }
    </style>
  </head>
  <body>
    <header>ORMANET UPSELLING</header>
    <div class="container">
      <div class="panel">
        <h3>Stato</h3>
        <ul class="status-list" id="statusList"></ul>
        <div class="actions">
          <button id="loadDefaults">Carica default</button>
        </div>
        <label>Cliente</label>
        <select id="clientSelect"></select>
        <label>Ordine Upsell</label>
        <select id="orderSelect"></select>
        <label>Ordini Storici (4)</label>
        <div class="history-meta">
          <div id="historyCounter">Selezionati: 0/4</div>
          <div class="history-help">Seleziona esattamente 4 file STORICO</div>
        </div>
        <div id="historyList" class="history-list"></div>
        <label>Causale</label>
        <select id="causaleSelect">
          <option value="DISPONIBILE">DISPONIBILE</option>
          <option value="IN ARRIVO">IN ARRIVO</option>
          <option value="PROGRAMMATO">PROGRAMMATO</option>
        </select>
        <label>Aggressività sconto</label>
        <select id="aggressivitaSelect">
          <option value="0">0</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
        </select>
        <div class="actions">
          <button id="computeBtn">Calcola upsell</button>
          <button id="copyBtn" class="secondary">Copia valori</button>
          <button id="exportBtn" class="secondary">Export Excel</button>
          <button id="openOutputBtn" class="secondary">Apri cartella output</button>
        </div>
        <div class="error" id="errorBox"></div>
        <div class="info" id="infoBox"></div>
      </div>
      <div class="panel">
        <h3>Risultati</h3>
        <table>
          <thead>
            <tr>
              <th>Codice</th>
              <th>Descrizione</th>
              <th>Qty</th>
              <th>Prezzo unit (ex VAT)</th>
              <th>Ric % richiesto</th>
              <th>Totale (ex VAT)</th>
              <th>Disp.</th>
              <th>Disponibile dal</th>
            </tr>
          </thead>
          <tbody id="resultsBody"></tbody>
        </table>
      </div>
    </div>
    <script>
      const statusList = document.getElementById("statusList");
      const clientSelect = document.getElementById("clientSelect");
      const orderSelect = document.getElementById("orderSelect");
      const historyList = document.getElementById("historyList");
      const historyCounter = document.getElementById("historyCounter");
      const causaleSelect = document.getElementById("causaleSelect");
      const aggressivitaSelect = document.getElementById("aggressivitaSelect");
      const computeBtn = document.getElementById("computeBtn");
      const copyBtn = document.getElementById("copyBtn");
      const exportBtn = document.getElementById("exportBtn");
      const openOutputBtn = document.getElementById("openOutputBtn");
      const errorBox = document.getElementById("errorBox");
      const infoBox = document.getElementById("infoBox");
      const resultsBody = document.getElementById("resultsBody");
      let copyBlock = "";

      function setError(message) {
        errorBox.textContent = message || "";
      }

      function setInfo(message) {
        infoBox.textContent = message || "";
      }

      async function api(path, payload) {
        const res = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload || {})
        });
        return res.json();
      }

      function renderStatus(status) {
        statusList.innerHTML = "";
        const items = [
          ["Clienti caricati", status.clients_loaded],
          ["Stock caricato", status.stock_loaded],
          [`Storici selezionati (${status.histories_selected_count}/4)`, status.histories_ok],
          ["Ordine upsell caricato", status.order_loaded],
          ["Causale selezionata", status.causale_set],
          ["Cliente selezionato", status.client_selected]
        ];
        items.forEach(([label, ok]) => {
          const li = document.createElement("li");
          li.textContent = label + (ok ? " ✓" : " ✗");
          li.className = ok ? "status-ok" : "status-missing";
          statusList.appendChild(li);
        });
        computeBtn.disabled = !status.ready_to_compute;
        copyBtn.disabled = !status.has_results;
        exportBtn.disabled = !status.has_results;
      }

      function renderTable(rows) {
        resultsBody.innerHTML = "";
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          ["codice","descrizione","qty","prezzo_unit","required_ric","totale","disp","disponibile_dal"].forEach((key) => {
            const td = document.createElement("td");
            td.textContent = row[key] ?? "";
            tr.appendChild(td);
          });
          resultsBody.appendChild(tr);
        });
      }

      function populateSelect(select, options, placeholder) {
        select.innerHTML = "";
        if (placeholder) {
          const opt = document.createElement("option");
          opt.value = "";
          opt.textContent = placeholder;
          select.appendChild(opt);
        }
        options.forEach((optData) => {
          const opt = document.createElement("option");
          opt.value = optData.value;
          opt.textContent = optData.label;
          select.appendChild(opt);
        });
      }

      async function refreshStatus() {
        const status = await api("/api/status");
        renderStatus(status);
        populateSelect(clientSelect, status.clients, "Seleziona cliente");
        populateSelect(orderSelect, status.upsell_orders, "Seleziona ordine");
        renderHistoryList(status.storico_orders, status.selected_histories);
        if (status.selected_client) {
          clientSelect.value = status.selected_client;
        }
        if (status.selected_order) {
          orderSelect.value = status.selected_order;
        }
        if (status.causale) {
          causaleSelect.value = status.causale;
        }
        if (status.aggressivita !== null && status.aggressivita !== undefined) {
          aggressivitaSelect.value = String(status.aggressivita);
        }
      }

      function updateHistoryCounter(selectedCount) {
        historyCounter.textContent = `Selezionati: ${selectedCount}/4`;
      }

      function renderHistoryList(options, selected) {
        historyList.innerHTML = "";
        const selectedSet = new Set(selected || []);
        options.forEach((optData) => {
          const wrapper = document.createElement("label");
          wrapper.className = "history-item";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.name = "storici";
          checkbox.value = optData.value;
          checkbox.checked = selectedSet.has(optData.value);
          checkbox.addEventListener("change", onHistoryChange);
          const text = document.createElement("span");
          text.textContent = optData.label;
          wrapper.appendChild(checkbox);
          wrapper.appendChild(text);
          historyList.appendChild(wrapper);
        });
        updateHistoryCounter(selectedSet.size);
      }

      async function onHistoryChange(event) {
        setError("");
        const selected = [...historyList.querySelectorAll('input[name="storici"]:checked')].map(
          (input) => input.value
        );
        if (selected.length > 4) {
          event.target.checked = false;
          setError("Puoi selezionare al massimo 4 storici.");
          return;
        }
        updateHistoryCounter(selected.length);
        const res = await api("/api/set_histories", { histories: selected });
        if (res.ok === false || res.success === false) {
          setError(res.error || "Errore selezione storici");
        }
        await refreshStatus();
      }

      document.getElementById("loadDefaults").addEventListener("click", async () => {
        setError("");
        const res = await api("/api/load");
        if (!res.success) {
          setError(res.error || "Errore caricamento default");
        } else {
          setInfo(res.message || "Caricamento completato");
        }
        await refreshStatus();
      });

      clientSelect.addEventListener("change", async () => {
        setError("");
        await api("/api/select_client", { client_id: clientSelect.value });
        await refreshStatus();
      });

      orderSelect.addEventListener("change", async () => {
        setError("");
        await api("/api/set_order", { order_name: orderSelect.value });
        await refreshStatus();
      });

      causaleSelect.addEventListener("change", async () => {
        await api("/api/set_causale", { causale: causaleSelect.value });
        await refreshStatus();
      });

      aggressivitaSelect.addEventListener("change", async () => {
        await api("/api/set_aggressivita", { aggressivita: Number(aggressivitaSelect.value) });
        await refreshStatus();
      });

      computeBtn.addEventListener("click", async () => {
        setError("");
        setInfo("");
        const res = await api("/api/compute");
        if (!res.success) {
          setError(res.error || "Errore calcolo");
          return;
        }
        copyBlock = res.copy_block || "";
        renderTable(res.rows || []);
        await refreshStatus();
      });

      copyBtn.addEventListener("click", async () => {
        setError("");
        if (!copyBlock) {
          setError("Nessun testo da copiare");
          return;
        }
        try {
          await navigator.clipboard.writeText(copyBlock);
          setInfo("Valori copiati negli appunti");
        } catch (err) {
          setError("Copia non riuscita");
        }
      });

      exportBtn.addEventListener("click", async () => {
        setError("");
        const res = await api("/api/export");
        if (!res.success) {
          setError(res.error || "Errore export");
        } else {
          setInfo(res.message || "Export completato");
        }
      });

      openOutputBtn.addEventListener("click", async () => {
        await api("/api/open_output");
      });

      refreshStatus();
    </script>
  </body>
</html>
"""
