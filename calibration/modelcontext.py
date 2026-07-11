import os
from geomeppy import IDF

def calculate_real_model_context(idf_path, idd_path, user_calibration_targets):
    """
    Parses an EnergyPlus IDF file using GeomEppy, inspects structural 
    complexity, and counts tunable parameters based on user targets.
    """
    if not os.path.exists(idd_path) or not os.path.exists(idf_path):
        raise FileNotFoundError("Verify local path routes for your IDD and IDF files.")
        
    # Initialize GeomEppy IDF
    IDF.setiddname(idd_path)
    geom_idf = IDF(idf_path)
    
    # Extract native structural metrics
    zones = geom_idf.idfobjects['ZONE']
    zone_count = len(zones)
    
    total_parameters = 0
    parameter_breakdown = {}
    
    # Continuous Parameter Diagnostics
    if "envelope" in user_calibration_targets:
        standard_materials = len(geom_idf.idfobjects['MATERIAL'])
        nomass_materials = len(geom_idf.idfobjects['MATERIAL:NOMASS'])
        envelope_params = standard_materials + nomass_materials
        total_parameters += envelope_params
        parameter_breakdown["envelope_layers"] = envelope_params
        
    if "infiltration" in user_calibration_targets:
        inf_objects = len(geom_idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'])
        total_parameters += inf_objects
        parameter_breakdown["infiltration_zones"] = inf_objects
        
    if "internal_gains" in user_calibration_targets:
        lights = len(geom_idf.idfobjects['LIGHTS'])
        equip = len(geom_idf.idfobjects['ELECTRICEQUIPMENT'])
        gains_params = lights + equip
        total_parameters += gains_params
        parameter_breakdown["internal_gain_objects"] = gains_params
        
    return {
        "tunable_parameters_count": total_parameters,
        "thermal_zones_count": zone_count,
        "breakdown": parameter_breakdown,
        "geom_idf_object": geom_idf  # Retained in memory for downstream testing
    }
user_targets = ["envelope", "infiltration"] 
current_model_context = calculate_real_model_context(
            idf_path=r"C:\Users\annaa\Downloads\IISC\calibration\level4_ACH_par.idf", 
            idd_path=r"C:\Users\annaa\Downloads\IISC\calibration\V9-4-0-Energy+.idd", 
            user_calibration_targets=user_targets
        )

print(current_model_context)