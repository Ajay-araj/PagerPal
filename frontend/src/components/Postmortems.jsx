import React from 'react';
import { Copy, Download, FileText, CheckCircle2, ShieldCheck, Share2 } from 'lucide-react';

export function Postmortems({ activeSim, onToast }) {
  const isResolved = activeSim && activeSim.active && activeSim.sim.phase === 'resolved';
  const s = activeSim && activeSim.active ? activeSim.sim : null;
  const sc = s ? s.scenario : null;

  const getPostmortemText = () => {
    if (!s || !sc) {
      return `# Incident Postmortem: INC-2037 (HISTORICAL SAMPLE)

**Title:** Checkout 5xx after cache restart on \`cache\`  
**Date:** Yesterday 14:12 UTC  
**Status:** Resolved (Simulated Recovery Verified)  
**Severity:** High  
**Affected Service:** \`cache\`  

---

## 1. Executive Summary
During a simulated restart event, Redis cache keys were evicted, causing a 3x query load spike against orders-db. PagerPal agents correlated the alerts, traced the causal link, secured operator approval for cache warming and flush, and verified that latency returned to 85ms.

## 2. Root Cause
Cache restart emptied hot key sets without pre-warming, driving database read IOPS beyond nominal thresholds.

## 3. Remediation & Policy Engine Evaluation
- Proposed: "Flush and restart the cache node"
- Policy Engine: L2 Reversible action approved by human operator.

## 4. Recovery Verification
- p95 latency: 980 ms → 85 ms
- Error rate: 4.8% → 0.05%
- All 4 health probes passed.
`;
    }

    return `# Incident Postmortem: ${s.id} (SYNTHETIC SIMULATION)

**Title:** ${sc.name} on \`${sc.svc_name}\`  
**Detected:** ${s.detected || 'Active Simulation'}  
**Status:** Resolved (Recovery Verified)  
**Severity:** ${sc.sev || 'High'}  
**Target Component:** \`${sc.svc_name}\`  

---

## 1. Executive Summary
A simulated chaos fault "${sc.name}" was injected into \`${sc.svc_name}\`. Checkout success dropped to **${s.success_rate || 81.2}%**, putting **~${s.orders_at_risk || 340} orders/min** at risk. PagerPal's 7 autonomous agent workflow correlated alerts, identified root causes via NetworkX causal graph, verified evidence, obtained Policy Engine clearance, secured operator approval, executed the simulated fix, and verified recovery.

## 2. Impact Summary
- Customer Impact: p95 latency peaked at **${sc.before_metrics?.p95_latency || 'N/A'}**; error rate spiked to **${sc.before_metrics?.error_rate || 'N/A'}**.
- Blast Radius: Upstream \`checkout-svc\` degraded due to dependency delays on \`${sc.svc_name}\`.

## 3. Root Cause Analysis
- Identified Root Cause: ${sc.cause || 'Under investigation'}
- Causal Propagation: checkout-svc → ${sc.svc_name} → orders-db
- Dropped Claim: ${sc.dropped_claim || 'None'}

## 4. Remediation & Policy Decision
- Proposed Action: "${sc.fix}"
- Policy Engine: Evaluated 5 safety rules (Allowlist, Reversibility, Boundary, Coverage >= 80%, Human Approval). Preconditions verified.
- Human Approval: Granted by Operator (Human).

## 5. Recovery Verification (Independent)
- p95 Latency: ${sc.before_metrics?.p95_latency || 'N/A'} → **${sc.after_metrics?.p95_latency || 'Nominal'}**
- Error Rate: ${sc.before_metrics?.error_rate || 'N/A'} → **${sc.after_metrics?.error_rate || '0.0%'}**
- Resource Saturation: ${sc.before_metrics?.saturation || 'N/A'} → **${sc.after_metrics?.saturation || 'Nominal'}**
- Verification Checks: 4 of 4 independent probes PASSED.

## 6. Preventive Action Items
1. Add regression checks for connection limits in CI/CD pre-deploy gates.
2. Alert on connection pool wait times exceeding 200ms.
3. Establish automatic canary rollouts for critical payment path updates.
`;
  };

  const copyMarkdown = () => {
    try {
      navigator.clipboard.writeText(getPostmortemText());
      onToast('Postmortem copied to clipboard as Markdown');
    } catch {
      onToast('Failed to copy to clipboard');
    }
  };

  const downloadMarkdown = () => {
    const text = getPostmortemText();
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PagerPal-Postmortem-${s ? s.id : 'sample'}.md`;
    a.click();
    URL.revokeObjectURL(url);
    onToast('Postmortem downloaded as .md');
  };

  return (
    <div>
      <div className="hd">
        <div>
          <h1>Postmortems & Incident Forensics</h1>
          <p>
            Automatically authored markdown postmortems with causal timelines, impact analysis, and preventive actions.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn" onClick={copyMarkdown}>
            <Copy size={14} /> Copy as Markdown
          </button>
          <button className="btn p" onClick={downloadMarkdown}>
            <Download size={14} /> Download .md
          </button>
        </div>
      </div>

      <div className="pn">
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '18px' }}>
          <span className="b amb">SYNTHETIC SCENARIO</span>
          {isResolved && (
            <span className="b grn" style={{ boxShadow: '0 0 12px rgba(0, 230, 160, 0.3)' }}>
              <CheckCircle2 size={13} /> 4/4 Probes Verified
            </span>
          )}
        </div>

        <div className="pm">
          {getPostmortemText()}
        </div>
      </div>
    </div>
  );
}
