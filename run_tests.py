#!/usr/bin/env python3

import pytest
import sys
import os

if __name__ == "__main__":
    # Change to workspace directory
    os.chdir('/workspace')
    
    # Run pytest on tests directory
    result = pytest.main(['tests/test_generator.py', '-v'])
    sys.exit(result)