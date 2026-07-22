# Interactive BIM Viewer and Adaptive IFC-to-IDF Converter

This project was developed during the IASc-INSA-NASI Summer Research Fellowship 2026 at the Indian Institute of Science (IISc), Bengaluru. It combines an interactive IFC viewer with a Python-based converter that generates a baseline EnergyPlus 26.1 IDF model.

The main aim is safe and transparent conversion. If a part of the IFC model cannot be converted reliably, the program skips it or uses a clearly reported fallback instead of silently creating invalid EnergyPlus geometry.

## Main capabilities

### IFC visualization

- Upload and read an IFC building model.
- Display the complete model in an interactive Plotly 3D viewer.
- Filter the model by building storey and IFC element type.
- View project, storey, space and mesh counts.
- Find individual IFC elements using a selector.
- Highlight the selected element in yellow.
- Display element name, type, storey, material and GlobalId.
- Display generated IDF zone area, volume, surface count, geometry source and confidence.

### IFC-to-IDF conversion

- Converts IFC length units and placements into metres and world coordinates.
- Creates EnergyPlus thermal zones from `IfcSpace` objects.
- Uses the following three-level geometry hierarchy:

  1. A complete and valid `IfcRelSpaceBoundary` shell.
  2. A validated watertight `IfcSpace` mesh.
  3. A closed bounding-box fallback, reported as low confidence.

- Rejects incomplete boundary sets instead of exporting open zones.
- Cleans polygons, rejects degenerate surfaces and divides supported concave polygons.
- Checks zone-shell closure and floor, wall and roof orientation.
- Assigns floor, wall and roof surface types and boundary conditions.
- Reads IFC material layers when available and reports inferred properties when data are missing.
- Creates reciprocal interzone surface references only for reliable full-surface matches.
- Rejects partial adjacencies that require surface subdivision.
- Allows exterior openings only on Outdoors surfaces.
- Checks that every exported window or door is contained inside its parent surface.
- Creates matching reciprocal openings for valid interzone parents.
- Skips unsafe windows and doors and records the reason in the report.
- Generates baseline occupancy, lighting, equipment and Ideal Loads HVAC objects.

### EnergyPlus 26.1 checks

- Declares `Version, 26.1` in the generated IDF.
- Requires an EnergyPlus 26.1 IDD and checks for the exact 26.1.0 executable.
- Uses fields supported by the EnergyPlus 26.1 schema.
- Checks reciprocal surface and subsurface references before serialization.
- Checks opening-parent conditions and containment.
- Checks that exported zones are closed and have correctly oriented floors and roofs.
- Requests EnergyPlus summary tables, hourly Ideal Loads outputs and an electricity meter.
- Attempts design-day and weather validation when EnergyPlus 26.1 and an EPW are configured.
- Separates EnergyPlus Severe/Fatal errors from research-quality warnings.

## Generated outputs

The Streamlit application provides two downloads:

- `baseline_v14.idf` - generated EnergyPlus 26.1 input file.
- `report_v14.json` - detailed conversion and validation report.

The JSON report records:

- Generated and skipped zones.
- Geometry source and confidence for each zone.
- IFC unit scale and site information.
- Recovered and rejected space boundaries.
- Matched and unresolved adjacencies.
- Converted and skipped windows and doors.
- Material assumptions and geometry warnings.
- Pre-serialization geometry checks.
- EnergyPlus version, preprocessing and simulation results.
- Weather-file comparison with the IFC location.
- Research-quality gate status and reasons for failure.

## Possible use cases

- Visual inspection of IFC models before energy modelling.
- Preliminary generation of EnergyPlus 26.1 baseline models.
- Study of geometry fallbacks in automatic BIM-to-BEM conversion.
- Comparison of conversion confidence across different IFC files.
- Identification of missing materials, openings, space boundaries and adjacencies.
- Creation of an IFC-to-IDF validation dataset for research.
- Batch conversion and report generation for multiple IFC files.

This application is a research prototype. It is not a replacement for manual checking by a building-energy modeller, and it should not be used for compliance or certified energy analysis without validation.

## Requirements

- Python 3
- EnergyPlus 26.1.0
- An IFC file containing usable `IfcSpace` objects
- A suitable EPW file for a weather simulation

Python packages:

```text
streamlit
plotly
numpy
ifcopenshell
shapely
eppy
```

Install the Python packages using:

```powershell
pip install streamlit plotly numpy ifcopenshell shapely eppy
```

## EnergyPlus 26.1 setup on Windows

Open PowerShell in the project folder and set the EnergyPlus paths:

```powershell
$env:ENERGYPLUS_IDD="C:\EnergyPlusV26-1-0\Energy+.idd"
$env:ENERGYPLUS_EXE="C:\EnergyPlusV26-1-0\energyplus.exe"
$env:ENERGYPLUS_EXPANDOBJECTS="C:\EnergyPlusV26-1-0\ExpandObjects.exe"
```

If `ExpandObjects.exe` is inside the `PreProcess` folder, use that complete path instead.

To allow the application to compare and run a weather file automatically, optionally set:

```powershell
$env:ENERGYPLUS_EPW="C:\path\to\weather_file.epw"
```

The EPW should represent the IFC building location. A successful simulation with an unrelated EPW does not prove that the energy results are accurate.

## Run the application

```powershell
streamlit run .\final_visualization_and_converter.py
```

Streamlit will display a local URL, normally `http://localhost:8501`.

## Batch or command-line conversion

The same file can be used without the Streamlit interface:

```powershell
python .\final_visualization_and_converter.py `
  --ifc .\model.ifc `
  --idf-output .\baseline.idf `
  --report-output .\conversion_report.json
```

## Function-based runner

The repository also includes `run_converter.py`. This file keeps all input and output files as variables at the beginning of the script and defines the conversion steps as separate functions.

Edit these variables before running it:

- `INPUT_IFC_FILE`
- `OUTPUT_IDF_FILE`
- `OUTPUT_REPORT_FILE`
- `ENERGYPLUS_FOLDER`
- `WEATHER_FILE`

The runner performs the following function calls in order:

1. `validate_input_files()`
2. `configure_energyplus_environment()`
3. `convert_assigned_ifc_file()`
4. `print_conversion_summary()`

Run it using:

```powershell
python .\run_converter.py
```

The Streamlit interface and the function-based runner use the same converter backend.

## Current test status

The Duplex Architecture IFC has been used as the main development case. On 22 July 2026, the generated IDF completed an EnergyPlus 26.1.0 weather simulation using the Chicago Midway TMY3 EPW. EnergyPlus reported one Warning, zero Severe errors and zero Fatal errors, and completed the run in 6.76 seconds. The Warning stated that the EPW location would be used instead of the IDF location because of small coordinate differences and a 186 m elevation difference. This result confirms numerical executability for this generated IDF; it does not establish general conversion or energy accuracy.

The current research evaluation is still incomplete. Before making broader claims, the converter should be tested on at least three IFC models, including the FZK Haus and an ArchiCAD building model. At least one generated model should also be compared with a manually prepared reference IDF using floor area, zone volume, exterior surface area, window-to-wall ratio and annual energy error.

## Known limitations

- Some IFC models have incomplete or missing space boundaries.
- Bounding-box zones lose the original room shape and are low confidence.
- Partial surface overlaps are rejected because reliable subdivision is not yet implemented.
- Unsupported planar topology may be dropped.
- Some unresolved walls may be inferred as Outdoors or kept Adiabatic.
- Doors and windows are skipped when no safe parent surface can be found.
- Material thickness and thermal properties may be inferred when IFC information is incomplete.
- Design-day conditions and ground temperatures are generic fallbacks.
- Schedules and internal loads are simplified baseline assumptions.
- Infiltration and detailed ventilation systems are not modelled.
- The converter requires `IfcSpace`; reconstruction of rooms directly from physical walls and slabs is not implemented.
- A successful EnergyPlus run proves numerical executability, not agreement with a manually prepared energy model.

## Recommended validation table

For each IFC test case, record:

| Item | Value |
|---|---|
| IFC source and schema |  |
| Number of spaces and generated zones |  |
| High-, medium- and low-confidence zones |  |
| Geometry fallback used |  |
| Base surfaces and openings |  |
| Skipped openings |  |
| Resolved and unresolved adjacencies |  |
| Conversion time |  |
| EnergyPlus Severe and Fatal errors |  |
| Annual electricity, heating and cooling |  |

## Research scope

The intended contribution is an uncertainty-aware and safety-focused IFC-to-IDF workflow. The program reports assumptions, rejects unsafe geometry and validates the generated object-reference graph. It is not claimed to convert every IFC model perfectly or to produce universally accurate annual energy results.

## Author

**Anurag Bashal**  
B.Tech., Civil Engineering, National Institute of Technology Agartala  
Summer Research Fellow, Indian Institute of Science, Bengaluru  

**Guide:** Dr. Pandarasamy Arjunan, Indian Institute of Science
