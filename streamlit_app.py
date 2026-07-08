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

# Soglie manutenzione (km)
S_TAGLIANDO = 30000
S_GOMME = 40000

# Flotta 31 Veicoli
FLOTTA = {
    "GG730AV": "VF7YAANFA12S97743", "GG206JK": "VF7YAANFA12T50337",
    "GG243ZM": "VF7YAANFA12T90153", "GG677RR": "VF7YAANFA12T70979",
    "GG927ZP": "VF7YAANFA12T93188", "GG429ZP": "VF7YAANFA12T91627",
    "GG208ZN": "VF7YAANFA12T90957", "GG790ZL": "VF3YAANFA12T90411",
    "GG075ZP": "VF3YAANFA12T92295", "GG834JH": "VF7YAANFA12T46333",
    "GG736AV": "VF7YAANFA12S86619", "GG477JF": "VF7YAANFA12T42666",
    "HB183CY": "W1VVUCFZ6T4541044", "HB284CY": "W1VVUCFZ0T4541010",
    "HB339CY": "W1VVUCFZ0T4536437", "HB184CY": "W1VVUCFZ4T4543617",
    "GS595DF": "VF3YABPF612Y68182", "GS597DF": "VF3YABPF912Y68581",
    "GZ399JY": "ZFA250003SMB27292", "GZ401JY": "ZFA25000XSMB26849",
    "HA412FV": "VXFVLEHT5SU312069", "HA717DG": "VFEVLEHT8SZ058970",
    "HA630DC": "VF3VLEHT2SZ058981", "HA881MM": "VXFVLEHT1SU319536",
    "GZ249ZS": "VXFVLEHT1SZ044821", "GZ023SB": "VF3VLEHT6S7817160",
    "HA668DG": "VXFVLEHT5SU308023", "HA942FV": "VF3VLEHT3SU320388",
    "HA953FV": "VF3VLEHT2SU318132", "HA957FV": "VF3VLEHT0SU318131",
    "GZ532JY": "ZFA250005SMB27620"
}
LISTA_TARGHE = sorted(list(FLOTTA.keys()))

conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.astype(str)
    except:
        # Se il foglio non esiste, crea dati iniziali
        data = [{"Targa": t, "KM_Attuali": "0", "KM_Gomme": "0", "KM_Tagliando": "0", "Data": "-", "User": "-"} for t in LISTA_TARGHE]
        df_new = pd.DataFrame(data)
        conn.update(worksheet="Manutenzione", data=df_new)
        return df_new.astype(str)

# --- APP ---
if 'user' not in st.session_state:
    st.title("🚚 Accesso GSSA Manutenzione")
    nome = st.text_input("Inserisci Nome e Cognome")
    if st.button("ACCEDI"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

df = carica_dati()

st.title("🛠 Gestione Chilometri")

# 1. Scansione Targa con AI
with st.container(border=True):
    st.write("### 📸 Rilevamento Targa")
    foto = st.camera_input("Inquadra la targa del furgone")
    targa_scelta = LISTA_TARGHE[0]

    if foto:
        with st.spinner("AI sta leggendo la targa..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            img = PIL.Image.open(foto)
            res = model.generate_content(["Leggi la targa di questo furgone. Scrivi SOLO la targa (es: GG123AA). Se non è una targa valida scrivi ERROR.", img])
            testo = res.text.strip().upper().replace(" ", "")
            if testo in LISTA_TARGHE:
                targa_scelta = testo
                st.success(f"Targa rilevata: {testo}")
            else:
                st.warning("Targa non riconosciuta automaticamente. Selezionala dal menu.")

# 2. Selezione e Modifica
targa = st.selectbox("Veicolo:", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_scelta))
idx = df.index[df['Targa'] == targa].tolist()[0]

col1, col2, col3 = st.columns(3)
with col1: km_att = st.number_input("KM Attuali", value=int(df.at[idx, 'KM_Attuali']))
with col2: km_gom = st.number_input("KM Cambio Gomme", value=int(df.at[idx, 'KM_Gomme']))
with col3: km_tag = st.number_input("KM Tagliando", value=int(df.at[idx, 'KM_Tagliando']))

# 3. Allerta Manutenzione
mancano_t = S_TAGLIANDO - (km_att - km_tag)
mancano_g = S_GOMME - (km_att - km_gom)

c1, c2 = st.columns(2)
with c1:
    if mancano_t < 2000: st.error(f"🛑 TAGLIANDO: Scadenza tra {mancano_t} km")
    else: st.success(f"✅ Tagliando OK: Mancano {mancano_t} km")
with c2:
    if mancano_g < 2000: st.warning(f"🚨 GOMME: Scadenza tra {mancano_g} km")
    else: st.success(f"✅ Gomme OK: Mancano {mancano_g} km")

if st.button("💾 SALVA AGGIORNAMENTO", use_container_width=True, type="primary"):
    df.at[idx, 'KM_Attuali'] = str(km_att)
    df.at[idx, 'KM_Gomme'] = str(km_gom)
    df.at[idx, 'KM_Tagliando'] = str(km_tag)
    df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
    df.at[idx, 'User'] = st.session_state.user
    conn.update(worksheet="Manutenzione", data=df)
    st.balloons()
    st.success("Dati salvati sul foglio Manutenzione!")

st.divider()
st.subheader("Stato Flotta")
st.dataframe(df, use_container_width=True, hide_index=True)
