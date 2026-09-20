function hours(min) {
  return (min / 60).toFixed(1);
}

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;
  return (
    <div className="metrics-row">
      <div className="metric-card">
        <div className="label">Downtime reduction</div>
        <div className="value highlight">{metrics.downtime_reduction_pct}%</div>
        <div className="sub">
          {hours(metrics.naive_downtime_min)}h → {hours(metrics.optimized_downtime_min)}h blocked
        </div>
      </div>
      <div className="metric-card">
        <div className="label">Conflicts avoided</div>
        <div className="value highlight">{metrics.conflicts_avoided}</div>
        <div className="sub">
          {metrics.naive_conflicts} → {metrics.optimized_conflicts} overlapping blocks
        </div>
      </div>
      <div className="metric-card">
        <div className="label">Requests scheduled</div>
        <div className="value">
          {metrics.optimized_scheduled}/{metrics.total_requests}
        </div>
        <div className="sub">vs {metrics.naive_scheduled} in manual process</div>
      </div>
      <div className="metric-card">
        <div className="label">Zero-conflict plan</div>
        <div className="value" style={{ color: metrics.optimized_conflicts === 0 ? "var(--success)" : "var(--danger)" }}>
          {metrics.optimized_conflicts === 0 ? "Yes ✓" : "No"}
        </div>
        <div className="sub">AI-optimized, CP-SAT solved</div>
      </div>
    </div>
  );
}
