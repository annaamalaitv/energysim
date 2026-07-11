from pathlib import Path
from geomeppy import IDF

# 1. Initialize with your v26.1 environment
IDF.setiddname("C:/EnergyPlusV26-1-0/Energy+.idd")
idf = IDF(r"C:\Users\annaa\Downloads\IISC\calibration\output\modified_level4_ACH_par.idf")

# ---- FIX 1: CEILING GEOMETRY ----
try:
    ceiling = idf.getobject('BUILDINGSURFACE:DETAILED', 'Plenum1_Ceiling')
    if ceiling:
        ceiling.Wind_Exposure = 'NoWind'
        ceiling.Sun_Exposure = 'NoSun'
        print("Successfully fixed Plenum1_Ceiling attributes.")
except Exception as e:
    print(f"Could not fix ceiling: {e}")


# ---- FIX 2: REBUILD CORRUPTED FAN ----
# Find the broken fan object
old_fans = idf.idfobjects['FAN:SYSTEMMODEL']
fan_to_replace = None

for fan in old_fans:
    if fan.Name == "Fan_AHU2":
        fan_to_replace = fan
        break

if fan_to_replace:
    # Remove the scrambled fan object out of the model
    idf.removeidfobject(fan_to_replace)
    print("Removed corrupted legacy Fan_AHU2 object.")
    
    # Re-build using exact schema-compliant field names for v26.1
    idf.newidfobject(
        'FAN:SYSTEMMODEL',
        Name='Fan_AHU2',
        Availability_Schedule_Name='Always_On',
        Air_Inlet_Node_Name='NODEOUTLET_AIR_SUPPLY22', 
        Air_Outlet_Node_Name='NODEOUTLET_AIR_SUPPLY2',
        Design_Maximum_Flow_Rate='autosize',  # Fixed for v26.1 schema
        Speed_Control_Method='Continuous',
        Electric_Power_Minimum_Flow_Rate_Fraction=0.2, 
        Design_Pressure_Rise=75.0,                    
        Motor_Efficiency=0.9,
        Motor_In_Airstream_Fraction=1.0,
        Design_Electric_Power_Sizing_Method='TotalEfficiencyAndPressure',
        Fan_Power_Modifier_Function_of_Speed_Fraction_Curve_Name='Fan_AHU2_Curve_EC'
    )
    print("Created fresh, schema-aligned Fan_AHU2 object.")

# 3. Save the repaired file
idf.saveas(r"C:\Users\annaa\Downloads\IISC\calibration\output\repairidf.idf")
print("Saved clean file as 'repaired_v26_model.idf'. Try running this in EnergyPlus!")