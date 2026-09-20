export const DEPARTMENTS = [
  {
    id: "ENGINEERING",
    label: "Engineering",
    shortLabel: "TMS",
    color: "#2563eb",
    colorSoft: "#dbeafe",
    defectTypes: [
      "Rail fracture risk",
      "Ballast degradation",
      "Track geometry deviation",
      "Rail wear beyond limit",
      "Fastening failure",
      "Bridge deck inspection due",
    ],
  },
  {
    id: "SIGNAL_TELECOM",
    label: "Signal & Telecom",
    shortLabel: "SMMS",
    color: "#7c3aed",
    colorSoft: "#ede9fe",
    defectTypes: [
      "Signal relay fault",
      "Point machine malfunction",
      "Track circuit failure",
      "Axle counter fault",
      "Cable insulation fault",
      "Interlocking overdue check",
    ],
  },
  {
    id: "TRACTION",
    label: "Traction",
    shortLabel: "TDMS",
    color: "#0d9488",
    colorSoft: "#ccfbf1",
    defectTypes: [
      "OHE wire wear",
      "Insulator flashover risk",
      "Feeder cable fault",
      "Traction substation overdue check",
      "Pantograph contact wear",
    ],
  },
];

export const DEPT_BY_ID = Object.fromEntries(DEPARTMENTS.map((d) => [d.id, d]));

export const SEVERITY = [
  { id: "CRITICAL", label: "Critical", color: "#dc2626", colorSoft: "#fee2e2", slaDays: 3 },
  { id: "MAJOR", label: "Major", color: "#d97706", colorSoft: "#fef3c7", slaDays: 10 },
  { id: "MINOR", label: "Minor", color: "#16a34a", colorSoft: "#dcfce7", slaDays: 30 },
];

export const SEVERITY_BY_ID = Object.fromEntries(SEVERITY.map((s) => [s.id, s]));

export const PLANNING_START = new Date("2026-09-01T00:00:00");
export const HORIZON_DAYS = { WEEKLY: 7, MONTHLY: 30 };
