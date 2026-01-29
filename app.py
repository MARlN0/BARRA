import streamlit as st
import pandas as pd
import random
from datetime import date
import json
import os
import base64

# Intentamos importar FPDF, si falla (porque no se ha instalado requirements.txt), no rompemos la app inmediatamente
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Falta instalar FPDF. Por favor crea el archivo requirements.txt")
    FPDF = None

# --- 1. CONFIGURACIÓN VISUAL (CSS AVANZADO) ---
st.set_page_config(page_title="Barra Staff Pro", page_icon="🍸", layout="wide")

st.markdown("""
    <style>
    /* Ocultar la barra de herramientas de las tablas (Lupa, descargar, etc.) */
    [data-testid="stElementToolbar"] {
        display: none;
    }

    /* OPTIMIZACIÓN MÓVIL */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
        }
        
        /* Ajuste de tablas para que no haya huecos */
        div[data-testid="stDataEditor"] table {
            font-size: 13px !important;
        }
        div[data-testid="stDataEditor"] th {
            font-size: 10px !important;
            padding: 2px !important;
            text-align: center !important;
        }
        div[data-testid="stDataEditor"] td {
            padding: 0px 2px !important;
        }
        
        /* Botones grandes */
        .stButton button {
            width: 100% !important;
            height: 3.5rem !important;
            border-radius: 8px !important;
            font-weight: bold !important;
        }
    }

    /* TARJETAS */
    .plan-card {
        border: 1px solid rgba(200, 200, 200, 0.3);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 10px;
        background-color: rgba(128, 128, 128, 0.05);
    }
    .barra-header {
        font-size: 1.1rem;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--text-color);
        border-bottom: 3px solid #FF4B4B;
        margin-bottom: 8px;
        padding-bottom: 4px;
    }
    .fila-rol {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    .badge {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
        background-color: rgba(128, 128, 128, 0.15);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN DE SEGURIDAD ---
def check_password():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center;'>🔐 Acceso QiuClub</h3>", unsafe_allow_html=True)
                user = st.text_input("Usuario", key="login_user")
                password = st.text_input("Contraseña", type="password", key="login_pass")
                if st.button("Ingresar", type="primary", use_container_width=True):
                    if user == "qiuclub" and password == "barra2026":
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.error("Datos incorrectos")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. GENERADOR PDF ---
if FPDF:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'REPORTE OPERATIVO - BARRA STAFF', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    def generar_pdf(evento, fecha, plan, banca):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"EVENTO: {evento}  |  FECHA: {fecha}", 0, 1)
        pdf.ln(5)
        
        for barra, equipo in plan.items():
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, barra, 1, 1, 'L', fill=True)
            
            pdf.set_font("Arial", "", 10)
            for miembro in equipo:
                rol = miembro['Rol'].replace("👑", "Jefe").replace("🍺", "Bar").replace("🧊", "Ayu")
                nombre = miembro['Nombre']
                pdf.cell(40, 7, rol, 1)
                pdf.cell(0, 7, nombre, 1, 1)
            pdf.ln(3)
            
        pdf.ln(5)
        pdf.set_fill_color(255, 200, 200)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"BANCA / DISPONIBLES ({len(banca)})", 1, 1, 'L', fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, ", ".join(banca), border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. SISTEMA DE DATOS ---
DB_FILE = "base_datos_staff.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                df_staff = pd.DataFrame(data['staff'])
                eventos = data['eventos']
                for ev_name, ev_data in eventos.items():
                    for barra in ev_data['Barras']:
                        barra['matriz_competencias'] = pd.DataFrame(barra['matriz_competencias'])
                return df_staff, eventos, data['historial'], data['logs']
        except: pass
    
    df = pd.DataFrame({
        'Nombre': ['Sebastian', 'Sandro', 'Vladimir', 'Kevin', 'Jhon', 'Forest', 'Guillermo', 'Jair', 'Jordi', 'Pedro', 'Franklin', 'Luis', 'Gabriel', 'Gerald', 'Marcelo', 'Leandro', 'Manuel', 'Kers'],
        'Cargo_Default': ['BARTENDER', 'BARTENDER', 'AYUDANTE', 'BARTENDER', 'AYUDANTE', 'BARTENDER', 'BARTENDER', 'BARTENDER', 'AYUDANTE', 'BARTENDER', 'AYUDANTE', 'AYUDANTE', 'AYUDANTE', 'BARTENDER', 'BARTENDER', 'BARTENDER', 'BARTENDER', 'BARTENDER']
    })
    return df, {}, {}, []

def guardar_datos():
    staff_json = st.session_state['db_staff'].to_dict(orient='records')
    eventos_json = {}
    for ev_name, ev_data in st.session_state['db_eventos'].items():
        barras_clean = []
        for barra in ev_data['Barras']:
            b_copy = barra.copy()
            b_copy['matriz_competencias'] = barra['matriz_competencias'].to_dict(orient='records')
            barras_clean.append(b_copy)
        eventos_json[ev_name] = {'Staff_Convocado': ev_data['Staff_Convocado'], 'Barras': barras_clean}

    data = {
        'staff': staff_json, 'eventos': eventos_json,
        'historial': st.session_state['db_historial_algoritmo'], 'logs': st.session_state['db_logs_visuales']
    }
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

if 'db_staff' not in st.session_state:
    s, e, h, l = cargar_datos()
    st.session_state['db_staff'] = s
    st.session_state['db_eventos'] = e
    st.session_state['db_historial_algoritmo'] = h
    st.session_state['db_logs_visuales'] = l

# --- 5. LOGICA ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    df = df.sort_values(by=['sort_key', 'Nombre'])
    return df.drop('sort_key', axis=1)

def agregar_indice(df):
    df_new = df.copy()
    df_new.insert(0, "N°", range(1, len(df_new) + 1))
    return df_new

def calc_altura(df):
    return (len(df) * 35) + 38

def ejecutar_algoritmo(nombre_evento):
    datos = st.session_state['db_eventos'][nombre_evento]
    hist = st.session_state['db_historial_algoritmo'].get(nombre_evento, {})
    asignacion = {}
    asignados = set()
    new_hist = {}

    for barra in datos['Barras']:
        nb = barra['nombre']
        req = barra['requerimientos']
        matriz = barra['matriz_competencias']
        equipo = []
        pool = matriz[~matriz['Nombre'].isin(asignados)].copy()

        for _ in range(req['enc']):
            cands = pool[pool['Es_Encargado']==True]
            validos = [r['Nombre'] for _, r in cands.iterrows() if hist.get(r['Nombre'], "") != nb]
            if not validos and not cands.empty: validos = cands['Nombre'].tolist()
            if validos:
                elegido = random.choice(validos)
                equipo.append({'Rol': 'Encargado', 'Icon': '👑', 'Nombre': elegido})
                asignados.add(elegido)
                new_hist[elegido] = nb
                pool = pool[pool['Nombre']!=elegido]
            else: equipo.append({'Rol': 'Encargado', 'Icon': '👑', 'Nombre': 'VACANTE'})

        for _ in range(req['bar']):
            cands = pool[pool['Es_Bartender']==True]
            if not cands.empty:
                elegido = random.choice(cands['Nombre'].tolist())
                equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': elegido})
                asignados.add(elegido)
                pool = pool[pool['Nombre']!=elegido]
            else: equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': 'VACANTE'})

        for _ in range(req['ayu']):
            cands = pool[pool['Es_Ayudante']==True]
            if not cands.empty:
                elegido = random.choice(cands['Nombre'].tolist())
                equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': elegido})
                asignados.add(elegido)
                pool = pool[pool['Nombre']!=elegido]
            else: equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': 'VACANTE'})
        
        asignacion[nb] = equipo
    banca = [p for p in datos['Staff_Convocado'] if p not in asignados]
    return asignacion, banca, new_hist

# --- 6. APP ---
st.title("🍸 Barra Staff V1")

tab1, tab2, tab3, tab4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

with tab1:
    with st.expander("➕ Alta / Baja"):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="rh_nn")
        nr = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"], key="rh_nr")
        if st.button("Guardar", key="rh_sv", use_container_width=True):
            if nn:
                nuevo = pd.DataFrame({'Nombre': [nn], 'Cargo_Default': [nr]})
                st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                guardar_datos()
                st.rerun()
        df_del = ordenar_staff(st.session_state['db_staff'])
        list_del = st.multiselect("Eliminar:", df_del['Nombre'].tolist(), key="rh_dl")
        if st.button("🚨 Eliminar", key="rh_bd", use_container_width=True):
            st.session_state['db_staff'] = st.session_state['db_staff'][~st.session_state['db_staff']['Nombre'].isin(list_del)]
            guardar_datos()
            st.rerun()

    st.caption("Nómina")
    df_v = ordenar_staff(st.session_state['db_staff'])
    df_v = agregar_indice(df_v)
    h_n = calc_altura(df_v)
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=h_n,
                 column_config={"N°": st.column_config.NumberColumn("N°", width="small", format="%d")})

with tab2:
    with st.expander("🆕 Evento"):
        ne = st.text_input("Nombre", key="cf_ne")
        if st.button("Crear", key="cf_bc", use_container_width=True):
            if ne and ne not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][ne] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][ne] = {}
                guardar_datos()
                st.rerun()

    lev = list(st.session_state['db_eventos'].keys())
    if not lev: st.stop()
    ev = st.selectbox("Evento:", lev, key="cf_se")
    dat = st.session_state['db_eventos'][ev]
    
    st.markdown("##### 1. Plantilla")
    df_b = ordenar_staff(st.session_state['db_staff'])
    conv = set(dat['Staff_Convocado'])
    df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    df_b = agregar_indice(df_b)
    
    with st.form("fp"):
        h_p = calc_altura(df_b)
        df_ed = st.data_editor(
            df_b,
            column_config={
                "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                "OK": st.column_config.CheckboxColumn("✅", width="small"),
                "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                "Cargo_Default": None 
            },
            disabled=["N°", "Nombre"], use_container_width=True, hide_index=True, height=h_p
        )
        if st.form_submit_button("💾 Guardar Plantilla", use_container_width=True):
            st.session_state['db_eventos'][ev]['Staff_Convocado'] = df_ed[df_ed['OK']==True]['Nombre'].tolist()
            guardar_datos()
            st.rerun()

    st.markdown("##### 2. Barras")
    lista_ok = dat['Staff_Convocado']
    if lista_ok:
        with st.expander("➕ Crear Barra"):
            with st.form("fb"):
                nb = st.text_input("Nombre", key="bn")
                c1, c2, c3 = st.columns(3)
                ne = c1.number_input("E", 0, 5, 1, key="be")
                nba = c2.number_input("B", 0, 5, 1, key="bb")
                nay = c3.number_input("A", 0, 5, 1, key="ba")
                
                df_m = df_b[df_b['Nombre'].isin(lista_ok)].copy().drop(['OK', 'N°'], axis=1)
                df_m['Es_Encargado'] = False; df_m['Es_Bartender'] = df_m['Cargo_Default']=='BARTENDER'; df_m['Es_Ayudante'] = df_m['Cargo_Default']=='AYUDANTE'
                df_m = agregar_indice(df_m[['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']])
                h_m = calc_altura(df_m)
                
                mo = st.data_editor(df_m, use_container_width=True, hide_index=True, height=h_m,
                    column_config={
                        "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                        "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                        "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                        "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                        "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small")
                    })
                if st.form_submit_button("Guardar", use_container_width=True):
                    if nb:
                        nueva = {'nombre': nb, 'requerimientos': {'enc': ne, 'bar': nba, 'ayu': nay}, 'matriz_competencias': mo.drop('N°', axis=1)}
                        st.session_state['db_eventos'][ev]['Barras'].append(nueva)
                        guardar_datos()
                        st.rerun()

        for i, barra in enumerate(dat['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"fe_{i}"):
                    nnb = st.text_input("Nombre", barra['nombre'], key=f"en_{i}")
                    c1, c2, c3 = st.columns(3)
                    req = barra['requerimientos']
                    nne = c1.number_input("E", 0, 5, req['enc'], key=f"ee_{i}")
                    nnba = c2.number_input("B", 0, 5, req['bar'], key=f"eb_{i}")
                    nnay = c3.number_input("A", 0, 5, req['ayu'], key=f"ea_{i}")
                    
                    df_e = agregar_indice(barra['matriz_competencias'])
                    h_e = calc_altura(df_e)
                    me = st.data_editor(df_e, use_container_width=True, hide_index=True, height=h_e,
                        column_config={
                            "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                            "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                            "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                            "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                            "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small")
                        })
                    if st.form_submit_button("Actualizar", use_container_width=True):
                        st.session_state['db_eventos'][ev]['Barras'][i] = {'nombre': nnb, 'requerimientos': {'enc': nne, 'bar': nnba, 'ayu': nnay}, 'matriz_competencias': me.drop('N°', axis=1)}
                        guardar_datos()
                        st.rerun()
                if st.button("Borrar", key=f"bd_{i}", use_container_width=True):
                    st.session_state['db_eventos'][ev]['Barras'].pop(i)
                    guardar_datos()
                    st.rerun()

with tab3:
    c1, c2 = st.columns(2)
    fec = c1.date_input("Fecha", date.today(), key="op_dt")
    evr = c2.selectbox("Evento Op.", lev, key="op_sl")
    
    if st.button("🚀 GENERAR ROTACIÓN", type="primary", key="op_go", use_container_width=True):
        if not st.session_state['db_eventos'][evr]['Barras']: st.error("Faltan barras.")
        else:
            p, b, u = ejecutar_algoritmo(evr)
            st.session_state['res'] = {'plan': p, 'banca': b, 'up': u, 'ev': evr, 'fecha': fec}
    
    if 'res' in st.session_state and st.session_state['res']['ev'] == evr:
        r = st.session_state['res']
        st.divider()
        
        # EXPORT PDF
        if FPDF:
            pdf_data = generar_pdf(r['ev'], str(r['fecha']), r['plan'], r['banca'])
            st.download_button("📄 Descargar PDF", pdf_data, f"Plan_{r['ev']}.pdf", "application/pdf", type="primary", use_container_width=True)
        
        edit_mode = st.toggle("✏️ Editar Asignación", key="op_tgl")
        banca_act = sorted(r['banca'])
        cols = st.columns(3)
        idx = 0
        for b_nom, eq in r['plan'].items():
            with cols[idx % 3]: 
                st.markdown(f"""<div class="plan-card"><div class="barra-header">{b_nom}</div>""", unsafe_allow_html=True)
                for i, m in enumerate(eq):
                    rol = m['Rol']; ic = m.get('Icon', ''); nm = m['Nombre']
                    if edit_mode:
                        ops = [nm] + banca_act
                        nnm = st.selectbox(f"{ic} {rol}", ops, index=0, key=f"sl_{b_nom}_{i}", label_visibility="collapsed")
                        if nnm != nm:
                            if nnm != "VACANTE" and nnm in r['banca']: r['banca'].remove(nnm)
                            if nm != "VACANTE": r['banca'].append(nm)
                            r['plan'][b_nom][i]['Nombre'] = nnm
                            st.rerun()
                    else:
                        color = "#FF4B4B" if nm == "VACANTE" else "var(--text-color)"
                        st.markdown(f"""<div class="fila-rol"><span class="badge">{ic} {rol}</span><span style="font-weight:bold; color:{color}">{nm}</span></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1
            
        st.info(f"Banca: {', '.join(r['banca'])}")
        if st.button("💾 CERRAR FECHA Y GUARDAR", key="op_save", use_container_width=True):
            nu = {}
            for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE": nu[m['Nombre']] = b
            for n, b in nu.items(): st.session_state['db_historial_algoritmo'][r['ev']][n] = b
            log = {'Fecha': str(r['fecha']), 'Evento': r['ev'], 'Plan': r['plan'], 'Banca': list(r['banca'])}
            st.session_state['db_logs_visuales'].append(log)
            guardar_datos()
            st.success("Guardado.")

with tab4:
    logs = st.session_state['db_logs_visuales']
    if logs:
        for i, log in enumerate(reversed(logs)):
            real_index = len(logs) - 1 - i
            with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                if st.button("🗑️ Eliminar Registro", key=f"del_h_{real_index}", type="primary", use_container_width=True):
                    st.session_state['db_logs_visuales'].pop(real_index)
                    guardar_datos()
                    st.rerun()
                for b, eq in log['Plan'].items():
                    st.markdown(f"**{b}**")
                    for m in eq: st.text(f"{m.get('Icon','')} {m['Rol']}: {m['Nombre']}")
                    st.divider()
                st.caption(f"Banca: {', '.join(log['Banca'])}")
    else:
        st.info("Sin historial.")
