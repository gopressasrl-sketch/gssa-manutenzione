import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import PIL.Image

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="GSSA MANUTENZIONE", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

S_TAGLIANDO = 30000
S_GOMME = 40000

FLOTTA = ["GG730AV", "GG206JK", "GG243ZM", "GG677RR", "GG927ZP", "GG429ZP", "GG208ZN", "GG790ZL", "GG075ZP", "GG834JH", "GG736AV", "GG477JF", "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GS595DF", "GS597DF", "GZ399JY", "GZ401JY", "HA412FV", "HA717DG", "HA630DC", "HA881MM", "GZ249ZS", "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "GZ532JY"]
LISTA_TARGHE = sorted(FLOTTA)

conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    """Converte in modo sicuro qualsiasi valore in intero, ritornando 0 se fallisce"""
    try:
        if pd.isna(val) or str(val).strip() == "" or str(val).strip() == "-":
            return 0
        return int(float(str(val).replace(',', '.')))
    except:
        return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_Tagliando", "Data", "User"])

# --- LOGIN ---
if 'user' not in st.session_state:
    st.title("🚚 Accesso GSSA")
    nome = st.text_input("Tuo Nome e Cognome")
    if st.button("ENTRA"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

df = carica_dati()

st.title("🛠 Gestione Manutenzione")

# 1. Scansione Targa con AI
with st.expander("📸 SCANSIONA TARGA", expanded=False):
    foto = st.camera_input("Inquadra la targa")
    targa_scelta_ai = None
    if foto:
        with st.spinner("AI sta leggendo..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            img = PIL.Image.open(foto)
            res = model.generate_content(["Scrivi solo la targa (es: GG123AA).", img])
            targa_scelta_ai = res.text.strip().upper().replace(" ", "")

# 2. Selezione Veicolo
targa_default = targa_scelta_ai if targa_scelta_ai in LISTA_TARGHE else LISTA_TARGHE[0]
targa_selezionata = st.selectbox("Seleziona Veicolo:", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_default))

st.divider()

# 3. Controllo se la targa esiste
if not df.empty and targa_selezionata in df['Targa'].values:
    idx = df.index[df['Targa'] == targa_selezionata].tolist()[0]
    
    # Recupero KM usando la funzione sicura safe_int
    v_km_att = safe_int(df.at[idx, 'KM_Attuali'])
    v_km_gom = safe_int(df.at[idx, 'KM_Gomme'])
    v_km_tag = safe_int(df.at[idx, 'KM_Tagliando'])

    col1, col2, col3 = st.columns(3)
    with col1: km_att = st.number_input("KM Attuali", value=v_km_att, step=1)
    with col2: km_gom = st.number_input("KM Cambio Gomme", value=v_km_gom, step=1)
    with col3: km_tag = st.number_input("KM Tagliando", value=v_km_tag, step=1)

    # Calcolo Allerta
    mancano_t = S_TAGLIANDO - (km_att - km_tag)
    mancano_g = S_GOMME - (km_att - km_gom)

    c1, c2 = st.columns(2)
    with c1:
        if mancano_t < 2000: st.error(f"🛑 TAGLIANDO: {mancano_t} km rimasti")
        else: st.success(f"✅ Tagliando OK: {mancano_t} km rimasti")
    with c2:
        if mancano_g < 2000: st.warning(f"🚨 GOMME: {mancano_g} km rimasti")
        else: st.success(f"✅ Gomme OK: {mancano_g} km rimasti")

    if st.button("💾 SALVA AGGIORNAMENTO", use_container_width=True, type="primary"):
        df.at[idx, 'KM_Attuali'] = str(km_att)
        df.at[idx, 'KM_Gomme'] = str(km_gom)
        df.at[idx, 'KM_Tagliando'] = str(km_tag)
        df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df.at[idx, 'User'] = st.session_state.user
        
        conn.update(worksheet="Manutenzione", data=df)
        st.balloons()
        st.success(f"Dati salvati per {targa_selezionata}!")
else:
    st.warning(f"⚠️ La targa {targa_selezionata} non è nel foglio.")
    if st.button("Aggiungi targa al foglio"):
        nuova_riga = pd.DataFrame([{"Targa": targa_selezionata, "KM_Attuali": "0", "KM_Gomme": "0", "KM_Tagliando": "0", "Data": "-", "User": "-"}])
        df = pd.concat([df, nuova_riga], ignore_index=True)
        conn.update(worksheet="Manutenzione", data=df)
        st.rerun()

st.divider()
st.subheader("📊 Riepilogo Flotta")
st.dataframe(df, use_container_width=True, hide_index=True)
