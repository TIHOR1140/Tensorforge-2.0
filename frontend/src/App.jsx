import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, RefreshCw, Send, Layers, Server, Trash2, Key } from 'lucide-react';

export default function App() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('API_KEY') || '');
  const [health, setHealth] = useState({ status: 'checking', model_version: null });
  const [activeTab, setActiveTab] = useState('single');

  // Single Predict State
  const [singleForm, setSingleForm] = useState({
    ticket_id: 'TF-001',
    channel: 'chat',
    subject: '',
    text: 'driver is taking wrong turn and car is not stopping i am scared'
  });
  const [singleResult, setSingleResult] = useState(null);
  const [singleLoading, setSingleLoading] = useState(false);
  const [singleError, setSingleError] = useState(null);

  // Batch Predict State
  const [batchJson, setBatchJson] = useState(JSON.stringify([
    { ticket_id: 'TF-B01', channel: 'chat', subject: '', text: 'order is 1 hour late and rider is not answering, refund please' },
    { ticket_id: 'TF-B02', channel: 'chat', subject: '', text: 'කාර් එකේ මගේ බෑග් එක අමතක වුණා' },
    { ticket_id: 'TF-B03', channel: 'email', subject: 'Inquiry', text: 'How do I become a registered driver partner on RideEat?' }
  ], null, 2));
  const [batchResults, setBatchResults] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchError, setBatchError] = useState(null);

  // Async Jobs State
  const [jobInputJson, setJobInputJson] = useState(JSON.stringify([
    { ticket_id: 'TF-J01', channel: 'chat', subject: '', text: 'food arrived completely cold and spoiled' },
    { ticket_id: 'TF-J02', channel: 'chat', subject: '', text: 'card was charged twice for the same ride' }
  ], null, 2));
  const [activeJobId, setActiveJobId] = useState('');
  const [jobStatus, setJobStatus] = useState(null);
  const [jobResults, setJobResults] = useState(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [jobError, setJobError] = useState(null);

  // Health check on mount and interval
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  // Save API key
  const handleApiKeyChange = (e) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem('API_KEY', val);
  };

  const checkHealth = async () => {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      setHealth(data);
    } catch {
      setHealth({ status: 'offline', model_version: null });
    }
  };

  const getHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey.trim()) {
      headers['X-API-Key'] = apiKey.trim();
    }
    return headers;
  };

  // 1. Single Ticket Prediction
  const handleSinglePredict = async (e) => {
    e.preventDefault();
    setSingleLoading(true);
    setSingleError(null);
    setSingleResult(null);

    try {
      const payload = {
        ticket_id: singleForm.ticket_id.trim() || undefined,
        channel: singleForm.channel,
        subject: singleForm.subject.trim() || undefined,
        text: singleForm.text.trim()
      };

      const res = await fetch('/predict', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || `HTTP error ${res.status}`);
      }
      setSingleResult(data);
    } catch (err) {
      setSingleError(err.message);
    } finally {
      setSingleLoading(false);
    }
  };

  // 2. Synchronous Batch Prediction (1-100)
  const handleBatchPredict = async (e) => {
    e.preventDefault();
    setBatchLoading(true);
    setBatchError(null);
    setBatchResults(null);

    try {
      let tickets;
      try {
        tickets = JSON.parse(batchJson);
      } catch {
        throw new Error('Invalid JSON format');
      }

      if (!Array.isArray(tickets)) {
        throw new Error('Batch payload must be a JSON array of tickets');
      }

      const res = await fetch('/predict/batch', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ tickets })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || `HTTP error ${res.status}`);
      }
      setBatchResults(data);
    } catch (err) {
      setBatchError(err.message);
    } finally {
      setBatchLoading(false);
    }
  };

  // 3. Asynchronous Batch Job Submission
  const handleSubmitJob = async (e) => {
    e.preventDefault();
    setJobLoading(true);
    setJobError(null);
    setJobStatus(null);
    setJobResults(null);

    try {
      let tickets;
      try {
        tickets = JSON.parse(jobInputJson);
      } catch {
        throw new Error('Invalid JSON format');
      }

      const res = await fetch('/batch/jobs', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ tickets })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || `HTTP error ${res.status}`);
      }
      setActiveJobId(data.job_id);
      setJobStatus(data);
    } catch (err) {
      setJobError(err.message);
    } finally {
      setJobLoading(false);
    }
  };

  // Poll Job Status
  const handlePollJob = async (jobIdToPoll) => {
    const id = jobIdToPoll || activeJobId;
    if (!id) return;
    setJobLoading(true);
    setJobError(null);

    try {
      const res = await fetch(`/batch/jobs/${id}`, {
        headers: getHeaders()
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error?.message || `HTTP error ${res.status}`);
      }
      setJobStatus(data);

      if (data.status === 'succeeded') {
        fetchJobResults(id);
      }
    } catch (err) {
      setJobError(err.message);
    } finally {
      setJobLoading(false);
    }
  };

  // Fetch Job Results
  const fetchJobResults = async (id) => {
    try {
      const res = await fetch(`/batch/jobs/${id}/results?offset=0&limit=100`, {
        headers: getHeaders()
      });
      const data = await res.json();
      if (res.ok) {
        setJobResults(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Cancel Job
  const handleCancelJob = async () => {
    if (!activeJobId) return;
    try {
      const res = await fetch(`/batch/jobs/${activeJobId}`, {
        method: 'DELETE',
        headers: getHeaders()
      });
      if (res.status === 204) {
        setJobStatus((prev) => prev ? { ...prev, status: 'cancelled' } : null);
      }
    } catch (err) {
      setJobError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">TensorForge 2.0 MVP</h1>
          <p className="text-xs text-slate-400">Customer Support Ticket Classification & Routing</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Health Status Indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            {health.status === 'ok' ? (
              <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <CheckCircle size={14} /> Ready ({health.model_version})
              </span>
            ) : health.status === 'loading' ? (
              <span className="flex items-center gap-1.5 text-amber-400 font-medium">
                <RefreshCw size={14} className="animate-spin" /> Loading
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-red-400 font-medium">
                <AlertCircle size={14} /> Offline
              </span>
            )}
          </div>

          {/* API Key Input */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs gap-2">
            <Key size={14} className="text-slate-400" />
            <input
              type="password"
              placeholder="API_KEY"
              value={apiKey}
              onChange={handleApiKeyChange}
              className="bg-transparent text-slate-200 outline-none w-32 font-mono text-xs placeholder:text-slate-500"
            />
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="border-b border-slate-800 bg-slate-950/60 px-6 flex gap-2 pt-2">
        <button
          onClick={() => setActiveTab('single')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg border-b-2 flex items-center gap-2 transition ${
            activeTab === 'single'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Send size={14} /> Single Ticket (POST /predict)
        </button>
        <button
          onClick={() => setActiveTab('batch')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg border-b-2 flex items-center gap-2 transition ${
            activeTab === 'batch'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers size={14} /> Batch Sync (POST /predict/batch)
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg border-b-2 flex items-center gap-2 transition ${
            activeTab === 'jobs'
              ? 'border-emerald-500 text-emerald-400 bg-slate-900'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Server size={14} /> Async Jobs (POST /batch/jobs)
        </button>
      </div>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">

        {/* TAB 1: SINGLE PREDICTION */}
        {activeTab === 'single' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Form */}
            <form onSubmit={handleSinglePredict} className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Send size={16} className="text-emerald-400" /> Ticket Input
              </h2>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Ticket ID</label>
                  <input
                    type="text"
                    value={singleForm.ticket_id}
                    onChange={(e) => setSingleForm({ ...singleForm, ticket_id: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Channel *</label>
                  <select
                    value={singleForm.channel}
                    onChange={(e) => setSingleForm({ ...singleForm, channel: e.target.value })}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-emerald-500"
                  >
                    <option value="chat">chat</option>
                    <option value="email">email</option>
                    <option value="call_transcript">call_transcript</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Subject (optional)</label>
                <input
                  type="text"
                  placeholder="Subject line for email..."
                  value={singleForm.subject}
                  onChange={(e) => setSingleForm({ ...singleForm, subject: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Ticket Text *</label>
                <textarea
                  rows={5}
                  required
                  placeholder="Ticket text in English, Sinhala, Tamil, Singlish, Tanglish..."
                  value={singleForm.text}
                  onChange={(e) => setSingleForm({ ...singleForm, text: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 outline-none focus:border-emerald-500 font-mono leading-relaxed"
                />
              </div>

              <button
                type="submit"
                disabled={singleLoading}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-xs rounded-lg transition"
              >
                {singleLoading ? 'Classifying...' : 'Predict Ticket'}
              </button>
            </form>

            {/* Prediction Output */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
              <h2 className="text-sm font-bold text-white">Prediction Output</h2>

              {singleError && (
                <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300">
                  {singleError}
                </div>
              )}

              {singleResult ? (
                <div className="space-y-3">
                  <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-2.5 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Primary Category:</span>
                      <span className="font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                        {singleResult.category}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Assigned Team:</span>
                      <span className="font-semibold text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                        {singleResult.team}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Secondary Category:</span>
                      <span className="font-mono text-slate-300">
                        {singleResult.secondary_category ?? 'null'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Urgent:</span>
                      <span className={`px-2 py-0.5 rounded font-bold ${
                        singleResult.is_urgent
                          ? 'bg-red-950 text-red-400 border border-red-800'
                          : 'bg-slate-800 text-slate-400'
                      }`}>
                        {singleResult.is_urgent ? 'YES (URGENT)' : 'NO'}
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Confidence:</span>
                      <span className="font-mono font-bold text-white">
                        {(singleResult.confidence * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Model Version:</span>
                      <span className="font-mono text-slate-400">{singleResult.model_version}</span>
                    </div>
                  </div>

                  <div>
                    <p className="text-[11px] font-medium text-slate-400 mb-1">JSON Response:</p>
                    <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-auto max-h-44">
                      {JSON.stringify(singleResult, null, 2)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div className="py-16 text-center text-xs text-slate-500">
                  Submit a ticket to view classification results.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: SYNCHRONOUS BATCH PREDICTION */}
        {activeTab === 'batch' && (
          <div className="space-y-4">
            <form onSubmit={handleBatchPredict} className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3">
              <div className="flex justify-between items-center">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Layers size={16} className="text-emerald-400" /> Synchronous Batch Input (1 - 100 tickets)
                </h2>
                <button
                  type="submit"
                  disabled={batchLoading}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-xs rounded-lg transition"
                >
                  {batchLoading ? 'Evaluating...' : 'Run Batch Prediction'}
                </button>
              </div>

              <textarea
                rows={7}
                value={batchJson}
                onChange={(e) => setBatchJson(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 outline-none focus:border-emerald-500 font-mono leading-relaxed"
              />
            </form>

            {batchError && (
              <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300">
                {batchError}
              </div>
            )}

            {batchResults && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Predictions ({batchResults.predictions?.length || 0})
                  </h3>
                  {batchResults.meta?.processing_time_ms && (
                    <span className="text-xs font-mono text-emerald-400">
                      {batchResults.meta.processing_time_ms} ms
                    </span>
                  )}
                </div>

                <div className="overflow-x-auto border border-slate-800 rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900 text-slate-400 uppercase text-[10px]">
                      <tr>
                        <th className="p-2.5">Ticket ID</th>
                        <th className="p-2.5">Category</th>
                        <th className="p-2.5">Team</th>
                        <th className="p-2.5">Secondary</th>
                        <th className="p-2.5">Urgent</th>
                        <th className="p-2.5">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 font-mono text-slate-200">
                      {batchResults.predictions?.map((p, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/50">
                          <td className="p-2.5 text-slate-300">{p.ticket_id}</td>
                          <td className="p-2.5 text-emerald-400 font-semibold">{p.category}</td>
                          <td className="p-2.5 text-cyan-300">{p.team}</td>
                          <td className="p-2.5 text-slate-400">{p.secondary_category ?? 'null'}</td>
                          <td className="p-2.5">{p.is_urgent ? <span className="text-red-400 font-bold">YES</span> : 'NO'}</td>
                          <td className="p-2.5 font-bold">{(p.confidence * 100).toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: ASYNC BATCH JOBS */}
        {activeTab === 'jobs' && (
          <div className="space-y-4">
            {/* Submit & Poll Panel */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <form onSubmit={handleSubmitJob} className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Server size={16} className="text-purple-400" /> Submit Evaluation Job (POST /batch/jobs)
                </h2>
                <textarea
                  rows={6}
                  value={jobInputJson}
                  onChange={(e) => setJobInputJson(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 outline-none focus:border-purple-500 font-mono leading-relaxed"
                />
                <button
                  type="submit"
                  disabled={jobLoading}
                  className="w-full py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold text-xs rounded-lg transition"
                >
                  {jobLoading ? 'Submitting...' : 'Submit Asynchronous Job'}
                </button>
              </form>

              {/* Status Poller */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-bold text-white">Poll Job (GET /batch/jobs/{'{job_id}'})</h2>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter Job ID"
                    value={activeJobId}
                    onChange={(e) => setActiveJobId(e.target.value)}
                    className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 outline-none font-mono"
                  />
                  <button
                    onClick={() => handlePollJob()}
                    className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg"
                  >
                    Poll
                  </button>
                </div>

                {jobError && (
                  <div className="p-3 bg-red-950/50 border border-red-800 rounded-lg text-xs text-red-300">
                    {jobError}
                  </div>
                )}

                {jobStatus && (
                  <div className="p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-3 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Status:</span>
                      <span className="font-bold uppercase px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                        {jobStatus.status}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-slate-400 text-[11px]">
                        <span>Progress:</span>
                        <span>{jobStatus.processed} / {jobStatus.total} tickets</span>
                      </div>
                      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-500 transition-all duration-300"
                          style={{
                            width: `${jobStatus.total ? (jobStatus.processed / jobStatus.total) * 100 : 0}%`
                          }}
                        />
                      </div>
                    </div>

                    {jobStatus.status === 'running' || jobStatus.status === 'queued' ? (
                      <button
                        onClick={handleCancelJob}
                        className="w-full py-1.5 bg-red-950/60 hover:bg-red-900/60 text-red-300 rounded border border-red-800/60 text-xs flex items-center justify-center gap-1"
                      >
                        <Trash2 size={12} /> Cancel Job
                      </button>
                    ) : null}
                  </div>
                )}
              </div>
            </div>

            {/* Succeeded Job Results */}
            {jobResults && (
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-5 space-y-3">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                  Job Results ({jobResults.predictions?.length || 0} of {jobResults.total})
                </h3>
                <pre className="p-3 bg-slate-900 rounded-lg border border-slate-800 text-[11px] font-mono text-purple-300 overflow-auto max-h-56">
                  {JSON.stringify(jobResults, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 px-6 py-3 text-center text-xs text-slate-500">
        TensorForge 2.0 • Phase 2 MVP Stage
      </footer>
    </div>
  );
}
