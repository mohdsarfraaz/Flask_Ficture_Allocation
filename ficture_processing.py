
import pandas as pd
import numpy as np
from datetime import datetime
import time

def ficture_allocation(df, col_map, log_fn=print):
    """
    Performs the fixture allocation process.

    Args:
        df (pd.DataFrame): The input DataFrame.
        col_map (dict): A dictionary mapping generic column names to user-defined names.
        log_fn (function): Optional logging function to report progress (default: print).

    Returns:
        pd.DataFrame: The processed DataFrame with allocation columns.
    """
    start_time = datetime.now()

    store_name = col_map['store']
    department = col_map['department']
    udf = col_map['udf']
    mc_fic = col_map['mc_fic']
    cont_per = col_map['cont_per']
    art = col_map['art']

    df_1 = df.copy()
    fict_bal_dict = {}
    fict_req_dict = {}

    passes = 3

    for i in range(passes):
        df_1[f"Allocate_{i}"] = np.zeros(len(df_1))
        df_1[f"MC_BAl_{i}"] = np.zeros(len(df_1))
        df_1[f"FIC_REQ_{i}"] = np.zeros(len(df_1))

    df_1['rest_per'] = np.zeros(len(df_1))

    for i in range(passes):
        elapsed_time = datetime.now() - start_time
        elapsed_time = str(elapsed_time).split('.')[0]
        log_fn(f"Processing Pass {i+1} of {passes}... Elapsed Time: {elapsed_time}")
        time.sleep(0.5)

        grouped_data = df_1.groupby([store_name, department, udf])

        for (store, dep, disp), group in grouped_data:
            mc_fic_val = group[mc_fic].iloc[0]
            for idx in group.index:
                cont_per_val = df_1.at[idx, cont_per]
                fic_req = round(mc_fic_val * cont_per_val, 0)
                df_1.at[idx, f"FIC_REQ_{i}"] = fic_req
                df_1.at[idx, f"Allocate_{i}"] = fic_req
                df_1.at[idx, f"MC_BAl_{i}"] = mc_fic_val - fic_req
                mc_fic_val -= fic_req

    return df_1
