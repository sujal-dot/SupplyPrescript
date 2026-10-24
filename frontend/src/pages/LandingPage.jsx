import React, { useEffect, useState } from 'react';
import { getBackendHealth, getDatabaseHealth, getApiRoot } from '../services/api';
import StatusCard from '../components/StatusCard';
import { 
  Server, 
  Database, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  TrendingUp, 
  Box, 
  Activity, 
  Layers,
  Cpu,
  ShieldCheck
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [databaseStatus, setDatabaseStatus] = useState('checking');
  const [backendDetails, setBackendDetails] = useState(null);
  const [databaseDetails, setDatabaseDetails] = useState(null);
  const [apiMessage, setApiMessage] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const rootRes = await getApiRoot();
      setApiMessage(rootRes.message || 'Connected');
    } catch (err) {
      setApiMessage('Unable to reach root endpoint');
    }

    try {
      const backendRes = await getBackendHealth();
      setBackendStatus(backendRes.status || 'healthy');
      setBackendDetails(backendRes);
    } catch (err) {
      setBackendStatus('unhealthy');
      setBackendDetails({ error: err.message });
    }

    try {
      const dbRes = await getDatabaseHealth();
      setDatabaseStatus(dbRes.database || dbRes.status || 'connected');
      setDatabaseDetails(dbRes);
    } catch (err) {
      setDatabaseStatus('disconnected');
      setDatabaseDetails({ error: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-12">
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto relative pt-4">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full glass-pill-red text-red-300 text-xs font-semibold uppercase tracking-wider mb-8 shadow-lg shadow-red-500/10">
          <Sparkles className="h-3.5 w-3.5 text-red-300 animate-pulse" />
          <span>Prescriptive Intelligence &bull; SupplyPrescript</span>
        </div>
        
        <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white mb-6">
          Supply<span className="bg-gradient-to-r from-red-500 via-rose-400 to-red-400 bg-clip-text text-transparent">Prescript</span>
        </h1>
        
        <p className="text-xl sm:text-2xl font-medium text-slate-200/90 mb-4">
          Next-Gen Supply Chain Analytics &amp; Autonomous Prescription
        </p>

        <p className="text-slate-400 text-base max-w-2xl mx-auto leading-relaxed">
          Enterprise platform combining predictive demand forecasting, multi-echelon inventory optimization, and automated prescriptive routing with modern glass telemetry.
        </p>

        {apiMessage && (
          <div className="mt-8 inline-flex items-center space-x-2.5 text-xs font-mono text-red-300 glass-badge px-4 py-2 rounded-xl">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-md shadow-emerald-400/80 animate-pulse" />
            <span>API Gateway: {apiMessage}</span>
          </div>
        )}
      </div>

      {/* Glassmorphic Metric Cards Showcase */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card-interactive rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium tracking-wide">Active Orders</span>
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
              <Box className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">94</span>
            <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-md">
              +5.2%
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Current active dispatch nodes</p>
        </div>

        <div className="glass-card-interactive rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium tracking-wide">Logistics Efficiency</span>
            <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-400/20 text-rose-400">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">91%</span>
            <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-md">
              +2.1%
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Optimal route adherence</p>
        </div>

        <div className="glass-card-interactive rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium tracking-wide">Inventory Health</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-400/20 text-emerald-400">
              <Layers className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">88%</span>
            <span className="text-xs font-semibold text-red-400 bg-red-500/10 border border-red-500/20 px-1.5 py-0.5 rounded-md">
              Optimal
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">Zero critical stockouts</p>
        </div>

        <div className="glass-card-interactive rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium tracking-wide">Telemetry Latency</span>
            <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white">42ms</span>
            <span className="text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-md">
              Real-time
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">FastAPI + PostgreSQL Pool</p>
        </div>
      </div>

      {/* Connectivity & Health Status Grid */}
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400 shadow-md shadow-red-500/80 animate-ping" />
            <h2 className="text-lg font-bold text-white tracking-wide">
              System Connectivity Telemetry
            </h2>
          </div>
          <span className="text-xs text-red-300/70 font-mono glass-badge px-2.5 py-1 rounded-md">
            Live Axios Polling
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatusCard
            title="FastAPI Backend Service"
            status={backendStatus}
            details={backendDetails}
            loading={loading}
            onRefresh={fetchHealth}
          />

          <StatusCard
            title="PostgreSQL 16 Engine"
            status={databaseStatus}
            details={databaseDetails}
            loading={loading}
            onRefresh={fetchHealth}
          />
        </div>

        {/* Architecture Verification Checklist in Glass Panel */}
        <div className="glass-card rounded-2xl p-6 sm:p-8 relative overflow-hidden">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/[0.08]">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
                  Verified Stack Architecture
                </h3>
                <p className="text-xs text-slate-400">Production-grade foundation components</p>
              </div>
            </div>
            <span className="text-xs font-semibold text-emerald-300 glass-pill-emerald px-2.5 py-1 rounded-full">
              Phase 1 Online
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-slate-300">
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>React 18 + Vite + Tailwind Glassmorphism</span>
            </div>
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>FastAPI Backend Service (Port 8000)</span>
            </div>
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>PostgreSQL 16 in Docker (Port 5432)</span>
            </div>
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>CORS &amp; Real-time Axios Connectivity</span>
            </div>
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>SQLAlchemy Engine Connection Pool</span>
            </div>
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
              <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>ML &amp; Optimization Architecture Active</span>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-white/[0.08] flex justify-end">
            <Link
              to="/health"
              className="inline-flex items-center space-x-2 text-sm font-semibold text-red-300 hover:text-white glass-badge hover:bg-red-500/20 px-4 py-2 rounded-xl transition-all duration-200"
            >
              <span>View Deep Diagnostics</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
