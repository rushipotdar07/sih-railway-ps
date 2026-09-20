import { useMemo, useState } from "react";
import { DEPARTMENTS, DEPT_BY_ID, SEVERITY_BY_ID } from "../constants";

function fmtDay(date) {
  return date.toLocaleDateString(undefined, { weekday: "short", day: "numeric" });
}

function fmtDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function GanttChart({ plan, planningStart, horizonDays, mode, onOverride }) {
  const [popover, setPopover] = useState(null); // { assignment, x, y }

  const dayCols = useMemo(
    () =>
      Array.from({ length: horizonDays }, (_, i) => {
        const d = new Date(planningStart);
        d.setDate(d.getDate() + i);
        return d;
      }),
    [planningStart, horizonDays]
  );

  const totalMs = horizonDays * 24 * 3600 * 1000;
  const daywidthPct = `${100 / horizonDays}%`;

  const scheduled = plan.assignments.filter((a) => a.assigned_start);
  const unscheduled = plan.assignments.filter((a) => !a.assigned_start);

  const sectionOrder = [];
  const bySection = new Map();
  for (const a of scheduled) {
    if (!bySection.has(a.section_id)) {
      bySection.set(a.section_id, []);
      sectionOrder.push(a.section_id);
    }
    bySection.get(a.section_id).push(a);
  }
  sectionOrder.sort((x, y) => bySection.get(y).length - bySection.get(x).length);

  function openPopover(e, assignment) {
    const rect = e.currentTarget.getBoundingClientRect();
    let x = rect.left;
    let y = rect.bottom + 8;
    if (x + 320 > window.innerWidth) x = window.innerWidth - 330;
    if (y + 220 > window.innerHeight) y = rect.top - 220;
    setPopover({ assignment, x, y });
  }

  return (
    <div>
      <div className="gantt-legend">
        {DEPARTMENTS.map((d) => (
          <span className="item" key={d.id}>
            <span className="swatch" style={{ background: d.color }} /> {d.label}
          </span>
        ))}
        <span className="item">
          <span
            className="swatch"
            style={{
              background: "repeating-linear-gradient(45deg, #dc2626, #dc2626 3px, #f87171 3px, #f87171 6px)",
            }}
          />{" "}
          Conflict
        </span>
        {mode === "optimized" && (
          <span className="item">
            <span className="swatch" style={{ background: "var(--navy)" }} /> Locked (override)
          </span>
        )}
        <span style={{ marginLeft: "auto", fontStyle: "italic" }}>
          Click a block for AI reasoning{mode === "optimized" ? " and overrides" : ""}
        </span>
      </div>

      <div className="gantt-wrap">
        <div className="gantt-scroll">
          <div className="gantt-header">
            <div className="row-label-col">Section</div>
            <div className="days">
              {dayCols.map((d, i) => (
                <div className="day-cell" key={i}>
                  {fmtDay(d)}
                </div>
              ))}
            </div>
          </div>
          <div className="gantt-body">
            {sectionOrder.length === 0 ? (
              <div className="empty-state">No scheduled blocks in this horizon.</div>
            ) : (
              sectionOrder.map((sectionId) => {
                const rows = bySection.get(sectionId);
                return (
                  <div className="gantt-row" key={sectionId}>
                    <div className="row-label-col">
                      {rows[0].section_name}
                      <span className="freq">{rows.length} block{rows.length > 1 ? "s" : ""}</span>
                    </div>
                    <div className="track" style={{ "--daywidth": daywidthPct }}>
                      {rows.map((a) => {
                        const start = new Date(a.assigned_start).getTime();
                        const end = new Date(a.assigned_end).getTime();
                        const left = Math.max(0, ((start - planningStart.getTime()) / totalMs) * 100);
                        const width = Math.max(0.4, ((end - start) / totalMs) * 100);
                        const dept = DEPT_BY_ID[a.department];
                        const isLocked = a.reasoning?.startsWith("Locked by controller override");
                        return (
                          <div
                            key={a.request_id}
                            className={`gantt-bar ${a.is_conflict ? "conflict" : ""} ${isLocked ? "locked" : ""}`}
                            style={{
                              left: `${left}%`,
                              width: `${width}%`,
                              background: dept?.color || "#666",
                            }}
                            onClick={(e) => openPopover(e, a)}
                            title={`${dept?.label} · ${a.defect_type} · ${a.severity}`}
                          >
                            <span className="bar-label">{a.severity[0]}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {unscheduled.length > 0 && (
        <div className="unscheduled-strip">
          <strong>{unscheduled.length} request(s) not scheduled</strong> in this horizon — no
          conflict-free window was found: {unscheduled.map((a) => `#${a.request_id}`).join(", ")}
        </div>
      )}

      {popover && (
        <Popover
          data={popover}
          mode={mode}
          onClose={() => setPopover(null)}
          onOverride={() => {
            onOverride(popover.assignment);
            setPopover(null);
          }}
        />
      )}
    </div>
  );
}

function Popover({ data, mode, onClose, onOverride }) {
  const { assignment: a, x, y } = data;
  const dept = DEPT_BY_ID[a.department];
  const sev = SEVERITY_BY_ID[a.severity];
  return (
    <>
      <div
        style={{ position: "fixed", inset: 0, zIndex: 99 }}
        onClick={onClose}
      />
      <div className="popover" style={{ left: x, top: y }}>
        <div className="po-title">
          <span className="dot" style={{ width: 8, height: 8, borderRadius: "50%", background: dept?.color }} />
          {dept?.label} · Request #{a.request_id}
        </div>
        <div className="po-row"><span>Section</span><span>{a.section_name}</span></div>
        <div className="po-row"><span>Defect</span><span>{a.defect_type}</span></div>
        <div className="po-row">
          <span>Severity</span>
          <span style={{ color: sev?.color, fontWeight: 700 }}>{a.severity}</span>
        </div>
        <div className="po-row"><span>Priority score</span><span>{a.priority_score.toFixed(3)}</span></div>
        {a.assigned_start && (
          <div className="po-row">
            <span>Window</span>
            <span>{fmtDateTime(a.assigned_start)} → {fmtDateTime(a.assigned_end)}</span>
          </div>
        )}
        {a.coordinated_with?.length > 0 && (
          <div className="po-row">
            <span>Coordinated with</span>
            <span>#{a.coordinated_with.join(", #")}</span>
          </div>
        )}
        <ScoreBreakdown a={a} />
        <div className="po-reason">{a.reasoning}</div>
        {mode === "optimized" && a.assigned_start && (
          <div className="po-actions">
            <button className="po-btn-override" onClick={onOverride}>
              Override this block
            </button>
            <button className="po-btn-close" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </>
  );
}

const SCORE_FACTORS = [
  { key: "urgency_score", label: "Urgency", weight: 0.35, color: "#f87171" },
  { key: "severity_score", label: "Severity", weight: 0.3, color: "#fb923c" },
  { key: "network_score", label: "Network", weight: 0.2, color: "#60a5fa" },
  { key: "coordination_bonus", label: "Coord.", weight: 0.15, color: "#34d399" },
];

function ScoreBreakdown({ a }) {
  return (
    <div className="score-breakdown">
      {SCORE_FACTORS.map((f) => {
        const raw = a[f.key] ?? 0;
        const pct = Math.max(2, Math.min(100, raw * 100));
        return (
          <div className="score-row" key={f.key}>
            <span className="score-label">{f.label} ×{f.weight}</span>
            <span className="score-track">
              <span className="score-fill" style={{ width: `${pct}%`, background: f.color }} />
            </span>
            <span className="score-val">{raw.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}
