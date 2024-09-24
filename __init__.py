from . import instruments
from . import tasks
import sys

if 'ipykernel' in sys.modules:
    from matplotlib import pyplot as plt
    from IPython.display import display, clear_output
    import numpy as np
    import math
    import time
    import pandas
    import mpld3
    mpld3.enable_notebook()
