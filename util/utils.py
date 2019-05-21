import numpy as np
import pandas as pd
import math


def currency_to_number(x):
    """Format dollar currency value with comma grouping to a float"""
    if isinstance(x, str):
        if ',' in x:
            x = x.replace(',', '')
        if '$' in x:
            x = x.strip('$')
        return float(x)
    elif math.isnan(x):
        return np.nan
    elif isinstance(x, float) and not math.isnan(x):
        return x
    else:
        raise TypeError


def percentage_to_ratio(x):
    """Format percentage string to float"""
    if isinstance(x, str):
        if '%' in x:
            x = x.strip('%')
        return float(x) / 100
    elif math.isnan(x):
        return np.nan
    elif isinstance(x, float) and not math.isnan(x):
        return x
    else:
        raise TypeError


def boolean_to_boolean(x):
    """Convert from f and t to Python False and True types"""

    if isinstance(x, str):
        if x == 'f':
            return False
        elif x == 't':
            return True
        else:
            raise ValueError
    elif math.isnan(x):
        return np.nan
    elif isinstance(x, bool):
        return x
    else:
        print(x)
        raise TypeError


def boolean_to_int(x):
    """Convert from f and t to Python False and True types"""

    if isinstance(x, str):
        if x == 'f':
            return 0
        elif x == 't':
            return 1
        else:
            raise ValueError
    elif math.isnan(x):
        return np.nan
    elif isinstance(x, bool):
        raise TypeError
    elif isinstance(x, int):
        return x
    else:
        print(x)
        raise TypeError
