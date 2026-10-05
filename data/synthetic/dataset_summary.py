"""
SupplyPrescript - Synthetic Dataset Summary
Computes and prints statistical summaries and distribution breakdowns for the supply chain dataset.
"""

from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SUPPLIERS_CSV = SCRIPT_DIR / "suppliers.csv"
PRODUCTS_CSV = SCRIPT_DIR / "products.csv"
SHIPMENTS_CSV = SCRIPT_DIR / "shipments.csv"


def main():
    if not SHIPMENTS_CSV.exists() or not SUPPLIERS_CSV.exists() or not PRODUCTS_CSV.exists():
        print("Error: Dataset CSV files not found. Run generate_supply_chain_data.py first.")
        return

    shipments = pd.read_csv(SHIPMENTS_CSV)
    suppliers = pd.read_csv(SUPPLIERS_CSV)
    products = pd.read_csv(PRODUCTS_CSV)

    # Merge product category and supplier name for breakdown
    shipments_enriched = shipments.merge(
        products[["product_id", "category"]], on="product_id", how="left"
    ).merge(
        suppliers[["supplier_id", "supplier_name"]], on="supplier_id", how="left"
    )

    total_shipments = len(shipments)
    total_suppliers = len(suppliers)
    total_products = len(products)

    avg_qty = shipments["quantity"].mean()
    avg_unit_cost = shipments["unit_cost"].mean()
    avg_shipping_cost = shipments["shipping_cost"].mean()
    avg_lead_time = shipments["lead_time"].mean()
    avg_delay = shipments["delay_days"].mean()

    delayed_count = (shipments["delay_days"] > 0).sum()
    delayed_pct = (delayed_count / total_shipments) * 100
    ontime_pct = 100.0 - delayed_pct

    shortage_count = (shipments["inventory_level"] < shipments["demand"]).sum()
    shortage_pct = (shortage_count / total_shipments) * 100

    avg_reliability = shipments["supplier_reliability"].mean()

    print("================================================================================")
    print("                      SUPPLYPRESCRIPT DATASET SUMMARY                           ")
    print("================================================================================")
    print(f"Total shipments:            {total_shipments:,}")
    print(f"Total suppliers:            {total_suppliers}")
    print(f"Total products:             {total_products}")
    print(f"Date range:                 {shipments['order_date'].min()} to {shipments['order_date'].max()}")
    print("--------------------------------------------------------------------------------")
    print(f"Average quantity:           {avg_qty:,.2f} units")
    print(f"Average unit cost:          ${avg_unit_cost:,.2f}")
    print(f"Average shipping cost:      ${avg_shipping_cost:,.2f}")
    print(f"Average lead time:          {avg_lead_time:.2f} days")
    print(f"Average delay:              {avg_delay:.2f} days")
    print("--------------------------------------------------------------------------------")
    print(f"Delayed shipment %:         {delayed_pct:.2f}% ({delayed_count:,} shipments)")
    print(f"On-time shipment %:         {ontime_pct:.2f}% ({total_shipments - delayed_count:,} shipments)")
    print(f"Inventory shortage %:       {shortage_pct:.2f}% ({shortage_count:,} shipments)")
    print(f"Average supplier reliability: {avg_reliability:.4f}")
    print("================================================================================")

    print("\n[Shipments by Transport Mode]")
    mode_counts = shipments["transport_mode"].value_counts()
    mode_pcts = shipments["transport_mode"].value_counts(normalize=True) * 100
    for mode, count in mode_counts.items():
        print(f"  - {mode:<10}: {count:>6,} ({mode_pcts[mode]:>5.2f}%)")

    print("\n[Shipments by Priority]")
    prio_counts = shipments["priority"].value_counts()
    prio_pcts = shipments["priority"].value_counts(normalize=True) * 100
    for prio, count in prio_counts.items():
        print(f"  - {prio:<10}: {count:>6,} ({prio_pcts[prio]:>5.2f}%)")

    print("\n[Shipments by Product Category]")
    cat_counts = shipments_enriched["category"].value_counts()
    cat_pcts = shipments_enriched["category"].value_counts(normalize=True) * 100
    for cat, count in cat_counts.items():
        print(f"  - {cat:<16}: {count:>6,} ({cat_pcts[cat]:>5.2f}%)")

    print("\n[Top 10 Suppliers by Shipment Volume]")
    sup_counts = shipments_enriched.groupby(["supplier_id", "supplier_name"]).size().sort_values(ascending=False).head(10)
    for (sid, sname), count in sup_counts.items():
        pct = (count / total_shipments) * 100
        print(f"  - {sid} ({sname[:28]:<28}): {count:>5,} ({pct:>4.2f}%)")

    print("\n[Bottom 5 Suppliers by Reliability (High-Risk Delays)]")
    bottom_sup = suppliers.sort_values(by="supplier_reliability").head(5)
    for _, row in bottom_sup.iterrows():
        sup_shipments = shipments[shipments["supplier_id"] == row["supplier_id"]]
        sup_delay_pct = (sup_shipments["delay_days"] > 0).mean() * 100 if len(sup_shipments) > 0 else 0.0
        print(f"  - {row['supplier_id']} ({row['supplier_name'][:26]:<26}): Reliability={row['supplier_reliability']:.2f}, Delay Rate={sup_delay_pct:>5.1f}%")

    print("================================================================================")


if __name__ == "__main__":
    main()
