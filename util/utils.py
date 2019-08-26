import os
import matplotlib.pyplot as plt
import statsmodels.api as sm
import numpy as np
import pandas as pd
import math
import folium



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


def regplot(x, y, label, color, **kwargs):
    plt.scatter(x, y, c='k')
    name = x.name
    x_reg = sm.add_constant(pd.Series(data=np.linspace(np.min(x), np.max(x), num=20), name=x.name))
    x = sm.add_constant(x)
    mod = sm.OLS(y, x, has_constant='add')
    res = mod.fit()
    plt.plot(x_reg[name], res.predict(x_reg), 'r')
    plt.annotate("R2: {:.3}".format(res.rsquared), xy=(0.9, 1), xycoords='axes fraction')
    plt.annotate("y={:.3}x + {:.3}".format(res.params[name], res.params['const']), xy=(0.01, 1),
                 xycoords='axes fraction')
    if name == 'price':
        if y.name == 'weekly_price':
            plt.plot(x_reg[name], 7 * x_reg[name], label='7xprice')
        if y.name == 'monthly_price':
            plt.plot(x_reg[name], 30 * x_reg[name], label='30xprice')
    if name == 'weekly_price' and y.name == 'monthly_price':
        plt.plot(x_reg[name], 4 * x_reg[name], label='4xweekly price')
    plt.legend()
    return res


def _inline_map(m, width=650, height=500):
    from IPython.display import HTML, display
    srcdoc = m.HTML.replace('"', '&quot;')
    embed = HTML('<iframe srcdoc="{}" '
                 'style="width :{}px; height: {}px; display:block; width: 50%; margin: 0 auto;'
                 'border: none"></iframe>'.format(srcdoc, width, height))
    return embed


def plot_map(df, loc, data_col, prefix=None, bins=None):
    neighborhoods_json = os.path.join("seattle_neighborhoods.geojson")
    m = folium.Map(location=[47.611406, -122.337498], zoom_start=12)

    if loc == 'neighbourhood' or loc == 'neighbourhood_cleansed':
        keyon = 'feature.properties.name'
    elif loc == 'neighbourhood_group_cleansed':
        keyon = 'feature.properties.nhood'

    else:
        return None

    if bins is None:
        bins = 6

    folium.Choropleth(
        geo_data=neighborhoods_json,
        name='choropleth',
        data=df,
        columns=[loc, data_col],
        key_on=keyon,
        fill_color='YlGnBu',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=data_col,
        reset=True,
        bins=bins
    ).add_to(m)
    folium.LayerControl().add_to(m)
    if prefix:
        m.save('{}_{}.html'.format(prefix, data_col))
    else:
        m.save('{}.html'.format(data_col))
    return m