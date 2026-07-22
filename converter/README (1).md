# Interactive BIM Viewer and Adaptive IFC-to-IDF Converter

It combines an interactive IFC viewer with a Python-based converter that generates a baseline EnergyPlus 9.4 IDF model.

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

### EnergyPlus 9.4 checks

- Declares `Version, 9.4` in the generated IDF.
- Requires an EnergyPlus 9.4 IDD and checks the executable version.
- Uses fields supported by the EnergyPlus 9.4 schema.
- Checks reciprocal surface and subsurface references before serialization.
- Checks opening-parent conditions and containment.
- Checks that exported zones are closed and have correctly oriented floors and roofs.
- Requests EnergyPlus summary tables, hourly Ideal Loads outputs and an electricity meter.
- Attempts design-day and weather validation when EnergyPlus 9.4 and an EPW are configured.
- Separates EnergyPlus Severe/Fatal errors from research-quality warnings.

## Generated outputs

The Streamlit application provides two downloads:

- `baseline_v14.idf` - generated EnergyPlus 9.4 input file.
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
- Preliminary generation of EnergyPlus 9.4 baseline models.
- Study of geometry fallbacks in automatic BIM-to-BEM conversion.
- Comparison of conversion confidence across different IFC files.
- Identification of missing materials, openings, space boundaries and adjacencies.
- Creation of an IFC-to-IDF validation dataset for research.
- Batch conversion and report generation for multiple IFC files.

This application is a research prototype. It is not a replacement for manual checking by a building-energy modeller, and it should not be used for compliance or certified energy analysis without validation.

## Requirements

- Python 3
- EnergyPlus 9.4.0
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

## EnergyPlus 9.4 setup on Windows

Open PowerShell in the project folder and set the EnergyPlus paths:

```powershell
$env:ENERGYPLUS_IDD="C:\EnergyPlusV9-4-0\Energy+.idd"
$env:ENERGYPLUS_EXE="C:\EnergyPlusV9-4-0\energyplus.exe"
$env:ENERGYPLUS_EXPANDOBJECTS="C:\EnergyPlusV9-4-0\ExpandObjects.exe"
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

## Current test status

The Duplex Architecture IFC has been used as the main development case. The latest recorded manual EnergyPlus 9.4 weather run completed with one Warning and zero Severe or Fatal errors. This confirms that this particular generated IDF could complete the selected run; it does not establish general conversion or energy accuracy.

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



