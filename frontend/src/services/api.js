import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 5000,
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

export default apiClient;
