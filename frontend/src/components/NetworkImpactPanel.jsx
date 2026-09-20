export default function NetworkImpactPanel({ sectionsMap, loading }) {
  const top = [...sectionsMap]
    .sort((a, b) => b.pending_request_count - a.pending_request_count || b.daily_train_frequency - a.daily_train_frequency)
    .slice(0, 12);
  const maxCount = Math.max(1, ...top.map((s) => s.pending_request_count));

  return (
    <div className="card card-pad network-panel">
      <div className="section-title">Network impact — busiest sections</div>
      {loading ? (
        <div className="spinner-wrap">
          <span className="spinner" /> Loading…
        </div>
      ) : top.length === 0 ? (
        <div className="empty-state">No data.</div>
      ) : (
        top.map((s) => {
          const pct = Math.min(100, (s.pending_request_count / maxCount) * 100);
          const color = s.pending_request_count >= maxCount * 0.66
            ? "var(--danger)"
            : s.pending_request_count >= maxCount * 0.33
            ? "var(--warning)"
            : "var(--success)";
          return (
            <div className="impact-row" key={s.section_id} title={`${s.daily_train_frequency} trains/day`}>
              <span className="name">{s.section_name}</span>
              <span className="impact-bar-track">
                <span className="impact-bar-fill" style={{ width: `${pct}%`, background: color }} />
              </span>
              <span className="impact-count">{s.pending_request_count}</span>
            </div>
          );
        })
      )}
      <p style={{ fontSize: 11.5, color: "var(--text-faint)", marginTop: 14, lineHeight: 1.5 }}>
        Bars show pending-request load per section; color intensity flags corridors nearing
        over-block risk. Frequency is real daily train count derived from the timetable.
      </p>
    </div>
  );
}
