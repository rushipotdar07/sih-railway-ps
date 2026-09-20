import { useState } from "react";

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

export default function OverrideModal({ assignment, onCancel, onConfirm, submitting }) {
  const startDefault = assignment.assigned_start
    ? new Date(assignment.assigned_start)
    : new Date();
  const endDefault = assignment.assigned_end
    ? new Date(assignment.assigned_end)
    : new Date(Date.now() + 2 * 3600000);

  const [start, setStart] = useState(toLocalInputValue(startDefault));
  const [end, setEnd] = useState(toLocalInputValue(endDefault));
  const [error, setError] = useState(null);

  function handleConfirm() {
    // Compare as Date objects (fine even under timezone conversion, since both
    // shift by the same offset) but send the raw naive local strings - the
    // backend's timeline is all naive wall-clock, not real UTC.
    if (new Date(end) <= new Date(start)) {
      setError("End time must be after start time.");
      return;
    }
    onConfirm(start, end);
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>What-if override</h3>
        <p className="desc">
          Pin request #{assignment.request_id} ({assignment.section_name}) to a manual window.
          The AI engine will re-optimize every other pending request around this fixed choice.
        </p>
        <div className="form-grid">
          <div className="field">
            <label>New window start</label>
            <input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="field">
            <label>New window end</label>
            <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        </div>
        {error && <p className="form-msg err" style={{ marginTop: 10 }}>{error}</p>}
        <div className="modal-actions">
          <button className="btn-secondary" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleConfirm} disabled={submitting}>
            {submitting ? "Re-optimizing…" : "Lock & re-optimize"}
          </button>
        </div>
      </div>
    </div>
  );
}
