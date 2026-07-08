import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import PIL.Image
from fpdf import FPDF
import io

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

INTERVALLO_TAGLIANDO = 30000
FLOTTA = ["GG730AV", "GG206JK", "GG243ZM", "GG677RR", "GG927ZP", "GG429ZP", "GG208ZN", "GG790ZL", "GG075ZP", "GG834JH", "GG736AV", "GG477JF", "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GS595DF", "GS597DF", "GZ399JY", "GZ401JY", "HA412FV", "HA717DG", "HA630DC", "HA881MM", "GZ249ZS", "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "GZ532JY"]
LISTA_TARGHE = sorted(FLOTTA)

conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try:
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "None"]: return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"])

def genera_pdf(targa, km, km_tag, km_prossimo, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORT MANUTENZIONE GSSA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Chilometri Attuali: {km} km", ln=True)
    pdf.cell(0, 10, f"KM Ultimo Tagliando: {km_tag} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {km_prossimo} km", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "NOTE / ALTRI LAVORI:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, altro if altro.strip() != "" else "Nessuna nota inserita.")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.title("🚚 Sistema Manutenzione GSSA")
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- MENU ---
with st.sidebar:
    st.title("GSSA PRO")
    menu = st.radio("Menu", ["🏠 Inserimento", "👑 Admin"])
    st.write(f"👤 {st.session_state.user}")

df = carica_dati()

if menu == "🏠 Inserimento":
    st.title("🛠 Aggiorna Mezzo")
    
    # Scansione targa
    foto = st.camera_input("📸 Scansiona Targa")
    targa_ocr = None
    if foto:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(["Leggi la targa, scrivi solo quella.", PIL.Image.open(foto)])
        targa_ocr = res.text.strip().upper().replace(" ", "")

    targa_init = targa_ocr if targa_ocr in LISTA_TARGHE else LISTA_TARGHE[0]
    targa_sel = st.selectbox("Veicolo", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_init))

    if targa_sel in df['Targa'].values:
        idx = df.index[df['Targa'] == targa_sel].tolist()[0]
        
        c1, c2, c3 = st.columns(3)
        with c1: km_att = st.number_input("KM Attuali", value=safe_int(df.at[idx, 'KM_Attuali']))
        with c2: km_tag = st.number_input("KM Tagliando", value=safe_int(df.at[idx, 'KM_Tagliando']))
        with c3: km_gom = st.number_input("KM Gomme", value=safe_int(df.at[idx, 'KM_Gomme']))

        km_prossimo = km_tag + INTERVALLO_TAGLIANDO
        st.warning(f"🔔 Prossimo Tagliando a: {km_prossimo} km")
        
        altro = st.text_area("📝 Altri lavori / Note", value=df.at[idx, 'Altro'] if 'Altro' in df.columns else "")

        if st.button("💾 SALVA DATI E GENERA PDF", use_container_width=True, type="primary"):
            # Aggiorna il Foglio Google (Questo funziona sempre!)
            df.at[idx, 'KM_Attuali'] = str(km_att)
            df.at[idx, 'KM_Tagliando'] = str(km_tag)
            df.at[idx, 'KM_Gomme'] = str(km_gom)
            df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo)
            df.at[idx, 'Altro'] = altro
            df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            df.at[idx, 'User'] = st.session_state.user
            
            conn.update(worksheet="Manutenzione", data=df)
            st.success("✅ Chilometri e Note salvati nel Database!")
            
            # Crea il PDF per il download immediato
            pdf_b = genera_pdf(targa_sel, km_att, km_tag, km_prossimo, altro, st.session_state.user)
            st.download_button("📥 SCARICA ORA IL PDF", data=pdf_b, file_name=f"Report_{targa_sel}.pdf", mime="application/pdf")
            st.balloons()

elif menu == "👑 Admin":
    st.title("📊 Stato Flotta")
    pw = st.text_input("Password", type="password")
    if pw == "GSSA2026":
        st.dataframe(df, use_container_width=True, hide_index=True)
