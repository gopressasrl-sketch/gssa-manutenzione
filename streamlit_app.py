import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import requests
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

# API KEY per caricamento Cloud (Prendila dai secrets)
IMGBB_KEY = st.secrets.get("IMGBB_API_KEY", "")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
keys = ['pagina', 'sub_guasto', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']
for k in keys:
    if k not in st.session_state:
        if k == 'pagina': st.session_state[k] = "home"
        elif k == 'gallery': st.session_state[k] = {}
        elif k == 'is_admin': st.session_state[k] = True
        else: st.session_state[k] = None

# --- 2. CSS GOLD LUXURY IPHONE 17 PRO MAX ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');
    
    /* PULIZIA TOTALE */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stToolbar"] {{ display: none !important; }}

    .stApp {{ background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }}

    /* PILLOLA TITOLO ORO */
    .ios-pill-container {{
        background: rgba(255, 255, 255, 0.05); border-radius: 50px;
        padding: 15px 35px; border: 1px solid #d4af37;
        margin: 10px auto 40px auto; max-width: 500px; text-align: center;
        box-shadow: 0 10px 30px rgba(212, 175, 55, 0.2);
    }}
    .main-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #d4af37; margin: 0; }}

    /* GRIGLIA APP iPHONE */
    [data-testid="stHorizontalBlock"] {{ max-width: 450px !important; margin: 0 auto !important; }}
    [data-testid="column"] {{ display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; padding: 0 !important; }}

    .stButton>button {{
        border: none !important; border-radius: 20px !important;
        width: 72px !important; height: 72px !important;
        background: #1c1c1e !important; color: white !important;
        font-size: 2em !important; box-shadow: 0 4px 10px rgba(0,0,0,0.5) !important;
        transition: 0.1s !important;
    }}
    .app-label {{ color: white; font-size: 11px; margin-top: 6px; margin-bottom: 25px; font-weight: 400; }}

    /* CARD INTERNE */
    .ios-card {{ background: rgba(28, 28, 30, 0.98); border-radius: 35px; padding: 25px; color: white; border: 1px solid #d4af37; margin: 0 auto; max-width: 700px; }}
    .status-mini {{ text-align: center; background: #000; border-radius: 20px; padding: 15px; margin-bottom: 10px; border: 1px solid #d4af37; }}
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

def upload_image_cloud(image_file):
    """CARICAMENTO PROFESSIONALE SU IMGBB (SOLUZIONE ANTI-CRASH)"""
    if image_file is None or IMGBB_KEY == "": return ""
    try:
        img_bytes = image_file.getvalue()
        res = requests.post("https://api.imgbb.com/1/upload", params={"key": IMGBB_KEY}, files={"image": img_bytes})
        return res.json()["data"]["url"]
    except: return "Error"

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, link_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        links = "\n".join([f"- {k}: {v}" for k,v in link_list.items() if v and "http" in v])
        corpo = f"Buongiorno,\n\nvi scrivo per il veicolo {targa} - KM {km}.\nRichiesta: {tipo_guasto}.\n\nDocumentazione fotografica:\n{links}\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. DATA ---
st.markdown(f'<div class="ios-pill-container"><h1 class="island-title">GOPRESSA</h1><p class="status-text">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)
df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.show_cam = False
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="h1"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="h2"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="h3"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Danni</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="h4"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Flotta</p>', unsafe_allow_html=True)
    if st.button("👑 ADMIN PANEL"): st.session_state.pagina = "admin"; st.rerun()
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- 7. PAGINE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("KILOMETRI ATTUALI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='status-mini'><small>TAGLIANDO A</small><br><div class='status-val'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='status-mini'><small>GOMME A</small><br><div class='status-val'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
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
        note = st.text_area("🗒️ NOTE:") if tipo in ["ALTRO", "TAGLIANDO"] else ""
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
            if fi: 
                with st.spinner("Caricamento HD..."):
                    st.session_state.gallery[st.session_state.foto_tipo] = upload_image_cloud(fi)
                    st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA REPORT"):
            df_s = carica_dati("Segnalazioni")
            gal = st.session_state.gallery
            nuova = pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": f"{tipo} | {note}", "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": gal.get("Foto",""), "Foto_Gomme": gal.get("Gomme1","") or gal.get("Ex1",""), "Foto_Cruscotto": gal.get("Spia",""), "Foto_KM": gal.get("KM",""), "Foto_Targa": gal.get("Targa",""), "Foto_Libretto": gal.get("Libretto","")}])
            conn.update(worksheet="Segnalazioni", data=pd.concat([df_s, nuova], ignore_index=True))
            st.session_state.gallery = {}; st.session_state.sub_guasto = None; st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    # Logica Admin (Targhe, Driver, Email)
    df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']}")
            for k in ["Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]:
                if dg.get(k) and "http" in dg[k]: st.markdown(f"[👁️ Vedi Foto {k.split('_')[1]}]({dg[k]})")
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                fa = {k: dg.get(k, "") for k in ["Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]}
                if invia_email_ufficiale(rub_dict.get(sel_m,""), targa, dg['KM_Segnalazione'], dg['Descrizione'], fa): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Stato'] = 'CHIUSO'
                conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
