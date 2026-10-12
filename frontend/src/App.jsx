import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
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
      <div className="relative min-h-screen bg-[#07111F] text-slate-100 flex font-sans selection:bg-cyan-500 selection:text-white overflow-x-hidden">
        {/* Layered Ambient Atmospheric Background */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
          {/* Cyan Glow Orb */}
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-cyan-500/10 blur-[130px] ambient-glow-1" />
          {/* Blue Glow Orb */}
          <div className="absolute top-1/3 -right-48 w-[650px] h-[650px] rounded-full bg-blue-600/10 blur-[150px] ambient-glow-2" />
          {/* Center Subtle Violet Glow */}
          <div className="absolute top-2/3 left-1/4 w-[500px] h-[500px] rounded-full bg-indigo-600/08 blur-[140px] ambient-glow-1" />
          {/* Radial Mesh */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(34,211,238,0.08),transparent)]" />
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
              <Route path="/" element={<DashboardPage />} />
              <Route path="/forecasting" element={<ForecastingPage />} />
              <Route path="/inventory" element={<InventoryPage />} />
              <Route path="/shipments" element={<ShipmentsPage />} />
              <Route path="/prescriptions" element={<PrescriptionsPage />} />
              <Route path="/data" element={<DataPage />} />
              <Route path="/health" element={<HealthPage />} />
            </Routes>
          </main>

          <footer className="glass-nav py-6 px-4 sm:px-8 text-xs text-slate-400 mt-auto">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="font-medium text-slate-300">
                  SupplyPrescript &copy; {new Date().getFullYear()}
                </span>
                <span className="text-slate-600 hidden sm:inline">&bull;</span>
                <span className="text-slate-500">Autonomous Supply Chain Intelligence Matrix</span>
              </div>
              <div className="flex items-center space-x-3 text-[11px] font-mono text-slate-500">
                <span className="glass-badge px-2.5 py-1 text-cyan-300/80">
                  Glassmorphism Architecture Active
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
