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
st.set_page_config(page_title="GOPRESSA POWER PRO", layout="wide", initial_sidebar_state="collapsed")

# API KEY PER FOTO HD (Prendila dai secrets)
IMGBB_KEY = st.secrets.get("IMGBB_API_KEY", "")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
for key in ['pagina', 'sub_guasto', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery']:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. SUPER CSS: GOLD LUXURY PILL DESIGN ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap');
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}
    .stApp {{ background: linear-gradient(135deg, #0f0f0f 0%, #1a1605 100%); color: #ffffff; font-family: 'Inter', sans-serif; }}
    .ios-pill-container {{
        background: rgba(0, 0, 0, 0.6); border-radius: 50px; padding: 15px 35px; border: 1px solid #d4af37;
        margin: 10px auto 40px auto; max-width: 500px; text-align: center; box-shadow: 0 10px 40px rgba(212, 175, 55, 0.2);
    }}
    .island-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #d4af37; margin: 0; }}
    [data-testid="stHorizontalBlock"] {{ max-width: 550px !important; margin: 0 auto 15px auto !important; align-items: center !important; }}
    [data-testid="column"] {{ display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; }}
    .stButton>button {{
        border: none !important; border-radius: 18px !important; width: 70px !important; height: 70px !important;
        background: #1c1c1e !important; color: white !important; font-size: 2em !important; box-shadow: 0 4px 10px rgba(0,0,0,0.5) !important;
    }}
    .app-label {{ color: white; font-size: 11px; margin-top: 6px; margin-bottom: 25px; font-weight: 400; }}
    .ios-card {{ background: rgba(0, 0, 0, 0.85); border-radius: 35px; padding: 25px; color: white; border: 1px solid #d4af37; margin: 0 auto; max-width: 700px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNZIONI POTENTI (UPLOAD CLOUD) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def upload_image(image_file):
    """CARICAMENTO SU SERVER ESTERNO (NESSUN LIMITE DI MEMORIA)"""
    if image_file is None or IMGBB_KEY == "": return ""
    try:
        img_bytes = image_file.getvalue()
        res = requests.post("https://api.imgbb.com/1/upload", 
                            params={"key": IMGBB_KEY}, 
                            files={"image": img_bytes})
        return res.json()["data"]["url"]
    except: return "Errore Caricamento"

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, link_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        links_text = "\n".join([f"- {k}: {v}" for k,v in link_list.items() if v])
        corpo = f"Buongiorno,\n\nvi scrivo per il veicolo {targa} - KM {km}.\nRichiesta: {tipo_guasto}.\n\nFoto allegate:\n{links_text}\n\nCordiali saluti,\nGopressa SRL"
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
    st.session_state.gallery = {}; st.session_state.sub_guasto = None
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
        if st.button("👑", key="h4"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p>', unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- 7. GUASTO (POWER MODE) ---
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
        t_g = st.selectbox("MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
        config = {"PASTIGLIE FRENI": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "GOMME": {"Gomme1":"GOMMA 1", "Gomme2":"GOMMA 2", "Targa":"TARGA", "Libretto":"LIBRETTO", "KM":"KM"},
                  "SPIA MOTORE": {"Spia":"SPIA", "KM":"KM", "Libretto":"LIBRETTO", "Targa":"TARGA"},
                  "TAGLIANDO": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
                  "ALTRO": {"Targa":"TARGA", "KM":"KM", "Ex1":"FOTO 1", "Ex2":"FOTO 2"}}
        for k, v in config[tipo].items():
            if k not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
            else: st.success(f"✅ {v} CARICATA")
        if st.session_state.show_cam:
            fi = st.camera_input("SCATTA"); 
            if fi:
                with st.spinner("Caricamento HD nel Cloud..."):
                    st.session_state.gallery[st.session_state.foto_tipo] = upload_image(fi)
                    st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA"):
            conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": tipo, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme1","") or st.session_state.gallery.get("Ex1",""), "Foto_Cruscotto": st.session_state.gallery.get("Spia",""), "Foto_KM": st.session_state.gallery.get("KM",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
            st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 8. ADMIN ---
elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']}")
            # Link Foto HD
            for col in ["Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]:
                if dg.get(col): st.markdown(f"[🔗 Vedi Foto {col.split('_')[1]}]({dg[col]})")
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                fa = {k: dg.get(k, "") for k in ["Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]}
                if invia_email_ufficiale(rub_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], fa): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
