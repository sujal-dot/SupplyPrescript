import axios from 'axios';

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getApiRoot = async () => {
  const response = await apiClient.get('/');
  return response.data;
};

export const getBackendHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const getDatabaseHealth = async () => {
  const response = await apiClient.get('/health/db');
  return response.data;
};

export const getDashboardMetrics = async () => {
  const response = await apiClient.get('/api/dashboard');
  return response.data;
};

// Backward-compatible alias
export const getDashboard = getDashboardMetrics;

export const getShipments = async (params = {}) => {
  const response = await apiClient.get('/api/shipments', { params });
  return response.data;
};

export const getSuppliers = async (params = {}) => {
  const response = await apiClient.get('/api/suppliers', { params });
  return response.data;
};

export const getProducts = async (params = {}) => {
  const response = await apiClient.get('/api/products', { params });
  return response.data;
};

export const getInventory = async (params = {}) => {
  const response = await apiClient.get('/api/inventory', { params });
  return response.data;
};

export const getPredictions = async (params = {}) => {
  const response = await apiClient.get('/api/predictions', { params });
  return response.data;
};

/**
 * Production Day 9/10 shipment delay prediction
 * Calls POST /api/predict with database feature resolution
 */
export const predictShipment = async (payload) => {
  const response = await apiClient.post('/api/predict', payload);
  return response.data;
};

/**
 * Legacy direct feature payload prediction
 */
export const predictShipmentDelay = async (payload) => {
  const response = await apiClient.post('/api/predictions/shipment-delay', payload);
  return response.data;
};

/**
 * Prescriptive Decision Alternatives (Day 13)
 */
export const getOptimizationAlternatives = async (shipmentId, params = {}) => {
  const response = await apiClient.get(`/api/optimization/alternatives/${shipmentId}`, { params });
  return response.data;
};

export const generateOptimizationAlternatives = async (payload) => {
  const response = await apiClient.post('/api/optimization/alternatives', payload);
  return response.data;
};

export const optimizeSupplyChain = async (scenarioOverrides = {}) => {
  const response = await apiClient.post('/api/optimize', scenarioOverrides);
  return response.data;
};

export const measureApiLatency = async () => {
  const start = performance.now();
  try {
    await apiClient.get('/health', { timeout: 3000 });
    const end = performance.now();
    return Math.round(end - start);
  } catch (err) {
    const end = performance.now();
    return { error: err.message, latency: Math.round(end - start) };
  }
};

/**
 * Formats API errors into clean, human-readable strings
 */
export const formatApiError = (error) => {
  if (!error) return 'An unexpected error occurred.';
  if (error.response) {
    const { status, data } = error.response;
    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        return data.detail.map((d) => d.msg || `${d.loc?.join('.')}: invalid`).join('; ');
      }
      return String(data.detail);
    }
    if (status === 404) return 'The requested resource was not found on the server.';
    if (status === 503) return 'ML model artifacts or service is temporarily unavailable.';
    if (status >= 500) return 'Server internal error occurred. Please try again.';
    return `Server error (${status}): ${error.message}`;
  }
  if (error.request) {
    return 'Unable to reach SupplyPrescript API server at ' + API_BASE_URL + '. Check that the backend is running.';
  }
  return error.message || 'An unexpected error occurred.';
};

export default apiClient;
