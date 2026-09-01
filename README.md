# SBM-Bioreactor

A high-performance Finite Element implementation of the **Suspension Balance Model (SBM)** for rotating bioreactor simulations, based on Chao & Das (2015).

This repository provides a fully coupled, monolithic solver for the Navier-Stokes, cell-volume-fraction (SBM), and nutrient-transport equations. It features:
- **5-Variable Mixed Monolithic Formulation** ($u, p, \Phi, C, \Gamma$).
- **Shear-Induced Migration Physics**: Captures complex cell-cell interaction and viscosity-gradient driven fluxes.
- **Bioreactor-Specific Physics**: Implements depth-averaged Hele-Shaw drag and global-clock cell growth kinetics.
- **Verification via MMS**: Includes a rigorous Method of Manufactured Solutions test suite.

## Getting Started

### 1. Installation
Ensure you have [Julia](https://julialang.org/) installed.
```bash
git clone https://github.com/elvis-aguero/sbm-bioreactor
cd sbm-bioreactor
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

### 2. Running the HARV Case Study
The repository includes a 2D HARV bioreactor prototype script.
```bash
julia --project=. scripts/run_harv_2d.jl
```

### 3. Running Tests
Verify the installation and implementation.
```bash
julia --project=. test/runtests.jl
```

## Documentation
- **Model Design:** See `docs/superpowers/specs/2026-03-17-bioreactor-simulation-design.md` for the full mathematical derivation and design choices.
- **Implementation Plan:** See `docs/superpowers/plans/2026-03-17-gridap-bioreactor-simulation.md` for implementation details.
