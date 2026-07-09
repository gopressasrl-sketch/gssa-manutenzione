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

# --- STILE CSS EXTREME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu { visibility: hidden; display: none !important; }
    .viewerBadge_container__1QSob, .viewerBadge_link__1QSob, div[class^="viewerBadge"] { display: none !important; }
    div[data-testid="stToolbar"], div[data-testid="stDecoration"] { display: none !important; }
    .stApp { background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0f172a 50%, #020617 100%); background-attachment: fixed; color: #f8fafc; font-family: 'Rajdhani', sans-serif; }
    .header-container { text-align: center; padding: 30px; background: rgba(255, 255, 255, 0.02); border-radius: 40px; border: 1px solid rgba(0, 255, 255, 0.2); box-shadow: 0 0 30px rgba(0, 255, 255, 0.1); margin-bottom: 20px; }
    .main-title { font-family: 'Orbitron', sans-serif; font-size: 3.5em !important; font-weight: 900; background: linear-gradient(to right, #00d2ff, #3a7bd5, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 8px; }
    .stButton>button { background: rgba(15, 23, 42, 0.6) !important; color: #00f2ff !important; border: 1px solid #00f2ff !important; border-radius: 15px !important; padding: 15px !important; font-size: 1.1em !important; font-weight: 700; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background: #00f2ff !important; color: #000 !important; box-shadow: 0 0 20px #00f2ff !important; }
    .guasto-card { background: rgba(0, 242, 255, 0.05); border: 1px solid #00f2ff; padding: 20px; border-radius: 20px; margin-bottom: 15px; }
    .status-card { padding: 20px; border-radius: 20px; text-align: center; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
    .val-neon { font-family: 'Orbitron', sans-serif; font-size: 28px; text-shadow: 0 0 10px #00d2ff; color: #00d2ff; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try: return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except:
        if foglio == "AnagraficaDriver": return pd.DataFrame(columns=["Nome", "Cognome"])
        if foglio == "RubricaEmail": return pd.DataFrame(columns=["Nome", "Email"])
        if foglio == "Segnalazioni": return pd.DataFrame(columns=["Targa", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto", "KM_Segnalazione"])
        return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img.thumbnail((400, 400))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=50)
    return base64.b64encode(buffered.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Mezzo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, f"KM REGISTRATI: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11); pdf.multi_cell(0, 8, f"Note: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        
        corpo = f"""Buongiorno,

vi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.
Avrei necessità di procedere con {tipo_guasto}.

Disponiamo di una carrozzeria convenzionata con noi, la Aldo Dal Maso & C. Snc, sita in Via Badia 7, 36043 Camisano Vicentino (VI), vicino alla stazione Amazon, che sarebbe disponibile a eseguire i lavori in tempi brevi.

Vi chiedo gentilmente se per Voi non ci sono problemi ad autorizzare questi interventi. Qualora ci confermaste la vostra approvazione, procederemmo immediatamente.

In allegato le foto del veicolo.

Resto in attesa di un Vostro gentile riscontro.

Cordiali saluti,
Gopressa SRL"""
        
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64_str in foto_list.items():
            if b64_str:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(b64_str))
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"')
                msg.attach(part)
        
        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
        server.starttls(); server.login(cfg["smtp_user"], cfg["smtp_password"])
        server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"Errore invio email: {e}"); return False

# --- HEADER FISSO ---
if 'user' in st.session_state:
    st.markdown(f'<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>UNIT: {st.session_state.user}</p></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1></div>', unsafe_allow_html=True)

# CARICAMENTO DATI
df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
df_rubrica = carica_dati("RubricaEmail")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# Rubrica
rubrica_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _, r in df_rubrica.iterrows(): rubrica_dict[r['Nome']] = r['Email']
lista_contatti = sorted(list(rubrica_dict.keys()))

# --- LOGIN ---
if 'user' not in st.session_state:
    nome_input = st.text_input("IDENTIFICAZIONE OPERATORE")
    if st.button("ACCEDI"):
        if nome_input: st.session_state.user = nome_input.upper(); st.rerun()
    st.stop()

# --- NAVIGAZIONE ---
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

# --- MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0]
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.success("OK"); st.rerun()

# --- GUASTO (CON RIGA KM AGGIUNTA) ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🚨 REGISTRAZIONE GUASTO</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("UNITÀ IN PANNE", lista_mezzi)
    
    # NUOVA RIGA KM RICHIESTA
    km_guasto = st.number_input("📟 CHILOMETRI ATTUALI DEL MEZZO:", value=0, step=1)
    
    st.write("Seleziona problemi:")
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    desc_extra = st.text_area("Altre note:")
    
    st.markdown("### 📸 SCATTA FOTO")
    f_keys = {"Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "FOTO KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    
    if st.session_state.show_cam:
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()

    if st.button("🚀 INVIA REPORT COMPLETO"):
        guasti = [k for k,v in {"Cambio Gomme Ant":p1,"Cambio Gomme Post":p2,"Pastiglie Freni":p3,"Tagliando":p4,"Spia Motore":p5}.items() if v]
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(guasti)+" | "+desc_extra, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto",""), "KM_Segnalazione": str(km_guasto)}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova_s], ignore_index=True))
        st.session_state.gallery = {}; st.session_state.pagina = "home"; st.rerun()

# --- ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    
    # AGGIUNTA DATI
    st.markdown("### ➕ AGGIUNGI NUOVI DATI")
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("🚛 NUOVO MEZZO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO"):
                nr = pd.DataFrame([{"Targa":nv, "KM_Attuali":"0", "KM_Gomme":"0", "KM_prossime Gomme":"0", "KM_Tagliando":"0", "KM_prossimo Tagliando":"0", "Data":"-", "User":"-", "Altro":"-"}])
                conn.update(worksheet="Manutenzione", data=pd.concat([df_man, nr], ignore_index=True)); st.rerun()
    with c2:
        with st.expander("👤 NUOVO DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"):
                nr = pd.DataFrame([{"Nome":nn, "Cognome":nc}]); conn.update(worksheet="AnagraficaDriver", data=pd.concat([df_drivers, nr], ignore_index=True)); st.rerun()
    with c3:
        with st.expander("📧 NUOVA EMAIL"):
            en = st.text_input("Nome Contatto").upper(); ee = st.text_input("Indirizzo Email")
            if st.button("SALVA EMAIL"):
                nr = pd.DataFrame([{"Nome":en, "Email":ee}]); conn.update(worksheet="RubricaEmail", data=pd.concat([df_rubrica, nr], ignore_index=True)); st.rerun()

    st.divider()
    df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE IN CORSO: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            # Usa i KM inseriti nella segnalazione, se mancano usa quelli del db manutenzione
            km_per_email = dg.get('KM_Segnalazione', '0')
            if km_per_email == "" or km_per_email == "0":
                km_per_email = df_man[df_man['Targa'] == targa]['KM_Attuali'].values[0]
            
            st.write(f"**Problema:** {dg['Descrizione']} | **KM Segnalati:** {km_per_email}")
            
            # --- EMAIL ---
            contatto_sel = st.selectbox(f"Destinatario per {targa}", lista_contatti, key=f"sel_{targa}")
            if st.button(f"📧 INVIA EMAIL UFFICIALE A {contatto_sel}"):
                f_att = {"Gomme":dg['Foto_Gomme'], "Cruscotto":dg['Foto_Cruscotto'], "KM":dg['Foto_KM'], "Targa":dg['Foto_Targa'], "Libretto":dg['Foto_Libretto']}
                if invia_email_ufficiale(rubrica_dict[contatto_sel], targa, km_per_email, dg['Descrizione'], f_att):
                    st.success("EMAIL INVIATA!")
            
            if st.button(f"✅ CHIUDI PRATICA {targa}"):
                df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'
                conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
