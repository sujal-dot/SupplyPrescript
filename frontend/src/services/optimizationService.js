/**
 * SupplyPrescript — Optimization & Prescriptive Decision Service (Day 16)
 * =======================================================================
 * Client service layer connecting the Command Center to FastAPI optimization endpoints:
 * - POST /api/optimize: Evaluates delay risk, computes solver constraints, and returns 3 strategic options
 * - POST /api/optimization/propose-decision: Records proposed decision in PostgreSQL (Safe Workflow)
 * - GET /api/optimization/alternatives/{shipment_id}: Retrieval of prescriptive alternatives
 * - GET /api/dashboard: Real-time supply chain aggregated KPIs and high-risk shipments
 * - GET /api/shipments: Real-time shipment log with pagination, search, and filtering
 */

import apiClient, { formatApiError } from './api';

/**
 * Execute prescriptive optimization for a target shipment
 * @param {Object} payload - { shipment_id, scenario_id, num_options, scenario_overrides }
 * @returns {Promise<Object>} OptimizationResponse schema
 */
export async function optimizeShipment(payload) {
  const cleanPayload = {
    shipment_id: payload.shipment_id?.trim() || '',
    scenario_id: payload.scenario_id || 'baseline',
    num_options: payload.num_options || 3,
    scenario_overrides: payload.scenario_overrides || null,
  };
  const response = await apiClient.post('/api/optimize', cleanPayload);
  return response.data;
}

/**
 * Record a proposed decision in PostgreSQL (Day 16 Safe Selection Workflow)
 * Does NOT execute live purchases or carrier dispatches.
 * @param {Object} payload - { shipment_id, option_id, option_name, decision_reason, notes, proposed_by }
 * @returns {Promise<Object>} ProposeDecisionResponse schema
 */
export async function proposeDecision(payload) {
  const response = await apiClient.post('/api/optimization/propose-decision', payload);
  return response.data;
}

/**
 * Get alternative recommendations by shipment ID
 * @param {string} shipmentId
 * @param {Object} params - { max_budget, max_delay }
 * @returns {Promise<Object>}
 */
export async function getOptimizationAlternatives(shipmentId, params = {}) {
  const response = await apiClient.get(`/api/optimization/alternatives/${shipmentId}`, { params });
  return response.data;
}

/**
 * Fetch high-level aggregated dashboard KPIs and high-risk shipments
 * @returns {Promise<Object>}
 */
export async function getDashboardMetrics() {
  const response = await apiClient.get('/api/dashboard');
  return response.data;
}

/**
 * Fetch shipments with pagination, filters, and sorting
 * @param {Object} params
 * @returns {Promise<Object>}
 */
export async function getShipments(params = {}) {
  const response = await apiClient.get('/api/shipments', { params });
  return response.data;
}

export { formatApiError };

export default {
  optimizeShipment,
  proposeDecision,
  getOptimizationAlternatives,
  getDashboardMetrics,
  getShipments,
  formatApiError,
};
