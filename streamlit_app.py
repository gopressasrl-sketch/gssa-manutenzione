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

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Costanti
INTERVALLO_TAGLIANDO = 30000
SOGLIA_GOMME = 40000

FLOTTA = ["GG730AV", "GG206JK", "GG243ZM", "GG677RR", "GG927ZP", "GG429ZP", "GG208ZN", "GG790ZL", "GG075ZP", "GG834JH", "GG736AV", "GG477JF", "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GS595DF", "GS597DF", "GZ399JY", "GZ401JY", "HA412FV", "HA717DG", "HA630DC", "HA881MM", "GZ249ZS", "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "GZ532JY"]
LISTA_TARGHE = sorted(FLOTTA)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNZIONI UTILI ---
def safe_int(val):
    try:
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "None"]: return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def carica_dati():
    try:
        df = conn.read(worksheet="Manutenzione", ttl=0)
        return df.astype(str)
    except:
        return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"])

def genera_pdf(targa, km, km_tag, km_prossimo, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORT MANUTENZIONE VEICOLO GSSA", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 10, f"Veicolo (Targa): {targa}", ln=True)
    pdf.cell(0, 10, f"Operatore: {user}", ln=True)
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, "DETTAGLI INTERVENTO", ln=True, fill=True)
    pdf.cell(0, 10, f"Chilometraggio Attuale: {km} km", ln=True)
    pdf.cell(0, 10, f"Ultimo Tagliando Eseguito a: {km_tag} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO PREVISTO A: {km_prossimo} km", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "NOTE E ALTRI LAVORI:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, altro if altro.strip() != "" else "Nessun lavoro extra dichiarato.")
    
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.title("🚚 Sistema Manutenzione GSSA")
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- MENU LATERALE ---
with st.sidebar:
    st.title("GSSA PRO")
    st.write(f"👤 {st.session_state.user}")
    menu = st.radio("Menu", ["🏠 Inserimento", "👑 Pannello Admin"])
    if st.button("Logout"):
        del st.session_state.user
        st.rerun()

df = carica_dati()

# --- PAGINA INSERIMENTO ---
if menu == "🏠 Inserimento":
    st.title("🛠 Aggiornamento Manutenzione")

    with st.container(border=True):
        col_cam, col_sel = st.columns([1, 1])
        with col_cam:
            foto = st.camera_input("📸 Scansiona Targa")
            targa_ocr = None
            if foto:
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(["Leggi la targa del furgone, scrivi solo la targa.", PIL.Image.open(foto)])
                targa_ocr = res.text.strip().upper().replace(" ", "")
        
        with col_sel:
            targa_init = targa_ocr if targa_ocr in LISTA_TARGHE else LISTA_TARGHE[0]
            targa_selezionata = st.selectbox("Seleziona Veicolo Manualmente", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_init))

    if targa_selezionata in df['Targa'].values:
        idx = df.index[df['Targa'] == targa_selezionata].tolist()[0]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            km_att = st.number_input("KM Attuali Mezzo", value=safe_int(df.at[idx, 'KM_Attuali']))
        with c2:
            km_tag = st.number_input("KM Ultimo Tagliando", value=safe_int(df.at[idx, 'KM_Tagliando']))
        with c3:
            km_gom = st.number_input("KM Ultimo Cambio Gomme", value=safe_int(df.at[idx, 'KM_Gomme']))

        # Calcoli Automatici
        km_prossimo = km_tag + INTERVALLO_TAGLIANDO
        st.info(f"📅 **Prossimo Tagliando suggerito a: {km_prossimo} km**")

        altro = st.text_area("📝 Altri lavori eseguiti (es. freni, lampadine, olio...)", value=df.at[idx, 'Altro'] if 'Altro' in df.columns else "")

        if st.button("💾 SALVA E GENERA REPORT", use_container_width=True, type="primary"):
            df.at[idx, 'KM_Attuali'] = str(km_att)
            df.at[idx, 'KM_Tagliando'] = str(km_tag)
            df.at[idx, 'KM_Gomme'] = str(km_gom)
            df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo)
            df.at[idx, 'Altro'] = altro
            df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            df.at[idx, 'User'] = st.session_state.user
            
            conn.update(worksheet="Manutenzione", data=df)
            st.success("Dati salvati nel Database!")
            
            # Generazione PDF
            pdf_bytes = genera_pdf(targa_selezionata, km_att, km_tag, km_prossimo, altro, st.session_state.user)
            st.download_button(label="📥 SCARICA REPORT PDF", data=pdf_bytes, file_name=f"Report_{targa_selezionata}.pdf", mime="application/pdf")
            st.balloons()

# --- PAGINA ADMIN ---
elif menu == "👑 Pannello Admin":
    st.title("📊 Riepilogo Flotta Completa")
    password = st.text_input("Inserisci Password Admin", type="password")
    
    if password == "GSSA2026":
        st.write("Qui puoi vedere lo stato di tutti i 31 veicoli:")
        
        # Formattazione per la tabella
        df_display = df.copy()
        if 'KM_prossimo Tagliando' in df_display.columns:
            # Evidenzia chi è vicino alla scadenza
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Esportazione Excel veloce
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Esporta tutto in CSV", csv, "flotta_gssa.csv", "text/csv")
    elif password != "":
        st.error("Password Errata")
