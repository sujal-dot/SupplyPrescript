# SupplyPrescript — Processed Dataset

## Pipeline

```
Raw CSV (data/synthetic/shipments.csv)
  ↓  Load & Schema Validation
  ↓  Initial Profiling
  ↓  Missing Value Handling
  ↓  Duplicate Removal
  ↓  Date Parsing & Validation
  ↓  Lead-Time Recalculation
  ↓  Negative Quantity Handling
  ↓  Numerical Value Validation
  ↓  Categorical Normalization
  ↓  Delay Recalculation
  ↓  Reference Validation (suppliers/products)
  ↓  Feature Engineering
  ↓  Final Validation
  ↓  Save (data/processed/shipments_processed.csv)
```

## Cleaning Rules

| Issue | Strategy |
|---|---|
| Missing critical IDs (`shipment_id`, `supplier_id`, `product_id`) | Row removed |
| Missing categorical fields (`origin`, `destination`, `priority`, `transport_mode`) | Filled with `"Unknown"` |
| Missing numeric fields (`quantity`, `unit_cost`, etc.) | Group-level median (by `supplier_id`), falling back to global median |
| Missing `order_date` | Row removed (cannot reconstruct) |
| Missing `expected_delivery_date` | Reconstructed from `order_date + lead_time` |
| Missing `actual_delivery_date` | Reconstructed from `expected_delivery_date + delay_days` |
| Duplicate rows | First valid record kept |
| Duplicate `shipment_id` | Most complete record kept |
| `expected_delivery_date < order_date` | Dates swapped |
| `actual_delivery_date < order_date` | `actual_delivery_date` set to `order_date` |
| `lead_time` inconsistent with dates | Recalculated from `actual_delivery_date - order_date` |
| `delay_days` inconsistent with dates | Recalculated from `max(0, actual − expected)` |
| `quantity < 0` | Sign-flip correction (data-entry error) |
| `quantity <= 0` | Imputed with product-level median |
| `unit_cost <= 0` | Imputed with product-level median |
| `shipping_cost < 0` | Absolute value taken |
| `inventory_level < 0` | Clipped to 0 |
| `demand < 0` | Absolute value taken |
| `supplier_reliability` as percentage (70–99) | Divided by 100 |
| `supplier_reliability` outside [0,1] | Clipped to [0,1] |
| `delay_days < 0` | Set to 0 |
| Invalid `transport_mode` | Mapped to canonical value or `"Unknown"` |
| Invalid `priority` | Mapped to canonical value or `"Unknown"` |
| Orphan `supplier_id` (not in suppliers.csv) | Row removed |
| Orphan `product_id` (not in products.csv) | Row removed |

## Engineered Features

| Feature | Description |
|---|---|
| `is_delayed` | 1 if `delay_days > 0`, else 0 |
| `delivery_status` | `"On Time"` or `"Delayed"` |
| `inventory_shortage` | 1 if `inventory_level < demand`, else 0 |
| `inventory_coverage_ratio` | `inventory_level / demand` (∞ when demand = 0) |
| `total_product_cost` | `quantity × unit_cost` |
| `total_cost` | `total_product_cost + shipping_cost` |
| `order_year` | Year extracted from `order_date` |
| `order_month` | Month (1–12) extracted from `order_date` |
| `order_quarter` | Quarter (1–4) extracted from `order_date` |
| `order_day_of_week` | Day-of-week (0=Monday, 6=Sunday) |
| `is_weekend_order` | 1 if order placed on Saturday or Sunday |
| `lead_time_category` | Tertile-based: `Short`, `Medium`, `Long` |
| `lead_time_outlier` | 1 if `lead_time` is a statistical IQR outlier |

## Data Leakage Warning

> **IMPORTANT**: The following fields represent **post-delivery outcomes**.
> They must **NOT** be used as predictive input features when building models
> that predict shipment outcomes **before** the actual delivery date.

| Field | Why it's a leakage risk |
|---|---|
| `actual_delivery_date` | Known only after delivery |
| `delay_days` | Derived from `actual_delivery_date` |
| `delivery_status` | Derived from `delay_days` |
| `is_delayed` | Derived from `delay_days` |
| `lead_time` | Recalculated from actual dates (post-delivery) |
| `lead_time_outlier` | Derived from `lead_time` |

Pre-delivery safe features include: `order_date`, `expected_delivery_date`,
`supplier_id`, `product_id`, `origin`, `destination`, `transport_mode`,
`priority`, `quantity`, `unit_cost`, `shipping_cost`, `supplier_reliability`,
`inventory_level`, `demand`, and all engineered date/cost features that do
not rely on actual delivery information.

## File Descriptions

| File | Description |
|---|---|
| `shipments_processed.csv` | Cleaned and feature-engineered shipment dataset |
| `validation_report.json` | Summary of validation checks and data-quality metrics |
| `cleaning_report.json` | Detailed record of all cleaning operations performed |
| `README.md` | This documentation file |
