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

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

# ID Cartella Google Drive dove salvare i PDF (INSERISCI IL TUO ID QUI)
ID_CARTELLA_DRIVE = "1KNPV94jAUpXNbq5JYoVQ1yp8aoExmNNU"

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Connessione GSheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNZIONE CARICAMENTO DRIVE ---
def carica_pdf_su_drive(pdf_bytes, nome_file):
    try:
        # Recupero credenziali dai secrets
        info_credenziali = st.secrets["connections"]["gsheets"]
        creds = service_account.Credentials.from_service_account_info(info_credenziali)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': nome_file,
            'parents': [ID_CARTELLA_DRIVE]
        }
        
        fh = io.BytesIO(pdf_bytes)
        media = MediaIoBaseUpload(fh, mimetype='application/pdf')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink') # Ritorna il link al PDF
    except Exception as e:
        st.error(f"Errore caricamento Drive: {e}")
        return "Errore Caricamento"

# --- FUNZIONE GENERAZIONE PDF ---
def genera_pdf(targa, km, km_tag, km_prossimo, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORT MANUTENZIONE VEICOLO GSSA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Chilometri Attuali: {km}", ln=True)
    pdf.cell(0, 10, f"Ultimo Tagliando: {km_tag} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {km_prossimo} km", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Note: {altro}")
    return pdf.output(dest='S').encode('latin-1')

# ... (Mantieni le funzioni safe_int e carica_dati del messaggio precedente) ...

def safe_int(val):
    try:
        if pd.isna(val) or str(val).strip() in ["", "-", "nan"]: return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro", "Link_Report"])

# --- INTERFACCIA ---
if 'user' not in st.session_state:
    st.title("🚚 Accesso GSSA")
    nome = st.text_input("Nome")
    if st.button("Vai"): st.session_state.user = nome.upper(); st.rerun()
    st.stop()

df = carica_dati()

# Assicuriamoci che la colonna Link_Report esista
if "Link_Report" not in df.columns:
    df["Link_Report"] = ""

st.title("🛠 Aggiornamento e Archivio PDF")

targa = st.selectbox("Seleziona Veicolo", sorted(df['Targa'].unique()))
idx = df.index[df['Targa'] == targa].tolist()[0]

col1, col2 = st.columns(2)
with col1:
    km_att = st.number_input("KM Attuali", value=safe_int(df.at[idx, 'KM_Attuali']))
    km_tag = st.number_input("KM Tagliando", value=safe_int(df.at[idx, 'KM_Tagliando']))
with col2:
    km_gom = st.number_input("KM Gomme", value=safe_int(df.at[idx, 'KM_Gomme']))
    altro = st.text_area("Lavori eseguiti", value=df.at[idx, 'Altro'] if 'Altro' in df.columns else "")

km_prossimo = km_tag + 30000

if st.button("💾 SALVA DATI E CARICA PDF SU DRIVE", use_container_width=True, type="primary"):
    with st.spinner("Generazione PDF e caricamento su Google Drive..."):
        # 1. Genera PDF
        pdf_b = genera_pdf(targa, km_att, km_tag, km_prossimo, altro, st.session_state.user)
        
        # 2. Carica su Drive
        nome_file_pdf = f"Report_{targa}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        link_drive = carica_pdf_su_drive(pdf_b, nome_file_pdf)
        
        # 3. Aggiorna DataFrame e GSheets
        df.at[idx, 'KM_Attuali'] = str(km_att)
        df.at[idx, 'KM_Tagliando'] = str(km_tag)
        df.at[idx, 'KM_Gomme'] = str(km_gom)
        df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo)
        df.at[idx, 'Altro'] = altro
        df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df.at[idx, 'User'] = st.session_state.user
        df.at[idx, 'Link_Report'] = link_drive
        
        conn.update(worksheet="Manutenzione", data=df)
        
        st.success(f"Tutto salvato! Link PDF: {link_drive}")
        st.markdown(f"[🔗 Apri Report PDF su Drive]({link_drive})")
        st.balloons()

st.divider()
st.subheader("📊 Database con Link ai Report")
# Mostra il link cliccabile nella tabella
st.dataframe(df, use_container_width=True, hide_index=True)
