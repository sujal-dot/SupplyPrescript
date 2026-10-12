import React, { useEffect, useState } from 'react';
import { 
  getApiRoot, 
  getBackendHealth, 
  getDatabaseHealth,
  measureApiLatency
} from '../services/api';
import { 
  CheckCircle2, 
  XCircle, 
  RefreshCw, 
  Server, 
  Database, 
  Globe, 
  ShieldCheck, 
  Activity,
  Terminal,
  AlertTriangle
} from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import GlassCard from '../components/ui/GlassCard';
import GlassPanel from '../components/ui/GlassPanel';
import GlassButton from '../components/ui/GlassButton';
import StatusBadge from '../components/ui/StatusBadge';

export default function HealthPage() {
  const [rootData, setRootData] = useState(null);
  const [backendData, setBackendData] = useState(null);
  const [dbData, setDbData] = useState(null);
  const [latency, setLatency] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    
    // Latency probe
    const pingStart = performance.now();
    try {
      const rootRes = await getApiRoot();
      setRootData({ status: 'success', data: rootRes });
    } catch (err) {
      setRootData({ status: 'error', error: err.message });
    }

    try {
      const backendRes = await getBackendHealth();
      setBackendData({ status: 'success', data: backendRes });
    } catch (err) {
      setBackendData({ status: 'error', error: err.message });
    }

    try {
      const dbRes = await getDatabaseHealth();
      setDbData({ status: 'success', data: dbRes });
    } catch (err) {
      setDbData({
        status: 'error',
        error: err.response?.data?.detail || err.message,
      });
    }

    const pingEnd = performance.now();
    setLatency(Math.round(pingEnd - pingStart));
    setLoading(false);
    setLastChecked(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const isAllHealthy =
    rootData?.status === 'success' &&
    backendData?.status === 'success' &&
    dbData?.status === 'success';

  return (
    <div className="space-y-8">
      <PageHeader
        title="System Infrastructure Health Diagnostics"
        subtitle="Real-time telemetry probing FastAPI application processes, PostgreSQL connection pools, and network roundtrip latencies."
        breadcrumbs={[{ label: 'System Health' }]}
        lastUpdated={lastChecked}
        actions={
          <GlassButton
            variant="primary"
            size="md"
            icon={RefreshCw}
            loading={loading}
            onClick={fetchDiagnostics}
          >
            Probe All Endpoints
          </GlassButton>
        }
      />

      {/* Global Status Banner */}
      <GlassCard
        className={`p-6 rounded-2xl border ${
          isAllHealthy
            ? 'border-emerald-400/30 bg-emerald-500/10'
            : 'border-rose-400/30 bg-rose-500/10'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div
              className={`p-2.5 rounded-2xl border ${
                isAllHealthy
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30'
                  : 'bg-rose-500/20 text-rose-300 border-rose-400/30'
              }`}
            >
              {isAllHealthy ? (
                <CheckCircle2 className="h-6 w-6" />
              ) : (
                <XCircle className="h-6 w-6" />
              )}
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                {isAllHealthy
                  ? 'All Core Systems Operational'
                  : 'Backend Disconnected or Unreachable'}
              </h3>
              <p className="text-xs text-slate-300 mt-0.5">
                {isAllHealthy
                  ? 'FastAPI process and PostgreSQL connection pool responding within SLA thresholds.'
                  : 'Unable to establish socket handshake with http://localhost:8000.'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">Probe Latency:</span>
            <span className="text-cyan-300 font-bold bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/10">
              {latency ? `${latency}ms` : 'Measuring...'}
            </span>
          </div>
        </div>

        {!isAllHealthy && (
          <div className="mt-4 pt-4 border-t border-white/[0.08] text-xs text-slate-400 space-y-1">
            <div className="font-semibold text-rose-300">To start backend services locally:</div>
            <code className="block bg-[#07111F] p-2.5 rounded-xl border border-white/10 text-cyan-300 font-mono text-[11px]">
              cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
            </code>
          </div>
        )}
      </GlassCard>

      {/* Diagnostics Endpoints Grid */}
      <div className="space-y-6">
        {/* Endpoint 1: Root / */}
        <GlassCard interactive className="p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-400/20 text-blue-400">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">GET / (API Root)</h4>
                <p className="text-xs text-slate-400">FastAPI Gateway Handshake</p>
              </div>
            </div>
            {rootData?.status === 'success' ? (
              <StatusBadge status="200 OK" variant="success" />
            ) : (
              <StatusBadge status="Connection Refused" variant="error" />
            )}
          </div>
          <pre className="glass-code p-4 rounded-xl text-xs font-mono text-slate-300 overflow-x-auto">
            {JSON.stringify(rootData, null, 2)}
          </pre>
        </GlassCard>

        {/* Endpoint 2: /health */}
        <GlassCard interactive className="p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-400/20 text-cyan-400">
                <Server className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">GET /health (Backend Core Service)</h4>
                <p className="text-xs text-slate-400">Process Liveness &amp; Memory Health</p>
              </div>
            </div>
            {backendData?.status === 'success' ? (
              <StatusBadge status="Healthy" variant="success" />
            ) : (
              <StatusBadge status="Service Down" variant="error" />
            )}
          </div>
          <pre className="glass-code p-4 rounded-xl text-xs font-mono text-slate-300 overflow-x-auto">
            {JSON.stringify(backendData, null, 2)}
          </pre>
        </GlassCard>

        {/* Endpoint 3: /health/db */}
        <GlassCard interactive className="p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-400/20 text-emerald-400">
                <Database className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">GET /health/db (PostgreSQL Engine)</h4>
                <p className="text-xs text-slate-400">SQLAlchemy Engine &amp; Connection Pool</p>
              </div>
            </div>
            {dbData?.status === 'success' ? (
              <StatusBadge status="Connected" variant="success" />
            ) : (
              <StatusBadge status="Pool Disconnected" variant="error" />
            )}
          </div>
          <pre className="glass-code p-4 rounded-xl text-xs font-mono text-slate-300 overflow-x-auto">
            {JSON.stringify(dbData, null, 2)}
          </pre>
        </GlassCard>
      </div>
    </div>
  );
}
