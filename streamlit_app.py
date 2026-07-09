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

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione variabili
for key in ['pagina', 'show_cam', 'foto_tipo', 'is_admin']:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = False

if 'gallery' not in st.session_state: st.session_state.gallery = {}

# --- STILE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu { visibility: hidden; display: none !important; }
    .stApp { background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0f172a 50%, #020617 100%); background-attachment: fixed; color: #f8fafc; font-family: 'Rajdhani', sans-serif; }
    .header-container { text-align: center; padding: 30px; background: rgba(255, 255, 255, 0.02); border-radius: 40px; border: 1px solid rgba(0, 255, 255, 0.2); box-shadow: 0 0 30px rgba(0, 255, 255, 0.1); margin-bottom: 20px; }
    .main-title { font-family: 'Orbitron', sans-serif; font-size: 3.5em !important; font-weight: 900; background: linear-gradient(to right, #00d2ff, #3a7bd5, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 8px; }
    .stButton>button { background: rgba(15, 23, 42, 0.6) !important; color: #00f2ff !important; border: 1px solid #00f2ff !important; border-radius: 15px !important; padding: 15px !important; font-size: 1.1em !important; font-weight: 700; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background: #00f2ff !important; color: #000 !important; box-shadow: 0 0 20px #00f2ff !important; }
    .guasto-card { background: rgba(0, 242, 255, 0.05); border: 1px solid #00f2ff; padding: 20px; border-radius: 20px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try: return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img.thumbnail((400, 400)) # Compressione per GSheets
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=50)
    return base64.b64encode(buffered.getvalue()).decode()

def invia_email_guasto(destinatario, targa, data, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]
        msg['To'] = destinatario
        msg['Subject'] = f"Segnalazione Guasto Mezzo - Targa {targa}"
        
        corpo = f"""Gentile Servizio Clienti,

con la presente vi comunico che in data {data} il furgone a noleggio targato {targa}, mentre era in circolazione, ha subito un guasto meccanico: {tipo_guasto}, risultando così inutilizzabile.

Il mezzo è stato quindi recuperato tramite carroattrezzi mediante intervento di soccorso stradale. In allegato trovate la documentazione e i dettagli fotografici dell'intervento.

Vista l'urgenza della situazione, vi chiedo cortesemente di predisporre al più presto un furgone sostitutivo, in modo da poter proseguire con le attività senza ulteriori disagi.

Resto in attesa di un vostro riscontro e vi ringrazio per la collaborazione.

Cordiali saluti,
Gopressa SRL"""
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        # Allegati Foto
        for label, b64_str in foto_list.items():
            if b64_str:
                img_data = base64.b64decode(b64_str)
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(img_data)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"')
                msg.attach(part)
        
        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
        server.starttls()
        server.login(cfg["smtp_user"], cfg["smtp_password"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Errore invio mail: {e}")
        return False

# --- UI LOGIN & HEADER ---
if 'user' not in st.session_state:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>MISSION CONTROL ACCESS</p></div>', unsafe_allow_html=True)
    nome_input = st.text_input("IDENTIFICAZIONE")
    if st.button("INIZIA"):
        if nome_input: st.session_state.user = nome_input.upper(); st.rerun()
    st.stop()

st.markdown(f'<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>OPERATORE: {st.session_state.user}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []
lista_drivers = sorted((df_drivers['Nome'] + " " + df_drivers['Cognome']).tolist()) if not df_drivers.empty else ["NESSUN DRIVER"]

# --- HOME ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🛠️ MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
    with col2:
        if st.button("🚨 SEGNALA GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
    with col3:
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with col4:
        if st.button("👑 ADMIN"): st.session_state.pagina = "admin"; st.rerun()
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- MANUTENZIONE --- (Logica precedente invariata)
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0]
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        conn.update(worksheet="Manutenzione", data=df_man); st.success("OK"); st.rerun()

# --- SEGNALA GUASTO (MULTI-FOTO) ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🚨 ANOMALIA E DOCUMENTAZIONE FOTOGRAFICA</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("UNITÀ IN PANNE", lista_mezzi)
    
    col_p, col_n = st.columns(2)
    with col_p:
        p1 = st.checkbox("Gomme Anteriore"); p2 = st.checkbox("Gomme Posteriore")
        p3 = st.checkbox("Freni"); p4 = st.checkbox("Tagliando"); p5 = st.checkbox("Spia Motore")
    with col_n:
        desc_extra = st.text_area("Note aggiuntive:")
    
    st.markdown("### 📸 SET FOTOGRAFICO OBBLIGATORIO")
    foto_keys = {
        "Gomme": "🛞 FOTO GOMME 2",
        "Cruscotto": "💡 FOTO CRUSCOTTO (SPIE)",
        "Chilometri": "📟 FOTO KM (ODOMETRO)",
        "Targa": "🆔 FOTO TARGA",
        "Libretto": "📄 FOTO LIBRETTO"
    }
    
    for key, label in foto_keys.items():
        if key not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {label}"):
                st.session_state.show_cam = True
                st.session_state.foto_tipo = key
                st.rerun()
        else:
            st.success(f"✅ {label} CATTURATA")
            if st.button(f"🗑️ RI-SCATTA {key}"):
                del st.session_state.gallery[key]
                st.rerun()

    if st.session_state.show_cam:
        foto_input = st.camera_input(f"INQUADRA: {st.session_state.foto_tipo}")
        if foto_input:
            st.session_state.gallery[st.session_state.foto_tipo] = process_image(foto_input)
            st.session_state.show_cam = False
            st.rerun()

    if st.button("🚀 INVIA REPORT COMPLETO IN OFFICINA"):
        guasti = [k for k,v in {"Gomme Ant":p1, "Gomme Post":p2, "Freni":p3, "Tagliando":p4, "Spia":p5}.items() if v]
        desc_f = ", ".join(guasti) + " | " + desc_extra
        
        nuova_s = pd.DataFrame([{
            "Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"),
            "Descrizione": desc_f, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO",
            "Foto_Gomme": st.session_state.gallery.get("Gomme", ""),
            "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto", ""),
            "Foto_KM": st.session_state.gallery.get("Chilometri", ""),
            "Foto_Targa": st.session_state.gallery.get("Targa", ""),
            "Foto_Libretto": st.session_state.gallery.get("Libretto", "")
        }])
        df_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_v, nuova_s], ignore_index=True))
        st.session_state.gallery = {}; vai_a("home")

# --- SEGNALA DANNO --- (Logica precedente)
elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    d_sel = st.selectbox("DRIVER", lista_drivers)
    t_sel = st.selectbox("VEICOLO", lista_mezzi)
    desc = st.text_area("DANNO")
    if st.button("INVIA"):
        # Salvataggio danno driver...
        vai_a("home")

# --- ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>👑 TERMINALE AMMINISTRATIVO</h2>", unsafe_allow_html=True)
    
    df_seg = carica_dati("Segnalazioni")
    
    # RAGGRUPPAMENTO PER FURGONE
    mezzi_in_panne = df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique()
    
    for targa in mezzi_in_panne:
        with st.expander(f"🚛 VEICOLO IN PANNE: {targa}", expanded=True):
            dati_g = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"**Guasto:** {dati_g['Descrizione']}")
            st.write(f"**Data:** {dati_g['Data_Segnalazione']}")
            
            # Visualizzazione Foto
            c = st.columns(5)
            f_labels = ["Gomme", "Cruscotto", "KM", "Targa", "Libretto"]
            f_cols = ["Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, label in enumerate(f_labels):
                img_b64 = dati_g.get(f_cols[i], "")
                if img_b64:
                    c[i].image(base64.b64decode(img_b64), caption=label)
            
            st.divider()
            st.subheader("📧 INVIO COMUNICAZIONE NOLEGGIO")
            email_dest = st.text_input(f"Email Destinatario per {targa}", key=f"mail_{targa}")
            if st.button(f"📧 INVIA EMAIL DI SOCCORSO PER {targa}"):
                if email_dest:
                    # Preparazione lista foto per allegati
                    foto_da_allegare = {f_labels[i]: dati_g.get(f_cols[i], "") for i in range(5)}
                    if invia_email_guasto(email_dest, targa, dati_g['Data_Segnalazione'], dati_g['Descrizione'], foto_da_allegare):
                        st.success("EMAIL INVIATA CON SUCCESSO!")
                else: st.error("Inserisci un destinatario.")
            
            if st.button(f"✅ CHIUDI PRATICA {targa}"):
                df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'
                conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

    # (Qui sotto rimangono i pannelli per Aggiunta Targa e Driver che hai già)
