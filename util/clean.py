import pandas as pd
import numpy  as np
from util.utils import currency_to_number, boolean_to_boolean, boolean_to_int, percentage_to_ratio


def rinse_listings(_df):
    type: pd.DataFrame
    """
    This function takes Inside Airbnb listings
    data and cleans and removes uninteresting columns.
    For now this is hardcoded, but could be expanded to a
    more elaborate function. It is not rinsed of all NaNs, as we have not performed feature engineering
    :param df:
    :return: cleaned dataframe
    """
    df = _df.copy(deep=True)
    # remove columns with only 1 value
    df = df.drop(labels=df.nunique()[df.nunique() < 2].index, axis=1)
    # remove columns with all unique values
    all_unique_cols = df.loc[:,df.nunique() / df.count() == 1]
    print(all_unique_cols.columns)
    all_unique_cols = all_unique_cols.drop(labels=['latitude', 'longitude', 'id'], axis=1).columns
    df = df.drop(labels=all_unique_cols, axis=1)
    # drop text columns and other non-informative columns
    drop_columns = ['square_feet', 'name', 'summary', 'space', 'description', 'neighborhood_overview', 'notes',
                    'transit', 'host_url', 'host_name', 'host_location', 'host_about', 'host_thumbnail_url',
                    'host_picture_url', 'host_neighbourhood', 'host_has_profile_pic', 'street', 'city', 'state',
                    'smart_location']
    df = df.drop(drop_columns, axis=1)
    # reformat currency to number, assuming dollar
    df['monthly_price'] = df['monthly_price'].map(currency_to_number)
    df['price'] = df['price'].map(currency_to_number)
    df['weekly_price'] = df['weekly_price'].map(currency_to_number)
    df['security_deposit'] = df['security_deposit'].map(currency_to_number)
    df['cleaning_fee'] = df['cleaning_fee'].map(currency_to_number)
    df['extra_people'] = df['extra_people'].map(currency_to_number)
    # reformat percentage to ratio
    df['host_response_rate'] = df['host_response_rate'].map(percentage_to_ratio)
    df['host_acceptance_rate'] = df['host_acceptance_rate'].map(percentage_to_ratio)
    # reformat boolean values to pythonic booleans or ints
    df['instant_bookable'] = df['instant_bookable'].map(boolean_to_boolean)
    df['require_guest_profile_picture'] = df['require_guest_profile_picture'].map(boolean_to_boolean)
    df['require_guest_phone_verification'] = df['require_guest_phone_verification'].map(boolean_to_boolean)
    df['is_location_exact'] = df['is_location_exact'].map(boolean_to_boolean)
    df['host_is_superhost'] = df['host_is_superhost'].map(boolean_to_int)
    df['host_identity_verified'] = df['host_identity_verified'].map(boolean_to_boolean)
    return df


