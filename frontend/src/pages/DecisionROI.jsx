import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp,
  RefreshCw,
  Download,
  AlertTriangle,
  FileCheck2,
  SlidersHorizontal,
  Info,
  CheckCircle2,
} from 'lucide-react';
import GlassButton from '../components/ui/GlassButton';
import ROIFilters from '../components/roi/ROIFilters';
import ROISummaryCards from '../components/roi/ROISummaryCards';
import DecisionSuccessChart from '../components/roi/DecisionSuccessChart';
import CostDifferenceChart from '../components/roi/CostDifferenceChart';
import PredictionAccuracyChart from '../components/roi/PredictionAccuracyChart';
import SavingsChart from '../components/roi/SavingsChart';
import ROIByStrategyChart from '../components/roi/ROIByStrategyChart';
import DecisionPerformanceTable from '../components/roi/DecisionPerformanceTable';
import DecisionDetailModal from '../components/dashboard/DecisionDetailModal';
import { getDecisionROIAnalytics } from '../services/roiService';

export default function DecisionROI() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter state
  const [filters, setFilters] = useState({
    page: 1,
    page_size: 20,
    currency: 'USD',
  });

  // Modal inspection state
  const [selectedDecisionId, setSelectedDecisionId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getDecisionROIAnalytics(filters);
      setData(res);
    } catch (err) {
      console.error('Failed to load Decision ROI analytics:', err);
      setError(err?.response?.data?.detail || err.message || 'Failed to fetch Decision ROI analytics');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
  };

  const handleResetFilters = () => {
    setFilters({
      page: 1,
      page_size: 20,
      currency: 'USD',
    });
  };

  const handlePageChange = (newPage) => {
    setFilters((prev) => ({
      ...prev,
      page: newPage,
    }));
  };

  const handleSelectDecision = (row) => {
    if (row && (row.decision_id || row.db_id)) {
      setSelectedDecisionId(row.decision_id || row.db_id);
      setIsModalOpen(true);
    }
  };

  const handleExportJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `decision_roi_audit_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const summary = data?.summary || {};
  const predictionAccuracy = data?.prediction_accuracy || {};
  const successBreakdown = data?.success_breakdown || [];
  const costDiffByStrategy = data?.cost_difference_by_strategy || [];
  const roiByStrategy = data?.roi_by_strategy || [];
  const savingsTimeline = data?.savings_timeline || [];
  const performanceTable = data?.performance_table || {};
  const dataQuality = data?.data_quality || {};

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-2 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-red-500/15 border border-red-500/30 text-red-300 shadow-lg shadow-red-500/10">
              <TrendingUp className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  Decision ROI
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                  Closed-Loop Phase 6
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
                Audit recommendation success, failure rates, cost differences, prediction accuracy, and verified financial return
              </p>
            </div>
          </div>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center space-x-3 self-start md:self-auto">
          <GlassButton
            onClick={fetchAnalytics}
            variant="ghost"
            disabled={loading}
            className="flex items-center space-x-2 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </GlassButton>
          <GlassButton
            onClick={handleExportJSON}
            variant="primary"
            disabled={loading || !data}
            className="flex items-center space-x-2 text-xs"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export Audit Data</span>
          </GlassButton>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start space-x-3 text-sm">
          <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block">Failed to load analytics</span>
            <span className="text-xs text-rose-400/80">{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchAnalytics}
            className="px-2.5 py-1 text-xs font-medium rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-white transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. Date-Range & Strategy Filters */}
      <ROIFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
        loading={loading}
      />

      {/* 3. KPI Summary Cards */}
      <ROISummaryCards
        summary={summary}
        currency={filters.currency || 'USD'}
        loading={loading}
      />

      {/* Visual Analytics Charts Grid: Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 4. Chart 1 — Successful vs Failed Decisions */}
        <DecisionSuccessChart
          breakdown={successBreakdown}
          summary={summary}
          loading={loading}
          height={320}
        />

        {/* 5. Chart 2 — Average Cost Difference */}
        <CostDifferenceChart
          strategyCostDifferences={costDiffByStrategy}
          currency={filters.currency || 'USD'}
          loading={loading}
          height={320}
        />
      </div>

      {/* Visual Analytics Charts Grid: Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 6. Chart 3 — Prediction Accuracy Chart */}
        <PredictionAccuracyChart
          accuracy={predictionAccuracy}
          currency={filters.currency || 'USD'}
          loading={loading}
          height={320}
        />

        {/* 7. Chart 4 — Cumulative Savings Timeline */}
        <SavingsChart
          timeline={savingsTimeline}
          currency={filters.currency || 'USD'}
          loading={loading}
          height={320}
        />
      </div>

      {/* 8. Chart 5 — ROI by Strategy Chart */}
      <ROIByStrategyChart
        strategyROI={roiByStrategy}
        currency={filters.currency || 'USD'}
        loading={loading}
        height={300}
      />

      {/* 9. Decision Performance Table */}
      <DecisionPerformanceTable
        performancePage={performanceTable}
        onPageChange={handlePageChange}
        onSelectDecision={handleSelectDecision}
        currency={filters.currency || 'USD'}
        loading={loading}
      />

      {/* 10. Data Completeness & Calculation Methodology */}
      <div className="glass-card p-6 rounded-2xl border border-white/[0.08] space-y-4">
        <div className="flex items-center space-x-2.5 pb-3 border-b border-white/[0.06]">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <FileCheck2 className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Data Completeness & Calculation Methodology
            </h3>
            <p className="text-xs text-slate-400">
              Audit trail standards, mathematical definitions, and non-distorting denominator policies
            </p>
          </div>
          <span className="ml-auto text-[11px] font-mono text-slate-400 bg-white/[0.04] px-2.5 py-1 rounded-lg border border-white/[0.06]">
            Methodology v{dataQuality.calculation_version || '1.0'}
          </span>
        </div>

        {/* Completeness Counts */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">In Filter Scope</span>
            <span className="text-lg font-bold font-mono text-white mt-1 block">
              {dataQuality.total_in_filter ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">Matching criteria</span>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">Cost Actuals</span>
            <span className="text-lg font-bold font-mono text-red-400 mt-1 block">
              {dataQuality.completed_with_valid_costs ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">With verified costs</span>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">Delay Actuals</span>
            <span className="text-lg font-bold font-mono text-rose-400 mt-1 block">
              {dataQuality.completed_with_valid_delays ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">With delivery dates</span>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">Documented Baselines</span>
            <span className="text-lg font-bold font-mono text-emerald-400 mt-1 block">
              {dataQuality.decisions_with_valid_baseline ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">Eligible for savings</span>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">Excluded Currency</span>
            <span className="text-lg font-bold font-mono text-amber-400 mt-1 block">
              {dataQuality.excluded_currency_mismatches ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">Non-{filters.currency || 'USD'} records</span>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
            <span className="text-slate-400 text-[10px] uppercase tracking-wider block">Excluded Missing Data</span>
            <span className="text-lg font-bold font-mono text-rose-400 mt-1 block">
              {dataQuality.excluded_missing_data ?? 0}
            </span>
            <span className="text-[10px] text-slate-500">Pending or incomplete</span>
          </div>
        </div>

        {/* Notes List */}
        <div className="p-4 rounded-xl bg-slate-900/50 border border-white/5 text-xs text-slate-400 space-y-2">
          <div className="font-semibold text-slate-200 flex items-center space-x-1.5">
            <Info className="h-4 w-4 text-red-400" />
            <span>Operational Accounting Principles:</span>
          </div>
          <ul className="list-disc pl-5 space-y-1 text-slate-400 text-[11px]">
            {dataQuality.methodology_notes?.map((note, idx) => (
              <li key={idx}>{note}</li>
            )) || (
              <>
                <li>Cost difference = actual_cost − predicted_cost (positive = overrun, negative = under budget).</li>
                <li>Success rate denominator strictly excludes pending review decisions to prevent undercounting actual recommendation success.</li>
                <li>Verified baseline savings requires a documented, comparable shipment baseline ((quantity * unit_cost) + shipping_cost).</li>
                <li>Portfolio ROI is calculated as weighted aggregate net benefit / incremental investment, never as an unweighted average of individual percentages.</li>
              </>
            )}
          </ul>
        </div>
      </div>

      {/* Decision Detail Modal (Day 20 Integration) */}
      {isModalOpen && selectedDecisionId && (
        <DecisionDetailModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedDecisionId(null);
          }}
          decisionId={selectedDecisionId}
          initialTab="roi"
        />
      )}
    </div>
  );
}
