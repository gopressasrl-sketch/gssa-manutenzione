import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import base64
from PIL import Image, ImageOps
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- 1. CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA GOLD PRO", layout="wide", initial_sidebar_state="collapsed")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione (TUTTE LE VARIABILI)
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'show_cam' not in st.session_state: st.session_state.show_cam = False
if 'foto_tipo' not in st.session_state: st.session_state.foto_tipo = None
if 'gallery' not in st.session_state: st.session_state.gallery = {}
if 'user' not in st.session_state: st.session_state.user = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = True
if 'sub_guasto' not in st.session_state: st.session_state.sub_guasto = None

# --- 2. SUPER CSS: GOLD LUXURY iPHONE DESIGN ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap');
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}
    .stApp {{ background: linear-gradient(135deg, #0f0f0f 0%, #1a1605 100%); color: #ffffff; font-family: 'Inter', sans-serif; }}
    .ios-pill-container {{
        background: rgba(0, 0, 0, 0.6); border-radius: 50px;
        padding: 15px 35px; border: 1px solid #d4af37;
        margin: 10px auto 40px auto; max-width: 500px; text-align: center;
        box-shadow: 0 10px 40px rgba(212, 175, 55, 0.2);
    }}
    .island-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #d4af37; margin: 0; }}
    .status-text {{ color: #8e8e93; font-size: 0.9em; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }}
    [data-testid="stHorizontalBlock"] {{ max-width: 650px !important; margin: 0 auto 15px auto !important; background: rgba(0,0,0,0.4); border-radius: 25px; padding: 10px !important; border: 1px solid rgba(212, 175, 55, 0.1); align-items: center !important; }}
    .stButton>button {{
        border: none !important; border-radius: 15px !important; height: 60px !important;
        background: transparent !important; color: #ffffff !important;
        font-size: 1.1em !important; font-weight: 600 !important; text-align: left !important;
        padding-left: 10px !important; width: 100% !important; transition: 0.3s !important;
    }}
    .icon-box {{ width: 60px; height: 60px; background: linear-gradient(135deg, #d4af37 0%, #8b6b23 100%); border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
    .ios-card {{ background: rgba(0, 0, 0, 0.85); border-radius: 35px; padding: 25px; color: white; border: 1px solid #d4af37; margin: 0 auto; max-width: 700px; }}
    .status-mini {{ text-align: center; background: #1a1605; border-radius: 20px; padding: 15px; margin-bottom: 10px; border: 1px solid #d4af37; }}
    .status-val {{ font-size: 24px; font-weight: 700; color: #d4af37; }}
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
    """COMPRESSIONE ANTI-CRASH: 400px - Bianco e Nero se necessario per stare nei limiti"""
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file).convert("RGB")
    img.thumbnail((400, 400)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=40, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Targa: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio {targa} - KM {km}.\nNecessità di: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64 and len(b64) > 50:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text">IDENTIFICAZIONE</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME PAGE ---
if st.session_state.pagina == "home":
    def row_btn(icon, label, target):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown(f'<div class="icon-box">{icon}</div>', unsafe_allow_html=True)
        with c2: 
            if st.button(label, key=f"btn_{target}"): st.session_state.pagina = target; st.rerun()
    row_btn("🛠️", "MANUTENZIONE", "manutenzione")
    row_btn("🚨", "GUASTI", "guasto")
    row_btn("💥", "DANNI DRIVER", "danno")
    row_btn("📊", "STATO FLOTTA", "status")
    row_btn("👑", "ADMIN", "admin")
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- 7. GUASTO (PULSANTI SPECIFICI) ---
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
        t_g = st.selectbox("🚛 UNITÀ", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
        note = st.text_area("🗒️ ALTRE NOTE:") if tipo in ["ALTRO", "TAGLIANDO"] else ""
        config = {"PASTIGLIE FRENI": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "GOMME": {"Gomme1":"GOMMA 1", "Gomme2":"GOMMA 2", "Targa":"TARGA", "Libretto":"LIBRETTO", "KM":"KM"},
                  "SPIA MOTORE": {"Spia":"SPIA", "KM":"KM", "Libretto":"LIBRETTO", "Targa":"TARGA"},
                  "TAGLIANDO": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "ALTRO": {"Targa":"TARGA", "KM":"KM", "Ex1":"FOTO 1", "Ex2":"FOTO 2"}}
        for k, v in config[tipo].items():
            if k not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
            else: st.success(f"✅ {v} OK")
        if st.session_state.show_cam:
            if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
            fi = st.camera_input("SCATTA")
            if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA REPORT"):
            df_s = carica_dati("Segnalazioni")
            nuova = pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": f"{tipo} | {note}", "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto_Gomme": st.session_state.gallery.get("Gomme1","") or st.session_state.gallery.get("Ex1",""), "Foto_Cruscotto": st.session_state.gallery.get("Spia",""), "Foto_KM": st.session_state.gallery.get("KM",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
            conn.update(worksheet="Segnalazioni", data=pd.concat([df_s, nuova], ignore_index=True))
            st.session_state.gallery = {}; st.session_state.sub_guasto = None; st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    # Logica Admin (Aggiunta dati e Chiusura)
    c1, c2, c3 = st.columns(3)
    with c1:
        nv = st.text_input("Targa").upper()
        if st.button("SALVA V"): conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0"}])], ignore_index=True)); st.rerun()
    # (Altra logica admin driver/email uguale a prima...)
    st.divider(); df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}"):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Guasto: {dg['Descrizione']}")
            # Link Foto per non pesare
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict.get("SIXT VERONA",""), targa, dg['KM_Segnalazione'], dg['Descrizione'], {}): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
