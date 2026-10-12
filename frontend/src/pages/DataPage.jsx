import React, { useState } from 'react';
import { 
  Database, 
  UploadCloud, 
  FileCheck, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  Layers, 
  Clock,
  ArrowRight
} from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import GlassCard from '../components/ui/GlassCard';
import GlassPanel from '../components/ui/GlassPanel';
import GlassButton from '../components/ui/GlassButton';
import StatusBadge from '../components/ui/StatusBadge';

export default function DataPage() {
  const [uploadStatus, setUploadStatus] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  const simulateUpload = () => {
    setIsUploading(true);
    setTimeout(() => {
      setIsUploading(false);
      setUploadStatus({
        fileName: 'supply_chain_logistics_batch_2026_q4.csv',
        recordsParsed: 1840,
        validRecords: 1836,
        anomalies: 4,
        status: 'Validated & Ingested',
      });
    }, 1200);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Enterprise Data Ingestion & Quality Audit"
        subtitle="Schema validation pipeline, automated outlier detection, and historical batch processing telemetry."
        breadcrumbs={[{ label: 'Data Management' }]}
      />

      {/* Data Quality Indicator Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <GlassCard interactive glow="cyan" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Completeness Score</span>
            <StatusBadge status="99.8%" variant="success" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">99.8%</div>
          <p className="text-xs text-slate-400 mt-2">Zero null values in mandatory keys</p>
        </GlassCard>

        <GlassCard interactive glow="emerald" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Schema Integrity</span>
            <StatusBadge status="Verified" variant="success" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">100%</div>
          <p className="text-xs text-slate-400 mt-2">Pydantic v2 strict typing verified</p>
        </GlassCard>

        <GlassCard interactive glow="amber" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Anomaly Rate</span>
            <StatusBadge status="0.32%" variant="info" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">0.32%</div>
          <p className="text-xs text-slate-400 mt-2">Statistical standard deviation outliers</p>
        </GlassCard>

        <GlassCard interactive glow="blue" className="rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Active Pipeline</span>
            <StatusBadge status="Idle" variant="neutral" dot={false} />
          </div>
          <div className="text-3xl font-extrabold text-white">Synced</div>
          <p className="text-xs text-slate-400 mt-2">PostgreSQL 16 connection pool ready</p>
        </GlassCard>
      </div>

      {/* Dataset Ingestion Interface */}
      <GlassPanel
        title="Batch Ingestion Pipeline"
        subtitle="Upload CSV or JSON shipment and inventory manifests for automatic schema verification"
        icon={UploadCloud}
      >
        <div className="p-8 border-2 border-dashed border-white/15 rounded-2xl hover:border-cyan-400/40 transition-all text-center space-y-4 bg-white/[0.01]">
          <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-400/20 flex items-center justify-center text-cyan-400 mx-auto">
            <UploadCloud className="h-7 w-7" />
          </div>
          <div>
            <h4 className="text-base font-bold text-white">
              Drag &amp; drop supply chain manifest file
            </h4>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Supports .csv and .json with fields: <code className="text-cyan-300">supplier_id</code>, <code className="text-cyan-300">product_id</code>, <code className="text-cyan-300">lead_time</code>, <code className="text-cyan-300">quantity</code>.
            </p>
          </div>

          <div className="pt-2">
            <GlassButton
              variant="primary"
              size="md"
              icon={FileCheck}
              loading={isUploading}
              onClick={simulateUpload}
            >
              Simulate File Validation &amp; Upload
            </GlassButton>
          </div>
        </div>

        {uploadStatus && (
          <div className="mt-6 p-4 rounded-xl glass-card border border-emerald-400/30 bg-emerald-500/10 flex items-start space-x-3 text-xs">
            <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            <div className="flex-1 space-y-1">
              <div className="font-bold text-emerald-300 text-sm">
                Batch Upload &amp; Schema Validation Passed!
              </div>
              <div className="text-slate-300">
                File: <span className="font-mono text-white">{uploadStatus.fileName}</span> &bull; Parsed: <span className="font-bold text-white">{uploadStatus.recordsParsed}</span> rows
              </div>
              <div className="text-slate-400">
                Valid: {uploadStatus.validRecords} &bull; Outliers Flagged: {uploadStatus.anomalies} (imputed via IQR boundaries)
              </div>
            </div>
          </div>
        )}
      </GlassPanel>

      {/* Historical Batch Ingestion Logs */}
      <GlassPanel
        title="Historical Processing & Ingestion Audit Log"
        subtitle="Recent data ingestion jobs processed by the backend"
        icon={Clock}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 font-semibold">
                <th className="pb-3 pl-2">Job ID</th>
                <th className="pb-3">Dataset Source</th>
                <th className="pb-3">Timestamp</th>
                <th className="pb-3">Rows Processed</th>
                <th className="pb-3">Pipeline Duration</th>
                <th className="pb-3 text-right pr-2">Ingestion Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {[
                { id: 'JOB-8421', src: 'shipments_october_manifest.csv', date: '2026-10-11 14:22', rows: 1240, duration: '1.42s', status: 'Completed' },
                { id: 'JOB-8420', src: 'inventory_snapshot_wh_east.json', date: '2026-10-11 09:15', rows: 450, duration: '0.84s', status: 'Completed' },
                { id: 'JOB-8419', src: 'suppliers_tier1_audit.csv', date: '2026-10-10 18:40', rows: 85, duration: '0.35s', status: 'Completed' },
                { id: 'JOB-8418', src: 'demand_forecast_features.parquet', date: '2026-10-09 21:05', rows: 2680, duration: '2.15s', status: 'Completed' },
              ].map((job, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 pl-2 font-mono text-cyan-300 font-semibold">
                    {job.id}
                  </td>
                  <td className="py-3 text-white font-medium">{job.src}</td>
                  <td className="py-3 text-slate-400 font-mono">{job.date}</td>
                  <td className="py-3 text-slate-300">{job.rows.toLocaleString()}</td>
                  <td className="py-3 text-slate-400 font-mono">{job.duration}</td>
                  <td className="py-3 text-right pr-2">
                    <StatusBadge status={job.status} variant="success" />
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
