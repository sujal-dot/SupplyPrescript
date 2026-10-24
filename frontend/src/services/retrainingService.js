/**
 * SupplyPrescript — Retraining & Model Monitoring API Client Service (Day 23)
 * =========================================================================
 * Integrates with:
 * - GET /api/ml/retraining/monitor
 * - POST /api/ml/retraining/run
 * - GET /api/ml/retraining/jobs
 * - GET /api/ml/retraining/jobs/:id
 * - POST /api/ml/retraining/jobs/:id/promote
 * - POST /api/ml/retraining/rollback
 */

import apiClient, { formatApiError } from './api';

/**
 * Retrieve current model performance drift diagnostic report
 * @param {Object} params - { model_version, dataset_version }
 * @returns {Promise<Object>} ModelMonitorStatusResponse schema
 */
export async function getRetrainingMonitorStatus(params = {}) {
  const cleanParams = {};
  Object.keys(params).forEach((key) => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      cleanParams[key] = params[key];
    }
  });
  const response = await apiClient.get('/api/ml/retraining/monitor', { params: cleanParams });
  return response.data;
}

/**
 * Initiate or evaluate a retraining cycle
 * @param {Object} payload - { trigger_reason, force }
 * @returns {Promise<Object>} RunRetrainingResponse schema
 */
export async function runRetrainingJob(payload = {}) {
  const response = await apiClient.post('/api/ml/retraining/run', payload);
  return response.data;
}

/**
 * Fetch paginated retraining jobs with optional status filter
 * @param {Object} params - { status, page, page_size }
 * @returns {Promise<Object>} RetrainingJobListResponse schema
 */
export async function getRetrainingJobs(params = {}) {
  const cleanParams = {};
  Object.keys(params).forEach((key) => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      cleanParams[key] = params[key];
    }
  });
  const response = await apiClient.get('/api/ml/retraining/jobs', { params: cleanParams });
  return response.data;
}

/**
 * Retrieve details and validation report for a specific retraining job
 * @param {string} jobId - e.g. "RETRAIN_20261026_XXXXXX"
 * @returns {Promise<Object>} RetrainingJobResponse schema
 */
export async function getRetrainingJob(jobId) {
  if (!jobId) throw new Error('jobId is required');
  const cleanId = encodeURIComponent(String(jobId).trim());
  const response = await apiClient.get(`/api/ml/retraining/jobs/${cleanId}`);
  return response.data;
}

/**
 * Promote an approved REGISTERED candidate model to active production
 * @param {string} jobId
 * @returns {Promise<Object>} PromoteCandidateResponse schema
 */
export async function promoteCandidateModel(jobId) {
  if (!jobId) throw new Error('jobId is required');
  const cleanId = encodeURIComponent(String(jobId).trim());
  const response = await apiClient.post(`/api/ml/retraining/jobs/${cleanId}/promote`);
  return response.data;
}

/**
 * Roll back active production model to a verified prior registered version
 * @param {string} targetVersion - e.g. "v1.0"
 * @returns {Promise<Object>} RollbackModelResponse schema
 */
export async function rollbackModelVersion(targetVersion) {
  if (!targetVersion) throw new Error('targetVersion is required');
  const response = await apiClient.post('/api/ml/retraining/rollback', {
    target_version: String(targetVersion).trim(),
  });
  return response.data;
}

export { formatApiError };

export default {
  getRetrainingMonitorStatus,
  runRetrainingJob,
  getRetrainingJobs,
  getRetrainingJob,
  promoteCandidateModel,
  rollbackModelVersion,
  formatApiError,
};
