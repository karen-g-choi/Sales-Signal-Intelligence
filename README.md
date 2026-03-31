# Sales-Signal-Intelligence

A structured sales analytics project that separates baseline demand from event-driven sales patterns to reveal true commercial performance.

## Purpose

This project generates a structured synthetic sales dataset for a business analytics portfolio.
It is designed to show business thinking, not just coding.

It is meant to demonstrate business logic translation, structured analytical
thinking, AI-assisted implementation, and explainable synthetic scenario
design. The point is not to simulate randomness. The point is to show how a
messy commercial story can be translated into readable analytical logic.

The core idea is simple:

1. Build a baseline that represents normal demand.
2. Layer explainable business events on top of that baseline.

This makes it possible to separate ordinary demand from exceptional sales patterns such as promotions, recalls, bulk orders, launch effects, and hidden drops.

Important modeling note:
"scenario_role" is included for synthetic data design traceability and debugging, not as an input for the downstream detection logic.

## Why this project is different

This is not a random data generator.

The dataset is intentionally designed around business scenarios,
so every visible pattern has an explainable commercial reason.

The dataset is built from business scenarios:

- fixed customer seed data
- fixed region and vehicle seed data
- strict product-to-vehicle mappings
- customer-product coverage rules
- customer size differences
- light seasonality
- traceable event layers applied in a fixed order

The result is easier to explain in interviews because every unusual pattern has a business story behind it.

## Architecture

The project is split into three simple layers.

### 1. `data_generation/`

This folder contains the structural backbone:

- fixed seed data
- dimensions
- bridge tables
- reference rules

These files answer questions like:

- who are the customers?
- which products exist?
- which vehicle models does each product fit?
- what does "effort driven" mean?

### 2. `logic/`

This folder contains the business logic:

- baseline demand generation
- event layering in strict sequence
- conversion from demand to line-level orders
- line-level invoice generation with delays and partial fulfillment

This is the analytical heart of the project.

### 3. `validation/`

This folder contains lightweight checks that confirm:

- the required tables exist
- the date range is correct
- strict mappings were preserved
- event layers were applied in the required order
- invoice lines link back to valid order lines

## Data model

### Dimensions / masters

- `dim_calendar`
- `dim_customer`
- `dim_product`
- `dim_region`
- `dim_vehicle_model`

### Facts

- `fact_orders`
- `fact_invoices`
- `fact_promotions`
- `fact_recall_warranty_cases`
- `fact_events`

### Bridges

- `bridge_case_vehicle_model`
- `bridge_product_vehicle_model`

### Reference

- `ref_effort_classification_rules`

## Baseline logic

Baseline demand is created before any event logic.

It uses:

- customer-product relationships
- customer size multipliers
- product-level base demand
- customer-specific volatility ranges
- simple product-property volatility adjustments
- light monthly seasonality
- business-day demand generation

This is meant to represent normal replenishment demand.

The raw baseline is generated at product level because that gives the
synthetic dataset more realistic commercial texture.

Downstream signal detection should later operate at customer x category
level instead of using raw product-level baseline noise directly.

"scenario_role" is included for synthetic data design traceability and debugging, not as an input for the downstream detection logic.

## Classification Philosophy

- Normal sales are repeatable baseline demand.
- Exceptional sales are temporary distortions such as promotions, bulk orders, recalls, and launch bursts.
- Effort type is a supporting interpretation dimension, not the main classification axis.
- Transitional periods, such as launch stabilization, should not be treated as immediate steady-state baseline.
- Structural shifts that create a new normal should be handled separately from one-off anomalies.

## Event logic

The event layers are applied after baseline generation and in this exact order:

1. Recurring promotions
2. One-off bulk orders
3. Recall / warranty events
4. New dealer launch
5. Extreme promotion
6. Promotion absence
7. Hidden drop
8. New normal shift
9. Mixed ambiguous behavior

Events are first applied at demand level.
Orders then carry event traceability so analysts can see why a spike, drop,
or structural shift happened directly in `fact_orders`.
Invoices intentionally remain cleaner and more realistic, so they continue to
focus on fulfillment behavior rather than event attribution.

Each event is written to `fact_events` so the reason for the pattern stays visible.

The new dealer logic is intentionally readable:

- launch period = initial exceptional phase
- stabilization period = transition phase
- post-stabilization = baseline-only phase

## Output

Running the generator saves every table as CSV into:

- `./output`

Run it with:

```bash
python3 generate_data.py
```

## Dashboard

The project also includes a Streamlit business dashboard built on top of the
generated CSV outputs. It is designed to feel like a business reporting tool
first and a risk interpretation layer second.

The current dashboard includes:

- a Sales Overview tab for executive and controller-style reporting
- a Risk & Detection tab for business-facing interpretation of hidden weakness
- a Rule Configuration tab for business-friendly threshold tuning

Run it with:

```bash
python3 -m streamlit run dashboard/app.py
```

If local Streamlit hosting is blocked in the browser, use the no-server local preview instead:

```bash
python3 dashboard/export_html.py
```

Then open:

- `./output/dashboard_preview.html`

Or simply double-click:

- `./open_dashboard.command`

## React Frontend

The project also includes a polished React frontend in `./frontend`.
It reads the existing CSV outputs and presents them in a more product-like
admin dashboard shell with:

- Sales Overview
- Risk & Detection
- Rule Configuration

Run it locally with:

```bash
cd frontend
npm install
npm run dev
```

## GitHub Pages

The React dashboard is configured for GitHub Pages deployment from this
repository.

Once GitHub Pages is enabled for the repository's GitHub Actions workflow,
the live dashboard URL will be:

- `https://karen-g-choi.github.io/Sales-Signal-Intelligence/`

- `Sales Overview`
- `Risk & Detection`
- `Rule Configuration`

Run it with:

```bash
cd frontend
npm install
npm run dev
```

Before the app starts, the `sync:data` step copies the current CSV files from
`./output` into `./frontend/public/data` so the frontend stays connected to
the existing synthetic dataset.

## Code Map

### `generate_data.py`

Main entry point. Runs the full pipeline, validates the outputs, and saves every CSV.

### `data_generation/seeds.py`

Holds the fixed seed data from the business brief. This is where the non-random structural backbone lives.

### `data_generation/dimensions.py`

Builds clean dimension, bridge, and reference tables from the seed data.

### `logic/baseline.py`

Generates the raw product-level baseline before any exceptional business event is applied. It also carries product context fields needed for later customer x category analysis.

### `logic/events.py`

Applies explainable event layers in the required order and writes traceability data for promotions, recall cases, and events, including review hints for ambiguous patterns.

### `logic/orders_invoices.py`

Turns demand into line-level orders using customer order cycles, carries demand-level event traceability into `fact_orders`, and then creates invoices with delays and partial fulfillment. This ensures end-to-end traceability from demand -> orders -> invoices.

### `validation/checks.py`

Runs readable checks to confirm the generated dataset still follows the business rules and now saves a validation summary for traceability.

## Current Scope

- synthetic data generation
- event traceability
- line-level commercial flow simulation

## Planned Next Phase

- analytical baseline calculation layer
- hidden drop detection logic
- dashboarding / AI explanation layer
