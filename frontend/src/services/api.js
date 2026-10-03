/**
 * API client service for TensorForge 2.0 RideEat Support Platform
 */

const BASE_URL = window.location.origin;

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  return res.json();
}

export async function predictSingle(ticket, apiKey = "") {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;

  const t0 = performance.now();
  const res = await fetch(`${BASE_URL}/predict`, {
    method: "POST",
    headers,
    body: JSON.stringify(ticket),
  });
  const latency = Math.round(performance.now() - t0);
  const data = await res.json();
  return { ok: res.ok, status: res.status, data, latency };
}

export async function predictBatch(tickets, apiKey = "") {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;

  const t0 = performance.now();
  const res = await fetch(`${BASE_URL}/predict/batch`, {
    method: "POST",
    headers,
    body: JSON.stringify({ tickets }),
  });
  const latency = Math.round(performance.now() - t0);
  const data = await res.json();
  return { ok: res.ok, status: res.status, data, latency };
}

export async function submitBatchJob(tickets, apiKey = "", idempotencyKey = "") {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const res = await fetch(`${BASE_URL}/batch/jobs`, {
    method: "POST",
    headers,
    body: JSON.stringify({ tickets }),
  });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function getJobStatus(jobId, apiKey = "") {
  const headers = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await fetch(`${BASE_URL}/batch/jobs/${jobId}`, { headers });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function getJobResults(jobId, apiKey = "", offset = 0, limit = 100) {
  const headers = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await fetch(`${BASE_URL}/batch/jobs/${jobId}/results?offset=${offset}&limit=${limit}`, { headers });
  const data = await res.json();
  return { ok: res.ok, status: res.status, data };
}

export async function cancelJob(jobId, apiKey = "") {
  const headers = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await fetch(`${BASE_URL}/batch/jobs/${jobId}`, {
    method: "DELETE",
    headers,
  });
  return { ok: res.ok, status: res.status };
}
