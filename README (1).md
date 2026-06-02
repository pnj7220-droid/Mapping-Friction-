# Clinical Friction — National Interactive Map

A Streamlit app that maps a **Clinical Friction Risk Index** across the entire United States
using the live CDC/ATSDR Social Vulnerability Index (2022). View the whole country by county,
or drill into any state at the census-tract level. Built to be deployed free and opened from a
QR code during a talk.

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy free (so a QR code can reach it)
1. Push this folder to a GitHub repo (you already have GitHub set up).
2. Go to **share.streamlit.io** → sign in with GitHub → **New app**.
3. Pick your repo, branch `main`, main file `streamlit_app.py`, and **Deploy**.
4. You get a public URL like `https://<your-app>.streamlit.app`.
5. Make a QR code for that URL (e.g. qr-code-generator.com or `qrcode` in Python) and drop it on slide 9.

## How it powers slides 5–9
- **Slide 5 — Study Area:** open on the **National (counties)** view. Your "study area" is the whole U.S.
- **Slide 6 — Friction Surface:** set the metric to **Clinical Friction Risk Index** — this is the centerpiece map.
- **Slide 7 — Results:** use the **Highest clinical-friction areas** table and the summary metrics.
- **Slide 8 — Implications:** switch metrics live (no-vehicle, uninsured) to show what drives the hot spots.
- **Slide 9 — Conclusion + QR:** the QR sends the audience to this same app on their phones.

## What the index means
CFRI is an equal-weight blend of overall SVI (`RPL_THEMES`), the housing & transportation theme
(`RPL_THEME4`), and the percentile-ranked no-vehicle, uninsured, and below-150%-poverty rates.
No-data values (`-999`) are dropped before indexing. Add an access layer (HRSA HPSA, facility
locations) for a fuller picture.

Data: CDC/ATSDR SVI 2022, pulled live from the public ArcGIS feature service.
