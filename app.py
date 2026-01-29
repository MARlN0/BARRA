import streamlit as st
import pandas as pd
import random
from datetime import date
import io

# --- 1. CONFIGURACIÓN E INYECCIÓN DE CSS (ESTILO MÓVIL) ---
st.set_page_config(page_title="ERP Staff V10 Mobile", page_icon="📱", layout="wide")

st.markdown("""
    <style>
    /* AJUSTES CELULAR */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
            padding-left: 0.2rem !important;
            padding-right: 0.2rem !important;
        }
        /* Forzar que los textos de la tabla sean legibles */
        .stDataFrame { font-size: 14px; }
        
        /* Botones grandes para dedos */
        .stButton button {
            width: 100% !important;
            height: 3.5rem !important;
            font-weight: bold !important;
        }
    }

    /* ESTILOS GENERALES */
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); }
    
    /* TARJETAS DE PLAN */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        border: 1px solid rgba(200, 200, 200, 0.2);
        border-radius: 12px;
        padding: 12px;
        background-color: rgba(255, 255, 255, 0.03);
        margin-bottom: 10px;
    }

    .barra-header {
        font-size: 1.2rem;
        font-weight: 800;
        text-transform: uppercase;
        color: var(--text-color);
        border-bottom: 2px solid #FF4B4B;
        margin-bottom: 10px;
        padding-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .fila-rol {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    .rol-badge {
        font-size: 0.8rem;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 4px;
        background-color: rgba(128, 128, 128, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BASE DE DATOS ---
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
if 'db_historial_algoritmo' not in st.session_state:
    st.session_state['db_historial_algoritmo'] = {}
if 'db_logs_visuales' not in st.session_state:
    st.session_state['db_logs_visuales'] = []

# --- 3. FUNCIONES AUXILIARES ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    df = df.sort_values(by=['sort_key', 'Nombre'])
    return df.drop('sort_key', axis=1)

# --- 4. ALGORITMO ---
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
        candidatos = matriz[~matriz['Nombre'].isin(personal_asignado_hoy)].copy()

        # 1. ENCARGADOS
        for _ in range(reqs['enc']):
            posibles = candidatos[candidatos['Es_Encargado'] == True]
            validos = [row['Nombre'] for _, row in posibles.iterrows() if historial_evento.get(row['Nombre'], "") != nombre_b]
            if not validos and not posibles.empty: validos = posibles['Nombre'].tolist()
            
            if validos:
                elegido = random.choice(validos)
                equipo.append({'Rol': 'Encargado', 'Icon': '👑', 'Nombre': elegido})
                personal_asignado_hoy.add(elegido)
                nuevo_historial_temp[elegido] = nombre_b
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Encargado', 'Icon': '👑', 'Nombre': 'VACANTE'})

        # 2. BARTENDERS
        for _ in range(reqs['bar']):
            posibles = candidatos[candidatos['Es_Bartender'] == True]
            if not posibles.empty:
                elegido = random.choice(posibles['Nombre'].tolist())
                equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': elegido})
                personal_asignado_hoy.add(elegido)
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Bartender', 'Icon': '🍺', 'Nombre': 'VACANTE'})

        # 3. AYUDANTES
        for _ in range(reqs['ayu']):
            posibles = candidatos[candidatos['Es_Ayudante'] == True]
            if not posibles.empty:
                elegido = random.choice(posibles['Nombre'].tolist())
                equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': elegido})
                personal_asignado_hoy.add(elegido)
                candidatos = candidatos[candidatos['Nombre'] != elegido]
            else:
                equipo.append({'Rol': 'Ayudante', 'Icon': '🧊', 'Nombre': 'VACANTE'})
                
        asignacion[nombre_b] = equipo

    banca = [p for p in plantilla_evento if p not in personal_asignado_hoy]
    return asignacion, banca, nuevo_historial_temp

# --- 5. INTERFAZ GRÁFICA ---

st.title("🏭 ERP Staff V10 (Mobile)")

tab1, tab2, tab3, tab4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Historial"])

# --- TAB 1: RH ---
with tab1:
    with st.expander("➕ Alta / Baja de Personal"):
        c1, c2 = st.columns(2)
        new_name = c1.text_input("Nombre")
        new_role = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"])
        if st.button("Guardar Nuevo", use_container_width=True):
            if new_name:
                nuevo = pd.DataFrame({'Nombre': [new_name], 'Cargo_Default': [new_role]})
                st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                st.rerun()
                
        st.divider()
        df_delete = ordenar_staff(st.session_state['db_staff'])
        del_list = st.multiselect("Eliminar:", df_delete['Nombre'].tolist())
        if st.button("🚨 Eliminar", type="primary", use_container_width=True):
            if del_list:
                df = st.session_state['db_staff']
                st.session_state['db_staff'] = df[~df['Nombre'].isin(del_list)]
                st.rerun()

    st.subheader("Nómina")
    df_view = ordenar_staff(st.session_state['db_staff'])
    
    # Altura dinámica
    altura_tabla = (len(df_view) + 1) * 35 + 3
    
    st.dataframe(
        df_view, 
        use_container_width=True, 
        height=altura_tabla,
        hide_index=True # <--- ADIÓS NUMEROS 0,1,2
    )

# --- TAB 2: CONFIG ---
with tab2:
    with st.expander("🆕 Crear Evento", expanded=False):
        new_ev = st.text_input("Nombre Evento")
        if st.button("Crear Evento", use_container_width=True):
            if new_ev and new_ev not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][new_ev] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][new_ev] = {}
                st.rerun()

    lista_ev = list(st.session_state['db_eventos'].keys())
    if not lista_ev:
        st.info("Crea un evento arriba.")
        st.stop()
        
    ev_actual = st.selectbox("Evento:", lista_ev)
    datos = st.session_state['db_eventos'][ev_actual]
    
    # 1. PLANTILLA
    st.caption("1. Habilitar Personal")
    df_base = ordenar_staff(st.session_state['db_staff'])
    convocados_set = set(datos['Staff_Convocado'])
    df_base.insert(0, 'PERTENECE', df_base['Nombre'].apply(lambda x: x in convocados_set))
    
    with st.form("form_plantilla"):
        h_editor = (len(df_base) + 1) * 35 + 3
        df_editado = st.data_editor(
            df_base,
            column_config={
                "PERTENECE": st.column_config.CheckboxColumn("✅", width="small", default=False),
                "Nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
            },
            disabled=["Nombre", "Cargo_Default"],
            use_container_width=True,
            height=h_editor,
            hide_index=True # <--- CLAVE PARA MÓVIL
        )
        if st.form_submit_button("💾 Guardar Plantilla", use_container_width=True):
            lista = df_editado[df_editado['PERTENECE'] == True]['Nombre'].tolist()
            st.session_state['db_eventos'][ev_actual]['Staff_Convocado'] = lista
            st.rerun()
            
    # 2. BARRAS
    st.caption("2. Barras")
    lista_actualizada = st.session_state['db_eventos'][ev_actual]['Staff_Convocado']
    
    if lista_actualizada:
        with st.expander("➕ Añadir Barra Nueva"):
            with st.form("new_barra"):
                nom_b = st.text_input("Nombre")
                c1, c2, c3 = st.columns(3)
                n_e = c1.number_input("Enc", 0, 5, 1)
                n_b = c2.number_input("Bar", 0, 10, 1)
                n_a = c3.number_input("Ayu", 0, 10, 1)
                
                df_m = df_base[df_base['Nombre'].isin(lista_actualizada)].copy().drop('PERTENECE', axis=1)
                df_m['Es_Encargado'] = False
                df_m['Es_Bartender'] = df_m['Cargo_Default'] == 'BARTENDER'
                df_m['Es_Ayudante'] = df_m['Cargo_Default'] == 'AYUDANTE'
                
                h_matriz = (len(df_m) + 1) * 35 + 3
                
                # --- CONFIGURACIÓN DE COLUMNAS PARA MÓVIL ---
                matriz_out = st.data_editor(
                    df_m, 
                    column_config={
                        "Nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
                        # USAMOS ICONOS EN LUGAR DE TEXTO LARGO
                        "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                        "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                        "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                        "Cargo_Default": None # Ocultamos el cargo por defecto para ahorrar espacio
                    },
                    use_container_width=True, 
                    height=h_matriz,
                    hide_index=True # <--- ESTO ES VITAL
                )
                
                if st.form_submit_button("Crear Barra", use_container_width=True):
                    if nom_b:
                        nueva = {'nombre': nom_b, 'requerimientos': {'enc': n_e, 'bar': n_b, 'ayu': n_a}, 'matriz_competencias': matriz_out}
                        st.session_state['db_eventos'][ev_actual]['Barras'].append(nueva)
                        st.rerun()

        # LISTA DE BARRAS
        for i, barra in enumerate(datos['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"ed_{i}"):
                    nn = st.text_input("Nombre", barra['nombre'])
                    c1, c2, c3 = st.columns(3)
                    ne = c1.number_input("E", 0, 5, value=barra['requerimientos']['enc'])
                    nb = c2.number_input("B", 0, 5, value=barra['requerimientos']['bar'])
                    na = c3.number_input("A", 0, 5, value=barra['requerimientos']['ayu'])
                    
                    h_ed = (len(barra['matriz_competencias']) + 1) * 35 + 3
                    
                    # --- MISMA CONFIG PARA MÓVIL ---
                    me = st.data_editor(
                        barra['matriz_competencias'], 
                        column_config={
                            "Nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
                            "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                            "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                            "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small"),
                            "Cargo_Default": None 
                        },
                        use_container_width=True, 
                        height=h_ed,
                        hide_index=True
                    )
                    
                    if st.form_submit_button("Guardar Cambios", use_container_width=True):
                        st.session_state['db_eventos'][ev_actual]['Barras'][i] = {
                            'nombre': nn, 'requerimientos': {'enc': ne, 'bar': nb, 'ayu': na}, 'matriz_competencias': me
                        }
                        st.rerun()
                        
                if st.button("Borrar Barra", key=f"d{i}", use_container_width=True):
                    st.session_state['db_eventos'][ev_actual]['Barras'].pop(i)
                    st.rerun()

# --- TAB 3: OPERACIÓN ---
with tab3:
    c_f, c_e = st.columns(2)
    fecha = c_f.date_input("Fecha", date.today())
    ev_run = c_e.selectbox("Evento Op.", lista_ev)
    
    if st.button("🚀 GENERAR ROTACIÓN", type="primary", use_container_width=True):
        if not st.session_state['db_eventos'][ev_run]['Barras']:
            st.error("Sin barras.")
        else:
            plan, banca, updates = ejecutar_algoritmo(ev_run)
            st.session_state['res'] = {'plan': plan, 'banca': banca, 'up': updates, 'ev': ev_run, 'fecha': fecha}

    if 'res' in st.session_state and st.session_state['res']['ev'] == ev_run:
        r = st.session_state['res']
        st.divider()
        
        modo_edicion = st.toggle("Modo Edición Manual")
        banca_actual = sorted(r['banca']) 
        
        cols = st.columns(3)
        idx = 0
        
        for b_nom, equipo in r['plan'].items():
            with cols[idx % 3]:
                with st.container():
                    st.markdown(f"<div class='barra-header'>{b_nom}</div>", unsafe_allow_html=True)
                    
                    for i, miembro in enumerate(equipo):
                        rol = miembro['Rol']
                        icon = miembro.get('Icon', '')
                        nom = miembro['Nombre']
                        
                        if modo_edicion:
                            ops = [nom] + banca_actual
                            # En móvil, label collapsed ayuda a ahorrar espacio vertical
                            nuevo = st.selectbox(f"{icon} {rol}", ops, index=0, key=f"s_{b_nom}_{i}")
                            if nuevo != nom:
                                if nuevo != "VACANTE" and nuevo in r['banca']: r['banca'].remove(nuevo)
                                if nom != "VACANTE": r['banca'].append(nom)
                                r['plan'][b_nom][i]['Nombre'] = nuevo
                                st.rerun()
                        else:
                            color = "#FF4B4B" if nom == "VACANTE" else "inherit"
                            st.markdown(f"""
                            <div class='fila-rol'>
                                <div><span class='rol-badge'>{icon} {rol}</span></div>
                                <div style='font-weight: bold; color:{color}; text-align:right'>{nom}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
            idx += 1

        st.info(f"Banca: {', '.join(r['banca'])}")
        
        if st.button("💾 CERRAR FECHA", type="primary", use_container_width=True):
             nu = {}
             for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE": nu[m['Nombre']] = b
             for n, b in nu.items(): st.session_state['db_historial_algoritmo'][r['ev']][n] = b
             
             log = {'Fecha': str(r['fecha']), 'Evento': r['ev'], 'Plan': r['plan'], 'Banca': list(r['banca'])}
             st.session_state['db_logs_visuales'].append(log)
             st.success("Guardado.")

# --- TAB 4: HISTORIAL ---
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
    else:
        st.write("Sin historial.")
