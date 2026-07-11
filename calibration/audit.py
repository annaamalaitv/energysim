import os
from eppy.modeleditor import IDF

BASE_DIR = r"C:\Users\annaa\Downloads\IISC\calibration"
CHOSEN_IDF = os.path.join(BASE_DIR, "level4_ACH_par.idf")
CHOSEN_IDD = os.path.join(BASE_DIR, "V9-4-0-Energy+.idd")

IDF.setiddname(CHOSEN_IDD)
idf = IDF(CHOSEN_IDF)

print("=== IDF STRUCTURAL AUDIT ===")
print(f"Total MATERIAL objects: {len(idf.idfobjects['MATERIAL'])}")
print(f"Total MATERIAL:NOMASS objects: {len(idf.idfobjects['MATERIAL:NOMASS'])}")
print(f"Total ZONEINFILTRATION:DESIGNFLOWRATE objects: {len(idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE'])}")

# Check Plenum1_Ceiling specifically BEFORE any modifications
print("\nChecking 'Plenum1_Ceiling' surface geometry in the original file:")
try:
    surface = idf.getobject('BUILDINGSURFACE:DETAILED', 'Plenum1_Ceiling')
    if surface:
        print(f"-> Found Surface: {surface.Name}")
        print(f"-> Construction Name: {surface.Construction_Name}")
        print(f"-> Number of Vertices field value: {surface.Number_of_Vertices}")
    else:
        print("-> 'Plenum1_Ceiling' was not found by name lookup!")
except Exception as e:
    print(f"-> Error inspecting surface: {e}")