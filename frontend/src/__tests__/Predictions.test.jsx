import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Predictions from '../pages/Predictions';
import * as api from '../services/api';

vi.mock('../services/api');

describe('Predictions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.formatApiError.mockImplementation((err) => err?.message || 'Error occurred');
  });

  it('loads real suppliers/products, validates form, and displays XGBoost prediction result', async () => {
    api.getSuppliers.mockResolvedValue({
      data: [
        { id: 1, supplier_id: 'SUP-001', supplier_name: 'Apex Global Logistics', supplier_reliability: 0.98 },
      ],
    });

    api.getProducts.mockResolvedValue({
      data: [
        { id: 1, product_id: 'PRD-001', product_name: 'Industrial Servo Motor', category: 'Motors' },
      ],
    });

    api.getPredictions.mockResolvedValue({
      data: [],
      total: 0,
    });

    api.predictShipment.mockResolvedValue({
      delay_probability: 0.84,
      predicted_delay_days: 12.5,
      risk: 'HIGH',
      model_version: 'v1.0.0-xgb',
      prediction_timestamp: '2026-10-13T10:00:00Z',
      features_used: {
        supplier_reliability: 0.98,
        inventory_level: 500,
        quantity: 100,
        transport_mode: 'Air',
      },
    });

    render(
      <MemoryRouter>
        <Predictions />
      </MemoryRouter>
    );

    // Initial page title check
    expect(screen.getByText(/Shipment Delay Risk Prediction Workspace/i)).toBeInTheDocument();

    // Wait for dynamic dropdown options to load
    await waitFor(() => {
      expect(screen.getByText(/Apex Global Logistics/i)).toBeInTheDocument();
      expect(screen.getByText(/Industrial Servo Motor/i)).toBeInTheDocument();
    });

    // Submit prediction form
    const submitBtn = screen.getByRole('button', { name: /Predict Shipment Risk/i });
    fireEvent.submit(submitBtn.closest('form'));

    // Verify prediction execution and output
    await waitFor(() => {
      expect(screen.getByText('84%')).toBeInTheDocument();
      expect(screen.getByText('+12.5')).toBeInTheDocument();
      expect(screen.getAllByText('HIGH').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('v1.0.0-xgb')).toBeInTheDocument();
    });

    // Verify explainability and disclaimer
    expect(screen.getByText(/Model Estimation Notice:/i)).toBeInTheDocument();
  });
});
