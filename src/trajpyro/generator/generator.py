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
            
        else:  # From deceased
            probs = [0.0, 0.0, 0.0, 1.0]
        
        # Adjust mortality based on age using Gompertz model
        if age > 0:
            base_rate = params['mortality_params']['base_mortality']
            age_factor = params['mortality_params']['age_exponent']
            age_mortality = base_rate * np.exp(age_factor * (age - 25))
            
            if current_state == 0:
                probs[-1] = min(probs[-1] + age_mortality, 0.5)
                probs[:-1] = [p * (1 - probs[-1]) / sum(probs[:-1]) for p in probs[:-1]]
            elif current_state == 1:
                probs[-1] = min(probs[-1] + age_mortality * 0.8, 0.3)  # Lower for workers
                probs[:-1] = [p * (1 - probs[-1]) / sum(probs[:-1]) for p in probs[:-1]]
            elif current_state == 2:
                probs[-1] = min(probs[-1] + age_mortality * 1.5, 0.9)  # Higher for retirees
                probs[:-1] = [p * (1 - probs[-1]) / sum(probs[:-1]) for p in probs[:-1]]
        
        # Ensure probabilities sum to 1
        probs = torch.tensor(probs, dtype=torch.float32)
        probs = probs / probs.sum()
        return probs
    
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
        income_log = pyro.sample(
            "income_log",
            dist.Normal(mean_log, std_log)
        )
        
        # Ensure non-negative income
        income = torch.exp(income_log)
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
        states = [0, 1, 2, 3]
        
        # Sample initial state
        initial_state = pyro.sample(
            f"initial_state_{person_id}",
            dist.Categorical(torch.tensor([
                initial_probs['inactive'],
                initial_probs['employed'],
                initial_probs['retired'],
                initial_probs['deceased']
            ]))
        ).item()
        
        # Initialize career
        career_data = []
        current_state = initial_state
        age = self.parameters['age_params']['min_age']
 
        while age <= self.parameters['age_params']['death_age']:
            # Handle deceased state
            if current_state == 3:
                # Deceased stays deceased - pad remaining years with income = 0
                for remaining_age in range(age, self.parameters['age_params']['death_age'] + 1):
                    career_data.append({
                        'person_id': person_id,
                        'year': 2020 + (remaining_age - self.parameters['age_params']['min_age']),
                        'age': remaining_age,
                        'state': current_state,
                        'income': 0.0
                    })
                break
            
            # Sample income
            income = self._sample_income(age, current_state)
            
            # Record current year
            career_data.append({
                'person_id': person_id,
                'year': 2020 + (age - self.parameters['age_params']['min_age']),
                'age': age,
                'state': current_state,
                'income': income
            })
            
            # Sample next state
            probs = self._get_transition_probs(current_state, age)
            current_state = pyro.sample(
                f"transition_{person_id}_{age}",
                dist.Categorical(probs)
            ).item()
            
            age += 1
            
            # Stop if deceased
            if current_state == 3 and age <= self.parameters['age_params']['death_age']:
                # Record final year as deceased
                career_data.append({
                    'person_id': person_id,
                    'year': 2020 + (age - self.parameters['age_params']['min_age']),
                    'age': age,
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
            if verbose and i % 1000 == 0:
                print(f"Generating careers... {i}/{n_individuals}")
            
            career = self.generate_career(i + 1)
            all_careers.extend(career)
        
        # Convert to DataFrame
        df = pd.DataFrame(all_careers)
        
        # Convert state to categorical for clarity
        state_names = ["inactive", "employed", "retired", "deceased"]
        df['state_name'] = df['state'].map({i: name for i, name in enumerate(state_names)})
        
        # Save output
        output_path = Path(output_file)
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
        print(df['state_name'].value_counts().to_string())
        
        employment_df = df[df['state'] == 1]
        if len(employment_df) > 0:
            print(f"\nEmployment income statistics:")
            print(f"  Median: ${employment_df['income'].median():,.0f}")
            print(f"  Mean: ${employment_df['income'].mean():,.0f}")
            print(f"  Std: ${employment_df['income'].std():,.0f}")
    
    def generate_validation_report(self, df: pd.DataFrame) -> Dict:
        """
        Generate validation report comparing synthetic data to expected parameters.
        
        Args:
            df: Generated dataset
            
        Returns:
            Dictionary with comparison metrics
        """
        params = self.parameters
        
        # Calculate empirical transition rates
        def calculate_transitions(state_from: int, state_to: int) -> float:
            mask = df['state'] == state_from
            prev_states = df[mask]
            if len(prev_states) == 0:
                return 0.0
            
            # Find next states for these individuals
            next_states = []
            for pid in prev_states['person_id'].unique():
                pid_data = df[df['person_id'] == pid]
                transitions_idx = pid_data[pid_data['state'] == state_from].index
                for idx in transitions_idx:
                    if idx + 1 < len(df) and df.loc[idx + 1, 'person_id'] == pid:
                        next_states.append(df.loc[idx + 1, 'state'])
            
            if not next_states:
                return 0.0
            
            return sum(1 for s in next_states if s == state_to) / len(next_states)
        
        # Create validation report
        report = {
            'empirical_transition_rates': {},
            'expected_income': {},
            'empirical_income': {},
            'coverage_summary': {}
        }
        
        # Add transition rate comparisons
        for from_state in range(4):
            for to_state in range(4):
                if from_state == 0:
                    param_key = f"transition_from_from_{['inactive', 'employed', 'retired', 'deceased'][from_state]}"
                    if param_key in params:
                        report['empirical_transition_rates'][f"{from_state}_{to_state}"] = {
                            'empirical': calculate_transitions(from_state, to_state),
                            'expected': params['transition_from_' + ['inactive', 'employed', 'retired', 'deceased'][from_state]][f"to_{['inactive', 'employed', 'retired', 'deceased'][to_state]}"]
                        }
        
        # Income statistics
        emp_data = df[df['state'] == 1]
        if len(emp_data) > 0:
            report['empirical_income'] = {
                'median': float(emp_data['income'].median()),
                'mean': float(emp_data['income'].mean()),
                'std': float(emp_data['income'].std())
            }
            report['expected_income'] = {
                'median': np.exp(params['income_params']['lognormal_mean']),
                'expected_distribution': 'log-normal'
            }
        
        return report


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
    parser.add_argument("--validate", action="store_true",
                        help="Generate validation report")
    
    args = parser.parse_args()
    
    generator = CareerGenerator(args.config, seed=args.seed)
    df = generator.generate_dataset(args.n_people, args.output)
    
    if args.validate:
        report = generator.generate_validation_report(df)
        
        # Save validation report
        val_file = args.output.replace('.csv', '_validation.json')
        with open(val_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Validation report saved to {val_file}")
    
    return df


if __name__ == "__main__":
    df = main()