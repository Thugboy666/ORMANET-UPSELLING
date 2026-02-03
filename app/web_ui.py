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
      .main-panel {
        display: flex;
        flex-direction: column;
        gap: 16px;
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
      .actions.inline {
        grid-template-columns: repeat(2, 1fr);
      }
      .mapping-button {
        margin-top: 12px;
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
      .table-wrapper {
        overflow-x: auto;
      }
      .controls {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        background: #fffaf5;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #f0d6bf;
      }
      .controls label {
        margin-top: 0;
      }
      .controls input,
      .controls select {
        width: 100%;
        padding: 6px 8px;
        border-radius: 6px;
        border: 1px solid #ddd;
      }
      .controls .inline {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .controls .value {
        font-weight: 600;
        font-size: 13px;
      }
      .row-error {
        background: #fff0f0;
      }
      .row-error td {
        color: #9b0000;
      }
      .lock-cell {
        text-align: center;
      }
      .warning {
        color: #7a2d00;
        font-weight: 600;
      }
      .trace-panel {
        background: #fffaf5;
        border: 1px solid #f0d6bf;
        border-radius: 8px;
        padding: 12px;
      }
      .trace-panel details {
        margin-top: 8px;
      }
      .trace-panel summary {
        cursor: pointer;
        font-weight: 600;
      }
      .trace-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 8px;
        margin-top: 8px;
        font-size: 13px;
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
      .modal {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.55);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 1000;
      }
      .modal.active {
        display: flex;
      }
      .modal-content {
        background: var(--white);
        width: min(900px, 92vw);
        max-height: 90vh;
        overflow: hidden;
        border-radius: 10px;
        display: flex;
        flex-direction: column;
      }
      .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background: #fff4e8;
        border-bottom: 1px solid #f0d6bf;
      }
      .modal-body {
        padding: 16px;
        overflow-y: auto;
      }
      .tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
      }
      .tab {
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid #ddd;
        background: #fff;
        cursor: pointer;
        font-weight: 600;
      }
      .tab.active {
        background: var(--orange);
        color: var(--black);
      }
      .mapping-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 12px;
      }
      .mapping-table th,
      .mapping-table td {
        border-bottom: 1px solid #eee;
        padding: 6px 8px;
        font-size: 13px;
      }
      .mapping-table th {
        background: #fffaf5;
      }
      .mapping-table input {
        width: 100%;
        padding: 6px;
        border-radius: 6px;
        border: 1px solid #ddd;
      }
      .required-badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 11px;
        border-radius: 10px;
        background: #ffe0c2;
        color: #7a2d00;
        margin-left: 6px;
      }
      .mapping-results {
        margin-top: 12px;
        font-size: 13px;
      }
      .mapping-results .missing {
        color: #b10000;
        font-weight: 600;
      }
      .mapping-results .ok {
        color: #0a7d2c;
        font-weight: 600;
      }
      .mapping-actions {
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        margin-top: 8px;
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
        <div class="actions">
          <button id="computeBtn">Calcola upsell</button>
          <button id="copyBtn" class="secondary">Copia valori</button>
          <button id="exportBtn" class="secondary">Export Excel</button>
          <button id="openOutputBtn" class="secondary">Apri cartella output</button>
        </div>
        <div class="actions">
          <button id="mappingBtn" class="secondary">Mappa campi</button>
        </div>
        <div class="error" id="errorBox"></div>
        <div class="info" id="infoBox"></div>
      </div>
      <div class="panel main-panel">
        <h3>Preventivo (Quote)</h3>
        <div class="controls">
          <div>
            <label for="aggressivityRange">Aggressività (0-100)</label>
            <div class="inline">
              <input type="range" id="aggressivityRange" min="0" max="100" value="0" />
              <span class="value" id="aggressivityValue">0</span>
            </div>
          </div>
          <div>
            <label for="aggressivityMode">Modalità aggressività</label>
            <select id="aggressivityMode">
              <option value="discount_from_baseline">Sconto da baseline</option>
              <option value="target_ric_reduction">Riduzione ric target</option>
            </select>
          </div>
          <div>
            <label for="bufferRic">Buffer ric (%)</label>
            <input type="number" id="bufferRic" min="0" step="0.1" value="2" />
          </div>
          <div>
            <label for="maxDiscount">Max sconto (%)</label>
            <input type="number" id="maxDiscount" min="0" step="0.1" value="10" />
          </div>
          <div>
            <label for="roundingMode">Arrotondamento</label>
            <select id="roundingMode">
              <option value="NONE">NONE</option>
              <option value="0.01">0.01</option>
              <option value="0.05">0.05</option>
              <option value="0.10">0.10</option>
            </select>
          </div>
          <div class="actions inline">
            <button id="recalcBtn">Ricalcola</button>
            <button id="resetOverridesBtn" class="secondary">Reset override</button>
          </div>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Lock</th>
                <th>Codice</th>
                <th>Descrizione</th>
                <th>Qty</th>
                <th>Listino</th>
                <th>Baseline</th>
                <th>Sconto %</th>
                <th>Prezzo unit (ex VAT)</th>
                <th>Ric % finale</th>
                <th>Ric % minimo</th>
                <th>Totale</th>
                <th>Disp.</th>
                <th>Disponibile dal</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody id="resultsBody"></tbody>
          </table>
        </div>
        <div class="error" id="validationBox"></div>
        <div class="warning" id="warningBox"></div>
        <div class="trace-panel">
          <details open>
            <summary>Explain / Debug</summary>
            <div id="traceSummary" class="trace-grid"></div>
            <div id="traceRows"></div>
          </details>
        </div>
      </div>
    </div>
    <div class="modal" id="mappingModal" aria-hidden="true">
      <div class="modal-content">
        <div class="modal-header">
          <strong>Field Mapping</strong>
          <button id="closeMapping" class="secondary">Chiudi</button>
        </div>
        <div class="modal-body">
          <div class="tabs" id="mappingTabs"></div>
          <div id="mappingFields"></div>
          <div class="mapping-actions">
            <button id="saveMapping">Salva mapping</button>
            <button id="reloadMapping" class="secondary">Ricarica mapping</button>
            <button id="resetMapping" class="secondary">Reset default</button>
            <button id="testMapping" class="secondary">Test mapping</button>
          </div>
          <div class="mapping-results" id="mappingResults"></div>
          <div class="error" id="mappingError"></div>
          <div class="info" id="mappingInfo"></div>
        </div>
      </div>
    </div>
    <script>
      const statusList = document.getElementById("statusList");
      const clientSelect = document.getElementById("clientSelect");
      const orderSelect = document.getElementById("orderSelect");
      const historyList = document.getElementById("historyList");
      const historyCounter = document.getElementById("historyCounter");
      const causaleSelect = document.getElementById("causaleSelect");
      const computeBtn = document.getElementById("computeBtn");
      const copyBtn = document.getElementById("copyBtn");
      const exportBtn = document.getElementById("exportBtn");
      const openOutputBtn = document.getElementById("openOutputBtn");
      const errorBox = document.getElementById("errorBox");
      const infoBox = document.getElementById("infoBox");
      const resultsBody = document.getElementById("resultsBody");
      const validationBox = document.getElementById("validationBox");
      const warningBox = document.getElementById("warningBox");
      const mappingBtn = document.getElementById("mappingBtn");
      const mappingModal = document.getElementById("mappingModal");
      const closeMapping = document.getElementById("closeMapping");
      const mappingTabs = document.getElementById("mappingTabs");
      const mappingFields = document.getElementById("mappingFields");
      const mappingResults = document.getElementById("mappingResults");
      const mappingError = document.getElementById("mappingError");
      const mappingInfo = document.getElementById("mappingInfo");
      const saveMappingBtn = document.getElementById("saveMapping");
      const reloadMappingBtn = document.getElementById("reloadMapping");
      const resetMappingBtn = document.getElementById("resetMapping");
      const testMappingBtn = document.getElementById("testMapping");
      const aggressivityRange = document.getElementById("aggressivityRange");
      const aggressivityValue = document.getElementById("aggressivityValue");
      const aggressivityMode = document.getElementById("aggressivityMode");
      const bufferRic = document.getElementById("bufferRic");
      const maxDiscount = document.getElementById("maxDiscount");
      const roundingMode = document.getElementById("roundingMode");
      const recalcBtn = document.getElementById("recalcBtn");
      const resetOverridesBtn = document.getElementById("resetOverridesBtn");
      const traceSummary = document.getElementById("traceSummary");
      const traceRows = document.getElementById("traceRows");
      let copyBlock = "";
      let mappingData = {};
      let activeMappingTab = "ORDINI";
      let globalParams = {
        aggressivity: 0,
        aggressivity_mode: "discount_from_baseline",
        max_discount_percent: 10,
        buffer_ric: 2,
        rounding: 0.01
      };
      let perRowOverrides = {};
      let lastValidation = { ok: true, errors: [] };

      const requiredFields = {
        ORDINI: ["codice", "qty", "prezzo_unit_exvat"],
        STOCK: ["codice", "disp"],
        CLIENTI: ["id", "ragione_sociale", "listino"]
      };
      const stockListinoGroup = ["listino_ri", "listino_ri10", "listino_di"];

      function setError(message) {
        errorBox.textContent = message || "";
      }

      function setInfo(message) {
        infoBox.textContent = message || "";
      }

      function setValidation(message) {
        validationBox.textContent = message || "";
      }

      function setWarning(message) {
        warningBox.textContent = message || "";
      }

      async function api(path, payload) {
        const res = await fetch(path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload || {})
        });
        return res.json();
      }

      function debounce(fn, delay) {
        let timer;
        return (...args) => {
          clearTimeout(timer);
          timer = setTimeout(() => fn(...args), delay);
        };
      }

      function setMappingError(message) {
        mappingError.textContent = message || "";
      }

      function setMappingInfo(message) {
        mappingInfo.textContent = message || "";
      }

      function setMappingResults(html) {
        mappingResults.innerHTML = html || "";
      }

      function openMappingModal() {
        mappingModal.classList.add("active");
        mappingModal.setAttribute("aria-hidden", "false");
      }

      function closeMappingModal() {
        mappingModal.classList.remove("active");
        mappingModal.setAttribute("aria-hidden", "true");
      }

      function renderMappingTabs() {
        mappingTabs.innerHTML = "";
        Object.keys(mappingData).forEach((key) => {
          const btn = document.createElement("button");
          btn.className = "tab" + (key === activeMappingTab ? " active" : "");
          btn.textContent = key;
          btn.addEventListener("click", () => {
            collectMappingFromUI();
            activeMappingTab = key;
            renderMappingTabs();
            renderMappingFields();
            setMappingResults("");
          });
          mappingTabs.appendChild(btn);
        });
      }

      function renderMappingFields() {
        mappingFields.innerHTML = "";
        const section = mappingData[activeMappingTab] || {};
        const table = document.createElement("table");
        table.className = "mapping-table";
        table.innerHTML = `
          <thead>
            <tr>
              <th>Campo logico</th>
              <th>Alias (separati da virgola)</th>
            </tr>
          </thead>
        `;
        const tbody = document.createElement("tbody");
        Object.keys(section).forEach((field) => {
          const tr = document.createElement("tr");
          const labelCell = document.createElement("td");
          const label = document.createElement("span");
          label.textContent = field;
          if (requiredFields[activeMappingTab]?.includes(field)) {
            const badge = document.createElement("span");
            badge.className = "required-badge";
            badge.textContent = "Required";
            labelCell.appendChild(label);
            labelCell.appendChild(badge);
          } else if (activeMappingTab === "STOCK" && stockListinoGroup.includes(field)) {
            const badge = document.createElement("span");
            badge.className = "required-badge";
            badge.textContent = "Required (uno tra listini)";
            labelCell.appendChild(label);
            labelCell.appendChild(badge);
          } else {
            labelCell.appendChild(label);
          }
          const inputCell = document.createElement("td");
          const input = document.createElement("input");
          input.type = "text";
          input.dataset.mappingField = field;
          input.value = (section[field] || []).join(", ");
          inputCell.appendChild(input);
          tr.appendChild(labelCell);
          tr.appendChild(inputCell);
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        mappingFields.appendChild(table);
      }

      function collectMappingFromUI() {
        const section = mappingData[activeMappingTab] || {};
        const inputs = mappingFields.querySelectorAll("input[data-mapping-field]");
        inputs.forEach((input) => {
          const field = input.dataset.mappingField;
          if (!field) {
            return;
          }
          const aliases = input.value
            .split(",")
            .map((value) => value.trim())
            .filter((value) => value.length > 0);
          section[field] = aliases;
        });
        mappingData[activeMappingTab] = section;
      }

      function buildTestResults(results) {
        let html = "";
        Object.keys(results).forEach((sectionKey) => {
          const items = results[sectionKey] || [];
          if (!items.length) {
            return;
          }
          html += `<div><strong>${sectionKey}</strong></div>`;
          items.forEach((item) => {
            html += `<div>File: <strong>${item.file}</strong></div>`;
            const missing = item.missing_required || [];
            if (missing.length) {
              html += `<div class="missing">Mancanti: ${missing.join(", ")}</div>`;
            } else {
              html += `<div class="ok">Tutti i campi richiesti trovati</div>`;
            }
            html += "<ul>";
            Object.keys(item.matches || {}).forEach((field) => {
              const match = item.matches[field] || "NOT FOUND";
              html += `<li>${field}: ${match}</li>`;
            });
            html += "</ul>";
          });
        });
        return html;
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
        exportBtn.disabled = !status.has_results || !lastValidation.ok;
        recalcBtn.disabled = !status.has_results;
        resetOverridesBtn.disabled = !status.has_results;
      }

      function syncControls() {
        aggressivityRange.value = globalParams.aggressivity;
        aggressivityValue.textContent = globalParams.aggressivity;
        aggressivityMode.value = globalParams.aggressivity_mode;
        bufferRic.value = globalParams.buffer_ric;
        maxDiscount.value = globalParams.max_discount_percent;
        roundingMode.value =
          globalParams.rounding === null || globalParams.rounding === undefined
            ? "NONE"
            : String(globalParams.rounding);
      }

      function renderTable(rows, validation) {
        resultsBody.innerHTML = "";
        const errorSkus = new Set((validation?.errors || []).map((err) => err.sku));
        rows.forEach((row) => {
          const tr = document.createElement("tr");
          if (errorSkus.has(row.codice)) {
            tr.classList.add("row-error");
          }
          const lockCell = document.createElement("td");
          lockCell.className = "lock-cell";
          const lockInput = document.createElement("input");
          lockInput.type = "checkbox";
          lockInput.checked = Boolean(perRowOverrides[row.codice]?.lock);
          lockInput.addEventListener("change", () => {
            const override = perRowOverrides[row.codice] || {};
            override.lock = lockInput.checked;
            if (override.lock) {
              override.unit_price_override = Number(row.prezzo_unit);
              delete override.discount_override;
            } else {
              delete override.unit_price_override;
              delete override.discount_override;
            }
            perRowOverrides[row.codice] = override;
            scheduleRecalc();
          });
          lockCell.appendChild(lockInput);
          tr.appendChild(lockCell);

          const cells = [
            row.codice,
            row.descrizione
          ];
          cells.forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value ?? "";
            tr.appendChild(td);
          });

          const qtyCell = document.createElement("td");
          const qtyInput = document.createElement("input");
          qtyInput.type = "number";
          qtyInput.min = "1";
          qtyInput.step = "1";
          qtyInput.value = row.qty;
          qtyInput.addEventListener("change", () => {
            const override = perRowOverrides[row.codice] || {};
            override.qty = Number(qtyInput.value);
            perRowOverrides[row.codice] = override;
            scheduleRecalc();
          });
          qtyCell.appendChild(qtyInput);
          tr.appendChild(qtyCell);

          const listinoCell = document.createElement("td");
          listinoCell.textContent = Number(row.listino_value).toFixed(2);
          tr.appendChild(listinoCell);

          const baselineCell = document.createElement("td");
          baselineCell.textContent = Number(row.baseline_price).toFixed(2);
          tr.appendChild(baselineCell);

          const discountCell = document.createElement("td");
          const discountInput = document.createElement("input");
          discountInput.type = "number";
          discountInput.step = "0.1";
          discountInput.min = "0";
          discountInput.value = Number(row.applied_discount_percent).toFixed(2);
          discountInput.addEventListener("change", () => {
            const override = perRowOverrides[row.codice] || {};
            override.discount_override = Number(discountInput.value);
            delete override.unit_price_override;
            perRowOverrides[row.codice] = override;
            scheduleRecalc();
          });
          discountCell.appendChild(discountInput);
          tr.appendChild(discountCell);

          const priceCell = document.createElement("td");
          const priceInput = document.createElement("input");
          priceInput.type = "number";
          priceInput.step = "0.01";
          priceInput.min = "0";
          priceInput.value = Number(row.prezzo_unit).toFixed(2);
          priceInput.addEventListener("change", () => {
            const override = perRowOverrides[row.codice] || {};
            override.unit_price_override = Number(priceInput.value);
            delete override.discount_override;
            perRowOverrides[row.codice] = override;
            scheduleRecalc();
          });
          priceCell.appendChild(priceInput);
          tr.appendChild(priceCell);

          const ricCell = document.createElement("td");
          ricCell.textContent = Number(row.final_ric_percent).toFixed(2);
          tr.appendChild(ricCell);

          const ricMinCell = document.createElement("td");
          ricMinCell.textContent = Number(row.required_ric).toFixed(2);
          tr.appendChild(ricMinCell);

          const totalCell = document.createElement("td");
          totalCell.textContent = Number(row.totale).toFixed(2);
          tr.appendChild(totalCell);

          const dispCell = document.createElement("td");
          dispCell.textContent = Number(row.disp).toFixed(2);
          tr.appendChild(dispCell);

          const availCell = document.createElement("td");
          availCell.textContent = row.disponibile_dal || "";
          tr.appendChild(availCell);

          const noteCell = document.createElement("td");
          if (row.clamp_reason === "MIN_RIC_FLOOR") {
            noteCell.textContent = `Sconto bloccato: ric minimo ${Number(row.required_ric).toFixed(2)}%`;
          } else if (row.clamp_reason === "BELOW_MIN_PRICE") {
            noteCell.textContent = `Prezzo sotto minimo ${Number(row.min_unit_price).toFixed(2)}`;
          } else if (row.clamp_reason) {
            noteCell.textContent = row.clamp_reason;
          } else {
            noteCell.textContent = "";
          }
          tr.appendChild(noteCell);

          resultsBody.appendChild(tr);
        });
      }

      function renderTrace(trace) {
        traceSummary.innerHTML = "";
        traceRows.innerHTML = "";
        const global = trace?.global || {};
        const pricing = global.pricing || {};
        const summaryItems = [
          ["Cliente", `${global.ragione_sociale || ""} (${global.client_id || ""})`],
          ["Listino", global.listino || ""],
          ["Listino key", global.listino_key || ""],
          ["Causale", global.causale || ""],
          ["Aggressività", pricing.aggressivity ?? ""],
          ["Modalità", pricing.aggressivity_mode ?? ""],
          ["Max sconto", pricing.max_discount_percent ?? ""],
          ["Buffer ric", pricing.buffer_ric ?? ""],
          ["Arrotondamento", pricing.rounding ?? ""]
        ];
        summaryItems.forEach(([label, value]) => {
          const div = document.createElement("div");
          div.innerHTML = `<strong>${label}:</strong> ${value}`;
          traceSummary.appendChild(div);
        });

        (trace?.rows || []).forEach((row) => {
          const details = document.createElement("details");
          const summary = document.createElement("summary");
          summary.textContent = `${row.sku} - ${row.macro_categoria || ""}`;
          details.appendChild(summary);
          const content = document.createElement("div");
          content.className = "trace-grid";
          const fields = [
            ["Categoria", row.categoria],
            ["Selezione", row.selection_reason],
            ["Listino", row.listino_value],
            ["Ric richiesto", row.required_ric],
            ["Baseline", row.baseline_price],
            ["Buffer ric", row.buffer_ric],
            ["Aggressività", row.aggressivity],
            ["Modalità", row.aggressivity_mode],
            ["Max sconto", row.max_discount_percent],
            ["Sconto override", row.discount_override],
            ["Prezzo override", row.unit_price_override],
            ["Sconto applicato", row.applied_discount_percent],
            ["Floor price", row.floor_price],
            ["Clamp reason", row.clamp_reason],
            ["Prezzo finale", row.final_price],
            ["Ric finale", row.final_ric_percent],
            ["Qty", row.qty],
            ["Stock source", `${row.stock_source?.file || "-"}:${row.stock_source?.row || "-"}`],
            ["Order source", `${row.order_source?.file || "-"}:${row.order_source?.row || "-"}`],
            ["Occorrenze storico", row.history_occurrences]
          ];
          fields.forEach(([label, value]) => {
            const div = document.createElement("div");
            div.innerHTML = `<strong>${label}:</strong> ${value ?? ""}`;
            content.appendChild(div);
          });
          details.appendChild(content);
          traceRows.appendChild(details);
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
        if (status.pricing) {
          globalParams = {
            aggressivity: status.pricing.aggressivity ?? globalParams.aggressivity,
            aggressivity_mode: status.pricing.aggressivity_mode ?? globalParams.aggressivity_mode,
            max_discount_percent: status.pricing.max_discount_percent ?? globalParams.max_discount_percent,
            buffer_ric: status.pricing.buffer_ric ?? globalParams.buffer_ric,
            rounding: status.pricing.rounding ?? globalParams.rounding
          };
          syncControls();
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

      function applyQuoteResponse(res) {
        if (!res || !res.quote) {
          return;
        }
        copyBlock = res.copy_block || copyBlock;
        lastValidation = res.validation || { ok: true, errors: [] };
        const validationErrors = (lastValidation.errors || [])
          .map((err) => `${err.sku}: minimo ${Number(err.min_unit_price).toFixed(2)}`)
          .join(" | ");
        setValidation(lastValidation.ok ? "" : `Errore ric minimo: ${validationErrors}`);
        const warnings = (res.warnings || []).join(" | ");
        setWarning(warnings);
        renderTable(res.quote, lastValidation);
        renderTrace(res.trace || {});
        exportBtn.disabled = !lastValidation.ok;
      }

      async function recalcQuote() {
        const res = await api("/api/recalc", {
          global_params: globalParams,
          per_row_overrides: perRowOverrides
        });
        if (res.ok === false) {
          setError(res.error || "Errore ricalcolo");
          return;
        }
        applyQuoteResponse(res);
      }

      const scheduleRecalc = debounce(recalcQuote, 300);

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
          setError(res.message || res.error || "Errore caricamento default");
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

      computeBtn.addEventListener("click", async () => {
        setError("");
        setInfo("");
        const res = await api("/api/compute");
        if (res.ok === false || res.success === false) {
          setError(res.message || res.error || "Errore calcolo");
          return;
        }
        globalParams = res.pricing || globalParams;
        syncControls();
        perRowOverrides = {};
        applyQuoteResponse(res);
        await refreshStatus();
      });

      recalcBtn.addEventListener("click", async () => {
        setError("");
        await recalcQuote();
      });

      resetOverridesBtn.addEventListener("click", async () => {
        perRowOverrides = {};
        await recalcQuote();
      });

      aggressivityRange.addEventListener("input", () => {
        globalParams.aggressivity = Number(aggressivityRange.value);
        aggressivityValue.textContent = aggressivityRange.value;
        scheduleRecalc();
      });

      aggressivityMode.addEventListener("change", () => {
        globalParams.aggressivity_mode = aggressivityMode.value;
        scheduleRecalc();
      });

      bufferRic.addEventListener("change", () => {
        globalParams.buffer_ric = Number(bufferRic.value);
        scheduleRecalc();
      });

      maxDiscount.addEventListener("change", () => {
        globalParams.max_discount_percent = Number(maxDiscount.value);
        scheduleRecalc();
      });

      roundingMode.addEventListener("change", () => {
        const value = roundingMode.value;
        globalParams.rounding = value === "NONE" ? null : Number(value);
        scheduleRecalc();
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

      mappingBtn.addEventListener("click", async () => {
        setMappingError("");
        setMappingInfo("");
        setMappingResults("");
        const res = await api("/api/mapping/get");
        if (!res.ok) {
          setMappingError(res.message || "Errore caricamento mapping");
          return;
        }
        mappingData = res.mapping || {};
        activeMappingTab = Object.keys(mappingData)[0] || "ORDINI";
        renderMappingTabs();
        renderMappingFields();
        openMappingModal();
      });

      closeMapping.addEventListener("click", () => {
        closeMappingModal();
      });

      saveMappingBtn.addEventListener("click", async () => {
        setMappingError("");
        setMappingInfo("");
        collectMappingFromUI();
        const res = await api("/api/mapping/save", { mapping: mappingData });
        if (!res.ok) {
          setMappingError(res.message || "Errore salvataggio mapping");
          return;
        }
        mappingData = res.mapping || mappingData;
        setMappingInfo("Mapping salvato");
      });

      reloadMappingBtn.addEventListener("click", async () => {
        setMappingError("");
        setMappingInfo("");
        const res = await api("/api/mapping/load");
        if (!res.ok) {
          setMappingError(res.message || "Errore ricarica mapping");
          return;
        }
        mappingData = res.mapping || {};
        renderMappingTabs();
        renderMappingFields();
        setMappingInfo("Mapping ricaricato");
      });

      resetMappingBtn.addEventListener("click", async () => {
        setMappingError("");
        setMappingInfo("");
        const res = await api("/api/mapping/reset");
        if (!res.ok) {
          setMappingError(res.message || "Errore reset mapping");
          return;
        }
        mappingData = res.mapping || {};
        renderMappingTabs();
        renderMappingFields();
        setMappingInfo("Mapping resettato ai default");
      });

      testMappingBtn.addEventListener("click", async () => {
        setMappingError("");
        setMappingInfo("");
        collectMappingFromUI();
        const res = await api("/api/mapping/test", { mapping: mappingData });
        if (!res.ok) {
          setMappingError(res.message || "Errore test mapping");
          setMappingResults(buildTestResults(res.results || {}));
          return;
        }
        setMappingResults(buildTestResults(res.results || {}));
      });

      refreshStatus();
    </script>
  </body>
</html>
"""
