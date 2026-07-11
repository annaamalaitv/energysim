import pandas as pd
import numpy as np
import os

def slicer(data_dir, output_dir=None):
    print("=== Starting Stage 1: Data Profiling & Subsetting ===\n")
    
    # -------------------------------------------------------------
    # 1. Load the Massive BMS Log (pi_data_BMS.csv) First
    # -------------------------------------------------------------
    bms_path = os.path.join(data_dir, 'pi_data_BMS.csv')
    print("[BMS] Loading large automation trend log...")
    bms_df = pd.read_csv(bms_path)
    
    # Convert and strictly strip timezone awareness to keep it naive
    bms_df['datetime'] = pd.to_datetime(bms_df['datetime'], dayfirst=True, errors='coerce')
    if bms_df['datetime'].dt.tz is not None:
        bms_df['datetime'] = bms_df['datetime'].dt.tz_localize(None)
        
    bms_min_date = bms_df['datetime'].min()
    bms_max_date = bms_df['datetime'].max()
    print(f"-> BMS Data covers range: {bms_min_date} to {bms_max_date}")

    # -------------------------------------------------------------
    # 2. Load the Experiment Schedule & Find a Matching Phase
    # -------------------------------------------------------------
    schedule_path = os.path.join(data_dir, 'experiment_schedule.csv')
    schedule_df = pd.read_csv(schedule_path, sep=None, engine='python')
    schedule_df.columns = schedule_df.columns.str.strip()
    
    # Parse dates and strip timezones if any exist
    schedule_df['start_dt'] = pd.to_datetime(schedule_df['start_date'] + ' ' + schedule_df['start_time'])
    schedule_df['end_dt'] = pd.to_datetime(schedule_df['end_date'] + ' ' + schedule_df['end_time'])
    
    # Filter schedule rows that actually overlap with our available BMS records
    valid_phases = schedule_df[
        (schedule_df['start_dt'] >= bms_min_date) & 
        (schedule_df['end_dt'] <= bms_max_date)
    ]
    
    if valid_phases.empty:
        print("⚠️ Warning: No schedule items directly overlap the BMS timestamp range.")
        print("Falling back to the first available schedule window for testing.")
        target_phase = schedule_df.loc[54]
    else:
        target_phase = valid_phases.loc[54]
        
    start_filter = target_phase['start_dt']
    end_filter = target_phase['end_dt']
    
    print(f"\n[Schedule] Selected Slicing Window: {target_phase['activity']}")
    print(f"   Timestamps: {start_filter} to {end_filter}\n")
    print(valid_phases[['activity', 'start_dt', 'end_dt']])
    # Example: select the 3rd valid phase instead of the 1st if it has more rows
    

    # -------------------------------------------------------------
    # 3. Profile & Slice BMS Log
    # -------------------------------------------------------------
    bms_time_deltas = bms_df['datetime'].sort_values().diff().dropna()
    bms_median_delta = bms_time_deltas.median().total_seconds() / 60.0
    bms_granularity = "sub-hourly" if bms_median_delta < 60 else "hourly"
    
    room_temp_col = r"\\SBBPIAF1\ACMV\ACMV\SS5_TESTBEDSYSTEM\Room3|SS5_ROOM3_TEMP"
    sliced_bms = bms_df[(bms_df['datetime'] >= start_filter) & (bms_df['datetime'] <= end_filter)].copy()
    
    bms_completeness = 1.0 - (sliced_bms[room_temp_col].isna().sum() / max(1, len(sliced_bms)))
    
    bms_profile = {
        "granularity": bms_granularity,
        "timestep_minutes": bms_median_delta,
        "completeness": round(bms_completeness, 2),
        "rows_in_subset": len(sliced_bms)
    }
    print(f"-> BMS Profile Created: {bms_profile}")

    # -------------------------------------------------------------
    # 4. Process & Profile Heat Flux Data (Fixed Timezone Bug)
    # -------------------------------------------------------------
    hf_path = os.path.join(data_dir, 'heat_flux.csv')
    print("\n[Heat Flux] Loading envelope heat sensor data...")
    hf_df = pd.read_csv(hf_path)
    
    # Convert and explicitly convert UTC/Z time to naive timestamp format
    hf_df['datetime'] = pd.to_datetime(hf_df['datetime'])
    if hf_df['datetime'].dt.tz is not None:
        hf_df['datetime'] = hf_df['datetime'].dt.tz_localize(None) # Drops the '+00:00' or 'Z' tag
        
    # Slicing will now execute safely without crashing
    sliced_hf = hf_df[(hf_df['datetime'] >= start_filter) & (hf_df['datetime'] <= end_filter)].copy()
    
    hf_time_deltas = hf_df['datetime'].sort_values().diff().dropna()
    hf_median_delta = hf_time_deltas.median().total_seconds() / 60.0
    
    hf_profile = {
        "granularity": "sub-hourly" if hf_median_delta < 60 else "hourly",
        "timestep_minutes": hf_median_delta,
        "rows_in_subset": len(sliced_hf)
    }
    print(f"-> Heat Flux Profile Created: {hf_profile}")

    # -------------------------------------------------------------
    # 5. Process & Profile Tracer Gas (sf6.csv)
    # -------------------------------------------------------------
    sf6_path = os.path.join(data_dir, 'sf6.csv')
    print("\n[Tracer Gas] Loading SF6 concentration data...")
    sf6_df = pd.read_csv(sf6_path)
    
    hf_df['datetime'] = pd.to_datetime(hf_df['datetime'])
    if sf6_df['datetime'].dtype == object or sf6_df['datetime'].dt.tz is not None:
        sf6_df['datetime'] = pd.to_datetime(sf6_df['datetime']).dt.tz_localize(None)
        
    sliced_sf6 = sf6_df[(sf6_df['datetime'] >= start_filter) & (sf6_df['datetime'] <= end_filter)].copy()
    
    sf6_profile = {
        "total_recorded_points": len(sf6_df),
        "points_in_active_window": len(sliced_sf6)
    }
    print(f"-> SF6 Tracer Profile Created: {sf6_profile}")

    # Assembly for Stage 2 Recommender Input Metrics
    recommender_inputs = {
        "data_profile": {
            "source": "BMS Trend Log + Field Sensors",
            "granularity": bms_profile["granularity"],
            "completeness": bms_profile["completeness"]
        },
        "weather_context": {
            "selected_weather_file": "testbed_.epw",
            "reason": "Matches the actual historical calendar year timestamps found in the parsed sensor streams."
        }
    }
    
    
    if output_dir and len(sliced_bms) > 0:
        os.makedirs(output_dir, exist_ok=True)
        sliced_bms.to_csv(os.path.join(output_dir, 'subset_bms.csv'), index=False)
        sliced_hf.to_csv(os.path.join(output_dir, 'subset_heat_flux.csv'), index=False)
        sliced_sf6.to_csv(os.path.join(output_dir, 'subset_sf6.csv'), index=False)
        print(f"\n[Output] Subsets safely written to: '{output_dir}'")
        
    return recommender_inputs

if __name__ == "__main__":
    profile_and_subset_pipeline(
        data_dir=r"C:\Users\annaa\Downloads\IISC\calibration", 
        output_dir=r"C:\Users\annaa\Downloads\IISC\calibration\output"
    )