# Optimization Environment

This directory houses mathematical programming and prescriptive optimization models for inventory optimization, safety stock determination, reorder planning, and routing constraints.

## Directory Structure

```text
optimization/
├── models/       # Mathematical formulation models (LP/MIP definitions)
├── scripts/      # Solvers and optimization execution scripts
├── requirements.txt # Python dependencies for optimization
└── README.md
```

## Dependencies

- `scipy` — Scientific algorithms and numerical optimization routines
- `pulp` — Linear and Mixed-Integer Linear Programming (MILP) modeling interface

## Usage

Dependencies are managed in `requirements.txt` and installed in the project virtual environment:

```bash
pip install -r optimization/requirements.txt
```
