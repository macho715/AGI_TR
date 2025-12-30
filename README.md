# AGI_TR - Ballast Management Pipeline

Integrated Ballast Management Pipeline System for AGI RORO TR (Transport) Project.

## 📋 Project Overview

This project is an integrated pipeline for automating and optimizing **Ballast Management** operations for vessels. Based on the SSOT (Single Source of Truth) principle, it manages Gate definitions, Tank catalogs, and Site profiles in a unified manner, and automatically generates Ballast plans through Linear Programming-based optimization.

## ✨ Key Features

- **SSOT (Single Source of Truth)**: Unified management of Gate definitions, Tank catalogs, and Site profiles
- **Definition Split**: Clear separation between forecast tide (Forecast Tide) and required water level (Required WL)
- **Gate Unified System**: Gate system that simultaneously enforces FWD maximum and AFT minimum values
- **Linear Programming Optimization**: LP Solver-based Ballast plan optimization
- **Automated Workflow**: Sequential execution of 6 independent steps
- **Operational Ready**: Automatic generation of Ballast sequence, Hold point, and Valve lineup
- **Tide Integration**: Tide-based UKC calculation and validation
- **SPMT Integration**: Automatic SPMT cargo import and integration
- **I/O Optimization**: Polars lazy scan, Parquet cache, Manifest logging
- **CI/CD Integration**: GitHub Actions workflows for quality assurance and automated testing

## 📁 Directory Structure

```
AGI_TR/
├── 01_EXECUTION_FILES/      # Execution files and scripts
│   ├── agi_tr_patched_v6_6_defsplit_v1.py
│   ├── ballast_sequence_generator.py
│   ├── bplus_inputs/        # B+ input data
│   ├── ssot/                # SSOT modules
│   ├── tide/                # Tide calculation modules
│   └── spmt v1/             # SPMT integration modules
├── 02_RAW_DATA/             # Raw data
│   ├── profiles/            # Site profile JSON files
│   ├── sensors/             # Sensor data
│   └── additional_inputs/   # Additional input files
├── 03_DOCUMENTATION/        # Documentation
│   └── 00_CORE_ARCHITECTURE/ # Core architecture documentation
├── tests/                   # Test suite
│   ├── test_ssot.py
│   └── conftest.py
└── .github/                  # GitHub Actions workflows
    └── workflows/           # CI/CD workflows
```

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- Git

### Dependency Installation

```bash
cd 01_EXECUTION_FILES
pip install -r requirements.txt
```

Key dependencies:
- `pandas>=1.5.0`
- `numpy>=1.23.0`
- `openpyxl>=3.0.0`
- `scipy>=1.9.0`
- `polars>=0.19.0` (High-performance I/O)
- `pydantic>=2.0.0` (Data validation)

## 📖 Usage

### Basic Execution

```bash
cd 01_EXECUTION_FILES
python agi_tr_patched_v6_6_defsplit_v1.py
```

### Main Scripts

- **Main Pipeline**: `agi_tr_patched_v6_6_defsplit_v1.py`
- **Ballast Sequence Generator**: `ballast_sequence_generator.py`
- **Excel Template Generator**: `create_bryan_excel_template_NEW.py`
- **Valve Lineup Generator**: `valve_lineup_generator.py`

### Integrated Pipeline Execution

```bash
cd 01_EXECUTION_FILES/tide
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
    --base_dir .. \
    --inputs_dir ../bplus_inputs \
    --out_dir ../outputs \
    --from_step 1 \
    --to_step 5
```

## 📚 Documentation

Detailed documentation is available in the `03_DOCUMENTATION/00_CORE_ARCHITECTURE/` directory.

### Recommended Reading Order

1. **Getting Started**: `README.md` (this file)
2. **System Architecture**: `00_System_Architecture_Complete.md`
3. **Data Flow**: `02_Data_Flow_SSOT.md`, `03_Pipeline_Execution_Flow.md`
4. **Solver Logic**: `04_LP_Solver_Logic.md`, `05_Definition_Split_Gates.md`
5. **User Guide**: `08_Bushra_System_User_Guide.md`

## 🔄 Latest Version Information

### v3.9 (2025-12-29)
- Added input data source and search order documentation
- Detailed pipeline step-by-step input file mapping
- Tide Integration priority specification

### v3.8 (2025-12-29)
- Added complete pipeline execution file list (21 files, categorized)
- Expanded component interface map (Step 0, Step 5, post-processing, utilities)
- Execution method classification (subprocess, import modules, dynamic import)
- Activation conditions and dependency relationships specified

### v3.7 (2025-12-29)
- Forecast_Tide_m priority change: CLI `--forecast_tide` value takes highest priority
- Complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`

### v3.6 (2025-12-28)
- Option 2 implementation: BALLAST_SEQUENCE option/execution separation
- Start_t/Target_t carry-forward implementation
- Stage 6B separation handling

### v3.5 (2025-12-28)
- I/O Optimization (PR-01~05)
- Polars lazy scan, Parquet sidecar cache
- Manifest logging integration

### v3.4 (2025-12-27)
- Tide Integration (AGI-only)
- SPMT Integration
- Step 5 added (SPMT Integrated Excel, Bryan Template)

## 🛠️ Development

### Project Structure

- **SSOT Module**: `01_EXECUTION_FILES/ssot/`
  - `gates_loader.py`: Gate definition loader
  - `draft_calc.py`: Draft calculation
  - `validators.py`: Data validation

- **Tide Module**: `01_EXECUTION_FILES/tide/`
  - `tide_ukc_engine.py`: UKC calculation engine
  - `tide_constants.py`: Tide constants

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=01_EXECUTION_FILES --cov-report=html
```

## 🔧 CI/CD

This project includes comprehensive GitHub Actions workflows:

1. **Python Quality Checks**: Code quality validation (ruff, black, isort, mypy, pytest)
2. **Data Pipeline Validation**: Data integrity verification
3. **Excel File Validation**: Excel file integrity checks
4. **Security Scan**: Automated security scanning
5. **Automated Release**: Version management and release automation
6. **Dependency Updates**: Automated dependency update PRs
7. **Performance Benchmark**: Performance regression detection
8. **Documentation Generation**: Automated API documentation

See `.github/workflows/` for workflow details.

## 📝 License

This project is proprietary to AGI.

## 👥 Contributing

For project improvements or bug reports, please submit via Issues.

## 📞 Contact

For project-related inquiries, please contact through the repository's Issues.

---

**Version**: v3.9  
**Last Updated**: 2025-12-30  
**Status**: Production Ready
