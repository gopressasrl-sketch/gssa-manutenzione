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

# --- LISTA TARGHE AGGIORNATA (52 Mezzi) ---
TARGHE_INIZIALI = sorted(list(set([
    "HB183CY", "HB284CY", "HB339CY", "HB184CY", "GG730AV", "GG243ZM", "GG677RR", "GG927ZP", 
    "GG429ZP", "GG790ZL", "GG075ZP", "GG206JK", "GG834JH", "GG477JF", "GG736AV", "GZ399JY", 
    "GZ401JY", "HA717DG", "GS597DF", "GZ532JY", "HA412FV", "HA630DC", "HA881MM", "GZ249ZS", 
    "GZ023SB", "HA668DG", "HA942FV", "HA953FV", "HA957FV", "HA539SS", "GG392AW", "GG733AV", 
    "GG303AW", "GG161HW", "GG850JH", "GG828JH", "GG831AV", "GG318AW", "GG484JF", "GG408AW", 
    "GG341AW", "GG207JK", "GG558JH", "GG564JH", "GG181HW", "GG473JF", "GG208JK", "GG829JH", 
    "GG192ZN", "GG163HW", "GJ873LS"
])))

# --- FUNZIONI DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_int(val):
    try: return int(float(str(val).replace(',', '.'))) if str(val).strip() not in ["", "-", "nan", "None"] else 0
    except: return 0

def carica_dati(foglio):
    try:
        df = conn.read(worksheet=foglio, ttl=0).fillna("").astype(str)
        if df.empty and foglio == "Manutenzione":
            # Se il foglio è vuoto, lo popoliamo con la lista iniziale
            data = [{"Targa": t, "KM_Attuali": "0", "KM_Gomme": "0", "KM_prossime Gomme": "0", 
                     "KM_Tagliando": "0", "KM_prossimo Tagliando": "0", "Data": "-", "User": "-", "Link_Report": "-", "Altro": "-"} for t in TARGHE_INIZIALI]
            df = pd.DataFrame(data)
            conn.update(worksheet="Manutenzione", data=df)
        return df
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
    pdf.multi_cell(0, 10, f"Note salvate: {row['Altro']}")
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🚚 GSSA PORTAL</h1>", unsafe_allow_html=True)
    nome = st.text_input("Inserisci il tuo Nome e Cognome")
    if st.button("ACCEDI", use_container_width=True, type="primary"):
        if nome:
            st.session_state.user = nome.upper()
            st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### Benvenuto\n**{st.session_state.user}**")
    st.divider()
    menu = st.radio("Scegli operazione:", ["🏠 Registro Manutenzione", "⚠️ Segnala Guasto", "📋 Archivio & Admin"])
    st.divider()
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

df_man = carica_dati("Manutenzione")
lista_mezzi = sorted(df_man['Targa'].unique().tolist()) if not df_man.empty else TARGHE_INIZIALI

# --- PAGINA 1: MANUTENZIONE ---
if menu == "🏠 Registro Manutenzione":
    df_seg = carica_dati("Segnalazioni")
    st.markdown("<h1>🛠 Registro Manutenzione</h1>", unsafe_allow_html=True)
    
    t_sel = st.selectbox("Seleziona il Veicolo:", lista_mezzi)
    
    guasti_aperti = df_seg[(df_seg['Targa'] == t_sel) & (df_seg['Stato'] == 'APERTO')]
    if not guasti_aperti.empty:
        st.markdown(f"""<div style='background-color:#442222; border:1px solid #ff4b4b; padding:15px; border-radius:10px; color:#ffbcbc; margin-bottom:15px;'>⚠️ <b>ATTENZIONE:</b> Guasti aperti segnalati!</div>""", unsafe_allow_html=True)
        for _, g in guasti_aperti.iterrows(): st.write(f"• {g['Descrizione']}")

    st.divider()
    idx = df_man.index[df_man['Targa'] == t_sel].tolist()[0]
    km_att = st.number_input("Chilometri attuali rilevati:", value=safe_int(df_man.at[idx, 'KM_Attuali']), step=1)
    
    km_pross_t = km_att + 30000
    km_pross_g = km_att + 40000
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='scadenza-box tagliando'><small>TAGLIANDO A</small><br><b style='font-size:24px;'>{km_pross_t} km</b></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='scadenza-box gomme'><small>GOMME A</small><br><b style='font-size:24px;'>{km_pross_g} km</b></div>", unsafe_allow_html=True)

    st.markdown("### Interventi eseguiti")
    ch_t = st.checkbox("⚙️ Tagliando completato")
    ch_g = st.checkbox("🛞 Cambio gomme completato")
    
    lavori_chiusi = []
    if not guasti_aperti.empty:
        for i, g in guasti_aperti.iterrows():
            if st.checkbox(f"Riparato: {g['Descrizione']}", key=f"f_{i}"): lavori_chiusi.append(i)

    altro = st.text_area("Note e lavori extra")

    if st.button("💾 SALVA INTERVENTO", use_container_width=True, type="primary"):
        df_man.at[idx, 'KM_Attuali'] = str(km_att)
        if ch_t:
            df_man.at[idx, 'KM_Tagliando'] = str(km_att)
            df_man.at[idx, 'KM_prossimo Tagliando'] = str(km_pross_t)
        if ch_g:
            df_man.at[idx, 'KM_Gomme'] = str(km_att)
            df_man.at[idx, 'KM_prossime Gomme'] = str(km_pross_g)
        df_man.at[idx, 'Data'] = datetime.now().strftime("%d/%m/%Y")
        df_man.at[idx, 'User'] = st.session_state.user
        
        if lavori_chiusi:
            for idx_g in lavori_chiusi: df_seg.at[idx_g, 'Stato'] = 'CHIUSO'
            conn.update(worksheet="Segnalazioni", data=df_seg)

        nuovo_s = pd.DataFrame([{"Targa": t_sel, "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": str(km_att), "KM_prossimo_Tagliando": str(km_pross_t), "KM_prossime_Gomme": str(km_pross_g), "User": st.session_state.user, "Altro": altro}])
        df_sto_v = carica_dati("Storico")
        conn.update(worksheet="Manutenzione", data=df_man)
        conn.update(worksheet="Storico", data=pd.concat([df_sto_v, nuovo_s], ignore_index=True))
        st.success("✅ Salvato!"); st.balloons()

# --- PAGINA 2: SEGNALAZIONE ---
elif menu == "⚠️ Segnala Guasto":
    st.markdown("<h1>⚠️ Segnala Problema</h1>", unsafe_allow_html=True)
    t_guasto = st.selectbox("Seleziona Veicolo:", lista_mezzi)
    desc = st.text_area("Descrizione del guasto")
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
        if st.text_input("Password Admin", type="password") == "GSSA2026":
            st.session_state.is_admin = True; st.rerun()
    
    if st.session_state.is_admin:
        if st.button("🔒 Esci da Admin"): st.session_state.is_admin = False; st.rerun()
        
        # Aggiunta Veicolo
        with st.expander("➕ AGGIUNGI NUOVO VEICOLO"):
            nv = st.text_input("Nuova Targa").upper().replace(" ", "")
            if st.button("REGISTRA"):
                if nv and nv not in lista_mezzi:
                    nuova_r = pd.DataFrame([{"Targa": nv, "KM_Attuali": "0", "KM_Gomme": "0", "KM_prossime Gomme": "0", "KM_Tagliando": "0", "KM_prossimo Tagliando": "0", "Data": "-", "User": "-", "Link_Report": "-", "Altro": "-"}])
                    conn.update(worksheet="Manutenzione", data=pd.concat([df_man, nuova_r], ignore_index=True))
                    st.success("Aggiunto!"); st.rerun()

        st.divider()
        df_seg = carica_dati("Segnalazioni")
        df_sto = carica_dati("Storico")

        st.subheader("🚨 Guasti Aperti in Flotta")
        df_aperti = df_seg[df_seg['Stato'] == 'APERTO']
        if not df_aperti.empty:
            for i, r in df_aperti.iterrows():
                st.markdown(f"<div style='border:1px solid #3b82f6; padding:10px; border-radius:10px; margin-bottom:5px;'><b>{r['Targa']}</b>: {r['Descrizione']} (del {r['Data_Segnalazione']})</div>", unsafe_allow_html=True)
                if st.button(f"Sistemato {r['Targa']} - {i}", key=f"adm_{i}"):
                    df_seg.at[i, 'Stato'] = 'CHIUSO'; conn.update(worksheet="Segnalazioni", data=df_seg)
                    # Crea storico riparazione
                    idx_m = df_man.index[df_man['Targa'] == r['Targa']].tolist()[0]
                    nuovo_s = pd.DataFrame([{"Targa": r['Targa'], "Data": datetime.now().strftime("%d/%m/%Y %H:%M"), "KM_Attuali": df_man.at[idx_m, 'KM_Attuali'], "KM_prossimo_Tagliando": df_man.at[idx_m, 'KM_prossimo Tagliando'], "KM_prossime_Gomme": df_man.at[idx_m, 'KM_prossime Gomme'], "User": st.session_state.user, "Altro": f"RIPARAZIONE ADMIN: {r['Descrizione']}"}])
                    conn.update(worksheet="Storico", data=pd.concat([df_sto, nuovo_s], ignore_index=True))
                    st.rerun()
        else: st.success("Nessun guasto aperto.")

        st.divider()
        t_search = st.selectbox("Storico Veicolo:", lista_mezzi)
        c_a, c_b = st.columns(2)
        with c_a:
            st.write("Guasti Mezzo:")
            for _, r in df_seg[df_seg['Targa'] == t_search].sort_index(ascending=False).iterrows():
                st.markdown(f"{'🟢' if r['Stato'] == 'CHIUSO' else '🔴'} {r['Data_Segnalazione']}: {r['Descrizione']}")
        with c_b:
            st.write("Report PDF:")
            for i, r in df_sto[df_sto['Targa'] == t_search].sort_index(ascending=False).iterrows():
                st.download_button(f"📄 Report {r['Data']}", data=genera_pdf_storico(r), file_name=f"Report_{t_search}.pdf", key=f"pdf_{i}")
