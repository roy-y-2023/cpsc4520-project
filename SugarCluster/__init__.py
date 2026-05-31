import sys
import os

_sugarscape_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "sugarscape"))
if os.path.isdir(_sugarscape_dir) and _sugarscape_dir not in sys.path:
    sys.path.insert(0, _sugarscape_dir)
