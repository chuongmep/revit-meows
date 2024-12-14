import os
import sys
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
print(src_dir)
sys.path.insert(0, src_dir)

from src.revit_meows import APSRevit