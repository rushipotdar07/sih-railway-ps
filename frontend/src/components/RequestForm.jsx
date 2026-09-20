import { useEffect, useState } from "react";
import { api } from "../api";
import { DEPARTMENTS, SEVERITY } from "../constants";

const DURATION_BY_SEVERITY = { CRITICAL: 180, MAJOR: 120, MINOR: 90 };

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

function defaultWindow() {
  const start = new Date();
  start.setDate(start.getDate() + 2);
  start.setHours(2, 0, 0, 0);
  const end = new Date(start.getTime() + 120 * 60000);
  return { start: toLocalInputValue(start), end: toLocalInputValue(end) };
}

export default function RequestForm({ sections, onSubmitted }) {
  const [dept, setDept] = useState(DEPARTMENTS[0].id);
  const [sectionId, setSectionId] = useState("");
  const [defectType, setDefectType] = useState(DEPARTMENTS[0].defectTypes[0]);
  const [severity, setSeverity] = useState("MAJOR");
  const [overdueDays, setOverdueDays] = useState(0);
  const [win, setWin] = useState(defaultWindow());
  const [duration, setDuration] = useState(DURATION_BY_SEVERITY.MAJOR);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState(null);

  const currentDept = DEPARTMENTS.find((d) => d.id === dept);
  const eligibleSections =
    dept === "TRACTION" ? sections.filter((s) => s.is_electrified) : sections;

  useEffect(() => {
    setDefectType(currentDept.defectTypes[0]);
  }, [dept]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!sectionId && eligibleSections.length) {
      setSectionId(eligibleSections[0].section_id);
    }
  }, [eligibleSections, sectionId]);

  useEffect(() => {
    setDuration(DURATION_BY_SEVERITY[severity]);
  }, [severity]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setMsg(null);
    try {
      await api.submitRequest({
        department: dept,
        section_id: sectionId,
        defect_type: defectType,
        severity,
        overdue_days: Number(overdueDays) || 0,
        // Sent as naive local wall-clock strings (no timezone conversion) - the
        // whole backend timeline (real timetable + synthetic data) is anchored
        // to naive datetimes on a fictional Sept 2026 demo clock, not real UTC.
        preferred_window_start: win.start,
        preferred_window_end: win.end,
        estimated_duration_min: Number(duration) || 120,
        notes: notes || undefined,
      });
      setMsg({ type: "ok", text: "Request submitted to the unified queue." });
      setNotes("");
      setOverdueDays(0);
      onSubmitted?.();
    } catch (err) {
      setMsg({ type: "err", text: err.message || "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="card card-pad" onSubmit={handleSubmit}>
      <div className="section-title">1. Choose department</div>
      <div className="dept-tabs">
        {DEPARTMENTS.map((d) => (
          <button
            type="button"
            key={d.id}
            className={`dept-tab ${dept === d.id ? "active" : ""}`}
            style={{ "--dept-color": d.color, "--dept-soft": d.colorSoft }}
            onClick={() => setDept(d.id)}
          >
            <span className="dot" style={{ background: d.color }} />
            {d.label}
            <span className="tag">{d.shortLabel}</span>
          </button>
        ))}
      </div>

      <div className="section-title">2. Describe the request</div>
      <div className="form-grid">
        <div className="field">
          <label>Section</label>
          <select value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
            {eligibleSections.map((s) => (
              <option key={s.section_id} value={s.section_id}>
                {s.section_name} · {s.daily_train_frequency} trains/day
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Defect / maintenance type</label>
          <select value={defectType} onChange={(e) => setDefectType(e.target.value)}>
            {currentDept.defectTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="field span-2">
          <label>Severity</label>
          <div className="severity-picker">
            {SEVERITY.map((s) => (
              <button
                type="button"
                key={s.id}
                className={`severity-btn ${severity === s.id ? "active" : ""}`}
                style={severity === s.id ? { background: s.color } : {}}
                onClick={() => setSeverity(s.id)}
              >
                {s.label}
                <div style={{ fontWeight: 500, fontSize: 10.5, marginTop: 2, opacity: 0.85 }}>
                  SLA {s.slaDays}d
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Days overdue (0 if newly reported)</label>
          <input
            type="number"
            min="0"
            value={overdueDays}
            onChange={(e) => setOverdueDays(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Estimated block duration (minutes)</label>
          <input
            type="number"
            min="30"
            step="15"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>

        <div className="field">
          <label>Preferred window start</label>
          <input
            type="datetime-local"
            value={win.start}
            onChange={(e) => setWin((w) => ({ ...w, start: e.target.value }))}
          />
        </div>

        <div className="field">
          <label>Preferred window end</label>
          <input
            type="datetime-local"
            value={win.end}
            onChange={(e) => setWin((w) => ({ ...w, end: e.target.value }))}
          />
        </div>

        <div className="field span-2">
          <label>Notes (optional)</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>

      <div className="form-actions">
        <button className="btn-primary" type="submit" disabled={submitting || !sectionId}>
          {submitting ? "Submitting…" : "Submit to unified queue"}
        </button>
        {msg && <span className={`form-msg ${msg.type}`}>{msg.text}</span>}
      </div>
    </form>
  );
}
