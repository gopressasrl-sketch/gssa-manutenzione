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

# --- 1. CONFIGURAZIONE SISTEMA ---
st.set_page_config(page_title="GOPRESSA PRO MAX", layout="wide", initial_sidebar_state="collapsed")

if 'pagina' not in st.session_state: st.session_state.pagina = "home"
if 'show_cam' not in st.session_state: st.session_state.show_cam = False
if 'is_admin' not in st.session_state: st.session_state.is_admin = True
if 'user' not in st.session_state: st.session_state.user = None
if 'gallery' not in st.session_state: st.session_state.gallery = {}
if 'foto_salvata' not in st.session_state: st.session_state.foto_salvata = None

# --- 2. DESIGN IPHONE PLATINUM (CSS AVANZATO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* PULIZIA TOTALE STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] { 
        display: none !important; visibility: hidden !important; 
    }

    .stApp {
        background: #000000;
        color: #ffffff;
        font-family: 'Inter', -apple-system, sans-serif;
    }

    /* HEADER IPHONE STYLE */
    .iphone-header {
        text-align: center;
        padding: 50px 20px 30px 20px;
        background: linear-gradient(180deg, rgba(28,28,30,0.8) 0%, rgba(0,0,0,0) 100%);
        margin-bottom: 20px;
    }
    .iphone-header h1 {
        font-size: 3em !important;
        font-weight: 700;
        letter-spacing: -1.5px;
        margin-bottom: 5px;
    }
    .iphone-header p {
        color: #8e8e93;
        font-size: 1.1em;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* MENU CARDS (BOTTONI PROFESSIONALI) */
    .stButton>button {
        background: #1c1c1e !important;
        color: #ffffff !important;
        border: 1px solid #2c2c2e !important;
        border-radius: 22px !important;
        padding: 35px 25px !important;
        text-align: left !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        margin-bottom: 12px !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }
    
    .stButton>button:hover {
        background: #2c2c2e !important;
        border-color: #3a3a3c !important;
        transform: scale(0.99);
    }

    .stButton>button p {
        font-size: 1.3em !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }

    /* BOX SCADENZE */
    .status-card {
        padding: 25px;
        border-radius: 25px;
        text-align: center;
        background: #1c1c1e;
        border: 1px solid #2c2c2e;
        margin-bottom: 15px;
    }
    .val-neon { font-size: 28px; font-weight: 700; color: #0a84ff; }

    /* TABS IOS */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c1c1e;
        border-radius: 15px;
        color: white;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #0a84ff !important; }

    /* SEGNALAZIONI CARD */
    .guasto-card { background: rgba(255, 69, 58, 0.1); border: 1px solid #ff453a; padding: 20px; border-radius: 25px; margin-bottom: 15px; }
    .riparato-card { background: rgba(52, 199, 89, 0.1); border: 1px solid #34c759; padding: 20px; border-radius: 25px; margin-bottom: 15px; }

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
        strutture = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "KM_prossimo_Tagliando", "KM_prossime_Gomme", "User", "Altro"],
            "AnagraficaDriver": ["Nome", "Cognome"],
            "DanniDriver": ["Driver", "Targa", "Data", "Descrizione", "Stato", "Operatore", "Foto"],
            "RubricaEmail": ["Nome", "Email"]
        }
        if foglio in strutture:
            for col in strutture[foglio]:
                if col not in df.columns: df[col] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Note: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo targato {targa} - KM {km}.\nIntervento richiesto: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="iphone-header"><h1>GOPRESSA</h1><p>Control Center</p></div>', unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1])
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="iphone-header"><h1>GOPRESSA</h1><p>Operatore: {st.session_state.user}</p></div>', unsafe_allow_html=True)

# DATI
df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
df_rub = carica_dati("RubricaEmail")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME (MENU PROFESSIONALE) ---
if st.session_state.pagina == "home":
    st.markdown("<div style='max-width:600px; margin: 0 auto;'>", unsafe_allow_html=True)
    if st.button("🛠️ REGISTRO MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
    if st.button("🚨 SEGNALA UN GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
    if st.button("💥 SEGNALA DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    if st.button("📊 STATO DELLA FLOTTA"): st.session_state.pagina = "status"; st.rerun()
    if st.button("👑 AREA AMMINISTRATORE"): st.session_state.pagina = "admin"; st.rerun()
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT UTENTE"): st.session_state.clear(); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- PAGINA STATO FLOTTA ---
elif st.session_state.pagina == "status":
    if st.button("⬅️ INDIETRO"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>📊 Monitoraggio Flotta</h2>", unsafe_allow_html=True)
    df_seg = carica_dati("Segnalazioni")
    t1, t2 = st.tabs(["🔴 DA RIPARARE", "🟢 RIPARATI"])
    with t1:
        ap = df_seg[df_seg['Stato'] == 'APERTO']
        if ap.empty: st.success("Nessun guasto attivo")
        for _, r in ap.iterrows():
            st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b> - {r['Descrizione']}<br><small>{r['Data_Segnalazione']} | KM: {r['KM_Segnalazione']}</small></div>", unsafe_allow_html=True)
    with t2:
        ch = df_seg[df_seg['Stato'] == 'CHIUSO'].sort_index(ascending=False).head(15)
        for _, r in ch.iterrows():
            st.markdown(f"<div class='riparato-card'><b>{r['Targa']}</b> - OK<br><small>Riparato da {r['Operatore']} il {r['Data_Segnalazione']}</small></div>", unsafe_allow_html=True)

# --- MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("VEICOLO", lista_mezzi)
    idx_l = df_man.index[df_man['Targa'] == t_sel].tolist()
    idx = idx_l[0] if idx_l else 0
    km_att = st.number_input("KILOMETRI ATTUALI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    ch_t = st.checkbox("⚙️ Tagliando fatto"); ch_g = st.checkbox("🛞 Gomme cambiate"); alt = st.text_area("Note:")
    if st.button("💾 SALVA"):
        if idx_l:
            df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            if ch_t: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
            if ch_g: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
            conn.update(worksheet="Manutenzione", data=df_man)
        pd.concat([carica_dati("Storico"), pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "User": st.session_state.user, "Altro": alt}])], ignore_index=True)
        st.success("OK"); st.session_state.pagina = "home"; st.rerun()

# --- GUASTO ---
elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("UNITÀ", lista_mezzi); km_g = st.number_input("KILOMETRI ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    note = st.text_area("🗒️ ALTRE NOTE:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("FOTO")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA REPORT"):
        sel = [k for k,v in {"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        nuova = pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova], ignore_index=True)); st.session_state.gallery={}; st.session_state.pagina="home"; st.rerun()

# --- DANNO ---
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

# --- ADMIN ---
elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("### ➕ AGGIUNTA DATI")
    ca, cb, cc = st.columns(3)
    with ca:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO"):
                pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0","KM_Gomme":"0","KM_prossime Gomme":"0","KM_Tagliando":"0","KM_prossimo Tagliando":"0","Data":"-","User":"-"}])], ignore_index=True); st.rerun()
    with cb:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"):
                conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True)); st.rerun()
    with cc:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto").upper(); ee = st.text_input("Email")
            if st.button("SALVA EMAIL"):
                conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True)); st.rerun()
    st.divider(); df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico"); df_danni = carica_dati("DanniDriver")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            c = st.columns(6); fl = ["Gen", "Gomme", "Spia", "KM", "Targa", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                fa = {fl[i]: dg.get(fc[i], "") for i in range(6)}
                if invia_email_ufficiale(rub_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], fa): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
