import React, { useState, useEffect, useRef } from 'react';
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
import { api } from './api';

export default function App() {
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

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 3200);
  };

  const isSimBusy =
    activeSim &&
    activeSim.active &&
    ['running', 'await', 'executing', 'verifying'].includes(activeSim.sim.phase);

  // Poll dashboard & active simulation
  const refreshData = async () => {
    try {
      const [dash, sim, incs, kb, scens] = await Promise.all([
        api.getDashboard().catch(() => null),
        api.getActiveSimulation().catch(() => null),
        api.getIncidents().catch(() => []),
        api.getKnowledge().catch(() => []),
        api.getScenarios().catch(() => [])
      ]);

      if (dash) setDashboard(dash);
      if (scens && scens.length) setScenarios(scens);
      if (sim) {
        setActiveSim(sim);

        // Check for phase transitions to alert operator
        if (sim.active && sim.sim) {
          const currentPhase = sim.sim.phase;
          if (prevSimPhaseRef.current !== currentPhase) {
            if (currentPhase === 'await') {
              showToast('Policy Engine passed. Remediation awaits human approval!');
            } else if (currentPhase === 'resolved') {
              showToast('Recovery verified! Incident resolved & archived in Knowledge Base.');
            } else if (currentPhase === 'rejected') {
              showToast('Remediation rejected. Incident escalated to on-call lead.');
            } else if (currentPhase === 'stopped') {
              showToast('Emergency stop executed. Rollback initiated.');
            }
            prevSimPhaseRef.current = currentPhase;
          }
        }
      }
      if (incs) setIncidents(incs);
      if (kb) setKbItems(kb);

      // Refresh graph if on map page
      if (currentPage === 'map') {
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
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, isSimBusy ? 1400 : 4000);
    return () => clearInterval(interval);
  }, [isSimBusy, currentPage]);

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
      showToast('Chaos fault injected! Agents dispatched.');
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
      showToast('Remediation rejected. Incident escalated.');
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

      <div>
        <TopBar
          isSimBusy={isSimBusy}
          onOpenChaos={() => setIsChaosOpen(true)}
        />

        <main id="main">
          {currentPage === 'overview' && (
            <Overview
              dashboard={dashboard}
              onOpenChaos={() => setIsChaosOpen(true)}
              onOpenIncident={handleOpenIncident}
              isSimBusy={isSimBusy}
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
          {toastMessage}
        </div>
      )}
    </div>
  );
}

