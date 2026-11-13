const RAW_BASE = import.meta.env.VITE_API_BASE_URL || '';
const BASE_URL = RAW_BASE.endsWith('/') ? RAW_BASE.slice(0, -1) : RAW_BASE;

async function request(url, options = {}, timeoutMs = 6000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE_URL}${url}`, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return await res.json();
  } catch (e) {
    clearTimeout(timeoutId);
    const msg = e.name === 'AbortError' ? `Request timeout after ${timeoutMs}ms` : e.message;
    console.warn(`API call failed for ${url}:`, msg);
    throw new Error(msg);
  }
}

export const api = {
  getHealth: () => request('/health'),
  getDashboard: () => request('/api/dashboard'),
  getScenarios: () => request('/api/scenarios'),
  startSimulation: (scenario_id) => request('/api/simulations', {
    method: 'POST',
    body: JSON.stringify({ scenario_id })
  }),
  getActiveSimulation: () => request('/api/simulations/active'),
  getSimulation: (id) => request(`/api/simulations/${id}`),
  getIncidents: (params = {}) => {
    const sp = new URLSearchParams();
    if (params.q) sp.append('q', params.q);
    if (params.severity) sp.append('severity', params.severity);
    if (params.status) sp.append('status', params.status);
    const qs = sp.toString();
    return request(`/api/incidents${qs ? `?${qs}` : ''}`);
  },
  getIncidentDetail: (id) => request(`/api/incidents/${id}`),
  getIncidentGraph: (id) => request(`/api/incidents/${id}/graph`),
  approveIncident: (id, reviewer = 'Operator (Human)') => request(`/api/incidents/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ reviewer })
  }),
  rejectIncident: (id, reviewer = 'Operator (Human)', reason = 'Rejected by operator') => request(`/api/incidents/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reviewer, reason })
  }),
  emergencyStop: (id, actor = 'Operator (Human)') => request(`/api/incidents/${id}/stop`, {
    method: 'POST',
    body: JSON.stringify({ actor })
  }),
  getPostmortem: (id) => request(`/api/incidents/${id}/postmortem`),
  getKnowledge: (q = '') => request(`/api/knowledge${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  getSettings: () => request('/api/settings'),
  updateSettings: (payload) => request('/api/settings', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),
  runEvaluationSuite: () => request('/api/evaluate', { method: 'POST' })
};
