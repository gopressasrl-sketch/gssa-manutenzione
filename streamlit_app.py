import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

# Inizializzazione variabili di sessione
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# --- STILE CSS PREMIUM ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stVerticalBlock"] > div:has(div.stMarkdown) {
        background-color: #1a1c24; border-radius: 15px; padding: 20px; border: 1px solid #2d2f39;
    }
    .stButton>button { border-radius: 10px !important; font-weight: bold !important; height: 3em !important; }
    .scadenza-box { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white; }
    .tagliando { background-color: #1e3a5f; border-left: 5px solid #3b82f6; }
    .gomme { background-color: #143e2f; border-left: 5px solid #10b981; }
    .status-riparato { color: #00ff00; font-weight: bold; border: 1px solid #00ff00; padding: 2px 8px; border-radius: 5px; font-size: 12px; }
    .status-aperto { color: #ff4b4b; font-weight: bold; border: 1px solid #ff4b4b; padding: 2px 8px; border-radius: 5px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        return conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
    except:
        return pd.DataFrame()

def genera_pdf_storico(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "GSSA LOGISTICS - REPORT INTERVENTO", ln=True, align='C')
    pdf.ln(5); pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Data Intervento: {row['Data']}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.cell(0, 10, f"Chilometri registrati: {row['KM_Attuali']} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"SCADENZA TAGLIANDO FISSATA: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"SCADENZA GOMME FISSATA: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, f"Note: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN UTENTE ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI AL PORTALE", use_container_width=True, type="primary"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Utente: **{st.session_state.user}**")
    st.divider()
    menu = st.radio("Menu Operazioni:", ["🏠 Registro Manutenzione", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    st.divider()
    if st.button("Chiudi Sessione"):
        st.session_state.clear()
        st.rerun()

# --- PAGINA 1: MANUTENZIONE ---
if menu == "🏠 Registro Manutenzione":
    df_man = carica_dati("Manutenzione")
    df_seg = carica_dati("Segnalazioni")
    st.markdown("<h1>🛠 Registro Chilometri e Manutenzione</h1>", unsafe_allow_html=True)
    
    lista_t = sorted(df_man['Targa'].unique()) if not df_man.empty else ["GG730AV"]
    t_sel = st.selectbox("Seleziona il Veicolo:", lista_t)
    
    # Alert Guasti Aperti per il mezzo
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background-color:#442222; border:1px solid #ff4b4b; padding:15px; border-radius:10px; color:#ffbcbc; margin-bottom:15px;'>
            ⚠️ <b>ATTENZIONE:</b> Sono presenti {len(guasti_aperti)} guasti segnalati per questo mezzo!
        </div>""", unsafe_allow_html=True)
        for _, g in guasti_aperti.iterrows(): st.write(f"• {g['Descrizione']}")

    st.divider()
    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("Chilometri attuali rilevati sul cruscotto:", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    col1, col2 = st.columns(2)
    col1.markdown(f"<div class='scadenza-box tagliando'><small>PROSSIMO TAGLIANDO</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='scadenza-box gomme'><small>PROSSIME GOMME</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    st.markdown("### Lavori Eseguiti oggi")
    c1, c2 = st.columns(2)
    check_t = c1.checkbox("⚙️ Tagliando completato")
    check_g = c2.checkbox("🛞 Cambio gomme completato")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        st.write("Segna come riparati i guasti segnalati:")
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"fix_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("Note e lavori extra (freni, luci, olio, ecc.)")

    if st.button("💾 SALVA INTERVENTO E AGGIORNA DATABASE", use_container_width=True, type="primary"):
        # Update Manutenzione Principale
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if check_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if check_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        # Chiusura guasti
        if lavori_chiusi:
            for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        # Nuovo record nello storico
        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_pross_t), "KM_prossime_Gomme": str(km_pross_g), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        
        conn.update(worksheet="Manutenzione", data=df_man)
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("✅ Dati registrati correttamente!"); st.balloons()

# --- PAGINA 2: SEGNALAZIONE ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h1>⚠️ Segnala un nuovo problema</h1>", unsafe_allow_html=True)
    df_man = carica_dati("Manutenzione")
    t_guasto = st.selectbox("Seleziona Veicolo:", sorted(df_man['Targa'].unique()))
    desc = st.text_area("Cosa c'è da riparare?")
    urg = st.select_slider("Livello Urgenza:", options=["BASSA", "MEDIA", "ALTA"])
    
    if st.button("INVIA SEGNALAZIONE ALL'OFFICINA", use_container_width=True, type="primary"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.warning("⚠️ Segnalazione inviata con successo!")

# --- PAGINA 3: ADMIN & ARCHIVIO ---
elif menu == "📋 Archivio & Admin":
    st.markdown("<h1>📋 Dashboard Amministrativa</h1>", unsafe_allow_html=True)
    
    if not st.session_state.is_admin:
        pwd = st.text_input("Inserisci Password Admin", type="password")
        if st.button("SBLOCCA", use_container_width=True):
            if pwd == "GSSA2026":
                st.session_state.is_admin = True; st.rerun()
            else: st.error("Password errata.")

    if st.session_state.is_admin:
        if st.button("🔒 Esci da Admin"): st.session_state.is_admin = False; st.rerun()
        
        df_man = carica_dati("Manutenzione")
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")

        # 1. RIEPILOGO GUASTI APERTI
        st.subheader("🚨 Guasti da Risolvere (Tutta la Flotta)")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                ritardo = (datetime.now() - datetime.strptime(r['Data_Segnalazione'], "%d/%m/%Y")).days >= 2
                colore = "#ff4b4b" if ritardo else "#3b82f6"
                with st.container():
                    st.markdown(f"<div style='border:1px solid {colore}; padding:15px; border-radius:10px; margin-bottom:10px;'><b>{r['Targa']}</b>: {r['Descrizione']}<br><small>Segnalato il {r['Data_Segnalazione']} {'🚨 <b>RITARDO</b>' if ritardo else ''}</small></div>", unsafe_allow_html=True)
                    if st.button(f"✅ Segna {r['Targa']} come Riparato", key=f"fix_adm_{i}"):
                        df_seg.at[i, 'Stato'] = 'CHIUSO'
                        conn.update(worksheet="Segnalazioni", data=df_seg)
                        # Storico automatico
                        idx_m = df_man.index[df_man['Targa'] == r['Targa']].tolist()[0]
                        nuovo_s = pd.DataFrame([{"Targa": r['Targa'], "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": df_man.at[idx_m, 'KM_Attuali'], "KM_prossimo_Tagliando": df_man.at[idx_m, 'KM_prossimo Tagliando'], "KM_prossime_Gomme": df_man.at[idx_m, 'KM_prossime Gomme'], "User": st.session_state.user, "Altro": f"RIPARAZIONE ADMIN: {r['Descrizione']}"}])
                        df_sto_v = carica_dati("Storico")
                        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
                        st.rerun()
        else: st.success("Nessun guasto aperto.")

        st.divider()
        st.subheader("🔍 Ricerca Veicolo")
        t_search = st.selectbox("Seleziona Mezzo:", sorted(df_man['Targa'].unique()))
        
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("**Guasti del mezzo:**")
            for _, r in df_seg[df_seg['Targa'] == t_search].sort_index(ascending=False).iterrows():
                tag = '<span class="status-riparato">Riparato</span>' if r['Stato'] == 'CHIUSO' else '<span class="status-aperto">Non riparato</span>'
                st.markdown(f"• {r['Data_Segnalazione']}: {r['Descrizione']} | {tag}", unsafe_allow_html=True)
        with c_b:
            st.write("**Report Manutenzione:**")
            for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
                st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"p_{i}")
