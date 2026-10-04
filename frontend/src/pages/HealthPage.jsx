import React, { useEffect, useState } from 'react';
import { getApiRoot, getBackendHealth, getDatabaseHealth } from '../services/api';
import { CheckCircle2, XCircle, RefreshCw, Server, Database, Globe, ShieldCheck } from 'lucide-react';

export default function HealthPage() {
  const [rootData, setRootData] = useState(null);
  const [backendData, setBackendData] = useState(null);
  const [dbData, setDbData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
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
    } finally {
      setLoading(false);
      setLastChecked(new Date().toLocaleTimeString());
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  return (
    <div className="py-12 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center space-x-3">
            <ShieldCheck className="h-8 w-8 text-cyan-400" />
            <span>System Health Diagnostics</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status of backend services and database infrastructure
          </p>
        </div>
        <button
          onClick={fetchDiagnostics}
          disabled={loading}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-colors disabled:opacity-50 shadow-lg shadow-cyan-600/20"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh All</span>
        </button>
      </div>

      {lastChecked && (
        <p className="text-xs text-slate-500 mb-6">
          Last health verification check at {lastChecked}
        </p>
      )}

      <div className="space-y-6">
        {/* API Root Endpoint */}
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <Globe className="h-5 w-5 text-blue-400" />
              <h3 className="font-semibold text-slate-200">
                GET / (API Root)
              </h3>
            </div>
            {rootData?.status === 'success' ? (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>200 OK</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950 text-rose-400 border border-rose-800">
                <XCircle className="h-3.5 w-3.5" />
                <span>Failed</span>
              </span>
            )}
          </div>
          <pre className="text-xs font-mono bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto">
            {JSON.stringify(rootData, null, 2)}
          </pre>
        </div>

        {/* Backend /health Endpoint */}
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <Server className="h-5 w-5 text-cyan-400" />
              <h3 className="font-semibold text-slate-200">
                GET /health (Backend Core Service)
              </h3>
            </div>
            {backendData?.status === 'success' ? (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>200 OK - Healthy</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950 text-rose-400 border border-rose-800">
                <XCircle className="h-3.5 w-3.5" />
                <span>Unhealthy</span>
              </span>
            )}
          </div>
          <pre className="text-xs font-mono bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto">
            {JSON.stringify(backendData, null, 2)}
          </pre>
        </div>

        {/* Database /health/db Endpoint */}
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <Database className="h-5 w-5 text-emerald-400" />
              <h3 className="font-semibold text-slate-200">
                GET /health/db (PostgreSQL Connection Pool)
              </h3>
            </div>
            {dbData?.status === 'success' ? (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>200 OK - Connected</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950 text-rose-400 border border-rose-800">
                <XCircle className="h-3.5 w-3.5" />
                <span>Disconnected</span>
              </span>
            )}
          </div>
          <pre className="text-xs font-mono bg-slate-900/80 p-3 rounded-lg border border-slate-800 text-slate-300 overflow-x-auto">
            {JSON.stringify(dbData, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
