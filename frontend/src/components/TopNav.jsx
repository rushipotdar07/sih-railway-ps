export default function TopNav({ view, setView, onReseed, reseeding }) {
  return (
    <header className="topnav">
      <div className="topnav-brand">
        <div className="mark">🚆</div>
        <div>
          <div className="title">Block Planning Control Centre</div>
          <div className="subtitle">SIH26027 · AI-Powered Automatic Block Planning</div>
        </div>
      </div>

      <nav className="topnav-tabs">
        <button
          className={view === "submit" ? "active" : ""}
          onClick={() => setView("submit")}
        >
          Submit Request
        </button>
        <button
          className={view === "dashboard" ? "active" : ""}
          onClick={() => setView("dashboard")}
        >
          Block Plan Dashboard
        </button>
      </nav>

      <div className="topnav-right">
        <span className="persona-chip">Divisional Section Controller</span>
        <button className="reseed-btn" onClick={onReseed} disabled={reseeding}>
          {reseeding ? "Reseeding…" : "↺ Reset demo data"}
        </button>
      </div>
    </header>
  );
}
