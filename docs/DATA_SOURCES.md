# EmberGuide Data Sources & Attribution

Complete documentation of all data sources used in EmberGuide, with licensing requirements, attribution text, and terms of use.

---

## Overview

EmberGuide uses **public, freely available datasets** for wildfire nowcasting. This document ensures:
- **Proper attribution** to data providers
- **Compliance** with licensing requirements
- **Transparency** about data provenance and limitations

**All data sources must be credited** in:
- UI footer (every page)
- API responses (in `attribution` field)
- README and documentation
- Publications using EmberGuide

---

## Primary Data Sources

### 1. FIRMS (Fire Information for Resource Management System)

#### Provider
**NASA LANCE** (Land, Atmosphere Near real-time Capability for EOS)

#### Source
- **MODIS** (Moderate Resolution Imaging Spectroradiometer) on Terra and Aqua satellites
- **VIIRS** (Visible Infrared Imaging Radiometer Suite) on Suomi-NPP and NOAA-20 satellites

#### Access
- **Website**: https://firms.modaps.eosdis.nasa.gov/
- **API**: https://firms.modaps.eosdis.nasa.gov/api/
- **Registration**: Free account required (https://firms.modaps.eosdis.nasa.gov/api/data_availability/)

#### License
**Public Domain** (U.S. government data)

NASA data is generally available without restriction. However, **proper attribution is required**.

#### Attribution (Required)

**Short form** (UI footer):
> FIRMS (NASA)

**Full citation** (publications):
> NASA. (2024). MODIS/VIIRS Active Fire Detections from the Fire Information for Resource Management System (FIRMS). NASA LANCE. Available: https://firms.modaps.eosdis.nasa.gov/

**BibTeX**:
```bibtex
@misc{nasa_firms_2024,
  author = {{NASA LANCE}},
  title = {MODIS/VIIRS Active Fire Detections},
  howpublished = {Fire Information for Resource Management System (FIRMS)},
  year = {2024},
  url = {https://firms.modaps.eosdis.nasa.gov/}
}
```

#### Terms of Use

From [NASA Data Use Policy](https://earthdata.nasa.gov/learn/use-data/data-use-policy):
- Free and open access
- No redistribution restrictions
- Attribution appreciated
- Not for commercial sale of raw data (but derived products like EmberGuide are allowed)

#### Data Specifications

- **Temporal resolution**: Near real-time (~3 hours latency)
- **Spatial resolution**: ~375 m (VIIRS), ~1 km (MODIS)
- **Coverage**: Global
- **Format**: CSV, JSON, Shapefile, KML
- **Update frequency**: Multiple times daily

#### EmberGuide Usage

- **Hotspot detections** → fire seeds for nowcast initialization
- **Confidence filtering** → used by denoiser module
- **Clustering** → group nearby detections into fire objects

---

### 2. ERA5 (ECMWF Reanalysis v5)

#### Provider

**Copernicus Climate Change Service (C3S)** / **European Centre for Medium-Range Weather Forecasts (ECMWF)**

#### Source

Global atmospheric reanalysis combining:
- Weather observations (satellites, stations, balloons)
- Numerical weather prediction model
- Data assimilation

#### Access

- **Website**: https://cds.climate.copernicus.eu/
- **API**: https://cds.climate.copernicus.eu/api/v2
- **Registration**: Free account required (https://cds.climate.copernicus.eu/user/register)

#### License

**Copernicus License** (free for all uses with attribution)

Full terms: https://cds.climate.copernicus.eu/api/v2#!/terms/

**Summary**:
- Free for research and commercial use
- Redistribution allowed (with attribution)
- No warranty

#### Attribution (Required)

**Short form** (UI footer):
> ERA5 (Copernicus/ECMWF)

**Full citation** (publications):
> Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz‐Sabater, J., et al. (2020). The ERA5 global reanalysis. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999–2049. https://doi.org/10.1002/qj.3803

**BibTeX**:
```bibtex
@article{hersbach2020era5,
  title={The ERA5 global reanalysis},
  author={Hersbach, Hans and Bell, Bill and Berrisford, Paul and Hirahara, Shoji and Hor{\'a}nyi, Andr{\'a}s and Mu{\~n}oz-Sabater, Joaqu{\'\i}n and Nicolas, Julien and Peubey, Carole and Radu, Raluca and Schepers, Dinand and others},
  journal={Quarterly Journal of the Royal Meteorological Society},
  volume={146},
  number={730},
  pages={1999--2049},
  year={2020},
  publisher={Wiley Online Library},
  doi={10.1002/qj.3803}
}
```

**Acknowledgment text** (from Copernicus):
> Contains modified Copernicus Climate Change Service information [year]. Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.

#### Terms of Use

Full license: https://cds.climate.copernicus.eu/api/v2#!/terms/

**Key points**:
- Free access for all users
- Redistribution allowed (with attribution)
- No sublicensing of raw data (but derived products like EmberGuide are allowed)
- Must acknowledge Copernicus and cite Hersbach et al. (2020)

#### Data Specifications

- **Temporal resolution**: Hourly
- **Spatial resolution**: 0.25° (~25 km)
- **Coverage**: Global
- **Latency**: ~5 days (final), ~3 hours (preliminary)
- **Format**: GRIB, NetCDF

#### Variables Used

- `u10`, `v10`: 10-m wind components (m/s)
- `t2m`: 2-m temperature (K)
- `d2m`: 2-m dew point temperature (K)
- `blh`: Boundary layer height (m) *(optional)*

#### EmberGuide Usage

- **Wind** → primary driver of fire spread direction
- **Temperature + Dew Point** → compute Relative Humidity (fuel dryness proxy)
- **Boundary layer height** → optional context for smoke dispersion

---

### 3. SRTM (Shuttle Radar Topography Mission)

#### Provider

**NASA** / **USGS** (United States Geological Survey)

#### Source

Space Shuttle Endeavour radar mission (February 2000)

#### Access

- **OpenTopography**: https://portal.opentopography.org/
- **USGS EarthExplorer**: https://earthexplorer.usgs.gov/
- **Direct download**: https://srtm.csi.cgiar.org/

#### License

**Public Domain** (U.S. government data)

No restrictions on use, redistribution, or modification.

#### Attribution (Required)

**Short form** (UI footer):
> SRTM (NASA/USGS)

**Full citation** (publications):
> NASA JPL (2013). NASA Shuttle Radar Topography Mission Global 3 arc second [Data set]. NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL3.003

**BibTeX**:
```bibtex
@misc{nasa_srtm_2013,
  author = {{NASA JPL}},
  title = {NASA Shuttle Radar Topography Mission Global 3 arc second},
  year = {2013},
  publisher = {NASA EOSDIS Land Processes DAAC},
  doi = {10.5067/MEaSUREs/SRTM/SRTMGL3.003},
  url = {https://lpdaac.usgs.gov/products/srtmgl3v003/}
}
```

#### Terms of Use

From [USGS Data Policy](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits):
- Public domain (no copyright)
- Free to use and redistribute
- Attribution appreciated but not legally required (we do it anyway)

#### Data Specifications

- **Spatial resolution**: 3 arc-second (~90 m) globally; 1 arc-second (~30 m) for U.S.
- **Coverage**: 60°N to 56°S (no polar regions)
- **Vertical accuracy**: ~16 m (absolute), ~10 m (relative)
- **Format**: GeoTIFF

#### Derived Products

EmberGuide computes:
- **Slope** (degrees): Rate of elevation change
- **Aspect** (degrees): Compass direction of slope (0° = north)

#### EmberGuide Usage

- **Slope** → modulates spread rate (upslope faster, downslope slower)
- **Aspect** → combined with solar radiation for fuel dryness (future enhancement)

---

## Optional Data Sources

### 4. MODIS Burned Area (MCD64A1)

#### Provider
NASA LPDAAC (Land Processes Distributed Active Archive Center)

#### Use in EmberGuide
- **Training labels** for ML denoiser and calibrator
- **Evaluation ground truth** for nowcast accuracy

#### Access
https://lpdaac.usgs.gov/products/mcd64a1v006/

#### License
Public Domain (NASA data)

#### Attribution
> NASA. (2021). MODIS/Terra+Aqua Burned Area Monthly L3 Global 500m SIN Grid V006. NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MODIS/MCD64A1.006

#### Terms
Same as FIRMS (public domain, attribution appreciated)

---

### 5. MODIS Land Cover (MCD12Q1)

#### Provider
NASA LPDAAC

#### Use in EmberGuide
- **Denoiser feature**: Identify non-burnable land cover (water, urban, barren)
- **Fuel type proxy** (future enhancement)

#### Access
https://lpdaac.usgs.gov/products/mcd12q1v006/

#### License
Public Domain (NASA data)

#### Attribution
> NASA. (2019). MODIS/Terra+Aqua Land Cover Type Yearly L3 Global 500m SIN Grid V006. NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MODIS/MCD12Q1.006

---

### 6. Weather Stations (RAWS, ASOS)

#### Provider
- **RAWS**: Remote Automated Weather Stations (U.S. Forest Service, BLM)
- **ASOS**: Automated Surface Observing System (NOAA)

#### Use in EmberGuide
- **Ground truth** for micro-downscaling ERA5 wind/RH (optional ML module)
- **Validation** of reanalysis accuracy

#### Access
- RAWS: https://raws.dri.edu/
- ASOS: https://mesonet.agron.iastate.edu/ASOS/

#### License
Public Domain (U.S. government data)

#### Attribution
> Remote Automated Weather Stations (RAWS) data courtesy of USDA Forest Service and BLM.

---

## UI Footer Attribution

### Recommended Text

Place in footer of every UI page:

> **Data Sources**: [FIRMS](https://firms.modaps.eosdis.nasa.gov/) (NASA) · [ERA5](https://cds.climate.copernicus.eu/) (Copernicus/ECMWF) · [SRTM](https://www2.jpl.nasa.gov/srtm/) (NASA/USGS)  
> Contains modified Copernicus Climate Change Service information 2024.  
> ⚠️ Research preview — not for life-safety decisions.

### Implementation (Streamlit)

```python
# ui/components/attribution.py
import streamlit as st

def render_attribution():
    st.markdown("---")
    st.caption("""
    **Data Sources**: 
    [FIRMS](https://firms.modaps.eosdis.nasa.gov/) (NASA) · 
    [ERA5](https://cds.climate.copernicus.eu/) (Copernicus/ECMWF) · 
    [SRTM](https://www2.jpl.nasa.gov/srtm/) (NASA/USGS)
    
    Contains modified Copernicus Climate Change Service information 2024.  
    ⚠️ Research preview — not for life-safety decisions.
    
    [About](./About) · [GitHub](https://github.com/yourusername/ember-guide)
    """)
```

---

## API Response Attribution

### Include in Every Response

```json
{
  "fire_id": "fire_001",
  "data": { ... },
  "attribution": [
    "FIRMS (NASA): Active fire detections",
    "ERA5 (Copernicus/ECMWF): Weather reanalysis",
    "SRTM (NASA/USGS): Terrain data"
  ],
  "disclaimer": "Research preview — not for life-safety decisions."
}
```

---

## Publication Guidelines

If you use EmberGuide in a publication, **you must cite**:

### EmberGuide Software
```bibtex
@software{emberguide2025,
  title={EmberGuide: Open Wildfire Nowcasts},
  author={Your Name},
  year={2025},
  url={https://github.com/yourusername/ember-guide},
  version={1.0.0}
}
```

### FIRMS Data
NASA LANCE. (2024). MODIS/VIIRS Active Fire Detections. https://firms.modaps.eosdis.nasa.gov/

### ERA5 Data
Hersbach et al. (2020). The ERA5 global reanalysis. QJRMS, 146(730), 1999-2049. https://doi.org/10.1002/qj.3803

### SRTM Data
NASA JPL (2013). SRTM Global 3 arc second. https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL3.003

### Acknowledgment Text (Recommended)

> This work uses satellite fire detections from NASA FIRMS, weather data from Copernicus ERA5 (Hersbach et al., 2020), and terrain data from NASA SRTM. We acknowledge the Copernicus Climate Change Service and ECMWF for providing ERA5 reanalysis data. Neither the European Commission nor ECMWF is responsible for any use made of this information.

---

## Compliance Checklist

Before deploying EmberGuide, ensure:

- [ ] UI footer includes FIRMS, ERA5, SRTM attribution
- [ ] API responses include `attribution` field
- [ ] README.md credits all data sources
- [ ] Copernicus acknowledgment text included (for ERA5)
- [ ] Disclaimer ("Research preview — not for life-safety decisions") visible
- [ ] API keys stored in `.env` (not committed)
- [ ] No redistribution of raw FIRMS/ERA5 data without attribution
- [ ] Publications cite Hersbach et al. (2020) and NASA FIRMS
- [ ] Model cards document data sources and splits

---

## Data Provider Contacts

### FIRMS Support
- **Email**: support@earthdata.nasa.gov
- **Forum**: https://forum.earthdata.nasa.gov/

### Copernicus User Support
- **Email**: copernicus-support@ecmwf.int
- **Documentation**: https://confluence.ecmwf.int/display/CKB/

### USGS Customer Services
- **Email**: custserv@usgs.gov
- **Phone**: 1-888-ASK-USGS (1-888-275-8747)

---

## Changes to Data Policies

**Last reviewed**: October 2024

Data provider policies may change. Check periodically:
- FIRMS: https://earthdata.nasa.gov/learn/use-data/data-use-policy
- ERA5: https://cds.climate.copernicus.eu/api/v2#!/terms/
- USGS: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits

**If policies change**, update:
- This document
- UI footer
- API attribution
- README.md

---

## Questions?

For questions about data licensing or attribution:
1. Check provider's official documentation (links above)
2. Contact provider support
3. Open an issue on GitHub (for EmberGuide-specific questions)

---

## References

- [NASA Data Use Policy](https://earthdata.nasa.gov/learn/use-data/data-use-policy)
- [Copernicus License](https://cds.climate.copernicus.eu/api/v2#!/terms/)
- [USGS Copyright Policy](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
- [Creative Commons Zero (CC0)](https://creativecommons.org/publicdomain/zero/1.0/) — equivalent to public domain
- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain background
- [data/README.md](../data/README.md) — Data layout and conventions

