import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { HORIZON_DAYS, PLANNING_START } from "../constants";
import MetricsPanel from "./MetricsPanel";
import GanttChart from "./GanttChart";
import NetworkImpactPanel from "./NetworkImpactPanel";
import OverrideModal from "./OverrideModal";
import EngineConsole from "./EngineConsole";
import { computeMetrics, buildEngineLog } from "../utils";

export default function Dashboard({ refreshKey, notify }) {
  const [horizon, setHorizon] = useState("WEEKLY");
  const [mode, setMode] = useState("optimized"); // 'naive' | 'optimized'
  const [naive, setNaive] = useState(null);
  const [optimized, setOptimized] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overrideTarget, setOverrideTarget] = useState(null);
  const [overrideBusy, setOverrideBusy] = useState(false);
  const [runToken, setRunToken] = useState(0);
  const [rerunning, setRerunning] = useState(false);

  const [sectionsMap, setSectionsMap] = useState([]);
  const [mapLoading, setMapLoading] = useState(true);

  async function loadPlans({ isRerun = false } = {}) {
    isRerun ? setRerunning(true) : setLoading(true);
    setError(null);
    try {
      // Re-fetched from scratch every time - the solver genuinely re-runs
      // against the live queue, so solve_time_seconds/objective_value below
      // are real numbers from this exact request, not cached decoration.
      const result = await api.comparePlan(horizon.toLowerCase());
      setNaive(result.naive);
      setOptimized(result.optimized);
      setMetrics(result.metrics);
      setRunToken((t) => t + 1);
    } catch (err) {
      setError(err.message || "Failed to load plan.");
    } finally {
      setLoading(false);
      setRerunning(false);
    }
  }

  async function loadMap() {
    setMapLoading(true);
    try {
      setSectionsMap(await api.sectionsMap());
    } catch {
      /* non-critical panel */
    } finally {
      setMapLoading(false);
    }
  }

  useEffect(() => {
    loadPlans();
    loadMap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [horizon, refreshKey]);

  async function handleOverrideConfirm(startIso, endIso) {
    setOverrideBusy(true);
    try {
      const newOptimized = await api.overridePlan(horizon.toLowerCase(), {
        request_id: overrideTarget.request_id,
        assigned_start: startIso,
        assigned_end: endIso,
      });
      setOptimized(newOptimized);
      if (naive) setMetrics(computeMetrics(naive, newOptimized));
      setRunToken((t) => t + 1);
      setMode("optimized");
      notify?.(`Request #${overrideTarget.request_id} locked — plan re-optimized around it.`);
      setOverrideTarget(null);
    } catch (err) {
      notify?.(err.message || "Override failed.", "err");
    } finally {
      setOverrideBusy(false);
    }
  }

  const plan = mode === "naive" ? naive : optimized;
  const horizonDays = HORIZON_DAYS[horizon];
  const logLines = useMemo(
    () => (naive && optimized && metrics ? buildEngineLog(naive, optimized, metrics) : []),
    [naive, optimized, metrics]
  );

  return (
    <>
      <div className="toolbar">
        <div className="toggle-group">
          <button className={horizon === "WEEKLY" ? "active" : ""} onClick={() => setHorizon("WEEKLY")}>
            Weekly plan (7d)
          </button>
          <button className={horizon === "MONTHLY" ? "active" : ""} onClick={() => setHorizon("MONTHLY")}>
            Monthly plan (30d)
          </button>
        </div>

        <div className="toggle-group mode-toggle">
          <button
            className={`mode-naive ${mode === "naive" ? "active" : ""}`}
            onClick={() => setMode("naive")}
          >
            Before · Manual/Naive
          </button>
          <button
            className={`mode-optimized ${mode === "optimized" ? "active" : ""}`}
            onClick={() => setMode("optimized")}
          >
            After · AI-Optimized
          </button>
        </div>
      </div>

      {error && <div className="form-msg err" style={{ marginBottom: 16 }}>{error}</div>}

      {logLines.length > 0 && (
        <EngineConsole
          logLines={logLines}
          runToken={runToken}
          engineStats={optimized?.engine}
          onRerun={() => loadPlans({ isRerun: true })}
          rerunning={rerunning}
        />
      )}

      <MetricsPanel metrics={metrics} />

      <div className="dashboard-grid">
        <div className="card card-pad">
          <div className="section-title">
            {horizon === "WEEKLY" ? "Weekly" : "Monthly"} block plan — {mode === "naive" ? "before (manual, decentralized)" : "after (AI-optimized)"}
          </div>
          {loading || !plan ? (
            <div className="spinner-wrap">
              <span className="spinner" /> Running {mode === "naive" ? "naive baseline" : "OR-Tools CP-SAT optimizer"}…
            </div>
          ) : (
            <GanttChart
              plan={plan}
              planningStart={PLANNING_START}
              horizonDays={horizonDays}
              mode={mode}
              onOverride={setOverrideTarget}
            />
          )}
        </div>

        <NetworkImpactPanel sectionsMap={sectionsMap} loading={mapLoading} />
      </div>

      {overrideTarget && (
        <OverrideModal
          assignment={overrideTarget}
          submitting={overrideBusy}
          onCancel={() => setOverrideTarget(null)}
          onConfirm={handleOverrideConfirm}
        />
      )}
    </>
  );
}
