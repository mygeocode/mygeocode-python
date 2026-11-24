"""Runs every test in this folder. Any warning (deprecation, resource, runtime ...) fails the run.

    python tests/run.py
"""

import os
import sys
import unittest
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)


def main():
    warnings.simplefilter("error")
    suite = unittest.defaultTestLoader.discover(HERE, pattern="test_*.py", top_level_dir=HERE)
    result = unittest.TextTestRunner(verbosity=1, stream=sys.stdout).run(suite)
    version = sys.version.split()[0]
    print(
        "Python {}: {} tests, {} failed, {} errors, {} skipped".format(
            version, result.testsRun, len(result.failures), len(result.errors), len(result.skipped)
        )
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
