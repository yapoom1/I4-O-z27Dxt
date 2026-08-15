import pytest
import sys
import os

if __name__ == "__main__":
    # Ensure tests are run from the project root
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    
    # Run pytest. You can pass arguments via command line or they will default to 'tests/'
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests/"]
    
    print(f"=== Running Pytest with args: {args} ===")
    exit_code = pytest.main(args)
    sys.exit(exit_code)
