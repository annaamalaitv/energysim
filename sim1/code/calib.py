import numpy as np
import pandas as pd


def calculate_rmse(target_csv_path, sim_csv_path):
    # Load both CSVs
    df_target = pd.read_csv(target_csv_path)
    df_sim = pd.read_csv(sim_csv_path)
    
    df_target.columns = df_target.columns.str.strip()
    df_sim.columns = df_sim.columns.str.strip()

    # Extract the energy column (e.g., 'Facility Total Electricity Demand Rate [W]')
    # Ensure timestamps align perfectly
    y_true = df_target['Whole Building:Facility Total Electricity Demand Rate [W](Hourly)'].values
    y_pred = df_sim['Whole Building:Facility Total Electricity Demand Rate [W](Hourly)'].values
    
    # Calculate RMSE
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    return rmse

a = calculate_rmse(r"C:\Users\\annaa\Downloads\\normal\eplusout.csv", 
                   r"C:\Users\\annaa\Downloads\\abnormal\eplusout.csv")
print(a)

import os
from eppy.modeleditor import IDF

ep_folder = r"C:\EnergyPlusV26-1-1" 
idd_file = os.path.join(ep_folder, "Energy+.idd")
IDF.setiddname(idd_file)

base_idf_path = r"C:\Users\annaa\Downloads\IISC\sim2\ASHRAE901_OfficeLarge_STD2019_NewDelhi.idf"
idf = IDF(base_idf_path)

# Grab the first people object
people_object = idf.idfobjects['PEOPLE'][0]

print("\n--- Available Field Names in your PEOPLE Object ---")
print(people_object)
print("---------------------------------------------------")
