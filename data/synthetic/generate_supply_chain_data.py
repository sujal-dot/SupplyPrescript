"""
SupplyPrescript - Synthetic Supply Chain Data Generator
Generates realistic historical supply-chain datasets for ML & Prescriptive Analytics.
Seed: 42 (Reproducible)
"""

import math
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
SEED = 42
NUM_SHIPMENTS = 15000
NUM_SUPPLIERS = 50
NUM_PRODUCTS = 100

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

SCRIPT_DIR = Path(__file__).resolve().parent
SUPPLIERS_CSV = SCRIPT_DIR / "suppliers.csv"
PRODUCTS_CSV = SCRIPT_DIR / "products.csv"
SHIPMENTS_CSV = SCRIPT_DIR / "shipments.csv"

# Geographic coordinates for the 16 Indian logistics hubs
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Delhi": (28.7041, 77.1025),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Hyderabad": (17.3850, 78.4867),
    "Ahmedabad": (23.0225, 72.5714),
    "Surat": (21.1702, 72.8311),
    "Nagpur": (21.1458, 79.0882),
    "Kolkata": (22.5726, 88.3639),
    "Jaipur": (26.9124, 75.7873),
    "Indore": (22.7196, 75.8577),
    "Nashik": (19.9975, 73.7898),
    "Vadodara": (22.3072, 73.1812),
    "Noida": (28.5355, 77.3910),
    "Gurugram": (28.4595, 77.0266),
}

CITIES = list(CITY_COORDINATES.keys())
PORT_CITIES = {"Mumbai", "Chennai", "Kolkata", "Surat"}

# Destination consumption weights (major demand centers)
DESTINATION_WEIGHTS: Dict[str, float] = {
    "Delhi": 0.12,
    "Mumbai": 0.12,
    "Bengaluru": 0.10,
    "Chennai": 0.08,
    "Hyderabad": 0.08,
    "Kolkata": 0.07,
    "Pune": 0.07,
    "Ahmedabad": 0.06,
    "Noida": 0.05,
    "Gurugram": 0.05,
    "Surat": 0.04,
    "Jaipur": 0.04,
    "Nagpur": 0.03,
    "Indore": 0.03,
    "Vadodara": 0.03,
    "Nashik": 0.03,
}

CATEGORIES = [
    "Electronics",
    "Automotive",
    "Industrial",
    "Consumer Goods",
    "Pharmaceutical",
    "Food",
    "Textile",
    "Machinery",
]


def calculate_distance_km(orig: str, dest: str) -> int:
    """Calculate realistic road/transit distance between two hubs using Haversine formula + circuity factor."""
    if orig == dest:
        return 35
    lat1, lon1 = CITY_COORDINATES[orig]
    lat2, lon2 = CITY_COORDINATES[dest]
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    r = 6371.0  # Earth radius in km
    circuity = 1.25  # Highway route circuity factor
    return max(35, int(round(r * c * circuity)))


# ---------------------------------------------------------
# 1. SUPPLIERS DATA GENERATION
# ---------------------------------------------------------
def generate_suppliers(rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate 50 realistic suppliers with varied reliability, base lead time, and capacity.
    IDs: SUP001 to SUP050
    Reliability: 0.70 to 0.99
    """
    supplier_names = [
        # Electronics
        ("Apex Micro Electronics", "Electronics", "Bengaluru"),
        ("Havells Industrial Components", "Electronics", "Noida"),
        ("Siemens Energy Electricals", "Electronics", "Gurugram"),
        ("ABB Power Automation", "Electronics", "Bengaluru"),
        ("Delta Circuit Systems", "Electronics", "Chennai"),
        ("Beltron Electronics Ltd", "Electronics", "Pune"),
        # Automotive
        ("Bharat Precision Forge", "Automotive", "Pune"),
        ("Mahindra Auto Ancillaries", "Automotive", "Nashik"),
        ("Sundram Fasteners Works", "Automotive", "Chennai"),
        ("Motherson Sumi Components", "Automotive", "Noida"),
        ("Bosch India Engineering", "Automotive", "Bengaluru"),
        ("Minda Auto Controls", "Automotive", "Gurugram"),
        ("TVS Dynamic Castings", "Automotive", "Chennai"),
        # Industrial
        ("Tata Metaliks Industrial", "Industrial", "Kolkata"),
        ("Larsen Hydraulic Systems", "Industrial", "Mumbai"),
        ("Kirloskar Fluid Pumps", "Industrial", "Pune"),
        ("Jindal Steel Extrusions", "Industrial", "Nagpur"),
        ("JSW Industrial Coils", "Industrial", "Mumbai"),
        ("Hindalco Alloy Works", "Industrial", "Surat"),
        ("Thermax Boiler Solutions", "Industrial", "Pune"),
        # Consumer Goods
        ("Godrej Consumer Hardware", "Consumer Goods", "Mumbai"),
        ("Wipro Consumer Packaging", "Consumer Goods", "Bengaluru"),
        ("Marico Polymer Containers", "Consumer Goods", "Ahmedabad"),
        ("Dabur Essentials Supply", "Consumer Goods", "Delhi"),
        ("ITC Paperboards Division", "Consumer Goods", "Kolkata"),
        ("Crompton Appliances Supply", "Consumer Goods", "Vadodara"),
        # Pharmaceutical
        ("Sun Pharma Bulk Actives", "Pharmaceutical", "Vadodara"),
        ("Cipla Formulation Labs", "Pharmaceutical", "Mumbai"),
        ("Dr Reddys API Works", "Pharmaceutical", "Hyderabad"),
        ("Aurobindo Pharma Bulk", "Pharmaceutical", "Hyderabad"),
        ("Lupin Generics Supply", "Pharmaceutical", "Pune"),
        ("Torrent Pharma Chemicals", "Pharmaceutical", "Ahmedabad"),
        # Food
        ("Britannia Foods Logistics", "Food", "Kolkata"),
        ("Adani Wilmar Edible Oils", "Food", "Ahmedabad"),
        ("Amul Dairy Ingredients", "Food", "Vadodara"),
        ("Tata Consumer Products", "Food", "Mumbai"),
        ("Patanjali Agro Supplies", "Food", "Delhi"),
        ("Vadilal Agro Processors", "Food", "Surat"),
        # Textile
        ("Arvind Denim & Textiles", "Textile", "Ahmedabad"),
        ("Raymond Fabric Mills", "Textile", "Nashik"),
        ("Vardhman Synthetic Yarns", "Textile", "Jaipur"),
        ("Welspun Global Home", "Textile", "Surat"),
        ("Alok Industries Cotton", "Textile", "Mumbai"),
        ("Sutlej Spinning Mills", "Textile", "Indore"),
        # Machinery
        ("BHEL Heavy Engineering", "Machinery", "Nagpur"),
        ("Escorts Heavy Equipment", "Machinery", "Delhi"),
        ("Voltas Industrial Machinery", "Machinery", "Mumbai"),
        ("Blue Star Heavy Chillers", "Machinery", "Ahmedabad"),
        ("Cummins Diesel Engines", "Machinery", "Pune"),
        ("Action Construction Equip", "Machinery", "Jaipur"),
    ]

    # Predefined distribution of reliability tiers to ensure high variance:
    # 10 low-reliability suppliers (0.70 - 0.82) -> higher delays
    # 15 medium-reliability suppliers (0.83 - 0.91)
    # 25 high-reliability suppliers (0.92 - 0.99)
    reliabilities = []
    reliabilities.extend(np.round(rng.uniform(0.70, 0.82, size=10), 2))
    reliabilities.extend(np.round(rng.uniform(0.83, 0.91, size=15), 2))
    reliabilities.extend(np.round(rng.uniform(0.92, 0.99, size=25), 2))
    rng.shuffle(reliabilities)

    suppliers = []
    for idx, (name, category, origin) in enumerate(supplier_names, start=1):
        sup_id = f"SUP{idx:03d}"
        reliability = float(reliabilities[idx - 1])
        base_lead = int(rng.choice([2, 3, 4, 5, 6, 7], p=[0.15, 0.25, 0.30, 0.15, 0.10, 0.05]))
        if reliability < 0.80:
            base_lead = min(7, base_lead + 1)
        capacity = int(rng.integers(8, 46) * 1000)

        suppliers.append({
            "supplier_id": sup_id,
            "supplier_name": name,
            "category": category,
            "origin": origin,
            "supplier_reliability": reliability,
            "base_lead_time": base_lead,
            "capacity": capacity,
        })

    return pd.DataFrame(suppliers)


# ---------------------------------------------------------
# 2. PRODUCTS DATA GENERATION
# ---------------------------------------------------------
def generate_products(rng: np.random.Generator) -> pd.DataFrame:
    """
    Generate 100 realistic products across 8 categories with varied unit costs, weights, and base demand.
    IDs: PROD001 to PROD100
    """
    product_catalogs = {
        "Electronics": [
            ("STM32 Microcontroller IC", 45.0, 0.15, 650),
            ("High-Voltage Power Supply 24V", 125.0, 1.8, 380),
            ("Multi-Layer PCB Board Assembly", 85.0, 0.45, 520),
            ("Industrial Optical Sensor 50m", 160.0, 0.35, 290),
            ("TFT LCD Display Module 7-inch", 110.0, 0.65, 410),
            ("Heavy-Duty Amphenol Connector", 28.0, 0.25, 850),
            ("Lithium Iron Phosphate Cell Pack", 240.0, 4.2, 220),
            ("Solid State Relay 40A", 55.0, 0.40, 580),
            ("Pure Sine Wave Inverter 1kVA", 320.0, 6.5, 180),
            ("Electrolytic Capacitor 450V Pack", 35.0, 0.50, 750),
            ("Toroidal Power Transformer", 145.0, 5.0, 240),
            ("ARM Cortex Edge Computing Kit", 380.0, 0.85, 160),
            ("Digital Temperature Transmitter", 195.0, 0.90, 210),
            ("Brushless DC Motor Driver 48V", 175.0, 1.2, 270),
            ("Industrial Ethernet Switch 8-Port", 290.0, 2.1, 190),
        ],
        "Automotive": [
            ("Hydraulic Disc Brake Caliper", 145.0, 6.2, 320),
            ("Heavy-Duty Alternator 120A", 260.0, 8.5, 210),
            ("Common Rail Fuel Injector", 185.0, 1.4, 380),
            ("Aluminum Engine Radiator Core", 210.0, 7.8, 250),
            ("Iridium Spark Plug 4-Pack", 42.0, 0.45, 950),
            ("EPDM Serpentine Drive Belt", 32.0, 0.80, 820),
            ("Tempered Steel Suspension Spring", 88.0, 11.5, 340),
            ("Ceramic Friction Clutch Plate", 175.0, 5.4, 280),
            ("Power Steering Rack Assembly", 420.0, 14.0, 140),
            ("Spin-On Engine Oil Filter", 18.0, 0.60, 1600),
            ("LED Matrix Headlight Assembly", 310.0, 4.5, 190),
            ("Cast Iron Exhaust Manifold", 195.0, 12.8, 170),
            ("Front Wheel Hub Bearing Kit", 115.0, 4.2, 420),
            ("Variable Valve Timing Solenoid", 95.0, 0.75, 460),
            ("Automotive Turbocharger Cartridge", 580.0, 9.2, 110),
        ],
        "Industrial": [
            ("Double-Acting Hydraulic Cylinder", 480.0, 28.0, 120),
            ("Pneumatic Control Valve 2-inch", 240.0, 6.5, 260),
            ("Cast Iron Centrifugal Slurry Pump", 850.0, 55.0, 85),
            ("Deep Groove Ball Bearing 120mm", 75.0, 3.2, 540),
            ("Reinforced Rubber Conveyor Belt 20m", 620.0, 72.0, 70),
            ("Spiral Wound Metallic Gasket 50-Pk", 65.0, 2.1, 620),
            ("Helical Bevel Speed Reducer", 1150.0, 88.0, 50),
            ("Digital Pressure Gauge 600 Bar", 185.0, 1.1, 310),
            ("Explosion-Proof Solenoid Valve", 295.0, 4.8, 190),
            ("Wire-Braided Hydraulic Hose 50m", 340.0, 32.0, 150),
            ("Electromagnetic Flow Meter DN80", 720.0, 16.5, 95),
            ("Forged Carbon Steel Flange ANSI 300", 110.0, 9.5, 380),
            ("Pneumatic Actuator Rotary 90-Deg", 360.0, 12.0, 140),
            ("Mechanical Face Seal Cartridge", 215.0, 2.8, 280),
            ("Vibration Damper Mount Set", 90.0, 5.0, 410),
        ],
        "Consumer Goods": [
            ("Airtight Food Storage Container Set", 18.5, 1.2, 1400),
            ("Ultra-Clean Laundry Detergent 5L", 14.0, 5.4, 2100),
            ("Stainless Steel Cutlery Set 24-Pc", 28.0, 1.8, 950),
            ("Energy Efficient LED Bulb 12W 10-Pk", 22.0, 0.9, 1850),
            ("Heavy-Duty Storage Crate 60L", 26.0, 3.1, 1100),
            ("Tempered Glass Drinkware 6-Pc", 16.0, 2.2, 1300),
            ("Ceramic Coffee Mug 4-Pack", 12.5, 1.5, 1500),
            ("Absorbent Paper Towel 12-Rolls", 15.0, 2.8, 2200),
            ("BPA-Free Tritan Water Bottle 1L", 9.5, 0.35, 2600),
            ("Multipurpose Kitchen Cleaner 1L", 6.5, 1.1, 2800),
            ("Automatic Soap Dispenser Sensor", 24.0, 0.65, 1250),
            ("Modular Wardrobe Organizer Rack", 42.0, 4.8, 720),
            ("Microfiber Dusting Cloth 10-Pk", 8.0, 0.40, 3100),
            ("Non-Stick Aluminium Fry Pan 28cm", 34.0, 1.4, 880),
            ("Thermal Insulated Lunch Bag", 17.0, 0.55, 1650),
        ],
        "Pharmaceutical": [
            ("Paracetamol Active Ingredient 25kg", 185.0, 26.0, 380),
            ("Amoxicillin Trihydrate Powder 10kg", 320.0, 10.5, 240),
            ("Sterile Normal Saline 500ml 24-Pk", 36.0, 13.0, 920),
            ("Recombinant Human Insulin Vials 10-Pk", 450.0, 0.8, 410),
            ("Ibuprofen Granules Bulk 20kg", 210.0, 20.8, 310),
            ("Antitussive Cough Syrup 100ml 50-Pk", 68.0, 8.5, 780),
            ("Ciprofloxacin Blister Pack 100-Tabs", 52.0, 0.45, 1150),
            ("Nitrile Examination Gloves 1000-Ct", 75.0, 5.2, 850),
            ("Povidone Iodine Antiseptic 5L", 48.0, 5.6, 680),
            ("Ascorbic Acid Vitamin C 25kg", 165.0, 25.5, 450),
        ],
        "Food": [
            ("Premium Basmati Rice Bag 25kg", 38.0, 25.2, 1400),
            ("Refined Sunflower Cooking Oil 15L", 32.0, 14.5, 1650),
            ("Stone-Ground Whole Wheat Atta 20kg", 18.0, 20.1, 2200),
            ("Refined Plantation Sugar 50kg", 35.0, 50.2, 1250),
            ("Skimmed Milk Powder Bulk 25kg", 85.0, 25.4, 620),
            ("Organic Garam Masala Blend 5kg", 54.0, 5.2, 850),
            ("Assam CTC Black Tea Bulk 20kg", 95.0, 20.3, 540),
            ("Arabica Roasted Coffee Beans 10kg", 140.0, 10.2, 410),
            ("Split Red Lentils Masoor Dal 25kg", 29.0, 25.1, 1550),
            ("Aseptic Tomato Puree Paste Drum 50kg", 62.0, 52.0, 480),
        ],
        "Textile": [
            ("Combed Cotton Yarn Cone 24-Pk", 92.0, 24.5, 480),
            ("Dyed Polyester Knitted Fabric 50m", 115.0, 18.0, 410),
            ("Raw Heavy Denim Indigo Bolt 30m", 145.0, 26.0, 320),
            ("Pure Mulberry Silk Yarn Spool", 280.0, 2.5, 190),
            ("Bonded Nylon Sewing Thread 10-Spools", 38.0, 3.2, 820),
            ("Single Jersey Cotton Roll 25kg", 88.0, 25.3, 530),
            ("Merino Wool Blend Suiting 20m", 240.0, 12.0, 210),
            ("High-Tenacity Webbing Strap 100m", 64.0, 8.5, 610),
            ("Natural Washed Linen Fabric 30m", 175.0, 10.5, 290),
            ("Heavy Waterproof Canvas Roll 25m", 130.0, 22.0, 360),
        ],
        "Machinery": [
            ("CNC Lathe Hydraulic Chuck 10-inch", 850.0, 45.0, 85),
            ("Three-Phase Induction Motor 15kW", 1250.0, 95.0, 60),
            ("Rotary Screw Air Compressor 10HP", 2800.0, 220.0, 35),
            ("Industrial Centrifugal Blower 5.5kW", 980.0, 68.0, 75),
            ("Tungsten Carbide Milling Cutter Set", 620.0, 8.5, 140),
            ("Vertical Hydraulic Press Ram 30-Ton", 3800.0, 380.0, 20),
            ("Multi-Process Inverter Welder 400A", 1450.0, 38.0, 55),
            ("Heavy-Duty Planetary Gearhead", 1950.0, 110.0, 45),
            ("Industrial Scroll Chiller Pump Unit", 2200.0, 160.0, 40),
            ("Fiber Laser Cutting Precision Head", 4200.0, 24.0, 25),
        ],
    }

    products = []
    prod_counter = 1
    for category in CATEGORIES:
        for name, unit_cost, weight_kg, base_demand in product_catalogs[category]:
            prod_id = f"PROD{prod_counter:03d}"
            products.append({
                "product_id": prod_id,
                "product_name": name,
                "category": category,
                "unit_cost": float(unit_cost),
                "weight_kg": float(weight_kg),
                "base_demand": int(base_demand),
            })
            prod_counter += 1

    return pd.DataFrame(products)


# ---------------------------------------------------------
# 3. SHIPMENT GENERATION HELPERS
# ---------------------------------------------------------
def generate_order_dates(num_records: int, rng: np.random.Generator) -> List[date]:
    """
    Generate realistic historical dates between 2023-01-01 and 2025-12-31.
    Includes day-of-week seasonality (Mon-Fri peak), annual growth trend, and Q4 festive spikes.
    """
    total_days = (END_DATE - START_DATE).days + 1
    day_weights = []

    for d in range(total_days):
        cur_date = START_DATE + timedelta(days=d)
        year_factor = 0.90 + (cur_date.year - 2023) * 0.10
        dow = cur_date.weekday()
        if dow == 6:  # Sunday
            dow_factor = 0.40
        elif dow == 5:  # Saturday
            dow_factor = 0.75
        else:
            dow_factor = 1.15

        month = cur_date.month
        if month in [10, 11]:  # Festival season (Diwali)
            month_factor = 1.35
        elif month == 12:  # Year-end push
            month_factor = 1.25
        elif month == 3:  # Fiscal year-end close
            month_factor = 1.20
        elif month in [7, 8]:  # Monsoon slowdown
            month_factor = 0.85
        else:
            month_factor = 1.00

        spike = 1.6 if (d % 37 == 0) else 1.0
        weight = year_factor * dow_factor * month_factor * spike
        day_weights.append(weight)

    day_probs = np.array(day_weights) / sum(day_weights)
    chosen_day_offsets = rng.choice(total_days, size=num_records, replace=True, p=day_probs)
    chosen_day_offsets.sort()
    return [START_DATE + timedelta(days=int(offset)) for offset in chosen_day_offsets]


def choose_transport_mode(
    origin: str,
    destination: str,
    distance_km: int,
    category: str,
    weight_kg: float,
    priority: str,
    rng: np.random.Generator,
) -> str:
    """
    Assign transport mode based on route, product characteristics, and priority.
    Target distribution:
      Road: ~58-60% (most common)
      Rail: ~22-25% (moderate)
      Sea:  ~10-12% (moderate)
      Air:  ~5-7%   (least common)
    """
    is_coastal_route = (origin in PORT_CITIES or destination in PORT_CITIES)
    is_high_value = category in ["Electronics", "Pharmaceutical"]
    is_heavy_bulk = category in ["Machinery", "Industrial", "Food"] or (weight_kg > 30)

    # Air is least common: reserved for Critical urgent or high-value long-distance
    if priority == "Critical" and rng.random() < 0.28:
        return "Air"
    if is_high_value and distance_km > 1000 and rng.random() < 0.14:
        return "Air"

    # Sea candidate: coastal route or heavy bulk long distance
    if is_coastal_route and distance_km > 600 and rng.random() < 0.24:
        return "Sea"

    # Rail candidate: heavy bulk medium-long distance
    if is_heavy_bulk and distance_km > 550 and rng.random() < 0.32:
        return "Rail"

    # Probabilistic fallback to match exact realistic target proportions:
    # Road (~58%), Rail (~22%), Sea (~13%), Air (~7%)
    roll = rng.random()
    if is_coastal_route:
        if roll < 0.52:
            return "Road"
        elif roll < 0.72:
            return "Rail"
        elif roll < 0.94:
            return "Sea"
        else:
            return "Air"
    else:
        # Inland-to-inland routes: Road, Rail, Air only
        if roll < 0.68:
            return "Road"
        elif roll < 0.93:
            return "Rail"
        else:
            return "Air"


def calculate_transit_lead_time(mode: str, distance_km: int, base_lead: int) -> int:
    """Calculate expected transit lead time based on mode, distance, and supplier handling."""
    if mode == "Air":
        transit_days = 1 if distance_km <= 1000 else 2
    elif mode == "Road":
        transit_days = max(1, int(math.ceil(distance_km / 450)))
    elif mode == "Rail":
        transit_days = max(2, int(math.ceil(distance_km / 350)) + 1)
    else:  # Sea
        transit_days = max(4, int(math.ceil(distance_km / 250)) + 3)

    return base_lead + transit_days


# ---------------------------------------------------------
# 4. MAIN SHIPMENT GENERATOR
# ---------------------------------------------------------
def generate_shipments(
    suppliers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    num_records: int = NUM_SHIPMENTS,
    seed: int = SEED,
) -> pd.DataFrame:
    """
    Generate 15,000 realistic shipment records with correlated supply-chain dynamics.
    """
    rng = np.random.default_rng(seed)
    order_dates = generate_order_dates(num_records, rng)

    # Build lookup dictionaries for fast access
    suppliers_by_category: Dict[str, List[dict]] = {}
    for _, row in suppliers_df.iterrows():
        cat = row["category"]
        if cat not in suppliers_by_category:
            suppliers_by_category[cat] = []
        suppliers_by_category[cat].append(row.to_dict())

    products_list = products_df.to_dict(orient="records")
    prod_weights = np.array([p["base_demand"] for p in products_list], dtype=float)
    prod_weights = prod_weights ** 0.6
    prod_probs = prod_weights / prod_weights.sum()

    shipments = []

    for i in range(num_records):
        shipment_id = f"SHIP{i + 1:06d}"
        order_date = order_dates[i]

        # 1. Product Selection
        prod = products_list[rng.choice(len(products_list), p=prod_probs)]
        prod_id = prod["product_id"]
        prod_category = prod["category"]
        prod_base_cost = prod["unit_cost"]
        prod_weight = prod["weight_kg"]
        prod_base_demand = prod["base_demand"]

        # 2. Supplier Selection (domain-matched supplier)
        candidate_suppliers = suppliers_by_category[prod_category]
        supplier = candidate_suppliers[rng.choice(len(candidate_suppliers))]
        sup_id = supplier["supplier_id"]
        origin = supplier["origin"]
        sup_reliability = float(supplier["supplier_reliability"])
        base_lead_time = int(supplier["base_lead_time"])
        supplier_capacity = int(supplier["capacity"])

        # 3. Destination (different from origin)
        dest_candidates = [c for c in CITIES if c != origin]
        dest_weights = np.array([DESTINATION_WEIGHTS[c] for c in dest_candidates])
        dest_weights /= dest_weights.sum()
        destination = dest_candidates[rng.choice(len(dest_candidates), p=dest_weights)]
        distance_km = calculate_distance_km(origin, destination)

        # 4. Demand Calculation
        dow = order_date.weekday()
        dow_mult = 1.15 if dow < 5 else (0.85 if dow == 5 else 0.50)
        month = order_date.month
        if month in [10, 11]:
            month_mult = 1.30
        elif month == 12:
            month_mult = 1.20
        elif month == 3:
            month_mult = 1.15
        elif month in [7, 8]:
            month_mult = 0.88
        else:
            month_mult = 1.00

        # Demand spike (~4.5% chance)
        is_spike = rng.random() < 0.045
        spike_factor = rng.uniform(1.6, 2.4) if is_spike else 1.0
        noise = rng.normal(1.0, 0.10)
        demand = max(10, int(round(prod_base_demand * dow_mult * month_mult * spike_factor * noise)))

        # 5. Inventory Level & Shortage Simulation
        # Target: ~8-12% inventory shortage situations (inventory_level < demand)
        shortage_prob = 0.08
        if is_spike:
            shortage_prob += 0.35
        if sup_reliability < 0.80:
            shortage_prob += 0.08

        is_shortage = rng.random() < shortage_prob
        if is_shortage:
            shortage_ratio = rng.uniform(0.15, 0.85)
            inventory_level = max(0, int(round(demand * shortage_ratio)))
        else:
            inv_ratio = rng.uniform(1.08, 2.40)
            inventory_level = int(round(demand * inv_ratio))

        # 6. Priority Assignment
        # Target overall: Low ~20%, Medium ~50%, High ~25%, Critical ~5%
        # Strong correlation with shortages
        if is_shortage:
            priority = rng.choice(["Low", "Medium", "High", "Critical"], p=[0.02, 0.18, 0.56, 0.24])
        else:
            priority = rng.choice(["Low", "Medium", "High", "Critical"], p=[0.22, 0.53, 0.22, 0.03])

        # 7. Quantity
        if is_shortage:
            deficit = demand - inventory_level
            order_qty = int(round(deficit + demand * rng.uniform(0.3, 0.7)))
        else:
            order_qty = int(round(demand * rng.uniform(0.5, 1.15)))

        if prod_category == "Machinery":
            quantity = max(10, min(180, order_qty))
        elif prod_category in ["Industrial", "Automotive"]:
            quantity = max(15, min(1200, order_qty))
        elif prod_category == "Electronics":
            quantity = max(25, min(2500, order_qty))
        elif prod_category == "Pharmaceutical":
            quantity = max(20, min(2000, order_qty))
        else:  # Consumer Goods, Food, Textile
            quantity = max(50, min(5000, order_qty))

        # 8. Transport Mode
        transport_mode = choose_transport_mode(
            origin=origin,
            destination=destination,
            distance_km=distance_km,
            category=prod_category,
            weight_kg=prod_weight,
            priority=priority,
            rng=rng,
        )

        # 9. Expected Delivery Date
        expected_lead_time = calculate_transit_lead_time(transport_mode, distance_km, base_lead_time)
        expected_delivery_date = order_date + timedelta(days=expected_lead_time)

        # 10. Delays & Actual Delivery Date
        p_sup = (0.99 - sup_reliability) * 1.55

        mode_delay_bias = {
            "Air": 0.05,
            "Road": 0.12,
            "Rail": 0.15,
            "Sea": 0.18,
        }[transport_mode]

        distance_bias = 0.04 if distance_km > 1000 else 0.0
        weather_bias = 0.06 if month in [7, 8] else (0.04 if month in [10, 11] else 0.0)
        capacity_bias = 0.05 if (quantity * 10 > supplier_capacity) else 0.0
        priority_mitigation = 0.06 if priority == "Critical" else (0.02 if priority == "High" else 0.0)

        total_delay_prob = np.clip(
            p_sup + mode_delay_bias + distance_bias + weather_bias + capacity_bias - priority_mitigation,
            0.04,
            0.75,
        )

        # Overall target delayed shipments: 15% - 30% (calibrated ~21-23%)
        is_delayed = rng.random() < (total_delay_prob * 0.72)

        if is_delayed:
            delay_tier = rng.choice(["minor", "moderate", "severe", "extreme"], p=[0.60, 0.25, 0.12, 0.03])
            if delay_tier == "minor":
                delay_days = int(rng.integers(1, 4))
            elif delay_tier == "moderate":
                delay_days = int(rng.integers(4, 8))
            elif delay_tier == "severe":
                delay_days = int(rng.integers(8, 15))
            else:
                delay_days = int(rng.integers(15, 25))

            if sup_reliability < 0.85 and rng.random() < 0.55:
                delay_reason = "Supplier Issue"
            elif weather_bias > 0 and rng.random() < 0.40:
                delay_reason = "Weather"
            elif capacity_bias > 0 and rng.random() < 0.35:
                delay_reason = "Capacity Constraint"
            elif is_shortage and rng.random() < 0.30:
                delay_reason = "Inventory Constraint"
            else:
                delay_reason = "Transportation Issue"
        else:
            delay_days = 0
            delay_reason = "None"

        actual_delivery_date = expected_delivery_date + timedelta(days=delay_days)
        lead_time = (actual_delivery_date - order_date).days

        # 11. Unit Cost
        cost_variation = float(np.clip(rng.normal(1.0, 0.018), 0.95, 1.05))
        unit_cost = round(prod_base_cost * cost_variation, 2)

        # 12. Shipping Cost
        total_weight_kg = quantity * prod_weight

        if transport_mode == "Air":
            base_fee = 120.0
            dist_rate = 0.085
            weight_rate = 0.85
        elif transport_mode == "Road":
            base_fee = 35.0
            dist_rate = 0.040
            weight_rate = 0.12
        elif transport_mode == "Rail":
            base_fee = 50.0
            dist_rate = 0.025
            weight_rate = 0.065
        else:  # Sea
            base_fee = 95.0
            dist_rate = 0.015
            weight_rate = 0.035

        prio_mult = {
            "Critical": 1.28,
            "High": 1.12,
            "Medium": 1.00,
            "Low": 0.95,
        }[priority]

        reroute_mult = 1.10 if delay_reason == "Transportation Issue" else 1.0

        raw_shipping_cost = (
            base_fee
            + (distance_km * dist_rate)
            + (total_weight_kg * weight_rate)
        ) * prio_mult * reroute_mult

        shipping_cost = round(max(15.0, raw_shipping_cost), 2)

        shipments.append({
            "shipment_id": shipment_id,
            "supplier_id": sup_id,
            "product_id": prod_id,
            "origin": origin,
            "destination": destination,
            "order_date": order_date.isoformat(),
            "expected_delivery_date": expected_delivery_date.isoformat(),
            "actual_delivery_date": actual_delivery_date.isoformat(),
            "lead_time": lead_time,
            "quantity": quantity,
            "unit_cost": unit_cost,
            "shipping_cost": shipping_cost,
            "supplier_reliability": sup_reliability,
            "inventory_level": inventory_level,
            "demand": demand,
            "priority": priority,
            "transport_mode": transport_mode,
            "delay_days": delay_days,
            "delay_reason": delay_reason,
        })

    return pd.DataFrame(shipments)


# ---------------------------------------------------------
# 5. ENTRYPOINT
# ---------------------------------------------------------
def main():
    print(f"Generating SupplyPrescript Synthetic Dataset (SEED={SEED})...")
    rng = np.random.default_rng(SEED)

    # 1. Suppliers
    print(f"Generating {NUM_SUPPLIERS} suppliers...")
    suppliers_df = generate_suppliers(rng)
    # Output suppliers with exact business fields
    suppliers_export = suppliers_df[[
        "supplier_id",
        "supplier_name",
        "origin",
        "supplier_reliability",
        "base_lead_time",
        "capacity",
    ]]
    suppliers_export.to_csv(SUPPLIERS_CSV, index=False)
    print(f"Saved suppliers to {SUPPLIERS_CSV} ({len(suppliers_export)} records)")

    # 2. Products
    print(f"Generating {NUM_PRODUCTS} products...")
    products_df = generate_products(rng)
    products_df.to_csv(PRODUCTS_CSV, index=False)
    print(f"Saved products to {PRODUCTS_CSV} ({len(products_df)} records)")

    # 3. Shipments
    print(f"Generating {NUM_SHIPMENTS} shipments...")
    shipments_df = generate_shipments(suppliers_df, products_df, num_records=NUM_SHIPMENTS, seed=SEED)
    shipments_df.to_csv(SHIPMENTS_CSV, index=False)
    print(f"Saved shipments to {SHIPMENTS_CSV} ({len(shipments_df)} records)")

    print("\nDataset generation completed successfully!")


if __name__ == "__main__":
    main()
