import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  History,
  AlertCircle,
  RefreshCw,
  Cpu,
  Clock,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { predictShipment, getPredictions, formatApiError } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import GlassButton from '../components/ui/GlassButton';
import StatusBadge from '../components/ui/StatusBadge';
import PredictionForm from '../components/predictions/PredictionForm';
import PredictionResult from '../components/predictions/PredictionResult';

export default function Predictions() {
  const [predictionResult, setPredictionResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState(null);

  // Recent predictions history
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(null);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState(null);

  const fetchRecentPredictions = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await getPredictions({ page: 1, page_size: 15 });
      setRecentPredictions(res?.data || []);
    } catch (err) {
      console.warn('Could not load prediction history:', err);
      setHistoryError(formatApiError(err));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentPredictions();
  }, []);

  const handlePredictSubmit = async (payload) => {
    setLoading(true);
    setFormError(null);
    try {
      const result = await predictShipment(payload);
      setPredictionResult(result);
      // Refresh history to see newly evaluated or stored predictions
      fetchRecentPredictions();
    } catch (err) {
      console.error('Prediction failed:', err);
      setFormError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 pb-10">
      <PageHeader
        title="Shipment Delay Risk Prediction Workspace"
        subtitle="Execute active dual XGBoost classification and regression inference using authoritative database features."
        actions={
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono px-3 py-1.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">
              Active Model: v1.0 XGBoost
            </span>
            <Link
              to="/feedback"
              className="flex items-center space-x-1.5 text-xs font-mono px-3 py-1.5 rounded-xl bg-violet-500/15 border border-violet-400/30 text-violet-300 hover:bg-violet-500/25 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Feedback Pipeline</span>
            </Link>
            <GlassButton
              variant="secondary"
              size="md"
              icon={RefreshCw}
              loading={historyLoading}
              onClick={fetchRecentPredictions}
            >
              Refresh History
            </GlassButton>
          </div>
        }
      />

      {/* Main Prediction Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: 7 cols */}
        <div className="lg:col-span-7">
          <PredictionForm
            onSubmit={handlePredictSubmit}
            loading={loading}
            error={formError}
          />
        </div>

        {/* Right Result: 5 cols */}
        <div className="lg:col-span-5">
          <PredictionResult result={predictionResult} />
        </div>
      </div>

      {/* Recent Model Predictions History Table */}
      <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
        <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
              <History className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">
                Stored Model Predictions Log
              </h3>
              <p className="text-xs text-slate-400">
                Authoritative predictions stored in PostgreSQL database
              </p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {recentPredictions.length} Records
          </span>
        </div>

        {historyLoading ? (
          <div className="p-6 space-y-3 animate-pulse">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-white/5 rounded-xl w-full" />
            ))}
          </div>
        ) : recentPredictions.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-xs">
            No stored prediction records found in the database.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono uppercase text-[11px]">
                  <th className="py-3 px-4 font-semibold">Prediction ID</th>
                  <th className="py-3 px-4 font-semibold">Shipment ID</th>
                  <th className="py-3 px-4 font-semibold">Supplier</th>
                  <th className="py-3 px-4 font-semibold">Product</th>
                  <th className="py-3 px-4 font-semibold">Delay Probability</th>
                  <th className="py-3 px-4 font-semibold">Predicted Delay</th>
                  <th className="py-3 px-4 font-semibold">Risk Level</th>
                  <th className="py-3 px-4 font-semibold">Model Version</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {recentPredictions.map((pred) => {
                  const prob = Number(pred.prediction_probability) || 0;
                  const probPct = Math.round(prob * 100);
                  const days = Number(pred.predicted_value) || 0;
                  const riskLevel = pred.risk || 'LOW';

                  return (
                    <tr
                      key={pred.id || pred.prediction_id}
                      className="hover:bg-white/[0.03] transition-colors"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-red-300">
                        {pred.prediction_id}
                      </td>
                      <td className="py-3 px-4 font-mono text-white">
                        {pred.shipment_id}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {pred.supplier_id || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {pred.product_id || '—'}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        <span
                          className={`font-bold ${
                            riskLevel === 'HIGH'
                              ? 'text-rose-400'
                              : riskLevel === 'MEDIUM'
                              ? 'text-amber-400'
                              : 'text-emerald-400'
                          }`}
                        >
                          {probPct}%
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-200">
                        +{days.toFixed(1)} days
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge
                          status={riskLevel}
                          variant={
                            riskLevel === 'HIGH'
                              ? 'error'
                              : riskLevel === 'MEDIUM'
                              ? 'warning'
                              : 'success'
                          }
                          dot={true}
                        />
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-400">
                        {pred.model_version || 'v1.0'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-white/[0.04] text-slate-300">
                          {pred.prediction_status || 'Generated'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
