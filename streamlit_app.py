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
st.set_page_config(page_title="GOPRESSA GOLD PRO", layout="wide", initial_sidebar_state="collapsed")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
keys_to_init = ['pagina', 'sub_guasto', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. SUPER CSS: GOLD LUXURY PILL DESIGN (PULIZIA TOTALE) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap');
    
    /* ELIMINA OGNI ELEMENTO STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    .stApp {{ background: linear-gradient(135deg, #1a1605 0%, #4d3d0d 50%, #1a1605 100%); color: #ffffff; font-family: 'Inter', sans-serif; }}

    /* DYNAMIC ISLAND GOLD */
    .ios-pill-container {{
        background: rgba(0, 0, 0, 0.6); border-radius: 50px;
        padding: 15px 35px; border: 1px solid #d4af37;
        margin: 10px auto 40px auto; max-width: 500px; text-align: center;
        box-shadow: 0 10px 40px rgba(212, 175, 55, 0.2);
    }}
    .island-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #d4af37; margin: 0; }}
    .status-text {{ color: #8e8e93; font-size: 0.9em; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }}

    /* GRIGLIA ORIZZONTALE */
    [data-testid="stHorizontalBlock"] {{ max-width: 650px !important; margin: 0 auto 15px auto !important; background: rgba(0,0,0,0.4); border-radius: 25px; padding: 10px !important; border: 1px solid rgba(212, 175, 55, 0.1); align-items: center !important; }}
    [data-testid="column"] {{ display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; }}

    .stButton>button {{
        border: none !important; border-radius: 15px !important; height: 60px !important;
        background: transparent !important; color: #ffffff !important;
        font-size: 1.1em !important; font-weight: 600 !important; text-align: left !important;
        padding-left: 10px !important; width: 100% !important; transition: 0.3s !important;
    }}
    .icon-box {{ width: 60px; height: 60px; background: linear-gradient(135deg, #d4af37 0%, #8b6b23 100%); border-radius: 18px; display: flex; align-items: center; justify-content: center; font-size: 1.8em; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
    .app-label {{ color: white; font-size: 11px; margin-top: 6px; margin-bottom: 25px; font-weight: 400; }}
    
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
        req = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"]
        }
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    """RISOLUZIONE ERRORE API DEFINITIVA: Ridimensionamento a 400px per sicurezza totale"""
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img = img.convert("RGB") # Assicura compatibilità
    img.thumbnail((400, 400)) 
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=40, optimize=True) # Qualità bilanciata per GSheets
    return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Targa: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDI": "3"}
if not st.session_state.user:
    st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text">Identification Required</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. DATA LOADING ---
st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.sub_guasto = None
    def grid_row(icon, label, target):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown(f'<div class="icon-box">{icon}</div>', unsafe_allow_html=True)
        with c2: 
            if st.button(label, key=f"btn_{target}"): st.session_state.pagina = target; st.rerun()
    grid_row("🛠️", "REGISTRO MANUTENZIONE", "manutenzione")
    grid_row("🚨", "SEGNALA UN GUASTO", "guasto")
    grid_row("💥", "SEGNALA DANNO DRIVER", "danno")
    grid_row("📊", "STATO DELLA FLOTTA", "status")
    grid_row("👑", "AREA AMMINISTRATORE", "admin")
    st.write("<br>")
    grid_row("🚪", "LOGOUT UTENTE", "logout")
    if st.session_state.pagina == "logout": st.session_state.clear(); st.rerun()

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Indietro"): 
        if st.session_state.sub_guasto: st.session_state.sub_guasto = None
        else: st.session_state.pagina = "home"
        st.rerun()
    if not st.session_state.sub_guasto:
        st.markdown("### 🚨 Seleziona Problema")
        if st.button("🦷 PASTIGLIE FRENI"): st.session_state.sub_guasto = "Pastiglie Freni"; st.rerun()
        if st.button("🛞 GOMME DA CAMBIARE"): st.session_state.sub_guasto = "Gomme"; st.rerun()
        if st.button("💡 SPIA MOTORE"): st.session_state.sub_guasto = "Spia Motore"; st.rerun()
        if st.button("⚙️ TAGLIANDO"): st.session_state.sub_guasto = "Tagliando"; st.rerun()
        if st.button("❓ ALTRI GUASTI"): st.session_state.sub_guasto = "Altro"; st.rerun()
    else:
        tipo = st.session_state.sub_guasto
        t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
        note = st.text_area("🗒️ NOTE:") if tipo in ["Altro", "Tagliando"] else ""
        configs = {
            "Pastiglie Freni": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
            "Gomme": {"Gomme1":"GOMMA 1", "Gomme2":"GOMMA 2", "Targa":"TARGA", "Libretto":"LIBRETTO", "KM":"KM"},
            "Spia Motore": {"Spia":"SPIA", "KM":"KM", "Libretto":"LIBRETTO", "Targa":"TARGA"},
            "Tagliando": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
            "Altro": {"Targa":"TARGA", "KM":"KM", "Extra1":"FOTO 1", "Extra2":"FOTO 2"}
        }
        for k, v in configs[tipo].items():
            if k not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
            else: st.success(f"✅ {v} OK")
        if st.session_state.show_cam:
            if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
            fi = st.camera_input("SCATTA")
            if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA REPORT"):
            conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": f"{tipo} | {note}", "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto_Gomme": st.session_state.gallery.get("Gomme1","") or st.session_state.gallery.get("Extra1",""), "Foto_Cruscotto": st.session_state.gallery.get("Spia",""), "Foto_KM": st.session_state.gallery.get("KM",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
            st.session_state.gallery = {}; st.session_state.pagina="home"; st.rerun()
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
                if invia_email_ufficiale(rub_dict.get("SIXT VERONA",""), targa, dg['KM_Segnalazione'], dg['Descrizione'], { "Gomme": dg['Foto_Gomme'], "Spia": dg['Foto_Cruscotto'], "KM": dg['Foto_KM'], "Targa": dg['Foto_Targa'], "Libretto": dg['Foto_Libretto'] }): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# (Pagine manutenzione, danno e status caricate come prima ma dentro ios-card)
