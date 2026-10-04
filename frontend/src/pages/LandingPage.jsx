import React, { useEffect, useState } from 'react';
import { getBackendHealth, getDatabaseHealth, getApiRoot } from '../services/api';
import StatusCard from '../components/StatusCard';
import { Server, Database, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';
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
    <div className="py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-6">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Phase 1 — Project Foundation</span>
        </div>
        
        <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight text-white mb-6">
          SupplyPrescript
        </h1>
        
        <p className="text-xl sm:text-2xl font-medium text-cyan-300/90 mb-4">
          Supply Chain Analytics &amp; Prescription Platform
        </p>

        <p className="text-slate-400 text-base max-w-2xl mx-auto">
          Enterprise foundation for prescriptive supply chain intelligence, predictive demand modeling, and inventory optimization.
        </p>

        {apiMessage && (
          <div className="mt-6 inline-flex items-center space-x-2 text-xs font-mono text-slate-300 bg-slate-800/80 px-4 py-2 rounded-lg border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>API Root: {apiMessage}</span>
          </div>
        )}
      </div>

      {/* Connectivity & Health Status Grid */}
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-200">
            System Connectivity Status
          </h2>
          <span className="text-xs text-slate-400">
            Endpoints tested via Axios in real time
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatusCard
            title="Backend Status"
            status={backendStatus}
            details={backendDetails}
            loading={loading}
            onRefresh={fetchHealth}
          />

          <StatusCard
            title="Database Status"
            status={databaseStatus}
            details={databaseDetails}
            loading={loading}
            onRefresh={fetchHealth}
          />
        </div>

        {/* Phase 1 Verification Checklist */}
        <div className="mt-12 bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">
            Day 1 Architecture Verification
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-slate-300">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>React 18 + Vite + Tailwind CSS</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>FastAPI Backend Service (Port 8000)</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>PostgreSQL 16 in Docker (Port 5432)</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>CORS &amp; Real-time Axios Connectivity</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>SQLAlchemy Engine Connection Pool</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>ML &amp; Optimization Environments Configured</span>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-700/50 flex justify-end">
            <Link
              to="/health"
              className="inline-flex items-center space-x-1.5 text-sm font-semibold text-cyan-400 hover:text-cyan-300 transition-colors"
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
