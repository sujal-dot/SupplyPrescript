import React, { useState, useEffect } from 'react';
import { Send, AlertCircle, RefreshCw, Sparkles, Sliders } from 'lucide-react';
import { getSuppliers, getProducts } from '../../services/api';
import GlassButton from '../ui/GlassButton';

const TRANSPORT_MODES = ['Road', 'Rail', 'Air', 'Sea'];
const PRIORITIES = ['Low', 'Medium', 'High', 'Critical'];
const SEASONS = ['Winter', 'Summer', 'Monsoon', 'Post-Monsoon'];

export default function PredictionForm({ onSubmit, loading = false, error = null }) {
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [fetchingDropdowns, setFetchingDropdowns] = useState(true);

  // Form state
  const [supplierId, setSupplierId] = useState('1');
  const [productId, setProductId] = useState('1');
  const [quantity, setQuantity] = useState('500');
  const [inventoryLevel, setInventoryLevel] = useState('1200');
  const [transportMode, setTransportMode] = useState('Road');

  // Optional scenario parameters
  const [destination, setDestination] = useState('');
  const [shippingCost, setShippingCost] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [leadTime, setLeadTime] = useState('');
  const [season, setSeason] = useState('');
  const [demand, setDemand] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Validation state
  const [clientErrors, setClientErrors] = useState({});

  useEffect(() => {
    let isMounted = true;
    const loadOptions = async () => {
      setFetchingDropdowns(true);
      try {
        const [supRes, prodRes] = await Promise.all([
          getSuppliers({ page_size: 100 }),
          getProducts({ page_size: 100 }),
        ]);

        if (isMounted) {
          const supList = supRes?.data || [];
          const prodList = prodRes?.data || [];
          setSuppliers(supList);
          setProducts(prodList);

          if (supList.length > 0) {
            setSupplierId(String(supList[0].id || 1));
          }
          if (prodList.length > 0) {
            setProductId(String(prodList[0].id || 1));
          }
        }
      } catch (err) {
        console.warn('Failed to load dropdown options:', err);
      } finally {
        if (isMounted) setFetchingDropdowns(false);
      }
    };
    loadOptions();
    return () => {
      isMounted = false;
    };
  }, []);

  const validate = () => {
    const errs = {};
    const parsedSup = parseInt(supplierId, 10);
    const parsedProd = parseInt(productId, 10);
    const parsedQty = parseInt(quantity, 10);
    const parsedInv = parseInt(inventoryLevel, 10);

    if (!supplierId || isNaN(parsedSup) || parsedSup <= 0) {
      errs.supplierId = 'Please select a valid supplier.';
    }
    if (!productId || isNaN(parsedProd) || parsedProd <= 0) {
      errs.productId = 'Please select a valid product.';
    }
    if (isNaN(parsedQty) || parsedQty <= 0) {
      errs.quantity = 'Quantity must be a positive number greater than 0.';
    }
    if (isNaN(parsedInv) || parsedInv < 0) {
      errs.inventoryLevel = 'Inventory level must be a non-negative number (≥ 0).';
    }
    if (!transportMode) {
      errs.transportMode = 'Please select a transport mode.';
    }
    if (shippingCost && (isNaN(parseFloat(shippingCost)) || parseFloat(shippingCost) < 0)) {
      errs.shippingCost = 'Shipping cost must be non-negative.';
    }
    if (leadTime && (isNaN(parseInt(leadTime, 10)) || parseInt(leadTime, 10) <= 0)) {
      errs.leadTime = 'Lead time must be greater than 0.';
    }

    setClientErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (loading) return; // prevent duplicate clicks

    if (!validate()) return;

    const payload = {
      supplier_id: parseInt(supplierId, 10),
      product_id: parseInt(productId, 10),
      quantity: parseInt(quantity, 10),
      inventory_level: parseInt(inventoryLevel, 10),
      transport_mode: transportMode,
    };

    if (destination.trim()) payload.destination = destination.trim();
    if (shippingCost !== '') payload.shipping_cost = parseFloat(shippingCost);
    if (priority) payload.priority = priority;
    if (leadTime !== '') payload.lead_time = parseInt(leadTime, 10);
    if (season) payload.season = season;

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card p-6 rounded-2xl border border-white/[0.08] space-y-6">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Inference Scenario Parameters
            </h3>
            <p className="text-xs text-slate-400">
              Evaluates XGBoost classification (risk probability) and regression (delay duration)
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-slate-400 hover:text-red-300 flex items-center space-x-1 font-mono transition-colors"
        >
          <Sliders className="h-3.5 w-3.5" />
          <span>{showAdvanced ? 'Simple Mode' : 'Advanced Scenario'}</span>
        </button>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-400/30 text-rose-300 text-xs flex items-start space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Prediction Request Failed</div>
            <div className="text-rose-200/90 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* Grid Inputs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Supplier Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
            Supplier <span className="text-rose-400">*</span>
          </label>
          <select
            value={supplierId}
            onChange={(e) => setSupplierId(e.target.value)}
            disabled={fetchingDropdowns || loading}
            className="w-full glass-input text-xs px-3 py-2.5 bg-slate-900/80 border border-white/10 rounded-xl text-white focus:border-red-500 focus:outline-none"
          >
            {fetchingDropdowns ? (
              <option value="">Loading suppliers from database...</option>
            ) : suppliers.length === 0 ? (
              <option value="1">Supplier 1 (Default)</option>
            ) : (
              suppliers.map((s) => (
                <option key={s.id || s.supplier_id} value={s.id}>
                  {s.supplier_name} ({s.supplier_id}) — Rel:{' '}
                  {s.supplier_reliability !== null && s.supplier_reliability !== undefined
                    ? `${Math.round(Number(s.supplier_reliability) * 100)}%`
                    : 'N/A'}
                </option>
              ))
            )}
          </select>
          {clientErrors.supplierId && (
            <p className="text-[11px] text-rose-400 mt-1">{clientErrors.supplierId}</p>
          )}
        </div>

        {/* Product Selector */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
            Product SKU <span className="text-rose-400">*</span>
          </label>
          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            disabled={fetchingDropdowns || loading}
            className="w-full glass-input text-xs px-3 py-2.5 bg-slate-900/80 border border-white/10 rounded-xl text-white focus:border-red-500 focus:outline-none"
          >
            {fetchingDropdowns ? (
              <option value="">Loading products from database...</option>
            ) : products.length === 0 ? (
              <option value="1">Product 1 (Default)</option>
            ) : (
              products.map((p) => (
                <option key={p.id || p.product_id} value={p.id}>
                  {p.product_name || p.name || p.product_id} ({p.product_id})
                  {p.category ? ` — ${p.category}` : ''}
                </option>
              ))
            )}
          </select>
          {clientErrors.productId && (
            <p className="text-[11px] text-rose-400 mt-1">{clientErrors.productId}</p>
          )}
        </div>

        {/* Order Quantity */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
            Order Quantity (units) <span className="text-rose-400">*</span>
          </label>
          <input
            type="number"
            min="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            disabled={loading}
            placeholder="e.g. 500"
            className="w-full glass-input text-xs px-3 py-2.5 bg-slate-900/80 border border-white/10 rounded-xl text-white focus:border-red-500 focus:outline-none"
          />
          {clientErrors.quantity && (
            <p className="text-[11px] text-rose-400 mt-1">{clientErrors.quantity}</p>
          )}
        </div>

        {/* Available Inventory Level */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
            Inventory on Hand (units) <span className="text-rose-400">*</span>
          </label>
          <input
            type="number"
            min="0"
            value={inventoryLevel}
            onChange={(e) => setInventoryLevel(e.target.value)}
            disabled={loading}
            placeholder="e.g. 1200"
            className="w-full glass-input text-xs px-3 py-2.5 bg-slate-900/80 border border-white/10 rounded-xl text-white focus:border-red-500 focus:outline-none"
          />
          {clientErrors.inventoryLevel && (
            <p className="text-[11px] text-rose-400 mt-1">{clientErrors.inventoryLevel}</p>
          )}
        </div>

        {/* Transport Mode */}
        <div className="md:col-span-2">
          <label className="block text-xs font-semibold text-slate-300 mb-2 font-mono">
            Transit Modality <span className="text-rose-400">*</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {TRANSPORT_MODES.map((mode) => {
              const isSelected = transportMode === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setTransportMode(mode)}
                  disabled={loading}
                  className={`py-2 px-3 rounded-xl text-xs font-medium border transition-all ${
                    isSelected
                      ? 'bg-red-500/20 border-red-500 text-red-200 shadow-[0_0_15px_rgba(239,68,68,0.2)] font-bold'
                      : 'bg-white/[0.03] border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.06]'
                  }`}
                >
                  {mode}
                </button>
              );
            })}
          </div>
          {clientErrors.transportMode && (
            <p className="text-[11px] text-rose-400 mt-1">{clientErrors.transportMode}</p>
          )}
        </div>
      </div>

      {/* Advanced scenario inputs */}
      {showAdvanced && (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-4 pt-3">
          <div className="text-xs font-mono text-red-300/90 font-semibold uppercase tracking-wider">
            Optional Scenario Overrides
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                Destination Hub
              </label>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                disabled={loading}
                placeholder="e.g. Mumbai, Delhi"
                className="w-full glass-input text-xs px-2.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                disabled={loading}
                className="w-full glass-input text-xs px-2.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg text-white"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                Planned Lead Time (days)
              </label>
              <input
                type="number"
                min="1"
                value={leadTime}
                onChange={(e) => setLeadTime(e.target.value)}
                disabled={loading}
                placeholder="Resolved from DB if empty"
                className="w-full glass-input text-xs px-2.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                Shipping Cost ($)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={shippingCost}
                onChange={(e) => setShippingCost(e.target.value)}
                disabled={loading}
                placeholder="Resolved from DB if empty"
                className="w-full glass-input text-xs px-2.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-[11px] font-mono text-slate-400 mb-1">
                Season
              </label>
              <select
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                disabled={loading}
                className="w-full glass-input text-xs px-2.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg text-white"
              >
                <option value="">Current Calendar Season (Default)</option>
                {SEASONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <div className="pt-2 flex items-center justify-between">
        <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
          Authorized Endpoint: POST /api/predict
        </span>

        <GlassButton
          type="submit"
          onClick={handleSubmit}
          variant="primary"
          size="md"
          icon={loading ? RefreshCw : Send}
          loading={loading}
          disabled={loading}
          className="w-full sm:w-auto"
        >
          {loading ? 'Evaluating Model Inference...' : 'Predict Shipment Risk'}
        </GlassButton>
      </div>
    </form>
  );
}
