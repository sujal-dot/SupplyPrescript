/**
 * SupplyPrescript — Model Feedback API Client Service (Day 22)
 * =============================================================
 * Connects the UI to continuous learning feedback pipeline endpoints:
 * - POST /api/feedback/generate: Scans predictions & outcomes, updates feedback records, exports manifests.
 * - GET /api/feedback: Lists feedback records with pagination and filters.
 * - GET /api/feedback/:id: Retrieves a single feedback record.
 * - POST /api/feedback/evaluate: Evaluates model performance on eligible feedback actuals.
 * - GET /api/feedback/datasets: Lists available versioned feedback dataset manifests.
 */

import apiClient, { formatApiError } from './api';

/**
 * Generate or refresh model feedback observations
 * @param {Object} payload - { dataset_version, export_dataset, force_refresh }
 * @returns {Promise<Object>} GenerateFeedbackResponse schema
 */
export async function generateFeedback(payload = {}) {
  const response = await apiClient.post('/api/feedback/generate', payload);
  return response.data;
}

/**
 * Fetch paginated feedback records with filtering
 * @param {Object} params - { shipment_id, model_version, feedback_status, dataset_version, page, page_size }
 * @returns {Promise<Object>} FeedbackListResponse schema
 */
export async function getFeedbackList(params = {}) {
  const cleanParams = {};
  Object.keys(params).forEach((key) => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      cleanParams[key] = params[key];
    }
  });

  const response = await apiClient.get('/api/feedback', { params: cleanParams });
  return response.data;
}

/**
 * Retrieve a specific feedback record by ID
 * @param {string|number} feedbackId - e.g. "FB-XXXXXX"
 * @returns {Promise<Object>} FeedbackItemResponse schema
 */
export async function getFeedbackRecord(feedbackId) {
  if (!feedbackId) {
    throw new Error('feedbackId is required');
  }
  const cleanId = encodeURIComponent(String(feedbackId).trim());
  const response = await apiClient.get(`/api/feedback/${cleanId}`);
  return response.data;
}

/**
 * Evaluate a model version against verified feedback actuals
 * @param {Object} payload - { model_version, dataset_version, min_sample_threshold }
 * @returns {Promise<Object>} EvaluateModelResponse schema
 */
export async function evaluateModel(payload) {
  if (!payload?.model_version) {
    throw new Error('model_version is required for evaluation');
  }
  const response = await apiClient.post('/api/feedback/evaluate', payload);
  return response.data;
}

/**
 * Retrieve list of generated dataset manifests
 * @returns {Promise<Array<Object>>} List of dataset manifest objects
 */
export async function getDatasetManifests() {
  const response = await apiClient.get('/api/feedback/datasets');
  return response.data;
}

export { formatApiError };

export default {
  generateFeedback,
  getFeedbackList,
  getFeedbackRecord,
  evaluateModel,
  getDatasetManifests,
  formatApiError,
};
