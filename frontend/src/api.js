const BASE_URL = '';

async function request(url, options = {}) {
  try {
    const res = await fetch(`${BASE_URL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Network request failed');
    }
    return await res.json();
  } catch (e) {
    console.warn(`API call failed for ${url}:`, e.message);
    throw e;
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

