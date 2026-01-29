import streamlit as st
import pandas as pd
import random
from datetime import date, datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Logístico Staff V8", page_icon="🏗️", layout="wide")

# --- ESTILOS CSS ADAPTATIVOS (Funciona en Negro y Blanco) ---
st.markdown("""
    <style>
    /* Ajustes generales */
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); }
    .stExpander { border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; }
    
    /* Títulos de las tarjetas de barras */
    .barra-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: var(--text-color);
        border-bottom: 2px solid #FF4B4B;
        margin-bottom: 10px;
        padding-bottom: 5px;
    }
    
    /* Roles resaltados */
    .rol-tag {
        font-weight: bold;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS (SESIÓN) ---
# Inicializamos todas las variables de memoria
if 'db_staff' not in st.session_state:
    st.session_state['db_staff'] = pd.DataFrame({
        'Nombre': ['Sebastian', 'Sandro', 'Vladimir', 'Kevin', 'Jhon', 'Forest', 
                   'Guillermo', 'Jair', 'Jordi', 'Pedro', 'Franklin', 'Luis', 
                   'Gabriel', 'Gerald', 'Marcelo', 'Leandro', 'Manuel', 'Kers'],
        'Cargo_Default': ['BARTENDER', 'BARTENDER', 'AYUDANTE', 'BARTENDER', 'AYUDANTE', 'BARTENDER',
                  'BARTENDER', 'BARTENDER', 'AYUDANTE', 'BARTENDER', 'AYUDANTE', 'AYUDANTE',
                  'AYUDANTE', 'BARTENDER', 'BARTENDER', 'BARTENDER', 'BARTENDER', 'BARTENDER']
    })

if 'db_eventos' not in st.session_state:
    st.session_state['db_eventos'] = {} 

# Historial para el algoritmo (Memoria de rotación)
if 'db_historial_algoritmo' not in st.session_state:
    st.session_state['db_historial_algoritmo'] = {}

# Historial Visual (Logs completos para ver después)
if 'db_logs_visuales' not in st.session_state:
    st.session_state['db_logs_visuales'] = []

# --- FUNCIÓN DE ORDENAMIENTO ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    df = df.sort_values(by=['sort_key', 'Nombre'])
    return df.drop('sort_key', axis=1)

# --- ALGORITMO ---
def ejecutar_algoritmo(nombre_evento):
    datos_evento = st.session_state['db_eventos'][nombre_evento]
    plantilla_evento = datos_evento['Staff_Convocado'] 
    historial_evento = st.session_state['db_historial_algoritmo'].get(nombre_evento, {})
    
    asignacion = {}
    personal_asignado_hoy = set()
    nuevo_historial_temp = {} 

    for barra in datos_evento['Barras']:
        nombre_b = barra['nombre']
        reqs = barra['requerimientos']
        matriz = barra['matriz_competencias']
        
        equipo = []
        
        # Filtramos matriz para gente disponible
        candidatos = matriz[~matriz['Nombre'].isin(personal_asignado_hoy)].copy()

        # 1. ENCARGADOS
        for _ in range(reqs['enc']):
            posibles = candidatos[candidatos['Es_Encargado'] == True]
            # Filtro Memoria (Rotación)
            validos = [row['Nombre'] for _, row in posibles.iterrows() 
                       if historial_evento.get(row['Nombre'], "") != nombre_b]
            
            # Si no hay válidos por memoria, relajamos la restricción (mejor repetir que dejar vacante)
            if not validos and not posibles.empty:
                validos = posibles['Nombre'].tolist()
            
            if validos:
                elegido = random.choice(validos)
                equipo.append({'Rol': 'Encargado 👑', 'Nombre': elegido, 'Tipo': 'ENCARGADO'})
                personal_asignado_hoy.add(elegido)
                nuevo_historial_temp[elegido] = nombre_b
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Encargado 👑', 'Nombre': 'VACANTE', 'Tipo': 'VACANTE'})

        # 2. BARTENDERS
        for _ in range(reqs['bar']):
            posibles = candidatos[candidatos['Es_Bartender'] == True]
            if not posibles.empty:
                elegido = random.choice(posibles['Nombre'].tolist())
                equipo.append({'Rol': 'Bartender 🍺', 'Nombre': elegido, 'Tipo': 'BARTENDER'})
                personal_asignado_hoy.add(elegido)
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Bartender 🍺', 'Nombre': 'VACANTE', 'Tipo': 'VACANTE'})

        # 3. AYUDANTES
        for _ in range(reqs['ayu']):
            posibles = candidatos[candidatos['Es_Ayudante'] == True]
            if not posibles.empty:
                elegido = random.choice(posibles['Nombre'].tolist())
                equipo.append({'Rol': 'Ayudante 🧊', 'Nombre': elegido, 'Tipo': 'AYUDANTE'})
                personal_asignado_hoy.add(elegido)
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Ayudante 🧊', 'Nombre': 'VACANTE', 'Tipo': 'VACANTE'})
                
        asignacion[nombre_b] = equipo

    banca = [p for p in plantilla_evento if p not in personal_asignado_hoy]
    return asignacion, banca, nuevo_historial_temp

# --- INTERFAZ GRÁFICA ---

st.title("🏭 ERP Logística Staff V8.0")

tab1, tab2, tab3, tab4 = st.tabs(["1. Personal (RH)", "2. Configuración Eventos", "3. Operación Diaria (Asignación)", "4. Historial"])

# --- TAB 1: GESTIÓN PERSONAL ---
with tab1:
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.subheader("Alta de Personal")
        with st.form("add_staff"):
            new_name = st.text_input("Nombre:")
            new_role = st.selectbox("Cargo:", ["BARTENDER", "AYUDANTE"])
            if st.form_submit_button("Guardar"):
                if new_name and new_name not in st.session_state['db_staff']['Nombre'].values:
                    nuevo = pd.DataFrame({'Nombre': [new_name], 'Cargo_Default': [new_role]})
                    st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                    st.success("Guardado.")
                    st.rerun()
        
        st.divider()
        st.subheader("Baja de Personal")
        with st.form("del_staff"):
            df_delete = ordenar_staff(st.session_state['db_staff'])
            delete_list = st.multiselect("Eliminar:", df_delete['Nombre'].tolist())
            if st.form_submit_button("🚨 ELIMINAR"):
                if delete_list:
                    df_actual = st.session_state['db_staff']
                    st.session_state['db_staff'] = df_actual[~df_actual['Nombre'].isin(delete_list)]
                    st.success("Eliminado.")
                    st.rerun()

    with col_der:
        st.subheader("Nómina Global")
        df_view = ordenar_staff(st.session_state['db_staff'])
        df_view.index = range(1, len(df_view) + 1)
        st.dataframe(df_view, use_container_width=True, height=500)

# --- TAB 2: CONFIGURACIÓN (PLANTILLA) ---
with tab2:
    col1, col2 = st.columns([1, 3])
    with col1:
        with st.form("create_event"):
            nuevo_ev = st.text_input("Crear Tipo de Evento:")
            if st.form_submit_button("Crear"):
                if nuevo_ev and nuevo_ev not in st.session_state['db_eventos']:
                    st.session_state['db_eventos'][nuevo_ev] = {'Staff_Convocado': [], 'Barras': []}
                    st.session_state['db_historial_algoritmo'][nuevo_ev] = {}
                    st.success("Creado.")
                    st.rerun()
    
    lista_ev = list(st.session_state['db_eventos'].keys())
    if not lista_ev:
        st.stop()
        
    ev_actual = st.selectbox("Configurando Evento:", lista_ev)
    datos = st.session_state['db_eventos'][ev_actual]
    
    st.divider()
    
    # 1. PLANTILLA
    st.markdown(f"#### 1. Plantilla Habilitada: {ev_actual}")
    df_base = ordenar_staff(st.session_state['db_staff'])
    convocados_set = set(datos['Staff_Convocado'])
    df_base.insert(0, 'PERTENECE', df_base['Nombre'].apply(lambda x: x in convocados_set))
    df_base.index = range(1, len(df_base) + 1)
    
    with st.form("form_plantilla"):
        df_editado = st.data_editor(
            df_base,
            column_config={"PERTENECE": st.column_config.CheckboxColumn("Habilitado", default=False)},
            disabled=["Nombre", "Cargo_Default"],
            use_container_width=True,
            height=300
        )
        if st.form_submit_button("💾 Actualizar Plantilla"):
            lista_final = df_editado[df_editado['PERTENECE'] == True]['Nombre'].tolist()
            st.session_state['db_eventos'][ev_actual]['Staff_Convocado'] = lista_final
            st.success("Plantilla actualizada.")
            st.rerun()
    
    # 2. BARRAS
    st.divider()
    st.markdown(f"#### 2. Gestión de Barras")
    
    with st.expander("➕ CREAR NUEVA BARRA"):
        with st.form("new_barra"):
            c1, c2, c3, c4 = st.columns(4)
            nom_b = c1.text_input("Nombre Barra")
            n_e = c2.number_input("Encargados", 0, 5, 1)
            n_b = c3.number_input("Bartenders", 0, 10, 1)
            n_a = c4.number_input("Ayudantes", 0, 10, 1)
            
            st.write("Matriz de Roles:")
            lista_actualizada = st.session_state['db_eventos'][ev_actual]['Staff_Convocado']
            df_matriz = df_base[df_base['Nombre'].isin(lista_actualizada)].copy().drop('PERTENECE', axis=1)
            df_matriz['Es_Encargado'] = False
            df_matriz['Es_Bartender'] = df_matriz['Cargo_Default'] == 'BARTENDER'
            df_matriz['Es_Ayudante'] = df_matriz['Cargo_Default'] == 'AYUDANTE'
            
            matriz_out = st.data_editor(df_matriz, disabled=["Nombre", "Cargo_Default"], use_container_width=True, height=200)
            
            if st.form_submit_button("Crear Barra"):
                if nom_b:
                    nueva = {
                        'nombre': nom_b,
                        'requerimientos': {'enc': n_e, 'bar': n_b, 'ayu': n_a},
                        'matriz_competencias': matriz_out
                    }
                    st.session_state['db_eventos'][ev_actual]['Barras'].append(nueva)
                    st.success("Barra creada.")
                    st.rerun()

    # EDITAR BARRAS
    if datos['Barras']:
        for i, barra in enumerate(datos['Barras']):
            with st.expander(f"✏️ Editar: {barra['nombre']}"):
                with st.form(f"edit_barra_{i}"):
                    new_name = st.text_input("Nombre", value=barra['nombre'])
                    c1, c2, c3 = st.columns(3)
                    n_e = c1.number_input("Enc", value=barra['requerimientos']['enc'])
                    n_b = c2.number_input("Bar", value=barra['requerimientos']['bar'])
                    n_a = c3.number_input("Ayu", value=barra['requerimientos']['ayu'])
                    
                    matriz_edit = st.data_editor(barra['matriz_competencias'], use_container_width=True, height=200)
                    
                    if st.form_submit_button("Guardar Cambios"):
                        st.session_state['db_eventos'][ev_actual]['Barras'][i] = {
                            'nombre': new_name, 'requerimientos': {'enc': n_e, 'bar': n_b, 'ayu': n_a}, 'matriz_competencias': matriz_edit
                        }
                        st.rerun()
                
                if st.button("🗑️ Borrar Barra", key=f"del_{i}"):
                     st.session_state['db_eventos'][ev_actual]['Barras'].pop(i)
                     st.rerun()

# --- TAB 3: OPERACIÓN DIARIA (ASIGNACIÓN + EDICIÓN MANUAL) ---
with tab3:
    st.header("Operación del Día")
    
    col_ctrl, col_info = st.columns([1, 2])
    with col_ctrl:
        fecha = st.date_input("Fecha:", date.today())
        ev_run = st.selectbox("Evento:", lista_ev, key="sel_run_op")
        
        if st.button("🎲 GENERAR ROTACIÓN AUTOMÁTICA", type="primary", use_container_width=True):
            if not st.session_state['db_eventos'][ev_run]['Barras']:
                st.error("Faltan barras.")
            else:
                plan, banca, updates = ejecutar_algoritmo(ev_run)
                st.session_state['res'] = {'plan': plan, 'banca': banca, 'up': updates, 'ev': ev_run, 'fecha': fecha}

    # VISUALIZACIÓN Y EDICIÓN
    if 'res' in st.session_state and st.session_state['res']['ev'] == ev_run:
        r = st.session_state['res']
        
        st.divider()
        c_tit, c_edit_switch = st.columns([3, 1])
        c_tit.markdown(f"### Plan: {r['ev']} - {r['fecha']}")
        
        # --- MODO EDICIÓN MANUAL ---
        modo_edicion = c_edit_switch.toggle("✏️ Activar Edición Manual")
        
        banca_actual = sorted(r['banca']) # Lista para selectbox
        
        cols = st.columns(3)
        idx = 0
        
        # Iteramos sobre el plan guardado
        for b_nom, equipo in r['plan'].items():
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"<div class='barra-title'>{b_nom}</div>", unsafe_allow_html=True)
                    
                    for i, miembro in enumerate(equipo):
                        # Colores adaptativos usando clases CSS o lógica simple
                        rol_txt = miembro['Rol']
                        nombre_actual = miembro['Nombre']
                        
                        if modo_edicion:
                            # --- MODO EDICIÓN: SELECTBOX ---
                            # Opciones: El actual + Toda la banca
                            opciones = [nombre_actual] + banca_actual
                            
                            # Selectbox único por posición
                            nuevo_nombre = st.selectbox(
                                f"{rol_txt}", 
                                options=opciones, 
                                index=0, 
                                key=f"sel_{b_nom}_{i}"
                            )
                            
                            # Lógica de Intercambio (Swap)
                            if nuevo_nombre != nombre_actual:
                                # 1. Sacar al nuevo de la banca
                                if nuevo_nombre != "VACANTE":
                                    if nuevo_nombre in r['banca']:
                                        r['banca'].remove(nuevo_nombre)
                                
                                # 2. Mandar al viejo a la banca (si no era vacante)
                                if nombre_actual != "VACANTE":
                                    r['banca'].append(nombre_actual)
                                
                                # 3. Actualizar el plan
                                r['plan'][b_nom][i]['Nombre'] = nuevo_nombre
                                
                                # 4. Forzar recarga para actualizar listas
                                st.rerun()
                                
                        else:
                            # --- MODO VISUALIZACIÓN ---
                            color_style = "color: #FF4B4B;" if nombre_actual == "VACANTE" else ""
                            st.markdown(f"""
                                <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                                    <span class='rol-tag'>{rol_txt}</span>
                                    <span style='font-weight: bold; {color_style}'>{nombre_actual}</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
            idx += 1

        # BARRA DE BANCA
        st.divider()
        st.markdown(f"#### 🛋️ Personal en Banca ({len(r['banca'])})")
        st.info(", ".join(sorted(r['banca'])))
        
        # GUARDAR
        st.divider()
        col_s1, col_s2 = st.columns([1, 4])
        if col_s1.button("💾 CERRAR Y GUARDAR FECHA"):
            # 1. Actualizamos memoria del algoritmo (Solo encargados)
            # Recalculamos quienes son encargados ahora (por si hubo cambios manuales)
            nuevos_updates = {}
            for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE":
                        nuevos_updates[m['Nombre']] = b
            
            # Guardamos en la memoria del algoritmo
            for n, b in nuevos_updates.items():
                st.session_state['db_historial_algoritmo'][r['ev']][n] = b
            
            # 2. Guardamos en el LOG VISUAL (Historial completo)
            log_entry = {
                'Fecha': str(r['fecha']),
                'Evento': r['ev'],
                'Plan': r['plan'], # Guardamos copia del diccionario
                'Banca': list(r['banca'])
            }
            st.session_state['db_logs_visuales'].append(log_entry)
            
            st.success("✅ Fecha cerrada correctamente. Puedes ver el detalle en la pestaña 'Historial'.")

# --- TAB 4: HISTORIAL VISUAL ---
with tab4:
    st.header("🗂️ Historial de Operaciones")
    
    logs = st.session_state['db_logs_visuales']
    
    if not logs:
        st.info("No hay fechas cerradas todavía.")
    else:
        # Filtros
        fechas_disponibles = sorted(list(set([l['Fecha'] for l in logs])), reverse=True)
        sel_fecha = st.selectbox("Filtrar por Fecha:", ["Todas"] + fechas_disponibles)
        
        # Mostrar Logs (Invertido para ver lo más reciente arriba)
        for log in reversed(logs):
            if sel_fecha == "Todas" or sel_fecha == log['Fecha']:
                with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                    st.caption("Distribución Guardada:")
                    
                    # Reconstruimos visualización compacta
                    cols_log = st.columns(3)
                    idx_log = 0
                    for b_nom, eq in log['Plan'].items():
                        with cols_log[idx_log % 3]:
                            st.markdown(f"**{b_nom}**")
                            for m in eq:
                                st.markdown(f"- {m['Rol']}: {m['Nombre']}")
                        idx_log += 1
                    
                    st.divider()
                    st.caption(f"Banca ese día: {', '.join(log['Banca'])}")