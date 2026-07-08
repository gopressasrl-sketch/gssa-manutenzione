import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import PIL.Image
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

# --- STILE CSS PERSONALIZZATO (Per rendere l'app bellissima) ---
st.markdown("""
    <style>
    /* Sfondo e font */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Box delle sezioni (Card) */
    .st-emotion-cache-12w0qpk, .st-emotion-cache-vj128p {
        background-color: #1a1c24 !important;
        border-radius: 15px !important;
        padding: 25px !important;
        border: 1px solid #2d2f39 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* Pulsanti */
    .stButton>button {
        border-radius: 10px !important;
        height: 3em !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    
    /* Pulsante Salva - Rosso Brillante */
    div.stButton > button:first-child[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b 0%, #c11212 100%) !important;
        border: none !important;
    }

    /* Titoli */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #ffffff !important;
    }

    /* Messaggi info personalizzati */
    .scadenza-box {
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .tagliando { background-color: #1e3a5f; border-left: 5px solid #3b82f6; }
    .gomme { background-color: #143e2f; border-left: 5px solid #10b981; }
    
    /* Nascondi header streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA AI ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def seleziona_miglior_modello():
    try:
        modelli = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in ["3.5", "3.1", "3.0", "1.5"]:
            for m in modelli:
                if p in m and "flash" in m: return m
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

MODELLO_ATTIVO = seleziona_miglior_modello()

# --- DATABASE ---
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
        # Sostituiamo i valori non validi con stringa vuota subito
        return df.fillna("").astype(str)
    except:
        cols = ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Link_Report", "Altro"]
        return pd.DataFrame(columns=cols)

def genera_pdf(targa, km, km_t, km_g, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT MANUTENZIONE", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Data Intervento: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 8, f"Operatore: {user}", ln=True)
    pdf.cell(0, 8, f"Veicolo: {targa}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"CHILOMETRI REGISTRATI: {km} km", ln=True)
    pdf.ln(5)
    pdf.set_text_color(0, 50, 150)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {km_t} km", ln=True)
    pdf.set_text_color(0, 100, 50)
    pdf.cell(0, 10, f"PROSSIMO CAMBIO GOMME: {km_g} km", ln=True)
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "NOTE:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 8, altro if altro.strip() != "" else "Nessuna nota aggiuntiva.")
    return pdf.output(dest='S').encode('latin-1')

# --- UI LOGIN ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    with st.container():
        nome = st.text_input("Inserisci il tuo Nome e Cognome per iniziare")
        if st.button("ACCEDI AL SISTEMA", use_container_width=True, kind="primary"):
            if nome:
                st.session_state.user = nome.upper()
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Benvenuto\n**{st.session_state.user}**")
    st.divider()
    menu = st.radio("Scegli operazione:", ["🏠 Nuovo Intervento", "📋 Archivio Flotta"], label_visibility="collapsed")
    st.divider()
    if st.button("Esci dal sistema"):
        del st.session_state.user
        st.rerun()

df = carica_dati()

# --- PAGINA INSERIMENTO ---
if menu == "🏠 Nuovo Intervento":
    st.markdown("<h1>🛠 Registro Intervento</h1>", unsafe_allow_html=True)

    # Scanner
    with st.container():
        if 'mostra_camera' not in st.session_state: st.session_state.mostra_camera = False
        
        if not st.session_state.mostra_camera:
            if st.button("📷 APRI SCANNER TARGA", use_container_width=True):
                st.session_state.mostra_camera = True
                st.rerun()
        else:
            foto = st.camera_input("Scatta foto alla targa")
            if foto:
                try:
                    model = genai.GenerativeModel(MODELLO_ATTIVO)
                    res = model.generate_content(["Leggi la targa.", PIL.Image.open(foto)])
                    targa_letta = res.text.strip().upper().replace(" ", "")
                    st.session_state.targa_ocr = targa_letta
                    st.session_state.mostra_camera = False
                    st.rerun()
                except:
                    st.session_state.mostra_camera = False
            if st.button("Chiudi Scanner"):
                st.session_state.mostra_camera = False
                st.rerun()

    # Selezione
    targa_init = st.session_state.get('targa_ocr', LISTA_TARGHE[0])
    if targa_init not in LISTA_TARGHE: targa_init = LISTA_TARGHE[0]
    
    targa_sel = st.selectbox("Veicolo Selezionato", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_init))
    
    idx = df.index[df['Targa'] == targa_sel].tolist()[0]
    
    # Input KM
    with st.container():
        st.markdown("### Chilometraggio")
        km_att = st.number_input("Chilometri Attuali rilevati", value=safe_int(df.at[idx, 'KM_Attuali']), step=100)
        
        km_prossimo_t = km_att + 30000
        km_prossimo_g = km_att + 40000
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""<div class='scadenza-box tagliando'>
                <small style='color:#a6c8ff'>CALCOLO TAGLIANDO</small><br>
                <b style='font-size:22px;'>{km_prossimo_t} km</b>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class='scadenza-box gomme'>
                <small style='color:#a7f3d0'>PROSSIME GOMME</small><br>
                <b style='font-size:22px;'>{km_prossimo_g} km</b>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # Note e Checklist
    with st.container():
        st.markdown("### Dettagli Lavoro")
        c1, c2 = st.columns(2)
        with c1: check_t = st.checkbox("⚙️ Tagliando completato")
        with c2: check_g = st.checkbox("🛞 Cambio gomme completato")
        
        note_esistenti = df.at[idx, 'Altro']
        if note_esistenti.lower() == "nan": note_esistenti = ""
        
        altro = st.text_area("🗒️ Note aggiuntive (altri lavori effettuati)", value=note_esistenti)

    # Bottone Salva
    if st.button("💾 SALVA INTERVENTO E GENERA REPORT", use_container_width=True, type="primary"):
        df.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df.at[idx, 'KM_Tagliando'] = str(km_att)
            df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo_t)
        if check_g:
            df.at[idx, 'KM_Gomme'] = str(km_att)
            df.at[idx, 'KM_prossime Gomme'] = str(km_prossimo_g)
        
        df.at[idx, 'Altro'] = altro
        df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df.at[idx, 'User'] = st.session_state.user
        
        conn.update(worksheet="Manutenzione", data=df)
        st.success("Dati archiviati con successo!")
        
        pdf_rep = genera_pdf(targa_sel, km_att, km_prossimo_t, km_prossimo_g, altro, st.session_state.user)
        st.download_button("📥 SCARICA RICEVUTA PDF", data=pdf_rep, file_name=f"Report_{targa_sel}.pdf", use_container_width=True)
        st.balloons()

# --- PAGINA ADMIN ---
elif menu == "📋 Archivio Flotta":
    st.markdown("<h1>📋 Stato Generale Flotta</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Password Amministratore", type="password")
    if pwd == "GSSA2026":
        st.dataframe(df, use_container_width=True, hide_index=True)
