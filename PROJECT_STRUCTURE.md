# AGI_TR Project Structure

## Directory Layout

```
AGI_TR/
├── 01_EXECUTION_FILES/      # Main execution scripts
│   ├── ssot/                # SSOT modules
│   ├── tide/                # Tide calculation
│   ├── spmt v1/             # SPMT integration
│   └── bplus_inputs/        # B+ input data
├── 02_RAW_DATA/             # Raw data files
│   ├── profiles/            # Site profiles
│   └── sensors/             # Sensor data
└── 03_DOCUMENTATION/        # Documentation
    └── 00_CORE_ARCHITECTURE/ # Architecture docs
```

## Key Components

### Main Pipeline
- `agi_tr_patched_v6_6_defsplit_v1.py`: Main pipeline execution
- `ballast_sequence_generator.py`: Ballast sequence generation
- `valve_lineup_generator.py`: Valve lineup automation

### SSOT Module
- `gates_loader.py`: Gate definition management
- `draft_calc.py`: Draft calculations
- `validators.py`: Data validation

### Tide Module
- `tide_ukc_engine.py`: UKC calculation engine
- `tide_constants.py`: Tide constants

## Data Flow

1. Load SSOT definitions (Gates, Tanks, Sites)
2. Import cargo and tide data
3. Run LP optimization
4. Generate ballast sequence
5. Create operational outputs

