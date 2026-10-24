import React from 'react';
import { TrendingUp, HelpCircle, AlertCircle, ShieldCheck } from 'lucide-react';

export default function ROIBreakdown({ roi = {}, currency = 'USD' }) {
  const { investment_cost, net_benefit, roi_percentage, status = 'UNAVAILABLE', reason } = roi;

  const isCalculated = status === 'CALCULATED' && roi_percentage != null;

  const formatMoney = (val) => {
    if (val == null) return '—';
    const num = Number(val);
    const sign = num > 0 ? '+' : num < 0 ? '-' : '';
    return `${sign}$${Math.abs(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
  };

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-4">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <TrendingUp className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white font-mono uppercase tracking-wider">
              Return on Investment (ROI)
            </h4>
            <p className="text-[11px] text-slate-400">
              Incremental net benefit relative to documented investment cost base
            </p>
          </div>
        </div>

        <span
          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
            isCalculated
              ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}
        >
          {status}
        </span>
      </div>

      {/* Main Metric Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
        <div>
          <span className="text-[10px] font-mono uppercase text-slate-400 block">
            ROI Percentage
          </span>
          <div className="text-xl font-mono font-bold mt-0.5">
            {isCalculated ? (
              <span className={roi_percentage >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
                {roi_percentage > 0 ? `+${roi_percentage}%` : `${roi_percentage}%`}
              </span>
            ) : (
              <span className="text-slate-500">N/A</span>
            )}
          </div>
        </div>

        <div>
          <span className="text-[10px] font-mono uppercase text-slate-400 block">
            Net Decision Benefit
          </span>
          <div className="text-sm font-mono font-bold text-slate-200 mt-1">
            {net_benefit != null ? formatMoney(net_benefit) : '—'}
          </div>
        </div>

        <div>
          <span className="text-[10px] font-mono uppercase text-slate-400 block">
            Investment Denominator
          </span>
          <div className="text-sm font-mono font-bold text-slate-200 mt-1">
            {investment_cost != null ? formatMoney(investment_cost) : '—'}
          </div>
        </div>
      </div>

      {/* Transparent Explanation */}
      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start space-x-2 text-xs">
        <HelpCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-0.5">
          <strong className="text-slate-300 font-mono text-[11px] block">
            Financial Methodology & Policy Reason:
          </strong>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {reason || 'ROI is calculated only when a valid documented baseline and positive incremental investment denominator are recorded.'}
          </p>
        </div>
      </div>
    </div>
  );
}
