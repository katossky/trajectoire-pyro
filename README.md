# trajectoire‑pyro

## Overall objective {#goal}

This project has two aims:

* to demonstrate the usefulness of Pyro and Bayesian statistics for modelling career paths;
* to experiment with AI‑assisted development.

## Model‑building stages {#stages}

1. **Create a synthetic data set** (role: “generator”).
   Only the “observable” part is given to the modeller/forecaster; the full data set goes to the evaluator, and the data‑generation parameters go **only** to the evaluator.
2. **Audit** that the generator’s code contains nothing but the architecture and that the parameters are properly hidden (role: “auditor”).
3. **Use Pyro to build an estimator** that mirrors the data‑generation process (role: “modeller”).
   The modeller knows the architecture of the generator (its code) but **never** the parameter values (the config file).
4. **Compare** the estimation results with the true generation parameters (role: “evaluator”).
5. **Project careers forward and create new careers** from the estimated model (role: “forecaster”).
6. **Compare** those projections with the synthetic data, taking every source of uncertainty into account (role: “evaluator”).
7. The evaluator also measures the modeller’s runtime and memory usage.
8. The auditor gives critical feedback on all previous steps and proposes improvements, either immediately actionable or for future work.

## Roadmap / features {#roadmap}

* [ ] Compare synthetic and resimulated data on: number of active people per year; total income paid per year; income distributions by job type, age and year; number of pensioners per year; total pensions paid per year; pension distributions.
  A given individual career need not match between the two data sets as long as the **aggregate** numbers of people, monetary volumes and distributions remain coherent.
* [ ] For each evaluation, use several configurations—not just one—to check estimator convergence.
* [ ] Vary sample size for each evaluation and track “convergence as *n* → ∞”.
* [ ] Start with a simple four‑state model (inactivity / employment / retirement / death), then extend to 5, 6, 7, 8… states by adding job types (private, public, etc.) and inactivity types (childhood, study, unemployment, maternity, sickness, disability, etc.).
* [ ] Show uncertainty around aggregate quantities (credible intervals): population counts, monetary volumes, average income, etc.
* [ ] Show uncertainty around distributions: pension distribution, wage distribution.
* [ ] Optionally include fixed covariates (age, birth year, birthplace, parents’ social class, etc.).
* [ ] Introduce 1‑, 2‑, 3‑…‑dimensional latent variables capturing individual idiosyncrasies (propensity to earn high wages, to stay in a given activity, to retire early, etc.).
* [ ] Model income either as a variable attached to the *employment* state, **or** as a vector of scheme‑specific incomes (`r_{cnav,t}=1200`, `r_{sre,t}=200`, `r_{msa,t}=0`) instead of discrete states.
* [ ] Model the pension as a variable attached to the *retirement* state, computed by deterministic rules (average of best 20 years / 2, then annual revaluation of 3%).
  These deterministic rules can be shared between data generator and modeller, like the model architecture, but **not** the parameters.
* [ ] Increase the complexity of how variables depend on latent variables (non‑linearities via neural networks, amortised inference, etc.).
* [ ] Model work intensity (with peaks at 50 % and 80 %).
* [ ] Implement ways to encode hypotheses such as “the unemployment rate rises until 2040 then plateaus” or “average labour‑market entry age is fixed at 18”.
* [ ] Integrate macro‑economic series (e.g. time‑series of contributors to a scheme) or point data (life expectancy in year *x*).
* [ ] Co‑generate a representative sample of macro‑control data (i.e. *n* ≪ *N* diverse career trajectories whose aggregation approximates real data).
* [ ] Allow for a statutory retirement‑eligibility age that varies deterministically with birth year.
* [ ] Layered career simulation: first simulate birth and death dates, then simulate careers conditional on those dates.
* [ ] Generate **differentially private** careers.
* [ ] Enrich the comparison of estimated vs. true parameters (e.g. different goodness‑of‑fit measures; convergence as the number of examples grows).
* [ ] Enhance quality metrics for simulated careers.
* [ ] Handle fully observable data (a person from birth to death) **or** more complex survey designs (career observed only up to survey year).
* [ ] Check whether an advanced estimation model recovers the parameters of a simpler model that is its special case.

## Constraints {#constraints}

* Must run in an isolated environment (container).
* Use `uv` as the environment manager.
* Write unit tests.
* Data, parameters, estimates, evaluations, etc. must be well organised in a sensible file structure (role: “planner”).
* Model comparisons must be planned, documented and gradually enriched (role: “planner”).
* Overall documentation must be planned and progressively improved (role: “documentalist”).
* Generator‑model parameters are stored in a config file inaccessible to the modeller but accessible to the evaluator; this lets us share the generator’s code without exposing its parameters.
* Every milestone must be recorded in `news.md` and incorporated into the documentation.
* Summary tables comparing approaches and model quality must appear in the documentation (role: “documentalist”).
* The documentation must include a graph of arrows showing which models are special cases of more complex ones (role: “documentalist”).

## Points to watch {#cautionary-notes}

* Is the estimation *numerically* identifiable? *Causally* identifiable?
* Could mortality introduce selection bias that disrupts estimation?
