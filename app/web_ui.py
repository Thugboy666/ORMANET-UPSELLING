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
      .guide-steps {
        list-style: none;
        padding: 0;
        margin: 12px 0 16px;
        font-size: 12px;
      }
      .guide-steps li {
        margin-bottom: 6px;
        display: flex;
        gap: 8px;
        align-items: flex-start;
      }
      .step-badge {
        background: #ffe0c2;
        color: #7a2d00;
        font-weight: 700;
        font-size: 11px;
        border-radius: 999px;
        padding: 2px 6px;
      }
      .banner {
        padding: 10px 12px;
        border-radius: 6px;
        margin-top: 12px;
        font-size: 13px;
      }
      .banner.warning {
        background: #fff4e0;
        color: #7a2d00;
        border: 1px solid #f0d6bf;
      }
      .banner.error {
        background: #ffecec;
        color: #9b0000;
        border: 1px solid #f3c0c0;
      }
      .inline-toggle {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        margin-top: 6px;
      }
      .ric-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 12px;
      }
      .ric-table th,
      .ric-table td {
        border-bottom: 1px solid #eee;
        padding: 6px 8px;
        font-size: 13px;
      }
      .ric-table th {
        background: #fffaf5;
      }
      .ric-table input {
        width: 100%;
        padding: 6px;
        border-radius: 6px;
        border: 1px solid #ddd;
      }
      .ric-help {
        font-size: 13px;
        color: #444;
        margin-bottom: 10px;
      }
      .ric-help strong {
        color: #7a2d00;
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
        <h4>Guida rapida</h4>
        <ul class="guide-steps">
          <li><span class="step-badge">1</span>Carica clienti/stock/ordini</li>
          <li><span class="step-badge">2</span>Seleziona cliente, ordine, 4 storici</li>
          <li><span class="step-badge">3</span>Controlla margini (RIC) se necessario</li>
          <li><span class="step-badge">4</span>Imposta aggressività / sconto</li>
          <li><span class="step-badge">5</span>Verifica righe (note clamp) e modifica se serve</li>
          <li><span class="step-badge">6</span>Esporta</li>
        </ul>
        <div class="actions">
          <button id="loadDefaults">Carica default</button>
          <button id="ricParamsBtn" class="secondary">Parametri margini (RIC)</button>
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
            <label for="aggressivityRange" title="Aumenta lo sconto commerciale (entro i limiti di ric minimo).">
              Aggressività (0-100)
            </label>
            <div class="inline">
              <input type="range" id="aggressivityRange" min="0" max="100" value="0" />
              <span class="value" id="aggressivityValue">0</span>
            </div>
          </div>
          <div>
            <label for="priceMode">Modalità prezzo</label>
            <select id="priceMode">
              <option value="discount">Sconto %</option>
              <option value="final_price">Prezzo finale</option>
            </select>
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
            <input type="number" id="bufferRic" min="0" step="0.1" value="2" readonly />
            <label class="inline-toggle">
              <input type="checkbox" id="bufferRicOverrideToggle" />
              Override avanzato
            </label>
          </div>
          <div>
            <label for="maxDiscount" title="Cap massimo aggiuntivo, non può superare il max reale calcolato.">
              Max sconto (%)
            </label>
            <input type="number" id="maxDiscount" min="0" step="0.1" value="10" />
            <div class="info" id="maxDiscountHint"></div>
          </div>
          <div>
            <label for="roundingMode" title="Arrotonda il prezzo finale senza scendere sotto il pavimento.">
              Arrotondamento
            </label>
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
          <div class="actions inline">
            <label class="inline">
              <input type="checkbox" id="toggleTrace" checked />
              Mostra dettagli
            </label>
          </div>
        </div>
        <div class="banner warning" id="clampBanner" style="display:none"></div>
        <div class="banner error" id="ricOverrideBanner" style="display:none"></div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Lock</th>
                <th>Codice</th>
                <th>Descrizione</th>
                <th>Qty</th>
                <th>LM</th>
                <th>Sconto fisso (SCONTI2026)</th>
                <th>Prezzo baseline (RIC.BASE)</th>
                <th>Prezzo minimo (RIC.)</th>
                <th>Sconto commerciale</th>
                <th>Prezzo finale</th>
                <th>Ric % finale</th>
                <th>Ric % minimo</th>
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
            <summary>Passaggi di calcolo</summary>
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
    <div class="modal" id="ricModal" aria-hidden="true">
      <div class="modal-content">
        <div class="modal-header">
          <strong>Parametri margini (RIC)</strong>
          <button id="closeRic" class="secondary">Chiudi</button>
        </div>
        <div class="modal-body">
          <div class="ric-help">
            <p><strong>RIC.BASE</strong>: È il ricarico di partenza: da qui parte il prezzo “standard” prima dello sconto commerciale. Più alto = più spazio per scontare senza scendere sotto il minimo.</p>
            <p><strong>RIC (minimo)</strong>: È il ricarico minimo accettabile: sotto questo valore NON si può scendere. È il pavimento anti-perdita.</p>
            <p><strong>Relazione</strong>: Lo sconto commerciale può muoversi solo tra RIC.BASE e RIC.</p>
            <p id="ricExample" class="info"></p>
          </div>
          <label class="inline-toggle">
            <input type="checkbox" id="ricOverrideToggle" />
            Override manuale (avanzato)
          </label>
          <label for="ricCategorySelect">Categoria per reset</label>
          <select id="ricCategorySelect"></select>
          <div class="error" id="ricModalError"></div>
          <table class="ric-table">
            <thead>
              <tr>
                <th>Categoria</th>
                <th>Listino</th>
                <th>RIC.BASE</th>
                <th>RIC</th>
                <th>Note</th>
                <th>Reset</th>
              </tr>
            </thead>
            <tbody id="ricTableBody"></tbody>
          </table>
          <div class="actions inline">
            <button id="saveRicOverrides">Salva override</button>
            <button id="resetRicCategory" class="secondary">Reset override categoria</button>
          </div>
          <div class="actions">
            <button id="resetRicAll" class="secondary">Reset tutto (torna a SCONTI 2026)</button>
          </div>
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
      const clampBanner = document.getElementById("clampBanner");
      const ricOverrideBanner = document.getElementById("ricOverrideBanner");
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
      const bufferRicOverrideToggle = document.getElementById("bufferRicOverrideToggle");
      const maxDiscount = document.getElementById("maxDiscount");
      const maxDiscountHint = document.getElementById("maxDiscountHint");
      const roundingMode = document.getElementById("roundingMode");
      const recalcBtn = document.getElementById("recalcBtn");
      const resetOverridesBtn = document.getElementById("resetOverridesBtn");
      const priceMode = document.getElementById("priceMode");
      const toggleTrace = document.getElementById("toggleTrace");
      const tracePanel = document.querySelector(".trace-panel");
      const traceSummary = document.getElementById("traceSummary");
      const traceRows = document.getElementById("traceRows");
      const ricParamsBtn = document.getElementById("ricParamsBtn");
      const ricModal = document.getElementById("ricModal");
      const closeRic = document.getElementById("closeRic");
      const ricOverrideToggle = document.getElementById("ricOverrideToggle");
      const ricTableBody = document.getElementById("ricTableBody");
      const ricExample = document.getElementById("ricExample");
      const ricModalError = document.getElementById("ricModalError");
      const saveRicOverrides = document.getElementById("saveRicOverrides");
      const resetRicCategory = document.getElementById("resetRicCategory");
      const resetRicAll = document.getElementById("resetRicAll");
      const ricCategorySelect = document.getElementById("ricCategorySelect");
      let copyBlock = "";
      let mappingData = {};
      let activeMappingTab = "ORDINI";
      let pricingLimits = {
        max_discount_real_min: null,
        max_discount_real_max: null,
        buffer_ric_example: null
      };
      let globalParams = {
        aggressivity: 0,
        aggressivity_mode: "discount_from_baseline",
        max_discount_percent: 10,
        buffer_ric: 2,
        rounding: 0.01
      };
      let currentPriceMode = "discount";
      let perRowOverrides = {};
      let lastValidation = { ok: true, errors: [] };
      let lastQuoteRows = [];
      let ricRows = [];
      let ricOverrideEnabled = false;

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

      function setClampBanner(message) {
        clampBanner.textContent = message || "";
        clampBanner.style.display = message ? "block" : "none";
      }

      function setRicOverrideBanner(message) {
        ricOverrideBanner.textContent = message || "";
        ricOverrideBanner.style.display = message ? "block" : "none";
      }

      function setRicModalError(message) {
        ricModalError.textContent = message || "";
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

      function openRicModal() {
        ricModal.classList.add("active");
        ricModal.setAttribute("aria-hidden", "false");
      }

      function closeRicModal() {
        ricModal.classList.remove("active");
        ricModal.setAttribute("aria-hidden", "true");
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

      function renderRicCategorySelect() {
        const categories = [...new Set(ricRows.map((row) => row.categoria))].sort();
        ricCategorySelect.innerHTML = "";
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Seleziona categoria";
        ricCategorySelect.appendChild(placeholder);
        categories.forEach((category) => {
          const opt = document.createElement("option");
          opt.value = category;
          opt.textContent = category;
          ricCategorySelect.appendChild(opt);
        });
      }

      function renderRicTable() {
        ricTableBody.innerHTML = "";
        ricRows.forEach((row, index) => {
          const tr = document.createElement("tr");
          const cells = [
            row.categoria,
            row.listino
          ];
          cells.forEach((value) => {
            const td = document.createElement("td");
            td.textContent = value ?? "";
            tr.appendChild(td);
          });

          const baseCell = document.createElement("td");
          const baseInput = document.createElement("input");
          baseInput.type = "number";
          baseInput.step = "0.1";
          baseInput.value = Number(row.ric_base).toFixed(2);
          baseInput.min = Number(row.ric_floor).toFixed(2);
          baseInput.disabled = !ricOverrideEnabled;
          baseInput.addEventListener("change", () => {
            ricRows[index].ric_base = Number(baseInput.value);
          });
          baseCell.appendChild(baseInput);
          tr.appendChild(baseCell);

          const floorCell = document.createElement("td");
          const floorInput = document.createElement("input");
          floorInput.type = "number";
          floorInput.step = "0.1";
          floorInput.value = Number(row.ric_floor).toFixed(2);
          floorInput.min = Number(row.ric_floor_min).toFixed(2);
          floorInput.disabled = !ricOverrideEnabled;
          floorInput.addEventListener("change", () => {
            ricRows[index].ric_floor = Number(floorInput.value);
          });
          floorCell.appendChild(floorInput);
          tr.appendChild(floorCell);

          const noteCell = document.createElement("td");
          const noteInput = document.createElement("input");
          noteInput.type = "text";
          noteInput.value = row.note || "";
          noteInput.disabled = !ricOverrideEnabled;
          noteInput.addEventListener("change", () => {
            ricRows[index].note = noteInput.value;
          });
          noteCell.appendChild(noteInput);
          const buffer = Number(row.ric_base) - Number(row.ric_floor);
          if (buffer < 0.5) {
            const warn = document.createElement("div");
            warn.className = "warning";
            warn.textContent = "Spazio sconto quasi nullo";
            noteCell.appendChild(warn);
          }
          tr.appendChild(noteCell);

          const resetCell = document.createElement("td");
          const resetBtn = document.createElement("button");
          resetBtn.type = "button";
          resetBtn.className = "secondary";
          resetBtn.textContent = "Reset";
          resetBtn.disabled = !ricOverrideEnabled || row.source !== "override";
          resetBtn.addEventListener("click", async () => {
            setRicModalError("");
            const res = await api("/api/ric/reset_overrides", {
              categoria: row.categoria,
              listino: row.listino
            });
            if (!res.ok) {
              setRicModalError(res.error || "Errore reset override");
              return;
            }
            await loadRicOverrides();
          });
          resetCell.appendChild(resetBtn);
          tr.appendChild(resetCell);

          ricTableBody.appendChild(tr);
        });
        saveRicOverrides.disabled = !ricOverrideEnabled;
        resetRicCategory.disabled = !ricOverrideEnabled;
        resetRicAll.disabled = !ricOverrideEnabled;
      }

      async function loadRicOverrides() {
        setRicModalError("");
        const res = await api("/api/ric/get_overrides");
        if (!res.ok) {
          setRicModalError(res.error || "Errore caricamento RIC");
          return;
        }
        ricRows = res.rows || [];
        ricExample.textContent = res.example || "";
        ricOverrideEnabled = ricOverrideToggle.checked;
        renderRicCategorySelect();
        renderRicTable();
      }

      function renderStatus(status) {
        statusList.innerHTML = "";
        const items = [
          ["Clienti caricati", status.clients_loaded],
          ["Stock caricato", status.stock_loaded],
          [`Storici selezionati (${status.histories_selected_count}/4)`, status.histories_ok],
          ["Ordine upsell caricato", status.order_loaded],
          ["Causale selezionata", status.causale_set],
          ["Cliente selezionato", status.client_selected],
          ["Override RIC validi", status.ric_overrides_ok]
        ];
        items.forEach(([label, ok]) => {
          const li = document.createElement("li");
          li.textContent = label + (ok ? " ✓" : " ✗");
          li.className = ok ? "status-ok" : "status-missing";
          statusList.appendChild(li);
        });
        computeBtn.disabled = !status.ready_to_compute;
        copyBtn.disabled = !status.has_results;
        exportBtn.disabled = !status.has_results || !lastValidation.ok || !status.ric_overrides_ok;
        recalcBtn.disabled = !status.has_results;
        resetOverridesBtn.disabled = !status.has_results;
        if (!status.ric_overrides_ok) {
          const details = (status.ric_override_errors || []).join(" | ");
          setRicOverrideBanner(
            details || "Override RIC non valide: correggi prima di esportare."
          );
        } else {
          setRicOverrideBanner("");
        }
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

      function updatePricingLimitsHint() {
        if (pricingLimits.max_discount_real_min !== null && pricingLimits.max_discount_real_min !== undefined) {
          const limit = Number(pricingLimits.max_discount_real_min);
          maxDiscount.max = limit;
          maxDiscountHint.textContent = `Max reale calcolato: ${limit.toFixed(2)}%`;
          if (globalParams.max_discount_percent > limit) {
            globalParams.max_discount_percent = limit;
            maxDiscount.value = limit.toFixed(2);
          }
        } else {
          maxDiscountHint.textContent = "";
          maxDiscount.removeAttribute("max");
        }
        if (!bufferRicOverrideToggle.checked && pricingLimits.buffer_ric_example !== null) {
          globalParams.buffer_ric = Number(pricingLimits.buffer_ric_example);
          bufferRic.value = Number(pricingLimits.buffer_ric_example).toFixed(2);
        }
      }

      function renderTable(rows, validation) {
        resultsBody.innerHTML = "";
        lastQuoteRows = rows || [];
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

          const lmCell = document.createElement("td");
          lmCell.textContent = Number(row.lm).toFixed(2);
          tr.appendChild(lmCell);

          const fixedDiscountCell = document.createElement("td");
          fixedDiscountCell.textContent = Number(row.fixed_discount_percent).toFixed(2);
          tr.appendChild(fixedDiscountCell);

          const basePriceCell = document.createElement("td");
          basePriceCell.textContent = Number(row.customer_base_price).toFixed(2);
          tr.appendChild(basePriceCell);

          const floorPriceCell = document.createElement("td");
          floorPriceCell.textContent = Number(row.min_unit_price).toFixed(2);
          tr.appendChild(floorPriceCell);

          const discountCell = document.createElement("td");
          const discountInput = document.createElement("input");
          discountInput.type = "number";
          discountInput.step = "0.1";
          discountInput.min = "0";
          discountInput.value = Number(row.desired_discount_percent).toFixed(2);
          discountInput.disabled = currentPriceMode !== "discount";
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
          priceInput.disabled = currentPriceMode !== "final_price";
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

          const noteCell = document.createElement("td");
          if (row.clamp_reason === "MIN_RIC_FLOOR") {
            noteCell.textContent = `Sconto bloccato: ric minimo ${Number(row.required_ric).toFixed(2)}% (floor=${Number(row.min_unit_price).toFixed(2)}; baseline=${Number(row.customer_base_price).toFixed(2)}; max_sconto_reale=${Number(row.max_discount_real).toFixed(2)}%)`;
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
          ["Max sconto (cap)", pricing.max_discount_percent ?? ""],
          ["Buffer ric (info)", pricing.buffer_ric ?? ""],
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
            ["LM", row.lm],
            ["Sconto fisso", row.fixed_discount_percent],
            ["RIC.BASE", row.ric_base],
            ["RIC minimo", row.ric_floor],
            ["RIC source", row.ric_source],
            ["Prezzo baseline", row.baseline_price],
            ["Prezzo minimo (RIC.)", row.floor_price],
            ["Max sconto reale", row.max_discount_real],
            ["Max sconto effettivo", row.max_discount_effective],
            ["Buffer ric", row.buffer_ric],
            ["Aggressività", row.aggressivity],
            ["Modalità", row.aggressivity_mode],
            ["Max sconto (cap)", row.max_discount_percent],
            ["Sconto override", row.discount_override],
            ["Prezzo override", row.unit_price_override],
            ["Sconto desiderato", row.desired_discount_percent],
            ["Sconto applicato", row.applied_discount_percent],
            ["Prezzo candidato", row.candidate_price],
            ["Clamp reason", row.clamp_reason],
            ["Prezzo finale", row.final_price],
            ["Ric finale", row.final_ric_percent],
            ["Qty", row.qty],
            ["Formula", row.formula],
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
          bufferRic.readOnly = !bufferRicOverrideToggle.checked;
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
        pricingLimits = res.pricing_limits || pricingLimits;
        const validationErrors = (lastValidation.errors || [])
          .map((err) => `${err.sku}: minimo ${Number(err.min_unit_price).toFixed(2)}`)
          .join(" | ");
        setValidation(lastValidation.ok ? "" : `Errore ric minimo: ${validationErrors}`);
        const warnings = (res.warnings || []).join(" | ");
        setWarning(warnings);
        const hasClamp = (res.quote || []).some((row) => row.clamp_reason === "MIN_RIC_FLOOR");
        if (hasClamp) {
          const maxDiscountReal = pricingLimits.max_discount_real_min;
          setClampBanner(
            `Alcune righe sono al pavimento ric minimo (max sconto reale ${maxDiscountReal?.toFixed?.(2) ?? "-" }%).`
          );
        } else {
          setClampBanner("");
        }
        renderTable(res.quote, lastValidation);
        renderTrace(res.trace || {});
        if (res.ric_override_errors && res.ric_override_errors.length) {
          setRicOverrideBanner(res.ric_override_errors.join(" | "));
        }
        const overrideInvalid = res.ric_override_errors && res.ric_override_errors.length;
        exportBtn.disabled = !lastValidation.ok || overrideInvalid;
        updatePricingLimitsHint();
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
        if (!bufferRicOverrideToggle.checked) {
          return;
        }
        globalParams.buffer_ric = Number(bufferRic.value);
        scheduleRecalc();
      });

      maxDiscount.addEventListener("change", () => {
        let value = Number(maxDiscount.value);
        if (maxDiscount.max) {
          const maxAllowed = Number(maxDiscount.max);
          if (value > maxAllowed) {
            value = maxAllowed;
            maxDiscount.value = maxAllowed.toFixed(2);
          }
        }
        globalParams.max_discount_percent = value;
        scheduleRecalc();
      });

      priceMode.addEventListener("change", () => {
        currentPriceMode = priceMode.value;
        renderTable(lastQuoteRows, lastValidation);
      });

      toggleTrace.addEventListener("change", () => {
        tracePanel.style.display = toggleTrace.checked ? "" : "none";
      });

      roundingMode.addEventListener("change", () => {
        const value = roundingMode.value;
        globalParams.rounding = value === "NONE" ? null : Number(value);
        scheduleRecalc();
      });

      bufferRicOverrideToggle.addEventListener("change", () => {
        bufferRic.readOnly = !bufferRicOverrideToggle.checked;
        if (!bufferRicOverrideToggle.checked) {
          updatePricingLimitsHint();
        }
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

      ricParamsBtn.addEventListener("click", async () => {
        ricOverrideToggle.checked = false;
        ricOverrideEnabled = false;
        await loadRicOverrides();
        renderRicTable();
        openRicModal();
      });

      closeRic.addEventListener("click", () => {
        closeRicModal();
      });

      ricOverrideToggle.addEventListener("change", () => {
        ricOverrideEnabled = ricOverrideToggle.checked;
        renderRicTable();
      });

      saveRicOverrides.addEventListener("click", async () => {
        if (!ricOverrideEnabled) {
          setRicModalError("Attiva l'override manuale per modificare i valori.");
          return;
        }
        const overridesToSave = ricRows
          .filter((row) => {
            const baseChanged = Number(row.ric_base) !== Number(row.ric_base_default);
            const floorChanged = Number(row.ric_floor) !== Number(row.ric_floor_default);
            const noteChanged = (row.note || "") !== (row.note_default || "");
            return baseChanged || floorChanged || noteChanged;
          })
          .map((row) => ({
            categoria: row.categoria,
            listino: row.listino,
            ric_base: row.ric_base,
            ric_floor: row.ric_floor,
            note: row.note || ""
          }));
        const res = await api("/api/ric/save_overrides", { overrides: overridesToSave });
        if (!res.ok) {
          setRicModalError((res.details || []).join(" | ") || res.error || "Errore salvataggio override");
          return;
        }
        await loadRicOverrides();
        setRicModalError("");
      });

      resetRicCategory.addEventListener("click", async () => {
        const category = ricCategorySelect.value;
        if (!category) {
          setRicModalError("Seleziona una categoria da resettare.");
          return;
        }
        const res = await api("/api/ric/reset_overrides", { categoria: category });
        if (!res.ok) {
          setRicModalError(res.error || "Errore reset categoria");
          return;
        }
        await loadRicOverrides();
      });

      resetRicAll.addEventListener("click", async () => {
        const res = await api("/api/ric/reset_overrides", {});
        if (!res.ok) {
          setRicModalError(res.error || "Errore reset totale");
          return;
        }
        await loadRicOverrides();
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
      tracePanel.style.display = toggleTrace.checked ? "" : "none";
    </script>
  </body>
</html>
"""
