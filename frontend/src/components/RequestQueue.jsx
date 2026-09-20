import { DEPT_BY_ID, SEVERITY_BY_ID } from "../constants";

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RequestQueue({ requests, loading, onDelete }) {
  return (
    <div className="card card-pad">
      <div className="section-title">Unified request queue (BDMS-lite) · {requests.length} total</div>
      {loading ? (
        <div className="spinner-wrap">
          <span className="spinner" /> Loading queue…
        </div>
      ) : requests.length === 0 ? (
        <div className="empty-state">No requests yet — submit one above.</div>
      ) : (
        <div className="queue-table-wrap">
          <table className="queue">
            <thead>
              <tr>
                <th>#</th>
                <th>Department</th>
                <th>Section</th>
                <th>Defect</th>
                <th>Severity</th>
                <th>Overdue</th>
                <th>Preferred window</th>
                <th>Status</th>
                <th>Source</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => {
                const dept = DEPT_BY_ID[r.department];
                const sev = SEVERITY_BY_ID[r.severity];
                return (
                  <tr key={r.request_id}>
                    <td>{r.request_id}</td>
                    <td>
                      <span
                        className="badge"
                        style={{ background: dept?.colorSoft, color: dept?.color }}
                      >
                        <span className="dot" />
                        {dept?.label}
                      </span>
                    </td>
                    <td>{r.section_name || r.section_id}</td>
                    <td>{r.defect_type}</td>
                    <td>
                      <span
                        className="badge"
                        style={{ background: sev?.colorSoft, color: sev?.color }}
                      >
                        <span className="dot" />
                        {sev?.label}
                      </span>
                    </td>
                    <td>{r.overdue_days}d</td>
                    <td>
                      {fmt(r.preferred_window_start)} → {fmt(r.preferred_window_end)}
                    </td>
                    <td>{r.status}</td>
                    <td>{r.source === "live" ? "Submitted" : "Synthetic"}</td>
                    <td>
                      <button
                        className="row-del"
                        title="Remove request"
                        onClick={() => onDelete(r.request_id)}
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
