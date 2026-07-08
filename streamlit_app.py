import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import PIL.Image
from fpdf import FPDF
import io

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GSSA GESTIONE PRO 2026", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- FUNZIONE AUTO-SELECT MODELLO 2026 ---
@st.cache_resource
def seleziona_miglior_modello():
    try:
        # Recupera la lista di tutti i modelli disponibili
        modelli = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Ordine di preferenza (dal più nuovo al più vecchio)
        priorita = ["3.5", "3.1", "3.0", "2.5", "2.0", "1.5"]
        
        for p in priorita:
            for m in modelli:
                if p in m and "flash" in m: # Preferiamo le versioni 'flash' perché sono istantanee
                    return m
        return "models/gemini-1.5-flash" # Default di emergenza
    except:
        return "models/gemini-1.5-flash"

MODELLO_ATTIVO = seleziona_miglior_modello()

# --- INIZIALIZZAZIONE ---
if 'mostra_camera' not in st.session_state:
    st.session_state.mostra_camera = False

KM_INTERVALLO_TAGLIANDO = 30000
KM_INTERVALLO_GOMME = 40000

FLOTTA = ["GG730AV", "GG206JK", "GG243ZM", "GG677RR", "GG927ZP", "GG429ZP", "GG208ZN", "GG790ZL", "GG075ZP", "GG834JH", "GG736AV", "GG477JF", "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GS595DF", "GS597DF", "GZ399JY", "GZ401JY", "HA412FV", "HA717DG", "HA630DC", "HA881MM", "GZ249ZS", "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "GZ532JY"]
LISTA_TARGHE = sorted(FLOTTA)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNZIONI CORE ---
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
        cols = ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Link_Report", "Altro"]
        return pd.DataFrame(columns=cols)

def genera_pdf(targa, km, km_prossimo_t, km_prossimo_g, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORT MANUTENZIONE GSSA 2026", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, f"KM Rilevati: {km} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"SCADENZA TAGLIANDO: {km_prossimo_t} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA GOMME: {km_prossimo_g} km", ln=True)
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Note: {altro}")
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
if 'user' not in st.session_state:
    st.title("🚀 GSSA PRO - NEXT GEN 2026")
    nome = st.text_input("Inserisci Nome e Cognome")
    if st.button("ACCEDI"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

df = carica_dati()

with st.sidebar:
    st.title("GSSA 2026")
    st.success(f"Modello AI: {MODELLO_ATTIVO.split('/')[-1]}")
    menu = st.radio("Menu", ["🏠 Inserimento", "👑 Admin"])
    st.write(f"👤 {st.session_state.user}")

if menu == "🏠 Inserimento":
    st.title("🛠 Nuovo Intervento")
    
    targa_ocr = None
    
    # PULSANTE FOTOCAMERA
    if not st.session_state.mostra_camera:
        if st.button("📷 APRI SCANNER TARGA 2026", use_container_width=True):
            st.session_state.mostra_camera = True
            st.rerun()
    else:
        if st.button("❌ CHIUDI SCANNER"):
            st.session_state.mostra_camera = False
            st.rerun()
            
        foto = st.camera_input("Inquadra la targa")
        if foto:
            with st.spinner(f"Analisi con {MODELLO_ATTIVO}..."):
                try:
                    model = genai.GenerativeModel(MODELLO_ATTIVO)
                    res = model.generate_content(["Leggi la targa, rispondi SOLO con la targa.", PIL.Image.open(foto)])
                    targa_ocr = res.text.strip().upper().replace(" ", "")
                    st.session_state.mostra_camera = False
                    st.success(f"Targa rilevata: {targa_ocr}")
                except:
                    st.error("Errore di connessione AI. Seleziona manualmente.")
                    st.session_state.mostra_camera = False

    targa_init = targa_ocr if targa_ocr in LISTA_TARGHE else LISTA_TARGHE[0]
    targa_sel = st.selectbox("Veicolo", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_init))

    if targa_sel in df['Targa'].values:
        idx = df.index[df['Targa'] == targa_sel].tolist()[0]
        
        km_att = st.number_input("Chilometri Attuali:", value=safe_int(df.at[idx, 'KM_Attuali']), step=1)
        
        km_prossimo_t = km_att + KM_INTERVALLO_TAGLIANDO
        km_prossimo_g = km_att + KM_INTERVALLO_GOMME
        
        c1, c2 = st.columns(2)
        with c1: st.info(f"📅 **Tagliando a:**\n{km_prossimo_t} km")
        with c2: st.success(f"🛞 **Gomme a:**\n{km_prossimo_g} km")

        st.divider()
        eseguito_t = st.checkbox("✅ Tagliando eseguito oggi")
        eseguite_g = st.checkbox("✅ Cambio Gomme eseguito oggi")
        altro = st.text_area("📝 Note / Altri lavori", value=df.at[idx, 'Altro'] if 'Altro' in df.columns else "")

        if st.button("💾 SALVA E GENERA REPORT", use_container_width=True, type="primary"):
            df.at[idx, 'KM_Attuali'] = str(km_att)
            if eseguito_t:
                df.at[idx, 'KM_Tagliando'] = str(km_att)
                df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo_t)
            if eseguite_g:
                df.at[idx, 'KM_Gomme'] = str(km_att)
                df.at[idx, 'KM_prossime Gomme'] = str(km_prossimo_g)
                
            df.at[idx, 'Altro'] = altro
            df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            df.at[idx, 'User'] = st.session_state.user
            
            conn.update(worksheet="Manutenzione", data=df)
            st.success("✅ Sistema aggiornato!")
            
            pdf_b = genera_pdf(targa_sel, km_att, km_prossimo_t, km_prossimo_g, altro, st.session_state.user)
            st.download_button("📥 SCARICA REPORT PDF", data=pdf_b, file_name=f"Report_{targa_sel}.pdf", mime="application/pdf")
            st.balloons()

elif menu == "👑 Admin":
    st.title("📊 Riepilogo Flotta 2026")
    pw = st.text_input("Password Admin", type="password")
    if pw == "GSSA2026":
        st.dataframe(df, use_container_width=True, hide_index=True)
