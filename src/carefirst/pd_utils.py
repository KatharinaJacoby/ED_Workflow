
import pandas as pd
from typing import Optional

def clamp_series_or_frame(obj, lower: Optional[float] = None, upper: Optional[float] = None):
    """
    Replacement for non-existent pd.clamp: uses .clip on Series/DataFrame.
    """
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.clip(lower=lower, upper=upper)
    raise TypeError("Expected pandas Series or DataFrame")

def safe_assign(df: pd.DataFrame, col: str, values):
    """
    Avoid SettingWithCopy: always use .loc and return the mutated frame.
    """
    df.loc[:, col] = values
    return df

def assert_no_na(df: pd.DataFrame, cols):
    cols = list(cols)
    na = df[cols].isna().sum()
    if int(na.sum()) > 0:
        raise ValueError(f"NA values present in columns: {na[na>0].to_dict()}")
    return True
