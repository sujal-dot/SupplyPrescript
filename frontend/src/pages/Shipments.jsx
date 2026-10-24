import React, { useState, useEffect } from 'react';
import {
  Truck,
  RefreshCw,
  AlertTriangle,
  X,
  ExternalLink,
  Sparkles,
  Calendar,
  DollarSign,
  Package,
} from 'lucide-react';
import { getShipments, predictShipment, formatApiError } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import GlassButton from '../components/ui/GlassButton';
import StatusBadge from '../components/ui/StatusBadge';
import ShipmentTable from '../components/shipments/ShipmentTable';

export default function Shipments() {
  const [shipments, setShipments] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters state
  const [filters, setFilters] = useState({
    search: '',
    transport_mode: '',
    is_delayed: null,
    sort_by: 'order_date',
    sort_order: 'desc',
  });

  // Selected shipment for inspector drawer
  const [selectedShipment, setSelectedShipment] = useState(null);
  const [predictingShipment, setPredictingShipment] = useState(false);
  const [shipmentPrediction, setShipmentPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState(null);

  const fetchShipments = async () => {
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
      if (filters.transport_mode) params.transport_mode = filters.transport_mode;
      if (filters.is_delayed !== null && filters.is_delayed !== undefined) {
        params.is_delayed = filters.is_delayed;
      }

      const res = await getShipments(params);
      setShipments(res.data || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load shipments:', err);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShipments();
  }, [page, pageSize, filters.sort_by, filters.sort_order, filters.transport_mode, filters.is_delayed]);

  const handleSearch = (term) => {
    setFilters((prev) => ({ ...prev, search: term }));
    setPage(1);
    // Immediate fetch for search
    setTimeout(() => {
      fetchShipments();
    }, 50);
  };

  const handleFilterChange = (key, val) => {
    setFilters((prev) => ({ ...prev, [key]: val }));
    setPage(1);
  };

  const handleSortChange = (sortBy) => {
    setFilters((prev) => ({ ...prev, sort_by: sortBy }));
    setPage(1);
  };

  const openInspector = (shipment) => {
    setSelectedShipment(shipment);
    setShipmentPrediction(null);
    setPredictionError(null);
  };

  const handlePredictForShipment = async () => {
    if (!selectedShipment) return;
    setPredictingShipment(true);
    setPredictionError(null);
    try {
      // Parse numerical IDs
      const supMatch = selectedShipment.supplier_id.match(/\d+/);
      const prodMatch = selectedShipment.product_id.match(/\d+/);
      const supId = supMatch ? parseInt(supMatch[0], 10) : 1;
      const prodId = prodMatch ? parseInt(prodMatch[0], 10) : 1;

      const payload = {
        supplier_id: supId,
        product_id: prodId,
        quantity: selectedShipment.quantity,
        inventory_level: selectedShipment.inventory_level,
        transport_mode: selectedShipment.transport_mode,
        destination: selectedShipment.destination,
        priority: selectedShipment.priority,
        shipping_cost: Number(selectedShipment.shipping_cost),
      };

      const res = await predictShipment(payload);
      setShipmentPrediction(res);
    } catch (err) {
      console.error('Prediction failed for shipment:', err);
      setPredictionError(formatApiError(err));
    } finally {
      setPredictingShipment(false);
    }
  };

  return (
    <div className="space-y-8 pb-10">
      <PageHeader
        title="Shipment Logistics & Monitoring"
        subtitle="Live tracking of 15,000 real shipment records with historical delivery outcomes and active machine learning delay predictions."
        actions={
          <GlassButton
            variant="secondary"
            size="md"
            icon={RefreshCw}
            loading={loading}
            onClick={fetchShipments}
          >
            Refresh Shipments
          </GlassButton>
        }
      />

      {error && (
        <div className="glass-card p-4 rounded-2xl border-rose-400/30 bg-rose-500/10 flex items-start justify-between text-xs">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-rose-300">Shipments API Notice: </span>
              <span className="text-rose-200/90">{error}</span>
            </div>
          </div>
          <button
            onClick={fetchShipments}
            className="font-semibold text-red-300 hover:underline shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      {/* Shipment Table Component */}
      <ShipmentTable
        shipments={shipments}
        total={total}
        page={page}
        pageSize={pageSize}
        totalPages={totalPages}
        loading={loading}
        onPageChange={setPage}
        onSearchChange={handleSearch}
        onFilterChange={handleFilterChange}
        onSortChange={handleSortChange}
        onRefresh={fetchShipments}
        onSelectShipment={openInspector}
        filters={filters}
      />

      {/* Shipment Detail & Prediction Drawer Modal */}
      {selectedShipment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="glass-card w-full max-w-2xl rounded-2xl border border-white/20 p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            {/* Close Button */}
            <button
              onClick={() => setSelectedShipment(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Header */}
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2.5 rounded-xl bg-red-500/20 border border-red-500/30 text-red-300">
                <Truck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white font-mono">
                  Shipment: {selectedShipment.shipment_id}
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedShipment.origin} &rarr; {selectedShipment.destination} via {selectedShipment.transport_mode}
                </p>
              </div>
            </div>

            {/* Data Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono mb-6">
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Supplier ID</span>
                <span className="text-white font-bold">{selectedShipment.supplier_id}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Product SKU</span>
                <span className="text-white font-bold">{selectedShipment.product_id}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Quantity</span>
                <span className="text-white font-bold">{Number(selectedShipment.quantity).toLocaleString()}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Order Date</span>
                <span className="text-slate-200">{selectedShipment.order_date}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Expected Delivery</span>
                <span className="text-slate-200">{selectedShipment.expected_delivery_date}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Actual Delivery</span>
                <span className="text-slate-200">{selectedShipment.actual_delivery_date || 'In Transit'}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Shipping Cost</span>
                <span className="text-white">${Number(selectedShipment.shipping_cost).toLocaleString()}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Priority</span>
                <span className="text-white">{selectedShipment.priority}</span>
              </div>
              <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <span className="text-slate-500 block text-[10px]">Historical Delay</span>
                <span className={selectedShipment.delay_days > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                  {selectedShipment.delay_days > 0 ? `+${selectedShipment.delay_days} days` : '0 days (On-Time)'}
                </span>
              </div>
            </div>

            {/* Prediction Evaluation Section */}
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2">
                  <Sparkles className="h-4 w-4 text-red-400" />
                  <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                    XGBoost ML Risk Evaluation
                  </span>
                </div>

                <GlassButton
                  variant="primary"
                  size="sm"
                  loading={predictingShipment}
                  onClick={handlePredictForShipment}
                >
                  {predictingShipment ? 'Running Inference...' : 'Run Prediction Now'}
                </GlassButton>
              </div>

              {predictionError && (
                <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-400/30 text-rose-300 text-xs mt-2">
                  {predictionError}
                </div>
              )}

              {shipmentPrediction ? (
                <div className="mt-3 p-3.5 rounded-xl bg-slate-900/60 border border-white/10 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-300 font-mono">Evaluated Risk Tier:</span>
                    <StatusBadge
                      status={shipmentPrediction.risk}
                      variant={
                        shipmentPrediction.risk === 'HIGH'
                          ? 'error'
                          : shipmentPrediction.risk === 'MEDIUM'
                          ? 'warning'
                          : 'success'
                      }
                      dot={true}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs font-mono pt-1">
                    <div>
                      <span className="text-slate-400 block text-[10px]">Delay Probability</span>
                      <span className="text-xl font-extrabold text-red-300">
                        {Math.round(shipmentPrediction.delay_probability * 100)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">Predicted Duration</span>
                      <span className="text-xl font-extrabold text-white">
                        +{Number(shipmentPrediction.predicted_delay_days).toFixed(1)} days
                      </span>
                    </div>
                  </div>
                </div>
              ) : selectedShipment.prediction_probability !== null && selectedShipment.prediction_probability !== undefined ? (
                <div className="mt-2 text-xs text-slate-300 font-mono">
                  Stored prediction: {Math.round(Number(selectedShipment.prediction_probability) * 100)}% probability, +{Number(selectedShipment.predicted_delay_days || 0).toFixed(1)} days delay.
                </div>
              ) : (
                <p className="text-xs text-slate-400 mt-1">
                  No prediction is stored yet for this order. Click "Run Prediction Now" to invoke the active ML models with this shipment's parameters.
                </p>
              )}
            </div>

            <div className="flex justify-end">
              <GlassButton variant="secondary" size="md" onClick={() => setSelectedShipment(null)}>
                Close
              </GlassButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
