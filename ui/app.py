"""EmberGuide Streamlit UI - Main Application."""

import json
from datetime import datetime

import streamlit as st

from ui.utils.api_client import get_fires, get_nowcast, download_geotiff, get_report, check_health
from ui.components.map_viewer import render_map

# Page configuration
st.set_page_config(
    page_title="EmberGuide Wildfire Nowcast",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .disclaimer {
        background-color: #FFF3CD;
        border: 2px solid #FFE082;
        padding: 15px;
        border-radius: 5px;
        margin: 15px 0;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application."""
    
    # Title
    st.title("🔥 EmberGuide Wildfire Nowcast")
    st.markdown("**Open-source probabilistic wildfire nowcasts from satellite hotspots, weather, and terrain**")
    
    # Disclaimer banner
    st.markdown("""
    <div class="disclaimer">
        ⚠️ <strong>Research Preview — Not for Life-Safety Decisions</strong><br>
        EmberGuide is a research and communications tool. Always defer to official incident information and evacuation orders.
    </div>
    """, unsafe_allow_html=True)
    
    # Check API health
    if not check_health():
        st.error("⚠️ Cannot connect to EmberGuide API. Make sure the API server is running.")
        st.info("Start the API with: `make serve-api` or `uvicorn api.main:app --port 8000`")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("Controls")
        
        # Fire selector
        fires = get_fires()
        
        if not fires:
            st.warning("No active fires found. Run the pipeline first: `make run-pipeline`")
            st.stop()
        
        fire_options = {f"{f['id']} ({f['region']})": f['id'] for f in fires}
        selected_label = st.selectbox("Select Fire", list(fire_options.keys()))
        selected_fire_id = fire_options[selected_label]
        
        # Horizon selector (for POC, only 24h available)
        horizon = st.radio("Forecast Horizon", [24], format_func=lambda x: f"{x}h")
        
        st.markdown("---")
        
        # Info
        st.markdown("### About")
        st.markdown("""
        EmberGuide produces 24-hour probabilistic wildfire spread maps using:
        - 🛰️ **FIRMS** satellite hotspots
        - 🌬️ **ERA5** weather data
        - ⛰️ **SRTM** terrain elevation
        """)
        
        st.markdown("---")
        st.caption("EmberGuide POC v0.1.0")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header(f"Fire: {selected_fire_id}")
        
        # Load nowcast data
        with st.spinner("Loading nowcast data..."):
            nowcast = get_nowcast(selected_fire_id, horizon)
        
        if not nowcast:
            st.error(f"Could not load nowcast data for {selected_fire_id}")
            st.stop()
        
        # Display map
        st.subheader("🗺️ Probability Map")
        
        # Try to download GeoTIFF for visualization
        prob_filename = f"nowcast_{horizon}h.tif"
        prob_tif_bytes = download_geotiff(selected_fire_id, prob_filename)
        
        render_map(nowcast, prob_tif_bytes)
        
        st.caption(f"Last updated: {nowcast['generated_at']} UTC")
    
    with col2:
        st.header("Metrics")
        
        # Display metrics
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Max Probability",
            f"{nowcast['metrics']['max_probability']:.2%}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Mean Probability",
            f"{nowcast['metrics']['mean_probability']:.2%}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Affected Area",
            f"{nowcast['metrics']['affected_area_km2']:.1f} km²"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "Hotspot Detections",
            f"{nowcast['detections']['count']}"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Downloads
        st.subheader("📥 Downloads")
        
        # Download GeoTIFF
        if prob_tif_bytes:
            st.download_button(
                label="Download Probability GeoTIFF",
                data=prob_tif_bytes,
                file_name=f"{selected_fire_id}_nowcast_{horizon}h.tif",
                mime="image/tiff"
            )
        
        # Download report
        if st.button("Generate Report"):
            report = get_report(selected_fire_id, horizon)
            if report:
                st.download_button(
                    label="Download JSON Report",
                    data=json.dumps(report, indent=2),
                    file_name=f"{selected_fire_id}_report_{horizon}h.json",
                    mime="application/json"
                )
    
    # Caveats
    st.markdown("---")
    st.subheader("ℹ️ Important Caveats")
    
    for caveat in nowcast.get('caveats', []):
        st.markdown(f"- {caveat}")
    
    # Attribution footer
    st.markdown("---")
    st.caption("**Data Sources**: " + " · ".join(nowcast.get('attribution', [])))
    st.caption("Contains modified Copernicus Climate Change Service information 2024.")
    st.caption("[GitHub](https://github.com/yourusername/ember-guide) · [Documentation](../README.md)")


if __name__ == "__main__":
    main()

