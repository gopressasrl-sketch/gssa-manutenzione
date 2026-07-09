import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
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

# Ora esatta Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
for key in ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. SUPER CSS: IPHONE PILL DESIGN ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');
    
    /* PULIZIA TOTALE */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    .stApp {{ background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }}

    /* IL DESIGN A "PILLOLA" PER IL TITOLO (COME TUA IMMAGINE) */
    .ios-pill-container {{
        background: rgba(255, 255, 255, 0.05);
        border-radius: 50px;
        padding: 20px 40px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 20px auto 40px auto;
        max-width: 600px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .main-title {{ 
        font-family: 'Orbitron', sans-serif; 
        font-size: 2.5em !important; 
        font-weight: 900; 
        letter-spacing: 5px; 
        color: #ffffff;
        margin: 0;
    }}
    .status-text {{
        color: #8e8e93;
        font-size: 0.9em;
        margin-top: 5px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* GRIGLIA ICONE */
    [data-testid="stHorizontalBlock"] {{ max-width: 450px !important; margin: 0 auto !important; }}
    [data-testid="column"] {{ display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; }}

    .stButton>button {{
        border: none !important; border-radius: 18px !important;
        width: 70px !important; height: 70px !important;
        background: #1c1c1e !important; color: white !important;
        font-size: 2em !important; box-shadow: 0 4px 10px rgba(0,0,0,0.5) !important;
        transition: 0.2s !important;
    }}
    .stButton>button:active {{ transform: scale(0.9); }}

    .app-label {{ color: white; font-size: 11px; margin-top: 6px; margin-bottom: 25px; font-weight: 400; }}

    /* CARD INTERNE BIANCHE */
    .ios-card {{ background: white; border-radius: 30px; padding: 25px; color: black; margin: 10px; }}
    .status-card {{ text-align: center; background: #f2f2f7; border-radius: 20px; padding: 15px; margin-bottom: 10px; }}
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
        req = {{
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "User", "Altro"]
        }}
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno, veicolo {targa} - KM {km}.\nRichiesta: {tipo_guasto}."
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{{label}}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {{"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}}
if not st.session_state.user:
    st.markdown(f'<div class="ios-pill-container"><h1 class="main-title">GOPRESSA</h1><p class="status-text">Identificazione richiesta</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER PILL ---
st.markdown(f'<div class="ios-pill-container"><h1 class="main-title">GOPRESSA</h1><p class="status-text">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {{"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME ---
if st.session_state.pagina == "home":
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="h1"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="h2"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="h3"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Danni Driver</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="h4"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Flotta</p>', unsafe_allow_html=True)

    st.write("<br><br>", unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        if st.button("👑", key="h5"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p>', unsafe_allow_html=True)
    with d4:
        if st.button("🚪", key="h6"): st.session_state.clear(); st.rerun()
        st.markdown('<p class="app-label">Logout</p>', unsafe_allow_html=True)

# --- 7. PAGINE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("🗒️ NOTE:")
    f_keys = {{"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {{v}}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {{v}} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA"); 
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        sel = [k for k,v in {{"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}}.items() if v]
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
        st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 {{targa}}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            if st.button(f"📧 INVIA MAIL {{targa}}"):
                if invia_email_ufficiale(rub_dict.get("SIXT VERONA",""), targa, dg['KM_Segnalazione'], dg['Descrizione'], {{ "Gen": dg['Foto'], "Gomme": dg['Foto_Gomme'], "Spia": dg['Foto_Cruscotto'], "KM": dg['Foto_KM'], "Targa": dg['Foto_Targa'], "Libretto": dg['Foto_Libretto'] }}): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {{targa}}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
