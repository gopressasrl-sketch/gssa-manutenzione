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

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="GOPRESSA COMMAND", layout="wide", initial_sidebar_state="collapsed")

# Inizializzazione sessione
for key in ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. CSS CUSTOM: STEALTH LUXURY DESIGN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Orbitron:wght@500;900&display=swap');
    
    /* PULIZIA TOTALE INTERFACCIA */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] { 
        display: none !important; visibility: hidden !important; 
    }

    /* SFONDO E BASE */
    .stApp { background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }

    /* HEADER */
    .brand-header {
        text-align: center; padding: 40px 0 20px 0;
        background: linear-gradient(180deg, #1c1c1e 0%, #000000 100%);
        border-bottom: 1px solid #2c2c2e; margin-bottom: 30px;
    }
    .brand-header h1 { font-family: 'Orbitron', sans-serif; font-size: 3em; letter-spacing: 5px; color: #ffffff; margin: 0; }
    .brand-header p { color: #8e8e93; font-size: 0.9em; text-transform: uppercase; letter-spacing: 2px; }

    /* GRIGLIA DASHBOARD */
    [data-testid="stHorizontalBlock"] { max-width: 900px !important; margin: 0 auto !important; gap: 20px !important; }
    
    /* BOTTONI HUB */
    .stButton>button {
        background: #1c1c1e !important; color: white !important;
        border: 1px solid #2c2c2e !important; border-radius: 24px !important;
        height: 160px !important; width: 100% !important;
        font-size: 1.2em !important; font-weight: 600 !important;
        transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important; flex-direction: column !important;
    }
    .stButton>button:hover { background: #2c2c2e !important; border-color: #0a84ff !important; transform: translateY(-5px); }

    /* CARD INTERNE */
    .work-card {
        background: #1c1c1e; border-radius: 30px; padding: 30px;
        border: 1px solid #2c2c2e; margin: 0 auto; max-width: 800px;
    }
    
    /* STATUS BADGES */
    .stat-box { background: #000000; border-radius: 20px; padding: 20px; text-align: center; border: 1px solid #2c2c2e; }
    .stat-val { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #0a84ff; }
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
        # PROTEZIONE AUTO-REPAIR COLONNE
        req = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "User", "Altro"]
        }
        if foglio in req:
            for c in req[foglio]:
                if c not in df.columns: df[c] = ""
        return df
    except: return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file); img.thumbnail((1280, 1280)) # HD QUALITY
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - ACTIVITY LOG", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Unit: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Notes: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nDisponiamo di carrozzeria convenzionata Aldo Dal Maso & C. Snc (Camisano Vicentino).\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="brand-header"><h1>GOPRESSA</h1><p>Auth Required</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("USER", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("UNLOCK"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="brand-header"><h1>GOPRESSA</h1><p>{st.session_state.user} | {datetime.now().strftime("%H:%M")}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. NAVIGAZIONE HOME ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.foto_salvata = None; st.session_state.show_cam = False
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛠️\nManutenzione", key="h1"): st.session_state.pagina = "manutenzione"; st.rerun()
        if st.button("💥\nDanno Driver", key="h2"): st.session_state.pagina = "danno"; st.rerun()
        if st.button("🚪\nLogout", key="h3"): st.session_state.clear(); st.rerun()
    with col2:
        if st.button("🚨\nSegnala Guasto", key="h4"): st.session_state.pagina = "guasto"; st.rerun()
        if st.button("📊\nStato Flotta", key="h5"): st.session_state.pagina = "status"; st.rerun()
        if st.button("👑\nAdmin Panel", key="h6"): st.session_state.pagina = "admin"; st.rerun()

# --- 7. PAGINE ---
elif st.session_state.pagina == "manutenzione":
    st.markdown("<div class='work-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("UNITÀ", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
    km_att = st.number_input("KILOMETRI ATTUALI", value=safe_int(df_man.at[idx, 'KM_Attuali']))
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"<div class='stat-box'><small>TAGLIANDO A</small><br><div class='stat-val'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='stat-box'><small>GOMME A</small><br><div class='stat-val'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    ct=st.checkbox("Tagliando fatto"); cg=st.checkbox("Gomme cambiate")
    if st.button("💾 SALVA"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        if ct: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
        if cg: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
        conn.update(worksheet="Manutenzione", data=df_man); st.session_state.pagina = "home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "guasto":
    st.markdown("<div class='work-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    t_g = st.selectbox("UNITÀ", lista_mezzi); km_g = st.number_input("KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia"); note = st.text_area("🗒️ NOTE:")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("FOTO"); 
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        sel = [k for k,v in {"Gomme Ant":p1,"Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
        st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.pagina == "admin":
    st.markdown("<div class='work-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa")
            if st.button("SALVA V"): conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv.upper(),"KM_Attuali":"0"}])], ignore_index=True)); st.rerun()
    with c2:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome"); nc = st.text_input("Cognome")
            if st.button("SALVA D"): conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn.upper(),"Cognome":nc.upper()}])], ignore_index=True)); st.rerun()
    with c3:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto"); ee = st.text_input("Email")
            if st.button("SALVA E"): conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en.upper(),"Email":ee}])], ignore_index=True)); st.rerun()
    
    st.divider(); df_seg = carica_dati("Segnalazioni")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Problema: {dg['Descrizione']} | KM: {dg['KM_Segnalazione']}")
            c = st.columns(6); fl = ["Gen", "Gom", "Spi", "KM", "Tar", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], {fl[i]: dg.get(fc[i], "") for i in range(6)}): st.success("OK")
            if st.button(f"✅ CHIUDI {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    
    st.divider(); df_sto = carica_dati("Storico"); t_s = st.selectbox("STORICO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
    st.markdown("</div>", unsafe_allow_html=True)

# (Pagine status e danno caricate con lo stesso stile)
