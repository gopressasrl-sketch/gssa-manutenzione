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
    .stButton>button { border-radius: 10px !important; font-weight: bold !important; }
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

def carica_dati(foglio):
    try:
        return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except:
        return pd.DataFrame()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT ARCHIVIATO", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data Intervento: {row['Data']}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, f"Chilometri registrati: {row['KM_Attuali']} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"SCADENZA TAGLIANDO FISSATA: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA GOMME FISSATA: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "NOTE SALVATE:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, row['Altro'] if row['Altro'] != "" else "Nessuna nota.")
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

# --- MENU ---
with st.sidebar:
    st.markdown(f"### Benvenuto\n**{st.session_state.user}**")
    menu = st.radio("Scegli operazione:", ["🏠 Nuovo Intervento", "📋 Archivio Flotta"])
    if st.button("Esci"):
        del st.session_state.user
        st.rerun()

# --- PAGINA INSERIMENTO ---
if menu == "🏠 Nuovo Intervento":
    df_manutenzione = carica_dati("Manutenzione")
    st.markdown("<h1>🛠 Registro Intervento</h1>", unsafe_allow_html=True)
    
    if 'mostra_camera' not in st.session_state: st.session_state.mostra_camera = False
    
    if not st.session_state.mostra_camera:
        if st.button("📷 SCANNER TARGA", use_container_width=True):
            st.session_state.mostra_camera = True; st.rerun()
    else:
        foto = st.camera_input("Inquadra la targa")
        if foto:
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            res = model.generate_content(["Leggi la targa.", PIL.Image.open(foto)])
            st.session_state.targa_ocr = res.text.strip().upper().replace(" ", "")
            st.session_state.mostra_camera = False; st.rerun()
        if st.button("Chiudi Scanner"): st.session_state.mostra_camera = False; st.rerun()

    lista_t = sorted(df_manutenzione['Targa'].unique()) if not df_manutenzione.empty else ["GG730AV"]
    t_init = st.session_state.get('targa_ocr', lista_t[0])
    t_sel = st.selectbox("Veicolo", lista_t, index=lista_t.index(t_init) if t_init in lista_t else 0)
    
    idx = df_manutenzione.index[df_manutenzione['Targa'] == t_sel].tolist()[0]
    
    km_att = st.number_input("Chilometri oggi", value=safe_int(df_manutenzione.at[idx, 'KM_Attuali']), step=1)
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    check_t = c1.checkbox("⚙️ Tagliando completato")
    check_g = c2.checkbox("🛞 Cambio gomme completato")
    
    altro = st.text_area("Note e lavori extra", value="")

    if st.button("💾 SALVA INTERVENTO E ARCHIVIA", use_container_width=True, type="primary"):
        # 1. Aggiorna Stato Attuale
        df_manutenzione.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df_manutenzione.at[idx, 'KM_Tagliando'] = str(km_att)
            df_manutenzione.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if check_g:
            df_manutenzione.at[idx, 'KM_Gomme'] = str(km_att)
            df_manutenzione.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_manutenzione.at[idx, 'Altro'] = altro
        df_manutenzione.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_manutenzione.at[idx, 'User'] = st.session_state.user
        
        # 2. Crea riga per lo STORICO
        nuovo_storico = pd.DataFrame([{
            "Targa": t_sel,
            "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "KM_Attuali": str(km_att),
            "KM_prossimo_Tagliando": str(km_pross_t),
            "KM_prossime_Gomme": str(km_pross_g),
            "User": st.session_state.user,
            "Altro": altro
        }])
        
        # Carica storico esistente e aggiungi
        df_storico_vecchio = carica_dati("Storico")
        df_storico_nuovo = pd.concat([df_storico_vecchio, nuovo_storico], ignore_index=True)
        
        # Salva entrambi i fogli
        conn.update(worksheet="Manutenzione", data=df_manutenzione)
        conn.update(worksheet="Storico", data=df_storico_nuovo)
        
        st.success("✅ Intervento salvato e archiviato con successo!")
        st.balloons()

# --- PAGINA ARCHIVIO ---
elif menu == "📋 Archivio Flotta":
    st.markdown("<h1>📋 Archivio Storico Interventi</h1>", unsafe_allow_html=True)
    
    # Carichiamo i dati
    df_manutenzione = carica_dati("Manutenzione")
    df_storico = carica_dati("Storico")
    
    t_ricerca = st.selectbox("Seleziona furgone per vedere la cronologia:", sorted(df_manutenzione['Targa'].unique()))
    
    st.divider()
    
    # Filtra lo storico per la targa scelta
    cronologia = df_storico[df_storico['Targa'] == t_ricerca].sort_index(ascending=False)
    
    if cronologia.empty:
        st.info("Nessun intervento registrato per questo veicolo.")
    else:
        for i, row in cronologia.iterrows():
            with st.expander(f"📅 Intervento del {row['Data']} - {row['KM_Attuali']} km"):
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"**Operatore:** {row['User']}")
                    st.write(f"**Note:** {row['Altro']}")
                with col_b:
                    # Genera il PDF al volo per questa riga
                    pdf_storico = genera_pdf_storico(row)
                    st.download_button(
                        label="📄 Apri Report PDF",
                        data=pdf_storico,
                        file_name=f"Report_{t_ricerca}_{row['Data'].replace('/', '-')}.pdf",
                        mime="application/pdf",
                        key=f"btn_{i}"
                    )
