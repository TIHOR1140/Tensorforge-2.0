import { useState, useEffect, useCallback } from 'react';

const API_BASE = '';

// --- Toast System ---
function ToastContainer({ toasts, removeToast }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white transition-all duration-300 ${
            t.type === 'success' ? 'bg-emerald-600' : t.type === 'error' ? 'bg-rose-600' : 'bg-indigo-600'
          }`}
        >
          <span>{t.type === 'success' ? '[OK]' : t.type === 'error' ? '[!]' : '[i]'}</span>
          <span className="flex-1">{t.message}</span>
          <button onClick={() => removeToast(t.id)} className="ml-2 opacity-70 hover:opacity-100">x</button>
        </div>
      ))}
    </div>
  );
}

// --- Spinner ---
function Spinner({ size = 'sm' }) {
  const s = size === 'lg' ? 'w-6 h-6 border-2' : 'w-4 h-4 border-2';
  return <div className={`${s} border-current border-t-transparent rounded-full animate-spin inline-block`}></div>;
}

// --- Status Badge ---
function StatusBadge({ status }) {
  const isOk = status === 'ok' || status === 'healthy';
  const isLoading = status === 'loading' || status === 'pending';
  const isRunning = status === 'running';
  const isFailed = status === 'failed' || status === 'offline' || status === 'error';
  const isSucceeded = status === 'succeeded';

  const colorClass = isOk || isSucceeded
    ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
    : isLoading
    ? 'bg-amber-100 text-amber-700 border-amber-200'
    : isRunning
    ? 'bg-blue-100 text-blue-700 border-blue-200'
    : isFailed
    ? 'bg-rose-100 text-rose-700 border-rose-200'
    : 'bg-slate-100 text-slate-600 border-slate-200';

  const label = isOk ? 'Online' : status || 'Checking';

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${colorClass}`}>
      {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>}
      {isOk && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>}
      {isLoading && <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>}
      {isFailed && <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>}
      {label}
    </span>
  );
}


// --- Category-to-Team mapping reference ---
const CATEGORY_MAP = [
  { category: 'payment_refund', team: 'Payments & Refunds', color: 'text-emerald-600' },
  { category: 'ride_trip_issue', team: 'Ride Operations', color: 'text-cyan-600' },
  { category: 'lost_item', team: 'Lost & Found', color: 'text-indigo-600' },
  { category: 'order_missing_wrong', team: 'Food Operations', color: 'text-amber-600' },
  { category: 'delivery_delay', team: 'Delivery Operations', color: 'text-orange-600' },
  { category: 'food_quality', team: 'Restaurant Quality', color: 'text-rose-600' },
  { category: 'account_promo', team: 'Account Services', color: 'text-purple-600' },
  { category: 'safety_conduct', team: 'Trust & Safety', color: 'text-red-600' },
  { category: 'app_technical', team: 'Tech Support', color: 'text-blue-600' },
  { category: 'general_inquiry', team: 'Front-line Support', color: 'text-teal-600' },
  { category: 'spam_irrelevant', team: 'Auto-close / Spam Filter', color: 'text-slate-500' },
];

// --- NAV ITEMS ---
const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'D' },
  { id: 'single',    label: 'Single Predict', icon: 'S' },
  { id: 'batch',     label: 'Batch Predict', icon: 'B' },
  { id: 'jobs',      label: 'Async Jobs', icon: 'J' },
  { id: 'settings',  label: 'Settings', icon: 'G' },
];

// ===== MAIN APP =====
export default function App() {
  const [page, setPage] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('tf2_api_key') || '');
  const [health, setHealth] = useState(null);
  const [toasts, setToasts] = useState([]);

  // Toast helpers
  const toast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);
  const removeToast = useCallback((id) => setToasts(prev => prev.filter(t => t.id !== id)), []);

  // Auth headers
  const headers = useCallback(() => {
    const h = { 'Content-Type': 'application/json' };
    if (apiKey) h['X-API-Key'] = apiKey;
    return h;
  }, [apiKey]);

  // Health polling
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setHealth(data);
    } catch {
      setHealth({ status: 'offline' });
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const iv = setInterval(checkHealth, 30000);
    return () => clearInterval(iv);
  }, [checkHealth]);

  useEffect(() => {
    if (apiKey) localStorage.setItem('tf2_api_key', apiKey);
  }, [apiKey]);

  // ---- SINGLE PREDICT ----
  const [channel, setChannel] = useState('email');
  const [text, setText] = useState('');
  const [sResult, setSResult] = useState(null);
  const [sLoading, setSLoading] = useState(false);

  const predictSingle = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    setSLoading(true); setSResult(null);
    try {
      const res = await fetch(`${API_BASE}/predict`, { method: 'POST', headers: headers(), body: JSON.stringify({ channel, text }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || data.detail || `Error ${res.status}`);
      setSResult(data);
      toast('Classification complete', 'success');
    } catch (e) { toast(e.message, 'error'); }
    finally { setSLoading(false); }
  };

  // ---- BATCH PREDICT ----
  const [batchInput, setBatchInput] = useState('[\n  {"channel": "email", "text": "My order never arrived and I was charged"},\n  {"channel": "chat", "text": "I left my bag in the car"}\n]');
  const [bResults, setBResults] = useState(null);
  const [bLoading, setBLoading] = useState(false);

  const predictBatch = async () => {
    setBLoading(true); setBResults(null);
    try {
      const tickets = JSON.parse(batchInput);
      if (!Array.isArray(tickets)) throw new Error('Input must be a JSON array');
      const res = await fetch(`${API_BASE}/predict/batch`, { method: 'POST', headers: headers(), body: JSON.stringify({ tickets }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || data.detail || `Error ${res.status}`);
      setBResults(data);
      toast(`Classified ${data.results?.length || 0} tickets`, 'success');
    } catch (e) { toast(e.message, 'error'); }
    finally { setBLoading(false); }
  };

  // ---- ASYNC JOBS ----
  const [jobInput, setJobInput] = useState('[\n  {"channel": "email", "text": "Food arrived cold and spoiled"},\n  {"channel": "chat", "text": "Card was charged twice for same ride"}\n]');
  const [jobs, setJobs] = useState([]);
  const [jobLoading, setJobLoading] = useState(false);

  const submitJob = async () => {
    setJobLoading(true);
    try {
      const tickets = JSON.parse(jobInput);
      const res = await fetch(`${API_BASE}/batch/jobs`, { method: 'POST', headers: headers(), body: JSON.stringify({ tickets }) });
      const data = await res.json();
      if (!res.ok && res.status !== 202) throw new Error(data.error?.message || data.detail || `Error ${res.status}`);
      setJobs(prev => [{ ...data, _expanded: false }, ...prev]);
      toast('Job submitted: ' + data.job_id, 'success');
    } catch (e) { toast(e.message, 'error'); }
    finally { setJobLoading(false); }
  };

  const pollJob = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/batch/jobs/${jobId}`, { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || `Error ${res.status}`);
      setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, ...data } : j));
      if (data.status === 'succeeded') toast('Job succeeded!', 'success');
    } catch (e) { toast(e.message, 'error'); }
  };

  const fetchJobResults = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/batch/jobs/${jobId}/results?offset=0&limit=100`, { headers: headers() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error?.message || `Error ${res.status}`);
      setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, _results: data, _expanded: true } : j));
    } catch (e) { toast(e.message, 'error'); }
  };

  const cancelJob = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/batch/jobs/${jobId}`, { method: 'DELETE', headers: headers() });
      if (res.status === 204) {
        setJobs(prev => prev.map(j => j.job_id === jobId ? { ...j, status: 'cancelled' } : j));
        toast('Job cancelled', 'info');
      }
    } catch (e) { toast(e.message, 'error'); }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => toast('Copied to clipboard', 'info'));
  };

  // ---- SETTINGS ----
  const [showKey, setShowKey] = useState(false);
  const [keyInput, setKeyInput] = useState(apiKey);

  // ===== RENDER =====
  return (
    <div className="min-h-screen bg-slate-50 flex" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Mobile hamburger */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-3 left-3 z-50 bg-slate-800 text-white p-2 rounded-lg shadow-lg"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>

      {/* Sidebar */}
      <aside className={`fixed md:sticky top-0 left-0 h-screen w-64 bg-slate-900 text-white flex flex-col z-40 transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-lg">
              TF
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight">TensorForge 2.0</h1>
              <p className="text-[11px] text-slate-400 leading-tight">Ticket Classification System</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(item => (
            <button
              key={item.id}
              onClick={() => { setPage(item.id); setSidebarOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                page === item.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <span className="w-7 h-7 rounded-md bg-slate-800/60 flex items-center justify-center text-xs font-bold">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Sidebar footer: health indicator */}
        <div className="px-4 py-4 border-t border-slate-800">
          <div className="flex items-center gap-2.5">
            <span className={`w-2.5 h-2.5 rounded-full ${health?.status === 'ok' || health?.status === 'healthy' ? 'bg-emerald-400' : health?.status === 'loading' ? 'bg-amber-400' : 'bg-rose-400'}`}></span>
            <span className="text-xs text-slate-400">
              {health?.status === 'ok' || health?.status === 'healthy' ? 'System Online' : health?.status === 'loading' ? 'Loading Model' : 'Offline'}
            </span>
          </div>
          {health?.model_version && (
            <p className="text-[10px] text-slate-500 mt-1 pl-5">Model: {health.model_version}</p>
          )}
        </div>
      </aside>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden" onClick={() => setSidebarOpen(false)}></div>}

      {/* Main Content */}
      <main className="flex-1 min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800 pl-8 md:pl-0">
            {NAV.find(n => n.id === page)?.label || 'Dashboard'}
          </h2>
          <div className="flex items-center gap-3">
            <StatusBadge status={health?.status || 'unknown'} />
            {apiKey ? (
              <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-2 py-1 rounded border border-emerald-200">Key Set</span>
            ) : (
              <span className="text-xs text-amber-600 font-medium bg-amber-50 px-2 py-1 rounded border border-amber-200">No Key</span>
            )}
          </div>
        </header>

        <div className="p-6 lg:p-8 max-w-6xl mx-auto">

          {/* ========== DASHBOARD ========== */}
          {page === 'dashboard' && (
            <div className="space-y-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full ${health?.status === 'ok' || health?.status === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
                    <span className="text-xl font-bold text-slate-800 capitalize">{health?.status === 'ok' ? 'Online' : health?.status || '...'}</span>
                  </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Model Version</p>
                  <p className="mt-2 text-xl font-bold text-slate-800 font-mono">{health?.model_version || 'N/A'}</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Categories</p>
                  <p className="mt-2 text-xl font-bold text-slate-800">11</p>
                </div>
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">API Key</p>
                  <p className="mt-2 text-xl font-bold text-slate-800">{apiKey ? 'Active' : 'Not Set'}</p>
                </div>
              </div>

              {/* Category Routing Reference */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-base font-semibold text-slate-800">Category to Team Routing</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Fixed 11-category mapping enforced by competition contract</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-slate-100">
                  {CATEGORY_MAP.map(item => (
                    <div key={item.category} className="bg-white px-5 py-3.5 flex justify-between items-center">
                      <code className="text-xs text-slate-600 font-mono">{item.category}</code>
                      <span className={`text-xs font-semibold ${item.color}`}>{item.team}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h3 className="text-base font-semibold text-slate-800 mb-4">Quick Actions</h3>
                <div className="flex flex-wrap gap-3">
                  <button onClick={() => setPage('single')} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition">
                    Classify a Ticket
                  </button>
                  <button onClick={() => setPage('batch')} className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg border border-slate-200 transition">
                    Run Batch
                  </button>
                  <button onClick={() => setPage('jobs')} className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg border border-slate-200 transition">
                    Submit Async Job
                  </button>
                  <a href="/docs" target="_blank" rel="noopener" className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium px-4 py-2 rounded-lg border border-slate-200 transition">
                    OpenAPI Docs
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* ========== SINGLE PREDICTION ========== */}
          {page === 'single' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Input */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-base font-semibold text-slate-800">Ticket Input</h3>
                  <p className="text-xs text-slate-500">POST /predict</p>
                </div>
                <form onSubmit={predictSingle} className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Channel</label>
                    <div className="flex gap-2">
                      {['email', 'chat', 'call_transcript'].map(c => (
                        <button
                          key={c}
                          type="button"
                          onClick={() => setChannel(c)}
                          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium border transition ${
                            channel === c
                              ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                              : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          {c.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Ticket Text</label>
                    <textarea
                      value={text}
                      onChange={e => setText(e.target.value)}
                      rows={6}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
                      placeholder="Enter customer support ticket text..."
                    />
                    <p className="text-right text-xs text-slate-400 mt-1">{text.length} characters</p>
                  </div>
                  <button
                    type="submit"
                    disabled={sLoading || !text.trim()}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg disabled:opacity-50 transition flex items-center justify-center gap-2"
                  >
                    {sLoading ? <><Spinner /> Classifying...</> : 'Classify Ticket'}
                  </button>
                </form>
              </div>

              {/* Result */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-base font-semibold text-slate-800">Classification Result</h3>
                </div>
                <div className="p-6">
                  {!sResult ? (
                    <div className="text-center py-16 text-slate-400">
                      <p className="text-4xl mb-3 opacity-30">?</p>
                      <p className="text-sm">Submit a ticket to see results</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Category */}
                      <div className="flex justify-between items-center py-2 border-b border-slate-100">
                        <span className="text-sm text-slate-500">Category</span>
                        <span className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-lg text-sm font-semibold">{sResult.category}</span>
                      </div>
                      {/* Secondary */}
                      <div className="flex justify-between items-center py-2 border-b border-slate-100">
                        <span className="text-sm text-slate-500">Secondary</span>
                        <span className="text-sm font-mono text-slate-600">{sResult.secondary_category || 'null'}</span>
                      </div>
                      {/* Team */}
                      <div className="flex justify-between items-center py-2 border-b border-slate-100">
                        <span className="text-sm text-slate-500">Assigned Team</span>
                        <span className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-lg text-sm font-semibold">{sResult.team}</span>
                      </div>
                      {/* Urgency */}
                      <div className="flex justify-between items-center py-2 border-b border-slate-100">
                        <span className="text-sm text-slate-500">Urgency</span>
                        {sResult.is_urgent ? (
                          <span className="bg-rose-100 text-rose-700 px-3 py-1 rounded-full text-xs font-bold uppercase">Urgent</span>
                        ) : (
                          <span className="bg-slate-100 text-slate-600 px-3 py-1 rounded-full text-xs font-bold uppercase">Normal</span>
                        )}
                      </div>
                      {/* Confidence */}
                      <div className="py-2 border-b border-slate-100">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-sm text-slate-500">Confidence</span>
                          <span className="text-sm font-bold text-slate-800">{(sResult.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div className="w-full bg-slate-200 rounded-full h-2.5">
                          <div className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${sResult.confidence * 100}%` }}></div>
                        </div>
                      </div>
                      {/* Model Version */}
                      <div className="flex justify-between items-center py-2">
                        <span className="text-sm text-slate-500">Model</span>
                        <span className="text-xs font-mono text-slate-400">{sResult.model_version}</span>
                      </div>
                      {/* JSON */}
                      <details className="mt-2">
                        <summary className="text-xs text-indigo-600 cursor-pointer font-medium hover:text-indigo-800">View Raw JSON</summary>
                        <pre className="mt-2 p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-700 overflow-auto max-h-48 border border-slate-200">
                          {JSON.stringify(sResult, null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ========== BATCH PREDICTION ========== */}
          {page === 'batch' && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                  <div>
                    <h3 className="text-base font-semibold text-slate-800">Synchronous Batch (1-100 tickets)</h3>
                    <p className="text-xs text-slate-500">POST /predict/batch</p>
                  </div>
                  <button
                    onClick={predictBatch}
                    disabled={bLoading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2 px-4 rounded-lg disabled:opacity-50 transition flex items-center gap-2"
                  >
                    {bLoading ? <><Spinner /> Processing...</> : 'Run Batch'}
                  </button>
                </div>
                <div className="p-6">
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">Tickets JSON Array</label>
                  <textarea
                    value={batchInput}
                    onChange={e => setBatchInput(e.target.value)}
                    rows={7}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm font-mono bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    placeholder='[{"channel": "email", "text": "..."}]'
                  />
                </div>
              </div>

              {bResults && bResults.results && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <div className="px-6 py-4 border-b border-slate-100">
                    <h3 className="text-base font-semibold text-slate-800">Results ({bResults.results.length} tickets)</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">#</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Category</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Secondary</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Team</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Urgent</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Confidence</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {bResults.results.map((r, i) => (
                          <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50/50'}>
                            <td className="px-6 py-3 text-slate-500 font-mono">{r.ticket_index !== undefined ? r.ticket_index : i}</td>
                            <td className="px-6 py-3">
                              <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-xs font-semibold">{r.category}</span>
                            </td>
                            <td className="px-6 py-3 text-slate-500 font-mono text-xs">{r.secondary_category || 'null'}</td>
                            <td className="px-6 py-3">
                              <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-xs font-semibold">{r.team}</span>
                            </td>
                            <td className="px-6 py-3">
                              {r.is_urgent ? (
                                <span className="text-rose-600 font-bold text-xs">YES</span>
                              ) : (
                                <span className="text-slate-400 text-xs">No</span>
                              )}
                            </td>
                            <td className="px-6 py-3 font-mono font-semibold text-slate-700">{(r.confidence * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <details className="px-6 py-3 border-t border-slate-100">
                    <summary className="text-xs text-indigo-600 cursor-pointer font-medium">View Raw JSON</summary>
                    <pre className="mt-2 p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-700 overflow-auto max-h-48">{JSON.stringify(bResults, null, 2)}</pre>
                  </details>
                </div>
              )}
            </div>
          )}

          {/* ========== ASYNC JOBS ========== */}
          {page === 'jobs' && (
            <div className="space-y-6">
              {/* Submit Form */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                  <div>
                    <h3 className="text-base font-semibold text-slate-800">Submit Async Job (up to 5,000 tickets)</h3>
                    <p className="text-xs text-slate-500">POST /batch/jobs</p>
                  </div>
                  <button
                    onClick={submitJob}
                    disabled={jobLoading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm py-2 px-4 rounded-lg disabled:opacity-50 transition flex items-center gap-2"
                  >
                    {jobLoading ? <><Spinner /> Submitting...</> : 'Submit Job'}
                  </button>
                </div>
                <div className="p-6">
                  <textarea
                    value={jobInput}
                    onChange={e => setJobInput(e.target.value)}
                    rows={5}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm font-mono bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    placeholder='[{"channel": "email", "text": "..."}]'
                  />
                </div>
              </div>

              {/* Job List */}
              {jobs.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Jobs ({jobs.length})</h3>
                  {jobs.map(job => (
                    <div key={job.job_id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                      <div className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <StatusBadge status={job.status} />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm text-slate-700 font-medium">{job.job_id}</span>
                              <button onClick={() => copyToClipboard(job.job_id)} className="text-xs text-slate-400 hover:text-indigo-600">[Copy]</button>
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">
                              {job.processed_tickets !== undefined ? `${job.processed_tickets} / ` : ''}{job.total_tickets} tickets
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button onClick={() => pollJob(job.job_id)} className="text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-200 transition">
                            Refresh
                          </button>
                          {job.status === 'succeeded' && (
                            <button onClick={() => fetchJobResults(job.job_id)} className="text-xs font-medium text-emerald-600 hover:text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 transition">
                              Get Results
                            </button>
                          )}
                          {['pending', 'running'].includes(job.status) && (
                            <button onClick={() => cancelJob(job.job_id)} className="text-xs font-medium text-rose-600 hover:text-rose-800 bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200 transition">
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Progress bar for running jobs */}
                      {['running', 'pending'].includes(job.status) && job.total_tickets && (
                        <div className="px-6 pb-4">
                          <div className="w-full bg-slate-100 rounded-full h-2">
                            <div
                              className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${job.total_tickets ? ((job.processed_tickets || 0) / job.total_tickets) * 100 : 0}%` }}
                            ></div>
                          </div>
                        </div>
                      )}

                      {/* Expanded Results */}
                      {job._expanded && job._results && (
                        <div className="border-t border-slate-100 px-6 py-4">
                          <p className="text-xs text-slate-500 mb-2">
                            Showing {job._results.results?.length || 0} of {job._results.total || '?'} results
                          </p>
                          <pre className="p-3 bg-slate-50 rounded-lg text-xs font-mono text-slate-700 overflow-auto max-h-60 border border-slate-200">
                            {JSON.stringify(job._results, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {jobs.length === 0 && (
                <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
                  <p className="text-sm">No jobs submitted yet. Submit a job above to get started.</p>
                </div>
              )}
            </div>
          )}

          {/* ========== SETTINGS ========== */}
          {page === 'settings' && (
            <div className="max-w-lg space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-base font-semibold text-slate-800">API Key Configuration</h3>
                  <p className="text-xs text-slate-500">Your API key is stored locally in the browser</p>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">API Key (X-API-Key)</label>
                    <div className="relative">
                      <input
                        type={showKey ? 'text' : 'password'}
                        value={keyInput}
                        onChange={e => setKeyInput(e.target.value)}
                        className="w-full border border-slate-300 rounded-lg px-3 py-2.5 pr-16 text-sm font-mono bg-slate-50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                        placeholder="Enter your API key..."
                      />
                      <button
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-700 font-medium px-2 py-1"
                      >
                        {showKey ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={() => { setApiKey(keyInput); localStorage.setItem('tf2_api_key', keyInput); toast('API Key saved successfully', 'success'); }}
                    className="bg-slate-800 hover:bg-slate-900 text-white font-medium py-2.5 px-6 rounded-lg transition"
                  >
                    Save Key
                  </button>
                </div>
              </div>

              {/* System Info */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
                <div className="px-6 py-4 border-b border-slate-100">
                  <h3 className="text-base font-semibold text-slate-800">System Information</h3>
                </div>
                <div className="p-6 space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Health Status</span>
                    <StatusBadge status={health?.status || 'unknown'} />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Model Version</span>
                    <span className="font-mono text-slate-700">{health?.model_version || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">API Base</span>
                    <span className="font-mono text-slate-700">{window.location.origin}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500">API Docs</span>
                    <a href="/docs" target="_blank" rel="noopener" className="text-indigo-600 hover:text-indigo-800 font-medium">
                      Open Swagger UI
                    </a>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Toasts */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </div>
  );
}
