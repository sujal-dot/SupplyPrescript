import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
// 5 Core Day 10 Pages
import Dashboard from './pages/Dashboard';
import CommandCenter from './pages/CommandCenter';
import DecisionROI from './pages/DecisionROI';
import Predictions from './pages/Predictions';
import FeedbackPipeline from './pages/FeedbackPipeline';
import Shipments from './pages/Shipments';
import Suppliers from './pages/Suppliers';
import Inventory from './pages/Inventory';

// Supporting and Legacy Pages
import DashboardPage from './pages/DashboardPage';
import ForecastingPage from './pages/ForecastingPage';
import InventoryPage from './pages/InventoryPage';
import ShipmentsPage from './pages/ShipmentsPage';
import PrescriptionsPage from './pages/PrescriptionsPage';
import DataPage from './pages/DataPage';
import HealthPage from './pages/HealthPage';

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ScrollToTop />
      <div className="relative min-h-screen bg-[#0C0406] text-slate-100 flex font-sans selection:bg-red-600 selection:text-white overflow-x-hidden">
        {/* Apple visionOS Style Multi-Orb Dynamic Atmospheric Background */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
          {/* Top-Left Radiant Crimson Orb */}
          <div className="absolute -top-32 -left-32 w-[680px] h-[680px] rounded-full bg-gradient-to-br from-red-600/20 to-rose-600/10 blur-[140px] ambient-glow-1" />
          {/* Top-Right Vivid Rose & Ruby Orb */}
          <div className="absolute -top-20 -right-32 w-[720px] h-[720px] rounded-full bg-gradient-to-bl from-rose-600/18 via-red-600/12 to-transparent blur-[160px] ambient-glow-2" />
          {/* Mid-Left Wine & Carmine Atmosphere */}
          <div className="absolute top-1/2 -left-48 w-[600px] h-[600px] rounded-full bg-red-700/14 blur-[150px] ambient-glow-2" />
          {/* Bottom-Right Deep Ember Glow */}
          <div className="absolute -bottom-32 right-1/4 w-[750px] h-[750px] rounded-full bg-gradient-to-tr from-rose-700/16 via-red-800/10 to-transparent blur-[160px] ambient-glow-1" />
          {/* Apple Sub-surface Radial Light Falloff */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_100%_80%_at_50%_-10%,rgba(244,63,94,0.12),transparent_65%)]" />
          {/* Apple Ambient Vignette */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(12,4,6,0.40)_100%)]" />
        </div>

        {/* Mobile Navigation Backdrop */}
        {mobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}

        {/* Desktop Sidebar (hidden on mobile, uses drawer) */}
        <div className="hidden lg:block">
          <Sidebar
            isOpen={true}
            setIsOpen={() => {}}
            isMobile={false}
            closeMobile={() => {}}
          />
        </div>

        {/* Mobile Sidebar Drawer */}
        <div className="lg:hidden">
          <Sidebar
            isOpen={mobileMenuOpen}
            setIsOpen={setMobileMenuOpen}
            isMobile={true}
            closeMobile={() => setMobileMenuOpen(false)}
          />
        </div>

        {/* Main Application Container */}
        <div className="flex-1 flex flex-col min-h-screen lg:pl-64 transition-all duration-300 relative z-10">
          <Navbar onMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
            <Routes>
              {/* 5 Core Day 10 Pages */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/command-center" element={<CommandCenter />} />
              <Route path="/decision-roi" element={<DecisionROI />} />
              <Route path="/predictions" element={<Predictions />} />
              <Route path="/feedback" element={<FeedbackPipeline />} />
              <Route path="/retraining" element={<FeedbackPipeline />} />
              <Route path="/shipments" element={<Shipments />} />
              <Route path="/suppliers" element={<Suppliers />} />
              <Route path="/inventory" element={<Inventory />} />

              {/* System Health */}
              <Route path="/health" element={<HealthPage />} />

              {/* Supporting and Legacy Pages */}
              <Route path="/forecasting" element={<ForecastingPage />} />
              <Route path="/prescriptions" element={<PrescriptionsPage />} />
              <Route path="/data" element={<DataPage />} />
              <Route path="/legacy/dashboard" element={<DashboardPage />} />
              <Route path="/legacy/shipments" element={<ShipmentsPage />} />
              <Route path="/legacy/inventory" element={<InventoryPage />} />
            </Routes>
          </main>

          <footer className="glass-nav py-6 px-4 sm:px-8 text-xs text-slate-400 mt-auto">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="font-medium text-slate-300">
                  SupplyPrescript &copy; {new Date().getFullYear()}
                </span>
                <span className="text-slate-600 hidden sm:inline">&bull;</span>
                <span className="text-slate-500">Autonomous Supply Chain Intelligence Matrix</span>
              </div>
              <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-500">
                <span className="glass-badge px-2.5 py-1 text-red-300/80">
                  Crimson Glassmorphism Active
                </span>
                <span className="text-slate-600">FastAPI &bull; XGBoost &bull; React 18</span>
              </div>
            </div>
          </footer>
        </div>
      </div>
    </Router>
  );
}
