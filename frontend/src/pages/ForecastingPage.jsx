import React, { useState } from 'react';
import { 
  TrendingUp, 
  Filter, 
  Calendar, 
  Cpu, 
  CheckCircle2, 
  Download, 
  Layers,
  ArrowUpRight
} from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import GlassCard from '../components/ui/GlassCard';
import GlassPanel from '../components/ui/GlassPanel';
import GlassButton from '../components/ui/GlassButton';
import { GlassSelect, GlassInput } from '../components/ui/GlassInput';
import StatusBadge from '../components/ui/StatusBadge';
import DataChart from '../components/ui/DataChart';

export default function ForecastingPage() {
  const [horizon, setHorizon] = useState('30d');
  const [selectedProduct, setSelectedProduct] = useState('PROD-ALL');
  const [selectedCategory, setSelectedCategory] = useState('Electronics');

  // Simulated dataset for forecast horizons
  const horizonData = {
    '7d': [
      { label: 'Day 1', value1: 120, value2: 118 },
      { label: 'Day 2', value1: 135, value2: 132 },
      { label: 'Day 3', value1: 140, value2: 144 },
      { label: 'Day 4', value1: 128, value2: 130 },
      { label: 'Day 5', value1: 165, value2: 160 },
      { label: 'Day 6', value1: 172, value2: 175 },
      { label: 'Day 7', value1: 180, value2: 185 },
    ],
    '14d': [
      { label: 'D1', value1: 120, value2: 118 },
      { label: 'D3', value1: 140, value2: 144 },
      { label: 'D5', value1: 165, value2: 160 },
      { label: 'D7', value1: 180, value2: 185 },
      { label: 'D9', value1: 195, value2: 190 },
      { label: 'D11', value1: 210, value2: 215 },
      { label: 'D14', value1: 230, value2: 228 },
    ],
    '30d': [
      { label: 'W1', value1: 820, value2: 810 },
      { label: 'W2', value1: 910, value2: 890 },
      { label: 'W3', value1: 880, value2: 905 },
      { label: 'W4', value1: 1040, value2: 1020 },
      { label: 'W5', value1: 1120, value2: 1100 },
      { label: 'W6', value1: 1180, value2: 1210 },
    ],
    '90d': [
      { label: 'M1', value1: 3400, value2: 3350 },
      { label: 'M2', value1: 3950, value2: 3900 },
      { label: 'M3', value1: 4200, value2: 4310 },
    ],
  };

  const currentChartData = horizonData[horizon] || horizonData['30d'];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Predictive Demand Forecasting"
        subtitle="Gradient boosted regression forecasting with cross-validated seasonality, trend decomposition, and confidence envelopes."
        breadcrumbs={[{ label: 'Demand Forecasting' }]}
        actions={
          <div className="flex items-center space-x-2">
            <GlassButton variant="outline" size="md" icon={Download}>
              Export Matrix
            </GlassButton>
          </div>
        }
      />

      {/* Model Performance Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <GlassCard interactive glow="cyan" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Model MAPE</span>
            <StatusBadge status="Optimal" variant="success" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">4.18%</div>
          <p className="text-xs text-slate-400 mt-2">Mean Absolute Percentage Error</p>
        </GlassCard>

        <GlassCard interactive glow="blue" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">R² Fit Score</span>
            <StatusBadge status="95.4%" variant="info" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">0.954</div>
          <p className="text-xs text-slate-400 mt-2">Variance explained by features</p>
        </GlassCard>

        <GlassCard interactive glow="emerald" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Forecast RMSE</span>
            <StatusBadge status="Low Drift" variant="success" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">18.42</div>
          <p className="text-xs text-slate-400 mt-2">Root Mean Squared Error (Units)</p>
        </GlassCard>

        <GlassCard interactive glow="amber" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Confidence Level</span>
            <StatusBadge status="95% CI" variant="info" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">&plusmn; 4.6%</div>
          <p className="text-xs text-slate-400 mt-2">Prediction interval bandwidth</p>
        </GlassCard>
      </div>

      {/* Filter and Control Bar */}
      <GlassCard className="p-5 rounded-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 items-end">
          <GlassSelect
            label="Product SKU"
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            options={[
              { value: 'PROD-ALL', label: 'All Primary SKUs (Aggregated)' },
              { value: 'PROD-001', label: 'PROD-001 — Solid State Memory Unit' },
              { value: 'PROD-002', label: 'PROD-002 — Optical Sensor Assembly' },
              { value: 'PROD-003', label: 'PROD-003 — Lithium Power Cell' },
            ]}
          />

          <GlassSelect
            label="Product Category"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            options={[
              { value: 'Electronics', label: 'Electronics & Semiconductors' },
              { value: 'Automotive', label: 'Automotive Components' },
              { value: 'Industrial', label: 'Industrial Automation' },
            ]}
          />

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Forecast Horizon
            </label>
            <div className="flex items-center space-x-1.5 bg-[#0B1426] p-1 rounded-xl border border-white/10">
              {['7d', '14d', '30d', '90d'].map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizon(h)}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    horizon === h
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>

          <div>
            <GlassButton variant="primary" size="md" className="w-full" icon={Cpu}>
              Retrain Horizon
            </GlassButton>
          </div>
        </div>
      </GlassCard>

      {/* Main Glass Forecast Chart */}
      <GlassPanel
        title="Demand Trajectory vs XGBoost Machine Learning Forecast"
        subtitle={`Displaying historical demand cycles and forward-looking predictions for ${horizon} horizon`}
        icon={TrendingUp}
      >
        <DataChart
          data={currentChartData}
          series={[
            { key: 'value1', label: 'Historical Actual Demand', color: '#22D3EE' },
            { key: 'value2', label: 'ML Projected Demand', color: '#3B82F6', dashed: true },
          ]}
          height={320}
          unit=" units"
        />
      </GlassPanel>

      {/* Historical Breakdown Table */}
      <GlassPanel
        title="SKU Demand Projection Breakdown"
        subtitle="Segmented forecast volume and projected safety buffer impact"
        icon={Layers}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                <th className="pb-3 pl-2">Product Code</th>
                <th className="pb-3">Category</th>
                <th className="pb-3">Current Demand</th>
                <th className="pb-3">Projected Demand</th>
                <th className="pb-3">Trend Variance</th>
                <th className="pb-3">Recommended Buffer</th>
                <th className="pb-3 text-right pr-2">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {[
                { sku: 'PROD-001', cat: 'Electronics', curr: 820, proj: 940, diff: '+14.6%', buffer: '+120 units', conf: '96.2%' },
                { sku: 'PROD-002', cat: 'Sensors', curr: 450, proj: 470, diff: '+4.4%', buffer: '+35 units', conf: '94.8%' },
                { sku: 'PROD-003', cat: 'Power', curr: 1200, proj: 1140, diff: '-5.0%', buffer: 'Maintain', conf: '97.1%' },
                { sku: 'PROD-004', cat: 'Modules', curr: 310, proj: 380, diff: '+22.5%', buffer: '+80 units', conf: '91.4%' },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 pl-2 font-mono text-cyan-300 font-semibold">
                    {row.sku}
                  </td>
                  <td className="py-3 text-slate-300">{row.cat}</td>
                  <td className="py-3 text-slate-300">{row.curr}</td>
                  <td className="py-3 text-white font-medium">{row.proj}</td>
                  <td className="py-3">
                    <span
                      className={
                        row.diff.startsWith('+') ? 'text-emerald-400' : 'text-slate-400'
                      }
                    >
                      {row.diff}
                    </span>
                  </td>
                  <td className="py-3 font-mono text-slate-300">{row.buffer}</td>
                  <td className="py-3 text-right pr-2">
                    <StatusBadge status={row.conf} variant="info" dot={false} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </div>
  );
}
