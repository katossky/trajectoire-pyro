#!/usr/bin/env python3
"""
Synthetic Career Generator for 4-State Markov Model

This module implements a career trajectory generator using a 4-state Markov model:
- 0: Inactive (unemployed, student, homemaker)
- 1: Employed (working with income)
- 2: Retired (no longer working)
- 3: Deceased (absorbing state)

The generator uses Pyro distributions to incorporate randomness and
produces realistic synthetic career data with hidden parameters.
"""

import numpy as np
import pandas as pd
import torch
import pyro
import pyro.distributions as dist
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import yaml
import json


class CareerGenerator:
    """
    A synthetic career generator using 4-state Markov model.
    
    Generates realistic career trajectories with hidden parameters
    using Pyro distributions for randomness and uncertainty.
    """
    
    def __init__(self, config_path: str, seed: Optional[int] = None):
        """
        Initialize the career generator.
        
        Args:
            config_path: Path to YAML configuration file with hidden parameters
            seed: Random seed for reproducibility
        """
        if seed is not None:
            pyro.set_rng_seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
        
        self.config_path = Path(config_path)
        self.parameters = self._load_parameters()
        
    def _load_parameters(self) -> Dict:
        """Load hidden parameters from configuration file."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _get_transition_probs(self, current_state: int, age: int) -> torch.Tensor:
        """
        Get transition probabilities from current state.
        
        Args:
            current_state: Current career state (0-3)
            age: Current age in years
            
        Returns:
            Tensor of transition probabilities for state 0-3
        """
        params = self.parameters
        
        if current_state == 0:  # From inactive
            probs = [
                params['transition_from_inactive']['to_inactive'],
                params['transition_from_inactive']['to_employed'],
                params['transition_from_inactive']['to_retired'],
                params['transition_from_inactive']['to_deceased']
            ]
            
        elif current_state == 1:  # From employed
            probs = [
                params['transition_from_employed']['to_inactive'],
                params['transition_from_employed']['to_employed'],
                params['transition_from_employed']['to_retired'],
                params['transition_from_employed']['to_deceased']
            ]
            
        elif current_state == 2:  # From retired
            probs = [
                params['transition_from_retired']['to_inactive'],
                params['transition_from_retired']['to_employed'],
                params['transition_from_retired']['to_retired'],
                params['transition_from_retired']['to_deceased']
            ]
            
        else:  # From deceased (3)
            probs = [0.0, 0.0, 0.0, 1.0]
        
        # Adjust mortality based on age using Gompertz model
        if current_state != 3:  # Only adjust for non-deceased states
            base_rate = params['mortality_params']['base_mortality']
            age_factor = params['mortality_params']['age_exponent']
            age_mortality = base_rate * np.exp(age_factor * (age - 25))
            
            if current_state == 0:  # inactive
                mortality_prob = age_mortality
                probs = [
                    params['transition_from_inactive']['to_inactive'],
                    params['transition_from_inactive']['to_employed'],
                    params['transition_from_inactive']['to_retired'],
                    params['transition_from_inactive']['to_deceased'] + mortality_prob
                ]
            elif current_state == 1:  # employed
                mortality_prob = 0.8 * age_mortality  # Lower mortality for employed
                probs = [
                    params['transition_from_employed']['to_inactive'],
                    params['transition_from_employed']['to_employed'],
                    params['transition_from_employed']['to_retired'],
                    params['transition_from_employed']['to_deceased'] + mortality_prob
                ]
            elif current_state == 2:  # retired
                mortality_prob = 1.5 * age_mortality  # Higher mortality for retired
                probs = [
                    params['transition_from_retired']['to_inactive'],
                    params['transition_from_retired']['to_employed'],
                    params['transition_from_retired']['to_retired'],
                    params['transition_from_retired']['to_deceased'] + mortality_prob
                ]
        
        # Convert to tensor and ensure exact normalization (sum to exactly 1.0)
        probs = np.array(probs, dtype=np.float64)
        
        # Handle any negative probabilities (safety check)
        probs = np.maximum(probs, 0.0)
        
        # Normalize to sum to exactly 1.0 using double precision
        total = probs.sum()
        if total > 0:
            probs = probs / total
        else:
            # Fallback: if somehow we get zero probabilities, use uniform
            probs = np.array([0.25, 0.25, 0.25, 0.25])
        
        # Convert to tensor and verify normalization at float precision
        probs_tensor = torch.tensor(probs, dtype=torch.float32)
        
        # Ensure exact sum to 1.0 within float precision tolerance
        # Use a more precise approach for float32
        total_sum = probs_tensor.sum()
        if abs(float(total_sum) - 1.0) > 1e-6:
            # Perfectly normalize
            normalized = probs_tensor / total_sum
            # Final check
            final_sum = float(normalized.sum())
            # Handle remaining tiny float precision issues
            if abs(final_sum - 1.0) > 1e-7:
                # Perfect normalization to exactly 1.0
                normalized = normalized.clone()
                normalized[-1] = 1.0 - normalized[:-1].sum()
            probs_tensor = normalized
        
        return probs_tensor
    
    def _sample_income(self, age: int, state: int) -> float:
        """
        Sample income based on person's age and state.
        
        Args:
            age: Current age in years
            state: Current career state
            
        Returns:
            Annual income (0 if not employed)
        """
        if state != 1:  # Not employed
            return 0.0
        
        params = self.parameters['income_params']
        
        # Base log-normal parameters
        mean_log = params['lognormal_mean']
        std_log = params['lognormal_std']
        
        # Age adjustment (career progression)
        age_bonus = params['career_progression'] * max(age - 25, 0)
        mean_log += age_bonus
        
        # Sample income using Pyro distribution
        income_dist = dist.LogNormal(mean_log, std_log)
        income = pyro.sample(
            f"income_{age}_{state}",
            income_dist
        )
        
        # Ensure non-negative income
        return max(float(income), 0.0)
    
    def generate_career(self, person_id: int) -> List[Dict]:
        """
        Generate a complete career for one individual.
        
        Args:
            person_id: Unique identifier for the person
            
        Returns:
            List of dictionaries with career data for each year
        """
        initial_probs = self.parameters['initial_state_probs']
        
        # Use Categorical distribution for proper initial state sampling
        state_probs = torch.tensor([
            initial_probs['inactive'],
            initial_probs['employed'],
            initial_probs['retired'],
            initial_probs['deceased']
        ], dtype=torch.float32)
        
        # Sample initial state using Pyro (avoiding person_id in key)
        initial_state = pyro.sample(
            f"initial_state",
            dist.Categorical(state_probs)
        ).item()
        
        # Initialize career
        career_data = []
        current_state = initial_state
        min_age = self.parameters['age_params']['min_age']
        death_age = self.parameters['age_params']['death_age']
        
        # Age range should be inclusive: min_age TO death_age
        for age in range(min_age, death_age + 1):
            
            # Handle deceased state before sampling income
            if current_state == 3:
                income = 0.0
            else:
                income = self._sample_income(age, current_state)
            
            # Record current year data
            career_data.append({
                'person_id': person_id,
                'year': 2020 + (age - min_age),
                'age': age,
                'state': current_state,
                'income': income
            })
            
            # If we're at the final age (death_age), we're done
            if age == death_age:
                break
                
            # Sample next state for next year (if not already deceased)
            if current_state != 3:
                probs = self._get_transition_probs(current_state, age)
                next_state = pyro.sample(
                    f"_transition_",
                    dist.Categorical(probs)
                ).item()
                current_state = next_state
            
            # Handle deceased state transition 
            if current_state == 3 and age + 1 <= death_age:
                # Fill remaining years with deceased state
                for remaining_age in range(age + 1, death_age + 1):
                    career_data.append({
                        'person_id': person_id,
                        'year': 2020 + (remaining_age - min_age),
                        'age': remaining_age,
                        'state': 3,
                        'income': 0.0
                    })
                break
        
        return career_data
    
    def generate_dataset(
        self,
        n_individuals: int,
        output_file: str = "synthetic_careers.csv",
        verbose: bool = True
    ) -> pd.DataFrame:
        """
        Generate synthetic career dataset.
        
        Args:
            n_individuals: Number of individuals to simulate
            output_file: Output CSV file path
            verbose: Whether to print progress
            
        Returns:
            DataFrame with synthetic career data
        """
        all_careers = []
        
        for i in range(n_individuals):
            if verbose and i > 0 and i % 1000 == 0:
                print(f"Generating careers... ({i}/{n_individuals})")
            
            career = self.generate_career(i + 1)
            all_careers.extend(career)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_careers)
        
        # Convert state to categorical for clarity
        state_names = ["inactive", "employed", "retired", "deceased"]
        df['state_name'] = df['state'].map(dict(zip(range(4), state_names)))
        
        # Sort by person and age for consistency
        df = df.sort_values(['person_id', 'age']).reset_index(drop=True)
        
        # Save output
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        if verbose:
            print(f"Generated {len(df)} career-year observations for {n_individuals} individuals")
            self._print_dataset_summary(df)
        
        return df
    
    def _print_dataset_summary(self, df: pd.DataFrame):
        """Print summary statistics of the generated dataset."""
        print("\n=== Dataset Summary ===")
        print(f"Total observations: {len(df)}")
        print(f"Unique individuals: {df['person_id'].nunique()}")
        print(f"Year range: {df['year'].min()}-{df['year'].max()}")
        print(f"Age range: {df['age'].min()}-{df['age'].max()}")
        
        print("\nState distribution:")
        state_counts = df['state_name'].value_counts().sort_index()
        print(state_counts.to_string())
        
        employment_df = df[df['state'] == 1]
        if len(employment_df) > 0:
            print(f"\nEmployment income statistics:")
            print(f"  Median: ${employment_df['income'].median():,.0f}")
            print(f"  Mean: ${employment_df['income'].mean():,.0f}")
            print(f"  Std: ${employment_df['income'].std():,.0f}")


def main():
    """Main entry point for testing the generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic career data")
    parser.add_argument("--config", default="exps/1a-config-hidden/parameters_4state.yaml",
                        help="Path to configuration file")
    parser.add_argument("--n-people", type=int, default=1000,
                        help="Number of individuals to simulate")
    parser.add_argument("--output", default="exps/2a-synthetic-data-hidden/synthetic_careers.csv",
                        help="Output file path")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed")
    
    args = parser.parse_args()
    
    generator = CareerGenerator(args.config, seed=args.seed)
    df = generator.generate_dataset(args.n_people, args.output)
    
    return df


if __name__ == "__main__":
    df = main()