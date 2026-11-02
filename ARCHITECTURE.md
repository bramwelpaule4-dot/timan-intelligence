
# TimanStat — Architectural Foundation

**Organisation:** Timan Analytics  
**Application:** TimanStat  
**Tagline:** Turning Data into Insights for Informed Decisions.

## 1. Purpose

This document describes the architectural direction of TimanStat, a modular statistical support platform developed by Timan Analytics.

The architecture is intended to support a shared analytical foundation across research, development programmes, MEAL, business intelligence, and other data-intensive applications.

The existing Streamlit application remains the web application entry point. New components should be introduced incrementally and integrated only after appropriate testing.

The architecture described here includes both existing foundation components and planned capabilities. A proposed component or module must not be interpreted as an implemented or verified feature.

## 2. Product Direction

TimanStat is being developed around a shared analytical engine with different application domains.

### 2.1 NGO and MEAL analytics

Intended areas include:

- Household and individual surveys.
- Indicator monitoring and performance measurement.
- Programme monitoring and evaluation.
- Demographic and geographic disaggregation.
- Accountability and feedback data.
- Outcome and impact assessment.
- Results-based management and reporting.

### 2.2 Research and academic statistics

Intended areas include:

- Descriptive statistics.
- Statistical inference and hypothesis testing.
- Estimation and confidence intervals.
- Regression and statistical modelling.
- Research design and sampling.
- Reproducible analytical procedures.
- Research reporting and interpretation.

### 2.3 Business analytics

Intended areas include:

- Sales and revenue analysis.
- Costs, margins, and profitability.
- Customer and market analysis.
- Inventory and operational performance.
- Business forecasting.
- Scenario analysis and decision support.

These are application domains, not separate statistical engines. Shared analytical services should be reused wherever appropriate.

## 3. Architectural Principles

The platform should follow these principles:

1. **Shared analytical services:** Web and desktop interfaces should call common analytical services rather than implement calculations independently.
2. **Modularity:** Data management, quality assessment, statistical methods, visualisation, and reporting should be separated into maintainable components.
3. **Statistical correctness:** Analytical methods must be appropriate to the research question, data structure, and assumptions.
4. **Reproducibility:** Methods, parameters, inputs, and outputs should be traceable.
5. **Data integrity:** Original source data must be preserved.
6. **Transparency:** Results should communicate sample sizes, assumptions, methods, and limitations.
7. **Extensibility:** New statistical methods and computing engines should be added without unnecessarily disrupting existing functionality.
8. **Responsible AI:** AI assistance should guide analytical decisions but must not replace validated numerical computation.
9. **Evidence-based implementation:** Feature implementation and methodological verification must be tracked separately.

## 4. Application Architecture

### 4.1 Web application

The web application is the initial delivery platform.

The existing Streamlit `app.py` remains the entry point while the shared analytical foundation is developed and integrated progressively.

### 4.2 Shared analytical layer

The shared analytical layer is intended to contain reusable services for:

- Data ingestion and inspection.
- Data-quality assessment.
- Descriptive statistics.
- Statistical inference.
- Research and statistical modelling.
- Survey analysis.
- Visualisation.
- Reporting and exports.

The web and desktop interfaces should consume these shared services.

### 4.3 Desktop application

The desktop application is a future interface built around the same analytical foundation.

The current PySide6 launcher is a desktop shell only. It does not yet provide the complete analytical workflow.

### 4.4 Statistical computing engines

The proposed engine strategy is:

- **Python:** Initial and default operational engine.
- **R:** Planned additional statistical engine, to be integrated progressively.

Both engines should eventually operate through controlled analytical interfaces.

Users should not need to manage the underlying programming language to use ordinary statistical procedures. Advanced users may be given engine-selection options where appropriate.

Each method must have its own implementation and verification record for each supported engine. An implementation in one engine does not establish that the method is available or verified in another.

R integration is a planned capability, not a claim of current functionality.

## 5. Current Foundation and Development Status

The following components are identified in the existing project architecture.

### 5.1 Foundation components

The existing scaffold describes the following as implemented foundation components:

- Shared CSV and Excel data-loading helper.
- Data-quality profiling for missingness, duplicate rows, and column-level summaries.
- Common request and result contracts.
- Domain and module registry.
- Basic descriptive-statistics functions.
- Initial automated tests.
- PySide6 desktop launcher shell.

These descriptions reflect the scaffold's documented implementation. Their current operation and verification should be confirmed through the relevant tests and project status records.

### 5.2 Capabilities not yet implemented in the documented scaffold

The following are not established as implemented by the existing scaffold:

- AI provider integration and natural-language execution.
- Survey weights, strata, and cluster-adjusted inference.
- Advanced statistical tests.
- Regression and advanced modelling.
- Forecasting and optimisation.
- Report and PowerPoint generation.
- Authentication and multi-user storage.
- Database persistence.
- Production security controls.
- Complete desktop analytical workflows.
- R statistical engine integration.

### 5.3 Registry interpretation

The module registry may contain planned or partially developed capabilities.

A registry entry does not prove that a feature is implemented, tested, or methodologically validated.

Implementation status and verification status must be recorded separately.

## 6. Data and Analytical Integrity

The following rules apply throughout the platform:

1. Preserve uploaded source data.
2. Perform cleaning and transformations on separate derived datasets or record them in an explicit transformation log.
3. Never silently change category labels, remove observations, impute missing values, or discard outliers.
4. Make data-quality findings visible to the user.
5. Record the relevant sample size for every analysis.
6. State the statistical method and relevant assumptions.
7. Communicate limitations and uncertainty.
8. Distinguish descriptive findings, statistical associations, predictions, and causal claims.
9. Use appropriate methods for the data structure and research design.
10. Ensure that numerical results can be reproduced from the documented procedure and inputs.

## 7. AI and Statistical Computation

AI-assisted functionality is intended to help users:

- Explain analytical objectives.
- Understand dataset structures.
- Identify potential data-quality concerns.
- Explore suitable statistical approaches.
- Review assumptions and method suitability.
- Interpret validated results.
- Prepare analytical narratives and reports.

AI may propose an analysis plan, but trusted statistical functions must calculate numerical results.

The platform must not allow arbitrary model-generated Python or R code to execute against user files.

Analytical execution should use controlled, validated procedures with appropriate input checks, parameter validation, error handling, and test coverage.

AI-generated interpretations must remain consistent with the actual analytical outputs and their limitations.

## 8. Repository Structure

The existing repository retains historical identifiers from the earlier project name.

The documented structure is:

```text
timan-intelligence/
├── app.py
├── requirements.txt
├── requirements-desktop.txt
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md
├── src/
│   └── timan_intelligence/
│       ├── core/
│       │   ├── contracts.py
│       │   ├── data_loader.py
│       │   └── data_quality.py
│       ├── modules/
│       │   ├── registry.py
│       │   └── descriptive.py
│       ├── services/
│       │   └── analysis_service.py
│       ├── ai/
│       │   └── README.md
│       └── config/
│           ├── __init__.py
│           └── branding.py
├── desktop/
│   └── run_desktop.py
└── tests/
```

This is a conceptual representation of the documented scaffold. The actual repository may contain additional files and modules.

The repository name and internal Python import package name are being managed separately from the user-facing TimanStat identity. They should only be changed through a controlled migration.

## 9. Installation and Development

### 9.1 Requirements

The project uses Python and the dependencies declared in its configuration files.

### 9.2 Clone the repository

```bash
git clone https://github.com/bramwelpaule4-dot/timan-intelligence.git
cd timan-intelligence
```

### 9.3 Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 9.4 Install web and development dependencies

```bash
pip install -r requirements.txt
pip install -e ".[web,dev]"
```

### 9.5 Run automated tests

```bash
pytest
```

### 9.6 Run the web application

```bash
streamlit run app.py
```

### 9.7 Install desktop dependencies

```bash
pip install -r requirements-desktop.txt
pip install -e .
```

### 9.8 Launch the desktop shell

```bash
python desktop/run_desktop.py
```

The desktop launcher currently provides a shell foundation rather than a complete analytical application.

## 10. Testing and Verification

Every new statistical procedure should have tests with known expected results before release.

Verification should distinguish between:

- **Not tested:** No recorded test evidence.
- **Unit tested:** Individual functions have passed relevant tests.
- **Integration tested:** Components have been tested together.
- **Numerically verified:** Results have been checked against known or independent reference calculations.
- **Methodologically reviewed:** The procedure and assumptions have been reviewed for statistical appropriateness.
- **Validated:** The feature has met its defined software and methodological acceptance criteria.

Passing a software test does not automatically establish statistical validity.

## 11. Security and Data Protection

The following controls are required before production use:

- Authentication and appropriate authorisation.
- User and organisation data isolation.
- Secure data storage and transfer.
- Access controls and audit trails.
- Data-retention and deletion policies.
- Protection of personally identifiable information.
- Secure management of API keys and credentials.
- Appropriate backup and recovery procedures.

Development repositories must not contain API keys, passwords, identifiable client data, or real survey files.

## 12. Implementation and Configuration Management

TimanStat should maintain a central configuration source for application identity and shared settings.

The project should also maintain an evidence-based implementation registry that records:

- Feature name and description.
- Application domain.
- Implementation status.
- Verification status.
- Relevant tests and evidence.
- Dependencies and outstanding work.
- Last reviewed or updated date.

The project status dashboard should derive its information from these records rather than manually maintained totals.

A one-click status refresh is a planned project-governance capability. It should run the relevant checks and produce an updated status report without falsely marking unverified features as complete.

## 13. Development Roadmap

The broad development sequence is:

1. Establish central application identity and configuration.
2. Strengthen the shared analytical foundation.
3. Improve data ingestion and data-quality assessment.
4. Expand descriptive statistics.
5. Develop survey and research analysis workflows.
6. Expand statistical inference and modelling.
7. Introduce controlled statistical engine support, including planned R integration.
8. Develop guided analytical recommendations and AI assistance.
9. Improve visualisation, reporting, and exports.
10. Expand the desktop interface using shared analytical services.
11. Strengthen project monitoring, testing, security, and governance.

The sequence may be refined as implementation and verification evidence becomes available.

---

## 14. Product Identity

**Application:** TimanStat  
**Organisation:** Timan Analytics  
**Tagline:** Turning Data into Insights for Informed Decisions.

**Project status:** Under active development.
