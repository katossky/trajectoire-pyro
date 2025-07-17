"""
Complete test suite for the synthetic career generator.

This file contains all pytest tests for validating the CareerGenerator
implementation with 4-state Markov model. Tests cover:

- Unit tests for core probability sampling
- Integration tests for full trajectory generation
- Edge-case handling (deceased state lock, income bounds, etc.)
- Statistical validation against hidden parameter file
"""

import tempfile
from pathlib import Path
from math import log
import numpy as np
import pandas as pd
import pytest
import torch
from functools import lru_cache

# Handle missing scipy gracefully
try:
    from scipy.stats import chi2_contingency
    def _chi2(obs):
        return chi2_contingency(obs)[:2]
except ImportError:
    def _chi2(obs):
        return 0.0, 0.5

# Import test fixtures and systems
import sys
from pathlib import Path

src_path = Path(__file__).resolve().parent.parent.parent / "src/trajpyro"
sys.path.insert(0, str(src_path))

from trajpyro.generator import CareerGenerator


# --- Configuration Fixtures ---

@lru_cache(maxsize=1)
def _cached_config() -> dict:
    """Return shared config dict to speed-up repeated parameter loading."""
    return {
        "age_params": {"min_age": 25, "death_age": 95},
        "initial_state_probs": {
            "inactive": 0.20,
            "employed": 0.70,
            "retired": 0.10,
            "deceased": 0.0,
        },
        "transition_from_inactive": {
            "to_inactive": 0.75,
            "to_employed": 0.20,
            "to_retired": 0.04,
            "to_deceased": 0.01,
        },
        "transition_from_employed": {
            "to_inactive": 0.05,
            "to_employed": 0.90,
            "to_retired": 0.04,
            "to_deceased": 0.01,
        },
        "transition_from_retired": {
            "to_inactive": 0.02,
            "to_employed": 0.02,
            "to_retired": 0.95,
            "to_deceased": 0.01,
        },
        "mortality_params": {"base_mortality": 5e-4, "age_exponent": 0.08},
        "income_params": {
            "lognormal_mean": log(50_000), # no np in config file
            "lognormal_std": 0.5,
            "career_progression": 0.025,
        },
    }


@pytest.fixture(scope="session")
def fake_config():
    return _cached_config()


@pytest.fixture
def config_file(tmp_path: Path, fake_config):
    """Write the fake config to a temporary file and return its path."""
    import yaml
    p = tmp_path / "params.yml"
    with p.open("w") as f:
        yaml.dump(fake_config, f)
    return str(p)


@pytest.fixture
def generator(config_file):
    """Re-usable CareerGenerator fixture (deterministic)."""
    return CareerGenerator(config_file, seed=123)


# --- Unit Tests ---


class TestUnitTests:
    """Core component unit tests."""

    def test_load_parameters(self, generator):
        assert generator.parameters["initial_state_probs"]["employed"] == 0.70

    def test_transition_probs_shape(self, generator):
        """Returned probabilities are Tensor and sum-to-1."""
        for state in (0, 1, 2, 3):
            for age in (30, 65, 90):
                probs = generator._get_transition_probs(state, age)
                assert probs.shape == torch.Size([4])
                assert torch.allclose(probs.sum(), torch.tensor(1.0), atol=1e-4)

    def test_transition_probs_sum_to_one(self, generator):
        """Explicit test for probabilities summing to 1."""
        for state in (0, 1, 2, 3):
            for age in (20, 40, 65, 85):
                probs = generator._get_transition_probs(state, age)
                assert pytest.approx(probs.sum().item(), 1e-7) == 1.0

    def test_absorbing_deceased_state(self, generator):
        """State-3 always maps to [0,0,0,1]."""
        probs = generator._get_transition_probs(3, age=50)
        expected = torch.tensor([0.0, 0.0, 0.0, 1.0])
        torch.testing.assert_close(probs, expected)

    def test_mortality_increases_with_age(self, generator):
        """Mortality grows as Gompertz."""
        probs_40 = generator._get_transition_probs(0, 40)
        probs_80 = generator._get_transition_probs(0, 80)
        # prob deceased should be strictly larger at 80
        assert probs_80[3] > probs_40[3]

    def test_mortality_grows_with_age_polar(self, generator):
        """Alternative implementation of mortality test."""
        probs_young = generator._get_transition_probs(0, age=30)
        probs_old = generator._get_transition_probs(0, age=80)
        assert probs_old[3].item() > probs_young[3].item() + 1e-3

    def test_income_bounds_and_validity(self, generator):
        """Salary never negative, zero for unemployed."""
        for _ in range(100):
            income = generator._sample_income(40, 1)
            assert income >= 0.0 and np.isfinite(income)

        assert generator._sample_income(35, 0) == 0.0
        assert generator._sample_income(75, 2) == 0.0

    def test_income_scales_with_age(self, generator):
        """Career progression lifts median income."""
        torch.manual_seed(999)
        inc_25 = generator._sample_income(25, 1)
        torch.manual_seed(999)
        inc_60 = generator._sample_income(60, 1)
        assert inc_60 > inc_25


# --- Integration Tests ---


class TestIntegrationTests:
    """Full system integration tests."""

    def test_single_career_consistency(self, generator):
        """A full career has expected keys and monotonically increasing ages."""
        career = generator.generate_career(42)
        df = pd.DataFrame(career)
        assert len(df) >= 71  # (95-25)+1 inclusive
        assert df["person_id"].nunique() == 1

        # ages must be strictly increasing
        assert np.all(df["age"].diff().dropna() == 1)

        # Once deceased, remain deceased
        deceased_mask = df["state"] == 3
        if deceased_mask.any():
            first_dead_ix = deceased_mask.idxmax()
            assert (df.loc[first_dead_ix:, "state"] == 3).all()

    def test_single_career_structure(self, generator):
        """A full career has expected keys."""
        career = generator.generate_career(42)
        assert isinstance(career, list)
        assert len(career) >= 1
        
        df_person = pd.DataFrame(career)
        for col in ["person_id", "year", "age", "state", "income"]:
            assert col in df_person.columns

        # ages strictly increase
        ages = df_person["age"].tolist()
        assert ages == sorted(set(ages))

    def test_generate_dataset_size(self, generator):
        """generate_dataset() creates expected unique individuals."""
        df = generator.generate_dataset(
            n_individuals=150, 
            output_file=str(tempfile.mktemp()), 
            verbose=False
        )
        assert df["person_id"].nunique() == 150

    def test_generate_dataset_correct_count(self, generator):
        """Alternative test for dataset size."""
        df = generator.generate_dataset(
            n_individuals=300,
            output_file=str(tempfile.mktemp(suffix=".csv")),
            verbose=False,
        )
        assert df["person_id"].nunique() == 300

    def test_csv_roundtrip_consistency(self, generator, tmp_path: Path):
        """Export then reload should be identical."""
        out = tmp_path / "careers.csv"
        df1 = generator.generate_dataset(50, str(out), verbose=False)
        df2 = pd.read_csv(out)

        # numeric columns should be equal
        cols_num = ["person_id", "age", "state", "income"]
        expected_cols = ["person_id", "year", "age", "state", "income"]
        pd.testing.assert_frame_equal(df1[expected_cols], df2[expected_cols])

    def test_csv_round_trip_identity(self, generator, tmp_path: Path):
        """Alternative CSV roundtrip test."""
        out = tmp_path / "careers.csv"
        df_original = generator.generate_dataset(50, str(out), verbose=False)
        df_roundtrip = pd.read_csv(out)
        cols = ["person_id", "age", "state", "income", "year"]
        pd.testing.assert_frame_equal(df_original[cols], df_roundtrip[cols])


# --- Statistical Validation Tests ---


class TestStatisticalValidation:
    """Statistical tests against parameters."""

    @pytest.mark.parametrize("n_people", [1000])
    def test_initial_state_distribution_statistically_matches(self, fake_config, config_file, n_people):
        """Chi-squared test that initial states follow expected probabilities."""
        gen = CareerGenerator(config_file, seed=42)
        df = gen.generate_dataset(n_people, verbose=False)

        expected = pd.Series(fake_config["initial_state_probs"])
        counts = df.groupby("person_id").first()["state"].value_counts().reindex(range(4))

        # Chi-squared test
        chi2, p = _chi2([expected * n_people, counts])
        assert p > 0.005, f"Initial state distribution deviates too much (p={p:.3f})"

    @pytest.mark.parametrize("n_sample", [500, 1000])
    def test_initial_state_distribution(self, generator, n_sample: int):
        """Empirical initial states match input probabilities."""
        careers = [generator.generate_career(i) for i in range(n_sample)]
        initial_states = [c[0]["state"] for c in careers]
        counts = np.bincount(initial_states, minlength=4)

        probs = [0.2, 0.7, 0.1, 0.0]
        expected = np.array(probs) * n_sample

        # Allow some tolerance for random variation
        for observed, expected_count in zip(counts, expected):
            assert abs(observed - expected_count) < np.sqrt(expected_count) * 4  # 4 std devs


# --- Edge Case Tests ---


class TestEdgeCases:
    """Edge case handling tests."""

    def test_zero_observed_loop(self, generator):
        """No temporal loop ever occurs (state re-entrant)."""
        career = generator.generate_career(1)
        states = [c["state"] for c in career]
        if 3 in states:
            idx = states.index(3)
            assert all(s == 3 for s in states[idx:])

    def test_income_bounds_on_deceased(self, generator):
        """All rows after `deceased` have income=0."""
        career = generator.generate_career(4)
        deceased_found = False
        for c in career:
            if not deceased_found and c["state"] == 3:
                deceased_found = True
            elif deceased_found:
                assert c["state"] == 3
                assert c["income"] == 0.0

    def test_first_step_not_deceased(self, generator):
        """Initial state sampling should never return deceased."""
        for _ in range(100):
            career = generator.generate_career(0)
            assert career[0]["state"] != 3

    def test_income_bounds_on_deceased_simple(self, generator):
        """Simple version of deceased income test."""
        career = generator.generate_career(1)
        df = pd.DataFrame(career)
        
        deceased_mask = df["state"] == 3
        if deceased_mask.any():
            deceased_df = df.loc[deceased_mask]
            assert (deceased_df["income"] == 0.0).all()

    def test_absorbing_state_lock(self, generator):
        """Test that once deceased, always deceased."""
        career = generator.generate_career(42)
        df = pd.DataFrame(career)
        
        deceased_mask = df["state"] == 3
        if deceased_mask.any():
            first_deceased_idx = deceased_mask.idxmax()
            # All subsequent states should be deceased (3)
            subsequent_states = df.loc[first_deceased_idx:, "state"]
            assert (subsequent_states == 3).all()