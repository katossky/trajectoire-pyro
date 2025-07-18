#!/usr/bin/env python3
"""
generate_random.py

A simple script to generate and print 10 random integers between 1 and 100.
"""

import random

def main():
    """Generate 10 random integers between 1 and 100 and print them."""
    numbers = [random.randint(1, 100) for _ in range(10)]
    
    for idx, value in enumerate(numbers, start=1):
        print(f"Random number {idx}: {value}")

if __name__ == "__main__":
    main()