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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="GOPRESSA GOLD", layout="wide", initial_sidebar_state="collapsed")
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'gallery' not in st.session_state: st.session_state.gallery = {}
if 'user' not in st.session_state: st.session_state.user = None
if 'sub_guasto' not in st.session_state: st.session_state.sub_guasto = None
if 'show_cam' not in st.session_state: st.session_state.show_cam = False

# --- 2. DESIGN GOLD LUXURY iPHONE ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Inter:wght@300;400;600&display=swap');
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu {{ display: none !important; }}
    .stApp {{ background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }}
    .ios-pill {{
        background: rgba(255, 255, 255, 0.05); border-radius: 50px; padding: 15px;
        border: 1px solid #d4af37; margin: 10px auto 30px auto; max-width: 500px; text-align: center;
    }}
    .main-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; color: #d4af37; margin: 0; }}
    [data-testid="stHorizontalBlock"] {{ max-width: 500px !important; margin: 0 auto 12px auto !important; align-items: center !important; }}
    .icon-box {{ width: 55px; height: 55px; background: linear-gradient(135deg, #d4af37 0%, #8b6b23 100%); border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; }}
    .stButton>button {{ border: none !important; border-radius: 15px !important; height: 60px !important; background: #1c1c1e !important; color: white !important; font-size: 1.1em !important; font-weight: 600 !important; text-align: left !important; padding-left: 20px !important; width: 100% !important; }}
    .ios-card {{ background: #1c1c1e; border-radius: 30px; padding: 20px; color: white; border: 1px solid #d4af37; margin: 0 auto; max-width: 600px; }}
    .status-mini {{ text-align: center; background: #000; border-radius: 20px; padding: 15px; margin-bottom: 10px; border: 1px solid #d4af37; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNZIONI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    """COMPRESSIONE ANTI-CRASH (FOTO LEGGERISSIME)"""
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((400, 400)) # Piccola e veloce
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=35, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

def invia_email_ufficiale(destinatario, targa, km, tipo, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"AUTORIZZAZIONE INTERVENTO - {targa}"
        corpo = f"Buongiorno, veicolo {targa} - KM {km}.\nNecessità di procedere con {tipo}.\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"')
                msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
        s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown('<div class="ios-pill"><h1 class="main-title">GOPRESSA</h1></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="ios-pill"><h1 class="main-title">GOPRESSA</h1><p style="color:gray;">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME ---
if st.session_state.pagina == "home":
    def row(icon, label, target):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown(f'<div class="icon-box">{icon}</div>', unsafe_allow_html=True)
        with c2: 
            if st.button(label, key=f"b_{target}"): st.session_state.pagina = target; st.rerun()
    row("🛠️", "MANUTENZIONE", "manutenzione")
    row("🚨", "GUASTI", "guasto")
    row("💥", "DANNI DRIVER", "danno")
    row("📊", "STATO FLOTTA", "status")
    row("👑", "ADMIN", "admin")
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- 7. PAGINE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    km = st.number_input("KM ATTUALI", value=0)
    if st.button("💾 SALVA"):
        st.success("OK"); st.session_state.pagina = "home"; st.rerun()
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
        t_g = st.selectbox("MEZZO", lista_mezzi); km_g = st.number_input("KM:", value=0)
        note = st.text_area("NOTE:") if tipo in ["ALTRO", "TAGLIANDO"] else ""
        config = {"PASTIGLIE FRENI": ["TARGA", "KM", "SPIA", "LIBRETTO"], "GOMME": ["GOMMA 1", "GOMMA 2", "TARGA", "LIBRETTO", "KM"], "SPIA MOTORE": ["SPIA", "KM", "LIBRETTO", "TARGA"], "TAGLIANDO": ["TARGA", "KM", "SPIA", "LIBRETTO"], "ALTRO": ["TARGA", "KM", "F1", "F2"]}
        for v in config[tipo]:
            if v not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.foto_tipo = v; st.session_state.show_cam = True; st.rerun()
            else: st.success(f"✅ {v} OK")
        if st.session_state.show_cam:
            fi = st.camera_input("FOTO")
            if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam = False; st.rerun()
        if st.button("🚀 INVIA"):
            conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa":t_g, "Stato":"APERTO", "Descrizione":tipo, "KM_Segnalazione":str(km_g), "Data_Segnalazione":datetime.now().strftime("%d/%m/%Y"), "Operatore":st.session_state.user}])], ignore_index=True))
            st.session_state.gallery = {}; st.session_state.sub_guasto = None; st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    df_s = carica_dati("Segnalazioni")
    for t in df_s[df_s['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 {t}"):
            if st.button(f"📧 INVIA MAIL {t}"): st.success("OK")
            if st.button(f"✅ CHIUDI {t}"):
                df_s.loc[df_s['Targa'] == t, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_s); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
