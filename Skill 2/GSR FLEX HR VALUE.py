# =========================
# Adjustable parameters
# =========================
RESAMPLE_STEP_M = 2.0     # Route resampling interval (meters)
SMOOTH_WINDOW_M = 30.0    # Smoothing window (meters)

# Make lines thinner (for even thinner: CORE_WEIGHT=2, GLOW_WEIGHT=4)
GLOW_WEIGHT = 6
GLOW_OPACITY = 0.18
CORE_WEIGHT = 3
CORE_OPACITY = 0.95

# Points
POINT_RADIUS = 1
POINT_OPACITY = 0.95      # Brighter points, like "star dots"
POINT_BORDER = 0          # 0 = no border

# Default visibility
SHOW_BASEMAP = True
SHOW_BLANK = False
SHOW_ROUTE_BASE = False

SHOW_GSR_LINE = True
SHOW_BPM_LINE = False
SHOW_FLEX_LINE = False

SHOW_GSR_POINTS = True
SHOW_BPM_POINTS = False
SHOW_FLEX_POINTS = False


# =========================
# 1) Upload CSV + KMZ/KML
# =========================
uploaded = files.upload()
csv_name, route_name = None, None
for n in uploaded:
    if n.lower().endswith(".csv"):
        csv_name = n
    if n.lower().endswith(".kmz") or n.lower().endswith(".kml"):
        route_name = n

if not csv_name or not route_name:
    raise RuntimeError("Please upload both: CSV data + KMZ/KML route file")

print("✅ CSV  :", csv_name)
print("✅ Route:", route_name)


# =========================
# 2) Read CSV (auto-detect columns)
# =========================
raw_csv = uploaded[csv_name]
try:
    df = pd.read_csv(io.BytesIO(raw_csv), encoding="utf-8-sig")
except UnicodeDecodeError:
    df = pd.read_csv(io.BytesIO(raw_csv), encoding="gbk")

def pick_col(cols, candidates):
    m = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand in m:
            return m[cand]
    return None

cols = df.columns.tolist()
time_col = pick_col(cols, ["time", "timestamp", "datetime", "date_time", "date"])
lat_col  = pick_col(cols, ["lat", "latitude"])
lon_col  = pick_col(cols, ["lon", "lng", "long", "longitude"])
gsr_col  = pick_col(cols, ["gsr", "eda"])
bpm_col  = pick_col(cols, ["bpm", "hr", "heart_rate", "heartrate", "heart rate"])
flex_col = pick_col(cols, ["flex"])

needed = [lat_col, lon_col, gsr_col, bpm_col, flex_col]
if any(x is None for x in needed):
    raise ValueError(
        "❌ Required columns not detected. Please ensure CSV includes: lat/lng + gsr + bpm/hr(heart_rate) + flex.\n"
        f"Current columns: {cols}"
    )

rename_map = {lat_col:"lat", lon_col:"lon", gsr_col:"gsr", bpm_col:"bpm", flex_col:"flex"}
if time_col is not None:
    rename_map[time_col] = "time"
df = df.rename(columns=rename_map).copy()

for c in ["lat","lon","gsr","bpm","flex"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

if "time" in df.columns:
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
else:
    df["time"] = np.arange(len(df))

df = df.dropna(subset=["lat","lon","gsr","bpm","flex"]).copy()
df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)].copy()
df = df.sort_values("time").reset_index(drop=True)

print("✅ Cleaned point count:", len(df))


# =========================
# 3) Parse KMZ/KML route coordinates (lon,lat)
# =========================
def extract_kml_text(route_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".kml"):
        return route_bytes.decode("utf-8", errors="ignore")
    zf = zipfile.ZipFile(io.BytesIO(route_bytes))
    kml_files = [n for n in zf.namelist() if n.lower().endswith(".kml")]
    if not kml_files:
        raise ValueError("No KML file found inside KMZ")
    return zf.read(kml_files[0]).decode("utf-8", errors="ignore")

def parse_route_lonlat(kml_text: str):
    candidates = []

    # <coordinates>
    try:
        root = ET.fromstring(kml_text)
        for elem in root.iter():
            tag = elem.tag.lower()
            if tag.endswith("coordinates") and elem.text:
                text = elem.text.strip()
                parts = re.split(r"\s+", text)
                pts = []
                for p in parts:
                    if not p:
                        continue
                    vals = p.split(",")
                    if len(vals) >= 2:
                        try:
                            lon = float(vals[0]); lat = float(vals[1])
                            pts.append((lon, lat))
                        except:
                            pass
                if len(pts) >= 2:
                    candidates.append(pts)
    except Exception:
        pass

    # gx:Track
    gx = re.findall(r"<gx:coord>\s*([-\d\.]+)\s+([-\d\.]+)(?:\s+[-\d\.]+)?\s*</gx:coord>", kml_text)
    if gx:
        pts = [(float(lon), float(lat)) for lon, lat in gx]
        if len(pts) >= 2:
            candidates.append(pts)

    if not candidates:
        raise ValueError("❌ No valid route extracted from KML")

    candidates.sort(key=len, reverse=True)
    return candidates[0]

def clean_route_lonlat(route_lonlat):
    cleaned = [(float(lon), float(lat)) for lon, lat in route_lonlat
               if np.isfinite(lon) and np.isfinite(lat)]
    dedup = []
    for pt in cleaned:
        if not dedup or pt != dedup[-1]:
            dedup.append(pt)
    if len(dedup) < 2:
        raise ValueError("❌ Route contains fewer than 2 valid points")
    return dedup

kml_text = extract_kml_text(uploaded[route_name], route_name)
route_lonlat = clean_route_lonlat(parse_route_lonlat(kml_text))
print("✅ Valid route points:", len(route_lonlat))


# =========================
# 5) Smoothing + resampling (for line visualization)
# =========================
print(f"✅ Smoothing window: {window_pts} points (~{SMOOTH_WINDOW_M}m), resampled points: {len(grid)}")


# =========================
# 6) Color scales
# =========================
# Note: point colors are scaled using original df values to reflect real distribution


# =========================
# 7) Map drawing
# =========================
# Basemap (clean, no labels)

# Pure black background (alternative basemap)

# Route base (optional)

# Gradient lines (3 types)

# Point layers: 3 toggles, colored by value


# =========================
# 8) Export
# =========================
print("✅ Output:", out_csv, out_html)
