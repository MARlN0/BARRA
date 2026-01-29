import streamlit as st
import pandas as pd
import random
from datetime import date
import json
import os

# --- 1. CONFIGURACIÓN E INYECCIÓN DE CSS (MOBILE FIRST & BRANDING) ---
st.set_page_config(page_title="Barra Staff V1", page_icon="🍸", layout="wide")

st.markdown("""
    <style>
    /* --- OPTIMIZACIÓN MÓVIL EXTREMA --- */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
        }
        
        /* FUENTE Y ESPACIADO DE TABLA */
        div[data-testid="stDataEditor"] table {
            font-size: 13px !important;
        }
        div[data-testid="stDataEditor"] th {
            font-size: 11px !important;
            padding: 4px !important;
        }
        div[data-testid="stDataEditor"] td {
            padding: 0px 4px !important;
            line-height: 1.2 !important;
        }
        
        /* Altura mínima de celda reducida para que quepan más */
        div[data-testid="stDataEditor"] div[role="gridcell"] {
            min-height: 35px !important;
            height: 35px !important;
            display: flex;
            align-items: center;
        }
        
        /* Títulos */
        h1 { font-size: 1.8rem !important; }
        h2, h3 { font-size: 1.2rem !important; }
        
        /* Botones grandes */
        .stButton button {
            width: 100% !important;
            height: 3rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
    }

    /* ESTILOS GENERALES */
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; }
    
    /* TARJETAS DE PLANIFICACIÓN */
    .plan-card {
        border: 1px solid rgba(200, 200, 200, 0.3);
        border-radius: 12px;
        padding: 10px;
        margin-bottom: 12px;
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
        letter-spacing: 1px;
    }
    
    .fila-rol {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 5px 0; 
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

# --- 2. SISTEMA DE GUARDADO ---
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
    
    # Defaults
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
        'staff': staff_json,
        'eventos': eventos_json,
        'historial': st.session_state['db_historial_algoritmo'],
        'logs': st.session_state['db_logs_visuales']
    }
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

if 'db_staff' not in st.session_state:
    s, e, h, l = cargar_datos()
    st.session_state['db_staff'] = s
    st.session_state['db_eventos'] = e
    st.session_state['db_historial_algoritmo'] = h
    st.session_state['db_logs_visuales'] = l

# --- 3. FUNCIONES LÓGICAS ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    df = df.sort_values(by=['sort_key', 'Nombre'])
    return df.drop('sort_key', axis=1)

def agregar_indice(df):
    df_new = df.copy()
    df_new.insert(0, "N°", range(1, len(df_new) + 1))
    return df_new

def calc_altura(df):
    # Fórmula mágica: (Filas * 35px) + Cabecera(38px) + Borde(3px)
    # Esto asegura que la tabla se vea ENTERA sin scroll interno.
    return (len(df) * 35) + 41

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

        # Encargados
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
            else:
                equipo.append({'Rol': 'Encargado', 'Icon': '👑', 'Nombre': 'VACANTE'})

        # Bartenders
        for _ in range(req['bar']):
            cands = pool[pool['Es_Bartender']==True]
            if not cands.empty:
                elegido = random.choice(cands['Nombre'].tolist())
                equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': elegido})
                asignados.add(elegido)
                pool = pool[pool['Nombre']!=elegido]
            else:
                equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': 'VACANTE'})

        # Ayudantes
        for _ in range(req['ayu']):
            cands = pool[pool['Es_Ayudante']==True]
            if not cands.empty:
                elegido = random.choice(cands['Nombre'].tolist())
                equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': elegido})
                asignados.add(elegido)
                pool = pool[pool['Nombre']!=elegido]
            else:
                equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': 'VACANTE'})
        
        asignacion[nb] = equipo
    banca = [p for p in datos['Staff_Convocado'] if p not in asignados]
    return asignacion, banca, new_hist

# --- 4. INTERFAZ GRÁFICA ---
st.title("🍸 Barra Staff V1")

tab1, tab2, tab3, tab4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Historial"])

# TAB 1: RH
with tab1:
    with st.expander("➕ Gestionar Personal (Alta/Baja)"):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="rh_in_name")
        nr = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"], key="rh_in_role")
        if st.button("Guardar", key="rh_btn_save", use_container_width=True):
            if nn:
                nuevo = pd.DataFrame({'Nombre': [nn], 'Cargo_Default': [nr]})
                st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                guardar_datos()
                st.rerun()
        
        st.divider()
        df_del = ordenar_staff(st.session_state['db_staff'])
        list_del = st.multiselect("Eliminar Personal:", df_del['Nombre'].tolist(), key="rh_multi_del")
        if st.button("🚨 Eliminar Seleccionados", key="rh_btn_del", use_container_width=True):
            st.session_state['db_staff'] = st.session_state['db_staff'][~st.session_state['db_staff']['Nombre'].isin(list_del)]
            guardar_datos()
            st.rerun()

    st.subheader("Nómina Completa")
    df_v = ordenar_staff(st.session_state['db_staff'])
    df_v = agregar_indice(df_v)
    
    # Altura dinámica para ver TODO sin scroll interno
    h_nomina = calc_altura(df_v)
    
    st.dataframe(
        df_v, 
        use_container_width=True, 
        hide_index=True, 
        height=h_nomina, # <--- ALTURA CALCULADA
        column_config={
            "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
            "Nombre": st.column_config.TextColumn("Nombre", width="small"),
            "Cargo_Default": st.column_config.TextColumn("Cargo", width="small")
        }
    )

# TAB 2: CONFIG
with tab2:
    with st.expander("🆕 Nuevo Evento"):
        ne = st.text_input("Nombre", key="conf_in_ev")
        if st.button("Crear", key="conf_btn_cre", use_container_width=True):
            if ne and ne not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][ne] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][ne] = {}
                guardar_datos()
                st.rerun()

    lev = list(st.session_state['db_eventos'].keys())
    if not lev: st.stop()
    ev = st.selectbox("Evento:", lev, key="conf_sel_ev")
    dat = st.session_state['db_eventos'][ev]
    
    # 1. PLANTILLA
    st.divider()
    st.markdown("##### 1. Plantilla Habilitada")
    st.caption("Selecciona quiénes pueden trabajar en este evento.")
    df_b = ordenar_staff(st.session_state['db_staff'])
    conv = set(dat['Staff_Convocado'])
    df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    df_b = agregar_indice(df_b)
    
    with st.form("f_plantilla"):
        h_plant = calc_altura(df_b)
        df_editado = st.data_editor(
            df_b,
            column_config={
                "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                "OK": st.column_config.CheckboxColumn("✅", width="small"),
                "Nombre": st.column_config.TextColumn("Nombre", width="small", disabled=True),
                "Cargo_Default": None
            },
            disabled=["N°", "Nombre"],
            use_container_width=True,
            hide_index=True,
            height=h_plant, # <--- ALTURA CALCULADA
            key="editor_plantilla"
        )
        if st.form_submit_button("💾 Guardar Plantilla", use_container_width=True):
            lista = df_editado[df_editado['OK']==True]['Nombre'].tolist()
            st.session_state['db_eventos'][ev]['Staff_Convocado'] = lista
            guardar_datos()
            st.rerun()

    # 2. BARRAS
    st.markdown("##### 2. Configuración de Barras")
    lista_ok = dat['Staff_Convocado']
    
    if lista_ok:
        with st.expander("➕ Crear Nueva Barra"):
            with st.form("f_barra"):
                nb = st.text_input("Nombre Barra", key="bar_new_name")
                c1, c2, c3 = st.columns(3)
                ne = c1.number_input("Enc", 0, 5, 1, key="bar_new_e")
                nba = c2.number_input("Bar", 0, 5, 1, key="bar_new_b")
                nay = c3.number_input("Ayu", 0, 5, 1, key="bar_new_a")
                
                df_m = df_b[df_b['Nombre'].isin(lista_ok)].copy()
                df_m = df_m.drop(['OK', 'N°'], axis=1) 
                
                df_m['Es_Encargado'] = False
                df_m['Es_Bartender'] = df_m['Cargo_Default'] == 'BARTENDER'
                df_m['Es_Ayudante'] = df_m['Cargo_Default'] == 'AYUDANTE'
                df_m = df_m[['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
                df_m = agregar_indice(df_m)
                
                h_mat = calc_altura(df_m)
                
                mo = st.data_editor(
                    df_m,
                    column_config={
                        "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                        "Nombre": st.column_config.TextColumn("Nombre", width="small", disabled=True),
                        "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                        "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                        "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=h_mat, # <--- ALTURA CALCULADA
                    key="editor_new_bar_matrix"
                )
                if st.form_submit_button("Crear Barra", use_container_width=True):
                    if nb:
                        mo_clean = mo.drop('N°', axis=1)
                        nueva = {'nombre': nb, 'requerimientos': {'enc': ne, 'bar': nba, 'ayu': nay}, 'matriz_competencias': mo_clean}
                        st.session_state['db_eventos'][ev]['Barras'].append(nueva)
                        guardar_datos()
                        st.rerun()

        for i, barra in enumerate(dat['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"ed_{i}"):
                    nnb = st.text_input("Nombre", barra['nombre'], key=f"edit_nm_{i}")
                    c1, c2, c3 = st.columns(3)
                    nne = c1.number_input("E", 0, 5, barra['requerimientos']['enc'], key=f"edit_e_{i}")
                    nnba = c2.number_input("B", 0, 5, barra['requerimientos']['bar'], key=f"edit_b_{i}")
                    nnay = c3.number_input("A", 0, 5, barra['requerimientos']['ayu'], key=f"edit_a_{i}")
                    
                    df_edit_base = barra['matriz_competencias'][['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
                    df_edit_base = agregar_indice(df_edit_base)
                    
                    h_edit_mat = calc_altura(df_edit_base)
                    
                    me = st.data_editor(
                        df_edit_base,
                        column_config={
                            "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                            "Nombre": st.column_config.TextColumn("Nombre", width="small", disabled=True),
                            "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                            "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                            "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                        },
                        use_container_width=True, hide_index=True, height=h_edit_mat,
                        key=f"editor_mx_{i}"
                    )
                    if st.form_submit_button("Actualizar", use_container_width=True):
                        me_clean = me.drop('N°', axis=1)
                        st.session_state['db_eventos'][ev]['Barras'][i] = {'nombre': nnb, 'requerimientos': {'enc': nne, 'bar': nnba, 'ayu': nnay}, 'matriz_competencias': me_clean}
                        guardar_datos()
                        st.rerun()
                if st.button("Borrar Barra", key=f"del_b_{i}", use_container_width=True):
                    st.session_state['db_eventos'][ev]['Barras'].pop(i)
                    guardar_datos()
                    st.rerun()

# TAB 3: OPERACIÓN
with tab3:
    c1, c2 = st.columns(2)
    fec = c1.date_input("Fecha", date.today(), key="op_dt")
    evr = c2.selectbox("Evento Op.", lev, key="op_sl")
    
    if st.button("🚀 GENERAR ROTACIÓN", type="primary", key="op_go", use_container_width=True):
        if not st.session_state['db_eventos'][evr]['Barras']:
            st.error("Faltan barras.")
        else:
            p, b, u = ejecutar_algoritmo(evr)
            st.session_state['res'] = {'plan': p, 'banca': b, 'up': u, 'ev': evr, 'fecha': fec}
    
    if 'res' in st.session_state and st.session_state['res']['ev'] == evr:
        r = st.session_state['res']
        st.divider()
        edit_mode = st.toggle("✏️ Editar Asignación", key="op_tgl")
        banca_act = sorted(r['banca'])
        cols = st.columns(3)
        idx = 0
        for b_nom, eq in r['plan'].items():
            with cols[idx % 3]: 
                st.markdown(f"""<div class="plan-card"><div class="barra-header">{b_nom}</div>""", unsafe_allow_html=True)
                for i, m in enumerate(eq):
                    rol = m['Rol']
                    ic = m.get('Icon', '')
                    nm = m['Nombre']
                    if edit_mode:
                        ops = [nm] + banca_act
                        nnm = st.selectbox(f"{ic} {rol}", ops, index=0, key=f"s_{b_nom}_{i}", label_visibility="collapsed")
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
        if st.button("💾 CERRAR FECHA", type="primary", key="op_save", use_container_width=True):
            nu = {}
            for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE": nu[m['Nombre']] = b
            for n, b in nu.items(): st.session_state['db_historial_algoritmo'][r['ev']][n] = b
            log = {'Fecha': str(r['fecha']), 'Evento': r['ev'], 'Plan': r['plan'], 'Banca': list(r['banca'])}
            st.session_state['db_logs_visuales'].append(log)
            guardar_datos()
            st.success("Guardado.")

# TAB 4: HISTORIAL
with tab4:
    logs = st.session_state['db_logs_visuales']
    if logs:
        # Iteramos en reverso para ver lo último primero
        # Usamos enumerate para saber qué índice borrar en la lista original
        for i, log in enumerate(reversed(logs)):
            # Calculamos el índice real en la lista original
            real_index = len(logs) - 1 - i
            
            with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                c_del, c_cont = st.columns([1, 4])
                
                # BOTÓN DE ELIMINAR
                if c_del.button("🗑️ Eliminar", key=f"del_log_{real_index}", type="primary", use_container_width=True):
                    st.session_state['db_logs_visuales'].pop(real_index)
                    guardar_datos()
                    st.rerun()
                
                for b, eq in log['Plan'].items():
                    st.markdown(f"**{b}**")
                    for m in eq: st.text(f"{m.get('Icon','')} {m['Rol']}: {m['Nombre']}")
                    st.divider()
                st.caption(f"Banca: {', '.join(log['Banca'])}")
    else:
        st.info("No hay historial guardado.")
