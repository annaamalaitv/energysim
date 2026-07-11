import os
import copy
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import minimize
from geomeppy import IDF
from altnew import altglo
from init import juzcsv

# Ensure eppy/geomeppy knows your core EnergyPlus directory
# Update the version tag if yours is different!
IDF.setiddname(r"C:\EnergyPlusV26-1-1\Energy+.idd")

# =================================================================
# YOUR PATH FILES CONFIGURATION
# =================================================================
BASE_IDF_PATH = Path(r"C:\Users\annaa\Downloads\IISC\sim2\ASHRAE901_OfficeLarge_STD2019_NewDelhi.idf")
WEATHER_PATH  = r"C:\Users\annaa\Downloads\IISC\sim2\IND_DL_New.Delhi-Gandhi.Intl.AP.421810_TMYx.2009-2023.epw"
TARGET_CSV    = r"C:\Users\annaa\Downloads\abnormal\eplusout.csv"
TEMP_SIM_DIR  = r"C:\Users\annaa\Downloads\IISC\sim1\code\temp_sim"

# Load the base pristine IDF object using your logic
base_idf_object = IDF(str(BASE_IDF_PATH))

# =================================================================
# 1. THE ERROR EVALUATION FUNCTION (RMSE)
# =================================================================
def calculate_rmse(target_csv_path, sim_csv_path):
    # Utilizing your load_and_clean_data logic structure implicitly
    df_target = pd.read_csv(Path(target_csv_path))
    df_sim = pd.read_csv(Path(sim_csv_path))
    
    df_target.columns = df_target.columns.str.strip()
    df_sim.columns = df_sim.columns.str.strip()
    
    column_name = 'Whole Building:Facility Total Electricity Demand Rate [W](Hourly)'
    
    y_true = df_target[column_name].values
    y_pred = df_sim[column_name].values
    
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    print(f"the current error is ", rmse)
    return rmse

# =================================================================
# 2. THE PIPELINE LOOP (OBJECTIVE FUNCTION FOR SCIPY)
# =================================================================
def calibration_loop(guess_multiplier):
    current_multiplier = guess_multiplier[0]
    print(f"\n[Optimizer Nudge] Trying Occupancy Scale Multiplier: x{current_multiplier:.4f}")
    
    try:
        # Step A: Use your altglo to modify and save the new .idf file to disk
        altglo(
            idf_object=base_idf_object,
            parameter_type='people',
            multiplier=current_multiplier,
            save_directory=TEMP_SIM_DIR,
            new_filename="temp_iteration.idf"
        )
        
        # Step B: Re-instantiate a fresh, healthy IDF object from the newly written file
        # This completely fixes the "no attribute 'epw'" deepcopy bug!
        temp_idf_file_path = Path(TEMP_SIM_DIR) / "temp_iteration.idf"
        fresh_idf_object = IDF(str(temp_idf_file_path), str(WEATHER_PATH))
        
        print(f"Successfully created a fresh IDF object for multiplier x{current_multiplier:.4f}")
        # Step C: Run the simulation using your clean juzcsv function
        juzcsv(
            idf_object=fresh_idf_object,
            weather_path=WEATHER_PATH,
            output_dir=TEMP_SIM_DIR
        )
        print(f"Simulation completed for multiplier x{current_multiplier:.4f}. Output CSV generated.")

        
        # Step D: Parse the output and calculate your RMSE
        generated_csv = os.path.join(TEMP_SIM_DIR, "eplusout.csv")
        error_score = calculate_rmse(TARGET_CSV, generated_csv)
        
        print(f"Current Loop Result ---> RMSE Error: {error_score:.2f}")
        return error_score

    except Exception as e:
        print(f"Loop Iteration failed or crashed. Penalizing path direction. Error: {e}")
        return 99999999.0
# =================================================================
# 3. EXECUTING THE MATHEMATICAL SEARCH
# =================================================================
if __name__ == "__main__":
    print("Initializing automated Synthetic Twin calibration pipeline...")
    
    # Range constraints: Don't let occupancy go below 0.1x or above 5x baseline
    search_bounds = [(0.1, 5.0)]
    
    # Start at 1.0 (assuming normal baseline model is unchanged at first)
    initial_guess = [1.0]
    
    # Let Nelder-Mead handle the step sizing, direction switches, and convergence checks
    optimization_result = minimize(
        calibration_loop,
        initial_guess,
        method='Nelder-Mead',
        bounds=search_bounds,
        options={'xatol': 0.01, 'fatol': 5.0, 'maxiter': 25} # Stop when the multiplier narrows down within 1% precision
    )
    
    print("\n==================================================")
    print("PIPELINE CALIBRATION COMPLETE")
    print(f"Discovered True Multiplier: x{optimization_result.x[0]:.4f}")
    print("==================================================")