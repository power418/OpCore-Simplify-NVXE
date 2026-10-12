#!/usr/bin/env python3
import unittest
import sys
import os

if __name__ == "__main__":
    # Ensure project root is in sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=os.path.dirname(__file__), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
