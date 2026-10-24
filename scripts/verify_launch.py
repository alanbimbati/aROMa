import sys
import json
import os

if '--snapshot' in sys.argv:
    idx = sys.argv.index('--snapshot')
    filename = sys.argv[idx+1]
    with open(filename, 'w') as f:
        json.dump({"snapshot": True}, f)
elif '--check' in sys.argv:
    idx = sys.argv.index('--check')
    filename = sys.argv[idx+1]
    if not os.path.exists(filename):
        sys.exit(1)
