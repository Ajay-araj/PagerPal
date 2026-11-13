from typing import List, Dict, Any

from backend.schemas import VerificationReport, ConfidenceReport, SimulationRun

class ConfidenceScorer:
    def calculate(self, report: VerificationReport, run: SimulationRun) -> ConfidenceReport:
        rules: List[str] = []

        # 1. Evidence Coverage across 4 pillars: logs, metrics, traces, deployments
        pillars_present = 0
        if run.logs:
            pillars_present += 1
            rules.append("Pillar: Logs available (+25% data quality)")
        if run.metrics:
            pillars_present += 1
            rules.append("Pillar: Metric time series available (+25% data quality)")
        if run.traces:
            pillars_present += 1
            rules.append("Pillar: Distributed trace spans available (+25% data quality)")
        if run.deployments:
            pillars_present += 1
            rules.append("Pillar: Deployment revision history available (+25% data quality)")

        data_quality_pct = round((pillars_present / 4.0) * 100.0, 1)

        # 2. Claim-level Evidence Coverage
        evidence_coverage_pct = report.evidence_coverage_pct
        rules.append(
            f"Coverage: {report.verified_count + report.conflicting_count} of {report.total_claims} claims "
            f"corroborated by telemetry ({evidence_coverage_pct:.1f}%)"
        )

        # 3. Source Agreement & Conflict Penalty
        # Base diagnostic score starts from verified proportion
        support_ratio = (report.verified_count / max(1, report.total_claims))
        base_confidence = support_ratio * 92.0

        # Conflict penalty: each conflicting claim deducts 6.5% from diagnostic confidence
        conflict_penalty = report.conflicting_count * 6.5
        if report.conflicting_count > 0:
            rules.append(f"Conflict Penalty: -{conflict_penalty:.1f}% for {report.conflicting_count} contradictory claim(s)")

        # Dropped claims penalty: each dropped claim deducts 4.0%
        dropped_penalty = report.dropped_count * 4.0
        if report.dropped_count > 0:
            rules.append(f"Dropped Claims Penalty: -{dropped_penalty:.1f}% for {report.dropped_count} unverified claim(s)")

        diagnostic_confidence_pct = max(10.0, min(98.0, round(base_confidence - conflict_penalty - dropped_penalty + (data_quality_pct * 0.1), 1)))
        rules.append(f"Result: Final diagnostic confidence computed at {diagnostic_confidence_pct:.1f}%")

        # 4. Gating decision: Coverage >= 80% and Confidence >= 75% required for L2 remediation
        blocks_l2 = (evidence_coverage_pct < 80.0) or (diagnostic_confidence_pct < 75.0)
        if blocks_l2:
            rules.append("Gating Rule: Low confidence (<75%) or coverage (<80%) BLOCKS Level 2 remediation")
        else:
            rules.append("Gating Rule: Evidence threshold satisfied (Coverage >= 80% and Confidence >= 75%)")

        return ConfidenceReport(
            diagnostic_confidence_pct=diagnostic_confidence_pct,
            evidence_coverage_pct=evidence_coverage_pct,
            data_quality_pct=data_quality_pct,
            conflict_penalty_pct=conflict_penalty,
            supporting_evidence_count=report.verified_count,
            conflicting_evidence_count=report.conflicting_count,
            blocks_l2=blocks_l2,
            rule_breakdown=rules
        )

confidence_scorer = ConfidenceScorer()
