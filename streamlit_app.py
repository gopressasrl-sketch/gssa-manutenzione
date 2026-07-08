import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# --- CSS DEEP SPACE 2026 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');

    /* Sfondo Spaziale Profondo */
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
        background-attachment: fixed;
        color: #f8fafc;
        font-family: 'Rajdhani', sans-serif;
    }

    /* Effetto Stelle distanti */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: radial-gradient(#fff 1px, transparent 1px);
        background-size: 50px 50px;
        opacity: 0.1;
        z-index: -1;
    }

    /* Header Mission Control */
    .header-container {
        text-align: center;
        padding: 60px 20px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 50px;
        border: 1px solid rgba(0, 255, 255, 0.2);
        box-shadow: 0 0 40px rgba(0, 255, 255, 0.1);
        margin-bottom: 50px;
        backdrop-filter: blur(10px);
    }

    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 5em !important;
        font-weight: 900;
        background: linear-gradient(to right, #00d2ff, #3a7bd5, #ff4b4b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 12px;
        margin: 0;
        filter: drop-shadow(0 0 15px rgba(0, 210, 255, 0.5));
    }

    .sub-title {
        font-size: 1.4em;
        color: #67e8f9;
        letter-spacing: 6px;
        text-transform: uppercase;
        margin-top: 15px;
        font-weight: 300;
    }

    /* Pulsanti a Mattonella Spaziale */
    .stButton>button {
        background: rgba(15, 23, 42, 0.6) !important;
        color: #00f2ff !important;
        border: 1px solid #00f2ff !important;
        border-radius: 20px !important;
        padding: 40px !important;
        font-size: 1.5em !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        transition: all 0.4s ease !important;
        backdrop-filter: blur(10px);
        box-shadow: inset 0 0 15px rgba(0, 242, 255, 0.2);
    }

    .stButton>button:hover {
        background: #00f2ff !important;
        color: #000 !important;
        box-shadow: 0 0 40px #00f2ff !important;
        transform: translateY(-5px);
    }

    /* Card Scadenze Neon */
    .status-card {
        padding: 35px;
        border-radius: 30px;
        text-align: center;
        background: rgba(0, 0, 0, 0.4);
        border: 2px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        transition: 0.5s;
    }
    
    .card-tagl { border-color: #3b82f6; box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    .card-gomme { border-color: #10b981; box-shadow: 0 0 20px rgba(16, 185, 129, 0.3); }

    .valore-neon {
        font-family: 'Orbitron', sans-serif;
        font-size: 38px;
        font-weight: 900;
        margin: 10px 0;
    }
    .val-blue { color: #00d2ff; text-shadow: 0 0 15px #00d2ff; }
    .val-green { color: #00ffaa; text-shadow: 0 0 15px #00ffaa; }

    /* Nascondi Menu Streamlit */
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
    pdf.cell(0, 15, "GOPRESSA SRL - FLIGHT DATA REPORT", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Timestamp: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Unit (Plate): {row['Targa']} | Tech: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"CURRENT ODOMETER: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 10, f"NEXT SERVICE: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"NEXT TIRES: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 10, f"Technical Notes: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGICA NAVIGAZIONE ---
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

def vai_a(nome):
    st.session_state.pagina = nome
    st.rerun()

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p class="sub-title">DEEP SPACE DISPATCHER</p></div>', unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        nome = st.text_input("SBLOCCO IDENTITÀ OPERATORE")
        if st.button("INIZIA MISSIONE"):
            if nome:
                st.session_state.user = nome.upper()
                st.rerun()
    st.stop()

# --- HEADER FISSO ---
st.markdown(f'''
    <div class="header-container">
        <h1 class="main-title">GOPRESSA</h1>
        <p class="sub-title">MISSION CONTROL | OPERATORE: {st.session_state.user}</p>
    </div>
''', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- HOME DASHBOARD ---
if st.session_state.pagina == "home":
    st.markdown("<h4 style='text-align:center; color:#94a3b8; letter-spacing:4px;'>SISTEMI DI BORDO ONLINE</h4>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛠️ REGISTRO\nMANUTENZIONE"): vai_a("manutenzione")
    with col2:
        if st.button("🚨 SEGNALA\nANOMALIA"): vai_a("guasto")
    with col3:
        if st.button("👑 TERMINALE\nAMMINISTRATORE"): vai_a("admin")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 CHIUDI SESSIONE"):
        st.session_state.clear()
        st.rerun()

# --- PAGINA MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ RITORNO AL COMANDO"): vai_a("home")
    
    st.markdown("<h2>🛠 AGGIORNAMENTO DATI VEICOLO</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    t_sel = st.selectbox("🛸 IDENTIFICA UNITÀ (TARGA)", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background:rgba(255, 75, 75, 0.15); padding:25px; border-radius:25px; border:2px solid #ff4b4b; margin-bottom:25px; box-shadow: 0 0 20px rgba(255, 75, 75, 0.4);'>
            🚨 <b>AVVISO CRITICO:</b> Sono stati rilevati guasti attivi per questa unità!
        </div>""", unsafe_allow_html=True)

    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 ODOMETRO ATTUALE (KM):", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='status-card card-tagl'><small>PROIETTA TAGLIANDO</small><br><div class='valore-neon val-blue'>{km_att + 30000} KM</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='status-card card-gomme'><small>PROIETTA GOMME</small><br><div class='valore-neon val-green'>{km_att + 40000} KM</div></div>", unsafe_allow_html=True)

    st.markdown("<br>### 📋 LOG OPERATIVO", unsafe_allow_html=True)
    ch_t = st.checkbox("⚙️ TAGLIANDO MOTORE ESEGUITO")
    ch_g = st.checkbox("🛞 SOSTITUZIONE PNEUMATICI ESEGUITA")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.write("---")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"🛠️ RIPARATO: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("✍️ DESCRIZIONE DETTAGLIATA INTERVENTO")

    if st.button("💾 TRASMETTI DATI AL DATABASE"):
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
        st.success("🛰️ TRASMISSIONE COMPLETATA!")
        st.balloons()

# --- PAGINA SEGNALAZIONE ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ RITORNO AL COMANDO"): vai_a("home")
    st.markdown("<h2>🚨 REGISTRAZIONE ANOMALIA</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("🚛 UNITÀ COINVOLTA", lista_mezzi)
    desc = st.text_area("DETTAGLIA IL MALFUNZIONAMENTO:")
    urg = st.select_slider("LIVELLO DI CRITICITÀ", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("🚀 INVIA REPORT DI ALLERTA"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.error("🚨 SEGNALAZIONE REGISTRATA NEL REGISTRO DI MISSIONE."); vai_a("home")

# --- PAGINA ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ RITORNO AL COMANDO"): vai_a("home")
    st.markdown("<h2>👑 TERMINALE DI COMANDO SUPERIORE</h2>", unsafe_allow_html=True)
    
    if not st.session_state.is_admin:
        pw = st.text_input("CHIAVE DI ACCESSO LIVELLO 1", type="password")
        if st.button("AUTENTICA"):
            if pw == "GSSA2026": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        if st.button("🔒 BLOCCA TERMINALE"): st.session_state.is_admin = False; st.rerun()
        
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")
        
        st.subheader("🛰️ INTERVENTI IN ATTESA DI RISOLUZIONE")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                st.markdown(f"<div style='border-left:5px solid #00f2ff; background:rgba(0,242,255,0.05); padding:15px; border-radius:15px; margin-bottom:10px;'><b>{r['Targa']}</b>: {r['Descrizione']}</div>", unsafe_allow_html=True)
                if st.button(f"RISOLTO: {r['Targa']}##{i}"):
                    df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
        else: st.success("NESSUNA ANOMALIA ATTIVA.")
        
        st.divider()
        st.subheader("📋 ARCHIVIO STORICO DIGITALE")
        t_search = st.selectbox("SELEZIONA UNITÀ", lista_mezzi)
        for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
            st.download_button(f"📄 LOG DATA {r['Data']} ({r['KM_Attuali']} KM)", data=genera_pdf_storico(r), file_name=f"Log_{t_search}.pdf", key=f"p_{i}")
