import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import PIL.Image
from fpdf import FPDF
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

# ⚠️ INSERISCI QUI L'ID DELLA TUA CARTELLA GOOGLE DRIVE
ID_CARTELLA_DRIVE = "1KNPV94jAUpXNbq5JYoVQ1yp8aoExmNNU"

# --- STILE CSS PREMIUM ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background-color: #1a1c24; border-radius: 15px; padding: 20px; border: 1px solid #2d2f39;
    }
    .stButton>button { border-radius: 10px !important; font-weight: bold !important; height: 3em !important; }
    .scadenza-box { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white; }
    .tagliando { background-color: #1e3a5f; border-left: 5px solid #3b82f6; }
    .gomme { background-color: #143e2f; border-left: 5px solid #10b981; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA AI & DRIVE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def upload_to_drive(pdf_bytes, filename):
    try:
        creds_info = st.secrets["connections"]["gsheets"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': filename, 'parents': [ID_CARTELLA_DRIVE]}
        media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
        # Carichiamo il file
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        # Rendiamo il file leggibile da chiunque abbia il link (opzionale)
        service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Errore caricamento Drive: {e}")
        return ""

def genera_pdf(targa, km, km_t, km_g, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT MANUTENZIONE", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 8, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"KM REGISTRATI: {km} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA PROSSIMO TAGLIANDO: {km_t} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA PROSSIME GOMME: {km_g} km", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "NOTE INTERVENTO:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 8, altro if altro.strip() != "" else "Nessuna nota.")
    return pdf.output(dest='S').encode('latin-1')

# --- DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.fillna("").astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Link_Report", "Altro"])

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    nome = st.text_input("Inserisci Nome e Cognome")
    if st.button("ACCEDI AL SISTEMA", use_container_width=True, type="primary"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Utente: **{st.session_state.user}**")
    menu = st.radio("Menu:", ["🏠 Nuovo Intervento", "📋 Archivio Flotta"])
    if st.button("Esci"):
        del st.session_state.user
        st.rerun()

df = carica_dati()

# --- INSERIMENTO ---
if menu == "🏠 Nuovo Intervento":
    st.markdown("<h1>🛠 Registro Intervento</h1>", unsafe_allow_html=True)
    
    if 'mostra_camera' not in st.session_state: st.session_state.mostra_camera = False
    
    if not st.session_state.mostra_camera:
        if st.button("📷 APRI SCANNER TARGA", use_container_width=True):
            st.session_state.mostra_camera = True
            st.rerun()
    else:
        foto = st.camera_input("Inquadra la targa")
        if foto:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            res = model.generate_content(["Leggi la targa.", PIL.Image.open(foto)])
            st.session_state.targa_ocr = res.text.strip().upper().replace(" ", "")
            st.session_state.mostra_camera = False
            st.rerun()
        if st.button("Chiudi"): st.session_state.mostra_camera = False; st.rerun()

    lista_t = sorted(df['Targa'].unique()) if not df.empty else ["GG730AV"]
    targa_init = st.session_state.get('targa_ocr', lista_t[0])
    targa_sel = st.selectbox("Veicolo", lista_t, index=lista_t.index(targa_init) if targa_init in lista_t else 0)
    
    idx = df.index[df['Targa'] == targa_sel].tolist()[0]
    
    km_att = st.number_input("Chilometri rilevati", value=safe_int(df.at[idx, 'KM_Attuali']), step=1)
    km_prossimo_t = km_att + 30000
    km_prossimo_g = km_att + 40000
    
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_prossimo_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_prossimo_g} km</b></div>", unsafe_allow_html=True)

    check_t = st.checkbox("⚙️ Tagliando completato")
    check_g = st.checkbox("🛞 Cambio gomme completato")
    altro = st.text_area("Note aggiuntive", value=df.at[idx, 'Altro'] if df.at[idx, 'Altro'] != "nan" else "")

    if st.button("💾 SALVA E CARICA REPORT SU DRIVE", use_container_width=True, type="primary"):
        with st.spinner("Generazione PDF e Caricamento su Drive..."):
            pdf_bytes = genera_pdf(targa_sel, km_att, km_prossimo_t, km_prossimo_g, altro, st.session_state.user)
            nome_file = f"Report_{targa_sel}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            link_drive = upload_to_drive(pdf_bytes, nome_file)
            
            df.at[idx, 'KM_Attuali'] = str(km_att)
            if check_t:
                df.at[idx, 'KM_Tagliando'] = str(km_att)
                df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo_t)
            if check_g:
                df.at[idx, 'KM_Gomme'] = str(km_att)
                df.at[idx, 'KM_prossime Gomme'] = str(km_prossimo_g)
            
            df.at[idx, 'Altro'] = altro
            df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
            df.at[idx, 'User'] = st.session_state.user
            df.at[idx, 'Link_Report'] = link_drive
            
            conn.update(worksheet="Manutenzione", data=df)
            st.success(f"Dati salvati! PDF disponibile nell'Archivio.")
            st.balloons()

# --- ARCHIVIO ---
elif menu == "📋 Archivio Flotta":
    st.markdown("<h1>📋 Stato Flotta e Report PDF</h1>", unsafe_allow_html=True)
    if st.text_input("Password Admin", type="password") == "GSSA2026":
        # Visualizziamo la tabella con i link cliccabili
        st.dataframe(
            df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Link_Report": st.column_config.LinkColumn("📄 Vedi Report PDF")
            }
        )
