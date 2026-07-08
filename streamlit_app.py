import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="GSSA GESTIONE PRO", layout="wide")

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
    pdf.cell(0, 10, f"Data: {row['Data']}", ln=True)
    pdf.cell(0, 10, f"Veicolo: {row['Targa']} | Operatore: {row['User']}", ln=True)
    pdf.ln(10); pdf.cell(0, 10, f"Chilometri registrati: {row['KM_Attuali']} km", ln=True)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"PROSSIMO TAGLIANDO: {row['KM_prossimo_Tagliando']} km", ln=True)
    pdf.cell(0, 10, f"PROSSIME GOMME: {row['KM_prossime_Gomme']} km", ln=True)
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, f"Note: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
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
    menu = st.radio("Menu:", ["🏠 Registro Manutenzione", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    st.divider()
    if st.button("Esci dal portale"):
        st.session_state.clear()
        st.rerun()

# Caricamento iniziale delle targhe dinamico dal database
df_man = carica_dati("Manutenzione")
lista_targhe_attuali = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else []

# --- PAGINA 1: MANUTENZIONE ---
if menu == "🏠 Registro Manutenzione":
    df_seg = carica_dati("Segnalazioni")
    st.markdown("<h1>🛠 Registro Manutenzione</h1>", unsafe_allow_html=True)
    
    if not lista_targhe_attuali:
        st.warning("Nessun veicolo in database. Vai in Admin per aggiungerne uno.")
    else:
        t_sel = st.selectbox("Seleziona il Veicolo:", lista_targhe_attuali)
        
        guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
        if not guasti_aperti.empty:
            st.markdown(f"<div style='background-color:#442222; border:1px solid #ff4b4b; padding:15px; border-radius:10px; color:#ffbcbc; margin-bottom:15px;'>⚠️ <b>ATTENZIONE:</b> Guasti aperti per questo mezzo!</div>", unsafe_allow_html=True)
            for _, g in guasti_aperti.iterrows(): st.write(f"• {g['Descrizione']}")

        st.divider()
        idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
        km_att = st.number_input("Chilometri attuali:", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
        
        km_pross_t = km_att + 30000
        km_pross_g = km_att + 40000
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

        check_t = st.checkbox("⚙️ Tagliando completato")
        check_g = st.checkbox("🛞 Cambio gomme completato")
        lavori_chiusi = []
        if not guasti_aperti.empty:
            for i, g in guasti_aperti.iterrows():
                if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

        altro = st.text_area("Note e lavori extra")

        if st.button("💾 SALVA INTERVENTO", use_container_width=True, type="primary"):
            df_man.at[idx, 'KM_Attuali'] = str(km_att)
            if check_t:
                df_man.at[idx, 'KM_Tagliando'] = str(km_att)
                df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
            if check_g:
                df_man.at[idx, 'KM_Gomme'] = str(km_att)
                df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
            df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
            df_man.at[idx, 'User'] = st.session_state.user
            
            if lavori_chiusi:
                for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
                conn.update(worksheet="Segnalazioni", data=df_seg)

            nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_pross_t), "KM_prossime_Gomme": str(km_pross_g), "User": st.session_state.user, "Altro": altro}])
            conn.update(worksheet="Manutenzione", data=df_man)
            df_sto_v = carica_dati("Storico")
            conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
            st.success("✅ Salvato!"); st.balloons()

# --- PAGINA 2: SEGNALAZIONE ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h1>⚠️ Segnala Problema</h1>", unsafe_allow_html=True)
    t_guasto = st.selectbox("Seleziona Veicolo:", lista_targhe_attuali)
    desc = st.text_area("Cosa c'è da riparare?")
    urg = st.select_slider("Urgenza:", options=["BASSA", "MEDIA", "ALTA"])
    if st.button("INVIA SEGNALAZIONE", use_container_width=True, type="primary"):
        nuova_s = pd.DataFrame([{"Targa": t_guasto, "Data_Segnalazione": datetime.now().strftime("%d/%m/%Y"), "Descrizione": desc, "Urgenza": urg, "Operatore": st.session_state.user, "Stato": "APERTO"}])
        df_s_v = carica_dati("Segnalazioni")
        conn.update(worksheet="Segnalazioni", data=pd.concat([df_s_v, nuova_s], ignore_index=True))
        st.warning("⚠️ Segnalazione inviata!")

# --- PAGINA 3: ADMIN & ARCHIVIO ---
elif menu == "📋 Archivio & Admin":
    st.markdown("<h1>📋 Dashboard Amministrativa</h1>", unsafe_allow_html=True)
    if not st.session_state.is_admin:
        pwd = st.text_input("Password Admin", type="password")
        if st.button("SBLOCCA"):
            if pwd == "GSSA2026": st.session_state.is_admin = True; st.rerun()
            else: st.error("Errata")

    if st.session_state.is_admin:
        # --- FUNZIONE AGGIUNTA TARGA ---
        with st.expander("➕ AGGIUNGI NUOVO VEICOLO ALLA FLOTTA"):
            nuova_targa = st.text_input("Inserisci Targa (es. AB123CD)").upper().replace(" ", "")
            if st.button("REGISTRA NUOVO VEICOLO"):
                if nuova_targa and nuova_targa not in lista_targhe_attuali:
                    nuova_riga = pd.DataFrame([{
                        "Targa": nuova_targa, "KM_Attuali": "0", "KM_Gomme": "0", "KM_prossime Gomme": "0",
                        "KM_Tagliando": "0", "KM_prossimo Tagliando": "0", "Data": "-", "User": "-", "Link_Report": "-", "Altro": "-"
                    }])
                    df_aggiornato = pd.concat([df_man, nuova_riga], ignore_index=True)
                    conn.update(worksheet="Manutenzione", data=df_aggiornato)
                    st.success(f"Veicolo {nuova_targa} aggiunto correttamente!")
                    st.rerun()
                else:
                    st.error("Targa vuota o già esistente.")

        st.divider()
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")

        st.subheader("🚨 Guasti Aperti")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        for i, r in df_aperti.iterrows():
            st.markdown(f"<div style='border:1px solid #3b82f6; padding:10px; border-radius:10px; margin-bottom:5px;'><b>{r['Targa']}</b>: {r['Descrizione']}</div>", unsafe_allow_html=True)
            if st.button(f"Sistemato {r['Targa']}", key=f"adm_{i}"):
                df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg); st.rerun()

        st.divider()
        t_search = st.selectbox("Storico Mezzo:", lista_targhe_attuali)
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("Guasti:")
            for _, r in df_seg[df_seg['Targa'] == t_search].sort_index(ascending=False).iterrows():
                tag = "🟢" if r['Stato'] == 'CHIUSO' else "🔴"
                st.write(f"{tag} {r['Data_Segnalazione']}: {r['Descrizione']}")
        with col_b:
            st.write("Report:")
            for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
                st.download_button(f"📄 PDF {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"pdf_{i}")
