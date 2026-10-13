import React, { useState, useEffect } from 'react';
import {
  Package,
  AlertTriangle,
  RefreshCw,
  X,
  ShieldCheck,
  TrendingDown,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import { getInventory, formatApiError } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import GlassButton from '../components/ui/GlassButton';
import StatusBadge from '../components/ui/StatusBadge';
import MetricCard from '../components/dashboard/MetricCard';
import InventoryTable from '../components/inventory/InventoryTable';

export default function Inventory() {
  const [inventoryRecords, setInventoryRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [filters, setFilters] = useState({
    search: '',
    inventory_status: '',
    sort_by: 'product_id',
    sort_order: 'asc',
  });

  // Selected item modal
  const [selectedRecord, setSelectedRecord] = useState(null);

  const fetchInventory = async () => {
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
      if (filters.inventory_status) params.inventory_status = filters.inventory_status;

      const res = await getInventory(params);
      setInventoryRecords(res.data || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load inventory records:', err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, [page, pageSize, filters.sort_by, filters.sort_order, filters.inventory_status]);

  const handleSearch = (term) => {
    setFilters((prev) => ({ ...prev, search: term }));
    setPage(1);
    setTimeout(() => {
      fetchInventory();
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
      sort_order: sortBy === 'inventory_level' ? 'asc' : 'asc',
    }));
    setPage(1);
  };

  // Quick summary stats from current records
  const healthyCount = inventoryRecords.filter((r) => r.inventory_status === 'Healthy').length;
  const lowCount = inventoryRecords.filter((r) => r.inventory_status === 'Low').length;
  const criticalCount = inventoryRecords.filter((r) => r.inventory_status === 'Critical' || r.inventory_status === 'Out of Stock').length;

  return (
    <div className="space-y-8 pb-10">
      <PageHeader
        title="Inventory Levels & Stock Optimization"
        subtitle="Authoritative SKU inventory balances, safety stock buffers, and reorder point thresholds from PostgreSQL."
        actions={
          <GlassButton
            variant="secondary"
            size="md"
            icon={RefreshCw}
            loading={loading}
            onClick={fetchInventory}
          >
            Refresh Inventory
          </GlassButton>
        }
      />

      {error && (
        <div className="glass-card p-4 rounded-2xl border-rose-400/30 bg-rose-500/10 flex items-start justify-between text-xs">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-rose-300">Inventory API Notice: </span>
              <span className="text-rose-200/90">{error}</span>
            </div>
          </div>
          <button
            onClick={fetchInventory}
            className="font-semibold text-cyan-300 hover:underline shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <MetricCard
          title="Monitored SKUs"
          value={total}
          subtitle="Active SKU inventory records"
          unit="SKUs"
          icon={Package}
          variant="cyan"
          loading={loading}
        />
        <MetricCard
          title="Healthy Stock"
          value={healthyCount}
          subtitle="Above reorder point"
          unit="SKUs"
          icon={CheckCircle2}
          variant="emerald"
          loading={loading}
        />
        <MetricCard
          title="Low Stock Warning"
          value={lowCount}
          subtitle="Approaching reorder threshold"
          unit="SKUs"
          icon={AlertTriangle}
          variant="amber"
          loading={loading}
        />
        <MetricCard
          title="Critical Shortages"
          value={criticalCount}
          subtitle="Below safety stock boundary"
          unit="SKUs"
          icon={TrendingDown}
          variant="rose"
          loading={loading}
          badge={criticalCount > 0 ? 'Action Required' : undefined}
        />
      </div>

      {/* Main Inventory Table */}
      <InventoryTable
        inventoryRecords={inventoryRecords}
        total={total}
        page={page}
        pageSize={pageSize}
        totalPages={totalPages}
        loading={loading}
        onPageChange={setPage}
        onSearchChange={handleSearch}
        onFilterChange={handleFilterChange}
        onSortChange={handleSortChange}
        onRefresh={fetchInventory}
        onSelectProduct={setSelectedRecord}
        filters={filters}
      />

      {/* Product Inventory Detail Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-card w-full max-w-lg rounded-2xl border border-white/20 p-6 shadow-2xl relative">
            <button
              onClick={() => setSelectedRecord(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center space-x-3 mb-5">
              <div className="p-3 rounded-2xl bg-cyan-500/20 border border-cyan-400/30 text-cyan-300">
                <Package className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  {selectedRecord.product_name || `Product SKU ${selectedRecord.product_id}`}
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  SKU: {selectedRecord.product_id}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono mb-6">
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">On-Hand Stock</span>
                <span className="text-white font-bold text-base">
                  {Number(selectedRecord.inventory_level).toLocaleString()} units
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Status Tier</span>
                <StatusBadge
                  status={selectedRecord.inventory_status}
                  variant={
                    selectedRecord.inventory_status === 'Healthy'
                      ? 'success'
                      : selectedRecord.inventory_status === 'Low'
                      ? 'warning'
                      : 'error'
                  }
                  dot={true}
                />
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Reorder Threshold</span>
                <span className="text-white font-bold">
                  {Number(selectedRecord.reorder_point).toLocaleString()} units
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Safety Stock Buffer</span>
                <span className="text-white font-bold">
                  {Number(selectedRecord.safety_stock).toLocaleString()} units
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Projected Demand</span>
                <span className="text-slate-200">
                  {Number(selectedRecord.demand).toLocaleString()} units
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Inventory Audit Date</span>
                <span className="text-slate-200">{selectedRecord.inventory_date}</span>
              </div>
            </div>

            <div className="flex justify-end">
              <GlassButton variant="secondary" size="md" onClick={() => setSelectedRecord(null)}>
                Close
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
