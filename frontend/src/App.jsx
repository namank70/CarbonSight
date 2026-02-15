import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import InfoTip from "./components/InfoTip.jsx";

import bagImg from "./assets/bag.png";
import aiGpuChipImg from "./assets/ai_gpu_chip.png";
import bottleImg from "./assets/bottle.png";
import logo from "./assets/logo_carbon.png";
import dataCenterCoolingImg from "./assets/data_center_cooling.png";
import electrolyzerImg from "./assets/electrolyzer.png";
import fiberCableImg from "./assets/fiber_cable.png";
import gpuServerImg from "./assets/Gpu_server.png";
import gridBatteryContainerImg from "./assets/grid_battery_container.png";
import laptopImg from "./assets/laptop.png";
import lithiumBatteryPackImg from "./assets/lithium_battery_pack.png";
import solarPanelImg from "./assets/solar_panel.png";
import tshirtImg from "./assets/tshirt.png";

const API_BASE = import.meta.env.VITE_API_URL;

const PRODUCT_CARDS = [
  { key: "t_shirt", name: "T-Shirt", img: tshirtImg, blurb: "Apparel supply chain footprint." },
  { key: "bottle", name: "Bottle", img: bottleImg, blurb: "Packaging + transport impact." },
  { key: "laptop", name: "Laptop", img: laptopImg, blurb: "Energy-intensive manufacturing." },
  { key: "bag", name: "Bag", img: bagImg, blurb: "Materials + shipping tradeoffs." },
  { key: "ai_gpu_chip", name: "AI GPU Chip", img: aiGpuChipImg, blurb: "Semiconductor manufacturing + global logistics impact." },
  { key: "gpu_server", name: "GPU Server", img: gpuServerImg, blurb: "Heavy compute hardware footprint." },
  { key: "data_center_cooling", name: "Data Center Cooling Unit", img: dataCenterCoolingImg, blurb: "Large industrial cooling equipment." },
  { key: "fiber_optic_roll", name: "Fiber Optic Cable Roll", img: fiberCableImg, blurb: "Telecom infrastructure materials impact." },
  { key: "grid_battery_container", name: "Grid-Scale Battery Container", img: gridBatteryContainerImg, blurb: "Utility storage system embodied carbon." },
  { key: "hydrogen_electrolyzer", name: "Hydrogen Electrolyzer", img: electrolyzerImg, blurb: "Industrial hydrogen production hardware." },
  { key: "lithium_battery_pack", name: "Lithium-Ion Battery Pack", img: lithiumBatteryPackImg, blurb: "Battery manufacturing + logistics impact." },
  { key: "solar_panel", name: "Solar Panel", img: solarPanelImg, blurb: "Module manufacturing + transport footprint." },
];

const BREAKDOWN_ITEMS = [
  { key: "materials_kg", label: "Materials" },
  { key: "manufacturing_kg", label: "Manufacturing" },
  { key: "transport_kg", label: "Transport" },
  { key: "packaging_kg", label: "Packaging" },
];

const TOOLTIP_TEXT = {
  originalCo2:
    "Predicted carbon footprint to produce + ship 1 unit of this product, in kg CO2e.",
  greenerCo2:
    "Same prediction after switching to lower-impact options (transport/materials/packaging).",
  score:
    "Category percentile score: lower CO2 in this product category gives higher score.",
  grade:
    "Letter grade mapped from score bands.",
  reduction:
    "Percent CO2 reduction from original to optimized scenario.",
};

const HIGH_GRID_REGIONS = new Set(["india", "china", "bangladesh", "vietnam", "south_korea"]);
const CARBON_TAX_PER_TON_USD = 100;
const CARBON_TAX_PER_KG_USD = CARBON_TAX_PER_TON_USD / 1000;

function clamp01(x) {
  if (Number.isNaN(x)) return 0;
  return Math.max(0, Math.min(1, x));
}

function fmt(n, digits = 3) {
  if (n === null || n === undefined) return "-";
  return Number(n).toFixed(digits);
}

function fmtChangeValue(v) {
  if (v === null || v === undefined) return "(none)";
  const s = String(v).trim();
  return s === "" ? "(none)" : s;
}

function fmtSuggestedChangeValue(field, value) {
  if (value === null || value === undefined) return "(none)";
  const raw = String(value).trim();
  if (raw === "") return "(none)";

  if (field === "manufacturing_energy_kwh") {
    const n = Number(value);
    if (!Number.isNaN(n)) {
      const ceil3 = Math.ceil(n * 1000) / 1000;
      return ceil3.toFixed(3);
    }
  }

  return fmtChangeValue(value);
}

function co2LevelClass(value) {
  if (value <= 20) return "co2Low";
  if (value <= 60) return "co2Medium";
  return "co2High";
}

function useCountUp(target, duration = 900) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const end = Number(target) || 0;
    let frame = 0;
    const start = performance.now();

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - (1 - t) ** 3;
      setDisplay(end * eased);
      if (t < 1) frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return display;
}

function computeCarbonRisk(form, result) {
  const drivers = [];
  const transportMode = result?.used_transport_mode || form.transport_mode;
  const manufacturingCountry = result?.used_origin || form.manufacturing_country;

  if (transportMode === "air") {
    drivers.push("Air transport");
  }
  if (HIGH_GRID_REGIONS.has(String(manufacturingCountry || "").toLowerCase())) {
    drivers.push("High grid intensity region");
  }
  if (Number(form.recycled_content_pct || 0) < 25) {
    drivers.push("Low recycled content");
  }

  const count = drivers.length;
  const level = count >= 2 ? "HIGH" : count === 1 ? "MEDIUM" : "LOW";
  return { level, drivers };
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("t_shirt");
  const [loadingMeta, setLoadingMeta] = useState(true);

  const [form, setForm] = useState({
    unit_weight_kg: 0.22,
    manufacturing_energy_kwh: 0.8,
    recycled_content_pct: 60,
    quantity_units: 10,

    material_1: "organic_cotton",
    material_share_1: 0.8,
    material_2: "recycled_polyester",
    material_share_2: 0.2,

    manufacturing_country: "mexico",
    destination_country: "usa",
    shipping_priority: "greenest",
    transport_mode: "auto",
    packaging_type: "recycled_cardboard_box",
    certification: "gots",
  });

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [distanceInfo, setDistanceInfo] = useState(null);
  const [animationSeed, setAnimationSeed] = useState(0);
  const [simulateCarbonTax, setSimulateCarbonTax] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function loadMeta() {
      try {
        setLoadingMeta(true);
        const res = await axios.get(`${API_BASE}/metadata`);
        if (mounted) setMeta(res.data);
      } catch (_e) {
        if (mounted) setErrorMsg("Could not load metadata. Is the backend running and CORS configured?");
      } finally {
        if (mounted) setLoadingMeta(false);
      }
    }
    loadMeta();
    return () => {
      mounted = false;
    };
  }, []);

  const currentCard = useMemo(
    () => PRODUCT_CARDS.find((p) => p.key === selectedCategory) || PRODUCT_CARDS[0],
    [selectedCategory]
  );

  const categoryMaterials = useMemo(() => {
    if (meta?.category_allowed_materials?.[selectedCategory]) {
      return meta.category_allowed_materials[selectedCategory];
    }
    if (meta?.materials_by_category?.[selectedCategory]) {
      return meta.materials_by_category[selectedCategory];
    }
    return meta?.materials || [];
  }, [meta, selectedCategory]);

  function applyPresetForCategory(category) {
    const preset = meta?.category_presets?.[category];
    if (!preset) return;
    setForm((prev) => ({
      ...prev,
      ...preset,
      quantity_units: prev.quantity_units,
      manufacturing_country: prev.manufacturing_country || "mexico",
      destination_country: prev.destination_country || "usa",
      shipping_priority: prev.shipping_priority || "greenest",
    }));
  }

  useEffect(() => {
    if (!meta) return;
    applyPresetForCategory(selectedCategory);
  }, [meta]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!categoryMaterials.length) return;
    setForm((prev) => {
      const next = { ...prev };
      if (!categoryMaterials.includes(next.material_1)) next.material_1 = categoryMaterials[0];
      if (next.material_2 && !categoryMaterials.includes(next.material_2)) {
        next.material_2 = "";
        next.material_share_1 = 1;
        next.material_share_2 = 0;
      }
      return next;
    });
  }, [categoryMaterials]);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function normalizeShares(next) {
    const s1 = Math.max(Number(next.material_share_1 || 0), 0);
    const s2 = next.material_2 ? Math.max(Number(next.material_share_2 || 0), 0) : 0;
    const sum = s1 + s2;
    if (sum <= 0) return { ...next, material_share_1: 1, material_share_2: 0 };
    return { ...next, material_share_1: s1 / sum, material_share_2: s2 / sum };
  }

  async function onAnalyze() {
    setErrorMsg("");
    setResult(null);

    const normalized = normalizeShares({ ...form });
    const { quantity_units: _quantity, ...payload } = normalized;

    try {
      setSubmitting(true);
      const res = await axios.post(`${API_BASE}/analyze/${selectedCategory}`, payload, {
        headers: { "Content-Type": "application/json" },
      });
      setResult(res.data);
      setAnimationSeed((v) => v + 1);
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Request failed. Check backend logs.";
      setErrorMsg(String(msg));
    } finally {
      setSubmitting(false);
    }
  }

  function applyRecommendationsToForm() {
    if (!result?.recommended_product) return;
    setForm((prev) => ({
      ...prev,
      ...result.recommended_product,
      quantity_units: prev.quantity_units,
      destination_country: prev.destination_country,
      shipping_priority: prev.shipping_priority,
    }));
  }

  async function onAutoDistance() {
    try {
      const res = await axios.get(`${API_BASE}/distance`, {
        params: {
          origin: form.manufacturing_country,
          destination: form.destination_country,
          priority: form.shipping_priority,
        },
      });
      setDistanceInfo(res.data);
      if (form.transport_mode === "auto") {
        setField("transport_mode", "auto");
      }
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Distance lookup failed.";
      setErrorMsg(String(msg));
    }
  }

  const quantity = Math.max(1, Math.min(100, Number(form.quantity_units || 1)));
  const reduction = result?.impact?.reduction_percent ?? 0;
  const reductionBar = clamp01(reduction / 100);

  const originalPerUnit = result?.original?.predicted_co2_kg ?? 0;
  const greenerPerUnit = result?.recommended?.predicted_co2_kg ?? 0;
  const originalTotal = originalPerUnit * quantity;
  const greenerTotal = greenerPerUnit * quantity;
  const totalSavings = Math.max(originalTotal - greenerTotal, 0);
  const routePreview = `${form.manufacturing_country} → ${form.destination_country}`;
  const baselineTaxImpactPerUnit = originalPerUnit * CARBON_TAX_PER_KG_USD;
  const greenerTaxImpactPerUnit = greenerPerUnit * CARBON_TAX_PER_KG_USD;
  const taxSavingsPerUnit = Math.max(baselineTaxImpactPerUnit - greenerTaxImpactPerUnit, 0);

  const animatedOriginal = useCountUp(result ? originalPerUnit : 0);
  const animatedGreener = useCountUp(result ? greenerPerUnit : 0);
  const animatedOriginalTotal = useCountUp(result ? originalTotal : 0);
  const animatedGreenerTotal = useCountUp(result ? greenerTotal : 0);
  const animatedReduction = useCountUp(result ? reduction : 0, 1100);
  const risk = useMemo(() => computeCarbonRisk(form, result), [form, result]);

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <div className="logo">🌿</div>
          <div>
            <div className="title">CarbonSight</div>
            <div className="subtitle">Supply-chain footprint estimator + greener recommendation</div>
          </div>
        </div>
        <div className="pill">
          API: <span className="mono">{API_BASE}</span>
        </div>
      </header>

      <main className="grid">
        <section className="card cardProducts">
          <div className="cardTitle">Pick a product</div>
          <div className="productGrid">
            {PRODUCT_CARDS.map((p) => (
              <button
                key={p.key}
                type="button"
                aria-pressed={selectedCategory === p.key}
                className={`productCard ${selectedCategory === p.key ? "active" : ""}`}
                onClick={() => {
                  setSelectedCategory(p.key);
                  applyPresetForCategory(p.key);
                }}
              >
                <img src={p.img} alt={p.name} className="productImg" />
                <div className="productName">{p.name}</div>
                <div className="productBlurb">{p.blurb}</div>
              </button>
            ))}
          </div>
          <div className="divider" />
          <div className="miniHero">
            <img src={currentCard.img} alt={currentCard.name} className="miniHeroImg" />
            <div>
              <div className="miniHeroTitle">{currentCard.name}</div>
              <div className="miniHeroText">Route-aware estimate with destination country and mode rules.</div>
            </div>
          </div>
          <div className="brandSection" aria-label="CarbonSight branding">
            <div className="riskMeter">
              <div className="riskHeader">Carbon Risk Meter</div>
              <div className={`riskLevel risk${risk.level}`}>Carbon Risk Level: {risk.level}</div>
              <div className="riskLead">Exposure driven by:</div>
              <ul className="riskList">
                {(risk.drivers.length ? risk.drivers : ["Balanced transport mix", "Moderate grid intensity", "Adequate recycled content"]).map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            </div>
            <img src={logo} alt="CarbonSight logo" className="brandLogo" />
          </div>
        </section>

        <section className="card cardInputs">
          <div className="cardTitle">Inputs</div>
          {loadingMeta && <div className="hint">Loading dropdown values…</div>}
          {!meta && !loadingMeta && <div className="errorBox">Metadata not loaded. Check backend and CORS.</div>}

          <div className="form">
            <div className="inputGroup">
              <div className="inputGroupTitle"><span>🌍</span> Route & Logistics</div>
              <div className="row">
                <label>Quantity (units): {quantity}</label>
                <input
                  className="rangeInput"
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={quantity}
                  onChange={(e) => setField("quantity_units", Number(e.target.value))}
                />
                <div className="rangeMeta">
                  <span>1</span>
                  <span className="rangeCenter">{quantity} units</span>
                  <span>100</span>
                </div>
              </div>

              <div className="row">
                <label>Manufacturing country</label>
                <select value={form.manufacturing_country} onChange={(e) => setField("manufacturing_country", e.target.value)}>
                  {(meta?.manufacturing_countries || [form.manufacturing_country]).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Destination country</label>
                <select value={form.destination_country} onChange={(e) => setField("destination_country", e.target.value)}>
                  {(meta?.destination_countries || [form.destination_country]).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Shipping priority</label>
                <select value={form.shipping_priority} onChange={(e) => setField("shipping_priority", e.target.value)}>
                  {(meta?.shipping_priorities || [form.shipping_priority]).map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Transport mode (validated by route)</label>
                <select value={form.transport_mode} onChange={(e) => setField("transport_mode", e.target.value)}>
                  <option value="auto">auto (recommended)</option>
                  {(meta?.transport_modes || [form.transport_mode]).map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <button className="secondary routeButton" type="button" onClick={onAutoDistance}>
                Auto-calculate distance
              </button>

              <div className="routeBox">
                <div><b>Distance (auto):</b> {fmt(distanceInfo?.distance_km ?? result?.used_distance_km, 1)} km</div>
                <div><b>Recommended mode:</b> {distanceInfo?.recommended_mode || result?.routing?.recommended_transport_mode || "-"}</div>
              </div>
            </div>

            <div className="inputGroup">
              <div className="inputGroupTitle"><span>⚙️</span> Manufacturing & Packaging</div>
              <div className="row">
                <label>Unit weight (kg)</label>
                <input type="number" step="0.01" value={form.unit_weight_kg} onChange={(e) => setField("unit_weight_kg", Number(e.target.value))} />
              </div>

              <div className="row">
                <label>Manufacturing energy (kWh)</label>
                <input type="number" step="0.01" value={form.manufacturing_energy_kwh} onChange={(e) => setField("manufacturing_energy_kwh", Number(e.target.value))} />
              </div>

              <div className="row">
                <label>Recycled content (%)</label>
                <input type="number" step="1" value={form.recycled_content_pct} onChange={(e) => setField("recycled_content_pct", Number(e.target.value))} />
              </div>

              <div className="row">
                <label>Packaging type</label>
                <select value={form.packaging_type} onChange={(e) => setField("packaging_type", e.target.value)}>
                  {(meta?.packaging_types || [form.packaging_type]).map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Certification (display only)</label>
                <select value={form.certification} onChange={(e) => setField("certification", e.target.value)}>
                  {(meta?.certifications || [form.certification]).map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="inputGroup">
              <div className="inputGroupTitle"><span>📦</span> Material Mix</div>
              <div className="row">
                <label>Material 1</label>
                <select value={form.material_1} onChange={(e) => setField("material_1", e.target.value)}>
                  {(categoryMaterials.length ? categoryMaterials : [form.material_1]).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Material 1 share</label>
                <input type="number" step="0.05" value={form.material_share_1} onChange={(e) => setField("material_share_1", Number(e.target.value))} />
              </div>

              <div className="row">
                <label>Material 2 (optional)</label>
                <select value={form.material_2} onChange={(e) => setField("material_2", e.target.value)}>
                  <option value="">(none)</option>
                  {categoryMaterials.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>

              <div className="row">
                <label>Material 2 share</label>
                <input type="number" step="0.05" value={form.material_share_2} onChange={(e) => setField("material_share_2", Number(e.target.value))} />
              </div>
            </div>

            <div className="stickyAnalyze">
              <button className="primary analyzeButton" onClick={onAnalyze} disabled={submitting}>
                {submitting ? "Analyzing…" : "Analyze footprint"}
              </button>
            </div>
            {errorMsg && <div className="errorBox">{errorMsg}</div>}
          </div>
        </section>

        <section className={`card cardResults ${result ? "resultVisible" : ""}`}>
          <div className="cardTitle">Results</div>
          <div className="summaryStrip">
            <div className="summaryItem">
              <div className="summaryIcon">🧾</div>
              <div>
                <div className="summaryLabel">Estimated CO2</div>
                <div className={`summaryValue ${co2LevelClass(originalPerUnit)}`}>
                  {result ? `${fmt(animatedOriginalTotal, 2)} kg` : "-"}
                </div>
              </div>
            </div>
            <div className="summaryItem">
              <div className="summaryIcon">🚚</div>
              <div>
                <div className="summaryLabel">Route</div>
                <div className="summaryValueRoute">{result ? `${result?.used_origin} → ${result?.used_destination}` : routePreview}</div>
              </div>
            </div>
            <div className="summaryItem">
              <div className="summaryIcon">📉</div>
              <div>
                <div className="summaryLabel">Reduction</div>
                <div className="summaryValuePositive">{result ? `${fmt(animatedReduction, 1)}%` : "-"}</div>
              </div>
            </div>
          </div>
          {!result && <div className="hint">Run an analysis to see predicted CO2 + recommendations.</div>}

          {result && (
            <>
              {!!result?.warnings?.length && (
                <div className="warnBox">
                  {result.warnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}

              <div className="routeBox routeBoxResults">
                <div className="routeRow"><span className="routeLabel">Route</span><span className="routeValue">{result?.used_origin} → {result?.used_destination}</span></div>
                <div className="routeRow"><span className="routeLabel">Distance (auto)</span><span className="routeValue">{fmt(result?.used_distance_km, 1)} km</span></div>
                <div className="routeRow"><span className="routeLabel">Type</span><span className="routeValue">{result?.routing?.route_type}</span></div>
                <div className="routeRow"><span className="routeLabel">Recommended mode</span><span className="routeValue">{result?.routing?.recommended_transport_mode}</span></div>
                <div className="routeRow"><span className="routeLabel">Used mode</span><span className="routeValue">{result?.used_transport_mode}</span></div>
              </div>

              <div className="kpiRow">
                <div className="kpi">
                  <div className="kpiLabel labelWithTip">Original CO2 (kg) <InfoTip text={TOOLTIP_TEXT.originalCo2} /></div>
                  <div className={`kpiValue ${co2LevelClass(originalPerUnit)}`}>{fmt(animatedOriginal, 3)}</div>
                  <div className="kpiSubStrong">Total for {quantity} units: {fmt(animatedOriginalTotal, 3)} kg CO2</div>
                  <div className="kpiSub">Score {result.original.score_0_100} <InfoTip text={TOOLTIP_TEXT.score} /> / Grade {result.original.grade} <InfoTip text={TOOLTIP_TEXT.grade} /></div>
                </div>
                <div className="kpi">
                  <div className="kpiLabel labelWithTip">Greener CO2 (kg) <InfoTip text={TOOLTIP_TEXT.greenerCo2} /></div>
                  <div className={`kpiValue ${co2LevelClass(greenerPerUnit)}`}>{fmt(animatedGreener, 3)}</div>
                  <div className="kpiSubStrong">Total for {quantity} units: {fmt(animatedGreenerTotal, 3)} kg CO2</div>
                  <div className="kpiSub">Score {result.recommended.score_0_100} <InfoTip text={TOOLTIP_TEXT.score} /> / Grade {result.recommended.grade} <InfoTip text={TOOLTIP_TEXT.grade} /></div>
                </div>
              </div>

              <div className="impact">
                <div className="impactTop">
                  <div className="impactLabel labelWithTip">Reduction <InfoTip text={TOOLTIP_TEXT.reduction} /></div>
                  <div className="impactValue">{fmt(animatedReduction, 1)}%</div>
                </div>
                <div className="bar"><div className="barFill" style={{ width: `${reductionBar * 100}%` }} /></div>
                <div className="impactSub">Estimated total savings for {quantity} units: {fmt(totalSavings, 3)} kg CO2</div>
              </div>

              <div className="divider" />
              <div className="sectionTitle">Emission breakdown (approx.)</div>
              <div className="hint">{result?.breakdown?.original?.method} Values are per unit (kg CO2e/unit).</div>
              <div className="breakdownGrid">
                <div className="breakdownCard">
                  <div className="breakdownTitle">Original</div>
                  {BREAKDOWN_ITEMS.map((item) => {
                    const value = result?.breakdown?.original?.components_kg?.[item.key] ?? 0;
                    const share = (result?.breakdown?.original?.shares_percent?.[item.key.replace("_kg", "_percent")] ?? 0) / 100;
                    return (
                      <div key={`orig-${item.key}-${animationSeed}`} className="breakdownRow">
                        <div className="breakdownLabel">{item.label}</div>
                        <div className="breakdownValue">{fmt(value, 3)} kg CO2e/unit</div>
                        <div className="breakdownBar"><div className="breakdownBarFill" style={{ "--target": `${clamp01(share) * 100}%` }} /></div>
                      </div>
                    );
                  })}
                </div>
                <div className="breakdownCard">
                  <div className="breakdownTitle">Greener</div>
                  {BREAKDOWN_ITEMS.map((item) => {
                    const value = result?.breakdown?.recommended?.components_kg?.[item.key] ?? 0;
                    const share = (result?.breakdown?.recommended?.shares_percent?.[item.key.replace("_kg", "_percent")] ?? 0) / 100;
                    return (
                      <div key={`green-${item.key}-${animationSeed}`} className="breakdownRow">
                        <div className="breakdownLabel">{item.label}</div>
                        <div className="breakdownValue">{fmt(value, 3)} kg CO2e/unit</div>
                        <div className="breakdownBar"><div className="breakdownBarFill" style={{ "--target": `${clamp01(share) * 100}%` }} /></div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="divider" />
              <div className="sectionTitle">Suggested changes</div>
              <div className="suggestedPanel">
                {result.changes?.length ? (
                  <>
                    <ul className="changes">
                      {result.changes.map((c, idx) => (
                        <li key={idx}>
                          <span className="changeField mono">{c.field}</span>
                          <span className="changeArrow">:</span>
                          <span className="from">{fmtSuggestedChangeValue(c.field, c.from)}</span>
                          <span className="changeArrow">→</span>
                          <span className="to">{fmtSuggestedChangeValue(c.field, c.to)}</span>
                          <span className="changeSaving">saves ~{fmt(c.estimated_savings_kg_per_unit, 3)} kg/unit</span>
                        </li>
                      ))}
                    </ul>
                    <button className="secondary applyBtn" onClick={applyRecommendationsToForm}>
                      Apply recommended changes to form
                    </button>
                  </>
                ) : (
                  <div className="hint">No carbon-reducing changes found under current constraints.</div>
                )}
              </div>

              <div className="divider" />
              <div className="quickSummaryBox">
                <div className="quickSummaryTitle">Quick summary</div>
                <div className="quickSummaryRow"><span>Original total</span><b>{fmt(originalTotal, 3)} kg CO2</b></div>
                <div className="quickSummaryRow"><span>Greener total</span><b>{fmt(greenerTotal, 3)} kg CO2</b></div>
                <div className="quickSummaryRow"><span>Total savings</span><b>{fmt(totalSavings, 3)} kg CO2</b></div>
                <div className="quickSummaryRow"><span>Recommended changes</span><b>{result.changes?.length || 0}</b></div>
              </div>

              <div className="sectionTitle">Carbon Tax Simulation</div>
              <div className="taxSimBox">
                <label className="taxToggle">
                  <input
                    type="checkbox"
                    checked={simulateCarbonTax}
                    onChange={(e) => setSimulateCarbonTax(e.target.checked)}
                  />
                  <span>Simulate ${CARBON_TAX_PER_TON_USD} per ton carbon tax</span>
                </label>
                {simulateCarbonTax ? (
                  <div className="taxRows">
                    <div className="taxRow">
                      <span>Baseline cost impact</span>
                      <b>${fmt(baselineTaxImpactPerUnit, 2)} per unit</b>
                    </div>
                    <div className="taxRow">
                      <span>Greener scenario</span>
                      <b>${fmt(greenerTaxImpactPerUnit, 2)} per unit</b>
                    </div>
                    <div className="taxRow taxSavings">
                      <span>Estimated tax savings</span>
                      <b>${fmt(taxSavingsPerUnit, 2)} per unit</b>
                    </div>
                  </div>
                ) : (
                  <div className="hint">Enable simulation to compare climate impact with cost exposure.</div>
                )}
              </div>
            </>
          )}
        </section>
      </main>

      <footer className="footer">
        <span className="mono">CarbonSight</span> - FastAPI + Random Forest + React
        {result?.lifecycle_boundary && <div className="boundaryNote">{result.lifecycle_boundary}</div>}
      </footer>
    </div>
  );
}
