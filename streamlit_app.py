import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
import base64
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time

# --- 1. CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione variabili
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'foto_salvata', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'is_admin': st.session_state[key] = True
        elif key == 'gallery': st.session_state[key] = {}
        else: st.session_state[key] = None

# --- 2. SUPER CSS PLATINUM EDITION (EFFETTO IPHONE + SPAZIALE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap');
    
    /* PULIZIA TOTALE STREAMLIT */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }

    .stApp {
        background: radial-gradient(circle at top right, #1a1a2e, #000000);
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }

    /* HEADER IPHONE PLATINUM */
    .iphone-header {
        text-align: center;
        padding: 40px 20px;
        background: rgba(255, 255, 255, 0.02);
        backdrop-filter: blur(30px);
        border-radius: 40px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 10px auto 30px auto;
        max-width: 900px;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    }
    .main-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 4em !important;
        font-weight: 900;
        letter-spacing: -2px;
        background: linear-gradient(180deg, #ffffff 30%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* STAT CARDS */
    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 25px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: 0.4s;
    }
    .stat-val { font-family: 'Orbitron', sans-serif; font-size: 2.2em; font-weight: 700; color: #00f2ff; }

    /* BOTTONI PREMIUM */
    .stButton>button {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 22px !important;
        padding: 30px 20px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s cubic-bezier(0, 0, 0.2, 1) !important;
    }
    .stButton>button:hover {
        background: #ffffff !important;
        color: #000000 !important;
        box-shadow: 0 0 30px rgba(255,255,255,0.3) !important;
        transform: translateY(-5px);
    }

    /* SCADENZE CARD */
    .status-card {
        background: #1c1c1e;
        border-radius: 25px;
        padding: 20px;
        border: 1px solid #2c2c2e;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNZIONI CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - OFFICIAL LOG", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Unit: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Ops Note: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"AUTHORIZATION REQUEST - {targa}"
        corpo = f"Buongiorno,\n\nveicolo targato {targa} - KM {km}.\nRichiesta intervento: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown('<div class="iphone-header"><h1 class="main-title">GOPRESSA</h1><p>BIO-METRIC ACCESS</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA TERMINALE"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. DASHBOARD HOME ---
df_man = carica_dati("Manutenzione")
df_seg = carica_dati("Segnalazioni")
df_danni = carica_dati("DanniDriver")
df_rub = carica_dati("RubricaEmail")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP

if st.session_state.pagina == "home":
    # Header con Orologio
    st.markdown(f'''
        <div class="iphone-header">
            <small style="color:#00f2ff; letter-spacing:2px;">{datetime.now().strftime("%H:%M")} | SYSTEM ONLINE</small>
            <h1 class="main-title">GOPRESSA</h1>
            <p style="color:gray;">Mission Commander: {st.session_state.user}</p>
        </div>
    ''', unsafe_allow_html=True)

    # Statistiche Visuali
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='stat-card'><div class='stat-label'>FLOTTA</div><div class='stat-val'>{len(lista_mezzi)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-card'><div class='stat-label'>GUASTI</div><div class='stat-val' style='color:#ff453a'>{len(df_seg[df_seg['Stato']=='APERTO'])}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-card'><div class='stat-label'>DANNI</div><div class='stat-val' style='color:#ff9f0a'>{len(df_danni[df_danni['Stato']=='APERTO'])}</div></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    # Centro di Comando (Pulsanti)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️ REGISTRO MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with col2:
        if st.button("🚨 SEGNALA GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
        if st.button("📊 STATO FLOTTA"): st.session_state.pagina = "status"; st.rerun()
    
    if st.button("👑 TERMINALE AMMINISTRATORE"): st.session_state.pagina = "admin"; st.rerun()
    
    st.write("---")
    if st.button("🚪 DISCONNETTI"): st.session_state.clear(); st.rerun()

# --- PAGINA STATUS ---
elif st.session_state.pagina == "status":
    if st.button("⬅️ DASHBOARD"): st.session_state.pagina = "home"; st.rerun()
    t1, t2 = st.tabs(["🔴 IN ATTESA", "🟢 COMPLETATI"])
    with t1:
        for _, r in df_seg[df_seg['Stato'] == 'APERTO'].iterrows():
            st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b> - {r['Descrizione']}</div>", unsafe_allow_html=True)
    with t2:
        for _, r in df_seg[df_seg['Stato'] == 'CHIUSO'].tail(10).iterrows():
            st.markdown(f"<div class='riparato-card'><b>{r['Targa']}</b> - RIPARATO DA {r['Operatore']}</div>", unsafe_allow_html=True)

# --- PAGINA MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("KILOMETRI ATTUALI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    ch_t = st.checkbox("⚙️ Tagliando fatto"); ch_g = st.checkbox("🛞 Gomme cambiate"); alt = st.text_area("Note:")
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        if ch_t: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if ch_g: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        conn.update(worksheet="Manutenzione", data=df_man)
        st.success("OK"); st.session_state.pagina = "home"; st.rerun()

# --- PAGINA GUASTO ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("UNITÀ", lista_mezzi); km_g = st.number_input("KILOMETRI ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    note = st.text_area("🗒️ ALTRI DANNI O NOTE:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA REPORT"):
        sel = [k for k,v in {"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        nuova = pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova], ignore_index=True)); st.session_state.gallery={}; st.session_state.pagina="home"; st.rerun()

# --- PAGINA DANNO ---
elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    df_d = carica_dati("AnagraficaDriver")
    l_d = (df_d['Nome'] + " " + df_d['Cognome']).tolist() if not df_d.empty else ["NESSUN DRIVER"]
    d_s = st.selectbox("DRIVER", l_d); t_s = st.selectbox("VEICOLO", lista_mezzi); ds = st.text_area("DANNO")
    if not st.session_state.show_cam:
        if st.button("📷 FOTO DANNO"): st.session_state.show_cam=True; st.rerun()
    else:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.foto_salvata = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        nuo = pd.DataFrame([{"Driver": d_s, "Targa": t_s, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": ds, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), nuo], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

# --- PAGINA ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("### ➕ AGGIUNTA DATI")
    ca, cb, cc = st.columns(3)
    with ca:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA"): pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0"}])], ignore_index=True); st.rerun()
    with cb:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA"): pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True); st.rerun()
    with cc:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto").upper(); ee = st.text_input("Email")
            if st.button("SALVA"): pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True); st.rerun()

    st.divider(); df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico"); df_danni = carica_dati("DanniDriver")
    rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
    
    # GUASTI
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Guasto: {dg['Descrizione']}")
            c = st.columns(6); fl = ["Gen", "Gomme", "Spia", "KM", "Targa", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", list(rub_dict.keys()), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], {fl[i]: dg.get(fc[i], "") for i in range(6)}): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

    st.divider(); t_s = st.selectbox("STORICO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
