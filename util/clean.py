import pandas as pd
import numpy  as np
from code import utils




def rinse_listings(_df):
    type: pd.DataFrame
    """
    This function takes Inside Airbnb listings
    data and cleans and removes uninteresting columns.
    For now this is hardcoded, but could be expanded to a
    more elaborate function
    :param df:
    :return:
    """
    df = _df.copy(deep=True)
    #remove columns with only 1 value
    df = df.drop(labels=df.nunique()[df.nunique() < 2].index, axis=1)
    #remove columns with all unique values
    all_unique_cols = df[df.nunique() / df.count() == 1]
    all_unique_cols = all_unique_cols.drop(labels=['latitude', 'longitude', 'id'], axis=0).index
    df = df.drop(labels=all_unique_cols, axis=1)
    #drop text columns and other non-informative columns
    drop_columns = ['name', 'summary', 'space', 'description', 'neighborhood_overview', 'notes', 'transit', 'host_url',
                    'host_name', 'host_location', 'host_about', 'host_thumbnail_url', 'host_picture_url',
                    'host_neighbourhood', 'host_has_profile_pic', 'street', 'city', 'state', 'smart_location']
    df = df.drop(drop_columns, axis=1)



