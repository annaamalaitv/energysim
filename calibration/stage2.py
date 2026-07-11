import os
import pandas as pd
from eppy.modeleditor import IDF

def calculate_real_model_context(idf_path, idd_path, user_calibration_targets):
    """
    Parses a physical EnergyPlus IDF file using eppy, extracts structural 
    complexity metrics, and calculates the exact parameter count based on user intent.
    """
    print(f"[IDF Inspector] Initializing inspection on: {os.path.basename(idf_path)}")
    
    # 1. Initialize the eppy IDF parser structure
    if not os.path.exists(idd_path):
        raise FileNotFoundError(f"Missing IDD file at: {idd_path}")
    if not os.path.exists(idf_path):
        raise FileNotFoundError(f"Missing IDF file at: {idf_path}")
        
    IDF.setiddname(idd_path)
    idf_object = IDF(idf_path)
    
    # 2. Extract structural metrics directly from the building model [cite: 121, 126]
    zones = idf_object.idfobjects['ZONE']
    zone_count = len(zones)
    
    total_parameters = 0
    parameter_breakdown = {}
    
    # 3. Dynamically count tunable variables based on User Intent [cite: 121, 126]
    # Envelope Calibration Target
    if "envelope" in user_calibration_targets:
        standard_materials = len(idf_object.idfobjects['MATERIAL'])
        nomass_materials = len(idf_object.idfobjects['MATERIAL:NOMASS'])
        
        envelope_params = standard_materials + nomass_materials
        total_parameters += envelope_params
        parameter_breakdown["envelope_layers"] = envelope_params
        
    # Infiltration/Air Leakage Calibration Target
    if "infiltration" in user_calibration_targets:
        infiltration_objects = len(idf_object.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'])
        total_parameters += infiltration_objects
        parameter_breakdown["infiltration_zones"] = infiltration_objects
        
    # Internal Gains (Equipment & Lights) Calibration Target
    if "internal_gains" in user_calibration_targets:
        lights = len(idf_object.idfobjects['LIGHTS'])
        equip = len(idf_object.idfobjects['ELECTRICEQUIPMENT'])
        
        gains_params = lights + equip
        total_parameters += gains_params
        parameter_breakdown["internal_gain_objects"] = gains_params

    print(f"-> Inspection Complete: Found {zone_count} thermal zones.")
    print(f"-> Target Parameter Breakdown based on scope: {parameter_breakdown}")
    print(f"-> Total Continuous Tunable Parameters (x, y, z): {total_parameters}\n")
    
    model_context = {
        "tunable_parameters_count": total_parameters,
        "thermal_zones_count": zone_count,
        "breakdown": parameter_breakdown
    }
    
    return model_context

def execute_deterministic_recommender(stage1_inputs, model_context, compute_budget):
    """
    Applies deterministic mathematical scoring gates across data profiles,
    model geometries, and compute limits to select the optimal calibration method[cite: 122, 126].
    """
    print("=== Starting Stage 2: Deterministic Method Selection ===\n")
    
    # Extract profiles from Stage 1 metrics 
    granularity = stage1_inputs["data_profile"]["granularity"]
    num_params = model_context["tunable_parameters_count"]
    max_allowed_runs = compute_budget.get("max_simulation_runs", 200)
    
    # Initialize algorithm scoring matrix [cite: 130]
    methods_scores = {
        "Bayesian Optimization": 0.0,
        "Genetic Algorithm": 0.0,
        "ASHRAE GL14 Pattern-Based": 0.0
    }
    
    justifications = {
        "Bayesian Optimization": [],
        "Genetic Algorithm": [],
        "ASHRAE GL14 Pattern-Based": []
    }
    
    # -------------------------------------------------------------
    # Rule Gate A: Evaluate Compute Budgets [cite: 126, 130]
    # -------------------------------------------------------------
    if max_allowed_runs <= 250:
        methods_scores["Bayesian Optimization"] += 0.5
        justifications["Bayesian Optimization"].append(
            f"Tight compute constraint ({max_allowed_runs} max runs) favors BO's data-efficient global search over GA[cite: 130]."
        )
        methods_scores["Genetic Algorithm"] -= 0.6
        justifications["Genetic Algorithm"].append(
            f"Penalized: Genetic Algorithms typically need 500+ iterations, exceeding stated budget[cite: 130]."
        )
    else:
        methods_scores["Genetic Algorithm"] += 0.4
        justifications["Genetic Algorithm"].append(
            f"Generous run budget ({max_allowed_runs} max runs) allows GA to explore large global landscapes securely."
        )
        
    # -------------------------------------------------------------
    # Rule Gate B: Evaluate Parameter Dimensionality [cite: 126, 130]
    # -------------------------------------------------------------
    if num_params <= 15:
        methods_scores["Bayesian Optimization"] += 0.4
        justifications["Bayesian Optimization"].append(
            f"Low parameter count ({num_params} variables) sits perfectly in BO's sweet spot[cite: 130]."
        )
    elif num_params > 30:
        methods_scores["Genetic Algorithm"] += 0.5
        justifications["Genetic Algorithm"].append(
            f"High parameter count ({num_params} variables) requires heuristic recombination pathways."
        )
        methods_scores["Bayesian Optimization"] -= 0.3
        justifications["Bayesian Optimization"].append(
            f"BO global performance scaling degrades under higher variable counts (>30 variables)."
        )
        
    # -------------------------------------------------------------
    # Rule Gate C: Evaluate Data Granularity Profiles [cite: 126, 130]
    # -------------------------------------------------------------
    if granularity == "sub-hourly":
        methods_scores["Bayesian Optimization"] += 0.2
        methods_scores["Genetic Algorithm"] += 0.2
        justifications["Bayesian Optimization"].append("High-resolution sub-hourly sensor spacing provides deep diagnostic power for optimization algorithms[cite: 130].")
    elif granularity == "daily/monthly":
        methods_scores["ASHRAE GL14 Pattern-Based"] += 0.7
        justifications["ASHRAE GL14 Pattern-Based"].append("Coarse granularity limits diagnostic power, favoring post-hoc pattern tuning[cite: 130].")

    # Normalize scores between 0 and 1 for presentation clarity
    final_rankings = {}
    for method, raw_score in methods_scores.items():
        final_rankings[method] = round(max(0.0, min(1.0, 0.5 + raw_score)), 2)
        
    sorted_rankings = sorted(final_rankings.items(), key=lambda item: item[1], reverse=True)
    top_recommendation = sorted_rankings[0][0]
    
    # -------------------------------------------------------------
    # Package Output Visual Summary
    # -------------------------------------------------------------
    print(f"🥇 TOP PICK RECOMMENDATION: {top_recommendation}\n")
    print("--- Detailed Fit Analysis ---")
    for method, fit_score in sorted_rankings:
        print(f"\n▶ {method} (Fit Score: {fit_score})")
        if justifications[method]:
            for line in justifications[method]:
                print(f"  • {line}")
        else:
            print("  • Maintained neutral baseline suitability profile.")
            
    return {
        "recommended_method": top_recommendation,
        "rankings": sorted_rankings,
        "selected_weather": stage1_inputs["weather_context"]["selected_weather_file"]
    }

# --- Unified Execution Loop ---
if __name__ == "__main__":
    # 1. Base Directory Configurations
    BASE_DIR = r"C:\Users\annaa\Downloads\IISC\calibration"
    
    # Explicit File Select Vectors matching your directory image structure
    CHOSEN_IDF = os.path.join(BASE_DIR, "level4_ACH_par.idf") 
    CHOSEN_IDD = os.path.join(BASE_DIR, "V9-4-0-Energy+.idd")
    
    # 2. Simulated Stage 1 dictionary output (generated by your operational stage1.py script) 
    mock_stage1_output = {
        "data_profile": {
            "source": "BMS Trend Log + Field Sensors",
            "granularity": "sub-hourly",
            "completeness": 1.0
        },
        "weather_context": {
            "selected_weather_file": "testbed_.epw"
        }
    }
    
    # 3. User Calibration Intent & Compute Limits configuration 
    user_targets = ["envelope", "infiltration"] 
    user_compute_budget = {"max_simulation_runs": 200}
    
    # 4. Sequenced Execution Chain
    try:
        # Step A: Parse the physical IDF file structural geometry
        current_model_context = calculate_real_model_context(
            idf_path=CHOSEN_IDF, 
            idd_path=CHOSEN_IDD, 
            user_calibration_targets=user_targets
        )
        
        # Step B: Pass structural measurements straight into the decision tree matrix
        decision = execute_deterministic_recommender(
            stage1_inputs=mock_stage1_output,
            model_context=current_model_context,
            compute_budget=user_compute_budget
        )
        
    except Exception as e:
        print(f"\n⚠️ Execution halted: {e}")
        print("Please double check that your local folder structures contain the exact 'idffiles' and 'iddfiles' folders!")