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

# Inizializzazione sessione
for key in ['pagina', 'show_cam', 'foto_tipo', 'is_admin', 'user', 'gallery']:
    if key not in st.session_state:
        st.session_state[key] = "home" if key == 'pagina' else (True if key == 'is_admin' else ({} if key == 'gallery' else None))

# --- 2. DESIGN IPHONE PLATINUM + DASHBOARD ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    /* PULIZIA STREAMLIT */
    [data-testid="stStatusWidget"], .stDeployButton, header, footer, #MainMenu, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }

    .stApp { background: #000000; color: #ffffff; font-family: 'Inter', sans-serif; }

    /* HEADER */
    .iphone-header {
        text-align: center; padding: 40px 20px;
        background: linear-gradient(180deg, rgba(28,28,30,0.9) 0%, rgba(0,0,0,0) 100%);
        border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 30px;
    }

    /* STAT CARDS */
    .stat-container {
        display: flex; justify-content: space-around; gap: 15px; margin-bottom: 30px;
    }
    .stat-card {
        background: #1c1c1e; padding: 20px; border-radius: 20px; border: 1px solid #2c2c2e;
        text-align: center; flex: 1; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .stat-val { font-size: 2em; font-weight: 800; color: #0a84ff; }
    .stat-label { color: #8e8e93; font-size: 0.8em; text-transform: uppercase; }

    /* BOTTONI MENU A GRIGLIA */
    .stButton>button {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 25px !important; padding: 30px !important;
        font-size: 1.1em !important; font-weight: 600 !important;
        transition: 0.3s !important;
    }
    .stButton>button:hover { background: #ffffff !important; color: #000000 !important; transform: translateY(-5px); }

    /* ALERT LIST */
    .alert-item {
        background: rgba(255, 255, 255, 0.03); padding: 15px; border-radius: 15px;
        margin-bottom: 10px; border-left: 5px solid #ff9f0a;
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
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, "GOPRESSA SRL - REPORT", ln=True, align='C')
    pdf.set_font("Arial", "", 12); pdf.cell(0, 8, f"Mezzo: {row.get('Targa','')} | KM: {row.get('KM_Attuali','')}", ln=True)
    pdf.multi_cell(0, 8, f"Note: {row.get('Altro','')}"); return pdf.output(dest='S').encode('latin-1')

def invia_email_ufficiale(destinatario, targa, km, tipo_guasto, foto_list):
    try:
        cfg = st.secrets["email"]; msg = MIMEMultipart(); msg['From'] = cfg["smtp_user"]; msg['To'] = destinatario
        msg['Subject'] = f"Richiesta Autorizzazione - {targa}"
        corpo = f"Buongiorno,\n\nveicolo targato {targa} - KM {km}.\nRichiesta: {tipo_guasto}.\n\nCordiali saluti,\nGopressa SRL"
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
    st.markdown('<div class="iphone-header"><h1>GOPRESSA</h1><p>IDENTIFICATION REQUIRED</p></div>', unsafe_allow_html=True)
    u_sel = st.selectbox("OPERATORE", [""] + list(UTENTI.keys()))
    p_in = st.text_input("PASSWORD", type="password")
    if st.button("SBLOCCA SISTEMA"):
        if u_sel != "" and p_in == UTENTI[u_sel]: st.session_state.user = u_sel; st.rerun()
    st.stop()

# --- 5. CARICAMENTO DATI ---
df_man = carica_dati("Manutenzione")
df_seg = carica_dati("Segnalazioni")
df_danni = carica_dati("DanniDriver")
TARGHE_BACKUP = sorted(["HB183CY","HB284CY","HB339CY","HB184CY","GG730AV","GG243ZM","GG677RR","GG927ZP","GG429ZP","GG790ZL","GG075ZP","GG206JK","GG834JH","GG477JF","GG736AV","GZ399JY","GZ401JY","HA717DG","GS597DF","GZ532JY","HA412FV","HA630DC","HA881MM","GZ249ZS","GZ023SB","HA668DG","HA942FV","HA953FV","HA957FV","HA539SS","GG392AW","GG733AV","GG303AW","GG161HW","GG850JH","GG828JH","GG831AV","GG318AW","GG484JF","GG408AW","GG341AW","GG207JK","GG558JH","GG564JH","GG181HW","GG473JF","GG208JK","GG829JH","GG192ZN","GG163HW","GJ873LS"])
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_BACKUP

# --- 6. HOME PAGE (DASHBOARD) ---
if st.session_state.pagina == "home":
    st.markdown(f'<div class="iphone-header"><h1>GOPRESSA PRO</h1><p>{datetime.now().strftime("%A, %d %B %Y")}</p></div>', unsafe_allow_html=True)
    
    # ROW 1: STATISTICHE
    total_mezzi = len(lista_mezzi)
    guasti_aperti = len(df_seg[df_seg['Stato'] == 'APERTO']) if not df_seg.empty else 0
    danni_aperti = len(df_danni[df_danni['Stato'] == 'APERTO']) if not df_danni.empty else 0
    
    st.markdown(f"""
    <div class="stat-container">
        <div class="stat-card"><div class="stat-label">Flotta</div><div class="stat-val">{total_mezzi}</div></div>
        <div class="stat-card"><div class="stat-label">Guasti</div><div class="stat-val" style="color:#ff453a">{guasti_aperti}</div></div>
        <div class="stat-card"><div class="stat-label">Danni</div><div class="stat-val" style="color:#ff9f0a">{danni_aperti}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ROW 2: PULSANTI MENU (2 Colonne)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🛠️ MANUTENZIONE"): st.session_state.pagina = "manutenzione"; st.rerun()
        if st.button("💥 DANNO DRIVER"): st.session_state.pagina = "danno"; st.rerun()
    with c2:
        if st.button("🚨 SEGNALA GUASTO"): st.session_state.pagina = "guasto"; st.rerun()
        if st.button("📊 STATO FLOTTA"): st.session_state.pagina = "status"; st.rerun()
    
    st.button("👑 AREA ADMIN", on_click=lambda: setattr(st.session_state, 'pagina', 'admin'))

    # ROW 3: SCADENZE IMMINENTI
    st.markdown("### 🔔 SCADENZE MANUTENZIONE")
    if not df_man.empty:
        # Trova i 3 mezzi con KM più alti verso il prossimo tagliando
        df_man['KM_Mancanti'] = df_man['KM_prossimo Tagliando'].apply(safe_int) - df_man['KM_Attuali'].apply(safe_int)
        alert_mezzi = df_man.sort_values('KM_Mancanti').head(3)
        for _, row in alert_mezzi.iterrows():
            st.markdown(f"""<div class='alert-item'>
                🚛 <b>{row['Targa']}</b>: mancano <b>{row['KM_Mancanti']} km</b> al prossimo tagliando.
            </div>""", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT"): st.session_state.clear(); st.rerun()

# --- PAGINA STATUS ---
elif st.session_state.pagina == "status":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    st.markdown("<h2>📊 Monitoraggio Flotta</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔴 DA RIPARARE", "🟢 RIPARATI"])
    with t1:
        ap = df_seg[df_seg['Stato'] == 'APERTO']
        if ap.empty: st.success("Tutti i furgoni sono operativi!")
        for _, r in ap.iterrows():
            st.markdown(f"<div style='background:rgba(255,69,58,0.1); padding:15px; border-radius:20px; border:1px solid #ff453a; margin-bottom:10px;'><b>{r['Targa']}</b> - {r['Descrizione']}<br><small>KM: {r['KM_Segnalazione']} | {r['Data_Segnalazione']}</small></div>", unsafe_allow_html=True)
    with t2:
        ch = df_seg[df_seg['Stato'] == 'CHIUSO'].sort_index(ascending=False).head(10)
        for _, r in ch.iterrows():
            st.markdown(f"<div style='background:rgba(52,199,89,0.1); padding:15px; border-radius:20px; border:1px solid #34c759; margin-bottom:10px;'><b>{r['Targa']}</b> - OK<br><small>Riparato da {r['Operatore']} il {r['Data_Segnalazione']}</small></div>", unsafe_allow_html=True)

# --- ALTRE PAGINE (Logica invariata come richiesto) ---
elif st.session_state.pagina == "manutenzione":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
    t_sel = st.selectbox("VEICOLO", lista_mezzi)
    idx = df_man[df_man['Targa'] == t_sel].index[0] if not df_man[df_man['Targa'] == t_sel].empty else 0
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
    t_guasto = st.selectbox("UNITÀ", lista_mezzi); km_guasto = st.number_input("📟 KM ATTUALI:", value=0)
    p1=st.checkbox("Cambio Gomme Ant"); p2=st.checkbox("Cambio Gomme Post"); p3=st.checkbox("Pastiglie Freni"); p4=st.checkbox("Tagliando"); p5=st.checkbox("Spia motore")
    note_extra = st.text_area("🗒️ NOTE:")
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
        sel = [k for k,v in {"Cambio Gomme Ant":p1,"Cambio Gomme Post":p2,"Freni":p3,"Tagliando":p4,"Spia":p5}.items() if v]
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "KM_Segnalazione": str(km_guasto), "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": ", ".join(sel)+" | "+note_extra, "Urgenza": "ALTA", "Operatore": st.session_state.user, "Stato": "APERTO", "Foto": st.session_state.gallery.get("Foto",""), "Foto_Gomme": st.session_state.gallery.get("Gomme",""), "Foto_Cruscotto": st.session_state.gallery.get("Cruscotto",""), "Foto_KM": st.session_state.gallery.get("Chilometri",""), "Foto_Targa": st.session_state.gallery.get("Targa",""), "Foto_Libretto": st.session_state.gallery.get("Libretto","")}])
        conn.update(worksheet="Segnalazioni", data=pd.concat([carica_dati("Segnalazioni"), nuova_s], ignore_index=True)); st.session_state.gallery = {}; st.session_state.pagina = "home"; st.rerun()

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
    if st.session_state.foto_salvata: st.image(base64.b64decode(st.session_state.foto_salvata), width=200)
    if st.button("🚀 INVIA"):
        nuo = pd.DataFrame([{"Driver": d_s, "Targa": t_s, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "Descrizione": ds, "Stato": "APERTO", "Operatore": st.session_state.user, "Foto": st.session_state.foto_salvata or ""}])
        conn.update(worksheet="DanniDriver", data=pd.concat([carica_dati("DanniDriver"), nuo], ignore_index=True)); st.session_state.pagina = "home"; st.rerun()

elif st.session_state.pagina == "admin":
    if st.button("⬅️ MENU"): st.session_state.pagina = "home"; st.rerun()
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
    st.divider(); df_sto = carica_dati("Storico")
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
    st.divider(); t_s = st.selectbox("STORICO PDF", lista_mezzi)
    for i, r in df_sto[df_sto['Targa'] == t_s].sort_index(ascending=False).iterrows():
        st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report.pdf", key=f"p_{i}")
