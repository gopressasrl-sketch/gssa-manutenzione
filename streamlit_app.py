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

# Inizializzazione variabili di sessione
keys_to_init = ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'foto_salvata', 'gallery']
for key in keys_to_init:
    if key not in st.session_state:
        if key == 'pagina': st.session_state[key] = "home"
        elif key == 'is_admin': st.session_state[key] = True
        elif key == 'gallery': st.session_state[key] = {}
        else: st.session_state[key] = None

# --- 2. SUPER CSS PER PULIZIA TOTALE E DESIGN ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=Rajdhani:wght@300;500;700&display=swap');
    
    /* ELIMINA OGNI TRACCIA DI CARICAMENTO E ICONE STREAMLIT */
    [data-testid="stStatusWidget"], .stStatusWidget, div[id="stStatusWidget"], .stDeployButton, 
    header, footer, #MainMenu, div[data-testid="stDecoration"], .viewerBadge_container__1QSob, 
    .viewerBadge_link__1QSob, div[class^="viewerBadge"], div[data-testid="stToolbar"] { 
        display: none !important; visibility: hidden !important; 
    }

    .stApp { background: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #0f172a 50%, #020617 100%); background-attachment: fixed; color: #f8fafc; font-family: 'Rajdhani', sans-serif; }
    .header-container { text-align: center; padding: 30px; background: rgba(255, 255, 255, 0.02); border-radius: 40px; border: 1px solid rgba(0, 255, 255, 0.2); box-shadow: 0 0 30px rgba(0, 255, 255, 0.1); margin-bottom: 20px; }
    .main-title { font-family: 'Orbitron', sans-serif; font-size: 3.5em !important; font-weight: 900; background: linear-gradient(to right, #00d2ff, #3a7bd5, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 8px; }
    .stButton>button { background: rgba(15, 23, 42, 0.6) !important; color: #00f2ff !important; border: 1px solid #00f2ff !important; border-radius: 15px !important; padding: 15px !important; font-size: 1.1em !important; font-weight: 700; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background: #00f2ff !important; color: #000 !important; box-shadow: 0 0 20px #00f2ff !important; }
    .guasto-card { background: rgba(0, 242, 255, 0.05); border: 1px solid #00f2ff; padding: 20px; border-radius: 20px; margin-bottom: 15px; }
    .danno-card { background: rgba(255, 75, 75, 0.05); border: 1px solid #ff4b4b; padding: 20px; border-radius: 20px; margin-bottom: 15px; }
    .status-card { padding: 20px; border-radius: 20px; text-align: center; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }
    .val-neon { font-family: 'Orbitron', sans-serif; font-size: 28px; text-shadow: 0 0 10px #00d2ff; color: #00d2ff; }
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
        df.columns = [c.strip() for c in df.columns]
        
        # DEFINIZIONE COLONNE OBBLIGATORIE
        strutture = {
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"],
            "Manutenzione": ["Targa", "KM_Attuali", "KM_Gomme", "KM_prossime Gomme", "KM_Tagliando", "KM_prossimo Tagliando", "Data", "User", "Altro"],
            "Storico": ["Targa", "Data", "KM_Attuali", "KM_prossimo_Tagliando", "KM_prossime_Gomme", "User", "Altro"],
            "AnagraficaDriver": ["Nome", "Cognome"],
            "RubricaEmail": ["Nome", "Email"]
        }
        
        if foglio in strutture:
            for col in strutture[foglio]:
                if col not in df.columns: df[col] = ""
        return df
    except:
        # Se il foglio non esiste affatto, crea struttura vuota
        cols = {
            "AnagraficaDriver": ["Nome", "Cognome"],
            "RubricaEmail": ["Nome", "Email"],
            "Storico": ["Targa", "Data", "KM_Attuali", "KM_prossimo_Tagliando", "KM_prossime_Gomme", "User", "Altro"],
            "Segnalazioni": ["Targa", "KM_Segnalazione", "Data_Segnalazione", "Descrizione", "Urgenza", "Operatore", "Stato", "Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
        }
        return pd.DataFrame(columns=cols.get(foglio, []))

def process_image(uploaded_file):
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    img.thumbnail((450, 450))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=50)
    return base64.b64encode(buffered.getvalue()).decode()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Data: {row.get('Data','')}", ln=True)
    pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | Operatore: {row.get('User','')}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, f"KM REGISTRATI: {row.get('KM_Attuali','')} km", ln=True)
    pdf.cell(0, 8, f"PROSSIMO TAGLIANDO: {row.get('KM_prossimo_Tagliando','')}", ln=True)
    pdf.cell(0, 8, f"PROSSIME GOMME: {row.get('KM_prossime_Gomme','')}", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11); pdf.multi_cell(0, 8, f"Note: {row.get('Altro','')}")
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

# --- 4. HEADER ---
if st.session_state.user:
    st.markdown(f'<div class="header-container"><h1 class="main-title">GOPRESSA</h1><p>UNIT: {st.session_state.user}</p></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="header-container"><h1 class="main-title">GOPRESSA</h1></div>', unsafe_allow_html=True)

df_man = carica_dati("Manutenzione")
df_drivers = carica_dati("AnagraficaDriver")
df_rubrica = carica_dati("RubricaEmail")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []
rubrica_dict = {"SIXT VERONA": "dt48721@sixt.com", "SIXT MESTRE": "dt48302@sixt.com"}
for _, r in df_rubrica.iterrows(): rubrica_dict[r['Nome']] = r['Email']
lista_contatti = sorted(list(rubrica_dict.keys()))
if not df_drivers.empty and 'Nome' in df_drivers.columns:
    df_drivers['Full'] = df_drivers['Nome'] + " " + df_drivers['Cognome']
    lista_drivers = sorted(df_drivers['Full'].tolist())
else: lista_drivers = ["NESSUN DRIVER"]

# --- 5. LOGIN ---
if not st.session_state.user:
    nome_input = st.text_input("IDENTIFICAZIONE OPERATORE")
    if st.button("ACCEDI"):
        if nome_input: st.session_state.user = nome_input.upper(); st.rerun()
    st.stop()

# --- 6. NAVIGAZIONE ---
if st.session_state.pagina == "home":
    st.session_state.gallery = {}; st.session_state.foto_salvata = None; st.session_state.show_cam = False
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

elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("🚛 MEZZO", lista_mezzi)
    idx_list = df_man.index[df_man['Targa'] == t_sel].tolist()
    if idx_list:
        idx = idx_list[0]
        km_att = st.number_input("📟 KM", value=safe_int(df_man.at[idx, 'KM_Attuali']))
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='status-card'><small>TAGLIANDO A</small><br><div class='val-neon'>{km_att + 30000}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='status-card'><small>GOMME A</small><br><div class='val-neon'>{km_att + 40000}</div></div>", unsafe_allow_html=True)
        ch_t = st.checkbox("⚙️ Tagliando fatto"); ch_g = st.checkbox("🛞 Gomme cambiate")
        if st.button("💾 SALVA"):
            df_man.at[idx, 'KM_Attuali'] = str(km_att); df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            if ch_t: df_man.at[idx, 'KM_Tagliando'] = str(km_att); df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_att + 30000)
            if ch_g: df_man.at[idx, 'KM_Gomme'] = str(km_att); df_man.at[idx, 'KM_prossime Gomme'] = str(km_att + 40000)
            conn.update(worksheet="Manutenzione", data=df_man); st.success("OK"); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "guasto":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_guasto = st.selectbox("UNITÀ", lista_mezzi)
    km_guasto = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie dei freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    f_keys = {"Foto": "GEN", "Gomme": "GOMME 2", "Cruscotto": "SPIA", "Chilometri": "KM", "Targa": "TARGA", "Libretto": "LIBRETTO"}
    for k, v in f_keys.items():
        if k not in st.session_state.gallery:
            if st.button(f"📷 SCATTA {v}"): st.session_state.show_cam=True; st.session_state.foto_tipo=k; st.rerun()
        else: st.success(f"✅ {v} OK")
    if st.session_state.show_cam:
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.gallery[st.session_state.foto_tipo] = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.button("🚀 INVIA REPORT"):
        sel = [k for k,v in {"Cambio Gomme Ant":p1,"Cambio Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "KM_Segnalazione": str(km_guasto), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel), "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova_s], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "danno":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    d_sel = st.selectbox("DRIVER", lista_drivers); t_sel = st.selectbox("VEICOLO", lista_mezzi); desc = st.text_area("DANNO")
    if not st.session_state.show_cam:
        if st.button("📷 FOTO DANNO"): st.session_state.show_cam=True; st.rerun()
    else:
        fi = st.camera_input("SCATTA")
        if fi: st.session_state.foto_salvata = process_image(fi); st.session_state.show_cam=False; st.rerun()
    if st.session_state.foto_salvata: st.image(base64.b64decode(st.session_state.foto_salvata), width=200)
    if st.button("🚀 INVIA"):
        nuovo_d = pd.DataFrame([{"Driver": d_sel, "Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": desc, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), nuovo_d], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.expander("🚛 VEICOLO"):
            nv = st.text_input("Targa").upper()
            if st.button("SALVA MEZZO"):
                nr = pd.DataFrame([{"Targa":nv,"KM_Attuali":"0","KM_Gomme":"0","KM_prossime Gomme":"0","KM_Tagliando":"0","KM_prossimo Tagliando":"0","Data":"-","User":"-"}])
                conn.update(worksheet="Manutenzione", data=pd.concat([df_man, nr], ignore_index=True)); st.rerun()
    with c2:
        with st.expander("👤 DRIVER"):
            nn = st.text_input("Nome").upper(); nc = st.text_input("Cognome").upper()
            if st.button("SALVA DRIVER"):
                nr = pd.DataFrame([{"Nome":nn, "Cognome":nc}]); conn.update(worksheet="AnagraficaDriver", data=pd.concat([carica_dati("AnagraficaDriver"), nr], ignore_index=True)); st.rerun()
    with c3:
        with st.expander("📧 EMAIL"):
            en = st.text_input("Contatto").upper(); ee = st.text_input("Email")
            if st.button("SALVA EMAIL"):
                nr = pd.DataFrame([{"Nome":en, "Email":ee}]); conn.update(worksheet="RubricaEmail", data=pd.concat([carica_dati("RubricaEmail"), nr], ignore_index=True)); st.rerun()

    st.divider()
    df_seg = carica_dati("Segnalazioni")
    if 'Stato' in df_seg.columns:
        aperti = df_seg[df_seg['Stato'] == 'APERTO']['Targa'].unique()
        for targa in aperti:
            with st.expander(f"🚛 PANNE: {targa}", expanded=True):
                dg = df_seg[(df_seg['Targa'] == targa) & (df_seg['Stato'] == 'APERTO')].iloc[0]
                st.write(f"Guasto: {dg['Descrizione']} | KM: {dg['KM_Segnalazione']}")
                c = st.columns(6); fl = ["Gen", "Gomme", "Spia", "KM", "Targa", "Lib"]; fc = ["Foto", "Foto_Gomme", "Foto_Cruscotto", "Foto_KM", "Foto_Targa", "Foto_Libretto"]
                for i, lab in enumerate(fl):
                    if dg.get(fc[i], ""): c[i].image(base64.b64decode(dg[fc[i]]), caption=lab)
                sel_m = st.selectbox("Invia a:", lista_contatti, key=f"s_{targa}")
                if st.button(f"📧 INVIA MAIL {targa}"):
                    f_att = {fl[i]: dg.get(fc[i], "") for i in range(6)}
                    if invia_email_ufficiale(rubrica_dict[sel_m], targa, dg['KM_Segnalazione'], dg['Descrizione'], f_att): st.success("OK")
                if st.button(f"✅ CHIUDI {targa}"):
                    df_seg.loc[df_seg['Targa'] == targa, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

    st.divider(); df_sto = carica_dati("Storico")
    t_s = st.selectbox("STORICO PDF", lista_mezzi)
    if not df_sto.empty and 'Targa' in df_sto.columns:
        for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
            st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
