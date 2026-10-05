# SupplyPrescript Synthetic Supply Chain Dataset

This directory contains the synthetic historical supply chain dataset designed and generated for **SupplyPrescript** (Phase 1 — Day 2).

The dataset models multi-echelon supply-chain interactions across 50 industrial suppliers, 100 products across 8 categories, and 15,000 historical shipments traversing 16 Indian logistics hubs between 2023 and 2025. It contains non-trivial, statistically grounded relationships between supplier reliability, lead times, transit modes, demand spikes, inventory shortages, and shipping costs.

---

## 1. Directory Structure

```text
data/
├── raw/                      # Future unprocessed external raw datasets
├── processed/                # Future transformed / feature-engineered datasets for ML
└── synthetic/
    ├── suppliers.csv         # 50 suppliers master dataset
    ├── products.csv          # 100 products master catalog
    ├── shipments.csv         # 15,000 historical shipment records (primary dataset)
    ├── generate_supply_chain_data.py   # Deterministic dataset generation script
    ├── validate_supply_chain_data.py   # Automated data validation script
    ├── dataset_summary.py              # Statistical aggregation & distribution script
    └── README.md                       # Dataset documentation & data dictionary
```

---

## 2. Dataset Overview & Key Metrics

- **Shipments Record Count**: 15,000 rows
- **Suppliers**: 50 unique suppliers (`SUP001` - `SUP050`)
- **Products**: 100 unique products (`PROD001` - `PROD100`)
- **Historical Date Range**: `2023-01-01` to `2025-12-31` (3 years, 1,096 days)
- **Random Seed**: `SEED = 42` (Deterministic and 100% reproducible)
- **Delayed Shipments**: ~22.42% (Target: 15% – 30%)
- **Inventory Shortages**: ~10.83% (Target: 5% – 15%)
- **Average Quantity**: ~1,036 units
- **Average Lead Time**: ~9.48 days
- **Average Delay**: ~1.03 days
- **Average Unit Cost**: $137.86
- **Average Shipping Cost**: $1,160.35

---

## 3. Data Dictionary

### Primary Dataset: `shipments.csv` (15,000 records)

| Field | Type | Description | Range / Values |
|---|---|---|---|
| `shipment_id` | String | Unique shipment identifier | `SHIP000001` - `SHIP015000` |
| `supplier_id` | String | Foreign key to `suppliers.csv` | `SUP001` - `SUP050` |
| `product_id` | String | Foreign key to `products.csv` | `PROD001` - `PROD100` |
| `origin` | String | Origin logistics hub / supplier city | 16 Indian industrial cities |
| `destination` | String | Destination consumption / warehouse hub | 16 Indian industrial cities (`origin != destination`) |
| `order_date` | Date (ISO) | Order placement date | `2023-01-01` to `2025-12-31` |
| `expected_delivery_date` | Date (ISO) | Planned delivery date (`order_date + expected_lead_time`) | `order_date <= expected_delivery_date` |
| `actual_delivery_date` | Date (ISO) | Actual delivery date (`expected_delivery_date + delay_days`) | `actual_delivery_date >= expected_delivery_date` |
| `lead_time` | Integer | Total delivery duration in days (`actual_delivery_date - order_date`) | 3 to 28 days |
| `quantity` | Integer | Number of units ordered and shipped | 10 to 5,000 units |
| `unit_cost` | Float | Unit purchase cost (product base cost ± 5%) | $2.85 to $4,402.10 |
| `shipping_cost` | Float | Total freight transport cost (depends on weight, mode, distance, priority) | $28.50 to $41,200.00+ |
| `supplier_reliability` | Float | Supplier reliability score copied from supplier record | 0.70 to 0.99 |
| `inventory_level` | Integer | On-hand warehouse inventory at order time | 0 to 11,000+ units |
| `demand` | Integer | Customer/market demand during order period | 10 to 7,500+ units |
| `priority` | String | Order fulfillment priority tier | `Low` (20%), `Medium` (49%), `High` (26%), `Critical` (5%) |
| `transport_mode` | String | Freight transportation mode | `Road` (49%), `Rail` (24%), `Sea` (19%), `Air` (9%) |
| `delay_days` | Integer | Days delivered past expected date (`actual - expected`) | 0 to 24 days (`delay_days >= 0`) |
| `delay_reason` | String | Root cause for delay (useful for future ML classification) | `None`, `Supplier Issue`, `Transportation Issue`, `Weather`, `Capacity Constraint`, `Inventory Constraint` |

### Supporting Dataset: `suppliers.csv` (50 records)

| Field | Type | Description | Range / Values |
|---|---|---|---|
| `supplier_id` | String | Unique supplier identifier | `SUP001` - `SUP050` |
| `supplier_name` | String | Industrial enterprise name | Realistic Indian supplier names |
| `origin` | String | Supplier manufacturing facility location | 16 logistics hubs |
| `supplier_reliability` | Float | Baseline supplier fulfillment reliability score | 0.70 to 0.99 |
| `base_lead_time` | Integer | Internal processing/manufacturing lead time (days) | 2 to 7 days |
| `capacity` | Integer | Monthly production capacity (units) | 8,000 to 45,000 units |

### Supporting Dataset: `products.csv` (100 records)

| Field | Type | Description | Range / Values |
|---|---|---|---|
| `product_id` | String | Unique product SKU identifier | `PROD001` - `PROD100` |
| `product_name` | String | Product name and specification | 100 industrial SKUs |
| `category` | String | Product business category | `Electronics`, `Automotive`, `Industrial`, `Consumer Goods`, `Pharmaceutical`, `Food`, `Textile`, `Machinery` |
| `unit_cost` | Float | Baseline unit manufacturing/acquisition cost | $6.50 to $4,200.00 |
| `weight_kg` | Float | Unit physical weight in kilograms | 0.15 kg to 380.0 kg |
| `base_demand` | Integer | Baseline daily/weekly customer demand | 20 to 3,100 units |

---

## 4. Modeling & Real-World Correlations

The synthetic generator encodes realistic supply chain dynamics rather than independent uniform distributions:

1. **Supplier Reliability & Delay Probability**:
   - High-reliability suppliers (`0.92 – 0.99`) achieve ~11%–16% delay rates.
   - Low-reliability suppliers (`0.70 – 0.82`) experience ~37%–46% delay rates.
   - Delay causes reflect the supplier reliability and capacity state.
2. **Transport Mode Dynamics**:
   - **Air**: Fast lead time (avg 6.1 days), highest shipping cost ($5,375 avg), lowest delay probability.
   - **Road**: Balanced lead time (avg 8.0 days), medium cost ($858 avg), dominant domestic mode.
   - **Rail**: Economical for heavy bulk over long distances (avg 10.1 days, $760 avg).
   - **Sea**: Coastal intermodal freight, lowest ton-km cost ($414 avg) but longest lead time (avg 14.5 days) and subject to port congestion.
3. **Inventory Shortage & Priority Correlation**:
   - Shortage scenarios occur when `inventory_level < demand` (~10.8% of shipments).
   - When a shortage occurs, order priority shifts drastically to `High` (~56%) or `Critical` (~24%), driving expedited shipping choices.
4. **Distance & Geography**:
   - Exact highway/transit distances computed using Haversine formula across 16 Indian industrial hubs (Mumbai, Pune, Delhi, Bengaluru, Chennai, Hyderabad, Ahmedabad, Surat, Nagpur, Kolkata, Jaipur, Indore, Nashik, Vadodara, Noida, Gurugram) with circuity multiplier.
5. **Temporal Seasonality**:
   - Q4 festival surge (October/November Diwali season) elevates order volume and transit congestion.
   - Monsoon months (July/August) trigger weather disruptions.
   - Sunday / weekend volumes reflect operational freight consolidation cycles.

---

## 5. Execution Instructions

### Regenerating the Dataset

To re-run the generator and regenerate all three CSV files deterministically:

```bash
python data/synthetic/generate_supply_chain_data.py
```

### Validating the Dataset

To execute the automated validation suite (checks schema, FK integrity, date constraints, non-negativity, delay math, and scenario existence):

```bash
python data/synthetic/validate_supply_chain_data.py
```

### Viewing Dataset Summary & Statistics

To view the statistical breakdown across transport modes, product categories, priorities, and supplier tiers:

```bash
python data/synthetic/dataset_summary.py
```
