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

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.fillna("").astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"])

def genera_pdf(targa, km, km_t, km_g, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT MANUTENZIONE", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, f"Chilometri registrati: {km} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {km_t} km", ln=True)
    pdf.cell(0, 10, f"PROSSIME GOMME: {km_g} km", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "NOTE INTERVENTO:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, altro if altro.strip() != "" else "Nessuna nota inserita.")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI AL SISTEMA", use_container_width=True, type="primary"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Benvenuto\n**{st.session_state.user}**")
    menu = st.radio("Scegli operazione:", ["🏠 Nuovo Intervento", "📋 Archivio Flotta"])
    if st.button("Esci"):
        del st.session_state.user
        st.rerun()

df = carica_dati()

# --- PAGINA INSERIMENTO ---
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
        if st.button("Annulla"): st.session_state.mostra_camera = False; st.rerun()

    lista_t = sorted(df['Targa'].unique()) if not df.empty else ["GG730AV"]
    t_init = st.session_state.get('targa_ocr', lista_t[0])
    t_sel = st.selectbox("Seleziona Veicolo", lista_t, index=lista_t.index(t_init) if t_init in lista_t else 0)
    
    idx = df.index[df['Targa'] == t_sel].tolist()[0]
    
    km_att = st.number_input("Chilometri rilevati oggi", value=safe_int(df.at[idx, 'KM_Attuali']), step=1)
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    check_t = st.checkbox("⚙️ Tagliando completato oggi")
    check_g = st.checkbox("🛞 Cambio gomme completato oggi")
    
    nota_precedente = df.at[idx, 'Altro']
    if nota_precedente.lower() == "nan": nota_precedente = ""
    altro = st.text_area("Note e lavori extra effettuati", value=nota_precedente)

    if st.button("💾 SALVA INTERVENTO", use_container_width=True, type="primary"):
        # Aggiorniamo il DataFrame
        df.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df.at[idx, 'KM_Tagliando'] = str(km_att)
            df.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if check_g:
            df.at[idx, 'KM_Gomme'] = str(km_att)
            df.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        
        df.at[idx, 'Altro'] = altro
        df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y %H:%M")
        df.at[idx, 'User'] = st.session_state.user
        
        # Salvataggio su Google Sheets
        conn.update(worksheet="Manutenzione", data=df)
        st.success("✅ Dati salvati con successo nel Database!")
        
        # Generiamo il PDF per il download immediato
        pdf_rep = genera_pdf(t_sel, km_att, km_pross_t, km_pross_g, altro, st.session_state.user)
        st.download_button("📥 SCARICA RICEVUTA PDF", data=pdf_rep, file_name=f"Report_{t_sel}.pdf", use_container_width=True)
        st.balloons()

# --- PAGINA ARCHIVIO ---
elif menu == "📋 Archivio Flotta":
    st.markdown("<h1>📋 Stato Generale Flotta</h1>", unsafe_allow_html=True)
    if st.text_input("Password Amministratore", type="password") == "GSSA2026":
        # Pulizia estetica della tabella
        df_view = df.copy()
        st.dataframe(df_view, use_container_width=True, hide_index=True)
