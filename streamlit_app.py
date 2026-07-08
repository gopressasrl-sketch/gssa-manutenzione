import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione navigazione
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- STILE CSS DEEP SPACE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
        background-attachment: fixed; color: #f8fafc; font-family: 'Rajdhani', sans-serif;
    }
    .header-container {
        text-align: center; padding: 30px; background: rgba(255, 255, 255, 0.02);
        border-radius: 40px; border: 1px solid rgba(0, 255, 255, 0.2);
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.1); margin-bottom: 20px; backdrop-filter: blur(10px);
    }
    .main-title {
        font-family: 'Orbitron', sans-serif; font-size: 3.5em !important; font-weight: 900;
        background: linear-gradient(to right, #00d2ff, #3a7bd5, #ff4b4b);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 8px;
    }
    .stButton>button {
        background: rgba(15, 23, 42, 0.6) !important; color: #00f2ff !important;
        border: 1px solid #00f2ff !important; border-radius: 20px !important; padding: 25px !important;
        font-size: 1.2em !important; font-weight: 700; text-transform: uppercase !important;
        transition: all 0.4s ease !important; width: 100%;
    }
    .stButton>button:hover { background: #00f2ff !important; color: #000 !important; box-shadow: 0 0 40px #00f2ff !important; }
    
    .status-card { padding: 20px; border-radius: 20px; text-align: center; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
    .val-neon { font-family: 'Orbitron', sans-serif; font-size: 28px; text-shadow: 0 0 10px #00d2ff; color: #00d2ff; }
    
    .danno-card { background: rgba(255, 75, 75, 0.05); border: 1px solid #ff4b4b; padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    .ritardo-alert { background: rgba(255, 0, 0, 0.2); border: 2px solid #ff0000; animation: blink 2s infinite; }
    @keyframes blink { 0% {opacity: 1;} 50% {opacity: 0.6;} 100% {opacity: 1;} }

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

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>MISSION CONTROL ACCESS</p></div>', unsafe_allow_html=True)
    nome_input = st.text_input("IDENTIFICAZIONE OPERATORE")
    if st.button("INIZIA MISSIONE"):
        if nome_input: st.session_state.user = nome_input.upper(); st.rerun()
    st.stop()

# --- HEADER FISSO ---
st.markdown(f'<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>UNIT: {st.session_state.user}</p></div>', unsafe_allow_html=True)

# CARICAMENTO DATI
df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# Creazione lista driver "Nome Cognome"
if not df_drivers.empty and 'Nome' in df_drivers.columns:
    df_drivers['Full'] = df_drivers['Nome'] + " " + df_drivers['Cognome']
    lista_drivers = sorted(df_drivers['Full'].tolist())
else:
    lista_drivers = ["NESSUN DRIVER REGISTRATO"]

# --- HOME DASHBOARD ---
if st.session_state.pagina == "home":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🛠️ MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
    with col2:
        if st.button("🚨 SEGNALA GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
    with col3:
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with col4:
        if st.button("👑 ADMIN"): st.session_state.pagina = "admin"; st.rerun()
    
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- PAGINA MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ TORNA AL MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🛠 REGISTRO INTERVENTO</h2>", unsafe_allow_html=True)
    t_sel = st.selectbox("🚛 SELEZIONA MEZZO", lista_mezzi)
    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 KM ATTUALI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)

    ch_t = st.checkbox("⚙️ Tagliando fatto")
    ch_g = st.checkbox("🛞 Gomme cambiate")
    altro = st.text_area("Note:")

    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if ch_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if ch_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        conn.update(worksheet="Manutenzione", data=df_man)
        # Salvataggio storico
        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_att+30000), "KM_prossime_Gomme": str(km_att+40000), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("REGISTRATO"); st.session_state.pagina = "home"; st.rerun()

# --- PAGINA SEGNALA DANNO ---
elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>💥 SEGNALA DANNO DRIVER</h2>", unsafe_allow_html=True)
    d_sel = st.selectbox("CHI HA CAUSATO IL DANNO?", lista_drivers)
    t_sel = st.selectbox("VEICOLO COINVOLTO", lista_mezzi)
    desc = st.text_area("DESCRIZIONE DEL DANNO")
    if st.button("INVIA REPORT DANNO"):
        nuovo_d = pd.DataFrame([{"Driver": d_sel, "Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": desc, "Stato": "APERTO", "Operatore": st.session_state.user}])
        df_d_v = carica_dati("DanniDriver")
        conn.update(worksheet="DanniDriver", data=pd.concat([df_d_v, nuovo_d], ignore_index=True))
        st.error("🚨 SEGNALAZIONE ARCHIVIATA."); st.session_state.pagina = "home"; st.rerun()

# --- PAGINA SEGNALA GUASTO ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🚨 SEGNALAZIONE ANOMALIA MEZZO</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("UNITÀ", lista_mezzi)
    desc = st.text_area("COSA C'È DA RIPARARE?")
    if st.button("INVIA ALL'OFFICINA"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.warning("NOTIFICATO"); st.session_state.pagina = "home"; st.rerun()

# --- PAGINA ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    if not st.session_state.is_admin:
        pw = st.text_input("CHIAVE DI ACCESSO", type="password")
        if st.button("AUTENTICA"):
            if pw == "GSSA2026": st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        st.markdown("<h2>👑 COMANDO ADMIN</h2>", unsafe_allow_html=True)
        
        # AGGIUNTA DRIVER (NOME E COGNOME)
        with st.expander("👤 AGGIUNGI NUOVO DRIVER NELL'ANAGRAFICA"):
            c_n1, c_n2 = st.columns(2)
            n_nome = c_n1.text_input("Nome").upper()
            n_cognome = c_n2.text_input("Cognome").upper()
            if st.button("SALVA NUOVO DRIVER"):
                if n_nome and n_cognome:
                    nuova_r = pd.DataFrame([{"Nome": n_nome, "Cognome": n_cognome}])
                    df_dr_v = carica_dati("AnagraficaDriver")
                    conn.update(worksheet="AnagraficaDriver", data=pd.concat([df_dr_v, nuova_r], ignore_index=True))
                    st.success("DRIVER AGGIUNTO"); st.rerun()

        st.divider()
        
        # GESTIONE DANNI (CON ALERT 24H)
        st.subheader("💥 DANNI DRIVER DA PRENDERE IN CARICO")
        df_danni = carica_dati("DanniDriver")
        if not df_danni.empty:
            for i, r in df_danni[df_danni['Stato'] == 'APERTO'].iterrows():
                try:
                    data_d = datetime.strptime(r['Data'], "%d/%m/%Y %H:%M")
                    ritardo = (datetime.now() - data_d).total_seconds() > 86400
                except: ritardo = False
                
                classe = "ritardo-alert" if ritardo else ""
                st.markdown(f'<div class="danno-card {classe}"><b>{r["Targa"]}</b> | Driver: <b>{r["Driver"]}</b><br>{r["Descrizione"]}<br><small>Segnalato il {r["Data"]} {"| 🚨 <b>NON GESTITO DA > 24H</b>" if ritardo else ""}</small></div>', unsafe_allow_html=True)
                if st.button(f"PRENDI IN CARICO {r['Targa']}##{i}"):
                    df_danni.at[i, 'Stato'] = 'PRESO IN CARICO'
                    conn.update(worksheet="DanniDriver", data=df_danni)
                    st.rerun()
        else: st.success("NESSUN DANNO PENDING.")
