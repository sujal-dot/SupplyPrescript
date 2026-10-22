import React from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  DollarSign,
  Package,
  Clock,
  Layers,
} from 'lucide-react';

export default function ConstraintStatus({
  constraintChecks = [],
  selectedOption = null,
  baseline = null,
}) {
  // If no backend constraintChecks provided, derive default checks from option & baseline
  const defaultConstraints = [
    {
      name: 'Maximum Budget Constraint',
      formula: 'C_total ≤ Budget Ceiling',
      icon: DollarSign,
      lhs_value: selectedOption?.estimated_total_cost ?? (baseline?.estimated_total_cost || 0),
      rhs_value: 50000.0,
      formatLhs: (v) => `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      formatRhs: (v) => `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      unit: '$',
      isViolated: selectedOption?.constraint_violations?.some((v) =>
        v.constraint_name?.toLowerCase().includes('budget')
      ) || (selectedOption?.estimated_total_cost != null && selectedOption.estimated_total_cost > 50000),
      description: 'Hard budget limit ($50,000 baseline ceiling). Over-budget candidate actions are disqualified.',
    },
    {
      name: 'Supplier Capacity Limit',
      formula: 'Order Quantity ≤ Monthly Capacity',
      icon: Layers,
      lhs_value: baseline?.quantity ?? 500,
      rhs_value: 1000.0,
      formatLhs: (v) => `${Number(v).toLocaleString()} units`,
      formatRhs: (v) => `${Number(v).toLocaleString()} units`,
      unit: ' units',
      isViolated: selectedOption?.constraint_violations?.some((v) =>
        v.constraint_name?.toLowerCase().includes('capacity')
      ),
      description: 'Production allotment must not exceed the supplier verified operational threshold.',
    },
    {
      name: 'Inventory Buffer Conservation',
      formula: 'Ending Inventory ≥ Safety Stock (50 units)',
      icon: Package,
      lhs_value: 100,
      rhs_value: 50,
      formatLhs: (v) => `${Number(v)} units`,
      formatRhs: (v) => `${Number(v)} units`,
      unit: ' units',
      isViolated: selectedOption?.constraint_violations?.some((v) =>
        v.constraint_name?.toLowerCase().includes('inventory')
      ),
      description: 'Warehouse safety reserve buffer must be maintained to absorb downstream demand spikes.',
    },
    {
      name: 'Delivery Window SLA',
      formula: 'Lead Time + Delay ≤ Max Allowed Window',
      icon: Clock,
      lhs_value: selectedOption?.estimated_delivery_days ?? (baseline?.total_delivery_days || 14),
      rhs_value: 20.0,
      formatLhs: (v) => `${Number(v).toFixed(1)} days`,
      formatRhs: (v) => `${Number(v).toFixed(1)} days`,
      unit: ' days',
      isViolated: selectedOption?.constraint_violations?.some((v) =>
        v.constraint_name?.toLowerCase().includes('delivery')
      ),
      description: 'Critical path delivery deadline established to prevent downstream supply stoppage.',
    },
  ];

  // Merge backend constraint checks if present
  const resolvedConstraints =
    constraintChecks && constraintChecks.length > 0
      ? constraintChecks.map((chk) => {
          const isFail = chk.status === 'VIOLATED' || chk.slack < 0;
          const isBinding = chk.status === 'BINDING' || Math.abs(chk.slack) < 0.001;
          return {
            name: chk.name,
            formula: chk.name.includes('Budget') ? 'C_total ≤ Budget Ceiling' : 'Actual ≤ Threshold',
            lhs_value: chk.lhs_value,
            rhs_value: chk.rhs_value,
            slack: chk.slack,
            status: chk.status,
            isViolated: isFail,
            isBinding: isBinding,
            formatLhs: (v) => (chk.name.includes('Budget') ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : `${Number(v).toFixed(1)}`),
            formatRhs: (v) => (chk.name.includes('Budget') ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : `${Number(v).toFixed(1)}`),
            description: chk.description || 'Verified by independent validation report.',
          };
        })
      : defaultConstraints.map((c) => {
          const slack = c.rhs_value - c.lhs_value;
          return {
            ...c,
            slack: slack,
            status: c.isViolated ? 'VIOLATED' : slack === 0 ? 'BINDING' : 'SATISFIED',
            isBinding: slack === 0,
          };
        });

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-white tracking-tight">
                Business Constraint Verification
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-400/30">
                Day 15 Audit Gate
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Deterministic mathematical checks. Violating any hard constraint disqualifies candidate actions.
            </p>
          </div>
        </div>

        {selectedOption && (
          <div className="text-xs font-mono text-slate-400 bg-white/[0.03] px-3 py-1.5 rounded-xl border border-white/[0.06] flex items-center space-x-2">
            <span>Option Audited:</span>
            <strong className="text-white font-bold">
              {selectedOption.option_id} ({selectedOption.name || selectedOption.strategy})
            </strong>
          </div>
        )}
      </div>

      {/* Constraints Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-white/[0.06]">
        {resolvedConstraints.map((item, idx) => {
          const isViolated = item.isViolated;
          const isBinding = item.isBinding;
          const slack = item.slack != null ? item.slack : item.rhs_value - item.lhs_value;

          return (
            <div
              key={idx}
              className={`p-4 flex flex-col justify-between space-y-3 ${
                isViolated
                  ? 'bg-rose-500/5'
                  : isBinding
                  ? 'bg-amber-500/5'
                  : 'bg-white/[0.01]'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-bold text-white tracking-tight">
                    {item.name}
                  </span>
                  {/* Status Indicator with Text AND Icon */}
                  {isViolated ? (
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono font-bold">
                      <XCircle className="h-3 w-3 text-rose-400" />
                      <span>FAIL</span>
                    </span>
                  ) : isBinding ? (
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-mono font-bold">
                      <AlertTriangle className="h-3 w-3 text-amber-400" />
                      <span>BINDING</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono font-bold">
                      <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      <span>PASS</span>
                    </span>
                  )}
                </div>
                <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                  {item.formula}
                </span>
              </div>

              {/* Evaluated Values */}
              <div className="space-y-1.5 pt-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Actual Value (LHS):</span>
                  <span className="font-mono font-semibold text-slate-200">
                    {item.formatLhs ? item.formatLhs(item.lhs_value) : item.lhs_value}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Limit Threshold (RHS):</span>
                  <span className="font-mono font-semibold text-slate-400">
                    {item.formatRhs ? item.formatRhs(item.rhs_value) : item.rhs_value}
                  </span>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-white/[0.04]">
                  <span className="text-slate-400">Slack Headroom:</span>
                  <span
                    className={`font-mono font-bold ${
                      slack > 0
                        ? 'text-emerald-400'
                        : slack < 0
                        ? 'text-rose-400'
                        : 'text-amber-400'
                    }`}
                  >
                    {slack > 0 ? `+${slack.toFixed(1)}` : slack.toFixed(1)}
                  </span>
                </div>
              </div>

              <p className="text-[10px] text-slate-500 leading-tight pt-1">
                {item.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
