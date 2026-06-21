"""Patch templates/index.html with extended desk tools (Phases 1-4 parity)."""
from pathlib import Path

INDEX = Path(__file__).parent / "templates" / "index.html"
text = INDEX.read_text(encoding="utf-8")

# Scrollable tab bar
text = text.replace(
    """    .tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }""",
    """    .tabs {
      display: flex;
      gap: 8px;
      flex-wrap: nowrap;
      overflow-x: auto;
      margin-bottom: 18px;
      padding-bottom: 4px;
      scrollbar-width: thin;
    }

    .tabs::-webkit-scrollbar { height: 6px; }
    .tabs::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 999px;
    }""",
)

text = text.replace(
    """        <p class="subtitle">
          Currency conversion, GCC fuel prices, truck sizing, and warehouse planning in one desktop app.
          FX rates refresh every 5 minutes; fuel prices refresh hourly from official sources.
        </p>""",
    """        <p class="subtitle">
          Freight quoting, chargeable weight, fuel surcharge, dispatch and warehouse desk tools in one desktop app.
          FX rates refresh every 5 minutes; fuel prices refresh hourly from official sources.
        </p>""",
)

OLD_TABS = """    <nav class="tabs">
      <button class="tab-btn active" data-tab="currency" type="button">Currency</button>
      <button class="tab-btn" data-tab="fuel" type="button">Fuel Prices</button>
      <button class="tab-btn" data-tab="truck" type="button">Truck Requirement</button>
      <button class="tab-btn" data-tab="warehouse" type="button">Warehouse Space</button>
    </nav>"""

NEW_TABS = """    <nav class="tabs">
      <button class="tab-btn active" data-tab="currency" type="button">Currency</button>
      <button class="tab-btn" data-tab="fuel" type="button">Fuel Prices</button>
      <button class="tab-btn" data-tab="quote" type="button">Freight Quote</button>
      <button class="tab-btn" data-tab="chargeable" type="button">Chargeable Weight</button>
      <button class="tab-btn" data-tab="fsc" type="button">Fuel Surcharge</button>
      <button class="tab-btn" data-tab="trip" type="button">Trip Cost</button>
      <button class="tab-btn" data-tab="transit" type="button">Transit ETA</button>
      <button class="tab-btn" data-tab="freetime" type="button">Free Time</button>
      <button class="tab-btn" data-tab="multistop" type="button">Multi-stop</button>
      <button class="tab-btn" data-tab="truck" type="button">Truck Requirement</button>
      <button class="tab-btn" data-tab="warehouse" type="button">Warehouse Space</button>
      <button class="tab-btn" data-tab="receiving" type="button">Receiving</button>
      <button class="tab-btn" data-tab="doh" type="button">Days on Hand</button>
      <button class="tab-btn" data-tab="pallet" type="button">Pallet Build</button>
      <button class="tab-btn" data-tab="fifo" type="button">FIFO / FEFO</button>
      <button class="tab-btn" data-tab="landed" type="button">Landed Cost</button>
      <button class="tab-btn" data-tab="docs" type="button">Doc Checklist</button>
      <button class="tab-btn" data-tab="dgseg" type="button">DG Segregation</button>
      <button class="tab-btn" data-tab="units" type="button">Unit Converter</button>
      <button class="tab-btn" data-tab="shpref" type="button">Shipment Ref</button>
    </nav>"""

if OLD_TABS not in text:
    raise SystemExit("Tab nav block not found — index.html may already be patched")
text = text.replace(OLD_TABS, NEW_TABS)

PANELS = r"""
    <!-- FREIGHT QUOTE -->
    <section class="panel" id="panel-quote">
      <main class="grid-2">
        <section class="card">
          <h2>Freight Quote</h2>
          <div class="grid-2eq">
            <div style="grid-column:1/-1">
              <label for="qtBasis">Rate basis</label>
              <select id="qtBasis">
                <option value="per_kg">Per kg (chargeable)</option>
                <option value="per_cbm">Per CBM</option>
                <option value="per_km">Per km</option>
                <option value="per_trip">Per trip (flat)</option>
              </select>
            </div>
            <div><label for="qtRate">Base rate</label><input id="qtRate" type="number" step="any" value="0.45"></div>
            <div><label for="qtCurrency">Currency</label><input id="qtCurrency" type="text" value="AED" maxlength="6"></div>
            <div><label for="qtWeight">Weight (kg)</label><input id="qtWeight" type="number" step="any" value="5000"></div>
            <div><label for="qtVolume">Volume (CBM)</label><input id="qtVolume" type="number" step="any" value="12"></div>
            <div style="grid-column:1/-1"><label for="qtVolFactor">Volumetric factor (kg/CBM)</label><input id="qtVolFactor" type="number" step="any" value="167"></div>
            <div><label for="qtDistance">Distance (km)</label><input id="qtDistance" type="number" step="any" value="250"></div>
            <div><label for="qtFsc">Fuel surcharge %</label><input id="qtFsc" type="number" step="any" value="8"></div>
            <div><label for="qtMargin">Margin %</label><input id="qtMargin" type="number" step="any" value="15"></div>
            <div><label for="qtTolls">Tolls / road fees</label><input id="qtTolls" type="number" step="any" value="0"></div>
            <div><label for="qtAcc1Label">Accessorial 1</label><input id="qtAcc1Label" type="text" value="Documentation fee"></div>
            <div><label for="qtAcc1Amt">Amount</label><input id="qtAcc1Amt" type="number" step="any" value="75"></div>
          </div>
          <button class="calc-btn" id="qtCalcBtn" type="button">Build quote</button>
          <div class="error" id="qtError"></div>
        </section>
        <aside class="card">
          <h2>Quote Result</h2>
          <div class="result-panel">
            <p class="result-amount" id="qtSummary">Enter rates and calculate</p>
            <p class="result-meta" id="qtDetail"></p>
          </div>
          <div id="qtLines"></div>
        </aside>
      </main>
    </section>

    <!-- CHARGEABLE WEIGHT -->
    <section class="panel" id="panel-chargeable">
      <main class="grid-2">
        <section class="card">
          <h2>Chargeable Weight</h2>
          <div class="grid-2eq">
            <div><label for="cwWeight">Actual weight (kg)</label><input id="cwWeight" type="number" step="any" placeholder="e.g. 500"></div>
            <div><label for="cwVolume">Volume (CBM)</label><input id="cwVolume" type="number" step="any" placeholder="e.g. 2.5"></div>
            <div style="grid-column:1/-1">
              <label for="cwPreset">Volumetric preset</label>
              <select id="cwPreset">
                <option value="road_167">Road LTL (167 kg/CBM)</option>
                <option value="road_333">Road dense (333 kg/CBM)</option>
                <option value="air_167">Air style (167 kg/CBM)</option>
                <option value="custom">Custom factor</option>
              </select>
            </div>
            <div style="grid-column:1/-1"><label for="cwFactor">Custom factor</label><input id="cwFactor" type="number" step="any" value="167"></div>
          </div>
          <button class="calc-btn" id="cwCalcBtn" type="button">Calculate chargeable weight</button>
          <div class="error" id="cwError"></div>
        </section>
        <aside class="card">
          <h2>Result</h2>
          <div class="result-panel">
            <p class="result-amount" id="cwSummary">—</p>
            <p class="result-meta" id="cwDetail"></p>
          </div>
          <div class="metric-grid" id="cwMetrics"></div>
        </aside>
      </main>
    </section>

    <!-- FUEL SURCHARGE -->
    <section class="panel" id="panel-fsc">
      <main class="grid-2">
        <section class="card">
          <h2>Fuel Surcharge</h2>
          <div class="grid-2eq">
            <div><label for="fscBaseline">Baseline diesel price</label><input id="fscBaseline" type="number" step="any" value="3.5"></div>
            <div><label for="fscCurrent">Current diesel (manual)</label><input id="fscCurrent" type="number" step="any" placeholder="Leave blank for live"></div>
          </div>
          <label class="check-row"><input id="fscLive" type="checkbox" checked> Use live diesel from Fuel tab</label>
          <button class="calc-btn" id="fscCalcBtn" type="button">Calculate FSC %</button>
          <div class="error" id="fscError"></div>
        </section>
        <aside class="card">
          <h2>FSC Result</h2>
          <div class="result-panel">
            <p class="result-amount" id="fscSummary">—</p>
            <p class="result-meta" id="fscDetail"></p>
          </div>
          <div class="metric-grid" id="fscMetrics"></div>
        </aside>
      </main>
    </section>

    <!-- TRIP COST -->
    <section class="panel" id="panel-trip">
      <main class="grid-2 desk-tool" data-endpoint="/api/trip-cost" data-btn="tripCalcBtn" data-error="tripError" data-summary="tripSummary" data-metrics="tripMetrics">
        <section class="card">
          <h2>Trip Cost</h2>
          <div class="grid-2eq">
            <div><label>Distance (km)</label><input data-field="distance_km" type="number" step="any" value="250"></div>
            <div><label>Fuel L/100km</label><input data-field="fuel_l_per_100km" type="number" step="any" value="28"></div>
            <div><label>Fuel price</label><input data-field="fuel_price" type="number" step="any" value="4.33"></div>
            <div><label>Driver cost</label><input data-field="driver_cost" type="number" step="any" value="350"></div>
            <div><label>Tolls / fees</label><input data-field="tolls_fees" type="number" step="any" value="25"></div>
            <div><label>Weight (kg)</label><input data-field="weight_kg" type="number" step="any" value="5000"></div>
          </div>
          <button class="calc-btn" id="tripCalcBtn" type="button">Estimate trip cost</button>
          <div class="error" id="tripError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="tripSummary">—</p></div><div class="metric-grid" id="tripMetrics"></div></aside>
      </main>
    </section>

    <!-- TRANSIT ETA -->
    <section class="panel" id="panel-transit">
      <main class="grid-2">
        <section class="card">
          <h2>Transit ETA</h2>
          <div class="grid-2eq">
            <div style="grid-column:1/-1"><label for="tePickup">Pickup date</label><input id="tePickup" type="date"></div>
            <div><label for="teDays">Transit days</label><input id="teDays" type="number" step="1" value="3"></div>
            <div><label for="teBuffer">Buffer days</label><input id="teBuffer" type="number" step="1" value="1"></div>
          </div>
          <label class="check-row"><input id="teSkipWE" type="checkbox" checked> Skip weekends</label>
          <button class="calc-btn" id="teCalcBtn" type="button">Estimate delivery</button>
          <div class="error" id="teError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="teSummary">—</p><p class="result-meta" id="teDetail"></p></div></aside>
      </main>
    </section>

    <!-- FREE TIME -->
    <section class="panel" id="panel-freetime">
      <main class="grid-2 desk-tool" data-endpoint="/api/free-time" data-btn="ftCalcBtn" data-error="ftError" data-summary="ftSummary" data-metrics="ftMetrics">
        <section class="card">
          <h2>Free Time</h2>
          <div class="grid-2eq">
            <div><label>Arrival date</label><input data-field="arrival_date" type="date"></div>
            <div><label>Free days</label><input data-field="free_days" type="number" step="1" value="7"></div>
          </div>
          <button class="calc-btn" id="ftCalcBtn" type="button">Calculate free time</button>
          <div class="error" id="ftError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="ftSummary">—</p></div><div class="metric-grid" id="ftMetrics"></div></aside>
      </main>
    </section>

    <!-- MULTI-STOP -->
    <section class="panel" id="panel-multistop">
      <main class="grid-2">
        <section class="card">
          <h2>Multi-stop Load</h2>
          <div class="grid-2eq">
            <div><label for="msW1">Stop 1 weight (kg)</label><input id="msW1" type="number" step="any" value="2000"></div>
            <div><label for="msV1">Stop 1 volume (CBM)</label><input id="msV1" type="number" step="any" value="5"></div>
            <div><label for="msW2">Stop 2 weight (kg)</label><input id="msW2" type="number" step="any" value="3000"></div>
            <div><label for="msV2">Stop 2 volume (CBM)</label><input id="msV2" type="number" step="any" value="7"></div>
          </div>
          <button class="calc-btn" id="msCalcBtn" type="button">Summarize load</button>
          <div class="error" id="msError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="msSummary">—</p><p class="result-meta" id="msDetail"></p></div></aside>
      </main>
    </section>

    <!-- RECEIVING -->
    <section class="panel" id="panel-receiving">
      <main class="grid-2 desk-tool" data-endpoint="/api/receiving" data-btn="rcvCalcBtn" data-error="rcvError" data-summary="rcvSummary" data-metrics="rcvMetrics">
        <section class="card">
          <h2>Receiving Capacity</h2>
          <div class="grid-2eq">
            <div><label>Dock doors</label><input data-field="dock_count" type="number" step="1" value="2"></div>
            <div><label>Hours per day</label><input data-field="hours_per_day" type="number" step="any" value="8"></div>
            <div><label>Avg unload (min)</label><input data-field="avg_unload_minutes" type="number" step="any" value="45"></div>
            <div><label>Trucks scheduled</label><input data-field="trucks_scheduled" type="number" step="1" value="6"></div>
          </div>
          <button class="calc-btn" id="rcvCalcBtn" type="button">Calculate dock capacity</button>
          <div class="error" id="rcvError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="rcvSummary">—</p></div><div class="metric-grid" id="rcvMetrics"></div></aside>
      </main>
    </section>

    <!-- DAYS ON HAND -->
    <section class="panel" id="panel-doh">
      <main class="grid-2 desk-tool" data-endpoint="/api/inventory-doh" data-btn="dohCalcBtn" data-error="dohError" data-summary="dohSummary" data-metrics="dohMetrics">
        <section class="card">
          <h2>Days on Hand</h2>
          <div class="grid-2eq">
            <div><label>On-hand qty</label><input data-field="on_hand_qty" type="number" step="any" value="1200"></div>
            <div><label>Daily outbound</label><input data-field="daily_outbound" type="number" step="any" value="80"></div>
            <div><label>Lead time (days)</label><input data-field="lead_time_days" type="number" step="any" value="14"></div>
            <div><label>Safety stock (days)</label><input data-field="safety_stock_days" type="number" step="any" value="7"></div>
          </div>
          <button class="calc-btn" id="dohCalcBtn" type="button">Calculate DOH</button>
          <div class="error" id="dohError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="dohSummary">—</p></div><div class="metric-grid" id="dohMetrics"></div></aside>
      </main>
    </section>

    <!-- PALLET BUILD -->
    <section class="panel" id="panel-pallet">
      <main class="grid-2 desk-tool" data-endpoint="/api/pallet-build" data-btn="palCalcBtn" data-error="palError" data-summary="palSummary" data-metrics="palMetrics">
        <section class="card">
          <h2>Pallet Build</h2>
          <div class="grid-2eq">
            <div><label>Carton L (cm)</label><input data-field="carton_length_cm" type="number" step="any" value="40"></div>
            <div><label>Carton W (cm)</label><input data-field="carton_width_cm" type="number" step="any" value="30"></div>
            <div><label>Carton H (cm)</label><input data-field="carton_height_cm" type="number" step="any" value="25"></div>
            <div><label>Cartons per layer</label><input data-field="cartons_per_layer" type="number" step="1" value="8"></div>
            <div><label>Layers</label><input data-field="layers" type="number" step="1" value="3"></div>
            <div><label>Pallet L (cm)</label><input data-field="pallet_length_cm" type="number" step="any" value="120"></div>
            <div><label>Pallet W (cm)</label><input data-field="pallet_width_cm" type="number" step="any" value="100"></div>
            <div><label>Carton weight (kg)</label><input data-field="carton_weight_kg" type="number" step="any" value="12"></div>
            <div><label>Max stack weight (kg)</label><input data-field="max_stack_weight_kg" type="number" step="any" value="1000"></div>
          </div>
          <button class="calc-btn" id="palCalcBtn" type="button">Calculate pallet build</button>
          <div class="error" id="palError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="palSummary">—</p></div><div class="metric-grid" id="palMetrics"></div></aside>
      </main>
    </section>

    <!-- FIFO / FEFO -->
    <section class="panel" id="panel-fifo">
      <main class="grid-2">
        <section class="card">
          <h2>FIFO / FEFO</h2>
          <div class="grid-2eq">
            <div style="grid-column:1/-1"><label for="ffDelivery">Delivery date</label><input id="ffDelivery" type="date"></div>
            <div><label for="ffB1">Lot A expiry</label><input id="ffB1" type="date" value="2026-08-01"></div>
            <div><label for="ffQ1">Lot A qty</label><input id="ffQ1" type="number" step="any" value="100"></div>
            <div><label for="ffB2">Lot B expiry</label><input id="ffB2" type="date" value="2026-09-15"></div>
            <div><label for="ffQ2">Lot B qty</label><input id="ffQ2" type="number" step="any" value="150"></div>
          </div>
          <button class="calc-btn" id="ffCalcBtn" type="button">Sort ship order</button>
          <div class="error" id="ffError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="ffSummary">—</p><p class="result-meta" id="ffDetail"></p></div></aside>
      </main>
    </section>

    <!-- LANDED COST -->
    <section class="panel" id="panel-landed">
      <main class="grid-2 desk-tool" data-endpoint="/api/landed-cost" data-btn="lcCalcBtn" data-error="lcError" data-summary="lcSummary" data-metrics="lcMetrics">
        <section class="card">
          <h2>Landed Cost</h2>
          <div class="grid-2eq">
            <div><label>Goods value</label><input data-field="goods_value" type="number" step="any" value="10000"></div>
            <div><label>Quantity</label><input data-field="quantity" type="number" step="1" value="100"></div>
            <div><label>Duty %</label><input data-field="duty_percent" type="number" step="any" value="5"></div>
            <div><label>VAT %</label><input data-field="vat_percent" type="number" step="any" value="5"></div>
            <div><label>Clearance fees</label><input data-field="clearance_fees" type="number" step="any" value="500"></div>
            <div><label>From currency</label><input data-field="from_currency" type="text" value="USD" maxlength="3"></div>
            <div><label>To currency</label><input data-field="to_currency" type="text" value="AED" maxlength="3"></div>
          </div>
          <button class="calc-btn" id="lcCalcBtn" type="button">Estimate landed cost</button>
          <div class="error" id="lcError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="lcSummary">—</p></div><div class="metric-grid" id="lcMetrics"></div></aside>
      </main>
    </section>

    <!-- DOC CHECKLIST -->
    <section class="panel" id="panel-docs">
      <main class="grid-2">
        <section class="card">
          <h2>Document Checklist</h2>
          <label class="check-row"><input id="dcDG" type="checkbox"> Dangerous goods</label>
          <label class="check-row"><input id="dcReefer" type="checkbox"> Temperature controlled</label>
          <label class="check-row"><input id="dcCross" type="checkbox" checked> Cross-border</label>
          <label class="check-row"><input id="dcFragile" type="checkbox"> Fragile cargo</label>
          <label class="check-row"><input id="dcHigh" type="checkbox"> High value</label>
          <button class="calc-btn" id="dcCalcBtn" type="button">Generate checklist</button>
          <div class="error" id="dcError"></div>
          <ul class="alt-list" id="dcList"></ul>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="dcSummary">—</p></div></aside>
      </main>
    </section>

    <!-- DG SEGREGATION -->
    <section class="panel" id="panel-dgseg">
      <main class="grid-2 desk-tool" data-endpoint="/api/dg-segregation" data-btn="dgsCalcBtn" data-error="dgsError" data-summary="dgsSummary">
        <section class="card">
          <h2>DG Segregation</h2>
          <div class="grid-2eq">
            <div><label>Class A</label><select data-field="class_a"><option>1</option><option>2</option><option selected>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option></select></div>
            <div><label>Class B</label><select data-field="class_b"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option selected>8</option><option>9</option></select></div>
          </div>
          <button class="calc-btn" id="dgsCalcBtn" type="button">Check segregation</button>
          <div class="error" id="dgsError"></div>
        </section>
        <aside class="card"><h2>Result</h2><div class="result-panel"><p class="result-amount" id="dgsSummary">—</p><p class="result-meta" id="dgsDetail"></p></div></aside>
      </main>
    </section>

    <!-- UNIT CONVERTER -->
    <section class="panel" id="panel-units">
      <main class="grid-2">
        <section class="card">
          <h2>Unit Converter</h2>
          <div class="grid-2eq">
            <div style="grid-column:1/-1">
              <label for="ucCategory">Category</label>
              <select id="ucCategory">
                <option value="mass">Mass</option>
                <option value="length">Length</option>
                <option value="volume">Volume</option>
                <option value="temperature">Temperature</option>
              </select>
            </div>
            <div><label for="ucAmount">Amount</label><input id="ucAmount" type="number" step="any" value="1"></div>
            <div></div>
            <div><label for="ucFrom">From</label><select id="ucFrom"></select></div>
            <div><label for="ucTo">To</label><select id="ucTo"></select></div>
          </div>
        </section>
        <aside class="card">
          <h2>Result</h2>
          <div class="result-panel"><p class="result-amount" id="ucSummary">—</p></div>
        </aside>
      </main>
    </section>

    <!-- SHIPMENT REF -->
    <section class="panel" id="panel-shpref">
      <main class="card" style="max-width:520px">
        <h2>Shipment Reference</h2>
        <div class="grid-2eq">
          <div><label for="srPrefix">Prefix</label><input id="srPrefix" type="text" value="SHP"></div>
          <div><label for="srSeq">Sequence</label><input id="srSeq" type="number" step="1" value="1001"></div>
        </div>
        <div class="result-panel" style="margin-top:16px">
          <p class="result-amount" id="srRef">—</p>
          <p class="result-meta">Internal shipment reference for tracking and filing.</p>
        </div>
        <button class="calc-btn" id="srCopyBtn" type="button" style="margin-top:12px">Copy reference</button>
      </main>
    </section>
"""

MARKER = "  </div>\n\n  <script>"
if MARKER not in text:
    raise SystemExit("Panel insert marker not found")
text = text.replace(MARKER, PANELS + MARKER, 1)

JS = r"""
    // --- Extended desk tools ---
    function todayISO() {
      return new Date().toISOString().slice(0, 10);
    }

    document.getElementById("tePickup").value = todayISO();
    document.querySelector('#panel-freetime input[data-field="arrival_date"]').value = todayISO();
    document.getElementById("ffDelivery").value = todayISO();

    async function postDesk(endpoint, payload) {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Calculation failed");
      return data;
    }

    function bindDeskTool(mainEl, metricMap) {
      const endpoint = mainEl.dataset.endpoint;
      const btn = document.getElementById(mainEl.dataset.btn);
      const errorEl = document.getElementById(mainEl.dataset.error);
      const summaryEl = document.getElementById(mainEl.dataset.summary);
      const metricsEl = mainEl.dataset.metrics ? document.getElementById(mainEl.dataset.metrics) : null;
      const detailEl = mainEl.dataset.detail ? document.getElementById(mainEl.dataset.detail) : null;

      btn.addEventListener("click", async () => {
        errorEl.textContent = "";
        const payload = {};
        mainEl.querySelectorAll("[data-field]").forEach((el) => {
          const key = el.dataset.field;
          if (el.type === "checkbox") payload[key] = el.checked;
          else if (el.type === "number") payload[key] = parseFloat(el.value) || 0;
          else payload[key] = el.value;
        });
        try {
          const data = await postDesk(endpoint, payload);
          summaryEl.textContent = data.summary || data.sell_total ? `${data.currency || ""} ${formatNumber(data.sell_total || 0)}` : "Done";
          if (detailEl) detailEl.textContent = data.disclaimer || data.delivery_date || "";
          if (metricsEl && metricMap) {
            renderMetrics(mainEl.dataset.metrics, metricMap(data));
          }
        } catch (err) {
          errorEl.textContent = err.message;
        }
      });
    }

    document.querySelectorAll(".desk-tool").forEach((el) => {
      const ep = el.dataset.endpoint;
      if (ep === "/api/trip-cost") {
        bindDeskTool(el, (d) => [
          ["Fuel cost", formatNumber(d.fuel_cost)],
          ["Total cost", formatNumber(d.total_cost)],
          ["Cost / kg", d.cost_per_kg != null ? formatNumber(d.cost_per_kg) : "—"],
        ]);
      } else if (ep === "/api/free-time") {
        bindDeskTool(el, (d) => [
          ["Last free day", d.last_free_day],
          ["Days remaining", String(d.days_remaining)],
        ]);
      } else if (ep === "/api/receiving") {
        bindDeskTool(el, (d) => [
          ["Total slots", String(d.total_slots)],
          ["Utilization", `${d.utilization_pct}%`],
          ["Spare slots", String(d.spare_slots)],
        ]);
      } else if (ep === "/api/inventory-doh") {
        bindDeskTool(el, (d) => [
          ["Days on hand", String(d.days_on_hand)],
          ["Reorder point", String(d.reorder_point)],
          ["Below reorder", d.below_reorder ? "Yes" : "No"],
        ]);
      } else if (ep === "/api/pallet-build") {
        bindDeskTool(el, (d) => [
          ["Cartons", String(d.total_cartons)],
          ["Pallet weight", `${formatNumber(d.pallet_weight_kg)} kg`],
          ["Height", `${formatNumber(d.stack_height_cm)} cm`],
        ]);
      } else if (ep === "/api/landed-cost") {
        bindDeskTool(el, (d) => [
          ["Landed / unit", `${d.to_currency} ${formatNumber(d.landed_per_unit)}`],
          ["Landed total", `${d.to_currency} ${formatNumber(d.landed_total)}`],
          ["FX rate", String(d.fx_rate)],
        ]);
      } else if (ep === "/api/dg-segregation") {
        document.getElementById("dgsCalcBtn").addEventListener("click", async () => {
          const errorEl = document.getElementById("dgsError");
          errorEl.textContent = "";
          try {
            const data = await postDesk("/api/dg-segregation", {
              class_a: document.querySelector('#panel-dgseg [data-field="class_a"]').value,
              class_b: document.querySelector('#panel-dgseg [data-field="class_b"]').value,
            });
            document.getElementById("dgsSummary").textContent = data.summary;
            document.getElementById("dgsDetail").textContent = data.guidance || "";
          } catch (err) {
            errorEl.textContent = err.message;
          }
        });
      }
    });

    // Freight quote
    document.getElementById("qtCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("qtError");
      errorEl.textContent = "";
      const accessorials = [];
      const a1 = parseFloat(document.getElementById("qtAcc1Amt").value) || 0;
      if (a1 > 0) accessorials.push({ label: document.getElementById("qtAcc1Label").value, amount: a1 });
      try {
        const data = await postDesk("/api/quote", {
          rate_basis: document.getElementById("qtBasis").value,
          base_rate: parseFloat(document.getElementById("qtRate").value) || 0,
          weight_kg: parseFloat(document.getElementById("qtWeight").value) || 0,
          volume_cbm: parseFloat(document.getElementById("qtVolume").value) || 0,
          distance_km: parseFloat(document.getElementById("qtDistance").value) || 0,
          volumetric_factor: parseFloat(document.getElementById("qtVolFactor").value) || 167,
          fsc_percent: parseFloat(document.getElementById("qtFsc").value) || 0,
          margin_percent: parseFloat(document.getElementById("qtMargin").value) || 0,
          tolls_fees: parseFloat(document.getElementById("qtTolls").value) || 0,
          accessorials,
          currency: document.getElementById("qtCurrency").value.toUpperCase(),
        });
        document.getElementById("qtSummary").textContent = `${data.currency} ${formatNumber(data.sell_total)}`;
        document.getElementById("qtDetail").textContent = data.summary || "";
        document.getElementById("qtLines").innerHTML = (data.line_items || []).map((line) =>
          `<p class="footer-note">${line.label}: ${data.currency} ${formatNumber(line.amount)}</p>`
        ).join("");
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Chargeable weight
    document.getElementById("cwCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("cwError");
      errorEl.textContent = "";
      const preset = document.getElementById("cwPreset").value;
      try {
        const data = await postDesk("/api/chargeable-weight", {
          actual_weight_kg: parseFloat(document.getElementById("cwWeight").value) || 0,
          volume_cbm: parseFloat(document.getElementById("cwVolume").value) || 0,
          volumetric_preset: preset,
          volumetric_factor: preset === "custom" ? parseFloat(document.getElementById("cwFactor").value) || 167 : undefined,
        });
        document.getElementById("cwSummary").textContent = `${formatNumber(data.chargeable_weight_kg)} kg chargeable`;
        document.getElementById("cwDetail").textContent = data.summary || "";
        renderMetrics("cwMetrics", [
          ["Actual", `${formatNumber(data.actual_weight_kg)} kg`],
          ["Volumetric", `${formatNumber(data.volumetric_weight_kg)} kg`],
          ["Binding", data.binding_constraint],
        ]);
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Fuel surcharge
    document.getElementById("fscCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("fscError");
      errorEl.textContent = "";
      const baseline = parseFloat(document.getElementById("fscBaseline").value) || 3.5;
      const useLive = document.getElementById("fscLive").checked;
      let url = `/api/fuel-surcharge?baseline=${baseline}`;
      if (!useLive) {
        const current = parseFloat(document.getElementById("fscCurrent").value);
        if (!Number.isFinite(current)) {
          errorEl.textContent = "Enter current diesel price or use live fuel.";
          return;
        }
        url += `&current=${current}`;
      }
      try {
        const response = await fetch(url);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Failed");
        document.getElementById("fscSummary").textContent = `${formatNumber(data.fsc_percent, 2)}% fuel surcharge`;
        document.getElementById("fscDetail").textContent = data.summary || "";
        renderMetrics("fscMetrics", [
          ["Baseline", `${data.currency} ${formatNumber(data.baseline_price)}`],
          ["Current", `${data.currency} ${formatNumber(data.current_price)}`],
          ["FSC %", `${formatNumber(data.fsc_percent, 2)}%`],
        ]);
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Transit ETA
    document.getElementById("teCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("teError");
      errorEl.textContent = "";
      try {
        const data = await postDesk("/api/transit-eta", {
          pickup_date: document.getElementById("tePickup").value,
          transit_days: parseInt(document.getElementById("teDays").value, 10) || 0,
          buffer_days: parseInt(document.getElementById("teBuffer").value, 10) || 0,
          skip_weekends: document.getElementById("teSkipWE").checked,
        });
        document.getElementById("teSummary").textContent = data.summary;
        document.getElementById("teDetail").textContent = `Delivery: ${data.delivery_date}`;
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Multi-stop
    document.getElementById("msCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("msError");
      errorEl.textContent = "";
      try {
        const data = await postDesk("/api/multi-stop", {
          stops: [
            { weight_kg: parseFloat(document.getElementById("msW1").value) || 0, volume_cbm: parseFloat(document.getElementById("msV1").value) || 0, pallets: 4 },
            { weight_kg: parseFloat(document.getElementById("msW2").value) || 0, volume_cbm: parseFloat(document.getElementById("msV2").value) || 0, pallets: 6 },
          ],
          transport_region: "uae",
          safety_margin_pct: 10,
        });
        document.getElementById("msSummary").textContent = data.summary;
        document.getElementById("msDetail").textContent = data.truck?.summary || "";
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // FIFO / FEFO
    document.getElementById("ffCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("ffError");
      errorEl.textContent = "";
      try {
        const data = await postDesk("/api/fifo-fefo", {
          delivery_date: document.getElementById("ffDelivery").value,
          batches: [
            { batch_id: "Lot A", expiry_date: document.getElementById("ffB1").value, quantity: parseFloat(document.getElementById("ffQ1").value) || 0 },
            { batch_id: "Lot B", expiry_date: document.getElementById("ffB2").value, quantity: parseFloat(document.getElementById("ffQ2").value) || 0 },
          ],
        });
        document.getElementById("ffSummary").textContent = data.summary;
        document.getElementById("ffDetail").textContent = (data.ship_order || []).map((b) => `${b.batch_id}: ${b.quantity}`).join(" → ");
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Doc checklist
    document.getElementById("dcCalcBtn").addEventListener("click", async () => {
      const errorEl = document.getElementById("dcError");
      errorEl.textContent = "";
      try {
        const data = await postDesk("/api/doc-checklist", {
          dangerous_goods: document.getElementById("dcDG").checked,
          temperature_controlled: document.getElementById("dcReefer").checked,
          cross_border: document.getElementById("dcCross").checked,
          fragile: document.getElementById("dcFragile").checked,
          high_value: document.getElementById("dcHigh").checked,
        });
        document.getElementById("dcSummary").textContent = data.summary;
        document.getElementById("dcList").innerHTML = (data.items || []).map((item) =>
          `<li>${item.document}${item.required ? " (required)" : ""}</li>`
        ).join("");
      } catch (err) {
        errorEl.textContent = err.message;
      }
    });

    // Unit converter (client-side)
    const UC_UNITS = {
      mass: ["kg", "lb"],
      length: ["cm", "in", "m", "ft"],
      volume: ["cbm", "cft", "l", "gal"],
      temperature: ["c", "f"],
    };

    function ucConvert(value, category, from, to) {
      if (category === "mass") {
        const kg = from === "kg" ? value : value * 0.45359237;
        return to === "kg" ? kg : kg / 0.45359237;
      }
      if (category === "length") {
        let m = value;
        if (from === "cm") m = value / 100;
        else if (from === "in") m = value * 0.0254;
        else if (from === "ft") m = value * 0.3048;
        if (to === "m") return m;
        if (to === "cm") return m * 100;
        if (to === "in") return m / 0.0254;
        return m / 0.3048;
      }
      if (category === "volume") {
        let cbm = value;
        if (from === "cft") cbm = value * 0.0283168;
        else if (from === "l") cbm = value / 1000;
        else if (from === "gal") cbm = value * 0.00378541;
        if (to === "cbm") return cbm;
        if (to === "cft") return cbm / 0.0283168;
        if (to === "l") return cbm * 1000;
        return cbm / 0.00378541;
      }
      const c = from === "c" ? value : ((value - 32) * 5) / 9;
      return to === "c" ? c : (c * 9) / 5 + 32;
    }

    function ucPopulate() {
      const cat = document.getElementById("ucCategory").value;
      const units = UC_UNITS[cat];
      const fromSel = document.getElementById("ucFrom");
      const toSel = document.getElementById("ucTo");
      fromSel.innerHTML = units.map((u) => `<option value="${u}">${u}</option>`).join("");
      toSel.innerHTML = units.map((u) => `<option value="${u}">${u}</option>`).join("");
      if (cat === "mass") { fromSel.value = "kg"; toSel.value = "lb"; }
      else if (cat === "length") { fromSel.value = "cm"; toSel.value = "in"; }
      else if (cat === "volume") { fromSel.value = "cbm"; toSel.value = "cft"; }
      else { fromSel.value = "c"; toSel.value = "f"; }
      ucRun();
    }

    function ucRun() {
      const amount = parseFloat(document.getElementById("ucAmount").value);
      const cat = document.getElementById("ucCategory").value;
      const from = document.getElementById("ucFrom").value;
      const to = document.getElementById("ucTo").value;
      if (!Number.isFinite(amount)) {
        document.getElementById("ucSummary").textContent = "—";
        return;
      }
      const result = ucConvert(amount, cat, from, to);
      document.getElementById("ucSummary").textContent = `${formatNumber(amount, 4)} ${from} = ${formatNumber(result, 4)} ${to}`;
    }

    document.getElementById("ucCategory").addEventListener("change", ucPopulate);
    ["ucAmount", "ucFrom", "ucTo"].forEach((id) => {
      document.getElementById(id).addEventListener("input", ucRun);
      document.getElementById(id).addEventListener("change", ucRun);
    });
    ucPopulate();

    // Shipment ref
    function updateShipmentRef() {
      const prefix = document.getElementById("srPrefix").value.toUpperCase() || "SHP";
      const seq = String(parseInt(document.getElementById("srSeq").value, 10) || 0).padStart(4, "0");
      const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      document.getElementById("srRef").textContent = `${prefix}-${date}-${seq}`;
    }
    ["srPrefix", "srSeq"].forEach((id) => {
      document.getElementById(id).addEventListener("input", updateShipmentRef);
    });
    updateShipmentRef();
    document.getElementById("srCopyBtn").addEventListener("click", () => {
      navigator.clipboard.writeText(document.getElementById("srRef").textContent);
    });

"""

JS_INSERT = "    document.getElementById(\"whCalcBtn\").addEventListener(\"click\", calculateWarehouse);\n\n"
if JS_INSERT not in text:
    raise SystemExit("JS insert marker not found")
text = text.replace(JS_INSERT, JS_INSERT + JS)

INDEX.write_text(text, encoding="utf-8")
print("Patched", INDEX)