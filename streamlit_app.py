import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GOPRESSA PRO", layout="wide", initial_sidebar_state="collapsed")

# --- STILE CSS AVANZATO (DESIGN 2026) ---
st.markdown("""
    <style>
    /* Sfondo Generale con Brand */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #1c1f26 100%);
    }
    
    /* Header Superiore Gopressa */
    .gopressa-header {
        background: rgba(255, 75, 75, 0.1);
        padding: 20px;
        border-radius: 0 0 20px 20px;
        border-bottom: 2px solid #ff4b4b;
        text-align: center;
        margin-bottom: 30px;
    }
    
    .gopressa-header h1 {
        color: #ff4b4b !important;
        margin: 0;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: 2px;
        font-weight: 800;
    }
    
    .gopressa-header p {
        color: #808495;
        margin: 0;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.9em;
    }

    /* Card di Sezione */
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background: rgba(30, 34, 45, 0.7) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        padding: 25px !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Styling Menu Laterale */
    section[data-testid="stSidebar"] {
        background-color: #11141a !important;
        border-right: 1px solid #ff4b4b !important;
    }
    
    /* Testo per facilitare l'apertura menu */
    .menu-hint {
        position: fixed;
        top: 15px;
        left: 55px;
        color: #ff4b4b;
        font-weight: bold;
        z-index: 1000;
        font-size: 0.8em;
    }

    /* Pulsanti Moderni */
    .stButton>button {
        background: linear-gradient(90deg, #ff4b4b 0%, #ff7676 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(255, 75, 75, 0.4) !important;
    }

    /* Box Scadenze */
    .scadenza-box {
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .tagliando { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); }
    .gomme { background: linear-gradient(135deg, #064e3b 0%, #10b981 100%); }
    
    /* Nascondi Elementi Standard Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    
    <!-- Testo aiuto per il menu -->
    <div class="menu-hint">⬅️ TOCCA QUI PER IL MENU</div>
    """, unsafe_allow_html=True)

# --- HEADER FISSO ---
st.markdown("""
    <div class="gopressa-header">
        <h1>GOPRESSA SRL</h1>
        <p>Dispacher Portal & Fleet Management</p>
    </div>
    """, unsafe_allow_html=True)

# --- LOGICA DI SESSIONE ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

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
    pdf.multi_cell(0, 8, f"Dettagli: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    with st.container():
        st.markdown("<h2 style='text-align:center;'>Accesso Operatore</h2>", unsafe_allow_html=True)
        nome = st.text_input("Inserisci Nome e Cognome")
        if st.button("ENTRA NEL PORTALE", use_container_width=True):
            if nome:
                st.session_state.user = nome.upper()
                st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"<h2 style='color:#ff4b4b;'>GOPRESSA</h2>", unsafe_allow_html=True)
    st.write(f"👤 **{st.session_state.user}**")
    st.divider()
    menu = st.radio("VAI A:", ["🏠 Registro Manutenzione", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    st.divider()
    if st.button("Disconnetti"):
        st.session_state.clear()
        st.rerun()

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- PAGINA 1: MANUTENZIONE ---
if menu == "🏠 Registro Manutenzione":
    st.markdown("<h2>🛠 Registro Interventi</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    
    t_sel = st.selectbox("🚛 Seleziona Veicolo:", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background-color:rgba(255, 75, 75, 0.2); border:1px solid #ff4b4b; padding:15px; border-radius:10px; color:#ffbcbc; margin-bottom:15px;'>
            🚨 <b>NOTIFICA OFFICINA:</b> Ci sono {len(guasti_aperti)} problemi segnalati per questo mezzo!
        </div>""", unsafe_allow_html=True)

    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("📟 KM Attuali (Cruscotto):", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<div class='scadenza-box tagliando'><small>PROSSIMO TAGLIANDO</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='scadenza-box gomme'><small>PROSSIME GOMME</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    st.markdown("### Lavori del giorno")
    c1, c2 = st.columns(2)
    ch_t = c1.checkbox("⚙️ Tagliando fatto")
    ch_g = c2.checkbox("🛞 Gomme cambiate")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.write("---")
        st.write("🔧 Riparazioni extra:")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("Note dell'operatore:")

    if st.button("💾 REGISTRA INTERVENTO", use_container_width=True):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if ch_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if ch_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        if lavori_chiusi:
            for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_pross_t), "KM_prossime_Gomme": str(km_pross_g), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Manutenzione", data=df_man)
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("✅ Salvataggio completato!"); st.balloons()

# --- PAGINA 2: SEGNALAZIONE ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h2>⚠️ Report Danni / Guasti</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("Quale mezzo ha il problema?", lista_mezzi)
    desc = st.text_area("Descrivi il guasto nel dettaglio:")
    urg = st.select_slider("Urgenza:", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("INVIA SEGNALAZIONE IN OFFICINA", use_container_width=True):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.warning("⚠️ Segnalazione Inviata.")

# --- PAGINA 3: ADMIN & ARCHIVIO ---
elif menu == "📋 Archivio & Admin":
    st.markdown("<h2>📋 Pannello di Controllo</h2>", unsafe_allow_html=True)
    if not st.session_state.is_admin:
        pwd = st.text_input("Password Amministratore", type="password")
        if st.button("ACCEDI"):
            if pwd == "GSSA2026": st.session_state.is_admin = True; st.rerun()
            else: st.error("Accesso negato.")

    if st.session_state.is_admin:
        if st.button("🔒 Blocca Dashboard"): st.session_state.is_admin = False; st.rerun()
        
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")

        st.subheader("🚨 Guasti Attivi in Flotta")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                st.markdown(f"<div style='border-left:5px solid #ff4b4b; padding:10px; background:rgba(255,255,255,0.05); border-radius:10px; margin-bottom:10px;'><b>{r['Targa']}</b>: {r['Descrizione']} <br><small>Segnalato il {r['Data_Segnalazione']}</small></div>", unsafe_allow_html=True)
                if st.button(f"Sistemato: {r['Targa']}", key=f"adm_{i}"):
                    df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
        else: st.success("Nessun guasto aperto.")

        st.divider()
        t_search = st.selectbox("Scegli mezzo per vedere la storia:", lista_mezzi)
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("**Eventi segnalati:**")
            for _, r in df_seg[df_seg['Targa'] == t_search].sort_index(ascending=False).iterrows():
                tag = "🟢 Riparato" if r['Stato'] == 'CHIUSO' else "🔴 Aperto"
                st.markdown(f"<small>{r['Data_Segnalazione']}: {r['Descrizione']} | {tag}</small>", unsafe_allow_html=True)
        with c_b:
            st.write("**Report Manutenzione:**")
            for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
                st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"pdf_{i}")
