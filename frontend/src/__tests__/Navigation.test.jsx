import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

describe('Sidebar Navigation', () => {
  it('renders all 5 core navigation links and logo', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar isOpen={true} setIsOpen={() => {}} isMobile={false} closeMobile={() => {}} />
      </MemoryRouter>
    );

    expect(screen.getByText(/Supply/i)).toBeInTheDocument();
    expect(screen.getByText(/Prescript/i)).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Predictions')).toBeInTheDocument();
    expect(screen.getByText('Shipments')).toBeInTheDocument();
    expect(screen.getByText('Suppliers')).toBeInTheDocument();
    expect(screen.getByText('Inventory')).toBeInTheDocument();
  });
});
