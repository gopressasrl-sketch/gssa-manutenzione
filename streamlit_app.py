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
if 'foto_tipo' not in st.session_state: st.session_state.foto_tipo = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = True
if 'user' not in st.session_state: st.session_state.user = None
if 'gallery' not in st.session_state: st.session_state.gallery = {}
if 'foto_salvata' not in st.session_state: st.session_state.foto_salvata = None

# --- 2. DESIGN IPHONE 17 PRO MAX ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    [data-testid="stStatusWidget"], .stStatusWidget, div[id="stStatusWidget"], .stDeployButton, 
    header, footer, #MainMenu, div[data-testid="stDecoration"], .viewerBadge_container__1QSob, 
    .viewerBadge_link__1QSob, div[class^="viewerBadge"], div[data-testid="stToolbar"] { 
        display: none !important; visibility: hidden !important; 
    }
    .stApp { background: linear-gradient(180deg, #000000 0%, #1c1c1e 100%); color: #ffffff; font-family: 'Inter', sans-serif; }
    .header-container { text-align: center; padding: 40px 20px; background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(20px); border-radius: 40px; border: 1px solid rgba(255, 255, 255, 0.1); margin: 10px auto 30px auto; max-width: 800px; }
    .main-title { font-size: 3.5em !important; font-weight: 800; letter-spacing: -2px; background: linear-gradient(180deg, #ffffff 0%, #a2a2a2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
    .stButton>button { background: rgba(255, 255, 255, 0.08) !important; color: #ffffff !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 25px !important; padding: 20px !important; font-size: 1.1em !important; font-weight: 600; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background: #ffffff !important; color: #000000 !important; }
    .status-card { padding: 25px; border-radius: 30px; text-align: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); }
    .val-neon { font-size: 32px; font-weight: 700; color: #ffffff; }
    .guasto-card { background: rgba(10, 132, 255, 0.15); border: 1px solid #0a84ff; padding: 20px; border-radius: 30px; margin-bottom: 15px; }
    .danno-card { background: rgba(255, 69, 58, 0.15); border: 1px solid #ff453a; padding: 20px; border-radius: 30px; margin-bottom: 15px; }
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
    except:
        return pd.DataFrame()

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img.thumbnail((1280, 1280))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Note: {row.get('Altro','')}")
    return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]
        msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione Intervento - {targa}"
        corpo = f"""Buongiorno,

vi scrivo in riferimento al veicolo a noleggio targato {targa} - KM {km}.
Avrei necessità di procedere con {tipo_guasto}.

Disponiamo di una carrozzeria convenzionata con noi, la Aldo Dal Maso & C. Snc, sita in Via Badia 7, 36043 Camisano Vicentino (VI), vicino alla stazione Amazon, che sarebbe disponibile a eseguire i lavori in tempi brevi.

Vi chiedo gentilmente se per Voi non ci sono problemi ad autorizzare questi interventi. Qualora ci confermaste la vostra approvazione, procederemmo immediatamente.

In allegato le foto del veicolo.

Resto in attesa di un Vostro gentile riscontro.

Cordiali saluti,
Gopressa SRL"""
        msg.attach(MIMEText(corpo, 'plain'))
        for label, b64_str in foto_list.items():
            if b64_str:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(b64_str))
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{label}.jpg"')
                msg.attach(part)
        server = smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"])
        server.starttls(); server.login(cfg["smtp_user"], cfg["smtp_password"])
        server.send_message(msg); server.quit()
        return True
    except Exception as e:
        st.error(f"Errore mail: {e}"); return False

# --- 4. LOGIN ---
UTENTI = {"ION PLUGARU": "1", "GURJIT SINGH": "2", "FILIPPO BERNARDI": "3"}
if not st.session_state.user:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p style="color:gray;">BENVENUTO</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_input = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA PORTALE"):
        if u_sel != "" and p_input == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. HEADER ---
st.markdown(f'<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p style="color:gray;">UNIT: {st.session_state.user}</p></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
df_rub = carica_dati("RubricaEmail")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP
rd = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _,r in df_rub.iterrows(): rd[r['Nome']] = r['Email']
lc = sorted(list(rd.keys()))

# --- 6. NAVIGAZIONE ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.foto_salvata = None; st.session_state.show_cam = False
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("🛠️ MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
    with c2:
        if st.button("🚨 GUASTI"): st.session_state.pagina = "guasto"; st.rerun()
    with c3:
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with c4:
        if st.button("👑 ADMIN"): st.session_state.pagina = "admin"; st.rerun()
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 UNITÀ", lista_mezzi)
    idx_l = df_man.index[df_man['Targa'] == t_sel].tolist()
    idx = idx_l[0] if idx_l else 0
    km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']) if idx_l else 0)
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
    ch_t = st.checkbox("⚙️ Tagliando fatto"); ch_g = st.checkbox("🛞 Gomme cambiate"); altro = st.text_area("Note:")
    if st.button("💾 SALVA"):
        if idx_l:
            df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            if ch_t: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
            if ch_g: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
            conn.update(worksheet="Manutenzione", data=df_man)
        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "User": st.session_state.user, "Altro": "Intervento Manutenzione"}])
        conn.update(worksheet="Storico", data=pd.concat([carica_dati("Storico"), nuovo_s], ignore_index=True)); st.success("OK"); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_guasto = st.selectbox("🚛 UNITÀ", lista_mezzi); km_guasto = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    note_extra = st.text_area("🗒️ ALTRE NOTE:")
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
        sel = [k for k,v in {"Cambio Gomme Ant":p1,"Cambio Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "KM_Segnalazione": str(km_guasto), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note_extra, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova_s], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    df_drivers = carica_dati("AnagraficaDriver")
    lista_d = (df_drivers['Nome'] + " " + df_drivers['Cognome']).tolist() if not df_drivers.empty else ["NESSUN DRIVER"]
    d_sel = st.selectbox("DRIVER", lista_d); t_sel = st.selectbox("VEICOLO", lista_mezzi); desc = st.text_area("DANNO")
    if not st.session_state.show_cam:
        if st.button("📷 FOTO"): st.session_state.show_cam=True; st.rerun()
    else:
        if st.button("❌ CHIUDI"): st.session_state.show_cam=False; st.rerun()
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.foto_salvata = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA"):
        nuovo_d = pd.DataFrame([{"Driver": d_sel, "Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": desc, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), nuovo_d], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("### ➕ AGGIUNTA DATI")
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO"):
                conn.update(worksheet="Manutenzione", data=pd.concat([df_man, pd.DataFrame([{"Targa":nv,"KM_Attuali":"0","KM_Gomme":"0","KM_prossime Gomme":"0","KM_Tagliando":"0","KM_prossimo Tagliando":"0","Data":"-","User":"-"}])], ignore_index=True)); st.rerun()
    with c_b:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"):
                conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), pd.DataFrame([{"Nome":nn, "Cognome":nc}])], ignore_index=True)); st.rerun()
    with c_c:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto").upper(); ee = st.text_input("Email")
            if st.button("SALVA EMAIL"):
                conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), pd.DataFrame([{"Nome":en, "Email":ee}])], ignore_index=True)); st.rerun()

    st.divider(); df_seg = carica_dati("Segnalazioni"); df_sto = carica_dati("Storico"); df_danni = carica_dati("DanniDriver")
    if 'Stato' in df_seg.columns:
        for targa in df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique():
            with st.expander(f"🚛 PANNE: {targa}", expanded=True):
                dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
                st.write(f"Guasto: {dg['Descrizione']} | KM: {dg['KM_Segnalazione']}")
                c = st.columns(6); fl = ["Gen", "Gomme", "Spia", "KM", "Targa", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
                for i, lab in enumerate(fl):
                    if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
                sel_m = st.selectbox("Invia a:", lc, key=f"s_{targa}")
                if st.button(f"📧 INVIA MAIL {targa}"):
                    fa = {fl[i]: dg.get(fc[i], "") for i in range(6)}
                    if invia_email_ufficiale(rd[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], fa): st.success("OK")
                if st.button(f"✅ CHIUDI GUASTO {targa}"):
                    df_seg.loc[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO'), 'Operatore'] = st.session_state.user
                    df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

    if 'Stato' in df_danni.columns:
        for i, r in df_danni[df_danni['Stato'] == 'APERTO'].iterrows():
            with st.expander(f"💥 DANNO DRIVER: {r['Targa']}", expanded=True):
                st.write(f"Driver: {r['Driver']} | {r['Descrizione']}")
                if r['Foto']: st.image(base64.b64decode(r['Foto']), width=300)
                if st.button(f"PRENDI IN CARICO {r['Targa']}##{i}"):
                    df_danni.at[i, 'Operatore'] = st.session_state.user; df_danni.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="DanniDriver", data=df_danni); st.rerun()

    st.divider(); t_s = st.selectbox("STORICO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
