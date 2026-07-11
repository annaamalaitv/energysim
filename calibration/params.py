# 12 material/insulation properties followed by 8 infiltration scale values
test_params = [
    # Envelope (Slots 0 to 11) - e.g. structural conductivity/resistance targets
    0.5, 0.5, 0.15, 1.2, 0.04, 0.8, 0.5, 0.5, 0.15, 1.2, 0.04, 0.8,
    # Infiltration (Slots 12 to 19) - e.g. airflow design coefficients
    0.005, 0.005, 0.01, 0.002, 0.005, 0.005, 0.01, 0.002
]

from geomeppy import IDF
import os

def apply_parameters_and_save(params, idf_object, output_idf_path):
    """
    Applies optimization parameters directly using GeomEppy object methods,
    avoiding raw string regex hacks.
    """
    # ... [Parameter Mapping logic for Materials and Infiltration] ...
    
    # Clean Geometry Modification instead of regex replacements:
    try:
        surface = idf_object.getobject('BUILDINGSURFACE:DETAILED', 'Plenum1_Ceiling')
        if surface:
            # Safely force surface configuration directly via GeomEppy API
            surface.Number_of_Vertices = 4
            surface.Sun_Exposure = 'NoSun'
            surface.Wind_Exposure = 'NoSun'
    except Exception as e:
        print(f"Geometry adjustments bypassed: {e}")
        
    idf_object.saveas(output_idf_path)

IDF.setiddname(r"C:\Users\annaa\Downloads\IISC\calibration\V9-4-0-Energy+.idd")
actual_geom_idf_object = IDF(r"C:\Users\annaa\Downloads\IISC\calibration\level4_ACH_par.idf")

apply_parameters_and_save(test_params, actual_geom_idf_object, r"C:\Users\annaa\Downloads\IISC\calibration\output\modified_level4_ACH_par.idf")