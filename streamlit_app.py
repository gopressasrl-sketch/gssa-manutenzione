import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GOPRESSA PRO", layout="wide", initial_sidebar_state="collapsed")

# --- STILE CSS PREMIUM (DESIGN DASHBOARD) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1c1f26 100%);
    }
    
    /* Header Gopressa */
    .gopressa-header {
        background: rgba(255, 75, 75, 0.1);
        padding: 30px;
        border-radius: 20px;
        border: 1px solid rgba(255, 75, 75, 0.3);
        text-align: center;
        margin-bottom: 30px;
    }
    
    .gopressa-header h1 {
        color: #ff4b4b !important;
        margin: 0;
        letter-spacing: 3px;
        font-weight: 800;
    }

    /* Card per i pulsanti del menu */
    .menu-card {
        background: rgba(30, 34, 45, 0.8);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
        transition: 0.3s;
        margin-bottom: 15px;
    }

    /* Pulsanti grandi tipo App */
    .stButton>button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 15px !important;
        background: linear-gradient(90deg, #ff4b4b 0%, #ff7676 100%) !important;
        color: white !important;
        font-size: 1.2em !important;
        font-weight: bold !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }
    
    /* Pulsante Indietro */
    .back-btn button {
        background: #3e4451 !important;
        height: 40px !important;
    }

    /* Box Scadenze */
    .scadenza-box {
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        color: white;
    }
    .tagliando { background: #1e3a8a; }
    .gomme { background: #064e3b; }
    
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try: return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except: return pd.DataFrame()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GOPRESSA SRL - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Mezzo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"KM al momento: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, f"Note: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA NAVIGAZIONE ---
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def vai_a(nome_pagina):
    st.session_state.pagina = nome_pagina
    st.rerun()

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown("""<div class="gopressa-header"><h1>GOPRESSA SRL</h1><p>Dispatcher Management</p></div>""", unsafe_allow_html=True)
    nome = st.text_input("Inserisci il tuo Nome e Cognome per accedere:")
    if st.button("ACCEDI AL PORTALE"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- HEADER FISSO ---
st.markdown(f"""
    <div class="gopressa-header">
        <h1>GOPRESSA SRL</h1>
        <p>Operatore: {st.session_state.user}</p>
    </div>
    """, unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- PAGINA HOME (IL NUOVO MENU) ---
if st.session_state.pagina == "home":
    st.markdown("<h3 style='text-align:center;'>Scegli un'operazione:</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 REGISTRO\nMANUTENZIONE"): vai_a("manutenzione")
    with col2:
        if st.button("⚠️ SEGNALA\nUN GUASTO"): vai_a("guasto")
    with col3:
        if st.button("📋 ARCHIVIO\n& ADMIN"): vai_a("admin")
    
    if st.button("🚪 Esci dal sistema", use_container_width=False):
        st.session_state.clear()
        st.rerun()

# --- PAGINA 1: MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ TORNA AL MENU", key="back1"): vai_a("home")
    
    st.markdown("<h2>🛠 Registro Intervento</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    t_sel = st.selectbox("🚛 Seleziona Veicolo:", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.error(f"⚠️ ATTENZIONE: Ci sono {len(guasti_aperti)} guasti aperti per questo mezzo!")

    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 KM Attuali:", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='scadenza-box tagliando'><small>PROSSIMO TAGLIANDO</small><br><b>{km_att + 30000} km</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='scadenza-box gomme'><small>PROSSIME GOMME</small><br><b>{km_att + 40000} km</b></div>", unsafe_allow_html=True)

    st.write("---")
    ch_t = st.checkbox("⚙️ Tagliando fatto")
    ch_g = st.checkbox("🛞 Gomme cambiate")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("Note:")

    if st.button("💾 SALVA INTERVENTO"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if ch_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if ch_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        if lavori_chiusi:
            for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_att+30000), "KM_prossime_Gomme": str(km_att+40000), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Manutenzione", data=df_man)
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("✅ Salvato!"); st.balloons()

# --- PAGINA 2: SEGNALAZIONE ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ TORNA AL MENU", key="back2"): vai_a("home")
    st.markdown("<h2>⚠️ Report Guasto</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("Quale mezzo?", lista_mezzi)
    desc = st.text_area("Descrivi il problema:")
    urg = st.select_slider("Urgenza:", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("INVIA SEGNALAZIONE"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.warning("⚠️ Inviato in officina."); vai_a("home")

# --- PAGINA 3: ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ TORNA AL MENU", key="back3"): vai_a("home")
    st.markdown("<h2>📋 Pannello Controllo</h2>", unsafe_allow_html=True)
    
    if not st.session_state.is_admin:
        pw = st.text_input("Password Admin", type="password")
        if st.button("ACCEDI"):
            if pw == "GSSA2026": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")
        
        st.subheader("🚨 Guasti Attivi")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        for i, r in df_aperti.iterrows():
            st.info(f"{r['Targa']}: {r['Descrizione']}")
            if st.button(f"Sistemato {r['Targa']}##{i}"):
                df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
        
        st.divider()
        t_search = st.selectbox("Storico Veicolo:", lista_mezzi)
        for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
            st.download_button(f"📄 Report {r['Data']} ({r['KM_Attuali']} km)", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
