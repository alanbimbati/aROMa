import os
import sys

# Force test DB for all tests in this package
os.environ['TEST_DB'] = '1'
os.environ['TEST'] = '1'

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
