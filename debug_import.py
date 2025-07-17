import os
import sys
import importlib.util
from pathlib import Path

print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Check src directory structure
src_root = Path('/workspace/src')
print(f"\nSource directories in {src_root}:")
for item in src_root.iterdir():
    print(f"  {item}")

# Check trajpyro directory
trajpyro_dir = src_root / 'trajpyro'
if trajpyro_dir.exists():
    print(f"\nFiles in {trajpyro_dir}:")
    for item in trajpyro_dir.iterdir():
        print(f"  {item}")
else:
    print(f"\nDirectory {trajpyro_dir} does not exist")

# Check for the generator module
generator_path = trajpyro_dir / 'generator.py'
if generator_path.exists():
    print(f"\ngenerator.py exists at: {generator_path}")
    
    # Try to import it directly
    try:
        spec = importlib.util.spec_from_file_location("generator", generator_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print("Successfully imported generator module")
        
        # Check for CareerGenerator class
        if hasattr(module, 'CareerGenerator'):
            print("CareerGenerator class found")
        else:
            print("CareerGenerator class NOT found")
    except Exception as e:
        print(f"Import error: {e}")
else:
    print(f"\ngenerator.py does NOT exist at: {generator_path}")