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

# Inizializzazione variabili di sessione
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'foto_salvata', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        else: st.session_state[key] = None

# --- 2. SUPER CSS IPHONE 17 PRO MAX (PULIZIA TOTALE + CENTRATURA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ELIMINA OGNI TRACCIA DI STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] { 
        display: none !important; visibility: hidden !important; 
    }

    .stApp { background: #000000; color: #ffffff; font-family: 'Inter', -apple-system, sans-serif; }

    /* CENTRATURA COLONNE PER ICONE */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    /* HEADER IPHONE STYLE */
    .iphone-header {
        text-align: center; padding: 40px 20px 20px 20px;
        background: linear-gradient(180deg, rgba(28,28,30,0.8) 0%, rgba(0,0,0,0) 100%);
        margin-bottom: 20px;
    }
    .main-title { font-size: 3.2em !important; font-weight: 700; letter-spacing: -1.5px; margin-bottom: 5px; }

    /* ICONA (BOTTONE) TIPO APP */
    .stButton>button {
        border: none !important;
        border-radius: 22px !important;
        width: 80px !important;
        height: 80px !important;
        background: #1c1c1e !important;
        color: white !important;
        font-size: 2.2em !important;
        padding: 0 !important;
        margin: 0 auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 8px 15px rgba(0,0,0,0.4) !important;
        transition: transform 0.2s !important;
    }
    .stButton>button:hover { transform: scale(1.1); background: #2c2c2e !important; }

    /* LABEL SOTTO L'ICONA */
    .app-label {
        color: white; font-size: 13px; margin-top: 8px; font-weight: 400;
        width: 100%; text-align: center; margin-bottom: 25px;
    }

    /* CONTENITORI INTERNI BIANCHI */
    .ios-card {
        background: rgba(255, 255, 255, 0.95); border-radius: 35px;
        padding: 25px; color: black; margin-top: 10px; box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    .status-card { text-align: center; background: #f2f2f7; border-radius: 20px; padding: 15px; margin: 5px; }
    .val-neon { font-size: 26px; font-weight: 700; color: #007aff; }

    /* CARD GUASTI/RIPARATI */
    .guasto-card { background: rgba(255, 69, 58, 0.1); border: 1px solid #ff453a; padding: 20px; border-radius: 25px; margin-bottom: 15px; color: black; }
    .riparato-card { background: rgba(52, 199, 89, 0.1); border: 1px solid #34c759; padding: 20px; border-radius: 25px; margin-bottom: 15px; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNZIONI CORE DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        df.columns = [str(c).strip() for c in df.columns]
        # PROTEZIONE COLONNE
        req = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "KM_prossimo_Tagliando", "KM_prossime_Gomme", "User", "Altro"],
            "AnagraficaDriver": ["Nome", "Cognome"],
            "RubricaEmail": ["Nome", "Email"]
        }
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280)) # ALTA QUALITÀ HD
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Intervento: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nDisponiamo di carrozzeria convenzionata Aldo Dal Maso & C. Snc (Camisano Vicentino).\n\nCordiali saluti,\nGopressa SRL"
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64 in foto_list.items():
            if b64:
                part = MIMEBase('application', 'octet-stream'); part.set_payload(base64.b64decode(b64))
                encoders.encode_base64(part); part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"'); msg.attach(part)
        s = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]); s.starttls(); s.login(cfg["smtp_user"], cfg["smtp_password"])
        s.send_message(msg); s.quit(); return True
    except: return False

# --- 4. LOGIN SYSTEM ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDINI": "3"}
if not st.session_state.user:
    st.markdown('<div class="iphone-header"><h1>GOPRESSA</h1><p>IDENTIFICATION</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="iphone-header"><h1>GOPRESSA</h1><p>{st.session_state.user} | {datetime.now().strftime("%H:%M")}</p></div>', unsafe_allow_html=True)

# CARICAMENTO DATI
df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
df_rub = carica_dati("RubricaEmail")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME (IPHONE GRID) ---
if st.session_state.pagina == "home":
    # RIGA 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="m"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="g"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="d"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Danni</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="s"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Stato Flotta</p>', unsafe_allow_html=True)

    # RIGA 2 (Dock)
    st.write("<br><br>", unsafe_allow_html=True)
    cd1, cd2, cd3, cd4 = st.columns(4)
    with cd1:
        if st.button("👑", key="a"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p>', unsafe_allow_html=True)
    with cd4:
        if st.button("🚪", key="l"): st.session_state.clear(); st.rerun()
        st.markdown('<p class="app-label">Logout</p>', unsafe_allow_html=True)

# --- PAGINE INTERNE ---
elif st.session_state.pagina == "status":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2 style='color:black;'>Stato Riparazioni</h2>", unsafe_allow_html=True)
    df_s = carica_dati("Segnalazioni")
    t1, t2 = st.tabs(["🔴 DA FARE", "🟢 COMPLETATI"])
    with t1:
        ap = df_s[df_s['Stato'] == 'APERTO']
        for _, r in ap.iterrows(): st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b><br>{r['Descrizione']}</div>", unsafe_allow_html=True)
    with t2:
        ch = df_s[df_s['Stato'] == 'CHIUSO'].sort_index(ascending=False).head(10)
        for _, r in ch.iterrows(): st.markdown(f"<div class='riparato-card'><b>{r['Targa']}</b><br>Riparato da {r['Operatore']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    ct=st.checkbox("Tagliando fatto"); cg=st.checkbox("Gomme cambiate"); alt=st.text_area("Note:")
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        if ct: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if cg: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Gomme Ant"); p2=st.checkbox("Gomme Post"); p3=st.checkbox("Pastiglie"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("🗒️ ALTRE NOTE:")
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
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
        st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "danno":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
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
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), pd.DataFrame([{"Driver": d_s, "Targa": t_s, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": ds, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    # AGGIUNTA DATI
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO"): conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0"}])], ignore_index=True)); st.rerun()
    with c_b:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"): conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True)); st.rerun()
    with c_c:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Nome").upper(); ee = st.text_input("Email")
            if st.button("SALVA EMAIL"): conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True)); st.rerun()
    
    st.divider(); df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Guasto: {dg['Descrizione']}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict["SIXT VERONA"], targa, dg['KM_Segnalazione'], dg['Descrizione'], { "Gen": dg['Foto'], "Gomme": dg['Foto_Gomme'], "Spia": dg['Foto_Cruscotto'], "KM": dg['Foto_KM'], "Targa": dg['Foto_Targa'], "Libretto": dg['Foto_Libretto'] }): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    
    st.divider(); df_sto = carica_dati("Storico"); t_s = st.selectbox("ARCHIVIO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
    st.markdown("</div>", unsafe_allow_html=True)
