import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import PredictionForm from '../components/predictions/PredictionForm';
import * as api from '../services/api';

vi.mock('../services/api');

describe('PredictionForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('submits valid form with default payload', async () => {
    api.getSuppliers.mockResolvedValue({
      data: [{ id: 10, supplier_id: 'SUP-010', supplier_name: 'Global Freight', supplier_reliability: 0.95 }],
    });
    api.getProducts.mockResolvedValue({
      data: [{ id: 20, product_id: 'PRD-020', product_name: 'Servo Unit', category: 'Parts' }],
    });

    const mockSubmit = vi.fn();
    render(<PredictionForm onSubmit={mockSubmit} />);

    await waitFor(() => {
      expect(screen.getByText(/Global Freight/i)).toBeInTheDocument();
    });

    const form = screen.getByRole('button', { name: /Predict Shipment Risk/i }).closest('form');
    fireEvent.submit(form);

    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        supplier_id: 10,
        product_id: 20,
        quantity: 500,
        inventory_level: 1200,
        transport_mode: 'Road',
      })
    );
  });
});
