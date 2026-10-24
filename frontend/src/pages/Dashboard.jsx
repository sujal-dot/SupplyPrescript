import React, { useState, useEffect } from 'react';
import {
  Package,
  Truck,
  TrendingUp,
  AlertTriangle,
  Award,
  RefreshCw,
  Clock,
  ShieldAlert,
  ArrowRight,
  Database,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { getDashboardMetrics, formatApiError } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import GlassButton from '../components/ui/GlassButton';
import MetricCard from '../components/dashboard/MetricCard';
import DelayTrendChart from '../components/dashboard/DelayTrendChart';
import SupplierReliabilityChart from '../components/dashboard/SupplierReliabilityChart';
import ShipmentRiskChart from '../components/dashboard/ShipmentRiskChart';
import RiskTable from '../components/dashboard/RiskTable';

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getDashboardMetrics();
      setMetrics(response.data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Failed to load dashboard metrics:', err);
      setError(formatApiError(err));
      setLastRefreshed(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const totalShipments = metrics?.total_shipments;
  const delayedShipments = metrics?.delayed_shipments;
  const avgDelayDays = metrics?.average_delay_days;
  const avgReliability = metrics?.average_supplier_reliability;
  const highRiskCount = metrics?.risk_distribution?.HIGH ?? (metrics?.high_risk_shipments?.length || 0);
  const totalEvaluatedPredictions = metrics?.risk_distribution
    ? (metrics.risk_distribution.LOW || 0) +
      (metrics.risk_distribution.MEDIUM || 0) +
      (metrics.risk_distribution.HIGH || 0)
    : 0;

  return (
    <div className="space-y-8 pb-10">
      {/* Page Header */}
      <PageHeader
        title="Supply Chain Intelligence Dashboard"
        subtitle="Operational overview of network logistics, real database records, and active machine learning risk assessments."
        lastUpdated={lastRefreshed}
        actions={
          <div className="flex items-center space-x-2">
            <Link to="/predictions">
              <GlassButton variant="primary" size="md">
                New Risk Prediction
              </GlassButton>
            </Link>
            <GlassButton
              variant="secondary"
              size="md"
              icon={RefreshCw}
              loading={loading}
              onClick={fetchDashboard}
            >
              Refresh
            </GlassButton>
          </div>
        }
      />

      {/* Error state banner */}
      {error && (
        <div className="glass-card p-4 rounded-2xl border-rose-400/30 bg-rose-500/10 flex items-start justify-between gap-3">
          <div className="flex items-start space-x-3 text-xs">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-rose-300">Database Connection Notice: </span>
              <span className="text-rose-200/90">{error}</span>
            </div>
          </div>
          <button
            onClick={fetchDashboard}
            className="text-xs font-semibold text-red-400 hover:underline shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI 1: Total Shipments */}
        <MetricCard
          title="Total Shipments"
          value={totalShipments ? Number(totalShipments).toLocaleString() : null}
          subtitle="Authoritative PostgreSQL records"
          unit="orders"
          icon={Truck}
          variant="red"
          loading={loading}
          empty={!totalShipments}
        />

        {/* KPI 2: High-Risk Shipments */}
        <MetricCard
          title="High-Risk Shipments"
          value={highRiskCount !== undefined ? highRiskCount : null}
          subtitle={`From ${totalEvaluatedPredictions} evaluated predictions`}
          unit="flagged"
          icon={ShieldAlert}
          variant="rose"
          loading={loading}
          empty={highRiskCount === null || highRiskCount === undefined}
          badge="ML ≥70%"
        />

        {/* KPI 3: Delayed Shipments */}
        <MetricCard
          title="Delayed Shipments"
          value={delayedShipments ? Number(delayedShipments).toLocaleString() : null}
          subtitle={
            metrics?.delay_rate !== undefined
              ? `${Math.round(metrics.delay_rate * 100)}% historical delay rate`
              : 'Historical delayed outcomes'
          }
          unit="shipments"
          icon={AlertTriangle}
          variant="amber"
          loading={loading}
          empty={!delayedShipments}
        />

        {/* KPI 4: Average Supplier Reliability */}
        <MetricCard
          title="Avg Supplier Reliability"
          value={
            avgReliability !== undefined && avgReliability !== null
              ? `${Math.round(avgReliability * 1000) / 10}%`
              : null
          }
          subtitle={`Across ${metrics?.total_suppliers || 50} contracted suppliers`}
          icon={Award}
          variant="emerald"
          loading={loading}
          empty={avgReliability === null || avgReliability === undefined}
        />

        {/* KPI 5: Average Delay Days */}
        <MetricCard
          title="Average Delay Days"
          value={avgDelayDays !== undefined ? `${Number(avgDelayDays).toFixed(2)}` : null}
          subtitle="Empirical average duration"
          unit="days"
          icon={Clock}
          variant="blue"
          loading={loading}
          empty={avgDelayDays === null || avgDelayDays === undefined}
        />
      </div>

      {/* Charts Grid: Delay Trends and Supplier Reliability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DelayTrendChart
          data={metrics?.delay_trends || []}
          loading={loading}
          height={280}
        />
        <SupplierReliabilityChart
          data={metrics?.supplier_reliability_rankings || []}
          loading={loading}
          height={280}
        />
      </div>

      {/* Risk Distribution Chart & High-Risk Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ShipmentRiskChart
            distribution={metrics?.risk_distribution}
            loading={loading}
            height={280}
          />
        </div>
        <div className="lg:col-span-2">
          <RiskTable
            shipments={metrics?.high_risk_shipments || []}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
