import React from 'react';
import {
  Truck,
  AlertTriangle,
  Clock,
  Sparkles,
  Package,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import MetricCard from './MetricCard';

export default function RiskMetrics({ metrics = null, loading = false }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="glass-card p-5 rounded-2xl border border-white/[0.08] animate-pulse h-28"
          />
        ))}
      </div>
    );
  }

  const totalShipments = metrics?.total_shipments ?? 0;
  const delayedShipments = metrics?.delayed_shipments ?? 0;
  const delayRate = metrics?.delay_rate ? (metrics.delay_rate * 100).toFixed(1) : '0.0';
  const highRiskCount =
    metrics?.risk_distribution?.HIGH ?? (metrics?.high_risk_shipments?.length || 0);
  const avgDelayDays = metrics?.average_delay_days != null ? Number(metrics.average_delay_days).toFixed(1) : '0.0';
  const shortageCount = metrics?.inventory_shortage_count ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. Total Active Shipments */}
      <MetricCard
        title="Total Active Shipments"
        label="Total Active Shipments"
        value={totalShipments.toLocaleString()}
        icon={Truck}
        variant="cyan"
        subtitle="PostgreSQL Registry"
      />

      {/* 2. High-Risk Shipments */}
      <MetricCard
        title="High-Risk Shipments"
        label="High-Risk Shipments"
        value={highRiskCount.toString()}
        icon={AlertTriangle}
        variant={highRiskCount > 0 ? 'rose' : 'emerald'}
        subtitle={highRiskCount > 0 ? 'Urgent Review' : 'Optimal'}
      />

      {/* 3. Delayed Shipments */}
      <MetricCard
        title="Predicted Delayed"
        label="Predicted Delayed"
        value={delayedShipments.toLocaleString()}
        icon={Clock}
        variant={delayedShipments > 0 ? 'amber' : 'emerald'}
        subtitle={`${delayRate}% Network Rate`}
      />

      {/* 4. Average Transit Delay */}
      <MetricCard
        title="Avg Delay Duration"
        label="Avg Delay Duration"
        value={`+${avgDelayDays} d`}
        icon={TrendingUp}
        variant={Number(avgDelayDays) > 3 ? 'amber' : 'cyan'}
        subtitle="ML Empirical Mean"
      />

      {/* 5. Inventory Shortage Alerts */}
      <MetricCard
        title="Inventory At Risk"
        label="Inventory At Risk"
        value={shortageCount.toString()}
        icon={Package}
        variant={shortageCount > 0 ? 'amber' : 'emerald'}
        subtitle={shortageCount > 0 ? 'Under Buffer Target' : 'Adequate Safety'}
      />
    </div>
  );
}
