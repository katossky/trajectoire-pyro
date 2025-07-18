import random

def generate_random_numbers(count=10, min_val=1, max_val=100):
    """Generate a list of random integers within a specified range."""
    return [random.randint(min_val, max_val) for _ in range(count)]

if __name__ == "__main__":
    # Set seed for reproducibility (optional)
    random.seed()  # Uses system time or OS-specific source
    
    # Generate 10 random integers between 1 and 100
    random_numbers = generate_random_numbers(10, 1, 100)
    
    # Print the results
    print("Generated 10 random numbers:")
    print(random_numbers)
    
    # Additional formatting for readability
    print("\nNumbers separated by commas:")
    print(", ".join(map(str, random_numbers)))