# EmberGuide UI

Streamlit-based interactive web interface for visualizing wildfire nowcasts, exploring detections, and downloading data products.

---

## Overview

The UI provides:
- **Interactive map** with fire detections, probability heatmap, wind barbs
- **Multiple horizons** (12h, 24h, 48h) with toggle buttons
- **Probability contours** (p≥0.3, 0.5, 0.7) for different risk envelopes
- **Metrics page** with reliability plots, CSI/IoU, directional error
- **Download buttons** for GeoTIFFs and reports
- **Disclaimers** and data attribution in footer

**Key principles**:
- **No heavy compute**: All data fetched from API
- **Clear timestamps**: "Last updated" for detections and weather
- **Non-tactical messaging**: Prominent disclaimer that this is research/communication only

---

## Quick Start

### Development

```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start API (in one terminal)
make serve-api  # Or: uvicorn api.main:app --port 8000

# Start UI (in another terminal)
streamlit run ui/app.py --server.port 8501

# Or use Make
make serve-ui
```

Visit http://localhost:8501

### Production

```bash
# Use streamlit with production settings
streamlit run ui/app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false
```

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for reverse proxy setup.

---

## UI Structure

```
ui/
├── app.py                  # Main Streamlit entry point
├── pages/
│   ├── 1_Map.py            # Interactive map view
│   ├── 2_Metrics.py        # Evaluation and reliability
│   └── 3_About.py          # Project info and disclaimers
├── components/
│   ├── map_viewer.py       # Pydeck/Folium map component
│   ├── fire_selector.py    # Dropdown for active fires
│   ├── horizon_toggle.py   # 12h/24h/48h buttons
│   └── attribution.py      # Footer with data credits
├── utils/
│   ├── api_client.py       # Wrapper for API calls
│   ├── styles.py           # CSS and theming
│   └── cache.py            # Streamlit caching helpers
└── assets/
    ├── logo.png
    └── disclaimer.md
```

---

## Pages

### 1. Map View (`pages/1_Map.py`)

**Features**:
- **Base layer**: Satellite or terrain
- **Fire detections**: Scatter plot with color by confidence
- **Probability heatmap**: Translucent overlay (0=transparent, 1=red/orange)
- **Wind barbs**: Vector arrows showing wind direction and speed
- **Contours**: p≥0.3 (yellow), p≥0.5 (orange), p≥0.7 (red)
- **Toggles**:
  - Horizon: 12h / 24h / 48h
  - Probability contours: Show/hide
  - Wind barbs: Show/hide
  - Detections: Show/hide

**Layout**:
```
+-----------------------------------+
| Fire: [Dropdown ▼] Horizon: 24h  |
| Last updated: 2024-01-15 12:30 UTC|
+-----------------------------------+
|                                   |
|         Interactive Map           |
|     (pydeck or folium)            |
|                                   |
+-----------------------------------+
| [Download GeoTIFF] [Download Report]
+-----------------------------------+
| ⚠️ Research preview — not for    |
| life-safety decisions.            |
+-----------------------------------+
```

**Implementation**:
```python
import streamlit as st
import pydeck as pdk
from utils.api_client import get_nowcast

st.title("🔥 EmberGuide Wildfire Nowcast")

# Fire selector
fire_id = st.selectbox("Select Fire", fires)
horizon = st.radio("Horizon", [12, 24, 48], index=1)

# Fetch data from API
nowcast = get_nowcast(fire_id, horizon)

# Build map layers
detections_layer = pdk.Layer(
    "ScatterplotLayer",
    data=nowcast["detections"],
    get_position=["lon", "lat"],
    get_color=[255, 100, 100],
    get_radius=500,
)

heatmap_layer = pdk.Layer(
    "HeatmapLayer",
    data=probability_grid,
    get_position=["lon", "lat"],
    get_weight="probability",
)

# Render map
st.pydeck_chart(pdk.Deck(
    layers=[detections_layer, heatmap_layer],
    initial_view_state=pdk.ViewState(
        latitude=nowcast["grid_meta"]["center_lat"],
        longitude=nowcast["grid_meta"]["center_lon"],
        zoom=9,
    ),
))

# Downloads
col1, col2 = st.columns(2)
with col1:
    st.download_button("Download GeoTIFF", data=geotiff_bytes, file_name="nowcast.tif")
with col2:
    st.download_button("Download Report", data=report_json, file_name="report.json")
```

---

### 2. Metrics View (`pages/2_Metrics.py`)

**Features**:
- **Reliability diagram**: Predicted probability vs observed frequency
- **CSI / IoU** over time (if multiple fires)
- **Directional error** distribution
- **Comparison**: Baseline vs ML-enhanced (if enabled)

**Layout**:
```
+-----------------------------------+
| Reliability Curve                 |
| (predicted prob vs observed freq) |
+-----------------------------------+
| CSI: 0.45  |  IoU: 0.38           |
| Directional Error: 23°            |
+-----------------------------------+
| Baseline vs ML Comparison         |
| [Toggle: Denoiser ON/OFF]         |
+-----------------------------------+
```

---

### 3. About Page (`pages/3_About.py`)

**Content**:
- Project summary (link to [WILDFIRE_101.md](../WILDFIRE_101.md))
- How to read the maps
- Known limitations
- Data sources and attribution
- Contact and GitHub link

---

## Components

### Fire Selector (`components/fire_selector.py`)

```python
import streamlit as st
from utils.api_client import get_fires

def fire_selector():
    fires = get_fires()
    fire_options = {f"{f['id']} ({f['region']})": f['id'] for f in fires}
    selected = st.selectbox("Select Fire", fire_options.keys())
    return fire_options[selected]
```

### Map Viewer (`components/map_viewer.py`)

Supports both **pydeck** (WebGL) and **folium** (Leaflet):

```python
def render_map(nowcast, use_pydeck=True):
    if use_pydeck:
        return render_pydeck_map(nowcast)
    else:
        return render_folium_map(nowcast)
```

**Pydeck** (faster, better for large datasets):
- HeatmapLayer for probability
- ScatterplotLayer for detections
- IconLayer for wind barbs

**Folium** (fallback, better browser compatibility):
- TileLayer for probability tiles
- CircleMarkers for detections
- Custom icon for wind arrows

---

## API Integration

### API Client (`utils/api_client.py`)

```python
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000"

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_fires():
    response = requests.get(f"{API_BASE_URL}/fires")
    response.raise_for_status()
    return response.json()["fires"]

@st.cache_data(ttl=300)
def get_nowcast(fire_id: str, horizon: int = 24):
    response = requests.get(f"{API_BASE_URL}/nowcast/{fire_id}?horizon={horizon}")
    response.raise_for_status()
    return response.json()

def download_geotiff(fire_id: str, horizon: int = 24):
    url = f"{API_BASE_URL}/downloads/{fire_id}/nowcast_{horizon}h.tif"
    response = requests.get(url)
    response.raise_for_status()
    return response.content
```

**Error handling**:
```python
try:
    fires = get_fires()
except requests.RequestException as e:
    st.error(f"Failed to load fires: {e}")
    st.stop()
```

---

## Design Principles

### 1. No Heavy Compute in UI

**Bad**:
```python
# Don't do this in Streamlit!
spread_model = run_spread_model(hotspots, weather)  # Slow!
```

**Good**:
```python
# Fetch pre-computed results from API
nowcast = get_nowcast(fire_id, horizon)  # Fast!
```

### 2. Timestamps Everywhere

Always show "Last updated" for detections and weather:
```python
st.caption(f"Last updated: {nowcast['generated_at']} UTC")
```

### 3. Non-Tactical Disclaimer

Prominently display in:
- Page footer
- About page
- Download confirmation

**Text**:
> ⚠️ **Research preview — not for life-safety decisions.**  
> EmberGuide is a research and communications tool. Always defer to official incident information and evacuation orders.

### 4. Attribution Footer

Credit data providers on every page:
```python
st.markdown("---")
st.caption("""
**Data Sources**: FIRMS (NASA) · ERA5 (Copernicus/ECMWF) · SRTM (NASA/USGS)  
[About](./About) · [GitHub](https://github.com/yourusername/ember-guide)
""")
```

---

## Styling & Theming

### Custom CSS (`utils/styles.py`)

```python
import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom fire warning colors */
    .fire-low {color: #FFA500;}
    .fire-medium {color: #FF6347;}
    .fire-high {color: #DC143C;}
    
    /* Disclaimer box */
    .disclaimer {
        background-color: #FFF3CD;
        border: 1px solid #FFE082;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
```

### Color Palette

- **Probability heatmap**: Yellow (low) → Orange → Red (high)
- **Detections**: Red circles (filled)
- **Wind barbs**: Blue arrows
- **Contours**: 
  - p≥0.3: `#FFEB3B` (yellow)
  - p≥0.5: `#FF9800` (orange)
  - p≥0.7: `#F44336` (red)

---

## Caching & Performance

### Streamlit Caching

```python
import streamlit as st

# Cache data for 5 minutes (don't hammer API)
@st.cache_data(ttl=300)
def load_fires():
    return api_client.get_fires()

# Cache resources (model, configs) indefinitely
@st.cache_resource
def load_config():
    return yaml.safe_load(open("configs/ui.yml"))
```

### Debouncing Filters

Avoid reloading on every slider change:
```python
horizon = st.slider("Horizon (hours)", 12, 48, 24, step=12)

if st.button("Update Map"):
    # Only reload when user clicks button
    nowcast = get_nowcast(fire_id, horizon)
```

---

## Accessibility

- **Alt text** for images
- **Color contrast**: Ensure text readable over map
- **Keyboard navigation**: Use Streamlit's native widgets
- **Screen readers**: Semantic HTML in markdown

---

## Testing

### Manual Testing Checklist

- [ ] Map loads with valid fire ID
- [ ] Detections appear at correct locations
- [ ] Probability heatmap shows gradient
- [ ] Horizon toggle updates map
- [ ] Download buttons work (GeoTIFF, report)
- [ ] Disclaimer visible on all pages
- [ ] Attribution in footer
- [ ] Timestamps show correct UTC time
- [ ] Error handling (invalid fire ID, API down)

### Automated Tests

```python
# tests/ui/test_api_client.py
import pytest
from ui.utils.api_client import get_fires, get_nowcast

def test_get_fires(mock_api):
    fires = get_fires()
    assert isinstance(fires, list)
    assert len(fires) > 0

def test_get_nowcast(mock_api):
    nowcast = get_nowcast("fire_001", 24)
    assert nowcast["fire_id"] == "fire_001"
    assert nowcast["horizon"] == 24
```

---

## Configuration

### `configs/ui.yml`

```yaml
ui:
  title: "EmberGuide Wildfire Nowcast"
  api_base_url: "http://localhost:8000"
  default_horizon: 24
  
  map:
    default_zoom: 9
    default_basemap: "satellite"  # or "terrain"
    use_pydeck: true  # Set false to use Folium
  
  colors:
    low_prob: "#FFEB3B"
    med_prob: "#FF9800"
    high_prob: "#F44336"
  
  cache_ttl: 300  # seconds
```

### Environment Variables

```bash
# API endpoint (for production)
API_BASE_URL=https://api.emberguide.example.com

# Streamlit server settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

---

## Troubleshooting

### "Connection error to API"

**Solution**:
- Check API is running: `curl http://localhost:8000/health`
- Verify `API_BASE_URL` in config
- Check CORS settings in API

### "Map is blank"

**Solution**:
- Inspect browser console for JavaScript errors
- Check nowcast data has valid lat/lon
- Verify tile URLs are accessible
- Try switching from pydeck to folium

### "Slow page load"

**Solution**:
- Reduce cache TTL (fetch fresh data less often)
- Limit number of detections rendered (sample if >1000)
- Use smaller tile sizes
- Enable CDN for tiles

---

## Deployment

### Docker

```dockerfile
# Dockerfile for UI
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ui/ ./ui/
COPY configs/ ./configs/

CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t emberguide-ui .
docker run -p 8501:8501 -e API_BASE_URL=http://api:8000 emberguide-ui
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name map.emberguide.example.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md) for full setup.

---

## Next Steps

- **API**: See [api/README.md](../api/README.md) for backend endpoints
- **Pipeline**: See [pipeline/README.md](../pipeline/README.md) for data generation
- **Deployment**: See [docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)

---

## References

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Pydeck Documentation](https://deckgl.readthedocs.io/en/latest/)
- [Folium Documentation](https://python-visualization.github.io/folium/)
- [WILDFIRE_101.md](../WILDFIRE_101.md) — Domain background

