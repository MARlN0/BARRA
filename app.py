import streamlit as st
import pandas as pd
import random
from datetime import date
import json
import os

# --- 1. CONFIGURACIÓN E INYECCIÓN DE CSS (ESTILO COMPACTO) ---
st.set_page_config(page_title="ERP Staff V13 (Compact)", page_icon="📲", layout="wide")

st.markdown("""
    <style>
    /* --- OPTIMIZACIÓN MÓVIL EXTREMA --- */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 3rem !important;
            padding-left: 0.1rem !important;
            padding-right: 0.1rem !important;
        }
        
        /* HACER LA TABLA SÚPER COMPACTA */
        div[data-testid="stDataEditor"] table {
            font-size: 13px !important;
        }
        div[data-testid="stDataEditor"] th {
            padding: 2px !important; /* Cabecera pegada */
            font-size: 11px !important;
        }
        div[data-testid="stDataEditor"] td {
            padding-top: 0px !important;
            padding-bottom: 0px !important;
            padding-left: 2px !important;
            padding-right: 2px !important;
            height: 30px !important; /* Fila bajita */
        }
        
        /* Botones grandes */
        .stButton button {
            width: 100% !important;
            height: 3rem !important;
            border-radius: 8px !important;
        }
    }

    /* ESTILOS GENERALES */
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; }
    
    .plan-card {
        border: 1px solid rgba(200, 200, 200, 0.3);
        border-radius: 10px;
        padding: 8px;
        margin-bottom: 8px;
        background-color: rgba(100, 100, 100, 0.05);
    }
    
    .barra-header {
        font-size: 1.1rem;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--text-color);
        border-bottom: 2px solid #FF4B4B;
        margin-bottom: 5px;
        padding-bottom: 2px;
    }
    
    .fila-rol {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    .badge {
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
        background-color: rgba(128, 128, 128, 0.1);
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
st.title("🏭 ERP Staff V13")

tab1, tab2, tab3, tab4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

# TAB 1: RH
with tab1:
    with st.expander("➕ Alta / Baja"):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre")
        nr = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"])
        if st.button("Guardar"):
            if nn:
                nuevo = pd.DataFrame({'Nombre': [nn], 'Cargo_Default': [nr]})
                st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                guardar_datos()
                st.rerun()
        df_del = ordenar_staff(st.session_state['db_staff'])
        list_del = st.multiselect("Eliminar:", df_del['Nombre'].tolist())
        if st.button("🚨 Eliminar"):
            st.session_state['db_staff'] = st.session_state['db_staff'][~st.session_state['db_staff']['Nombre'].isin(list_del)]
            guardar_datos()
            st.rerun()

    st.caption("Nómina")
    df_v = ordenar_staff(st.session_state['db_staff'])
    # Tabla compacta
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=(len(df_v)+1)*35+3)

# TAB 2: CONFIG
with tab2:
    with st.expander("🆕 Evento"):
        ne = st.text_input("Nombre")
        if st.button("Crear"):
            if ne and ne not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][ne] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][ne] = {}
                guardar_datos()
                st.rerun()

    lev = list(st.session_state['db_eventos'].keys())
    if not lev: st.stop()
    ev = st.selectbox("Evento:", lev)
    dat = st.session_state['db_eventos'][ev]
    
    # 1. PLANTILLA
    st.markdown("##### 1. Plantilla")
    df_b = ordenar_staff(st.session_state['db_staff'])
    conv = set(dat['Staff_Convocado'])
    df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    
    with st.form("f_plantilla"):
        # CONFIGURACIÓN: Nombre primero
        df_editado = st.data_editor(
            df_b,
            column_config={
                "OK": st.column_config.CheckboxColumn("✅", width="small"),
                "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                "Cargo_Default": None # Ocultar cargo para ahorrar espacio
            },
            disabled=["Nombre"],
            use_container_width=True,
            hide_index=True, # ESENCIAL
            height=(len(df_b)+1)*35+3
        )
        if st.form_submit_button("💾 Guardar"):
            lista = df_editado[df_editado['OK']==True]['Nombre'].tolist()
            st.session_state['db_eventos'][ev]['Staff_Convocado'] = lista
            guardar_datos()
            st.rerun()

    # 2. BARRAS
    st.markdown("##### 2. Barras")
    lista_ok = dat['Staff_Convocado']
    
    if lista_ok:
        with st.expander("➕ Crear Barra"):
            with st.form("f_barra"):
                nb = st.text_input("Nombre")
                c1, c2, c3 = st.columns(3)
                ne = c1.number_input("Enc", 0, 5, 1)
                nba = c2.number_input("Bar", 0, 5, 1)
                nay = c3.number_input("Ayu", 0, 5, 1)
                
                df_m = df_b[df_b['Nombre'].isin(lista_ok)].copy().drop('OK', axis=1)
                df_m['Es_Encargado'] = False
                df_m['Es_Bartender'] = df_m['Cargo_Default'] == 'BARTENDER'
                df_m['Es_Ayudante'] = df_m['Cargo_Default'] == 'AYUDANTE'
                
                # REORDENAR COLUMNAS EXPLÍCITAMENTE
                df_m = df_m[['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
                
                mo = st.data_editor(
                    df_m,
                    column_config={
                        "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                        "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                        "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                        "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=(len(df_m)+1)*35+3
                )
                if st.form_submit_button("Guardar"):
                    if nb:
                        nueva = {'nombre': nb, 'requerimientos': {'enc': ne, 'bar': nba, 'ayu': nay}, 'matriz_competencias': mo}
                        st.session_state['db_eventos'][ev]['Barras'].append(nueva)
                        guardar_datos()
                        st.rerun()

        for i, barra in enumerate(dat['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"ed_{i}"):
                    nnb = st.text_input("Nombre", barra['nombre'])
                    c1, c2, c3 = st.columns(3)
                    nne = c1.number_input("E", 0, 5, barra['requerimientos']['enc'])
                    nnba = c2.number_input("B", 0, 5, barra['requerimientos']['bar'])
                    nnay = c3.number_input("A", 0, 5, barra['requerimientos']['ayu'])
                    
                    # REORDENAR AL EDITAR TAMBIÉN
                    df_edit = barra['matriz_competencias'][['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
                    
                    me = st.data_editor(
                        df_edit,
                        column_config={
                            "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                            "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                            "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                            "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                        },
                        use_container_width=True, hide_index=True, height=(len(df_edit)+1)*35+3
                    )
                    if st.form_submit_button("Actualizar"):
                        st.session_state['db_eventos'][ev]['Barras'][i] = {'nombre': nnb, 'requerimientos': {'enc': nne, 'bar': nnba, 'ayu': nnay}, 'matriz_competencias': me}
                        guardar_datos()
                        st.rerun()
                if st.button("Borrar", key=f"d{i}"):
                    st.session_state['db_eventos'][ev]['Barras'].pop(i)
                    guardar_datos()
                    st.rerun()

# TAB 3: OPERACIÓN
with tab3:
    c1, c2 = st.columns(2)
    fec = c1.date_input("Fecha", date.today())
    evr = c2.selectbox("Evento Op.", lev)
    
    if st.button("🚀 GENERAR ROTACIÓN", type="primary"):
        if not st.session_state['db_eventos'][evr]['Barras']:
            st.error("Faltan barras.")
        else:
            p, b, u = ejecutar_algoritmo(evr)
            st.session_state['res'] = {'plan': p, 'banca': b, 'up': u, 'ev': evr, 'fecha': fec}
    
    if 'res' in st.session_state and st.session_state['res']['ev'] == evr:
        r = st.session_state['res']
        st.divider()
        edit_mode = st.toggle("✏️ Editar")
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
        if st.button("💾 CERRAR FECHA", type="primary"):
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
        for log in reversed(logs):
            with st.expander(f"{log['Fecha']} - {log['Evento']}"):
                for b, eq in log['Plan'].items():
                    st.markdown(f"**{b}**")
                    for m in eq: st.text(f"{m.get('Icon','')} {m['Rol']}: {m['Nombre']}")
                    st.divider()
                st.caption(f"Banca: {', '.join(log['Banca'])}")
