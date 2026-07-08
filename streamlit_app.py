import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
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
    .alert-guasto { background-color: #442222; border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; color: #ffbcbc; margin-bottom: 15px; }
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

# --- FUNZIONI DATABASE ---
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
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(5); pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.cell(0, 10, f"Chilometri registrati: {row['KM_Attuali']} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, f"Note: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI", use_container_width=True, type="primary"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Benvenuto\n**{st.session_state.user}**")
    menu = st.radio("Menu:", ["🏠 Nuovo Intervento", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    if st.button("Esci"):
        del st.session_state.user; st.rerun()

# --- PAGINA 1: NUOVO INTERVENTO ---
if menu == "🏠 Nuovo Intervento":
    df_man = carica_dati("Manutenzione")
    df_seg = carica_dati("Segnalazioni")
    st.markdown("<h1>🛠 Registro Manutenzione</h1>", unsafe_allow_html=True)
    
    if 'mostra_camera' not in st.session_state: st.session_state.mostra_camera = False
    
    if not st.session_state.mostra_camera:
        if st.button("📷 SCANSIONA TARGA VEICOLO", use_container_width=True):
            st.session_state.mostra_camera = True; st.rerun()
    else:
        foto = st.camera_input("Inquadra la targa")
        if foto:
            try:
                model = genai.GenerativeModel(MODELLO_ATTIVO)
                res = model.generate_content(["Leggi la targa.", PIL.Image.open(foto)])
                st.session_state.targa_ocr = res.text.strip().upper().replace(" ", "")
                st.session_state.mostra_camera = False; st.rerun()
            except:
                st.session_state.mostra_camera = False; st.rerun()
        if st.button("Annulla"): st.session_state.mostra_camera = False; st.rerun()

    lista_t = sorted(df_man['Targa'].unique()) if not df_man.empty else ["GG730AV"]
    t_init = st.session_state.get('targa_ocr', lista_t[0])
    if t_init not in lista_t: t_init = lista_t[0]
    t_sel = st.selectbox("Veicolo Selezionato", lista_t, index=lista_t.index(t_init))
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"<div class='alert-guasto'>⚠️ <b>ATTENZIONE!</b> {len(guasti_aperti)} guasti segnalati:</div>", unsafe_allow_html=True)
        for _, g in guasti_aperti.iterrows(): st.write(f"• {g['Descrizione']}")

    st.divider()
    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("Chilometri oggi", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    check_t = st.checkbox("⚙️ Tagliando completato")
    check_g = st.checkbox("🛞 Cambio gomme completato")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.markdown("### Riparazione Guasti")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"fix_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("Note aggiuntive")

    if st.button("💾 SALVA INTERVENTO", use_container_width=True, type="primary"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if check_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        if lavori_chiusi:
            for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_pross_t), "KM_prossime_Gomme": str(km_pross_g), "User": st.session_state.user, "Altro": altro}])
        conn.update(worksheet="Manutenzione", data=df_man)
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("✅ Salvato!"); st.balloons()

# --- PAGINA 2: SEGNALA GUASTO (CON SCANNER!) ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h1>⚠️ Segnala Problema</h1>", unsafe_allow_html=True)
    df_man = carica_dati("Manutenzione")
    
    # SCANNER TARGA ANCHE QUI!
    if 'mostra_camera_guasto' not in st.session_state: st.session_state.mostra_camera_guasto = False
    
    if not st.session_state.mostra_camera_guasto:
        if st.button("📷 SCANSIONA TARGA", use_container_width=True):
            st.session_state.mostra_camera_guasto = True; st.rerun()
    else:
        foto = st.camera_input("Inquadra la targa del mezzo con il problema")
        if foto:
            try:
                model = genai.GenerativeModel(MODELLO_ATTIVO)
                res = model.generate_content(["Leggi la targa.", PIL.Image.open(foto)])
                st.session_state.targa_ocr_guasto = res.text.strip().upper().replace(" ", "")
                st.session_state.mostra_camera_guasto = False; st.rerun()
            except:
                st.session_state.mostra_camera_guasto = False; st.rerun()
        if st.button("Chiudi"): st.session_state.mostra_camera_guasto = False; st.rerun()

    lista_t = sorted(df_man['Targa'].unique()) if not df_man.empty else ["GG730AV"]
    t_init = st.session_state.get('targa_ocr_guasto', lista_t[0])
    if t_init not in lista_t: t_init = lista_t[0]
    t_guasto = st.selectbox("Veicolo", lista_t, index=lista_t.index(t_init))
    
    desc = st.text_area("Descrizione del guasto")
    urg = st.select_slider("Urgenza", options=["BASSA", "MEDIA", "ALTA"])
    
    if st.button("INVIA SEGNALAZIONE", use_container_width=True, type="primary"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.error("Segnalazione inviata correttamente!"); st.session_state.targa_ocr_guasto = ""

# --- PAGINA 3: ARCHIVIO & ADMIN ---
elif menu == "📋 Archivio & Admin":
    st.markdown("<h1>📋 Dashboard</h1>", unsafe_allow_html=True)
    if st.text_input("Password Admin", type="password") == "GSSA2026":
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")
        st.subheader("🚨 Guasti da riparare")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        for i, r in df_aperti.iterrows():
            ritardo = (datetime.now() - datetime.strptime(r['Data_Segnalazione'], "%d/%m/%Y")).days >= 2
            colore = "#ff4b4b" if ritardo else "#3b82f6"
            st.markdown(f"<div style='border:1px solid {colore}; padding:10px; border-radius:10px; margin-bottom:5px;'><b>{r['Targa']}</b>: {r['Descrizione']} (del {r['Data_Segnalazione']}) {'🚨 <b>RITARDO</b>' if ritardo else ''}</div>", unsafe_allow_html=True)
        st.divider(); st.subheader("📄 Archivio Report")
        t_rep = st.selectbox("Mezzo", sorted(df_sto['Targa'].unique()))
        for i, r in df_sto[df_sto['Targa'] == t_rep].sort_index(ascending=False).iterrows():
            with st.expander(f"Report {r['Data']} - {r['KM_Attuali']} km"):
                st.download_button("📥 Scarica PDF", data=genera_pdf_storico(r), file_name=f"Report_{t_rep}.pdf", key=f"pdf_{i}")
