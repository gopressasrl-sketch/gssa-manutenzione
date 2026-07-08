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

# Inizializzazione stato fotocamera
if 'mostra_camera' not in st.session_state:
    st.session_state.mostra_camera = False

# Intervalli Manutenzione
KM_INTERVALLO_TAGLIANDO = 30000
KM_INTERVALLO_GOMME = 40000

FLOTTA = ["GG730AV", "GG206JK", "GG243ZM", "GG677RR", "GG927ZP", "GG429ZP", "GG208ZN", "GG790ZL", "GG075ZP", "GG834JH", "GG736AV", "GG477JF", "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GS595DF", "GS597DF", "GZ399JY", "GZ401JY", "HA412FV", "HA717DG", "HA630DC", "HA881MM", "GZ249ZS", "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "GZ532JY"]
LISTA_TARGHE = sorted(FLOTTA)

conn = st.connection("gsheets", type=GSheetsConnection)

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
        cols = ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Link_Report", "Altro"]
        return pd.DataFrame(columns=cols)

def genera_pdf(targa, km, km_prossimo_t, km_prossimo_g, altro, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REPORT MANUTENZIONE GSSA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {targa} | Operatore: {user}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Chilometri rilevati: {km} km", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {km_prossimo_t} km", ln=True)
    pdf.cell(0, 10, f"PROSSIME GOMME: {km_prossimo_g} km", ln=True)
    pdf.ln(10)
    pdf.cell(0, 10, "NOTE / LAVORI EXTRA:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, altro if altro.strip() != "" else "Nessuna nota.")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.title("🚚 Gestione Flotta GSSA")
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- MENU ---
with st.sidebar:
    st.title("GSSA PRO")
    menu = st.radio("Menu", ["🏠 Inserimento", "👑 Admin"])
    st.write(f"👤 {st.session_state.user}")

df = carica_dati()

if menu == "🏠 Inserimento":
    st.title("🛠 Nuovo Intervento")
    
    # GESTIONE FOTOCAMERA CON PULSANTE
    targa_ocr = None
    
    if not st.session_state.mostra_camera:
        if st.button("📷 APRI FOTOCAMERA PER TARGA"):
            st.session_state.mostra_camera = True
            st.rerun()
    else:
        if st.button("❌ CHIUDI FOTOCAMERA"):
            st.session_state.mostra_camera = False
            st.rerun()
            
        foto = st.camera_input("Scatta una foto alla targa")
        if foto:
            with st.spinner("L'intelligenza artificiale sta leggendo la targa..."):
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(["Leggi la targa, scrivi solo quella.", PIL.Image.open(foto)])
                targa_ocr = res.text.strip().upper().replace(" ", "")
                st.session_state.mostra_camera = False # Chiude la camera dopo lo scatto
                st.success(f"Targa rilevata: {targa_ocr}")

    # Selezione Targa
    targa_init = targa_ocr if targa_ocr in LISTA_TARGHE else LISTA_TARGHE[0]
    targa_sel = st.selectbox("Seleziona Veicolo", LISTA_TARGHE, index=LISTA_TARGHE.index(targa_init))

    if targa_sel in df['Targa'].values:
        idx = df.index[df['Targa'] == targa_sel].tolist()[0]
        
        st.subheader("1. Chilometri Attuali")
        km_att = st.number_input("Inserisci i chilometri del cruscotto:", value=safe_int(df.at[idx, 'KM_Attuali']), step=1)
        
        st.divider()
        
        # Calcolo proiezioni
        km_prossimo_t = km_att + KM_INTERVALLO_TAGLIANDO
        km_prossimo_g = km_att + KM_INTERVALLO_GOMME
        
        st.subheader("2. Scadenze Suggerite")
        c1, c2 = st.columns(2)
        with c1: st.info(f"📅 **Prossimo Tagliando a:**\n{km_prossimo_t} km")
        with c2: st.success(f"🛞 **Prossime Gomme a:**\n{km_prossime_g if 'KM_prossime Gomme' in df.columns else km_prossimo_g} km")

        st.divider()
        
        st.subheader("3. Lavori eseguiti oggi")
        eseguito_tagliando = st.checkbox("✅ Ho fatto il Tagliando oggi")
        eseguite_gomme = st.checkbox("✅ Ho cambiato le Gomme oggi")
        
        altro = st.text_area("📝 Note / Altri lavori (freni, lampadine, ecc...)", value=df.at[idx, 'Altro'] if 'Altro' in df.columns else "")

        if st.button("💾 SALVA E GENERA REPORT", use_container_width=True, type="primary"):
            df.at[idx, 'KM_Attuali'] = str(km_att)
            if eseguito_tagliando:
                df.at[idx, 'KM_Tagliando'] = str(km_att)
                df.at[idx, 'KM_prossimo Tagliando'] = str(km_prossimo_t)
            if eseguite_gomme:
                df.at[idx, 'KM_Gomme'] = str(km_att)
                df.at[idx, 'KM_prossime Gomme'] = str(km_prossimo_g)
                
            df.at[idx, 'Altro'] = altro
            df.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            df.at[idx, 'User'] = st.session_state.user
            df.at[idx, 'Link_Report'] = "Generato"
            
            conn.update(worksheet="Manutenzione", data=df)
            st.success("✅ Database aggiornato!")
            
            pdf_b = genera_pdf(targa_sel, km_att, km_prossimo_t, km_prossimo_g, altro, st.session_state.user)
            st.download_button("📥 SCARICA REPORT PDF", data=pdf_b, file_name=f"Report_{targa_sel}.pdf", mime="application/pdf")
            st.balloons()

elif menu == "👑 Admin":
    st.title("📊 Riepilogo Flotta")
    pw = st.text_input("Password Admin", type="password")
    if pw == "GSSA2026":
        st.dataframe(df, use_container_width=True, hide_index=True)
