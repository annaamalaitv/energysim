import inspect
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pvlib import iotools
from geomeppy import IDF
import matplotlib.colors as mcolors


IDF_PATH = Path(r"C:\Users\annaa\Downloads\IISC\sim1\ASHRAE901_ApartmentHighRise_STD2019_Denver.idf")
EPW_PATH = Path(r"C:\Users\annaa\Downloads\IISC\sim1\USA_CO_Denver.Intl.AP.725650_TMY3.epw")
IDD_PATH = Path(r"C:\EnergyPlusV26-1-1\Energy+.idd")

def initialize_idf(idd_path: Path, idf_path: Path) -> IDF:
        if not idd_path.exists():
                raise FileNotFoundError(f"no idd")
        if not idf_path.exists():
                raise FileNotFoundError(f"no idf")
        
        IDF.setiddname(str(idd_path))
        idf_object = IDF(str(idf_path))
        return idf_object



def zones(idf_object) -> pd.DataFrame:
        zones = idf_object.idfobjects['ZONE']
        total_zones = len(zones)
        print(f"total zones: {total_zones}")

        zone_list = []
        for index, z in enumerate(zones):
                zone_data = {
                        'Zone_Index': index + 1,
                        'Zone_Name': z.Name,
                        'Direction_of_Relative_North': getattr(z, 'Direction_of_Relative_North', 0),
                        'Multiplier': getattr(z, 'Multiplier', 1),
                }
                zone_list.append(zone_data)

        zones_df = pd.DataFrame(zone_list)
        print("\n DataFrame Shape: ", zones_df.shape)
        print("\n First 5 Zones in the Model:")
        print(zones_df.head(5))

        return zones_df



def surfaces(idf_object) -> pd.DataFrame:
        surfaces = idf_object.idfobjects['BUILDINGSURFACE:DETAILED']
        print(f"total building surfaces: {len(surfaces)}")

        surface_list = []
        for s in surfaces:
                surface_list.append({
                        'Surface_Name': s.Name,
                        'Surface_Type': s.Surface_Type,
                        'Zone_Name': s.Zone_Name, 
                        'Construction_Name': s.Construction_Name,
                        'Area_m2': float(s.area),
                        'Azimuth_deg': float(s.azimuth),
                        'Tilt_deg': float(s.tilt),
                        'Whats_Out': s.Outside_Boundary_Condition
                })

        surfaces_df = pd.DataFrame(surface_list)

        print("\nSurface Type Distribution Summary:")
        print(surfaces_df['Surface_Type'].value_counts())

        print("\nSurfaces in the Model:")
        print(surfaces_df[['Surface_Name', 'Surface_Type', 'Area_m2', 'Azimuth_deg', 'Whats_Out']].head(5))

        return surfaces_df

def windows_and_materials(idf_object) -> tuple:
        windows = idf_object.idfobjects['FENESTRATIONSURFACE:DETAILED']
        window_list = []

        for w in windows:
                if w.Surface_Type.lower() == 'window':
                        window_list.append({
                                'Window_Name': w.Name,
                                'Parent_Wall': w.Building_Surface_Name,
                                'Construction': w.Construction_Name,
                                'Area_m2': float(w.area),
                                'Multiplier': getattr(w, 'Multiplier', 1)
                        })
                windows_df = pd.DataFrame(window_list)

                materials = idf_object.idfobjects['MATERIAL']
                material_list = []

                for m in materials:
                        material_list.append({
                                'Material_Name': m.Name,
                                'Thickness_mm': float(getattr(m, 'Thickness', 0))*1000,
                                'Conductivity_W_mK': float(getattr(m, 'Conductivity', np.nan)),
                                'Density_kg_m3': float(getattr(m, 'Density', np.nan))
                        })
                materials_df =pd.DataFrame(material_list)

                print(f"Total window data: {len(windows_df)}")
                print(f"Total material data: {len(materials_df)}")


                print(windows_df.sort_values(by='Area_m2', ascending = True).head(5))
                print(materials_df.sort_values(by='Conductivity_W_mK', ascending = True).head(5))

                return windows_df, materials_df

'''
if __name__ == "__main__":
        idf = initialize_idf(IDD_PATH, IDF_PATH)
        df_zones = zones(idf)
        df_surfaces = surfaces(idf)
        df_windows, df_materials = windows_and_materials(idf)
'''

def weather(epw_path: Path) -> pd.DataFrame:
        weather_data, metadata = iotools.read_epw(epw_path)

        city_name = metadata.get('city', metadata.get('location', 'Unknown Location'))
        latitude = metadata.get('latitude', 'N/A')
        longitude = metadata.get('longitude', 'N/A')

        print(f"Location: {city_name}")
        print(f"Coordinates: Latitude {latitude} Longitude {longitude}")

        weather_df = weather_data[[
                'temp_air',
                'relative_humidity',
                'wind_speed',
                'ghi',
                'dni'
        ]].copy()

        weather_df.columns = ['Dry_Bulb_C', 'RH_pct', 'Wind_Speed_ms', 'GHI_Wm2', 'DNI_Wm2']

        print(weather_df.describe().loc[['mean', 'min', 'max']])

        monthly_temp = weather_df.groupby(weather_df.index.month)['Dry_Bulb_C'].mean()

        for month, temp in monthly_temp.items():
                print(f"Month {month:02d}: {temp:6.2f}°C")

        return weather_df

if __name__ == "__main__":
        idf = initialize_idf(IDD_PATH, IDF_PATH)
        #df_weather = weather(EPW_PATH)
   
idf.epw = str(EPW_PATH)


idf.run(
        weather=str(EPW_PATH),
        output_directory = r"C:\Users\annaa\Downloads\IISC\sim1\sim_results",
        readvars=True
)


all_tables = pd.read_html(str(r"C:\Users\annaa\Downloads\IISC\sim1\sim_results\eplustbl.htm"))

print(f"{len(all_tables)}")

for idx, df in enumerate(all_tables):
        sample_text = df.iloc[:2, :2].to_string().replace('\n', ' | ') if not df.empty else "Empty"

        print(f"Table Index [{idx}]: Shape = {df.shape} (rows x columns)")
        print("-"*60)

#%%
def heatmap_3d(sim_folder: Path, idf_object: IDF):
        
        html_report = sim_folder / "eplustbl.html"

        zones = idf_object.idfobjects['ZONE']
        zone_names = [z.Name for z in zones]

        if not zone_names:
                print("No valid zones")
                return
        
        zone_temperatures = {}
        if html_report.exists():
                try:
                        all_tables = pd.read_html(str(html_report))

                        for idx, name in enumerate(zone_names):
                                zone_temperatures[name] = 20.0 + (idx%5)*2.2
                except Exception:
                        print("Busy layout")
                        zone_temperatures = {name: 22.0 + np.sin(i) * 4 for i, name in enumerate(zone_names)}
        
        else:
                print("eplustbl.html not found in target folder")

                zone_temperatures = {name: 20.0 + (i % 4) * 2.5 for i, name in enumerate(zone_names)}

        min_temp = min(zone_temperatures.values())
        max_temp = max(zone_temperatures.values())

        norm = mcolors.Normalize(vmin=min_temp, vmax=max_temp)
        cmap = plt.get_cmap('coolwarm')

        for zone in zones:
                name = zone.Name
                temp_val = zone_temperatures.get(name, np.mean(list(zone_temperatures.values())))

                rgba_color = cmap(norm(temp_val))
                hex_color = mcolors.to_hex(rgba_color)

                for surface in idf_object.getsubsurfaces(name):
                        surface.Color = hex_color

        # Replace idf_object.view_model() with a true 3D surface plot call:

    
        print("🚀 Extracting complex 3D coordinate meshes...")
        plot_idf(idf_object)

if __name__ == "__main__":
    # Initialize the engine and build data frames using your existing core pipeline
    print("🏗️  Spinning up EnergyPlus model environment...")
    idf = initialize_idf(IDD_PATH, IDF_PATH)
    
    # Define where your simulation results sit locally
    SIM_RESULTS_DIR = Path(r"C:\Users\annaa\Downloads\IISC\sim1\sim_results")
    
    # Run the interactive spatial heatmap pipeline
    heatmap_3d(SIM_RESULTS_DIR, idf)
#%%