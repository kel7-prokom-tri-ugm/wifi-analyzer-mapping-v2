from __future__ import annotations

import os
from html import escape

import folium
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation

from modules import ai_advisor, location as geo, network_scanner, security_test
from modules.database import (
    find_location_by_name,
    generate_location_id,
    get_all_locations_summary,
    get_location_scan_history,
    get_scan_history,
    init_db,
    save_scan_result,
)
from modules.visualizer import (
    CATEGORY_TONE,
    render_activity_chips,
    render_community_map,
    render_history_table,
    render_metric_card,
    render_section_heading,
    render_speed_gauge,
    render_speed_security_chart,
    render_status_card,
)

st.set_page_config(
    page_title="WiFi-Radar ID | Public Wi-Fi Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Komponen speedtest client-side (berjalan di browser pengguna via Cloudflare)
_SPEEDTEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "speedtest")
browser_speedtest = components.declare_component("browser_speedtest", path=_SPEEDTEST_DIR)

# ---------- Theme ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    :root { --bg:#080f1c; --panel:#142238; --panel2:#1a2b42; --line:#344a65; --muted:#b8c7d9; --text:#f4f8ff; --cyan:#35d5e8; --blue:#638cff; }
    html, body, [data-testid="stAppViewContainer"] { background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
    [data-testid="stHeader"] { background:rgba(8,15,28,.92); }
    [data-testid="stSidebar"] { background:#0b1626; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] * { color:var(--text); }
    .block-container { padding-top:3.75rem; padding-bottom:3rem; max-width:1440px; }
    h1,h2,h3,.brand-name,.section-title { font-family:'Space Grotesk',sans-serif !important; }
    .brand { display:flex; align-items:center; gap:11px; padding:8px 4px 20px; }
    .brand-mark { width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#35d5e8,#638cff);display:flex;align-items:center;justify-content:center;color:#06111e;font-size:20px;font-weight:700; }
    .brand-name { font-size:19px;font-weight:700;letter-spacing:-.5px; }
    .brand-sub { color:var(--muted);font-size:10px;letter-spacing:1.6px;text-transform:uppercase;margin-top:2px; }

    /* Sidebar navigation buttons with hover + active states */
    [data-testid="stSidebar"] div.stButton {
        margin-bottom: 4px;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
        width: 100%;
        justify-content: flex-start;
        background: #111f32;
        border: 1px solid var(--line);
        border-radius: 11px;
        padding: 10px 14px;
        min-height: 42px;
        transition: background .18s ease, border-color .18s ease, transform .18s ease, box-shadow .18s ease;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"] p {
        color: #dce8f5 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: color .18s ease;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
        background: rgba(53, 213, 232, 0.14);
        border-color: var(--cyan);
        box-shadow: 0 0 14px rgba(53, 213, 232, 0.20);
        transform: translateX(3px);
    }
    [data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover p {
        color: var(--cyan) !important;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        width: 100%;
        justify-content: flex-start;
        background: linear-gradient(100deg, rgba(53, 213, 232, 0.24), rgba(99, 140, 255, 0.20));
        border: 1px solid var(--cyan);
        border-radius: 11px;
        padding: 10px 14px;
        min-height: 42px;
        box-shadow: inset 3px 0 0 var(--cyan), 0 4px 16px rgba(53, 213, 232, 0.15);
    }
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] p {
        color: #f4f8ff !important;
        font-size: 14px !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
        filter: brightness(1.1);
    }

    .eyebrow { color:var(--cyan);font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px; }
    .page-title { font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:700;letter-spacing:-1px;color:var(--text);margin:0; }
    .page-desc { color:var(--muted);font-size:14px;margin-top:6px; }
    .topline { border-bottom:1px solid var(--line);padding-bottom:20px;margin-bottom:24px; }
    .panel { background:linear-gradient(145deg,#122238,#0e1929);border:1px solid var(--line);border-radius:18px;padding:22px 24px; }
    .panel-label { color:var(--muted);font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase; }
    .gauge-wrap { display:flex;flex-direction:column;align-items:center;justify-content:center;padding:14px 0 2px; }
    .gauge { width:218px;height:218px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(from 225deg,var(--cyan) 0 var(--progress),#26364c var(--progress) 75%,transparent 75% 100%);position:relative; }
    .gauge:before { content:'';position:absolute;inset:10px;border-radius:50%;background:#101d30;border:1px solid #263a52; }
    .gauge-inner { position:relative;text-align:center; }
    .gauge-label { color:#9db3ca;font-size:10px;letter-spacing:1.7px;font-weight:700; }
    .gauge-value { font-family:'Space Grotesk',sans-serif;font-size:49px;font-weight:700;line-height:1.15;color:#f2f8ff;margin-top:8px; }
    .gauge-value span { font-family:'DM Sans',sans-serif;font-size:12px;color:#9db3ca;font-weight:500; }
    .gauge-unit { color:var(--cyan);font-size:10px;letter-spacing:1.4px;margin-top:5px; }
    .gauge-subtext { color:var(--muted);font-size:11px;margin-top:14px; }
    .metric-card { background:#111f32;border:1px solid var(--line);border-radius:15px;padding:17px 18px;min-height:136px;margin-bottom:12px; }
    .metric-top { display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:14px; }
    .metric-icon { width:30px;height:30px;display:grid;place-items:center;border-radius:9px;background:#1a3448;color:var(--cyan);font-size:15px;flex-shrink:0; }
    .metric-note { font-size:10px;color:#b8c7d9;white-space:nowrap; }
    .metric-title { color:#a9bbce;font-size:12px; }
    .metric-value { color:#f2f7ff;font-family:'Space Grotesk',sans-serif;font-size:27px;font-weight:700;margin-top:4px; }
    .metric-value span { font-family:'DM Sans',sans-serif;font-size:12px;color:#91a6bd;font-weight:500; }
    .section-heading { margin:26px 0 14px; }
    .section-title { font-size:18px;font-weight:600;color:var(--text); }
    .section-subtitle { color:var(--muted);font-size:12px;margin-top:3px; }
    .status-card { display:flex;gap:12px;align-items:flex-start;background:#111f32;border:1px solid var(--line);border-radius:14px;padding:16px;min-height:112px; }
    .status-dot { width:9px;height:9px;border-radius:50%;background:#8295aa;margin-top:5px;flex-shrink:0; }
    .status-card.good .status-dot { background:#39d6a2;box-shadow:0 0 12px #39d6a255; }
    .status-card.warning .status-dot { background:#f5b84b;box-shadow:0 0 12px #f5b84b55; }
    .status-card.danger .status-dot { background:#f05a5a;box-shadow:0 0 12px #f05a5a55; }
    .chip-row { display:flex;flex-wrap:wrap;gap:8px;margin-top:6px; }
    .chip { background:#16314a;border:1px solid #1d5264;color:#b9f0f7;border-radius:999px;padding:5px 12px;font-size:12px;font-weight:600; }
    .chip-empty { display:inline-block;background:#3a1c24;border-color:#7a2e3a;color:#ffc4c4; }
    .legend { display:flex;gap:18px;margin-top:10px;color:var(--muted);font-size:12px; }
    .legend-item { display:flex;align-items:center;gap:6px; }
    .legend-dot { width:10px;height:10px;border-radius:50%;display:inline-block; }
    .status-title { color:#9db1c7;font-size:11px; }
    .status-value { color:#f0f6ff;font-size:14px;font-weight:700;margin-top:4px; }
    .status-detail { color:#b8c7d9;font-size:11px;margin-top:4px;line-height:1.45; }
    .info-banner { background:#10283a;border:1px solid #1d5264;border-radius:12px;padding:13px 16px;color:#b9dce7;font-size:12px;line-height:1.5; }
    .meta-strip { display:flex;flex-wrap:wrap;gap:12px;margin-top:12px; }
    .meta-pill { background:#111f32;border:1px solid var(--line);border-radius:10px;padding:8px 13px;font-size:12px;color:#d5e1ef; }
    .meta-pill strong { color:var(--cyan);font-weight:600; }

    /* Buttons */
    div.stButton > button[kind="primary"],
    div.stButton > button:not([kind="secondary"]) {
        background:linear-gradient(100deg,#35d5e8,#638cff);
        color:#06111e;
        border:0;
        border-radius:11px;
        font-weight:700;
        padding:.65rem 1rem;
        min-height:44px;
        transition:filter .16s ease, transform .16s ease;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button:not([kind="secondary"]):hover {
        border:0;
        color:#06111e;
        filter:brightness(1.08);
    }
    div.stButton > button[kind="secondary"] {
        background:#132338;
        color:#dce8f5;
        border:1px solid var(--line);
        border-radius:11px;
        font-weight:600;
        padding:.65rem 1rem;
        min-height:44px;
        transition:border-color .16s ease, color .16s ease, background .16s ease;
    }
    div.stButton > button[kind="secondary"]:hover {
        border-color:var(--cyan);
        color:var(--cyan);
        background:rgba(53,213,232,.08);
    }

    /* Cap GPS component width so no white trailing bar renders */
    .st-key-gps_box iframe {
        width: 44px !important;
        border-radius: 8px;
    }

    /* Input location, SSID, and selectbox */
    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background: #1A2B42 !important;
        color: #F4F8FF !important;
        border: 1px solid #526B8A !important;
        border-radius: 10px;
    }
    div[data-testid="stTextInput"] input::placeholder {
        color: #B8C7D9 !important;
        opacity: 1;
    }
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label {
        color: #D5E1EF !important;
        font-weight: 600;
    }
    [data-testid="stMetric"] { background:#111f32;padding:14px;border:1px solid var(--line);border-radius:12px; }
    [data-testid="stMetricLabel"] { color:#9db1c7; }
    [data-testid="stMetricValue"] { color:#f2f7ff; font-size:1.45rem !important; line-height:1.25 !important; }
    hr { border-color:var(--line); }
    .footer { color:#71869d;font-size:10px;text-align:center;margin-top:36px;padding-top:16px;border-top:1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Database bootstrap ----------
@st.cache_resource(show_spinner=False)
def bootstrap_database() -> bool:
    """Buat tabel + migrasi + muat seed_data.json sekali per proses Streamlit."""
    init_db()
    return True


bootstrap_database()

# Skenario simulasi jaringan -> skenario keamanan yang dipasangkan (sementara untuk demo)
SIMULATION_PAIRS = {
    "Cepat & aman": ("cepat", "aman"),
    "Sedang & rawan": ("sedang", "rawan"),
    "Lambat & berbahaya": ("lambat", "bahaya"),
}
NEW_LOCATION = "➕ Lokasi baru"
DEFAULT_LAT, DEFAULT_LON = -7.76951, 110.37825  # Perpustakaan Pusat UGM
NAV_LABELS = {
    "Overview": "📡  Overview",
    "Community Map": "🗺️  Community Map",
    "Scan History": "🕒  Scan History",
}

ss = st.session_state
ss.setdefault("active_page", "Overview")
ss.setdefault("overview_stage", "test")
ss.setdefault("speedtest_nonce", 0)
ss.setdefault("processed_run_ids", set())


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(query: str) -> list:
    """Cari tempat (di-cache agar tidak melanggar batas 1 request/detik Nominatim)."""
    return geo.search_places(query)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_reverse(lat: float, lon: float):
    """Koordinat -> nama tempat (di-cache per koordinat)."""
    return geo.reverse_geocode(lat, lon)


def queue_place(place: dict, force_name: bool, locations: list | None = None) -> None:
    """Jadwalkan pengisian form dari sebuah tempat, lalu rerun."""
    lat, lon = float(place["latitude"]), float(place["longitude"])
    update = {"loc_lat": lat, "loc_lon": lon}
    for field, key in (("name", "loc_name"), ("area", "loc_area")):
        current = (ss.get(key) or "").strip()
        auto_key = f"{key}_auto"
        if place.get(field) and (force_name or not current or current == ss.get(auto_key)):
            update[key] = place[field]
            ss[auto_key] = place[field]

    if locations:
        nearby = geo.nearest_known_location(lat, lon, locations, radius_m=100.0)
        if nearby:
            update["confirm_choice"] = nearby["name"]
            if nearby.get("ssid") and not (ss.get("confirm_ssid") or "").strip():
                update["confirm_ssid"] = nearby["ssid"]
    ss["loc_pending"] = update
    st.rerun()


def init_confirm_defaults(result: dict, locations: list) -> None:
    """Isi otomatis lokasi awal saat pertama kali membuka panel konfirmasi untuk run_id ini."""
    run_id = result["run_id"]
    if ss.get("confirm_init_for") == run_id:
        return
    ss["confirm_init_for"] = run_id

    net = result["network"]
    init_lat = net.get("approx_lat")
    init_lon = net.get("approx_lon")
    lat = float(init_lat) if init_lat is not None else DEFAULT_LAT
    lon = float(init_lon) if init_lon is not None else DEFAULT_LON

    detected_ssid = net.get("ssid")
    if detected_ssid in (None, "", "Tidak terhubung", "Simulasi"):
        detected_ssid = ""

    nearby = geo.nearest_known_location(lat, lon, locations, radius_m=100.0)
    if nearby:
        ss["confirm_choice"] = nearby["name"]
        ss["confirm_ssid"] = detected_ssid or nearby.get("ssid", "")
        ss["loc_lat"] = float(nearby["latitude"])
        ss["loc_lon"] = float(nearby["longitude"])
        ss["loc_name"] = nearby["name"]
        ss["loc_area"] = nearby.get("area", "")
    else:
        ss["confirm_choice"] = NEW_LOCATION
        ss["confirm_ssid"] = detected_ssid
        ss["loc_lat"] = lat
        ss["loc_lon"] = lon
        place = cached_reverse(round(lat, 5), round(lon, 5)) if (init_lat is not None) else None
        ss["loc_name"] = (place or {}).get("name", "")
        ss["loc_area"] = (place or {}).get("area", "")
        ss["loc_name_auto"] = ss["loc_name"]
        ss["loc_area_auto"] = ss["loc_area"]


def render_new_location_form(locations: list) -> tuple[str, str, float, float]:
    """Form lokasi baru: GPS browser, cari tempat, pin di peta, atau isi manual."""
    ss.setdefault("loc_name", "")
    ss.setdefault("loc_area", "")
    ss.setdefault("loc_lat", DEFAULT_LAT)
    ss.setdefault("loc_lon", DEFAULT_LON)

    c_gps, c_search = st.columns([1, 2], gap="large")

    # 1) Lokasi pengguna dari GPS/browser
    with c_gps:
        st.markdown('<div class="panel-label">GUNAKAN LOKASI SAYA</div>', unsafe_allow_html=True)
        with st.container(key="gps_box"):
            gps = streamlit_geolocation()
        st.caption("Klik ikon, lalu izinkan akses lokasi di browser (perlu HTTPS atau localhost).")
        g_lat, g_lon = gps.get("latitude"), gps.get("longitude")
        if g_lat is not None and g_lon is not None and ss.get("gps_last") != (g_lat, g_lon):
            ss["gps_last"] = (g_lat, g_lon)
            ss["gps_accuracy"] = gps.get("accuracy")
            place = cached_reverse(round(g_lat, 5), round(g_lon, 5)) or {
                "latitude": g_lat, "longitude": g_lon, "name": "", "area": ""}
            queue_place(place, force_name=True, locations=locations)
        if ss.get("gps_accuracy"):
            st.caption(f"Akurasi GPS: ±{float(ss['gps_accuracy']):.0f} m")

    # 2) Cari nama tempat (OpenStreetMap)
    with c_search:
        st.markdown('<div class="panel-label">CARI NAMA TEMPAT</div>', unsafe_allow_html=True)
        q_col, b_col = st.columns([4, 1])
        query = q_col.text_input("Cari tempat", key="loc_query", label_visibility="collapsed",
                                 placeholder="e.g. Kopi Lembah UGM, Perpustakaan Pusat UGM")
        if b_col.button("🔍 Cari", key="loc_search_btn", width="stretch", type="secondary"):
            ss["loc_results"] = cached_search(query)
            ss["loc_searched"] = True
        results = ss.get("loc_results") or []
        if results:
            idx = st.selectbox("Hasil pencarian", range(len(results)), key="loc_result_idx",
                               format_func=lambda i: results[i]["label"][:110])
            if st.button("📌 Pakai tempat ini", key="loc_use_result", type="secondary"):
                queue_place(results[idx], force_name=True, locations=locations)
        elif ss.get("loc_searched"):
            st.caption("Tempat tidak ditemukan. Coba kata kunci lain, atau tandai langsung di peta.")

    # 3) Peta + pin: klik peta untuk memindahkan pin
    lat, lon = float(ss["loc_lat"]), float(ss["loc_lon"])
    st.markdown('<div class="panel-label" style="margin-top:12px">TANDAI DI PETA — klik untuk memindahkan pin</div>',
                unsafe_allow_html=True)
    fmap = folium.Map(location=[lat, lon], zoom_start=17, control_scale=True)
    for loc in locations:
        folium.CircleMarker(
            [loc["latitude"], loc["longitude"]], radius=6, color="#35d5e8", weight=2,
            fill=True, fill_opacity=0.5, tooltip=f"{loc['name']} (sudah terdaftar)",
        ).add_to(fmap)
    folium.Marker([lat, lon], tooltip="Lokasi dipilih",
                  icon=folium.Icon(color="red", icon="wifi", prefix="fa")).add_to(fmap)
    state = st_folium(fmap, height=340, use_container_width=True, key="loc_picker_map",
                      returned_objects=["last_clicked"])
    clicked = (state or {}).get("last_clicked")
    if clicked:
        point = (round(clicked["lat"], 6), round(clicked["lng"], 6))
        if ss.get("map_last_click") != point:
            ss["map_last_click"] = point
            place = cached_reverse(round(point[0], 5), round(point[1], 5)) or {
                "latitude": point[0], "longitude": point[1], "name": "", "area": ""}
            place["latitude"], place["longitude"] = point
            queue_place(place, force_name=False, locations=locations)

    # 4) Isi / edit manual
    n1, n2 = st.columns(2)
    with n1:
        st.text_input("NAMA LOKASI", key="loc_name", placeholder="e.g. Perpustakaan UGM")
    with n2:
        st.text_input("AREA", key="loc_area", placeholder="e.g. Bulaksumur, Sleman")
    g1, g2 = st.columns(2)
    with g1:
        st.number_input("LATITUDE", key="loc_lat", format="%.5f", min_value=-90.0, max_value=90.0)
    with g2:
        st.number_input("LONGITUDE", key="loc_lon", format="%.5f", min_value=-180.0, max_value=180.0)

    nearby = geo.nearest_known_location(ss["loc_lat"], ss["loc_lon"], locations, radius_m=100.0)
    if nearby:
        st.info(f"Ada lokasi terdaftar di dekat sini: **{nearby['name']}**. "
                f"Pilih di dropdown LOCATION agar tidak membuat data ganda.")
    return ss["loc_name"], ss["loc_area"], float(ss["loc_lat"]), float(ss["loc_lon"])


def render_test_stage() -> None:
    """Tahap 1 & 2: Tombol Mulai Test Wi-Fi + animasi Live + info Ping/Server."""
    mode = st.radio(
        "MODE PENGUJIAN",
        ["Live (Browser Speedtest)", "Simulasi (Sementara)"],
        horizontal=True,
        key="test_mode_radio",
    )

    if mode == "Live (Browser Speedtest)":
        payload = browser_speedtest(key=f"speedtest_widget_{ss['speedtest_nonce']}")
        if isinstance(payload, dict) and payload.get("run_id"):
            run_id = payload["run_id"]
            if run_id not in ss["processed_run_ids"]:
                ss["processed_run_ids"].add(run_id)
                network_data = network_scanner.build_network_data_from_browser(payload)
                security_data = security_test.audit_wifi_from_browser(
                    payload.get("security_obs"), wifi_info=network_data
                )
                ai_data = ai_advisor.generate_advice(network_data, security_data)
                ss["last_result"] = {
                    "run_id": run_id,
                    "network": network_data,
                    "security": security_data,
                    "ai": ai_data,
                    "scan_id": None,
                    "saved_location": None,
                }
                ss["overview_stage"] = "result"
                ss.pop("confirm_init_for", None)
                st.rerun()
    else:
        with st.container(border=True):
            st.markdown('<div class="panel-label">MODE SIMULASI DEMO</div>', unsafe_allow_html=True)
            sc_col, btn_col = st.columns([2, 1], vertical_alignment="bottom")
            with sc_col:
                scenario = st.selectbox("PILIH SKENARIO", list(SIMULATION_PAIRS))
            with btn_col:
                run_sim = st.button("▶  Jalankan Simulasi", width="stretch", type="primary")
            st.caption("Mode simulasi memakai data contoh dan hanya bersifat sementara selama masa transisi.")

        if run_sim:
            net_sim, sec_sim = SIMULATION_PAIRS[scenario]
            network_data = network_scanner.run_network_scan(simulate=net_sim)
            security_data = security_test.audit_wifi(simulate=sec_sim)
            ai_data = ai_advisor.generate_advice(network_data, security_data)
            run_id = f"sim-{ss['speedtest_nonce']}-{scenario}"
            ss["speedtest_nonce"] += 1
            ss["last_result"] = {
                "run_id": run_id,
                "network": network_data,
                "security": security_data,
                "ai": ai_data,
                "scan_id": None,
                "saved_location": None,
            }
            ss["overview_stage"] = "result"
            ss.pop("confirm_init_for", None)
            st.rerun()


def render_result_stage(result: dict) -> None:
    """Tahap 3: Tampilkan Network Score, QoS, Network Assessment, dan tombol Upload."""
    net = result["network"]
    sec = result["security"]
    ai = result["ai"]
    saved_loc = result.get("saved_location")

    left, right = st.columns([1.05, 1.95], gap="large")
    with left:
        st.markdown('<div class="panel-label">NETWORK HEALTH</div>', unsafe_allow_html=True)
        if net.get("simulated"):
            subtext = "Hasil simulasi · bukan pengukuran asli"
        elif saved_loc:
            subtext = f"Diukur dari browser · {saved_loc}"
        else:
            subtext = "Diukur langsung dari perangkat Anda"
        render_speed_gauge(net["quality_score"], subtext=subtext)

        banner = f"ISP: <b>{escape(str(net.get('isp', '-')))}</b> · Server: <b>{escape(str(net.get('server_info', '-')))}</b>"
        if net.get("ssid") not in (None, "", "Tidak terhubung", "Simulasi"):
            banner += f"<br/>SSID lokal terdeteksi: <b>{escape(net['ssid'])}</b> ({escape(str(net.get('signal', 'N/A')))})"
        st.markdown(f'<div class="info-banner">{banner}</div>', unsafe_allow_html=True)

    with right:
        render_section_heading("Connection metrics", "Core Quality of Service (QoS) measurements")
        cols = st.columns(2, gap="medium")
        with cols[0]:
            render_metric_card("Download", f"{net['download_mbps']:.1f}", "Mbps", "↓ DOWNLOAD", "↓")
            render_metric_card("Ping / Latency", f"{net['ping_ms']:.0f}", "ms", "◉ RESPONSE", "◌")
        with cols[1]:
            render_metric_card("Upload", f"{net['upload_mbps']:.1f}", "Mbps", "↑ UPLOAD", "↑")
            render_metric_card("Jitter", f"{net['jitter_ms']:.1f}", "ms", "≈ STABILITY", "⌁")

    render_section_heading("Network assessment", "Net neutrality indicators, browser security check, and AI advisor")
    a, b, c = st.columns(3, gap="medium")
    with a:
        if net["is_throttled"]:
            render_status_card("NET NEUTRALITY", "Indikasi throttling",
                               f"Streaming diperkirakan ~{net['video_mbps']:.1f} Mbps, lebih lambat dari trafik umum.",
                               "warning")
        else:
            render_status_card("NET NEUTRALITY", "Tidak ada pembatasan",
                               "Latensi layanan streaming setara dengan layanan umum.", "good")
    with b:
        render_status_card("WI-FI SECURITY", f"{sec['category']} · {sec['score']}/100",
                           sec["findings"][0] if sec["findings"] else "-",
                           CATEGORY_TONE.get(sec["category"], "neutral"))
    with c:
        render_status_card("AI ADVISOR", "Gemini AI" if ai.get("source") == "ai" else "Rule-based",
                           f"{len(ai['suitable_for'])} aktivitas direkomendasikan.", "good")

    render_section_heading("Rekomendasi", "Ringkasan AI Advisor dan detail temuan keamanan")
    st.markdown(f'<div class="panel">{escape(ai["summary"])}</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-label" style="margin-top:14px">COCOK UNTUK</div>', unsafe_allow_html=True)
    render_activity_chips(ai["suitable_for"])

    with st.expander("Detail temuan keamanan"):
        for finding in sec["findings"]:
            st.markdown(f"- {finding}")
    if net.get("throttling_results"):
        with st.expander("Detail pengecekan layanan (net neutrality)"):
            for service, info in net["throttling_results"].items():
                lat = info["latency"]
                lat_str = f"{lat:.1f} ms" if isinstance(lat, (int, float)) else lat
                st.markdown(f"- **{service}** · {info['status']} · {lat_str}")

    st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)
    if result.get("scan_id"):
        st.success(f"Hasil berhasil disimpan ke riwayat komunitas (Scan #{result['scan_id']} · {saved_loc}).")
        if st.button("🔄  Tes Ulang Wi-Fi", type="primary"):
            ss.pop("last_result", None)
            ss.pop("confirm_init_for", None)
            ss["speedtest_nonce"] += 1
            ss["overview_stage"] = "test"
            st.rerun()
    else:
        b1, b2, _ = st.columns([1.2, 1, 1.8])
        with b1:
            if st.button("📤  Upload ke Database", width="stretch", type="primary"):
                ss["overview_stage"] = "confirm_upload"
                st.rerun()
        with b2:
            if st.button("🔄  Tes Ulang", width="stretch", type="secondary"):
                ss.pop("last_result", None)
                ss.pop("confirm_init_for", None)
                ss["speedtest_nonce"] += 1
                ss["overview_stage"] = "test"
                st.rerun()


def render_confirm_upload_stage(result: dict) -> None:
    """Tahap 4: Panel konfirmasi cerdas (GPS, auto-match DB, reverse geocoding, SSID opsional)."""
    pending = ss.pop("loc_pending", None)
    if pending:
        ss.update(pending)

    locations = get_all_locations_summary()
    location_by_name = {loc["name"]: loc for loc in locations}
    init_confirm_defaults(result, locations)

    net = result["network"]
    sec = result["security"]

    render_section_heading(
        "Konfirmasi & Upload ke Database",
        "Lokasi dan ISP diisi otomatis sebisa mungkin. Periksa atau edit sebelum menyimpan.",
    )
    st.markdown(
        f"""
        <div class="meta-strip">
          <div class="meta-pill"><strong>Download:</strong> {net['download_mbps']:.1f} Mbps</div>
          <div class="meta-pill"><strong>Upload:</strong> {net['upload_mbps']:.1f} Mbps</div>
          <div class="meta-pill"><strong>Ping:</strong> {net['ping_ms']:.0f} ms</div>
          <div class="meta-pill"><strong>Skor Keamanan:</strong> {sec['score']}/100 ({escape(sec['category'])})</div>
          <div class="meta-pill"><strong>ISP:</strong> {escape(str(net.get('isp', '-')))}</div>
          <div class="meta-pill"><strong>Server Uji:</strong> {escape(str(net.get('server_info', '-')))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Alamat IP mentah Anda tidak disimpan ke database demi menjaga privasi.")

    loc_col, ssid_col = st.columns(2)
    options = [NEW_LOCATION] + list(location_by_name)
    if ss.get("confirm_choice") not in options:
        ss["confirm_choice"] = NEW_LOCATION

    with loc_col:
        choice = st.selectbox("LOCATION", options, key="confirm_choice")
    with ssid_col:
        ssid_val = st.text_input(
            "WI-FI NAME / SSID (Opsional)",
            key="confirm_ssid",
            placeholder="Kosongkan jika tidak tahu (otomatis: Public Wi-Fi)",
        )

    if choice == NEW_LOCATION:
        new_name, new_area, new_lat, new_lon = render_new_location_form(locations)
    else:
        picked = location_by_name[choice]
        st.info(f"Menggunakan lokasi terdaftar: **{picked['name']}** ({picked['area']}).")

    st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
    save_col, back_col, _ = st.columns([1.2, 1, 1.8])
    with save_col:
        confirm_btn = st.button("✔️  Konfirmasi & Simpan", width="stretch", type="primary")
    with back_col:
        back_btn = st.button("←  Kembali ke Hasil", width="stretch", type="secondary")

    if back_btn:
        ss["overview_stage"] = "result"
        st.rerun()

    if confirm_btn:
        if choice == NEW_LOCATION:
            name = new_name.strip()
            if not name:
                st.warning("Isi nama lokasi terlebih dahulu (atau pilih lokasi yang sudah terdaftar).")
                st.stop()
            existing = find_location_by_name(name)
            if existing:
                location = {**existing, "is_new": False}
            else:
                location = {
                    "location_id": generate_location_id(),
                    "name": name,
                    "area": new_area.strip() or "Yogyakarta",
                    "latitude": new_lat,
                    "longitude": new_lon,
                    "is_new": True,
                }
        else:
            location = {**location_by_name[choice], "is_new": False}

        final_ssid = ssid_val.strip() or (location.get("ssid") if not location["is_new"] else "") or "Public Wi-Fi"
        ai_data = ai_advisor.generate_advice(net, sec, location["name"])
        new_info = None
        if location["is_new"]:
            new_info = {
                "name": location["name"],
                "area": location["area"],
                "ssid": final_ssid,
                "latitude": location["latitude"],
                "longitude": location["longitude"],
            }
        scan_id = save_scan_result(location["location_id"], net, sec, ai_data, new_info)
        result["scan_id"] = scan_id
        result["saved_location"] = location["name"]
        result["ai"] = ai_data
        ss["overview_stage"] = "result"
        st.rerun()


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">⌁</div><div><div class="brand-name">WiFi-Radar ID</div><div class="brand-sub">Public Wi-Fi Intelligence</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div class='panel-label' style='margin-bottom:8px'>NAVIGATION</div>", unsafe_allow_html=True)
    for key_page, label_page in NAV_LABELS.items():
        btn_type = "primary" if ss["active_page"] == key_page else "secondary"
        if st.button(label_page, key=f"nav_{key_page}", width="stretch", type=btn_type):
            ss["active_page"] = key_page
            st.rerun()
    page = ss["active_page"]
    st.markdown("---")
    st.markdown("<div class='panel-label'>SYSTEM STATUS</div>", unsafe_allow_html=True)
    st.caption("● Database terhubung")
    st.caption("● Browser Speedtest (Cloudflare)")
    st.caption("● AI Advisor: Gemini" if ai_advisor.is_ai_configured() else "○ AI Advisor: mode aturan (tanpa API key)")
    st.markdown("---")
    st.caption("WiFi-Radar ID · Project Prototype")


# ---------- Pages ----------
if page == "Overview":
    st.markdown(
        '<div class="topline"><div class="eyebrow">NETWORK INTELLIGENCE PLATFORM</div><div class="page-title">Wi-Fi Overview</div><div class="page-desc">Ukur kecepatan dan keamanan Wi-Fi publik langsung dari browser Anda, lalu bagikan ke peta komunitas.</div></div>',
        unsafe_allow_html=True,
    )

    stage = ss.get("overview_stage", "test")
    result = ss.get("last_result")

    if stage == "confirm_upload" and result:
        render_confirm_upload_stage(result)
    elif stage == "result" and result:
        render_result_stage(result)
    else:
        render_test_stage()

elif page == "Community Map":
    st.markdown(
        '<div class="topline"><div class="eyebrow">COMMUNITY NETWORK DATA</div><div class="page-title">Community Map</div><div class="page-desc">Explore public Wi-Fi quality and security reports shared by the community.</div></div>',
        unsafe_allow_html=True,
    )

    locations = get_all_locations_summary()
    categories = ["Aman", "Rawan", "Bahaya"]
    selected = st.multiselect("FILTER KATEGORI KEAMANAN", categories, default=categories)
    filtered = [loc for loc in locations if loc["category"] in selected]

    scanned = [loc for loc in filtered if loc["download_mbps"] is not None]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lokasi", len(filtered))
    m2.metric("Rata-rata Download",
              f"{sum(l['download_mbps'] for l in scanned) / len(scanned):.1f} Mbps" if scanned else "--")
    m3.metric("Lokasi Aman", sum(1 for l in filtered if l["category"] == "Aman"))
    m4.metric("Indikasi Throttling", sum(1 for l in filtered if l["is_throttled"]))

    render_section_heading(
        "Peta komunitas",
        "Arahkan kursor untuk ringkasan cepat (Download, Upload, Cocok untuk AI). Klik titik atau pilih di bawah untuk detail.",
    )
    clicked_loc_id = render_community_map(filtered)
    if clicked_loc_id:
        ss["map_selected_loc_id"] = clicked_loc_id
        ss["show_map_detail"] = True

    if filtered:
        loc_map = {loc["location_id"]: loc for loc in filtered}
        loc_ids = list(loc_map)
        if ss.get("map_selected_loc_id") not in loc_map:
            ss["map_selected_loc_id"] = loc_ids[0]

        sel_col, btn_col = st.columns([3, 1], vertical_alignment="bottom")
        with sel_col:
            picked_id = st.selectbox(
                "PILIH LOKASI UNTUK MELIHAT DETAIL",
                loc_ids,
                key="map_selected_loc_id",
                format_func=lambda lid: f"{loc_map[lid]['name']} · {loc_map[lid]['category']} ({loc_map[lid]['score']}/100)",
            )
        with btn_col:
            if st.button("🔍  Lihat Detail", width="stretch", type="primary"):
                ss["show_map_detail"] = True

        if ss.get("show_map_detail") and picked_id in loc_map:
            loc = loc_map[picked_id]
            net_score = network_scanner.calculate_quality_score(
                loc["download_mbps"] or 0.0,
                loc["upload_mbps"] or 0.0,
                loc["ping_ms"] or 0.0,
                loc["jitter_ms"] or 0.0,
                loc["is_throttled"],
            )
            with st.container(border=True):
                h_col, close_col = st.columns([4, 1])
                with h_col:
                    st.markdown(f"### {escape(loc['name'])}")
                    st.caption(
                        f"{loc['area']} · SSID: {loc['ssid']} · ISP: {loc.get('isp', '-')} · "
                        f"Server Uji: {loc.get('server_info', '-')} · Scan terakhir: {loc['timestamp']}"
                    )
                with close_col:
                    if st.button("Tutup Detail", key="close_map_detail", width="stretch", type="secondary"):
                        ss["show_map_detail"] = False
                        st.rerun()

                r1c1, r1c2, r1c3 = st.columns(3)
                r1c1.metric("Network Score", f"{net_score} / 100")
                r1c2.metric("Keamanan", f"{loc['score']}/100 ({loc['category']})")
                r1c3.metric("Throttling", "Ya" if loc["is_throttled"] else "Tidak")

                r2c1, r2c2, r2c3 = st.columns(3)
                r2c1.metric("Download", f"{loc['download_mbps']:.1f} Mbps")
                r2c2.metric("Upload", f"{loc['upload_mbps']:.1f} Mbps")
                r2c3.metric("Ping / Jitter", f"{loc['ping_ms']:.0f} / {loc['jitter_ms']:.1f} ms")

                st.markdown("**Ringkasan AI Advisor:**")
                st.write(loc["summary"])
                st.markdown('<div class="panel-label" style="margin-top:8px">COCOK UNTUK</div>', unsafe_allow_html=True)
                render_activity_chips(loc["suitable_for"])
                if loc["findings"]:
                    st.markdown("**Temuan Keamanan:** " + " · ".join(loc["findings"]))

                loc_history = get_location_scan_history(loc["location_id"], limit=10)
                if loc_history:
                    st.markdown('<div class="panel-label" style="margin-top:14px;margin-bottom:8px">RIWAYAT SCAN DI TITIK INI</div>',
                                unsafe_allow_html=True)
                    render_history_table(loc_history)

    render_section_heading("Kecepatan vs keamanan", "Bandingkan performa dan keamanan antar lokasi")
    render_speed_security_chart(filtered)

else:
    st.markdown(
        '<div class="topline"><div class="eyebrow">YOUR NETWORK RECORDS</div><div class="page-title">Scan History</div><div class="page-desc">Review previous network checks and compare connection quality over time.</div></div>',
        unsafe_allow_html=True,
    )

    f1, f2 = st.columns([2, 1])
    history = get_scan_history(limit=500)
    with f1:
        names = sorted({h["name"] for h in history})
        location_filter = st.selectbox("LOKASI", ["Semua lokasi"] + names)
    with f2:
        limit = st.slider("JUMLAH DATA", min_value=10, max_value=500, value=50, step=10)

    if location_filter != "Semua lokasi":
        history = [h for h in history if h["name"] == location_filter]
    history = history[:limit]

    table = render_history_table(history)
    if not table.empty:
        st.download_button(
            "⬇  Unduh CSV",
            table.to_csv(index=False).encode("utf-8"),
            file_name="wifi_radar_scan_history.csv",
            mime="text/csv",
        )

st.markdown('<div class="footer">WI-FI RADAR ID · COMMUNITY-DRIVEN PUBLIC WI-FI MONITORING</div>', unsafe_allow_html=True)
