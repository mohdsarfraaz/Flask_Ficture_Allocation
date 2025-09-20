"""Core allocation logic for the fixture allocation tool."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict

import numpy as np
import pandas as pd

ProgressLogger = Callable[[str], None]


def _normalise_series(series: pd.Series) -> pd.Series:
    """Return a non-negative series that sums to 1.

    The contribution column occasionally contains negative values or missing
    data.  These values do not make sense for the allocation algorithm, so we
    clamp them to zero and, if necessary, distribute the share evenly across
    the remaining rows.
    """

    series = series.clip(lower=0)
    total = series.sum()

    if total == 0 or np.isclose(total, 0):
        if len(series) == 0:
            return series
        return pd.Series(np.repeat(1 / len(series), len(series)), index=series.index)

    return series / total


def ficture_allocation(df: pd.DataFrame, col_map: Dict[str, str], log_fn: ProgressLogger = print) -> pd.DataFrame:
    """Perform the multi-pass fixture allocation process.

    The raw data contains the desired share of fixtures for each article as a
    percentage.  Because fixtures are discrete objects, we calculate the
    requirement using three passes:

    1. The first pass allocates the floor of each article's desired share.
    2. The second pass distributes any remainder based on the largest
       fractional values (closest to the next full fixture).
    3. The third pass distributes any remaining fixtures evenly based on the
       weight of each article.

    Parameters
    ----------
    df:
        The uploaded dataset.
    col_map:
        Mapping of logical column names to the actual column titles supplied
        by the user via the web form.
    log_fn:
        Optional logger (defaults to :func:`print`).
    """

    start_time = datetime.now()

    store_name = col_map['store']
    department = col_map['department']
    udf = col_map['udf']
    mc_fic = col_map['mc_fic']
    cont_per = col_map['cont_per']

    df_processed = df.copy()

    for allocation_pass in range(3):
        df_processed[f"Allocate_{allocation_pass}"] = 0
        df_processed[f"MC_BAl_{allocation_pass}"] = 0
        df_processed[f"FIC_REQ_{allocation_pass}"] = 0.0

    df_processed['rest_per'] = 0.0
    df_processed['Final_Allocation'] = 0

    df_processed[mc_fic] = pd.to_numeric(df_processed[mc_fic], errors='coerce').fillna(0)
    df_processed[cont_per] = pd.to_numeric(df_processed[cont_per], errors='coerce').fillna(0)

    if (df_processed[cont_per] > 1).any():
        df_processed[cont_per] = df_processed[cont_per] / 100.0

    group_cols = [store_name, department, udf]
    grouped = df_processed.groupby(group_cols, dropna=False)
    group_total = grouped.ngroups
    progress = {'count': 0}

    def allocate_group(group: pd.DataFrame) -> pd.DataFrame:
        progress['count'] += 1
        if group_total:
            elapsed = datetime.now() - start_time
            elapsed_clean = str(elapsed).split('.')[0]
            if progress['count'] == 1 or progress['count'] % 25 == 0 or progress['count'] == group_total:
                log_fn(
                    f"Processing group {progress['count']}/{group_total}... "
                    f"Elapsed Time: {elapsed_clean}"
                )

        group = group.copy()

        total_fixtures = int(round(group[mc_fic].iloc[0]))
        if total_fixtures <= 0 or len(group) == 0:
            return group

        contributions = _normalise_series(group[cont_per])
        desired = contributions * total_fixtures

        allocate_first = np.floor(desired).astype(int)
        remainder = desired - allocate_first

        fixtures_left = int(total_fixtures - allocate_first.sum())
        allocate_second = np.zeros(len(group), dtype=int)
        allocate_third = np.zeros(len(group), dtype=int)

        if fixtures_left > 0:
            order = np.argsort(-remainder.to_numpy())
            for idx in order:
                if fixtures_left <= 0:
                    break
                if remainder.iat[idx] <= 0:
                    continue
                allocate_second[idx] += 1
                fixtures_left -= 1

        if fixtures_left > 0:
            order = np.argsort(-contributions.to_numpy())
            if len(order) > 0:
                idx = 0
                while fixtures_left > 0:
                    allocate_third[order[idx % len(order)]] += 1
                    fixtures_left -= 1
                    idx += 1

        total_allocation = allocate_first + allocate_second + allocate_third

        group[f"FIC_REQ_0"] = desired.round(2)
        group[f"Allocate_0"] = allocate_first
        group[f"MC_BAl_0"] = total_fixtures - allocate_first.sum()

        group[f"FIC_REQ_1"] = remainder.round(2)
        group[f"Allocate_1"] = allocate_second
        group[f"MC_BAl_1"] = total_fixtures - (allocate_first + allocate_second).sum()

        group[f"FIC_REQ_2"] = np.zeros(len(group))
        group[f"Allocate_2"] = allocate_third
        group[f"MC_BAl_2"] = total_fixtures - total_allocation.sum()

        group['Final_Allocation'] = total_allocation
        group['rest_per'] = (desired - total_allocation).round(4)

        return group

    processed = grouped.apply(allocate_group, group_keys=False)

    elapsed_time = datetime.now() - start_time
    elapsed_clean = str(elapsed_time).split('.')[0]
    log_fn(f"Fixture allocation completed. Total time: {elapsed_clean}")

    return processed
