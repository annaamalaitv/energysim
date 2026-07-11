import os
import sys
import pandas as pd
import numpy as np
from params import apply_parameters_and_save
from geomeppy import IDF

def calibration_loss_function(params, geom_idf, weather_file, run_dir, real_data_path, sensor_col):
    """
    Objective function for calibration. Updates the GeomEppy IDF object,
    runs the simulation natively via GeomEppy, and computes ASHRAE Guideline 14 CV(RMSE).
    """
    # Define the temporary IDF path where this iteration's variant will be saved
    os.makedirs(run_dir, exist_ok=True)
    tmp_idf_path = os.path.join(run_dir, "iteration_model.idf")
    
    # 1. Apply parameters and save the model using your working Step 3 logic
    apply_parameters_and_save(params, geom_idf, tmp_idf_path)
    

    # 2. Reload the saved iteration file as a fresh GeomEppy object to isolate execution
    from geomeppy import IDF
    iteration_idf = IDF(tmp_idf_path)
    iteration_idf.epw = weather_file

    actual_eplus_dir = r"C:\EnergyPlusV26-1-1"
    original_path = os.environ.get("PATH", "")
    
    # 3. Execute the simulation NATIVELY using GeomEppy's .run() method
    print(f"-> Launching native GeomEppy simulation run...")
    try:
        iteration_idf.run(

            os.environ["PATH"] == actual_eplus_dir + os.pathinfosep + original_path,

            weather=weather_file,
            output_directory=run_dir,
            readvars=True,       # Ensures output CSV is fully generated
            expandobjects=True  # Handles any HVAC or high-level macro expansions automatically
        )
    except Exception as e:
        print(f"⚠️ Native GeomEppy simulation crashed for parameters: {params}. Error: {e}")
        return 999.0  # Return penalty value to guide optimizer away from invalid zones
        
    # 4. Load baseline data vs new simulated outputs
    sim_data_path = os.path.join(run_dir, "eplusout.csv")
    if not os.path.exists(sim_data_path):
        print("⚠️ Simulation completed but 'eplusout.csv' was not found.")
        return 999.0
        
    df_real = pd.read_csv(real_data_path)
    df_sim = pd.read_csv(sim_data_path)
    
    # Standard EnergyPlus Output Variable for Zone Mean Air Temperature
    sim_temp_col = "ROOM3:Zone Air Temperature [C]" 
    
    # Extract arrays
    y_real = df_real[sensor_col].values
    
    # Slice the simulated arrays to match length if warm-up intervals cause length mismatches
    y_sim = df_sim[sim_temp_col].head(len(y_real)).values
    
    # 5. Calculate ASHRAE Guideline 14 CV(RMSE) % Loss Metric
    n = len(y_real)
    mean_real = np.mean(y_real)
    rmse_numerator = np.sum((y_real - y_sim) ** 2)
    
    if mean_real == 0:
        return 999.0
        
    cv_rmse = (1.0 / mean_real) * np.sqrt(rmse_numerator / (n - 1)) * 100
    
    print(f"-> Iteration complete. Evaluated CV(RMSE): {cv_rmse:.2f}%")
    return cv_rmse

if __name__ == "__main__":
    from geomeppy import IDF
    import numpy as np
    import os
    
    # Define Local Paths
    BASE_DIR = r"C:\Users\annaa\Downloads\IISC\calibration"
    CHOSEN_IDF = os.path.join(BASE_DIR, "level4_ACH_par.idf")
    CHOSEN_IDD = os.path.join(BASE_DIR, "V9-4-0-Energy+.idd")
    WEATHER_FILE = os.path.join(BASE_DIR, "testbed_.epw")
    
    RUN_SANDBOX = os.path.join(BASE_DIR, "eplus_run_test")
    REAL_DATA_PATH = os.path.join(BASE_DIR, "output", "subset_bms.csv")
    SENSOR_COL = r"\\SBBPIAF1\ACMV\ACMV\SS5_TESTBEDSYSTEM\Room3|SS5_ROOM3_TEMP"
    
    # Initialize GeomEppy Object
    IDF.setiddname(CHOSEN_IDD)
    test_geom_idf = IDF(CHOSEN_IDF)
    
    # Create a random array matching your 12 envelope + 8 infiltration variables
    mock_params = np.concatenate([
        np.random.uniform(0.1, 1.5, 12),  # Material space
        np.random.uniform(0.001, 0.01, 8)  # Infiltration space
    ]).tolist()
    
    print("Testing Native GeomEppy Calibration Loss Function...")
    try:
        current_loss = calibration_loss_function(
            params=mock_params,
            geom_idf=test_geom_idf,
            weather_file=WEATHER_FILE,
            run_dir=RUN_SANDBOX,
            real_data_path=REAL_DATA_PATH,
            sensor_col=SENSOR_COL
        )
        print(f"\n✅ Function successfully ran! Target CV(RMSE): {current_loss:.2f}%")
    except Exception as e:
        print(f"\n❌ Native execution failed: {e}")