import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
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

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione (TUTTE LE VARIABILI PRESENTI)
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'show_cam' not in st.session_state: st.session_state.show_cam = False
if 'foto_tipo' not in st.session_state: st.session_state.foto_tipo = None
if 'gallery' not in st.session_state: st.session_state.gallery = {}
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = True
if 'sub_guasto' not in st.session_state: st.session_state.sub_guasto = None
if 'foto_salvata' not in st.session_state: st.session_state.foto_salvata = None

# --- 2. SUPER CSS IPHONE 17 PRO MAX (PULIZIA TOTALE + GRID PERFETTA) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');
    
    /* ELIMINA OGNI TRACCIA DI STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    .stApp {{ background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }}

    /* DYNAMIC ISLAND PILL */
    .ios-pill-container {{
        background: rgba(255, 255, 255, 0.05); border-radius: 50px;
        padding: 15px 35px; border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 10px auto 40px auto; max-width: 500px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .island-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #ffffff; margin: 0; }}

    /* GRIGLIA APP iPHONE (CENTRATURA) */
    [data-testid="stHorizontalBlock"] {{
        max-width: 400px !important; margin: 0 auto !important; padding: 0 !important;
    }}
    
    [data-testid="column"] {{
        display: flex !important; flex-direction: column !important;
        align-items: center !important; justify-content: center !important;
        margin-bottom: 25px !important;
    }}

    /* ICONA APP (SQUIRCLE) */
    .stButton>button {{
        border: none !important; border-radius: 20px !important;
        width: 72px !important; height: 72px !important;
        background: #1c1c1e !important; color: white !important;
        font-size: 2.2em !important; padding: 0 !important;
        margin: 0 auto !important; box-shadow: 0 10px 20px rgba(0,0,0,0.4) !important;
        transition: transform 0.1s !important;
    }}
    
    /* COLORI iPHONE ORIGINALI */
    div[data-testid="column"]:nth-child(1) .stButton>button {{ background: linear-gradient(135deg, #FF9500, #FFCC00) !important; }}
    div[data-testid="column"]:nth-child(2) .stButton>button {{ background: linear-gradient(135deg, #FF3B30, #FF5E57) !important; }}
    div[data-testid="column"]:nth-child(3) .stButton>button {{ background: #444446 !important; }}
    div[data-testid="column"]:nth-child(4) .stButton>button {{ background: linear-gradient(135deg, #34C759, #4CD964) !important; }}
    .dock-icon .stButton>button {{ background: rgba(255,255,255,0.15) !important; width: 62px !important; height: 62px !important; }}

    /* LABEL TESTO SOTTO ICONA */
    .app-label {{
        color: white; font-size: 11px; margin-top: 6px; text-align: center;
        font-weight: 400; width: 80px; white-space: nowrap;
    }}

    /* THE DOCK */
    .ios-dock {{
        background: rgba(44, 44, 46, 0.4); backdrop-filter: blur(20px);
        border-radius: 30px; padding: 15px; max-width: 340px; margin: 40px auto 20px auto;
        display: flex; justify-content: space-around; border: 1px solid rgba(255,255,255,0.1);
    }}

    /* FINESTRE INTERNE */
    .ios-card {{ background: #1c1c1e; border-radius: 35px; padding: 25px; color: white; border: 1px solid #2c2c2e; margin: 0 auto; max-width: 600px; }}
    .status-card-inner {{ background: #000; border-radius: 20px; padding: 15px; text-align: center; margin-bottom: 15px; border: 1px solid #2c2c2e; }}
    .status-val {{ font-size: 26px; font-weight: 700; color: #0a84ff; }}
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
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((450, 450)) # Compressione salva-database
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=45, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nDisponiamo di carrozzeria convenzionata Aldo Dal Maso & C. Snc (Camisano Vicentino).\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text" style="color:gray;">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME PAGE (iPHONE GRID) ---
if st.session_state.pagina == "home":
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="i1"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="i2"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="i3"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Sinistri</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="i4"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Flotta</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="ios-dock">', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1:
        st.markdown('<div class="dock-icon">', unsafe_allow_html=True)
        if st.button("👑", key="d1"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p></div>', unsafe_allow_html=True)
    with d2:
        st.markdown('<div class="dock-icon">', unsafe_allow_html=True)
        if st.button("🚪", key="d2"): st.session_state.clear(); st.rerun()
        st.markdown('<p class="app-label">Esci</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. PAGINE INTERNE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='status-card-inner'><small>TAGLIANDO A</small><br><div class='status-val'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='status-card-inner'><small>GOMME A</small><br><div class='status-val'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Indietro"): 
        if st.session_state.sub_guasto: st.session_state.sub_guasto = None
        else: st.session_state.pagina = "home"
        st.rerun()
    if not st.session_state.sub_guasto:
        for g in ["PASTIGLIE FRENI", "GOMME", "SPIA MOTORE", "TAGLIANDO", "ALTRO"]:
            if st.button(g): st.session_state.sub_guasto = g; st.rerun()
    else:
        tipo = st.session_state.sub_guasto
        t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
        config = {"PASTIGLIE FRENI": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "GOMME": {"Gomme1":"GOMMA 1", "Gomme2":"GOMMA 2", "Targa":"TARGA", "Libretto":"LIBRETTO", "KM":"KM"},
                  "SPIA MOTORE": {"Spia":"SPIA", "KM":"KM", "Libretto":"LIBRETTO", "Targa":"TARGA"},
                  "TAGLIANDO": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "ALTRO": {"Targa":"TARGA", "KM":"KM", "E1":"FOTO 1", "E2":"FOTO 2"}}
        for k, v in config[tipo].items():
            if k not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
            else: st.success(f"✅ {v} OK")
        if st.session_state.show_cam:
            if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
            fi = st.camera_input("SCATTA")
            if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA REPORT"):
            conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": tipo, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto_Gomme": st.session_state.gallery.get("Gomme1",""), "Foto_Cruscotto": st.session_state.gallery.get("Spia",""), "Foto_KM": st.session_state.gallery.get("KM",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
            st.session_state.gallery={}; st.session_state.sub_guasto=None; st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    # Logica Admin (Targhe, Driver, Email)
    df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict.get("SIXT VERONA",""), targa, dg['KM_Segnalazione'], dg['Descrizione'], {}): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
