import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 6000,
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

export const getDashboard = async () => {
  const response = await apiClient.get('/api/dashboard');
  return response.data;
};

export const getInventory = async (params = {}) => {
  const response = await apiClient.get('/api/inventory', { params });
  return response.data;
};

export const getShipments = async (params = {}) => {
  const response = await apiClient.get('/api/shipments', { params });
  return response.data;
};

export const getSuppliers = async (params = {}) => {
  const response = await apiClient.get('/api/suppliers', { params });
  return response.data;
};

export const predictShipmentDelay = async (payload) => {
  const response = await apiClient.post('/api/predictions/shipment-delay', payload);
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

export default apiClient;
