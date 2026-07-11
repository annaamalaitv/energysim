from geomeppy import IDF
from pathlib import Path
import copy

# Copy your exact function setups to see their raw print statements
def altglo(idf_object, parameter_type: str, multiplier: float, save_directory: str, new_filename: str = "global_modified_model.idf"):
    modified_idf = copy.deepcopy(idf_object)
    param_choice = parameter_type.strip().lower()
    modified_count = 0

    if param_choice == 'people':
        people_objects = modified_idf.idfobjects['PEOPLE']
        print(f"👥 Total PEOPLE objects found in this file: {len(people_objects)}")
        
        for p in people_objects:
            method_value = str(getattr(p,"Number_of_People_Calculation_Method","")).strip().lower()
            print(f"-> Checking object '{p.Name}' | Method: '{method_value}'")
            try:
                if method_value == "people":
                    p.Number_of_People = float(p.Number_of_People) * multiplier
                    modified_count += 1
                elif method_value == "people/area":
                    p.People_per_Floor_Area = float(p.People_per_Floor_Area) * multiplier
                    modified_count += 1
                elif method_value == "area/person":
                    p.Floor_Area_per_Person = float(p.Floor_Area_per_Person) / multiplier
                    modified_count += 1
                else:
                    print(f"⚠️ Unknown Method value found: '{method_value}'")
            except Exception as e:
                print(f"❌ Failed processing object '{p.Name}': {e}")
    else:
        print("❌ Parameter choice is not 'people'")
        return None
        
    if modified_count == 0:
        print("⚠️ Warning: modified_count is ZERO! No objects were changed.")
        
    return modified_idf

# Initialise paths exactly like your main script
eplus_idd_path = r"C:\Users\annaa\Downloads\IISC\sim2\Energy+.idd"
IDF.setiddname(eplus_idd_path)
base_idf_object = IDF(r"C:\Users\annaa\Downloads\IISC\sim2\ASHRAE901_OfficeLarge_STD2019_NewDelhi.idf")

print("--- Running Test Modification Check ---")
test_run = altglo(base_idf_object, 'people', 1.5, "./test_debug_dir")
print(f"Return value of altglo: {test_run}")