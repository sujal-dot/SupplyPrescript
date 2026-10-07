-- =============================================================================
-- SupplyPrescript - Canonical PostgreSQL Database Schema
-- Phase 1 - Day 4: Core Supply-Chain Prescriptive Workflow
-- =============================================================================

-- Table 1: Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    supplier_id VARCHAR(50) NOT NULL UNIQUE,
    supplier_name VARCHAR(255) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    supplier_reliability NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    base_lead_time INTEGER,
    capacity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_suppliers_supplier_reliability CHECK (supplier_reliability >= 0 AND supplier_reliability <= 1),
    CONSTRAINT ck_suppliers_base_lead_time CHECK (base_lead_time IS NULL OR base_lead_time > 0),
    CONSTRAINT ck_suppliers_capacity CHECK (capacity IS NULL OR capacity >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_suppliers_supplier_id ON suppliers (supplier_id);


-- Table 2: Products
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    weight_kg NUMERIC(10, 2) NOT NULL,
    base_demand NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_products_unit_cost CHECK (unit_cost > 0),
    CONSTRAINT ck_products_weight_kg CHECK (weight_kg > 0),
    CONSTRAINT ck_products_base_demand CHECK (base_demand >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_products_product_id ON products (product_id);


-- Table 3: Shipments (Central historical shipment log)
CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    shipment_id VARCHAR(50) NOT NULL UNIQUE,
    supplier_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    origin VARCHAR(100) NOT NULL,
    destination VARCHAR(100) NOT NULL,
    order_date DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE NOT NULL,
    lead_time INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost NUMERIC(10, 2) NOT NULL,
    shipping_cost NUMERIC(10, 2) NOT NULL,
    supplier_reliability NUMERIC(5, 4) NOT NULL,
    inventory_level INTEGER NOT NULL,
    demand INTEGER NOT NULL,
    priority VARCHAR(50) NOT NULL,
    transport_mode VARCHAR(50) NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_shipments_supplier_id FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
    CONSTRAINT fk_shipments_product_id FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    CONSTRAINT ck_shipments_quantity CHECK (quantity > 0),
    CONSTRAINT ck_shipments_unit_cost CHECK (unit_cost > 0),
    CONSTRAINT ck_shipments_shipping_cost CHECK (shipping_cost >= 0),
    CONSTRAINT ck_shipments_supplier_reliability CHECK (supplier_reliability >= 0 AND supplier_reliability <= 1),
    CONSTRAINT ck_shipments_inventory_level CHECK (inventory_level >= 0),
    CONSTRAINT ck_shipments_demand CHECK (demand >= 0),
    CONSTRAINT ck_shipments_lead_time CHECK (lead_time > 0),
    CONSTRAINT ck_shipments_delay_days CHECK (delay_days >= 0),
    CONSTRAINT ck_shipments_order_expected_date CHECK (order_date <= expected_delivery_date),
    CONSTRAINT ck_shipments_order_actual_date CHECK (order_date <= actual_delivery_date)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_shipments_shipment_id ON shipments (shipment_id);
CREATE INDEX IF NOT EXISTS ix_shipments_supplier_id ON shipments (supplier_id);
CREATE INDEX IF NOT EXISTS ix_shipments_product_id ON shipments (product_id);
CREATE INDEX IF NOT EXISTS ix_shipments_order_date ON shipments (order_date);
CREATE INDEX IF NOT EXISTS ix_shipments_actual_delivery_date ON shipments (actual_delivery_date);
CREATE INDEX IF NOT EXISTS ix_shipments_delay_days ON shipments (delay_days);


-- Table 4: Inventory
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    inventory_date DATE NOT NULL,
    inventory_level INTEGER NOT NULL,
    demand INTEGER NOT NULL,
    reorder_point INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL,
    inventory_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_inventory_product_id FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    CONSTRAINT ck_inventory_level CHECK (inventory_level >= 0),
    CONSTRAINT ck_inventory_demand CHECK (demand >= 0),
    CONSTRAINT ck_inventory_reorder_point CHECK (reorder_point >= 0),
    CONSTRAINT ck_inventory_safety_stock CHECK (safety_stock >= 0),
    CONSTRAINT ck_inventory_status CHECK (inventory_status IN ('Healthy', 'Low', 'Critical', 'Out of Stock'))
);

CREATE INDEX IF NOT EXISTS ix_inventory_product_id ON inventory (product_id);
CREATE INDEX IF NOT EXISTS ix_inventory_inventory_date ON inventory (inventory_date);


-- Table 5: Model Versions (ML model artifact registry)
CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    training_date TIMESTAMP WITH TIME ZONE,
    dataset_version VARCHAR(50),
    metrics JSONB,
    model_path VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_model_versions_name_version UNIQUE (model_name, version)
);


-- Table 6: Predictions (ML Inference storage)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    prediction_id VARCHAR(50) NOT NULL UNIQUE,
    shipment_id VARCHAR(50) NOT NULL,
    model_version_id INTEGER NOT NULL,
    prediction_type VARCHAR(100) NOT NULL,
    predicted_value NUMERIC(10, 4) NOT NULL,
    prediction_probability NUMERIC(5, 4),
    prediction_status VARCHAR(50) NOT NULL DEFAULT 'Generated',
    prediction_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    prediction_horizon INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_predictions_shipment_id FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE RESTRICT,
    CONSTRAINT fk_predictions_model_version_id FOREIGN KEY (model_version_id) REFERENCES model_versions(id) ON DELETE RESTRICT,
    CONSTRAINT ck_predictions_probability CHECK (prediction_probability IS NULL OR (prediction_probability >= 0 AND prediction_probability <= 1)),
    CONSTRAINT ck_predictions_type CHECK (prediction_type IN ('Delay Risk', 'Delivery Time', 'Inventory Shortage', 'Demand Forecast'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_predictions_prediction_id ON predictions (prediction_id);
CREATE INDEX IF NOT EXISTS ix_predictions_shipment_id ON predictions (shipment_id);
CREATE INDEX IF NOT EXISTS ix_predictions_model_version_id ON predictions (model_version_id);


-- Table 7: Recommendations (Prescriptive optimization output)
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    recommendation_id VARCHAR(50) NOT NULL UNIQUE,
    prediction_id INTEGER NOT NULL,
    recommendation_type VARCHAR(100) NOT NULL,
    recommendation_text TEXT NOT NULL,
    recommended_action VARCHAR(255) NOT NULL,
    priority VARCHAR(50) NOT NULL DEFAULT 'Medium',
    confidence_score NUMERIC(5, 4) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_recommendations_prediction_id FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE RESTRICT,
    CONSTRAINT ck_recommendations_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT ck_recommendations_type CHECK (recommendation_type IN ('Expedite Shipment', 'Change Supplier', 'Increase Inventory', 'Reduce Order Quantity', 'Reorder Inventory', 'Monitor Supplier'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_recommendations_recommendation_id ON recommendations (recommendation_id);
CREATE INDEX IF NOT EXISTS ix_recommendations_prediction_id ON recommendations (prediction_id);


-- Table 8: Decisions (Human/AI operational decision log)
CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    decision_id VARCHAR(50) NOT NULL UNIQUE,
    recommendation_id INTEGER NOT NULL,
    decision VARCHAR(255) NOT NULL,
    decision_reason TEXT,
    decision_source VARCHAR(50) NOT NULL,
    approved_by VARCHAR(100),
    decision_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_decisions_recommendation_id FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE RESTRICT,
    CONSTRAINT ck_decisions_status CHECK (status IN ('Pending', 'Approved', 'Rejected', 'Executed', 'Cancelled')),
    CONSTRAINT ck_decisions_source CHECK (decision_source IN ('AI', 'Human', 'Rule', 'Optimization'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_decisions_decision_id ON decisions (decision_id);
CREATE INDEX IF NOT EXISTS ix_decisions_recommendation_id ON decisions (recommendation_id);


-- Table 9: Outcomes (Closed-loop feedback & post-decision tracking)
CREATE TABLE IF NOT EXISTS outcomes (
    id SERIAL PRIMARY KEY,
    outcome_id VARCHAR(50) NOT NULL UNIQUE,
    decision_id INTEGER NOT NULL,
    actual_delivery_date DATE,
    actual_delay_days INTEGER NOT NULL DEFAULT 0,
    actual_cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    inventory_impact INTEGER,
    outcome_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    success_score NUMERIC(5, 4),
    outcome_notes TEXT,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_outcomes_decision_id FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE RESTRICT,
    CONSTRAINT ck_outcomes_actual_delay_days CHECK (actual_delay_days >= 0),
    CONSTRAINT ck_outcomes_actual_cost CHECK (actual_cost >= 0),
    CONSTRAINT ck_outcomes_success_score CHECK (success_score IS NULL OR (success_score >= 0 AND success_score <= 1)),
    CONSTRAINT ck_outcomes_status CHECK (outcome_status IN ('Success', 'Partial Success', 'Failure', 'Pending'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_outcomes_outcome_id ON outcomes (outcome_id);
CREATE INDEX IF NOT EXISTS ix_outcomes_decision_id ON outcomes (decision_id);
