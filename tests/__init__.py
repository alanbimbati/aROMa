import os
import sys

# Force test DB for all tests in this package by default
os.environ.setdefault('TEST_DB', '1')
os.environ.setdefault('TEST', '1')

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
