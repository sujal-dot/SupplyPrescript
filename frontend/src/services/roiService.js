/**
 * SupplyPrescript — Decision ROI API Service (Day 21)
 * ===================================================
 * Service layer connecting the Decision ROI Dashboard to backend analytics:
 * - GET /api/analytics/decision-roi: Comprehensive portfolio metrics, error accuracy,
 *   strategy cost breakdowns, savings timeline, and paginated decision audit records.
 * - GET /api/decisions/{id}/roi: Single-decision deterministic ROI and multi-dimensional success report.
 */

import apiClient, { formatApiError } from './api';

/**
 * Fetch portfolio-level Decision ROI Dashboard analytics
 * @param {Object} params - Query filters { start_date, end_date, strategy, decision_status, currency, shipment_id, supplier, page, page_size }
 * @returns {Promise<Object>} DecisionROIDashboardResponse schema
 */
export async function getDecisionROIAnalytics(params = {}) {
  const cleanParams = {};
  Object.keys(params).forEach((key) => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      cleanParams[key] = params[key];
    }
  });

  const response = await apiClient.get('/api/analytics/decision-roi', { params: cleanParams });
  return response.data;
}

/**
 * Fetch deterministic ROI and success evaluation for a single decision
 * @param {string|number} decisionId - Decision business ID or primary key
 * @returns {Promise<Object>} DecisionROIResponse schema
 */
export async function getDecisionROI(decisionId) {
  if (decisionId == null) {
    throw new Error('decisionId is required to fetch ROI report');
  }
  const cleanId = encodeURIComponent(String(decisionId).trim());
  const response = await apiClient.get(`/api/decisions/${cleanId}/roi`);
  return response.data;
}

export { formatApiError };

export default {
  getDecisionROIAnalytics,
  getDecisionROI,
  formatApiError,
};
