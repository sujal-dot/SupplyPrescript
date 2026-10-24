/**
 * SupplyPrescript — Decision Execution & Write-Back API Service (Day 18)
 * =======================================================================
 * Client service layer connecting the Command Center to decision execution & write-back endpoints:
 * - POST /api/decisions: Authorizes and records an immutable decision in PostgreSQL
 * - GET /api/decisions: Retrieves chronological decision audit history with pagination & filtering
 * - GET /api/decisions/:id: Fetches individual decision record from database by ID
 */

import apiClient, { formatApiError } from './api';

/**
 * Execute and record an authorized prescriptive decision
 * @param {Object} payload - { shipment_id, option_id, strategy, recommendation, user_id, optimization_run_id, idempotency_key, notes, approved_by }
 * @returns {Promise<Object>} ExecuteDecisionResponse / DecisionResponse schema
 */
export async function executeDecision(payload) {
  const cleanPayload = {
    shipment_id: payload.shipment_id?.trim() || '',
    option_id: payload.option_id?.trim().toUpperCase() || '',
    strategy: payload.strategy || payload.recommendation || undefined,
    recommendation: payload.recommendation || payload.strategy || undefined,
    user_id: payload.user_id?.trim() || undefined,
    optimization_run_id: payload.optimization_run_id || undefined,
    idempotency_key: payload.idempotency_key || undefined,
    notes: payload.notes?.trim() || undefined,
    approved_by: payload.approved_by?.trim() || payload.user_id?.trim() || 'usr_ops_manager',
  };

  const response = await apiClient.post('/api/decisions', cleanPayload);
  return response.data;
}

/**
 * Fetch decision execution audit history with pagination and filtering
 * @param {Object} params - { shipment_id, user_id, status, limit, offset, start_time, end_time }
 * @returns {Promise<Object>} DecisionHistoryResponse schema { total, limit, offset, items, decisions }
 */
export async function getDecisions(params = {}) {
  const response = await apiClient.get('/api/decisions', { params });
  return response.data;
}

/**
 * Retrieve a specific decision record by decision ID or primary key
 * @param {string|number} decisionId - e.g. "DEC-20261021-0001" or integer ID
 * @returns {Promise<Object>} DecisionResponse schema
 */
export async function getDecisionById(decisionId) {
  if (decisionId == null) {
    throw new Error('decisionId is required');
  }
  const cleanId = String(decisionId).trim();
  const response = await apiClient.get(`/api/decisions/${encodeURIComponent(cleanId)}`);
  return response.data;
}

/**
 * Record an actual operational outcome for an executed decision (Day 19 Closed-Loop)
 * @param {string|number} decisionId - target decision identifier
 * @param {Object} payload - { actual_cost, currency, actual_delivery_date, actual_delay, actual_supplier, actual_quantity, source, notes, outcome_status }
 * @returns {Promise<Object>} OutcomeComparisonResponse schema
 */
export async function recordOutcome(decisionId, payload) {
  if (decisionId == null) {
    throw new Error('decisionId is required');
  }
  const cleanId = String(decisionId).trim();
  const cleanPayload = {
    actual_cost: Number(payload.actual_cost),
    currency: payload.currency || 'USD',
    actual_delivery_date: payload.actual_delivery_date || undefined,
    actual_delay: payload.actual_delay != null ? Number(payload.actual_delay) : undefined,
    actual_supplier: payload.actual_supplier?.trim() || undefined,
    actual_quantity: payload.actual_quantity != null ? Number(payload.actual_quantity) : undefined,
    source: payload.source?.trim() || 'manual_entry',
    notes: payload.notes?.trim() || undefined,
    outcome_status: payload.outcome_status || undefined,
  };
  const response = await apiClient.post(`/api/decisions/${encodeURIComponent(cleanId)}/outcome`, cleanPayload);
  return response.data;
}

/**
 * Retrieve recorded operational outcome and predicted vs actual comparison (Day 19)
 * @param {string|number} decisionId - target decision identifier
 * @returns {Promise<Object>} OutcomeComparisonResponse schema
 */
export async function getOutcome(decisionId) {
  if (decisionId == null) {
    throw new Error('decisionId is required');
  }
  const cleanId = String(decisionId).trim();
  const response = await apiClient.get(`/api/decisions/${encodeURIComponent(cleanId)}/outcome`);
  return response.data;
}

/**
 * List operational outcome records with pagination & filters (Day 19)
 * @param {Object} params - { shipment_id, supplier, outcome_status, start_date, end_date, limit, offset }
 * @returns {Promise<Object>} OutcomeListResponse schema
 */
export async function getOutcomes(params = {}) {
  const response = await apiClient.get('/api/outcomes', { params });
  return response.data;
}

/**
 * Retrieve comprehensive Decision ROI & Success Evaluation (Day 20 Decision ROI Engine)
 * @param {string|number} decisionId - target decision identifier
 * @param {Object} params - optional { investment_cost, additional_decision_costs }
 * @returns {Promise<Object>} DecisionROIResponse schema
 */
export async function getDecisionROI(decisionId, params = {}) {
  if (decisionId == null) {
    throw new Error('decisionId is required');
  }
  const cleanId = String(decisionId).trim();
  const response = await apiClient.get(`/api/decisions/${encodeURIComponent(cleanId)}/roi`, { params });
  return response.data;
}

/**
 * Retrieve portfolio-level aggregated Decision ROI summary (Day 20)
 * @param {Object} params - { shipment_id, status, supplier, start_date, end_date, currency }
 * @returns {Promise<Object>} PortfolioROISummaryResponse schema
 */
export async function getPortfolioROI(params = {}) {
  const response = await apiClient.get('/api/analytics/decision-roi', { params });
  return response.data;
}

export { formatApiError };

export default {
  executeDecision,
  getDecisions,
  getDecisionById,
  recordOutcome,
  getOutcome,
  getOutcomes,
  getDecisionROI,
  getPortfolioROI,
  formatApiError,
};

