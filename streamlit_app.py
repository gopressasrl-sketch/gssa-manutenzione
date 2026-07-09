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
st.set_page_config(page_title="GOPRESSA iOS", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione variabili
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'foto_salvata', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        else: st.session_state[key] = None

# --- 2. CSS STILE IPHONE HOME SCREEN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* PULIZIA TOTALE STREAMLIT */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }

    /* SFONDO BLU IPHONE */
    .stApp {
        background: linear-gradient(180deg, #1d72f2 0%, #104fa1 100%);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* HEADER (OROLOGIO E UTENTE) */
    .ios-status-bar {
        text-align: center;
        color: white;
        padding: 20px 0;
        font-weight: 600;
        font-size: 1.2em;
    }
    
    .ios-title {
        text-align: center;
        color: white;
        font-size: 3em;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 40px;
    }

    /* GRIGLIA ICONE */
    .stButton>button {
        border: none !important;
        border-radius: 22px !important;
        width: 80px !important;
        height: 80px !important;
        margin: 0 auto !important;
        display: block !important;
        font-size: 2em !important;
        transition: transform 0.2s !important;
        box-shadow: 0 8px 15px rgba(0,0,0,0.2) !important;
    }
    
    .stButton>button:hover { transform: scale(1.1); }
    
    /* COLORI DELLE ICONE (APP) */
    /* Manutenzione (Arancione) */
    div[data-testid="column"]:nth-child(1) .stButton>button { background: linear-gradient(135deg, #ff9f0a, #ffb340) !important; }
    /* Guasti (Rosso) */
    div[data-testid="column"]:nth-child(2) .stButton>button { background: linear-gradient(135deg, #ff3b30, #ff6b63) !important; }
    /* Danni (Nero) */
    div[data-testid="column"]:nth-child(3) .stButton>button { background: #1c1c1e !important; }
    /* Stato Flotta (Verde) */
    div[data-testid="column"]:nth-child(4) .stButton>button { background: linear-gradient(135deg, #34c759, #66d98a) !important; }
    
    /* LABEL SOTTO LE ICONE */
    .app-label {
        color: white;
        text-align: center;
        font-size: 0.75em;
        margin-top: 5px;
        font-weight: 500;
        margin-bottom: 20px;
    }

    /* BOX INTERNI BIANCHI */
    .ios-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 30px;
        padding: 20px;
        color: black;
        margin-bottom: 20px;
    }
    
    .status-card { text-align: center; background: #f2f2f7; border-radius: 20px; padding: 15px; margin: 5px; }
    .val-neon { font-size: 24px; font-weight: 700; color: #007aff; }

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
        strutture = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "KM_prossimo_Tagliando", "KM_prossime_Gomme", "User", "Altro"],
            "AnagraficaDriver": ["Nome", "Cognome"],
            "RubricaEmail": ["Nome", "Email"]
        }
        if foglio in strutture:
            for col in strutture[foglio]:
                if col not in df.columns: df[col] = ""
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
        msg['Subject'] = f"Richiesta Autorizzazione - {targa}"
        corpo = f"Buongiorno, veicolo targato {targa} - KM {km}. Intervento richiesto: {tipo_guasto}."
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
    st.markdown('<div class="ios-status-bar">Inserisci Password</div>', unsafe_allow_html=True)
    st.markdown('<div class="ios-title">GOPRESSA</div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. DATA LOADING ---
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME (GRID ICONS) ---
if st.session_state.pagina == "home":
    st.markdown(f'<div class="ios-status-bar">{datetime.now().strftime("%H:%M")} | {st.session_state.user}</div>', unsafe_allow_html=True)
    st.markdown('<div class="ios-title">GOPRESSA</div>', unsafe_allow_html=True)
    
    # RIGA 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="btn_man"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="btn_gua"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Segnala Guasto</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="btn_dan"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Danno Driver</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="btn_sta"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Stato Flotta</p>', unsafe_allow_html=True)
    
    # RIGA 2 (Dock)
    st.write("<br><br><br>", unsafe_allow_html=True)
    cd1, cd2, cd3, cd4 = st.columns(4)
    with cd1:
        if st.button("👑", key="btn_adm"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p>', unsafe_allow_html=True)
    with cd4:
        if st.button("🚪", key="btn_log"): st.session_state.clear(); st.rerun()
        st.markdown('<p class="app-label">Logout</p>', unsafe_allow_html=True)

# --- PAGINE INTERNE (LOGICA INVARIATA) ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("KILOMETRI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("MEZZO", lista_mezzi); km_g = st.number_input("KM ATTUALI:", value=0)
    p1=st.checkbox("Gomme Ant"); p2=st.checkbox("Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("NOTE:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        fi = st.camera_input("FOTO")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        sel = [k for k,v in {"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
        st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "status":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    df_s = carica_dati("Segnalazioni")
    for _, r in df_s[df_s['Stato'] == 'APERTO'].iterrows():
        st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b><br>{r['Descrizione']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    # Logica Admin (Targhe, Driver, Email, Chiusura Pratiche)
    df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']}")
            # Bottone Email e Chiudi...
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict["SIXT VERONA"], targa, "0", dg['Descrizione'], {}): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
