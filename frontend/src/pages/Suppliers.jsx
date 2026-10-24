import React, { useState, useEffect } from 'react';
import {
  Building2,
  Award,
  RefreshCw,
  AlertTriangle,
  X,
  TrendingUp,
  MapPin,
  Clock,
  Layers,
} from 'lucide-react';
import { getSuppliers, formatApiError } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import GlassButton from '../components/ui/GlassButton';
import SupplierTable from '../components/suppliers/SupplierTable';
import SupplierReliabilityChart from '../components/dashboard/SupplierReliabilityChart';

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [filters, setFilters] = useState({
    search: '',
    min_reliability: null,
    sort_by: 'supplier_id',
    sort_order: 'asc',
  });

  // Selected supplier drawer
  const [selectedSupplier, setSelectedSupplier] = useState(null);

  const fetchSuppliers = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: pageSize,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      };

      if (filters.search?.trim()) params.search = filters.search.trim();
      if (filters.min_reliability !== null && filters.min_reliability !== undefined) {
        params.min_reliability = filters.min_reliability;
      }

      const res = await getSuppliers(params);
      setSuppliers(res.data || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load suppliers:', err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
  }, [page, pageSize, filters.sort_by, filters.sort_order, filters.min_reliability]);

  const handleSearch = (term) => {
    setFilters((prev) => ({ ...prev, search: term }));
    setPage(1);
    setTimeout(() => {
      fetchSuppliers();
    }, 50);
  };

  const handleFilterChange = (key, val) => {
    setFilters((prev) => ({ ...prev, [key]: val }));
    setPage(1);
  };

  const handleSortChange = (sortBy) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: sortBy,
      sort_order: sortBy === 'reliability' ? 'desc' : 'asc',
    }));
    setPage(1);
  };

  return (
    <div className="space-y-8 pb-10">
      <PageHeader
        title="Supplier Reliability & Performance"
        subtitle="Manage 50 authoritative vendor partnerships, contract reliability metrics, and historical shipment fulfilment rates."
        actions={
          <GlassButton
            variant="secondary"
            size="md"
            icon={RefreshCw}
            loading={loading}
            onClick={fetchSuppliers}
          >
            Refresh Suppliers
          </GlassButton>
        }
      />

      {error && (
        <div className="glass-card p-4 rounded-2xl border-rose-400/30 bg-rose-500/10 flex items-start justify-between text-xs">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-rose-300">Suppliers API Notice: </span>
              <span className="text-rose-200/90">{error}</span>
            </div>
          </div>
          <button
            onClick={fetchSuppliers}
            className="font-semibold text-red-300 hover:underline shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* Supplier Reliability Performance Chart */}
      <SupplierReliabilityChart
        data={suppliers}
        loading={loading}
        height={260}
      />

      {/* Supplier Table Component */}
      <SupplierTable
        suppliers={suppliers}
        total={total}
        page={page}
        pageSize={pageSize}
        totalPages={totalPages}
        loading={loading}
        onPageChange={setPage}
        onSearchChange={handleSearch}
        onFilterChange={handleFilterChange}
        onSortChange={handleSortChange}
        onRefresh={fetchSuppliers}
        onSelectSupplier={setSelectedSupplier}
        filters={filters}
      />

      {/* Supplier Details Modal */}
      {selectedSupplier && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-card w-full max-w-lg rounded-2xl border border-white/20 p-6 shadow-2xl relative">
            <button
              onClick={() => setSelectedSupplier(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center space-x-3 mb-5">
              <div className="p-3 rounded-2xl bg-emerald-500/20 border border-emerald-400/30 text-emerald-300">
                <Building2 className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {selectedSupplier.supplier_name}
                </h3>
                <span className="text-xs font-mono text-red-300">
                  ID: {selectedSupplier.supplier_id}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono mb-6">
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Origin City</span>
                <span className="text-white font-bold">{selectedSupplier.origin}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Reliability Rating</span>
                <span className="text-emerald-400 font-bold text-base">
                  {selectedSupplier.supplier_reliability !== null
                    ? `${Math.round(Number(selectedSupplier.supplier_reliability) * 100)}%`
                    : 'Unavailable'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Total Shipments</span>
                <span className="text-white font-bold">
                  {selectedSupplier.total_shipments?.toLocaleString() || '—'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Historical Delay</span>
                <span className="text-white font-bold">
                  {selectedSupplier.historical_avg_delay !== undefined
                    ? `${Number(selectedSupplier.historical_avg_delay).toFixed(2)} days`
                    : '—'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Base Lead Time</span>
                <span className="text-slate-200">
                  {selectedSupplier.base_lead_time ? `${selectedSupplier.base_lead_time} days` : 'Variable'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Monthly Capacity</span>
                <span className="text-slate-200">
                  {selectedSupplier.capacity ? `${selectedSupplier.capacity.toLocaleString()} units` : 'Unconstrained'}
                </span>
              </div>
            </div>

            <div className="flex justify-end">
              <GlassButton variant="secondary" size="md" onClick={() => setSelectedSupplier(null)}>
                Close Profile
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
