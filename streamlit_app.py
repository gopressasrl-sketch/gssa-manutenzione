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
st.set_page_config(page_title="GOPRESSA PRO MAX", layout="wide", initial_sidebar_state="collapsed")

# Ora Italia
rome_tz = pytz.timezone('Europe/Rome')
ora_it = datetime.now(rome_tz).strftime("%H:%M")

# Inizializzazione sessione
keys_to_init = ['pagina', 'sub_guasto', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery', 'foto_salvata']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'gallery': st.session_state[key] = {}
        elif key == 'is_admin': st.session_state[key] = True
        else: st.session_state[key] = None

# --- 2. SUPER CSS: iPHONE 17 PRO MAX SUPREME UI ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');
    
    /* ELIMINA OGNI TRACCIA DI SISTEMA STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, .stDeployButton, header, footer, #MainMenu, 
    div[data-testid="stDecoration"], .viewerBadge_container__1QSob, div[data-testid="stToolbar"] {{ 
        display: none !important; visibility: hidden !important; 
    }}

    .stApp {{ background-color: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }}

    /* DYNAMIC ISLAND */
    .dynamic-island {{
        background: rgba(255, 255, 255, 0.05); border-radius: 50px;
        padding: 15px 35px; border: 1px solid rgba(255, 255, 255, 0.1);
        margin: 10px auto 40px auto; max-width: 500px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .island-title {{ font-family: 'Orbitron', sans-serif; font-size: 2.2em !important; font-weight: 900; letter-spacing: 4px; color: #ffffff; margin: 0; }}

    /* DESIGN ORIZZONTALE (ICONA A SINISTRA, BOTTONE A DESTRA) */
    [data-testid="stHorizontalBlock"] {{
        max-width: 600px !important;
        margin: 0 auto 12px auto !important;
        background: rgba(255,255,255,0.03);
        border-radius: 25px;
        padding: 8px !important;
        align-items: center !important;
    }}

    .icon-box {{
        width: 65px; height: 65px; background: #1c1c1e; border-radius: 18px;
        display: flex; align-items: center; justify-content: center;
        font-size: 2em; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }}

    .stButton>button {{
        border: none !important;
        border-radius: 15px !important;
        height: 65px !important;
        background: transparent !important;
        color: white !important;
        font-size: 1.1em !important;
        font-weight: 600 !important;
        text-align: left !important;
        padding-left: 10px !important;
        width: 100% !important;
    }}
    .stButton>button:active {{ transform: scale(0.98); background: rgba(255,255,255,0.1) !important; }}

    /* CARD INTERNE */
    .ios-card {{ background: rgba(28, 28, 30, 0.98); border-radius: 35px; padding: 25px; color: white; border: 1px solid #2c2c2e; margin: 0 auto; max-width: 700px; }}
    .status-mini {{ text-align: center; background: #000; border-radius: 20px; padding: 15px; margin-bottom: 10px; border: 1px solid #2c2c2e; }}
    .status-val {{ font-size: 26px; font-weight: 700; color: #0a84ff; }}
    
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div {{
        background-color: #2c2c2e !important; border-radius: 12px !important; border: none !important; color: white !important;
    }}
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
    img = Image.open(uploaded_file); img.thumbnail((1024, 1024))
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=80); return base64.b64encode(buf.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        corpo = f"Buongiorno,\n\nvi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.\nAvrei necessità di procedere con {tipo_guasto}.\n\nDisponiamo di carrozzeria convenzionata Aldo Dal Maso & C. Snc (Camisano Vicentino), vicino alla stazione Amazon.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown(f'<div class="dynamic-island"><h1 class="island-title">GOPRESSA</h1><p style="color:gray;">{ora_it}</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("UTENTE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("ACCEDI"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="dynamic-island"><h1 class="island-title">GOPRESSA</h1><p style="color:gray;">{st.session_state.user} | {ora_it}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
df_rub = carica_dati("RubricaEmail")
rub_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rub_dict[r['Nome']] = r['Email']

# --- 6. HOME PAGE (DESIGN ORIZZONTALE) ---
if st.session_state.pagina == "home":
    def row_btn(icon, label, target):
        c1, c2 = st.columns([1, 4])
        with c1: st.markdown(f'<div class="icon-box">{icon}</div>', unsafe_allow_html=True)
        with c2: 
            if st.button(label, key=f"btn_{target}"): st.session_state.pagina = target; st.rerun()

    row_btn("🛠️", "REGISTRO MANUTENZIONE", "manutenzione")
    row_btn("🚨", "SEGNALA UN GUASTO", "guasto")
    row_btn("💥", "SEGNALA DANNO DRIVER", "danno")
    row_btn("📊", "STATO DELLA FLOTTA", "status")
    row_btn("👑", "AREA AMMINISTRATORE", "admin")
    st.write("<br>")
    row_btn("🚪", "LOGOUT UTENTE", "logout")
    if st.session_state.pagina == "logout": st.session_state.clear(); st.rerun()

# --- 7. GUASTO (SOTTO-MENU) ---
elif st.session_state.pagina == "guasto":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Indietro"): 
        if st.session_state.sub_guasto: st.session_state.sub_guasto = None
        else: st.session_state.pagina = "home"
        st.rerun()

    if not st.session_state.sub_guasto:
        st.markdown("### 🚨 Seleziona Problema")
        if st.button("🦷 PASTIGLIE FRENI"): st.session_state.sub_guasto = "Pastiglie Freni"; st.rerun()
        if st.button("🛞 GOMME DA CAMBIARE"): st.session_state.sub_guasto = "Gomme"; st.rerun()
        if st.button("💡 SPIA MOTORE"): st.session_state.sub_guasto = "Spia Motore"; st.rerun()
        if st.button("⚙️ TAGLIANDO"): st.session_state.sub_guasto = "Tagliando"; st.rerun()
        if st.button("❓ ALTRI GUASTI"): st.session_state.sub_guasto = "Altro"; st.rerun()
    else:
        tipo = st.session_state.sub_guasto
        t_g = st.selectbox("🚛 MEZZO", lista_mezzi); km_g = st.number_input("📟 KM ATTUALI:", value=0)
        note = st.text_area("🗒️ NOTE:") if tipo == "Altro" else ""
        configs = {
            "Pastiglie Freni": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
            "Gomme": {"Gomme1":"GOMMA 1", "Gomme2":"GOMMA 2", "Targa":"TARGA", "Libretto":"LIBRETTO", "KM":"KM"},
            "Spia Motore": {"Spia":"SPIA", "KM":"KM", "Libretto":"LIBRETTO", "Targa":"TARGA"},
            "Tagliando": {"Targa":"TARGA", "KM":"KM", "Spia":"SPIA", "Libretto":"LIBRETTO"},
            "Altro": {"Targa":"TARGA", "KM":"KM", "Extra1":"FOTO 1", "Extra2":"FOTO 2"}
        }
        for k, v in configs[tipo].items():
            if k not in st.session_state.gallery:
                if st.button(f"📷 {v}"): st.session_state.show_cam = True; st.session_state.foto_tipo = k; st.rerun()
            else: st.success(f"✅ {v} OK")
        if st.session_state.show_cam:
            if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
            fi = st.camera_input("SCATTA"); 
            if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
        if st.button("🚀 INVIA REPORT"):
            sel = [k for k,v in {"Gomme Ant":True}.items()] # Placeholder
            conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), pd.DataFrame([{"Targa": t_g, "KM_Segnalazione": str(km_g), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": f"{tipo} | {note}", "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme1","") or st.session_state.gallery.get("Extra1",""), "Foto_Cruscotto": st.session_state.gallery.get("Spia",""), "Foto_KM": st.session_state.gallery.get("KM",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])], ignore_index=True))
            st.session_state.pagina="home"; st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 8. ADMIN ---
elif st.session_state.pagina == "admin":
    st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
    if st.button("⬅️ Chiudi"): st.session_state.pagina = "home"; st.rerun()
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa", key="admin_add_v").upper()
            if st.button("SALVA V"): conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0"}])], ignore_index=True)); st.rerun()
    with c2:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome", key="admin_add_dn").upper(); nc = st.text_input("Cognome", key="admin_add_dc").upper()
            if st.button("SALVA D"): conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True)); st.rerun()
    with c3:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto", key="admin_add_en").upper(); ee = st.text_input("Email", key="admin_add_ee")
            if st.button("SALVA E"): conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True)); st.rerun()
    
    st.divider(); df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico")
    for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
        with st.expander(f"🚛 PANNE: {targa}", expanded=True):
            dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
            st.write(f"Guasto: {dg['Descrizione']} | KM: {dg['KM_Segnalazione']}")
            c = st.columns(6); fl = ["Gen", "Gom", "Spi", "KM", "Tar", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
            for i, lab in enumerate(fl):
                if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
            sel_m = st.selectbox("Invia a:", sorted(list(rub_dict.keys())), key=f"s_{targa}")
            if st.button(f"📧 INVIA MAIL {targa}"):
                if invia_email_ufficiale(rub_dict.get(sel_m,""), targa, dg['KM_Segnalazione'], dg['Descrizione'], {fl[i]: dg.get(fc[i], "") for i in range(6)}): st.success("OK")
            if st.button(f"✅ CHIUDI GUASTO {targa}"):
                df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                df_seg.loc[df_seg['Stato'] == 'APERTO', 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
