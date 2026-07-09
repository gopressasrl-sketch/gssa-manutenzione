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
st.set_page_config(page_title="GOPRESSA MISSION CONTROL", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione variabili
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'foto_salvata', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'is_admin': st.session_state[key] = True
        elif key == 'gallery': st.session_state[key] = {}
        else: st.session_state[key] = None

# --- 2. SUPER CSS IPHONE 17 PRO MAX ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600;800&display=swap');
    [data-testid="stStatusWidget"], .stStatusWidget, div[id="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], .viewerBadge_container__1QSob, .viewerBadge_link__1QSob, div[class^="viewerBadge"], div[data-testid="stToolbar"] { display: none !important; visibility: hidden !important; }
    .stApp { background: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }
    .iphone-header { text-align: center; padding: 40px 20px; background: linear-gradient(180deg, rgba(28,28,30,0.9) 0%, rgba(0,0,0,0) 100%); border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px; }
    .main-title { font-family: 'Orbitron', sans-serif; font-size: 3.5em !important; font-weight: 900; background: linear-gradient(180deg, #ffffff 30%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stButton>button { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 22px !important; padding: 25px 20px !important; font-weight: 600 !important; transition: 0.3s !important; }
    .stButton>button:hover { background: #ffffff !important; color: #000000 !important; transform: translateY(-3px); }
    .status-card { padding: 20px; border-radius: 25px; text-align: center; background: #1c1c1e; border: 1px solid #2c2c2e; }
    .val-neon { font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700; color: #0a84ff; }
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
        msg['Subject'] = f"Richiesta Autorizzazione - {targa}"
        corpo = f"Buongiorno,\n\nveicolo targato {targa} - KM {km}.\nIntervento richiesto: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="iphone-header"><h1 class="main-title">GOPRESSA</h1><p>Control Center Access</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA PORTALE"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="iphone-header"><h1 class="main-title">GOPRESSA</h1><p style="color:gray;">{datetime.now().strftime("%H:%M")} | Commander: {st.session_state.user}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
df_seg = carica_dati("Segnalazioni")
df_danni = carica_dati("DanniDriver")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP

# --- 6. NAVIGAZIONE ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.foto_salvata = None; st.session_state.show_cam = False
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🛠️ MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with c2:
        if st.button("🚨 SEGNALA GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
        if st.button("📊 STATO FLOTTA"): st.session_state.pagina = "status"; st.rerun()
    st.button("👑 AREA ADMIN", on_click=lambda: setattr(st.session_state, 'pagina', 'admin'))
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

elif st.session_state.pagina == "status":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t1, t2 = st.tabs(["🔴 DA RIPARARE", "🟢 RIPARATI"])
    with t1:
        for _, r in df_seg[df_seg['Stato'] == 'APERTO'].iterrows():
            st.markdown(f"<div class='guasto-card'><b>{r['Targa']}</b> - {r['Descrizione']}</div>", unsafe_allow_html=True)
    with t2:
        for _, r in df_seg[df_seg['Stato'] == 'CHIUSO'].sort_index(ascending=False).head(10).iterrows():
            st.markdown(f"<div class='riparato-card'><b>{r['Targa']}</b> - OK (Riparato da {r['Operatore']})</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    if st.button("💾 SALVA INTERVENTO"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        conn.update(worksheet="Manutenzione", data=df_man); st.success("OK"); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("🚛 UNITÀ", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("🗒️ ALTRE NOTE:")
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
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova], ignore_index=True)); st.session_state.pagina="home"; st.rerun()

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
        nuovo_d = pd.DataFrame([{"Driver": d_s, "Targa": t_s, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": ds, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), nuovo_d], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO", key="save_v"):
                nr = pd.DataFrame([{"Targa":nv,"KM_Attuali":"0","KM_Gomme":"0","KM_prossime Gomme":"0","KM_Tagliando":"0","KM_prossimo Tagliando":"0","Data":"-","User":"-"}])
                conn.update(worksheet="Manutenzione", data=pd.concat([df_man, nr], ignore_index=True)); st.rerun()
    with c_b:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER", key="save_d"):
                df_dr = carica_dati("AnagraficaDriver")
                conn.update(worksheet="AnagraficaDriver", data=pd.concat([df_dr, pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True)); st.rerun()
    with c_c:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto").upper(); ee = st.text_input("Email")
            if st.button("SALVA EMAIL", key="save_e"):
                df_rub = carica_dati("RubricaEmail")
                conn.update(worksheet="RubricaEmail", data=pd.concat([df_rub, pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True)); st.rerun()

    df_rub = carica_dati("RubricaEmail")
    rd = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
    for _,r in df_rub.iterrows(): rd[r['Nome']] = r['Email']
    
    st.divider(); df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Guasto: {dg['Descrizione']}")
            c = st.columns(6); fl = ["Gen", "Gomme", "Spia", "KM", "Targa", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", sorted(list(rd.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                fa = {fl[i]: dg.get(fc[i], "") for i in range(6)}
                if invia_email_ufficiale(rd[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], fa): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

    st.divider(); df_sto = carica_dati("Storico")
    t_s = st.selectbox("ARCHIVIO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"pdf_{i}")
