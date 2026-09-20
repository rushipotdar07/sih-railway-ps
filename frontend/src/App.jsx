import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import TopNav from "./components/TopNav";
import RequestForm from "./components/RequestForm";
import RequestQueue from "./components/RequestQueue";
import Dashboard from "./components/Dashboard";
import Toast from "./components/Toast";

export default function App() {
  const [view, setView] = useState("submit");
  const [sections, setSections] = useState([]);
  const [requests, setRequests] = useState([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [reseeding, setReseeding] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toast, setToast] = useState(null);

  const notify = useCallback((text, type = "ok") => {
    setToast({ text, type });
    setTimeout(() => setToast(null), 3200);
  }, []);

  const loadSections = useCallback(async () => {
    try {
      setSections(await api.listSections());
    } catch (err) {
      notify(err.message || "Could not load sections.", "err");
    }
  }, [notify]);

  const loadRequests = useCallback(async () => {
    setQueueLoading(true);
    try {
      setRequests(await api.listRequests());
    } catch (err) {
      notify(err.message || "Could not load request queue.", "err");
    } finally {
      setQueueLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadSections();
    loadRequests();
  }, [loadSections, loadRequests]);

  async function handleDelete(id) {
    try {
      await api.deleteRequest(id);
      setRequests((rs) => rs.filter((r) => r.request_id !== id));
    } catch (err) {
      notify(err.message || "Could not delete request.", "err");
    }
  }

  async function handleReseed() {
    if (!confirm("This wipes all live-submitted requests and rebuilds demo data. Continue?")) return;
    setReseeding(true);
    try {
      await api.reseed();
      notify("Demo data reset.");
      await Promise.all([loadSections(), loadRequests()]);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      notify(err.message || "Reseed failed.", "err");
    } finally {
      setReseeding(false);
    }
  }

  function handleSubmitted() {
    loadRequests();
    setRefreshKey((k) => k + 1);
    notify("Submitted. Re-run the dashboard to see it scheduled.");
  }

  return (
    <div className="app-shell">
      <TopNav view={view} setView={setView} onReseed={handleReseed} reseeding={reseeding} />

      {view === "submit" ? (
        <div className="page">
          <div className="page-header">
            <h1>Submit a maintenance / block request</h1>
            <p>
              One shared form behind three department views (Engineering, Signal &amp; Telecom,
              Traction). Every submission lands in the same unified queue below — the BDMS-lite
              inbox the AI scheduling engine reads from.
            </p>
          </div>
          <div style={{ display: "grid", gap: 20 }}>
            <RequestForm sections={sections} onSubmitted={handleSubmitted} />
            <RequestQueue requests={requests} loading={queueLoading} onDelete={handleDelete} />
          </div>
        </div>
      ) : (
        <div className="page">
          <div className="page-header">
            <h1>AI-optimized block plan</h1>
            <p>
              Google OR-Tools CP-SAT scheduler vs. today's decentralized manual process, run
              against the live unified queue. Toggle horizons and before/after; click any block
              for its priority reasoning or to force a what-if override.
            </p>
          </div>
          <Dashboard refreshKey={refreshKey} notify={notify} />
        </div>
      )}

      <Toast message={toast?.text} type={toast?.type} />
    </div>
  );
}
