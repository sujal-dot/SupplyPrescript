import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Info,
  X,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import CommandCenterHeader from '../components/dashboard/CommandCenterHeader';
import ShipmentRiskBanner from '../components/dashboard/ShipmentRiskBanner';
import RiskMetrics from '../components/dashboard/RiskMetrics';
import ShipmentSummary from '../components/dashboard/ShipmentSummary';
import RecommendationCards from '../components/dashboard/RecommendationCards';
import CostComparison from '../components/dashboard/CostComparison';
import ConstraintStatus from '../components/dashboard/ConstraintStatus';
import RecommendationExplanation from '../components/dashboard/RecommendationExplanation';
import DecisionHistory from '../components/dashboard/DecisionHistory';
import ShipmentRiskTable from '../components/dashboard/ShipmentRiskTable';
import {
  DashboardLoadingState,
  DashboardErrorState,
  DashboardEmptyState,
} from '../components/dashboard/DashboardStates';
import RecommendationDetailsModal from '../components/dashboard/RecommendationDetailsModal';
import ExecuteDecisionModal from '../components/dashboard/ExecuteDecisionModal';
import ProposeDecisionModal from '../components/dashboard/ProposeDecisionModal';
import {
  optimizeShipment,
  proposeDecision,
  getDashboardMetrics,
  getShipments,
} from '../services/optimizationService';
import {
  executeDecision,
  getDecisions,
} from '../services/decisionService';

export default function CommandCenter() {
  // Telemetry & Data State
  const [metrics, setMetrics] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [scenarioId, setScenarioId] = useState('baseline');
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Loading & Error States
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [loadingOptimization, setLoadingOptimization] = useState(false);
  const [error, setError] = useState(null);

  // Modals & User Action States
  const [detailsModalOption, setDetailsModalOption] = useState(null);
  const [proposeModalOption, setProposeModalOption] = useState(null);
  const [executeModalOption, setExecuteModalOption] = useState(null);
  const [executingDecision, setExecutingDecision] = useState(false);
  const [executeError, setExecuteError] = useState(null);
  const [submittingProposal, setSubmittingProposal] = useState(false);
  const [proposedDecisionsByShipment, setProposedDecisionsByShipment] = useState({});
  const [executedDecisionsByShipment, setExecutedDecisionsByShipment] = useState({});
  const [toastMessage, setToastMessage] = useState(null);

  // Decision Execution History State
  const [decisionHistory, setDecisionHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [showAllHistory, setShowAllHistory] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLimit, setHistoryLimit] = useState(10);
  const [historyTotal, setHistoryTotal] = useState(0);

  // Load Decision History from PostgreSQL
  const loadDecisionHistory = useCallback(async (
    shipmentId = selectedShipment?.shipment_id,
    showAll = showAllHistory,
    page = historyPage,
    limit = historyLimit
  ) => {
    setLoadingHistory(true);
    try {
      const params = {};
      if (!showAll && shipmentId) {
        params.shipment_id = shipmentId;
      }
      params.limit = limit;
      params.offset = (page - 1) * limit;
      const data = await getDecisions(params);
      const list = data?.items || data?.decisions || [];
      setDecisionHistory(list);
      setHistoryTotal(data?.total ?? list.length);

      // Cache latest executed decision per shipment
      const map = {};
      list.forEach((dec) => {
        if (dec.shipment_id && !map[dec.shipment_id]) {
          map[dec.shipment_id] = dec;
        }
      });
      setExecutedDecisionsByShipment((prev) => ({ ...prev, ...map }));
    } catch (err) {
      console.warn('Unable to load decision execution history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, [selectedShipment?.shipment_id, showAllHistory, historyPage, historyLimit]);

  // 1. Initial Load: Fetch metrics, shipments, & decision history
  const loadInitialData = useCallback(async () => {
    setLoadingInitial(true);
    setError(null);
    try {
      const [metricsData, shipmentsData] = await Promise.all([
        getDashboardMetrics().catch(() => null),
        getShipments({ limit: 50 }).catch(() => ({ shipments: [] })),
      ]);

      setMetrics(metricsData);
      const shipList = shipmentsData?.shipments || [];
      setShipments(shipList);

      // Auto-select highest risk shipment or default
      const highRisk =
        shipList.find((s) => s.risk_level === 'HIGH' || Number(s.delay_probability) >= 0.7) ||
        shipList.find((s) => s.shipment_id === 'SHIP000005') ||
        shipList[0];

      if (highRisk) {
        setSelectedShipment(highRisk);
      }

      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
      setLoadingInitial(false);

      if (highRisk) {
        // Automatically optimize selected shipment
        await Promise.all([
          runOptimization(highRisk.shipment_id, 'baseline'),
          loadDecisionHistory(highRisk.shipment_id, false),
        ]);
      }
    } catch (err) {
      console.error('Failed to load initial Command Center data:', err);
      setError('Unable to load operational shipment data from PostgreSQL.');
      setLoadingInitial(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // 2. Prescriptive Optimization Execution
  const runOptimization = async (shipmentId, scenario = scenarioId) => {
    if (!shipmentId) return;
    setLoadingOptimization(true);
    setError(null);
    try {
      const result = await optimizeShipment({
        shipment_id: shipmentId,
        scenario_id: scenario,
        num_options: 3,
      });
      setOptimizationResult(result);
      setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    } catch (err) {
      console.error('Optimization error:', err);
      const errMsg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err.message ||
        'Prescriptive optimization failed for target shipment.';
      setError(typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
      setOptimizationResult(null);
    } finally {
      setLoadingOptimization(false);
    }
  };

  // 3. User selects another shipment to inspect & optimize
  const handleSelectShipment = (shipment) => {
    setSelectedShipment(shipment);
    runOptimization(shipment.shipment_id, scenarioId);
    loadDecisionHistory(shipment.shipment_id, showAllHistory);
  };

  // 4. Scenario Change Handler
  const handleScenarioChange = (newScenario) => {
    setScenarioId(newScenario);
    if (selectedShipment) {
      runOptimization(selectedShipment.shipment_id, newScenario);
    }
  };

  // 5. Execute Decision Confirmation Workflow (Day 17 - Authoritative Server Enforcement)
  const handleConfirmExecution = async (decisionPayload) => {
    setExecutingDecision(true);
    setExecuteError(null);
    try {
      const response = await executeDecision(decisionPayload);
      const shipId = response.shipment_id || decisionPayload.shipment_id;

      setExecutedDecisionsByShipment((prev) => ({
        ...prev,
        [shipId]: response,
      }));

      setToastMessage({
        type: 'success',
        title: 'Decision Recorded Successfully',
        text: `Option ${response.option_id} (${response.strategy}) authorized as RECORDED for shipment ${shipId}. External status: ${response.external_action_status} (no external bookings made).`,
      });

      setExecuteModalOption(null);
      await loadDecisionHistory(selectedShipment?.shipment_id, showAllHistory);
    } catch (err) {
      console.error('Decision execution failed:', err);
      const errMsg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Decision execution rejected by constraint validation.';
      setExecuteError(typeof errMsg === 'string' ? errMsg : JSON.stringify(errMsg));
      setToastMessage({
        type: 'error',
        title: 'Execution Blocked',
        text: typeof errMsg === 'string' ? errMsg : 'Constraint violation or execution rejection.',
      });
    } finally {
      setExecutingDecision(false);
    }
  };

  // 6. Legacy Propose Action (Safe Fallback)
  const handleSubmitProposal = async (proposalPayload) => {
    setSubmittingProposal(true);
    try {
      const response = await proposeDecision(proposalPayload);
      const shipId = proposalPayload.shipment_id;

      setProposedDecisionsByShipment((prev) => ({
        ...prev,
        [shipId]: {
          option_id: proposalPayload.option_id,
          decision_id: response.decision_id,
          status: response.status || 'Pending',
          recorded_at: response.recorded_at,
        },
      }));

      setToastMessage({
        type: 'success',
        title: 'Decision Proposal Recorded',
        text: `Option ${proposalPayload.option_id} proposed successfully for ${shipId}. Status set to PENDING for managerial review.`,
      });

      setProposeModalOption(null);
    } catch (err) {
      console.error('Failed to propose decision:', err);
      setToastMessage({
        type: 'error',
        title: 'Proposal Failed',
        text: err?.response?.data?.detail || 'Failed to record decision proposal in database.',
      });
    } finally {
      setSubmittingProposal(false);
    }
  };

  // Resolved Alternatives from Optimization Result
  const alternatives =
    optimizationResult?.options ||
    optimizationResult?.alternatives ||
    [];
  const recommendedOptionId =
    optimizationResult?.recommended_option_id ||
    alternatives.find((a) => a.is_recommended)?.option_id ||
    null;
  const recommendedOption =
    alternatives.find((a) => a.option_id === recommendedOptionId) ||
    alternatives[0] ||
    null;
  const baselineData =
    optimizationResult?.baseline ||
    selectedShipment;
  const constraintChecks =
    optimizationResult?.constraint_checks ||
    [];
  const recommendationReason =
    optimizationResult?.recommendation_reason ||
    '';
  const tradeOffAnalysis =
    optimizationResult?.trade_off_analysis ||
    '';

  const currentExecutedDecision = selectedShipment
    ? executedDecisionsByShipment[selectedShipment.shipment_id] || null
    : null;
  const currentProposedDecision = selectedShipment
    ? proposedDecisionsByShipment[selectedShipment.shipment_id] || null
    : null;

  return (
    <div className="space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Toast Notification Alert */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className={`p-4 rounded-2xl flex items-center justify-between border shadow-lg ${
            toastMessage.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200 shadow-emerald-950/20'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-200 shadow-rose-950/20'
          }`}
        >
          <div className="flex items-center space-x-3">
            {toastMessage.type === 'success' ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
            )}
            <div>
              <strong className="font-bold text-sm block">{toastMessage.title}</strong>
              <span className="text-xs text-slate-300">{toastMessage.text}</span>
            </div>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            aria-label="Dismiss message"
            className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 1. Command Center Header */}
      <CommandCenterHeader
        lastUpdated={lastUpdated}
        loading={loadingOptimization || loadingInitial}
        onRefresh={() => {
          if (selectedShipment) {
            runOptimization(selectedShipment.shipment_id, scenarioId);
            loadDecisionHistory(selectedShipment.shipment_id, showAllHistory);
          } else {
            loadInitialData();
          }
        }}
        scenarioId={scenarioId}
        onScenarioChange={handleScenarioChange}
      />

      {/* 2. Key Supply-Chain Risk Metrics (5 Cards) */}
      <RiskMetrics metrics={metrics} loading={loadingInitial} />

      {/* 3. High-Risk Shipment Flagged Banner */}
      <ShipmentRiskBanner
        shipment={selectedShipment}
        loading={loadingInitial}
        onEvaluateAlternatives={(shipId) => runOptimization(shipId, scenarioId)}
      />

      {/* 4. Active Target Shipment Operational Summary */}
      {selectedShipment && (
        <ShipmentSummary
          baseline={baselineData}
          shipment={selectedShipment}
        />
      )}

      {/* 5. Optimization & Recommendation Section */}
      {loadingOptimization ? (
        <DashboardLoadingState message="Evaluating mixed-integer prescriptive alternatives..." />
      ) : error ? (
        <DashboardErrorState
          title="Optimization Evaluation Failed"
          message={error}
          onRetry={() => {
            if (selectedShipment) {
              runOptimization(selectedShipment.shipment_id, scenarioId);
            } else {
              loadInitialData();
            }
          }}
        />
      ) : alternatives.length > 0 ? (
        <div className="space-y-6">
          {/* Section Heading */}
          <div className="flex items-center justify-between pt-2">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight flex items-center space-x-2">
                <Sparkles className="h-5 w-5 text-cyan-400" />
                <span>Prescriptive Decision Alternatives</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Mathematical solver results comparing Option A, Option B, and Option C
              </p>
            </div>
            {scenarioId !== 'baseline' && (
              <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 font-bold">
                Scenario: {scenarioId}
              </span>
            )}
          </div>

          {/* 3 Decision Alternative Cards */}
          <RecommendationCards
            alternatives={alternatives}
            baseline={baselineData}
            recommendedOptionId={recommendedOptionId}
            onViewDetails={(opt) => setDetailsModalOption(opt)}
            onSelectOption={(opt) => setExecuteModalOption(opt)}
            onExecuteDecision={(opt) => setExecuteModalOption(opt)}
            executedDecision={currentExecutedDecision}
            proposedDecision={currentProposedDecision}
            loading={loadingOptimization}
          />

          {/* Itemized Cost Matrix */}
          <CostComparison
            baseline={baselineData}
            alternatives={alternatives}
            recommendedOptionId={recommendedOptionId}
          />

          {/* Hard Business Constraint Verification Status */}
          <ConstraintStatus
            constraintChecks={constraintChecks}
            selectedOption={recommendedOption}
            baseline={baselineData}
          />

          {/* Mathematical Objective Score Rationale & Trade-Off Analysis */}
          <RecommendationExplanation
            recommendedOption={recommendedOption}
            baseline={baselineData}
            reason={recommendationReason}
            tradeOffs={tradeOffAnalysis}
          />
        </div>
      ) : (
        <DashboardEmptyState
          title="No Optimization Evaluated"
          message="Select a shipment below to generate prescriptive alternatives and audit business constraints."
          onAction={() => {
            if (shipments.length > 0) {
              handleSelectShipment(shipments[0]);
            }
          }}
          actionLabel="Optimize First Shipment"
        />
      )}

      {/* 6. Decision Execution Audit Trail (PostgreSQL Ledger) */}
      <DecisionHistory
        decisions={decisionHistory}
        loading={loadingHistory}
        onRefresh={() => loadDecisionHistory(selectedShipment?.shipment_id, showAllHistory, historyPage, historyLimit)}
        activeShipmentId={selectedShipment?.shipment_id}
        showAllShipments={showAllHistory}
        onToggleShowAll={() => {
          const next = !showAllHistory;
          setShowAllHistory(next);
          setHistoryPage(1);
          loadDecisionHistory(selectedShipment?.shipment_id, next, 1, historyLimit);
        }}
        page={historyPage}
        pageSize={historyLimit}
        total={historyTotal}
        onPageChange={(newPage) => {
          setHistoryPage(newPage);
          loadDecisionHistory(selectedShipment?.shipment_id, showAllHistory, newPage, historyLimit);
        }}
        onPageSizeChange={(newLimit) => {
          setHistoryLimit(newLimit);
          setHistoryPage(1);
          loadDecisionHistory(selectedShipment?.shipment_id, showAllHistory, 1, newLimit);
        }}
      />

      {/* 7. Shipment Risk Monitor Table */}
      <ShipmentRiskTable
        shipments={shipments}
        selectedShipmentId={selectedShipment?.shipment_id}
        onSelectShipment={handleSelectShipment}
        loading={loadingInitial}
      />

      {/* 8. Full Details Modal */}
      <RecommendationDetailsModal
        option={detailsModalOption}
        baseline={baselineData}
        isOpen={Boolean(detailsModalOption)}
        onClose={() => setDetailsModalOption(null)}
        onSelectOption={(opt) => setExecuteModalOption(opt)}
        onExecuteDecision={(opt) => setExecuteModalOption(opt)}
        executedDecision={currentExecutedDecision}
        proposedDecision={currentProposedDecision}
      />

      {/* 9. Execute Decision Confirmation Modal (Day 17 Secure Workflow) */}
      <ExecuteDecisionModal
        option={executeModalOption}
        shipment={selectedShipment}
        baseline={baselineData}
        isOpen={Boolean(executeModalOption)}
        onClose={() => {
          setExecuteModalOption(null);
          setExecuteError(null);
        }}
        onConfirmExecution={handleConfirmExecution}
        loading={executingDecision}
        error={executeError}
      />

      {/* 10. Propose Decision Modal (Fallback Protocol) */}
      <ProposeDecisionModal
        option={proposeModalOption}
        shipment={selectedShipment}
        isOpen={Boolean(proposeModalOption)}
        onClose={() => setProposeModalOption(null)}
        onSubmitProposal={handleSubmitProposal}
        loading={submittingProposal}
      />
    </div>
  );
}
