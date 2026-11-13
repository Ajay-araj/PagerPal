import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Navigation } from './components/Navigation';
import { TopBar } from './components/TopBar';
import { Overview } from './components/Overview';
import { IncidentsList } from './components/IncidentsList';
import { IncidentDetail } from './components/IncidentDetail';
import { LiveInvestigation } from './components/LiveInvestigation';
import { ServiceMap } from './components/ServiceMap';
import { KnowledgeBase } from './components/KnowledgeBase';
import { Postmortems } from './components/Postmortems';
import { Settings } from './components/Settings';
import { ChaosModal } from './components/ChaosModal';
import { ParticleBackground } from './components/ParticleBackground';
import { LoadingScreen } from './components/LoadingScreen';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { api } from './api';

export default function App() {
  // Logical loading lifecycle: 'loading' -> 'dashboard-ready'
  const [loadingPhase, setLoadingPhase] = useState(() => {
    try {
      return window.sessionStorage.getItem('pagerpal_dashboard_ready') === 'true'
        ? 'dashboard-ready'
        : 'loading';
    } catch {
      return 'loading';
    }
  });

  const [backendError, setBackendError] = useState(false);
  const [currentPage, setCurrentPage] = useState('overview');
  const [dashboard, setDashboard] = useState(null);
  const [activeSim, setActiveSim] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentDetail, setSelectedIncidentDetail] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [kbItems, setKbItems] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [isChaosOpen, setIsChaosOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const prevSimPhaseRef = useRef(null);

  const showToast = useCallback((msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 3600);
  }, []);

  const handleLoadingComplete = useCallback(() => {
    try {
      window.sessionStorage.setItem('pagerpal_dashboard_ready', 'true');
    } catch {}
    setLoadingPhase('dashboard-ready');
  }, []);

  const isSimBusy =
    activeSim &&
    activeSim.active &&
    ['running', 'await', 'executing', 'verifying'].includes(activeSim.sim.phase);

  // Poll dashboard & active simulation
  const refreshData = useCallback(async () => {
    try {
      const [dash, sim, incs, kb, scens] = await Promise.all([
        api.getDashboard().catch(() => null),
        api.getActiveSimulation().catch(() => null),
        api.getIncidents().catch(() => []),
        api.getKnowledge().catch(() => []),
        api.getScenarios().catch(() => [])
      ]);

      if (dash) {
        setDashboard(dash);
        setBackendError(false);
      } else if (!dashboard) {
        const health = await api.getHealth().catch(() => null);
        if (!health) setBackendError(true);
        else setBackendError(false);
      }
      if (scens && scens.length) setScenarios(scens);
      if (sim) {
        setActiveSim(sim);

        // Check for phase transitions to alert operator
        if (sim.active && sim.sim) {
          const currentPhase = sim.sim.phase;
          if (prevSimPhaseRef.current !== currentPhase) {
            if (currentPhase === 'await') {
              showToast('Policy Engine passed: Remediation awaits human approval!');
            } else if (currentPhase === 'resolved') {
              showToast('Recovery verified! Incident resolved & archived in Knowledge Base.');
            } else if (currentPhase === 'rejected') {
              showToast('Remediation rejected: Incident escalated to on-call lead.');
            } else if (currentPhase === 'stopped') {
              showToast('Emergency stop executed: Rollback initiated.');
            }
            prevSimPhaseRef.current = currentPhase;
          }
        }
      }
      if (incs) setIncidents(incs);
      if (kb) setKbItems(kb);

      // Refresh graph if on map or overview page
      if (currentPage === 'map' || currentPage === 'overview') {
        const activeId = sim && sim.active ? sim.sim.id : 'INC-2037';
        const g = await api.getIncidentGraph(activeId).catch(() => null);
        if (g) setGraphData(g);
      }

      // Refresh detail if on detail page
      if (currentPage === 'detail' && selectedIncidentDetail) {
        const det = await api.getIncidentDetail(selectedIncidentDetail.incident.id).catch(() => null);
        if (det) setSelectedIncidentDetail(det);
      }
    } catch (e) {
      console.warn('Refresh error:', e);
    }
  }, [currentPage, isSimBusy, selectedIncidentDetail, showToast]);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, isSimBusy ? 1400 : 4000);
    return () => clearInterval(interval);
  }, [refreshData, isSimBusy]);

  const handleOpenIncident = async (id, isLive) => {
    if (isLive) {
      setCurrentPage('live');
      return;
    }
    try {
      const detail = await api.getIncidentDetail(id);
      setSelectedIncidentDetail(detail);
      setCurrentPage('detail');
    } catch (e) {
      showToast('Could not load incident details: ' + e.message);
    }
  };

  const handleStartSimulation = async (scenarioId) => {
    try {
      const res = await api.startSimulation(scenarioId);
      setActiveSim(res);
      showToast('Chaos fault injected: Autonomous agents dispatched.');
      setCurrentPage('live');
      refreshData();
    } catch (e) {
      showToast('Failed to start simulation: ' + e.message);
    }
  };

  const handleApprove = async () => {
    if (!activeSim || !activeSim.active) return;
    try {
      const res = await api.approveIncident(activeSim.sim.id, 'Operator (Human)');
      setActiveSim(res);
      showToast('Remediation approved! Autonomous execution in progress.');
      refreshData();
    } catch (e) {
      showToast('Approval error: ' + e.message);
    }
  };

  const handleReject = async (reason) => {
    if (!activeSim || !activeSim.active) return;
    try {
      const res = await api.rejectIncident(activeSim.sim.id, 'Operator (Human)', reason);
      setActiveSim(res);
      showToast('Remediation rejected: Incident escalated.');
      refreshData();
    } catch (e) {
      showToast('Rejection error: ' + e.message);
    }
  };

  const handleEmergencyStop = async () => {
    if (!activeSim || !activeSim.active) return;
    try {
      const res = await api.emergencyStop(activeSim.sim.id, 'Operator (Human)');
      setActiveSim(res);
      showToast('Emergency stop engaged! Rollback triggered.');
      refreshData();
    } catch (e) {
      showToast('Emergency stop error: ' + e.message);
    }
  };

  return (
    <div className="app">
      {/* Exactly Two-Cycle Loading Screen */}
      {loadingPhase !== 'dashboard-ready' && (
        <LoadingScreen onComplete={handleLoadingComplete} />
      )}

      {/* Ambient Particle Background */}
      <ParticleBackground />

      {/* Left Navigation Bar */}
      <Navigation
        currentPage={currentPage}
        onNavigate={(page) => {
          if (page === 'map') {
            const activeId = activeSim && activeSim.active ? activeSim.sim.id : 'INC-2037';
            api.getIncidentGraph(activeId).then((g) => setGraphData(g)).catch(() => {});
          }
          setCurrentPage(page);
          window.scrollTo(0, 0);
        }}
        isSimBusy={isSimBusy}
      />

      {/* Main Layout Area */}
      <div style={{ position: 'relative', zIndex: 1, minWidth: 0 }}>
        <TopBar
          isSimBusy={isSimBusy}
          onOpenChaos={() => setIsChaosOpen(true)}
        />

        {/* Backend Connection Warning & Recovery Banner */}
        {backendError && (
          <div style={{
            background: 'rgba(255, 170, 54, 0.12)',
            borderBottom: '1px solid var(--amber)',
            padding: '10px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '13px',
            color: '#ffeaad',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={15} style={{ color: 'var(--amber)', flexShrink: 0 }} />
              <span>
                <b>Backend Connecting:</b> Unable to reach API endpoint ({import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}). Cloud instances (Render) may take ~30s on cold start.
              </span>
            </div>
            <button className="btn" onClick={() => refreshData()} style={{ padding: '4px 12px', fontSize: '12px', flexShrink: 0 }}>
              <RefreshCw size={12} /> Retry Now
            </button>
          </div>
        )}

        <main id="main">
          {currentPage === 'overview' && (
            <Overview
              dashboard={dashboard}
              onOpenChaos={() => setIsChaosOpen(true)}
              onOpenIncident={handleOpenIncident}
              isSimBusy={isSimBusy}
              activeSim={activeSim}
              onNavigate={setCurrentPage}
            />
          )}

          {currentPage === 'incidents' && (
            <IncidentsList
              incidents={incidents}
              onOpenIncident={handleOpenIncident}
              onOpenChaos={() => setIsChaosOpen(true)}
            />
          )}

          {currentPage === 'detail' && (
            <IncidentDetail
              detail={selectedIncidentDetail}
              onBack={() => setCurrentPage('incidents')}
              onApprove={handleApprove}
              onReject={handleReject}
              onEmergencyStop={handleEmergencyStop}
              isLive={isSimBusy}
            />
          )}

          {currentPage === 'live' && (
            <LiveInvestigation
              simData={activeSim}
              onOpenChaos={() => setIsChaosOpen(true)}
              onOpenApproval={() => {
                if (activeSim && activeSim.active) {
                  handleOpenIncident(activeSim.sim.id, false);
                }
              }}
            />
          )}

          {currentPage === 'map' && (
            <ServiceMap
              graphData={graphData}
              activeSim={activeSim}
            />
          )}

          {currentPage === 'kb' && (
            <KnowledgeBase
              items={kbItems}
            />
          )}

          {currentPage === 'reports' && (
            <Postmortems
              activeSim={activeSim}
              onToast={showToast}
            />
          )}

          {currentPage === 'settings' && (
            <Settings
              onToast={showToast}
            />
          )}
        </main>
      </div>

      {/* Chaos Mode Modal */}
      {isChaosOpen && (
        <ChaosModal
          onClose={() => setIsChaosOpen(false)}
          onConfirmRun={handleStartSimulation}
          isSimBusy={isSimBusy}
          scenarios={scenarios}
        />
      )}

      {/* Floating Notification Toast */}
      {toastMessage && (
        <div className="toast" role="status">
          <span style={{ color: 'var(--cyan)' }}>✦</span>
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
