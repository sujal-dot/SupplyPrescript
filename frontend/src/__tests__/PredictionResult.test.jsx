import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import PredictionResult from '../components/predictions/PredictionResult';

describe('PredictionResult Component', () => {
  it('renders awaiting state when no result is present', () => {
    render(<PredictionResult result={null} />);
    expect(screen.getByText(/Awaiting Scenario Submission/i)).toBeInTheDocument();
  });

  it('renders probability gauge, delay days, and risk level badge', () => {
    const mockResult = {
      delay_probability: 0.84,
      predicted_delay_days: 12.5,
      risk: 'HIGH',
      model_version: 'v1.0.0-xgb',
      prediction_id: 'PRED-TEST-123',
      prediction_timestamp: '2026-10-13T10:00:00Z',
      features_used: {
        supplier_reliability: 0.98,
        inventory_level: 500,
      },
    };

    render(<PredictionResult result={mockResult} />);

    expect(screen.getByText(/Shipment Risk Assessment/i)).toBeInTheDocument();
    expect(screen.getByText('84%')).toBeInTheDocument();
    expect(screen.getByText('+12.5')).toBeInTheDocument();
    expect(screen.getAllByText('HIGH').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('v1.0.0-xgb')).toBeInTheDocument();
    expect(screen.getByText(/Model Estimation Notice:/i)).toBeInTheDocument();
  });
});
