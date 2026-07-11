import os
import subprocess
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF
from skopt import Optimizer
from skopt.space import Real

# ==============================================================================
# CONFIGURATION SETTINGS
# ==============================================================================
BASE_DIR = r"C:\Users\annaa\Downloads\IISC\calibration"
IDF_DIR = os.path.join(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

CHOSEN_IDF = os.path.join(IDF_DIR, "level4_ACH_par.idf")
CHOSEN_IDD = os.path.join(IDF_DIR, "V9-4-0-Energy+.idd")
WEATHER_FILE = os.path.join(BASE_DIR, "testbed_.epw")

# Paths for EnergyPlus CLI execution
EPLUS_EXE = r"C:\EnergyPlusV26-1-1\energyplus.exe"  # Adjust path to your local installation
RUN_DIR = os.path.join(BASE_DIR, "eplus_run")

# Target evaluation keys from Stage 1 & 2
REAL_DATA_PATH = os.path.join(OUTPUT_DIR, "subset_bms.csv")
SENSOR_COL = r"\\SBBPIAF1\ACMV\ACMV\SS5_TESTBEDSYSTEM\Room3|SS5_ROOM3_TEMP"

# Initialize eppy
IDF.setiddname(CHOSEN_IDD)

# ==============================================================================
# 1. IDF PARAMETER MODIFIER FUNCTION
# ==============================================================================
import re

def apply_parameters_and_save(params, output_idf_path):
    """
    Applies optimization updates to target objects, then enforces a regex
    string replacement guardrail to fix eppy's geometry serialization bugs.
    """
    idf = IDF(CHOSEN_IDF)
    
    # ==============================================================================
    # STEP 1: CALIBRATION FIELD ASSIGNMENTS
    # ==============================================================================
    materials = list(idf.idfobjects['MATERIAL'])
    nomass_materials = list(idf.idfobjects['MATERIAL:NOMASS'])
    infiltrations = list(idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'])
    
    num_mats = len(materials)
    num_nomass = len(nomass_materials)
    
    total_material_slots = num_mats + num_nomass
    env_params = params[:total_material_slots]
    inf_params = params[total_material_slots:]
    
    param_idx = 0
    
    # Map Standard Materials securely by exact name anchors
    for mat in materials:
        if param_idx < len(env_params):
            mat_obj = idf.getobject('MATERIAL', mat.Name)
            if mat_obj and 'Conductivity' in mat_obj.objls:
                mat_obj.Conductivity = env_params[param_idx]
                param_idx += 1
            
    # Map NoMass Insulation Layers securely by exact name anchors
    for nomass in nomass_materials:
        if param_idx < len(env_params):
            mat_obj = idf.getobject('MATERIAL:NOMASS', nomass.Name)
            if mat_obj and 'Thermal_Resistance' in mat_obj.objls:
                mat_obj.Thermal_Resistance = env_params[param_idx]
                param_idx += 1

    # Map Air Leakage profiles securely by name anchors
    for idx, inf in enumerate(infiltrations):
        if idx < len(inf_params):
            inf_obj = idf.getobject('ZONEINFILTRATION:DESIGNFLOWRATE', inf.Name)
            if inf_obj:
                method = getattr(inf_obj, 'Design_Flow_Rate_Calculation_Method', 'AirChangesPerHour')
                if method == 'AirChangesPerHour':
                    inf_obj.Air_Changes_per_Hour = inf_params[idx]
                else:
                    inf_obj.Design_Flow_Rate = inf_params[idx]

    # ==============================================================================
    # STEP 2: STRENGTHENED REGEX GEOMETRY GUARDRAIL
    # ==============================================================================
    # Convert the currently modified in-memory object model to a raw text string stream
    raw_idf_text = idf.idfstr()
    
    # Look for the Plenum1_Ceiling block inside the raw text stream and patch it.
    # This prevents the fields from being stripped out during compilation.
    if "Plenum1_Ceiling" in raw_idf_text:
        # 1. Force the number of vertices from autocalculate to a literal 4
        raw_idf_text = re.sub(
            r"(BuildingSurface:Detailed,\s*Plenum1_Ceiling,\s*)[a-zA-Z\s]+,", 
            r"\1 4\2", 
            raw_idf_text, 
            flags=re.IGNORECASE
        )
        
        # 2. Fix the sun exposure field validation value (WindExposed -> NoSun)
        raw_idf_text = raw_idf_text.replace("WindExposed", "NoSun")
        raw_idf_text = raw_idf_text.replace("windExposed", "NoSun")
    
    # Write the stabilized raw text stream directly to disk, completely bypassing the bug
    with open(output_idf_path, 'w', encoding='utf-8') as f:
        f.write(raw_idf_text)
# ==============================================================================
# 2. ENERGYPLUS EXECUTION LOOP & LOSS EVALUATION
# ==============================================================================
def calibration_loss_function(params):
    """
    Objective function called by Bayesian Optimization. Takes parameter guesses,
    runs EnergyPlus, calculates CV(RMSE), and returns the loss score.
    """
    os.makedirs(RUN_DIR, exist_ok=True)
    tmp_idf = os.path.join(RUN_DIR, "iteration_model.idf")
    
    # Step A: Generate the unique model variant
    apply_parameters_and_save(params, tmp_idf)
    
    # Step B: Call EnergyPlus CLI as a quiet subprocess execution block
    cmd = [
        EPLUS_EXE,
        "--weather", WEATHER_FILE,
        "--output-directory", RUN_DIR,
        "--idd", CHOSEN_IDD,
        tmp_idf
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ EnergyPlus simulation crashed for parameters: {params}. Returning high penalty value.")
        return 999.0  # Return penalty value to guide optimizer away from invalid zones
        
    # Step C: Load real baseline data vs new simulated outputs
    sim_data_path = os.path.join(RUN_DIR, "eplusout.csv")
    if not os.path.exists(sim_data_path):
        return 999.0
        
    df_real = pd.read_csv(REAL_DATA_PATH)
    df_sim = pd.read_csv(sim_data_path)
    
    # Standardize simulated column keys (EnergyPlus outputs Zone Mean Air Temp)
    # Adjust this key name to match your exact EnergyPlus output variable setup
    sim_temp_col = "ROOM3:Zone Air Temperature [C]" 
    
    # Align rows based on your sliced subset timeline lengths
    y_real = df_real[SENSOR_COL].values
    
    # If simulated data lengths exceed or mismatch due to warm-up periods, slice to match
    y_sim = df_sim[sim_temp_col].head(len(y_real)).values
    
    # Step D: Calculate ASHRAE Guideline 14 CV(RMSE) Loss Metric
    n = len(y_real)
    mean_real = np.mean(y_real)
    rmse_numerator = np.sum((y_real - y_sim) ** 2)
    cv_rmse = (1.0 / mean_real) * np.sqrt(rmse_numerator / (n - 1)) * 100
    
    print(f"-> Iteration evaluated. Current Objective CV(RMSE): {cv_rmse:.2f}%")
    return cv_rmse

# ==============================================================================
# 3. BAYESIAN OPTIMIZATION ORCHESTRATION LAYER
# ==============================================================================
def run_bayesian_calibration(max_iterations=15):
    print("=== Starting Stage 3: Automated Bayesian Calibration Loop ===\n")
    
    idf = IDF(CHOSEN_IDF)
    materials = list(idf.idfobjects['MATERIAL'])
    nomass_materials = list(idf.idfobjects['MATERIAL:NOMASS'])
    infiltrations = list(idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'])
    
    search_bounds = []
    
    # Build envelope bounds based on actual objects found
    for i in range(len(materials) + len(nomass_materials)):
        search_bounds.append(Real(0.02, 2.5))
        
    # Build infiltration bounds based on actual objects found
    for j in range(len(infiltrations)):
        search_bounds.append(Real(0.0005, 0.02))
        
    # Initialize the Scikit-Optimize Bayesian Engine
    opt = Optimizer(
        dimensions=search_bounds,
        base_estimator="GP",  
        acq_func="EI",        
        n_initial_points=5    
    )
    
    print(f"Initialized optimization space over {len(search_bounds)} dynamic parameter paths.")
    print(f"Targeting execution over {max_iterations} strategic runs.\n")
    
    best_loss = float('inf')
    best_params = None
    
    for i in range(max_iterations):
        print(f"--- Calibration Step {i+1} / {max_iterations} ---")
        suggested_params = opt.ask()
        loss = calibration_loss_function(suggested_params)
        
        if loss == 999.0:
            err_file = os.path.join(RUN_DIR, "eplusout.err")
            if os.path.exists(err_file):
                print("   [Diagnostic Check] Extracting Severe Errors from log:")
                with open(err_file, 'r') as f:
                    for line in f:
                        if "Severe" in line or "Fatal" in line:
                            print(f"   ⚠️ E+ Log: {line.strip()}")
                            
        opt.tell(suggested_params, loss)
        if loss < best_loss:
            best_loss = loss
            best_params = suggested_params
            
    print("\n==============================================================================")
    print("🥇 CALIBRATION PROCESS COMPLETE")
    print(f"Final Calibrated Model CV(RMSE) Error: {best_loss:.2f}%")
    print("==============================================================================")
    final_calibrated_idf = os.path.join(OUTPUT_DIR, "calibrated_model_final.idf")
    apply_parameters_and_save(best_params, final_calibrated_idf)
    print(f"Saved the optimized, calibrated building model to: '{final_calibrated_idf}'")
if __name__ == "__main__":
    # Start the engine. We limit to 15 iterations for your first exploratory test run.
    run_bayesian_calibration(max_iterations=15)