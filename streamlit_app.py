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
st.set_page_config(page_title="GOPRESSA EXECUTIVE", layout="wide", initial_sidebar_state="collapsed")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. CSS EXECUTIVE DESIGN (PROFESSIONALE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* PULIZIA TOTALE STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    /* SFONDO ARDESIA PROFESSIONALE */
    .stApp {{ 
        background-color: #11141a; 
        color: #e1e1e6; 
        font-family: 'Inter', sans-serif; 
    }}

    /* HEADER TITANIUM PILL */
    .exec-header {{
        background: linear-gradient(90deg, #1c1f26 0%, #2d313d 100%);
        border-radius: 50px;
        padding: 15px 40px;
        border: 1px solid #3d4251;
        margin: 20px auto 40px auto;
        max-width: 700px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }}
    .exec-title {{ 
        font-size: 2.2em !important; 
        font-weight: 700; 
        letter-spacing: 2px; 
        color: #ffffff;
        margin: 0;
    }}
    .exec-status {{ color: #0a84ff; font-size: 0.9em; font-weight: 500; text-transform: uppercase; margin-top: 5px; }}

    /* GRIGLIA DASHBOARD */
    [data-testid="stHorizontalBlock"] {{ max-width: 850px !important; margin: 0 auto !important; }}
    
    /* BOTTONI DASHBOARD STYLE */
    .stButton>button {{
        background: #1c1f26 !important;
        color: #ffffff !important;
        border: 1px solid #3d4251 !important;
        border-radius: 20px !important;
        height: 140px !important;
        width: 100% !important;
        font-weight: 600 !important;
        font-size: 1.1em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
    }}
    .stButton>button:hover {{
        border-color: #0a84ff !important;
        background: #252932 !important;
        transform: translateY(-3px);
    }}

    /* CARD INTERNE GESTIONALI */
    .inner-card {{
        background: #1c1f26;
        border-radius: 25px;
        padding: 30px;
        border: 1px solid #3d4251;
        margin: 0 auto;
        max-width: 800px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.3);
    }}
    
    /* WIDGETS */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div {{
        background-color: #11141a !important;
        border: 1px solid #3d4251 !important;
        border-radius: 12px !important;
        color: white !important;
    }}
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
        req = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "User", "Altro"]
        }
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280)) # ALTA QUALITÀ HD
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - ACTIVITY LOG", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"AUTORIZZAZIONE INTERVENTO - {targa}"
        corpo = f"Buongiorno,\n\nveicolo {targa} - KM {km}.\nIntervento: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="exec-header"><h1 class="exec-title">GOPRESSA</h1><p class="exec-status">Auth Module</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA SISTEMA"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER PILL ---
st.markdown(f'<div class="exec-header"><h1 class="exec-title">GOPRESSA</h1><p class="exec-status">{st.session_state.user} | {ora_it} | ONLINE</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME PAGE (DASHBOARD) ---
if st.session_state.pagina == "home":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️\nMANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
        if st.button("💥\nDANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with col2:
        if st.button("🚨\nGUASTI MEZZO"): st.session_state.pagina = "guasto"; st.rerun()
        if st.button("📋\nAREA ADMIN"): st.session_state.pagina = "admin"; st.rerun()
    
    st.divider()
    if st.button("🚪 CHIUDI SESSIONE"): st.session_state.clear(); st.rerun()

# --- 7. PAGINE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ TORNA AL MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ TORNA AL MENU"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("MEZZO", lista_mezzi); km_g = st.number_input("KM:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("Note:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("FOTO"); 
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        sel = [k for k,v in {"Ant":p1,"Post":p2,"Freni":p3,"Tagl":p4,"Spia":p5}.items() if v]
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True)); st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    # Logica Admin (Targhe, Driver, Email)
    df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict.get("SIXT VERONA",""), targa, dg['KM_Segnalazione'], dg['Descrizione'], {}): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.divider(); ts = st.selectbox("STORICO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == ts].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
    st.markdown("</div>", unsafe_allow_html=True)
