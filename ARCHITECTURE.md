# Timan Intelligence — Architectural Foundation

This scaffold is designed to sit **alongside the existing `app.py`**. It does not replace or modify that entry point, so the current Streamlit deployment can continue running while features are migrated gradually.

## Product direction

Timan Intelligence will share one analytical engine across:
- **NGO / MEAL:** household surveys, indicators, disaggregation, monitoring and evaluation.
- **Research:** descriptive and inferential statistics, models and reproducible research outputs.
- **Business:** sales, costs, margins, customers, inventory and operational performance.

The web and desktop interfaces should call the same services and statistical modules. Do not implement calculations independently in each interface.

## Current scaffold status

Implemented as foundation:
- Shared data-loading helper for CSV and Excel.
- Data-quality profile for missingness, duplicate rows and column-level summaries.
- Common request/result contracts.
- Domain/module registry.
- Basic descriptive-statistics functions.
- Initial automated tests.
- Desktop launcher shell using PySide6 (optional dependency).

Not implemented yet:
- AI provider integration or natural-language execution.
- Survey weights, strata and cluster-adjusted inference.
- Advanced statistical tests, regression, forecasting or optimisation.
- Report and PowerPoint generation.
- Authentication, multi-user storage, database persistence or production security controls.

The registry lists planned modules; a registry entry does not mean its statistical methods are already implemented.

## Repository structure

```text
app.py                         # Existing Streamlit entry point; preserve
requirements.txt               # Web deployment dependencies
requirements-desktop.txt       # Optional desktop dependencies
pyproject.toml                 # Installable shared Python package
src/timan_intelligence/
  core/
    contracts.py               # Shared request/result data contracts
    data_loader.py             # CSV / Excel import
    data_quality.py            # Reusable data-quality profiling
  modules/
    registry.py                # Domain and capability catalogue
    descriptive.py             # Initial descriptive-statistics functions
  services/
    analysis_service.py        # Common orchestration entry point
  ai/
    README.md                  # Safe AI integration contract
desktop/
  run_desktop.py               # Optional desktop shell
tests/
  test_core.py                 # Automated foundation tests
```

## Installation

### Keep the deployed web app working

The existing Streamlit app remains the deployment entry point. Commit this scaffold as an additive change. The app will not import the new package until a later, separately tested migration.

The root `requirements.txt` contains the existing web app's likely core dependencies (`streamlit`, `pandas`, `openpyxl`). If the current app requires additional packages, preserve and merge those dependencies rather than deleting them.

### Local development

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
pip install -e ".[dev]"
pytest
streamlit run app.py
```

### Desktop development

```bash
pip install -r requirements-desktop.txt
pip install -e .
python desktop/run_desktop.py
```

The desktop launcher is a shell only. It does not yet provide the complete analytical workflow.

## Engineering rules

1. Preserve the uploaded source data; cleaning must produce a separate derived dataset or explicit transformation log.
2. Never silently change category labels, remove rows, impute missing values or discard outliers.
3. Every analysis result should state its method, relevant sample size, assumptions and limitations.
4. AI may propose an analysis plan, but trusted Python functions must calculate numerical results.
5. Do not allow arbitrary model-generated Python to execute against user files.
6. Distinguish descriptive findings, statistical associations, predictions and causal claims.
7. Add tests with known expected answers before releasing each new statistical method.
8. Do not commit API keys, passwords, identifiable client data or real survey files.
9. Before production use, add authentication, tenant isolation, access controls, retention rules and secure storage.
