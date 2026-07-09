import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import base64
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- 1. CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA PRO MAX", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione sessione
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        st.session_state[key] = "home" if key == 'pagina' else (True if key == 'is_admin' else ({} if key == 'gallery' else None))

# --- 2. CSS IPHONE REAL GRID (TESTO SOTTO ICONA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* PULIZIA TOTALE */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }

    .stApp {
        background: linear-gradient(180deg, #1d72f2 0%, #104fa1 100%);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* CENTRATURA E GRIGLIA */
    [data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* ICONA APP (QUADRATA ARROTONDATA) */
    .stButton>button {
        border: none !important;
        border-radius: 20px !important;
        width: 72px !important;
        height: 72px !important;
        padding: 0 !important;
        margin: 0 auto !important;
        font-size: 2.2em !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        transition: transform 0.2s !important;
    }
    
    .stButton>button:hover { transform: scale(1.1); }
    
    /* COLORI SPECIFICI ICONE */
    /* Manutenzione - Arancio */
    div[data-testid="column"]:nth-child(1) .stButton>button { background: linear-gradient(135deg, #FF9500, #FFCC00) !important; }
    /* Guasti - Rosso */
    div[data-testid="column"]:nth-child(2) .stButton>button { background: linear-gradient(135deg, #FF3B30, #FF5E57) !important; }
    /* Danni - Nero */
    div[data-testid="column"]:nth-child(3) .stButton>button { background: #1C1C1E !important; }
    /* Stato - Verde */
    div[data-testid="column"]:nth-child(4) .stButton>button { background: linear-gradient(135deg, #34C759, #4CD964) !important; }
    /* Admin - Blu */
    .admin-col .stButton>button { background: linear-gradient(135deg, #007AFF, #00BFFF) !important; }
    /* Logout - Grigio */
    .logout-col .stButton>button { background: #8E8E93 !important; }

    /* LABEL SOTTO L'ICONA */
    .app-label {
        color: white;
        font-size: 11px;
        margin-top: 5px;
        font-weight: 500;
        text-align: center;
        width: 80px;
        line-height: 1.2;
        margin-bottom: 25px;
    }

    /* HEADER */
    .ios-header {
        text-align: center;
        color: white;
        font-size: 3em;
        font-weight: 800;
        margin: 40px 0;
        letter-spacing: -1px;
    }
    
    .ios-card {
        background: rgba(255, 255, 255, 0.98);
        border-radius: 30px;
        padding: 25px;
        color: black;
        margin: 10px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Targa: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno, veicolo {targa} - KM {km}.\nRichiesta: {tipo_guasto}."
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown('<h1 class="ios-header">GOPRESSA</h1>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. CARICAMENTO DATI ---
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME PAGE (IPHONE GRID REAL) ---
if st.session_state.pagina == "home":
    st.markdown(f'<p style="text-align:center; color:white; margin-top:20px;">{datetime.now().strftime("%H:%M")} | {st.session_state.user}</p>', unsafe_allow_html=True)
    st.markdown('<h1 class="ios-header">GOPRESSA</h1>', unsafe_allow_html=True)
    
    # RIGA 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.button("🛠️", key="i1", on_click=lambda: setattr(st.session_state, 'pagina', 'manutenzione'))
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        st.button("🚨", key="i2", on_click=lambda: setattr(st.session_state, 'pagina', 'guasto'))
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        st.button("💥", key="i3", on_click=lambda: setattr(st.session_state, 'pagina', 'danno'))
        st.markdown('<p class="app-label">Danni Driver</p>', unsafe_allow_html=True)
    with c4:
        st.button("📊", key="i4", on_click=lambda: setattr(st.session_state, 'pagina', 'status'))
        st.markdown('<p class="app-label">Stato Flotta</p>', unsafe_allow_html=True)

    # DOCK (In basso)
    st.write("<br><br><br><br>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown('<div class="admin-col">', unsafe_allow_html=True)
        st.button("👑", key="i5", on_click=lambda: setattr(st.session_state, 'pagina', 'admin'))
        st.markdown('<p class="app-label">Admin</p></div>', unsafe_allow_html=True)
    with d4:
        st.markdown('<div class="logout-col">', unsafe_allow_html=True)
        st.button("🚪", key="i6", on_click=lambda: st.session_state.clear())
        st.markdown('<p class="app-label">Logout</p></div>', unsafe_allow_html=True)

# --- LOGICA PAGINE INTERNE (BIANCHE STILE IOS) ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("MEZZO", lista_mezzi)
    # ... resto del codice manutenzione ...
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("🚛 MEZZO", lista_mezzi)
    # ... resto del codice guasti con le 6 foto ...
    st.markdown("</div>", unsafe_allow_html=True)

# ... (seguono le altre pagine: danno, status, admin con lo stesso stile .ios-card)
