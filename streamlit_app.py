import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import base64
from PIL import Image

# --- CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione variabili di stato
if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'show_cam' not in st.session_state: st.session_state.show_cam = False
if 'foto_salvata' not in st.session_state: st.session_state.foto_salvata = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = True 

# --- STILE CSS EXTREME (CANCELLA TUTTE LE ICONE STREAMLIT) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');
    
    /* 1. CANCELLA DEFINITIVAMENTE CORONA, CERCHIETTO BLU E BARRE STRANE */
    #MainMenu, header, footer, [data-testid="stStatusWidget"], .stDeployButton {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Badge "Manage App" Streamlit Cloud */
    .viewerBadge_container__1QSob, .viewerBadge_link__1QSob, div[class^="viewerBadge"] {
        display: none !important;
    }

    /* Rimuove toolbar in alto a destra */
    div[data-testid="stToolbar"] { display: none !important; }

    /* 2. DESIGN DEEP SPACE */
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
        font-size: 1.1em !important; font-weight: 700; text-transform: uppercase !important;
        transition: all 0.4s ease !important; width: 100%;
    }
    .stButton>button:hover { background: #00f2ff !important; color: #000 !important; box-shadow: 0 0 40px #00f2ff !important; }
    
    .status-card { padding: 20px; border-radius: 20px; text-align: center; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
    .val-neon { font-family: 'Orbitron', sans-serif; font-size: 28px; text-shadow: 0 0 10px #00d2ff; color: #00d2ff; }
    
    .danno-card { background: rgba(255, 75, 75, 0.05); border: 1px solid #ff4b4b; padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    .guasto-card { background: rgba(0, 242, 255, 0.05); border: 1px solid #00f2ff; padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0)
        return df.fillna("").astype(str)
    except:
        if foglio == "AnagraficaDriver": return pd.DataFrame(columns=["Nome", "Cognome"])
        if foglio == "DanniDriver": return pd.DataFrame(columns=["Driver", "Targa", "Data", "Descrizione", "Stato", "Operatore", "Foto"])
        if foglio == "Segnalazioni": return pd.DataFrame(columns=["Targa", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto"])
        if foglio == "Manutenzione": return pd.DataFrame(columns=["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"])
        return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img.thumbnail((500, 500))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=60)
    return base64.b64encode(buffered.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GOPRESSA SRL - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 8, f"Mezzo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"KM REGISTRATI: {row['KM_Attuali']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 8, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, f"Note salvate: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

def reset_camera():
    st.session_state.show_cam = False
    st.session_state.foto_salvata = None

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

if not df_drivers.empty and 'Nome' in df_drivers.columns:
    df_drivers['Full'] = df_drivers['Nome'] + " " + df_drivers['Cognome']
    lista_drivers = sorted(df_drivers['Full'].tolist())
else:
    lista_drivers = ["NESSUN DRIVER REGISTRATO"]

# --- NAVIGAZIONE HOME ---
if st.session_state.pagina == "home":
    reset_camera()
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

# --- MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🛠 REGISTRO MANUTENZIONE</h2>", unsafe_allow_html=True)
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
            df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if ch_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y"); df_man.at[idx, 'User'] = st.session_state.user
        conn.update(worksheet="Manutenzione", data=df_man)
        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_att+30000), "KM_prossime_Gomme": str(km_att+40000), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("OK"); st.session_state.pagina = "home"; st.rerun()

# --- SEGNALA DANNO ---
elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>💥 SEGNALA DANNO DRIVER</h2>", unsafe_allow_html=True)
    d_sel = st.selectbox("DRIVER", lista_drivers)
    t_sel = st.selectbox("VEICOLO", lista_mezzi)
    desc = st.text_area("DESCRIZIONE DANNO")
    if not st.session_state.show_cam:
        if st.button("📷 APRI FOTOCAMERA"): st.session_state.show_cam = True; st.rerun()
    else:
        cam_foto = st.camera_input("SCATTA")
        if cam_foto:
            st.session_state.foto_salvata = process_image(cam_foto)
            st.session_state.show_cam = False; st.rerun()
        if st.button("CHIUDI"): st.session_state.show_cam = False; st.rerun()
    if st.session_state.foto_salvata:
        st.image(base64.b64decode(st.session_state.foto_salvata), width=200)
    if st.button("🚀 INVIA REPORT"):
        nuovo_d = pd.DataFrame([{"Driver": d_sel, "Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": desc, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        df_d_v = carica_dati("DanniDriver")
        conn.update(worksheet="DanniDriver", data=pd.concat([df_d_v, nuovo_d], ignore_index=True))
        reset_camera(); st.session_state.pagina = "home"; st.rerun()

# --- SEGNALA GUASTO (CON OPZIONI RICHIESTE) ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>🚨 ANOMALIA MEZZO</h2>", unsafe_allow_html=True)
    t_guasto = st.selectbox("UNITÀ", lista_mezzi)
    
    # OPZIONI RICHIESTE
    st.write("Seleziona i problemi riscontrati:")
    p1 = st.checkbox("Cambio Gomme Anteriore")
    p2 = st.checkbox("Cambio gomme Posteriore")
    p3 = st.checkbox("Pastiglie dei freni")
    p4 = st.checkbox("Tagliando")
    p5 = st.checkbox("Spia motore")
    
    desc_extra = st.text_area("Altre note o dettagli:")
    
    # Unione dei problemi selezionati
    problemi = []
    if p1: problemi.append("Cambio Gomme Anteriore")
    if p2: problemi.append("Cambio gomme Posteriore")
    if p3: problemi.append("Pastiglie dei freni")
    if p4: problemi.append("Tagliando")
    if p5: problemi.append("Spia motore")
    
    desc_finale = ", ".join(problemi)
    if desc_extra:
        desc_finale += " | Note: " + desc_extra

    if not st.session_state.show_cam:
        if st.button("📷 APRI FOTOCAMERA"): st.session_state.show_cam = True; st.rerun()
    else:
        cam_foto = st.camera_input("SCATTA")
        if cam_foto:
            st.session_state.foto_salvata = process_image(cam_foto)
            st.session_state.show_cam = False; st.rerun()
    
    if st.session_state.foto_salvata:
        st.image(base64.b64decode(st.session_state.foto_salvata), width=200)
        
    if st.button("🚀 INVIA ALL'OFFICINA"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc_finale, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.foto_salvata or ""}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        reset_camera(); st.session_state.pagina = "home"; st.rerun()

# --- ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    col_add1, col_add2 = st.columns(2)
    with col_add1:
        with st.expander("🚛 AGGIUNGI VEICOLO"):
            nv = st.text_input("Targa").upper().replace(" ", "")
            if st.button("REGISTRA VEICOLO"):
                nuova_r_t = pd.DataFrame([{"Targa": nv, "KM_Attuali": "0", "KM_Gomme": "0", "KM_prossime Gomme": "0", "KM_Tagliando": "0", "KM_prossimo Tagliando": "0", "Data": "-", "User": "-", "Altro": "-"}])
                conn.update(worksheet="Manutenzione", data=pd.concat([df_man, nuova_r_t], ignore_index=True)); st.rerun()
    with col_add2:
        with st.expander("👤 AGGIUNGI DRIVER"):
            n_n = st.text_input("Nome").upper(); n_c = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"):
                nuova_r = pd.DataFrame([{"Nome": n_n, "Cognome": n_c}])
                df_dr_v = carica_dati("AnagraficaDriver")
                conn.update(worksheet="AnagraficaDriver", data=pd.concat([df_dr_v, nuova_r], ignore_index=True)); st.rerun()

    st.divider()
    df_seg = carica_dati("Segnalazioni")
    df_danni = carica_dati("DanniDriver")
    if not df_seg.empty:
        for i, r in df_seg[df_seg['Stato'] == 'APERTO'].iterrows():
            st.markdown(f'<div class="guasto-card"><b>GUASTO: {r["Targa"]}</b><br>{r["Descrizione"]}</div>', unsafe_allow_html=True)
            if r["Foto"]: st.image(base64.b64decode(r["Foto"]), width=250)
            if st.button(f"CHIUDI GUASTO {r['Targa']}##{i}"):
                df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg)
                idx_m = df_man.index[df_man['Targa'] == r['Targa']].tolist()[0]
                nuovo_s = pd.DataFrame([{"Targa": r['Targa'], "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": df_man.at[idx_m, 'KM_Attuali'], "KM_prossimo_Tagliando": df_man.at[idx_m, 'KM_prossimo Tagliando'], "KM_prossime_Gomme": df_man.at[idx_m, 'KM_prossime Gomme'], "User": st.session_state.user, "Altro": f"RIPARATO: {r['Descrizione']}"}])
                df_sto = carica_dati("Storico")
                conn.update(worksheet="Storico", data=pd.concat([df_sto, nuovo_s], ignore_index=True)); st.rerun()

    if not df_danni.empty:
        for i, r in df_danni[df_danni['Stato'] == 'APERTO'].iterrows():
            st.markdown(f'<div class="danno-card"><b>DANNO DRIVER: {r["Targa"]}</b> | {r["Driver"]}<br>{r["Descrizione"]}</div>', unsafe_allow_html=True)
            if r["Foto"]: st.image(base64.b64decode(r["Foto"]), width=250)
            if st.button(f"PRENDI IN CARICO DANNO {r['Targa']}##{i}"):
                df_danni.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="DanniDriver", data=df_danni); st.rerun()

    st.divider()
    t_search = st.selectbox("VEICOLO", lista_mezzi)
    df_sto_view = carica_dati("Storico")
    for i, r in df_sto_view[df_sto_view['Targa'] == t_search].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"pdf_{i}")
