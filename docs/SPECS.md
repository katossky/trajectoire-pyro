# Technical Specifications

This document outlines architectural choices for the project.

## 1. Overall Architecture

- **Project structure.**

```
.gitignore
.env      # for API keys and such
Dockerfile
.docerignore
pyproject.toml
uv.lock
docs/
  SPECS.md
exps/       # experiment outcomes, reproducible through snake_make thus not gitted
    1a-config-hidden
    1b-config-observable
    2a-synthetic-data-hidden
    2b-synthetis-data-observable
    3-config-estimated
    4-simulated-data
scripts/    # wrappers for command line tools
src/trajpyro/
    evaluator/
    generator/
    modeler/
    planner/
    ...
tests/
```

- **Data generation vs. modeling separation**

- **Modular design**

- **Reproducibility.** We use `snakemake` for its ability to manage forks in pipelines, cartesian product of configurations and and hashing strategy for caching.

## 2. Data Handling

- **Data specification.** Data are made of two separate tables. One at the individual level giving permanent characteristics. One at the career level, with one line per id per year, giving changing occupation. For instance gender should be added to the first table, whereas income should be added to the second one. The exact variables depend on the data generator.

|  id |      birth |      death |
|-----|------------|------------|
|   1 | 03/01/1960 | 25/12/2010 |
|   2 | 01/03/1975 | 12/12/2005 |
| ... |        ... |        ... |

| id  | year |      state |
|-----|------|------------|
|   1 | 1960 | inactivity |
|   1 |  ... | inactivity |
|   1 | 1980 | inactivity |
|   1 | 1981 | employment |
|   1 |  ... | retirement |
|   1 | 2010 | retirement |
| ... |  ... |        ... |

- **Data storage format.** Individual and career data are stored as Parquet files. Model parametrization is stored as `.yaml`. **[Open question]** Is there a need to store data generators (either synthetic data generators or empiriacl generators) ? And if yes in which format?

- **Data versioning.** Config files for pipelines are expected to be permanent. (Deletion means we do not want the corresponding pipeline to be kept.) Snakefile generates locally the corresponding assets (synthetic data, parameters, reports...). **[Open question]** Is there nevertheless a need to store intermediate results with version control?

## 3. Model Implementation

- **Choice of framework.** Pyro is used for its ability to do amortised Bayesian inference.

- **Scalability.** No dedicated architectural solution is implemented until a computational problem is encountered ; methods used for estimation should reach a few millions of observed careers

## 4. Evaluation and Metrics

- **Evaluation criteria.**
    - parametric : when the generator and modeler share the same architecture, the true and estimated parameters can be contrasted
    - individual : **[Open question]** indivudal-level evaluation only makes sense for the prolongation of partially observed trajectories
    - aggregated :
        - number of employed people per year
        - number of pensioners per year
    - distributional : **[Open question]** distributional evaluation (e.g. with total variation) only make sense for quantitaive data (e.g. salary)

- **Metrics.** For individual criteria, RMSE. For parametric and aggregated criteria, simple difference.For distributional criteria, Wasserstein distance.

- **Sample size variation.** Scalibility of causal inference is evaluated on a single synthetic dataset by exponentially augmenting the number of individuals used for estimation ; speed of convergence is contrasted with computational time

## 5. Simulation and Forecasting

**[Open question]** Orchestration of experiments pipelines, integration of macroeconomic data, scenario modeling (how to model retirement age schedules), etc.

## 6. Testing and Validation

**Unit testing framework,** This package uses `pytest`.

**Performance monitoring**: determine how to track execution time and memory usage during experiments.

**Continuous integration.** **[Open question]**

## 7. Documentation

**Documentation tools.** choose between plain Markdown, Sphinx, or another system for building documentation.

**Visualization.** specify libraries for generating comparison tables and graphs (e.g. Matplotlib, Plotly, Pandas built-in plots).

## 8. Execution

**Containerization.** Contenerisation via Docker allows AI agents to use sandboxed environments without danger. Different Docker configurations also allow different roles to have access to different ressources and thus enforces data-separation (especially for generation parameters that should not be accessed at the modelling stage).

**Environment management.** This package uses `uv`.

**Packaging.** This package consists into several sub-modules, isolated for insuring data-separation.