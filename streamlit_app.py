"""
Clinical Friction — National Interactive Map
A Streamlit app that maps a Clinical Friction Risk Index across the entire U.S.
using the live CDC/ATSDR Social Vulnerability Index (2022) feature service.

Deploy free on Streamlit Community Cloud from GitHub, then point a QR code at it.
"""

import json
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
st.set_page_config(page_title="Clinical Friction — National Map",
                   page_icon="🧭", layout="wide")

SVI = ("https://onemap.cdc.gov/onemapservices/rest/services/SVI/"
       "CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer")
COUNTY_LAYER, TRACT_LAYER = 1, 2

# Fields we pull (SVI 2022 standard names). -999 = no data.
FIELDS = ["FIPS", "LOCATION", "COUNTY", "STATE", "ST_ABBR",
          "RPL_THEMES", "RPL_THEME4", "EP_NOVEH", "EP_UNINSUR", "EP_POV150"]

METRICS = {
    "Clinical Friction Risk Index": "CFRI",
    "Overall social vulnerability (SVI)": "RPL_THEMES",
    "Housing & transportation theme": "RPL_THEME4",
    "% households with no vehicle": "EP_NOVEH",
    "% uninsured": "EP_UNINSUR",
    "% below 150% poverty": "EP_POV150",
}

STATES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California",
"CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia","FL":"Florida",
"GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas",
"KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan",
"MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
"NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina",
"ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island",
"SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont",
"VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"}


# ----------------------------------------------------------------------
# Data layer
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86400)
def fetch_svi(layer: int, where: str = "1=1", simplify: float = 0.0) -> dict:
    """Page through an ArcGIS feature layer and return a GeoJSON FeatureCollection."""
    feats, offset, page = [], 0, 2000
    while True:
        params = {
            "where": where,
            "outFields": ",".join(FIELDS),
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page,
            "returnGeometry": "true",
            "geometryPrecision": 5,
        }
        if simplify:
            params["maxAllowableOffset"] = simplify
        r = requests.get(f"{SVI}/{layer}/query", params=params, timeout=60)
        r.raise_for_status()
        js = r.json()
        batch = js.get("features", [])
        feats.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return {"type": "FeatureCollection", "features": feats}


def to_frame(fc: dict) -> pd.DataFrame:
    rows = [f["properties"] for f in fc["features"]]
    df = pd.DataFrame(rows)
    for c in ["RPL_THEMES", "RPL_THEME4", "EP_NOVEH", "EP_UNINSUR", "EP_POV150"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df.loc[df[c] < 0, c] = np.nan          # -999 -> missing
    df["FIPS"] = df["FIPS"].astype(str)
    return df


def add_cfri(df: pd.DataFrame) -> pd.DataFrame:
    """Composite 0-1 index: equal blend of overall SVI, the housing/transport
    theme, and percentile-ranked no-vehicle, uninsured, and poverty rates."""
    comps = []
    for c in ["RPL_THEMES", "RPL_THEME4"]:
        if c in df: comps.append(df[c])
    for c in ["EP_NOVEH", "EP_UNINSUR", "EP_POV150"]:
        if c in df: comps.append(df[c].rank(pct=True))
    df["CFRI"] = pd.concat(comps, axis=1).mean(axis=1, skipna=True).round(3)
    return df


def bbox_center(fc: dict):
    xs, ys = [], []
    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for p in c: walk(p)
    for f in fc["features"]:
        g = f.get("geometry") or {}
        if g.get("coordinates"): walk(g["coordinates"])
    if not xs:
        return 38.0, -96.0, 3
    lon = (min(xs) + max(xs)) / 2
    lat = (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    zoom = 3 if span > 40 else 4 if span > 20 else 5 if span > 8 else 6 if span > 3 else 7
    return lat, lon, zoom


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.title("Clinical Friction — a national risk surface")
st.caption("Where social vulnerability and access barriers intersect to produce "
           "hidden delays in healthcare delivery. Data: CDC/ATSDR SVI 2022.")

with st.sidebar:
    st.header("Map controls")
    scope = st.radio("Geography", ["National (counties)", "State detail (census tracts)"])
    state = None
    if scope.startswith("State"):
        state = st.selectbox("State", options=list(STATES),
                             format_func=lambda k: STATES[k], index=list(STATES).index("WV"))
    metric_label = st.selectbox("Color the map by", list(METRICS), index=0)
    scheme = st.selectbox("Color scale", ["Inferno", "Magma", "Plasma", "Viridis", "Cividis"])
    st.markdown("---")
    st.markdown("**Clinical Friction Risk Index** blends overall SVI, the housing & "
                "transportation theme, and no-vehicle, uninsured, and poverty rates "
                "into a single 0–1 score per area.")

metric = METRICS[metric_label]

try:
    with st.spinner("Loading CDC/ATSDR SVI…"):
        if scope.startswith("National"):
            fc = fetch_svi(COUNTY_LAYER, simplify=0.01)
        else:
            fc = fetch_svi(TRACT_LAYER, where=f"ST_ABBR='{state}'", simplify=0.002)
        df = add_cfri(to_frame(fc))
except Exception as e:
    st.error(f"Could not reach the CDC service ({e}). Try again, or switch geography.")
    st.stop()

lat, lon, zoom = bbox_center(fc)
namecol = "LOCATION" if "LOCATION" in df else "COUNTY"

fig = px.choropleth_map(
    df, geojson=fc, locations="FIPS", featureidkey="properties.FIPS",
    color=metric, color_continuous_scale=scheme,
    range_color=(0, 1) if metric in ("CFRI", "RPL_THEMES", "RPL_THEME4") else None,
    map_style="carto-positron", zoom=zoom, center={"lat": lat, "lon": lon},
    opacity=0.78, hover_name=namecol,
    hover_data={"FIPS": False, "CFRI": ":.2f", "RPL_THEMES": ":.2f",
                "EP_NOVEH": ":.1f", "EP_UNINSUR": ":.1f"},
    labels={metric: metric_label},
)
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=620,
                  coloraxis_colorbar=dict(title=metric_label, thickness=14))
st.plotly_chart(fig, use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("Areas mapped", f"{len(df):,}")
c2.metric("Highest friction", f"{df['CFRI'].max():.2f}")
c3.metric("Median friction", f"{df['CFRI'].median():.2f}")

st.subheader("Highest clinical-friction areas")
top = (df.sort_values("CFRI", ascending=False)
         .head(15)[[namecol, "STATE", "CFRI", "RPL_THEMES", "EP_NOVEH", "EP_UNINSUR"]]
         .rename(columns={namecol: "Area", "RPL_THEMES": "Overall SVI",
                          "EP_NOVEH": "% no vehicle", "EP_UNINSUR": "% uninsured"}))
st.dataframe(top, use_container_width=True, hide_index=True)

with st.expander("Methods & data notes"):
    st.markdown(
        "- **Source:** CDC/ATSDR Social Vulnerability Index 2022, county and tract levels, "
        "pulled live from the public ArcGIS feature service.\n"
        "- **Clinical Friction Risk Index (CFRI):** equal-weight blend of overall SVI "
        "(`RPL_THEMES`), the housing & transportation theme (`RPL_THEME4`), and the "
        "percentile-ranked no-vehicle, uninsured, and below-150%-poverty rates.\n"
        "- **No-data** (`-999`) values are dropped before indexing.\n"
        "- Add an access layer (HRSA HPSA, facility locations) for a fuller friction picture.")
