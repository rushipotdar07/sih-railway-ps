import { useEffect, useRef, useState } from "react";

const STEP_DELAY_MS = 480;

export default function EngineConsole({ logLines, runToken, engineStats, onRerun, rerunning }) {
  const [visibleCount, setVisibleCount] = useState(0);
  const bodyRef = useRef(null);

  useEffect(() => {
    setVisibleCount(0);
  }, [runToken]);

  useEffect(() => {
    if (visibleCount >= logLines.length) return;
    const t = setTimeout(() => setVisibleCount((c) => c + 1), STEP_DELAY_MS);
    return () => clearTimeout(t);
  }, [visibleCount, logLines.length]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [visibleCount]);

  const done = visibleCount >= logLines.length;
  const stats = engineStats || {};

  return (
    <div className="card engine-console">
      <div className="engine-console-header">
        <span className="dot-status" style={{ background: done ? "var(--success)" : "var(--warning)" }} />
        <span>AI Engine Run Log</span>
        <span className="engine-console-sub">
          {done ? "computation trace — real numbers from the last solver run" : "computing…"}
        </span>
        <button className="rerun-btn" onClick={onRerun} disabled={rerunning}>
          {rerunning ? "Re-running…" : "▶ Re-run AI engine"}
        </button>
      </div>

      <div className="engine-console-body" ref={bodyRef}>
        {logLines.slice(0, visibleCount).map((l, i) => (
          <div className="log-line" key={i}>
            <span className="log-tag">[{l.tag}]</span> {l.text}
          </div>
        ))}
        {!done && <span className="log-cursor">▌</span>}
      </div>

      {done && (
        <div className="engine-stats-grid">
          <StatChip label="Solver" value={stats.solver} wide />
          <StatChip label="Status" value={stats.status} accent={stats.status === "OPTIMAL"} />
          <StatChip label="Solve time" value={stats.solve_time_seconds != null ? `${stats.solve_time_seconds}s` : "—"} />
          <StatChip label="Objective" value={stats.objective_value ?? "—"} />
          <StatChip label="Decision variables" value={stats.num_boolean_variables ?? "—"} />
          <StatChip label="Hard constraints" value={stats.num_hard_nooverlap_constraints ?? "—"} />
          <StatChip label="Sections involved" value={stats.num_sections_involved ?? "—"} />
          <StatChip label="Windows scanned" value={stats.num_candidate_windows_scanned ?? "—"} />
        </div>
      )}
    </div>
  );
}

function StatChip({ label, value, wide, accent }) {
  return (
    <div className={`stat-chip ${wide ? "wide" : ""}`}>
      <div className="stat-chip-label">{label}</div>
      <div className={`stat-chip-value ${accent ? "accent" : ""}`}>{value}</div>
    </div>
  );
}
