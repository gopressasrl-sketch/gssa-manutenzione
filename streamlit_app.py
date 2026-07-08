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

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNZIONI CORE ---
def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except:
        return pd.DataFrame()

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
    menu = st.radio("Scegli operazione:", ["🏠 Nuovo Intervento", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    if st.button("Esci"):
        del st.session_state.user
        st.rerun()

# --- PAGINA 1: NUOVO INTERVENTO (MANUTENZIONE) ---
if menu == "🏠 Nuovo Intervento":
    df_man = carica_dati("Manutenzione")
    df_seg = carica_dati("Segnalazioni")
    st.markdown("<h1>🛠 Registro Manutenzione</h1>", unsafe_allow_html=True)
    
    # Selezione veicolo
    lista_t = sorted(df_man['Targa'].unique()) if not df_man.empty else ["GG730AV"]
    t_sel = st.selectbox("Seleziona Veicolo", lista_t)
    
    # --- ALERT GUASTI APERTI ---
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"<div class='alert-guasto'>⚠️ <b>ATTENZIONE!</b> Ci sono {len(guasti_aperti)} guasti segnalati per questo mezzo:</div>", unsafe_allow_html=True)
        for _, g in guasti_aperti.iterrows():
            st.write(f"• **{g['Data_Segnalazione']}**: {g['Descrizione']} (Urgenza: {g['Urgenza']})")

    st.divider()
    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("Chilometri oggi", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    
    col1, col2 = st.columns(2)
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    col1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    check_t = st.checkbox("⚙️ Tagliando completato")
    check_g = st.checkbox("🛞 Cambio gomme completato")
    
    # Se ci sono guasti, permetti di chiuderli
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.markdown("### Riparazione Guasti Segnalati")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Ho riparato: {g['Descrizione']}", key=f"check_{i}"):
                lavori_chiusi.append(i)

    altro = st.text_area("Note aggiuntive")

    if st.button("💾 SALVA INTERVENTO", use_container_width=True, type="primary"):
        # Aggiorna Manutenzione
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if check_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        
        # Chiudi guasti nel foglio segnalazioni
        if lavori_chiusi:
            for idx_g in lavori_chiusi:
                df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        conn.update(worksheet="Manutenzione", data=df_man)
        st.success("✅ Tutto salvato e guasti aggiornati!")
        st.balloons()

# --- PAGINA 2: SEGNALA GUASTO (NUOVA!) ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h1>⚠️ Segnalazione Nuovo Guasto</h1>", unsafe_allow_html=True)
    df_man = carica_dati("Manutenzione")
    
    t_guasto = st.selectbox("Veicolo con problema", sorted(df_man['Targa'].unique()))
    desc = st.text_area("Descrizione del problema (es. Lampadina fulminata, Gomme lisce, Specchietto rotto...)")
    urg = st.select_slider("Livello Urgenza", options=["BASSA", "MEDIA", "ALTA"])
    
    if st.button("INVIA SEGNALAZIONE ALL'OFFICINA", use_container_width=True, type="primary"):
        nuova_seg = pd.DataFrame([{
            "Targa": t_guasto,
            "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"),
            "Descrizione": desc,
            "Urgenza": urg,
            "Operatore": st.session_state.user,
            "Stato": "APERTO"
        }])
        
        df_seg_vecchio = carica_dati("Segnalazioni")
        df_seg_nuovo = pd.concat([df_seg_vecchio, nuova_seg], ignore_index=True)
        conn.update(worksheet="Segnalazioni", data=df_seg_nuovo)
        st.error(f"Segnalazione inviata per il mezzo {t_guasto}!")

# --- PAGINA 3: ARCHIVIO & ADMIN (CON ALERT 2 GIORNI) ---
elif menu == "📋 Archivio & Admin":
    st.markdown("<h1>📋 Dashboard Amministrativa</h1>", unsafe_allow_html=True)
    if st.text_input("Password", type="password") == "GSSA2026":
        df_seg = carica_dati("Segnalazioni")
        
        st.subheader("🛠 Lavori da eseguire (Guasti Aperti)")
        
        if not df_seg.empty:
            df_aperti = df_seg[df_seg['Stato'] == 'APERTO'].copy()
            
            # Calcolo dei 2 giorni
            def check_ritardo(data_str):
                try:
                    data_seg = datetime.strptime(data_str, "%d/%m/%Y")
                    return (datetime.now() - data_seg).days >= 2
                except: return False

            df_aperti['Scaduto'] = df_aperti['Data_Segnalazione'].apply(check_ritardo)
            
            # Visualizzazione con evidenziatore per i ritardi
            for i, r in df_aperti.iterrows():
                colore = "#ff4b4b" if r['Scaduto'] else "#3b82f6"
                emoji = "🚨 SCADUTO (Oltre 48h)" if r['Scaduto'] else "⏳ In tempo"
                
                with st.container():
                    st.markdown(f"""
                    <div style='border: 1px solid {colore}; padding:15px; border-radius:10px; margin-bottom:10px;'>
                        <b style='color:{colore}'>{r['Targa']}</b> - {r['Descrizione']}<br>
                        <small>Segnalato il: {r['Data_Segnalazione']} da {r['Operatore']} | <b>{emoji}</b></small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.success("Nessun guasto aperto!")
