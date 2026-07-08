import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GOPRESSA PRO", layout="wide", initial_sidebar_state="collapsed")

# --- DESIGN ESTETICO AVANZATO (CSS) ---
st.markdown("""
    <style>
    /* Sfondo animato e font */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Inter:wght@300;400;600&display=swap');
    
    .stApp {
        background: radial-gradient(circle at top left, #1a1c2c, #0e1117);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }

    /* Header Aziendale */
    .brand-container {
        padding: 40px 20px;
        text-align: center;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 40px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.2);
    }
    
    .brand-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 3.5em !important;
        font-weight: 700;
        background: linear-gradient(90deg, #ff4b4b, #ff8e8e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 5px;
        margin: 0;
    }

    .brand-subtitle {
        font-size: 1.1em;
        color: #808495;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-top: 10px;
    }

    /* Card Menu (Mattonelle) */
    .menu-tile {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        border-radius: 25px;
        padding: 30px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: all 0.4s ease;
        cursor: pointer;
        height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }

    .menu-tile:hover {
        background: rgba(255, 75, 75, 0.1);
        border: 1px solid #ff4b4b;
        transform: translateY(-10px);
        box-shadow: 0 10px 30px rgba(255, 75, 75, 0.2);
    }

    /* Pulsanti Streamlit ridisegnati */
    .stButton>button {
        width: 100%;
        border-radius: 20px !important;
        background: linear-gradient(135deg, #ff4b4b 0%, #c11212 100%) !important;
        color: white !important;
        border: none !important;
        padding: 20px !important;
        font-size: 1.1em !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.3) !important;
        transition: 0.3s !important;
    }
    
    .stButton>button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 10px 25px rgba(255, 75, 75, 0.4) !important;
    }

    /* Box Scadenze */
    .status-card {
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        font-weight: bold;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .tagl-card { background: linear-gradient(135deg, #1e40af, #3b82f6); }
    .gomme-card { background: linear-gradient(135deg, #065f46, #10b981); }

    /* Rimuovi decorazioni Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
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
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(0, 15, "GOPRESSA SRL - OFFICIAL REPORT", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Mezzo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"KM REGISTRATI: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 10, f"Note Intervento: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA NAVIGAZIONE ---
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def vai_a(nome):
    st.session_state.pagina = nome
    st.rerun()

# --- LOGIN SCREEN ---
if 'user' not in st.session_state:
    st.markdown('<div class="brand-container"><h1 class="brand-title">GOPRESSA</h1><p class="brand-subtitle">Dispatcher Portal Access</p></div>', unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        nome = st.text_input("👤 Nome e Cognome Operatore")
        if st.button("ACCEDI AL PORTALE"):
            if nome:
                st.session_state.user = nome.upper()
                st.rerun()
    st.stop()

# --- HEADER FISSO ---
st.markdown(f'''
    <div class="brand-container">
        <h1 class="brand-title">GOPRESSA</h1>
        <p class="brand-subtitle">Bentornato, {st.session_state.user}</p>
    </div>
''', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- HOME DASHBOARD ---
if st.session_state.pagina == "home":
    st.markdown("<h3 style='text-align:center; margin-bottom:30px;'>⚙️ SELEZIONA ATTIVITÀ</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="menu-tile"><h2>🛠️</h2><p>MANUTENZIONE</p></div>', unsafe_allow_html=True)
        if st.button("APRI REGISTRO", key="m1"): vai_a("manutenzione")
        
    with col2:
        st.markdown('<div class="menu-tile"><h2>⚠️</h2><p>SEGNALA GUASTO</p></div>', unsafe_allow_html=True)
        if st.button("INVIA REPORT", key="m2"): vai_a("guasto")
        
    with col3:
        st.markdown('<div class="menu-tile"><h2>👑</h2><p>AREA ADMIN</p></div>', unsafe_allow_html=True)
        if st.button("ACCEDI ARCHIVIO", key="m3"): vai_a("admin")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 ESCI DAL SISTEMA"):
        st.session_state.clear()
        st.rerun()

# --- PAGINA MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU PRINCIPALE"): vai_a("home")
    
    st.markdown("<h2>🛠 Registro Intervento</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    t_sel = st.selectbox("🚛 Seleziona Veicolo:", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background:rgba(255,75,75,0.2); padding:20px; border-radius:20px; border:1px solid #ff4b4b; margin-bottom:20px;'>
            🚨 <b>NOTIFICA GUASTI:</b> {len(guasti_aperti)} segnalazioni attive!
        </div>""", unsafe_allow_html=True)

    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 Chilometri attuali (cruscotto):", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card tagl-card'><small>PROSSIMO TAGLIANDO</small><br><span style='font-size:25px;'>{km_att + 30000} km</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card gomme-card'><small>PROSSIME GOMME</small><br><span style='font-size:25px;'>{km_att + 40000} km</span></div>", unsafe_allow_html=True)

    st.markdown("<br>### 📋 CHECKLIST LAVORI", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    ch_t = col_a.checkbox("⚙️ Tagliando Eseguito")
    ch_g = col_b.checkbox("🛞 Gomme Cambiate")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.write("---")
        st.write("🔧 Riparazioni Straordinarie:")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Sistemato: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("✍️ Note e altri dettagli:")

    if st.button("💾 SALVA E ARCHIVIA"):
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
        st.success("✅ Intervento registrato con successo!")
        st.balloons()

# --- PAGINA SEGNALAZIONE ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU PRINCIPALE"): vai_a("home")
    st.markdown("<h2>⚠️ Report Danni e Malfunzionamenti</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("Quale mezzo ha il problema?", lista_mezzi)
    desc = st.text_area("Descrivi cosa non funziona:")
    urg = st.select_slider("Quanto è urgente?", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("INVIA SEGNALAZIONE"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.error("🚨 Segnalazione inoltrata al Dispatcher."); vai_a("home")

# --- PAGINA ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU PRINCIPALE"): vai_a("home")
    st.markdown("<h2>📋 Pannello di Gestione</h2>", unsafe_allow_html=True)
    
    if not st.session_state.is_admin:
        pw = st.text_input("Inserisci Password Admin", type="password")
        if st.button("SBLOCCA"):
            if pw == "GSSA2026": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")
        
        st.subheader("🚨 Guasti da Risolvere")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                st.markdown(f"<div style='border-left:5px solid #ff4b4b; background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px;'><b>{r['Targa']}</b>: {r['Descrizione']}</div>", unsafe_allow_html=True)
                if st.button(f"Segna come Riparato {r['Targa']}##{i}"):
                    df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
        else: st.success("Nessuna riparazione in sospeso.")
        
        st.divider()
        st.subheader("📄 Archivio Documenti")
        t_search = st.selectbox("Seleziona furgone per vedere i report:", lista_mezzi)
        for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
            st.download_button(f"📥 Scarica Report del {r['Data']} ({r['KM_Attuali']} km)", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"p_{i}")
