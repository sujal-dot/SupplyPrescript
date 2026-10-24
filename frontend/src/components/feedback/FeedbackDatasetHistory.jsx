import React, { useState } from 'react';
import {
  Database,
  Hash,
  Check,
  Copy,
  Calendar,
  Layers,
  FileCheck,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';

export default function FeedbackDatasetHistory({
  datasets = [],
  activeDatasetFilter = '',
  onSelectDataset = () => {},
  loading = false,
}) {
  const [copiedHash, setCopiedHash] = useState(null);

  const handleCopyHash = (hash, version) => {
    navigator.clipboard?.writeText(hash);
    setCopiedHash(version);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  return (
    <div className="glass-card rounded-2xl border border-white/[0.08] overflow-hidden mb-6">
      {/* Header */}
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-400/30 text-emerald-300">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Versioned Feedback Datasets & Cryptographic Manifests
            </h3>
            <p className="text-xs text-slate-400">
              Immutable snapshots exported with SHA-256 checksums for traceable model retraining
            </p>
          </div>
        </div>
        <div className="text-xs font-mono text-slate-400">
          {datasets.length} {datasets.length === 1 ? 'snapshot' : 'snapshots'}
        </div>
      </div>

      {/* Manifests list */}
      <div className="p-5">
        {loading ? (
          <div className="py-8 text-center text-slate-400">
            <div className="animate-spin h-6 w-6 border-2 border-emerald-400 border-t-transparent rounded-full mx-auto mb-2" />
            <span className="text-xs">Loading dataset manifests...</span>
          </div>
        ) : datasets.length === 0 ? (
          <div className="py-6 text-center text-slate-500">
            <AlertCircle className="h-6 w-6 text-slate-600 mx-auto mb-1.5" />
            <p className="text-xs font-medium text-slate-400">No Exported Snapshots Yet</p>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-0.5">
              Click &quot;Generate Feedback&quot; above to create a versioned snapshot with CSV export and SHA-256 manifest.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {datasets.map((ds) => {
              const isSelected = activeDatasetFilter === ds.dataset_version;
              const dateStr = ds.created_at ? new Date(ds.created_at).toLocaleDateString() : '';
              const checksumShort = ds.checksum ? `${ds.checksum.substring(0, 12)}...` : 'N/A';

              return (
                <div
                  key={ds.dataset_version}
                  className={`p-3.5 rounded-xl border transition-all ${
                    isSelected
                      ? 'bg-emerald-500/10 border-emerald-500/40 shadow-sm'
                      : 'bg-white/[0.02] border-white/[0.06] hover:border-white/20'
                  }`}
                >
                  {/* Title & Status */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-white tracking-tight truncate" title={ds.dataset_version}>
                      {ds.dataset_version}
                    </span>
                    <button
                      onClick={() => onSelectDataset(isSelected ? '' : ds.dataset_version)}
                      className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium transition-colors ${
                        isSelected
                          ? 'bg-emerald-500 text-slate-950 font-bold'
                          : 'bg-white/5 text-slate-300 hover:bg-white/10'
                      }`}
                    >
                      {isSelected ? 'Active Filter' : 'Filter by DS'}
                    </button>
                  </div>

                  {/* Metadata Row */}
                  <div className="grid grid-cols-3 gap-1 py-1.5 px-2 bg-slate-900/60 rounded-lg text-center font-mono text-[11px] mb-2">
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase">Total</div>
                      <div className="font-bold text-white">{ds.row_count}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-emerald-500 uppercase">Eligible</div>
                      <div className="font-bold text-emerald-400">{ds.eligible_count}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-rose-500 uppercase">Excluded</div>
                      <div className="font-bold text-rose-400">{ds.excluded_count}</div>
                    </div>
                  </div>

                  {/* Checksum & Date */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <div className="flex items-center space-x-1" title={ds.checksum}>
                      <Hash className="h-3 w-3 text-slate-500 flex-shrink-0" />
                      <span className="text-[10px]">{checksumShort}</span>
                      <button
                        onClick={() => handleCopyHash(ds.checksum, ds.dataset_version)}
                        className="text-slate-500 hover:text-white transition-colors"
                        title="Copy full SHA-256 checksum"
                      >
                        {copiedHash === ds.dataset_version ? (
                          <Check className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                    <div className="flex items-center space-x-1 text-[10px] text-slate-500">
                      <Calendar className="h-3 w-3" />
                      <span>{dateStr}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
