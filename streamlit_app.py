import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
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
st.set_page_config(page_title="GOPRESSA EXECUTIVE", layout="wide", initial_sidebar_state="collapsed")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. SUPER CSS: EXECUTIVE TITANIUM DESIGN ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Orbitron:wght@500;900&display=swap');
    
    /* PULIZIA TOTALE STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    /* SFONDO ARDESIA PROFESSIONALE */
    .stApp {{ background-color: #0e1117; color: #e1e1e6; font-family: 'Inter', sans-serif; }}

    /* HEADER TITANIUM PILL */
    .exec-header {{
        background: linear-gradient(180deg, #1c1f26 0%, #000000 100%);
        border-radius: 50px; padding: 15px 35px; border: 1px solid #3d4251;
        margin: 20px auto 40px auto; max-width: 600px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .main-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #ffffff; margin: 0; }}
    .status-text {{ color: #0a84ff; font-size: 0.9em; font-weight: 500; text-transform: uppercase; margin-top: 5px; }}

    /* GRID DASHBOARD */
    [data-testid="stHorizontalBlock"] {{ max-width: 800px !important; margin: 0 auto !important; }}
    [data-testid="column"] {{ display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center !important; }}

    /* BOTTONI TITANIUM */
    .stButton>button {{
        border: none !important; border-radius: 20px !important;
        width: 75px !important; height: 75px !important;
        background: #1c1f26 !important; color: white !important;
        font-size: 2em !important; border: 1px solid #3d4251 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5) !important;
        transition: 0.2s !important;
    }}
    .stButton>button:active {{ transform: scale(0.95); border-color: #0a84ff !important; }}

    .app-label {{ color: #8e8e93; font-size: 11px; margin-top: 6px; margin-bottom: 25px; font-weight: 600; text-transform: uppercase; }}

    /* CARD INTERNE GESTIONALI */
    .inner-card {{ background: #1c1f26; border-radius: 35px; padding: 25px; color: white; border: 1px solid #3d4251; margin: 0 auto; max-width: 800px; }}
    .status-card-inner {{ text-align: center; background: #000; border-radius: 20px; padding: 15px; margin-bottom: 10px; border: 1px solid #3d4251; }}
    .status-val {{ font-size: 24px; font-weight: 700; color: #0a84ff; }}
    
    /* LISTE STATO */
    .guasto-card {{ background: rgba(255, 69, 58, 0.1); border-left: 5px solid #ff453a; padding: 15px; border-radius: 10px; margin-bottom: 10px; }}
    .riparato-card {{ background: rgba(52, 199, 89, 0.1); border-left: 5px solid #34c759; padding: 15px; border-radius: 10px; margin-bottom: 10px; }}
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
        # PROTEZIONE AUTO-REPAIR
        req = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "User", "Altro"],
            "AnagraficaDriver": ["Nome", "Cognome"], "RubricaEmail": ["Nome", "Email"]
        }
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - ACTIVITY LOG", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Note: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"AUTORIZZAZIONE INTERVENTO - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nDisponiamo di carrozzeria convenzionata Aldo Dal Maso & C. Snc.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="exec-header"><h1 class="main-title">GOPRESSA</h1><p class="status-text">Accesso Pro</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="exec-header"><h1 class="main-title">GOPRESSA</h1><p class="status-text">{st.session_state.user} | {ora_it} | ROMA</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.foto_salvata = None; st.session_state.show_cam = False
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️", key="i1"): st.session_state.pagina = "manutenzione"; st.rerun()
        st.markdown('<p class="app-label">Manutenzione</p>', unsafe_allow_html=True)
    with c2:
        if st.button("🚨", key="i2"): st.session_state.pagina = "guasto"; st.rerun()
        st.markdown('<p class="app-label">Guasti</p>', unsafe_allow_html=True)
    with c3:
        if st.button("💥", key="i3"): st.session_state.pagina = "danno"; st.rerun()
        st.markdown('<p class="app-label">Danni Driver</p>', unsafe_allow_html=True)
    with c4:
        if st.button("📊", key="i4"): st.session_state.pagina = "status"; st.rerun()
        st.markdown('<p class="app-label">Stato Flotta</p>', unsafe_allow_html=True)
    
    st.write("<br><br>", unsafe_allow_html=True)
    cd1, cd2, cd3, cd4 = st.columns(4)
    with cd1:
        if st.button("👑", key="adm"): st.session_state.pagina = "admin"; st.rerun()
        st.markdown('<p class="app-label">Admin</p>', unsafe_allow_html=True)
    with cd4:
        if st.button("🚪", key="exit"): st.session_state.clear(); st.rerun()
        st.markdown('<p class="app-label">Logout</p>', unsafe_allow_html=True)

# --- 7. STATO FLOTTA ---
elif st.session_state.pagina == "status":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("### 📋 Monitoraggio Riparazioni")
    df_s = carica_dati("Segnalazioni")
    t1, t2 = st.tabs(["🔴 DA RIPARARE", "🟢 RIPARATI"])
    with t1:
        ap = df_s[df_s['Stato'] == 'APERTO']
        if ap.empty: st.success("Nessuna riparazione pendente.")
        for _, r in ap.iterrows():
            st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b> - {r['Descrizione']}<br><small>Dal {r['Data_Segnalazione']} | KM: {r['KM_Segnalazione']}</small></div>", unsafe_allow_html=True)
    with t2:
        ch = df_s[df_s['Stato'] == 'CHIUSO'].sort_index(ascending=False).head(15)
        for _, r in ch.iterrows():
            st.markdown(f"<div class='riparato-card'><b>{r['Targa']}</b> - OK<br><small>Riparato da {r['Operatore']} il {r['Data_Segnalazione']}</small></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 8. MANUTENZIONE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("KILOMETRI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='status-card-inner'><small>TAGLIANDO A</small><br><div class='status-val'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='status-card-inner'><small>GOMME A</small><br><div class='status-val'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 9. GUASTO ---
elif st.session_state.pagina == "guasto":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("NOTE:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        sel = [k for k,v in {"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
        st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 10. ADMIN ---
elif st.session_state.pagina == "admin":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    c_v, c_d, c_e = st.columns(3)
    with c_v:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa")
            if st.button("SALVA V"): conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv.upper(),"KM_Attuali":"0"}])], ignore_index=True)); st.rerun()
    with c_d:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome"); nc = st.text_input("Cognome")
            if st.button("SALVA D"): conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn.upper(),"Cognome":nc.upper()}])], ignore_index=True)); st.rerun()
    with c_e:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto"); ee = st.text_input("Email")
            if st.button("SALVA E"): conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en.upper(),"Email":ee}])], ignore_index=True)); st.rerun()
    
    st.divider(); df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']}")
            c = st.columns(6); fl = ["Gen", "Gom", "Spi", "KM", "Tar", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], {fl[i]: dg.get(fc[i], "") for i in range(6)}): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.divider(); df_sto_v = carica_dati("Storico"); ts = st.selectbox("ARCHIVIO PDF", lista_mezzi)
    for i, r in df_sto_v[df_sto_v['Targa'] == ts].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

# (Pagina Danno caricata allo stesso modo degli altri)
elif st.session_state.pagina == "danno":
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    df_dr = carica_dati("AnagraficaDriver")
    ld = (df_dr['Nome'] + " " + df_dr['Cognome']).tolist() if not df_dr.empty else ["NESSUN DRIVER"]
    ds = st.selectbox("DRIVER", ld); ts = st.selectbox("VEICOLO", lista_mezzi); dsc = st.text_area("DANNO")
    if not st.session_state.show_cam:
        if st.button("📷 FOTO DANNO"): st.session_state.show_cam=True; st.rerun()
    else:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.foto_salvata = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.session_state.foto_salvata: st.image(base64.b64decode(st.session_state.foto_salvata), width=200)
    if st.button("🚀 INVIA SINISTRO"):
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), pd.DataFrame([{"Driver": ds, "Targa": ts, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": dsc, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
