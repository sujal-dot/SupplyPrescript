import React from 'react';
import {
  Filter,
  RotateCcw,
  Calendar,
  Layers,
  CheckCircle2,
  DollarSign,
  Search,
  Truck,
} from 'lucide-react';

export default function ROIFilters({
  filters = {},
  onFilterChange = () => {},
  onReset = () => {},
  loading = false,
}) {
  const handleChange = (field, value) => {
    onFilterChange({
      ...filters,
      [field]: value === '' ? undefined : value,
      page: 1, // Reset to page 1 on filter modification
    });
  };

  const handlePreset = (days) => {
    if (!days) {
      onFilterChange({
        ...filters,
        start_date: undefined,
        end_date: undefined,
        page: 1,
      });
      return;
    }
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - days);
    onFilterChange({
      ...filters,
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
      page: 1,
    });
  };

  const hasActiveFilters = Boolean(
    filters.strategy ||
    filters.decision_status ||
    filters.shipment_id ||
    filters.supplier ||
    filters.start_date ||
    filters.end_date ||
    (filters.currency && filters.currency !== 'USD')
  );

  return (
    <div className="glass-card p-5 rounded-2xl border border-white/[0.08] mb-6 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <Filter className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">ROI Analytics Filters</h3>
            <p className="text-xs text-slate-400">Filter closed-loop performance by timeframe, strategy, or outcome</p>
          </div>
        </div>

        {/* Quick Date Presets */}
        <div className="flex items-center space-x-1.5 self-start sm:self-auto">
          <button
            type="button"
            onClick={() => handlePreset(7)}
            className="px-2.5 py-1 text-xs rounded-lg font-medium bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08] transition-colors"
          >
            7 Days
          </button>
          <button
            type="button"
            onClick={() => handlePreset(30)}
            className="px-2.5 py-1 text-xs rounded-lg font-medium bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08] transition-colors"
          >
            30 Days
          </button>
          <button
            type="button"
            onClick={() => handlePreset(null)}
            className="px-2.5 py-1 text-xs rounded-lg font-medium bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 border border-white/[0.08] transition-colors"
          >
            All Time
          </button>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center space-x-1 px-2.5 py-1 text-xs rounded-lg font-medium bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition-colors ml-1"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
        {/* Strategy Filter */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <Layers className="h-3.5 w-3.5 text-red-400" />
            <span>Operational Strategy</span>
          </label>
          <select
            value={filters.strategy || ''}
            onChange={(e) => handleChange('strategy', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
          >
            <option value="">All Strategies</option>
            <option value="AIR_FREIGHT">Air Freight Expedite</option>
            <option value="SECONDARY_SUPPLIER">Secondary Supplier</option>
            <option value="SPLIT_SHIPMENT">Split Shipment</option>
            <option value="EXPEDITE">Expedite Production</option>
            <option value="DELAY_LAUNCH">Delay Launch</option>
            <option value="BUFFER_STOCK">Buffer Stock Reallocation</option>
          </select>
        </div>

        {/* Outcome / Evaluation Status Filter */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            <span>Outcome Classification</span>
          </label>
          <select
            value={filters.decision_status || ''}
            onChange={(e) => handleChange('decision_status', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
          >
            <option value="">All Outcome Statuses</option>
            <option value="SUCCESS">Successful (Within Target)</option>
            <option value="PARTIAL_SUCCESS">Partially Successful (Acceptable Trade-off)</option>
            <option value="FAILURE">Failed (Overrun / Constraint Miss)</option>
            <option value="PENDING_REVIEW">Pending Review (Awaiting Actuals)</option>
            <option value="RECORDED">Operational Status: RECORDED</option>
          </select>
        </div>

        {/* Date From */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <Calendar className="h-3.5 w-3.5 text-red-400" />
            <span>Start Date</span>
          </label>
          <input
            type="date"
            value={filters.start_date || ''}
            onChange={(e) => handleChange('start_date', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
          />
        </div>

        {/* Date To */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <Calendar className="h-3.5 w-3.5 text-red-400" />
            <span>End Date</span>
          </label>
          <input
            type="date"
            value={filters.end_date || ''}
            onChange={(e) => handleChange('end_date', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
          />
        </div>

        {/* Shipment ID Search */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <Search className="h-3.5 w-3.5 text-violet-400" />
            <span>Shipment ID</span>
          </label>
          <input
            type="text"
            placeholder="e.g. SHIP000005"
            value={filters.shipment_id || ''}
            onChange={(e) => handleChange('shipment_id', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
          />
        </div>

        {/* Supplier ID Search */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <Truck className="h-3.5 w-3.5 text-amber-400" />
            <span>Supplier</span>
          </label>
          <input
            type="text"
            placeholder="e.g. SUP001"
            value={filters.supplier || ''}
            onChange={(e) => handleChange('supplier', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
          />
        </div>

        {/* Currency Filter */}
        <div>
          <label className="block text-slate-400 font-medium mb-1.5 flex items-center space-x-1.5">
            <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
            <span>Currency Isolation</span>
          </label>
          <select
            value={filters.currency || 'USD'}
            onChange={(e) => handleChange('currency', e.target.value)}
            disabled={loading}
            className="w-full bg-slate-900/80 border border-white/10 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-red-500 transition-colors"
          >
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
            <option value="INR">INR (₹)</option>
            <option value="GBP">GBP (£)</option>
          </select>
        </div>
      </div>
    </div>
  );
}
