import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE ESTREMA ---
st.set_page_config(page_title="GOPRESSA PREMIUM", layout="wide", initial_sidebar_state="collapsed")

# --- CSS CYBER-DESIGN 2026 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');

    /* Sfondo Animato */
    .stApp {
        background: linear-gradient(-45deg, #0f172a, #1e1b4b, #312e81, #1e1b4b);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        color: #f8fafc;
        font-family: 'Rajdhani', sans-serif;
    }

    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Header Futuristico */
    .header-box {
        text-align: center;
        padding: 50px 20px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 40px;
        border: 1px solid rgba(255, 75, 75, 0.3);
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.2);
        margin-bottom: 40px;
    }

    .header-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 4.5em !important;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 0 15px #ff4b4b, 0 0 30px #ff4b4b;
        letter-spacing: 8px;
        margin: 0;
    }

    .header-subtitle {
        font-size: 1.3em;
        color: #94a3b8;
        letter-spacing: 4px;
        text-transform: uppercase;
        margin-top: 10px;
    }

    /* Pulsanti Cyber-Menu */
    .stButton>button {
        background: linear-gradient(135deg, #ef4444 0%, #991b1b 100%) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 20px !important;
        padding: 30px !important;
        font-size: 1.4em !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4) !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        text-transform: uppercase !important;
    }

    .stButton>button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(239, 68, 68, 0.6) !important;
        border: 1px solid #ffffff !important;
    }

    /* Card per Manutenzione */
    .status-card {
        padding: 30px;
        border-radius: 25px;
        text-align: center;
        border: 2px solid rgba(255,255,255,0.05);
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(10px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.5);
    }
    
    .tagl-val { color: #3b82f6; font-size: 32px; font-weight: 900; text-shadow: 0 0 10px #3b82f6; }
    .gomme-val { color: #10b981; font-size: 32px; font-weight: 900; text-shadow: 0 0 10px #10b981; }

    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background: rgba(255,255,255,0.05) !important;
        color: white !important;
        border-radius: 15px !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }

    /* Hide default elements */
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
    pdf.set_text_color(220, 20, 60)
    pdf.cell(0, 15, "GOPRESSA SRL - DISPATCHER REPORT", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Veicolo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"KM REGISTRATI: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 10, f"Descrizione Intervento: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA NAVIGAZIONE ---
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def vai_a(nome):
    st.session_state.pagina = nome
    st.rerun()

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown('<div class="header-box"><h1 class="header-title">GOPRESSA</h1><p class="header-subtitle">Dispatcher Portal 2026</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        nome = st.text_input("IDENTIFICAZIONE OPERATORE")
        if st.button("SBLOCCA ACCESSO"):
            if nome:
                st.session_state.user = nome.upper()
                st.rerun()
    st.stop()

# --- HEADER FISSO ---
st.markdown(f'''
    <div class="header-box">
        <h1 class="header-title">GOPRESSA</h1>
        <p class="header-subtitle">LOGISTICS & FLEET MANAGEMENT | Operatore: {st.session_state.user}</p>
    </div>
''', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- HOME DASHBOARD ---
if st.session_state.pagina == "home":
    st.markdown("<h3 style='text-align:center; color:#94a3b8; margin-bottom:40px;'>SISTEMA OPERATIVO ATTIVO</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛠️ MANUTENZIONE"): vai_a("manutenzione")
    with col2:
        if st.button("🚨 SEGNALA GUASTO"): vai_a("guasto")
    with col3:
        if st.button("👑 AREA ADMIN"): vai_a("admin")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT PORTALE"):
        st.session_state.clear()
        st.rerun()

# --- PAGINA MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ TORNA ALLA DASHBOARD"): vai_a("home")
    
    st.markdown("<h2>🛠 REGISTRO INTERVENTO</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    t_sel = st.selectbox("🚛 SELEZIONA MEZZO", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background:rgba(239,68,68,0.2); padding:20px; border-radius:20px; border:2px solid #ef4444; margin-bottom:20px;'>
            🚨 <b>NOTIFICA GUASTO:</b> Sono presenti segnalazioni attive per questo veicolo!
        </div>""", unsafe_allow_html=True)

    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 CHILOMETRI ATTUALI (Rilevazione Cruscotto)", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='status-card'><small>PROSSIMO TAGLIANDO</small><br><span class='tagl-val'>{km_att + 30000} km</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='status-card'><small>PROSSIME GOMME</small><br><span class='gomme-val'>{km_att + 40000} km</span></div>", unsafe_allow_html=True)

    st.markdown("<br>### 🔧 CHECKLIST ATTIVITÀ", unsafe_allow_html=True)
    c_a, c_b = st.columns(2)
    ch_t = c_a.checkbox("⚙️ ESEGUITO TAGLIANDO COMPLETO")
    ch_g = c_b.checkbox("🛞 ESEGUITO CAMBIO PNEUMATICI")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.write("---")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"✅ RIPARATO: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("✍️ NOTE OPERATIVE E DETTAGLI")

    if st.button("💾 REGISTRA E ARCHIVIA"):
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
        st.success("✅ INTERVENTO ARCHIVIATO CON SUCCESSO!")
        st.balloons()

# --- PAGINA SEGNALAZIONE ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ TORNA ALLA DASHBOARD"): vai_a("home")
    st.markdown("<h2>🚨 SEGNALAZIONE ANOMALIA</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("🚛 MEZZO COINVOLTO", lista_mezzi)
    desc = st.text_area("DESCRIVI IL PROBLEMA RILEVATO")
    urg = st.select_slider("LIVELLO DI PRIORITÀ", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("🚀 INVIA REPORT ALL'OFFICINA"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.error("🚨 SEGNALAZIONE REGISTRATA."); vai_a("home")

# --- PAGINA ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ TORNA ALLA DASHBOARD"): vai_a("home")
    st.markdown("<h2>👑 TERMINALE DI CONTROLLO</h2>", unsafe_allow_html=True)
    
    if not st.session_state.is_admin:
        pw = st.text_input("PASSWORD DI SISTEMA", type="password")
        if st.button("AUTENTICA"):
            if pw == "GSSA2026": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        if st.button("🔒 CHIUDI SESSIONE ADMIN"): st.session_state.is_admin = False; st.rerun()
        
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")
        
        st.subheader("🛠️ INTERVENTI RICHIESTI")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                st.markdown(f"<div style='border-left:5px solid #ef4444; background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px;'><b>{r['Targa']}</b>: {r['Descrizione']}</div>", unsafe_allow_html=True)
                if st.button(f"SISTEMATO {r['Targa']}##{i}"):
                    df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
        else: st.success("NESSUNA ANOMALIA DA RIPARARE.")
        
        st.divider()
        st.subheader("📋 ARCHIVIO DOCUMENTALE")
        t_search = st.selectbox("SCEGLI VEICOLO", lista_mezzi)
        for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
            st.download_button(f"📄 REPORT {r['Data']} ({r['KM_Attuali']} km)", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"p_{i}")
