import streamlit as st
import pandas as pd
import random
from datetime import datetime, date
import json
import os
import base64
from PIL import Image, ImageDraw, ImageFont
import io

# --- 0. VALIDACIÓN DE LIBRERÍAS ---
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Falta FPDF. Por favor crea el archivo requirements.txt en GitHub con: fpdf")
    FPDF = None

# --- 1. CONFIGURACIÓN VISUAL (ESTILO APP NATIVA) ---
st.set_page_config(page_title="Barra Staff Pro V34", page_icon="🍸", layout="wide")

st.markdown("""
    <style>
    /* Ocultar elementos de sistema */
    [data-testid="stElementToolbar"] { display: none !important; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem !important; }

    /* ESTILOS MÓVILES */
    @media (max-width: 768px) {
        .block-container { padding-bottom: 6rem !important; padding-left: 0.2rem; padding-right: 0.2rem; }
        
        /* Tablas compactas */
        div[data-testid="stDataEditor"] table { font-size: 12px !important; }
        div[data-testid="stDataEditor"] th { padding: 2px !important; text-align: center !important; }
        div[data-testid="stDataEditor"] td { padding: 0px !important; }
        
        /* Altura fila */
        div[data-testid="stDataEditor"] div[role="gridcell"] { min-height: 35px !important; height: 35px !important; align-items: center; }
        
        /* Botones táctiles grandes */
        .stButton button { 
            width: 100% !important; 
            height: 3.5rem !important; 
            border-radius: 10px !important; 
            font-weight: 700 !important; 
            background-color: #FF4B4B; 
            color: white; 
            border: none; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }
    }

    /* DISEÑO DE TARJETAS DE RESULTADO */
    .plan-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .barra-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #FFF;
        border-bottom: 2px solid #FF4B4B;
        padding-bottom: 5px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .row-person {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid #333;
    }
    .role-badge {
        background-color: #333;
        color: #DDD;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .name-text { font-weight: bold; font-size: 0.95rem; }
    .ghost-text { font-size: 0.7rem; color: #888; font-style: italic; display: block; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DE LOGIN ---
def check_login():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center'>🔐 Acceso QiuClub</h3>", unsafe_allow_html=True)
                u = st.text_input("Usuario")
                p = st.text_input("Contraseña", type="password")
                if st.button("Ingresar", type="primary", use_container_width=True):
                    if u == "qiuclub" and p == "barra2026":
                        st.session_state.logged_in = True
                        st.rerun()
                    else: st.error("Acceso Denegado")
        return False
    return True

if not check_login(): st.stop()

# --- 3. GESTIÓN DE DATOS (JSON) ---
DB_FILE = "base_datos_staff.json"

def clean_str(s):
    """Limpia espacios invisibles que causan errores de duplicados"""
    return str(s).strip() if s else ""

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                # Reconstruir DataFrames
                df_staff = pd.DataFrame(data['staff'])
                eventos = data['eventos']
                for ev in eventos.values():
                    for b in ev['Barras']:
                        b['matriz_competencias'] = pd.DataFrame(b['matriz_competencias'])
                return df_staff, eventos, data.get('historial', {}), data.get('logs', [])
        except Exception: pass
    
    # Datos por defecto si es la primera vez
    return pd.DataFrame({'Nombre': ['Ejemplo'], 'Cargo_Default': ['BARTENDER']}), {}, {}, []

def save_data():
    # Convertir DataFrames a dicts para JSON
    staff_list = st.session_state.db_staff.to_dict(orient='records')
    ev_dict = {}
    for k, v in st.session_state.db_eventos.items():
        barras_clean = []
        for b in v['Barras']:
            bc = b.copy()
            bc['matriz_competencias'] = b['matriz_competencias'].to_dict(orient='records')
            barras_clean.append(bc)
        ev_dict[k] = {'Staff_Convocado': v['Staff_Convocado'], 'Barras': barras_clean}
    
    payload = {
        'staff': staff_list,
        'eventos': ev_dict,
        'historial': st.session_state.db_historial,
        'logs': st.session_state.db_logs
    }
    with open(DB_FILE, 'w') as f: json.dump(payload, f, indent=4)

# Inicializar Estado
if 'db_staff' not in st.session_state:
    s, e, h, l = load_data()
    st.session_state.db_staff = s
    st.session_state.db_eventos = e
    st.session_state.db_historial = h
    st.session_state.db_logs = l

# --- 4. ALGORITMO DE ASIGNACIÓN (CORE) ---
def run_allocation(event_name):
    event_data = st.session_state.db_eventos[event_name]
    # Historial estricto: {NombrePersona: NombreBarraDondeEstuvo}
    history_map = st.session_state.db_historial.get(event_name, {})
    
    # Personas habilitadas hoy (Plantilla)
    active_staff = set(event_data['Staff_Convocado'])
    
    allocation = {}
    assigned_people = set()
    
    for barra in event_data['Barras']:
        bar_name = barra['nombre']
        reqs = barra['requerimientos']
        matrix = barra['matriz_competencias']
        
        # Filtro 1: Solo gente habilitada en la plantilla de HOY
        # Filtro 2: Solo gente que no haya sido asignada ya en esta ronda
        # Filtro 3 (Matrix): Que tenga el check del rol
        
        team = []
        
        # Sub-función de sorteo estricto
        def pick_role(role_label, role_icon, col_check):
            # Candidatos base: Tienen el check Y están habilitados Y no están asignados hoy
            candidates = matrix[
                (matrix[col_check] == True) & 
                (matrix['Nombre'].isin(active_staff)) & 
                (~matrix['Nombre'].isin(assigned_people))
            ]
            
            valid_candidates = []
            
            # FILTRO DE ORO: NO REPETIR BARRA
            for _, row in candidates.iterrows():
                person = row['Nombre']
                last_bar = history_map.get(person, "")
                
                # Si la barra pasada es igual a la actual, DESCARTADO.
                if clean_str(last_bar) == clean_str(bar_name):
                    continue 
                
                valid_candidates.append(person)
            
            if valid_candidates:
                chosen = random.choice(valid_candidates)
                assigned_people.add(chosen)
                team.append({'Rol': role_label, 'Icon': role_icon, 'Nombre': chosen, 'IsSupport': False})
                return True
            else:
                # Nadie cumple los requisitos -> VACANTE
                team.append({'Rol': role_label, 'Icon': role_icon, 'Nombre': 'VACANTE', 'IsSupport': False})
                return False

        # Ejecutar por jerarquía
        for _ in range(reqs['enc']): pick_role('Encargado', '👑', 'Es_Encargado')
        for _ in range(reqs['bar']): pick_role('Bartender', '🍺', 'Es_Bartender')
        for _ in range(reqs['ayu']): pick_role('Ayudante', '🧊', 'Es_Ayudante')
        
        allocation[bar_name] = team

    # Calcular Banca
    banca = [p for p in event_data['Staff_Convocado'] if p not in assigned_people]
    return allocation, banca

# --- 5. EXPORTACIÓN (PDF & IMAGEN) ---
def get_pdf_bytes(evento, fecha, plan):
    if not FPDF: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"EVENTO: {evento} | {fecha}", 0, 1, 'L')
    pdf.ln(5)
    
    # Layout Grid
    col_w = 90
    x_left = 10
    x_right = 110
    
    # Ordenar barras por tamaño (Estética)
    sorted_bars = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
    
    pdf.set_text_color(0,0,0) # Siempre negro
    
    for i in range(0, len(sorted_bars), 2):
        if pdf.get_y() > 250: pdf.add_page()
        y_start = pdf.get_y()
        
        # Izquierda
        b1, eq1 = sorted_bars[i]
        pdf.set_xy(x_left, y_start)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(col_w, 8, b1, 1, 1, 'L', fill=True)
        pdf.set_font("Arial", "", 10)
        for m in eq1:
            r_cl = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apoyo")
            pdf.set_x(x_left)
            pdf.cell(30, 7, r_cl, 1)
            pdf.cell(60, 7, m['Nombre'], 1, 1)
            
        h1 = pdf.get_y() - y_start
        
        # Derecha
        h2 = 0
        if i+1 < len(sorted_bars):
            b2, eq2 = sorted_bars[i+1]
            pdf.set_xy(x_right, y_start)
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(col_w, 8, b2, 1, 1, 'L', fill=True)
            pdf.set_font("Arial", "", 10)
            for m in eq2:
                r_cl = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apoyo")
                pdf.set_x(x_right)
                pdf.cell(30, 7, r_cl, 1)
                pdf.cell(60, 7, m['Nombre'], 1, 1)
            h2 = pdf.get_y() - y_start
            
        pdf.set_y(y_start + max(h1, h2) + 5)
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

def get_img_bytes(evento, fecha, plan):
    # Config básica
    W, P = 800, 20
    # Fuentes seguras
    try: font_t = ImageFont.truetype("arialbd.ttf", 24)
    except: font_t = ImageFont.load_default()
    try: font_b = ImageFont.truetype("arialbd.ttf", 14)
    except: font_b = ImageFont.load_default()
    try: font_r = ImageFont.truetype("arial.ttf", 14)
    except: font_r = ImageFont.load_default()
    
    sorted_bars = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Calcular altura
    curr_y = 80
    row_h = 30
    head_h = 35
    for i in range(0, len(sorted_bars), 2):
        h_l = head_h + len(sorted_bars[i][1])*row_h
        h_r = head_h + len(sorted_bars[i+1][1])*row_h if i+1 < len(sorted_bars) else 0
        curr_y += max(h_l, h_r) + P
        
    img = Image.new('RGB', (W, curr_y), 'white')
    draw = ImageDraw.Draw(img)
    
    # Header
    draw.text((P, 20), f"{evento} | {fecha}", fill="black", font=font_t)
    draw.line((P, 60, W-P, 60), fill="black", width=3)
    
    # Dibujar
    curr_y = 80
    col_w = (W - 3*P) // 2
    
    for i in range(0, len(sorted_bars), 2):
        max_h_row = 0
        
        # Func dibuja columna
        def draw_col(x, bar, team):
            draw.rectangle([x, curr_y, x+col_w, curr_y+head_h], fill="#DDD", outline="black")
            draw.text((x+5, curr_y+8), bar, fill="black", font=font_b)
            cy = curr_y + head_h
            for m in team:
                rol = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apoyo")
                draw.rectangle([x, cy, x+80, cy+row_h], outline="#999")
                draw.text((x+5, cy+5), rol, fill="black", font=font_r)
                draw.rectangle([x+80, cy, x+col_w, cy+row_h], outline="#999")
                # Nombre en negro salvo vacante
                c = "red" if m['Nombre']=="VACANTE" else "black"
                draw.text((x+85, cy+5), m['Nombre'], fill=c, font=font_b)
                cy += row_h
            return cy - curr_y

        h1 = draw_col(P, sorted_bars[i][0], sorted_bars[i][1])
        max_h_row = h1
        
        if i+1 < len(sorted_bars):
            h2 = draw_col(P+col_w+P, sorted_bars[i+1][0], sorted_bars[i+1][1])
            max_h_row = max(h1, h2)
            
        curr_y += max_h_row + P
        
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# --- 6. INTERFAZ ---
st.title("🍸 Barra Staff V34")

t1, t2, t3, t4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

# --- TAB RH ---
with t1:
    with st.expander("➕ Alta Personal", expanded=True):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="n_rh")
        nr = c2.selectbox("Rol Principal", ["BARTENDER", "AYUDANTE"], key="r_rh")
        if st.button("Guardar", use_container_width=True):
            if nn:
                clean_n = clean_str(nn)
                if clean_n in st.session_state.db_staff['Nombre'].values:
                    st.error("Nombre duplicado")
                else:
                    new_row = pd.DataFrame({'Nombre':[clean_n], 'Cargo_Default':[nr]})
                    st.session_state.db_staff = pd.concat([st.session_state.db_staff, new_row], ignore_index=True)
                    save_data()
                    st.success("Guardado")
                    st.rerun()
                    
    st.markdown("---")
    # Tabla RH
    df_rh = st.session_state.db_staff.copy()
    df_rh.insert(0, "N°", range(1, len(df_rh)+1))
    
    # Borrar
    to_del = st.multiselect("Eliminar:", df_rh['Nombre'].tolist())
    if st.button("🗑️ Borrar Seleccionados"):
        st.session_state.db_staff = st.session_state.db_staff[~st.session_state.db_staff['Nombre'].isin(to_del)]
        save_data()
        st.rerun()
        
    st.dataframe(df_rh, use_container_width=True, hide_index=True)

# --- TAB CONFIG ---
with t2:
    # Crear Evento
    c1, c2 = st.columns([3, 1])
    new_ev = c1.text_input("Nuevo Evento", placeholder="Ej: Boda Juan y Maria")
    if c2.button("Crear Evento", use_container_width=True):
        if new_ev and new_ev not in st.session_state.db_eventos:
            st.session_state.db_eventos[new_ev] = {'Staff_Convocado': [], 'Barras': []}
            save_data()
            st.rerun()
    
    # Seleccionar Evento
    eventos = list(st.session_state.db_eventos.keys())
    if not eventos: st.stop()
    curr_ev = st.selectbox("Evento Activo:", eventos)
    ev_data = st.session_state.db_eventos[curr_ev]
    
    if st.button("🗑️ Eliminar este evento"):
        del st.session_state.db_eventos[curr_ev]
        save_data()
        st.rerun()
        
    st.markdown("---")
    st.write("#### 1. Plantilla (Quiénes trabajan)")
    
    # Preparar DF Plantilla
    df_global = st.session_state.db_staff.copy()
    df_global['Habilitado'] = df_global['Nombre'].isin(ev_data['Staff_Convocado'])
    df_global = df_global[['Habilitado', 'Nombre', 'Cargo_Default']] # Orden
    
    # Editor Plantilla
    edited_plantilla = st.data_editor(
        df_global,
        column_config={
            "Habilitado": st.column_config.CheckboxColumn("✅", width="small"),
            "Nombre": st.column_config.TextColumn("Nombre", width="large", disabled=True),
            "Cargo_Default": st.column_config.TextColumn("Rol", width="small", disabled=True)
        },
        use_container_width=True,
        hide_index=True,
        height=(len(df_global)*35)+38
    )
    
    if st.button("💾 Guardar Plantilla"):
        selected = edited_plantilla[edited_plantilla['Habilitado']==True]['Nombre'].tolist()
        st.session_state.db_eventos[curr_ev]['Staff_Convocado'] = selected
        save_data()
        st.success("Plantilla actualizada")
        
    st.markdown("---")
    st.write("#### 2. Barras")
    
    # Crear Barra
    with st.expander("Añadir Barra"):
        bn = st.text_input("Nombre Barra")
        c1, c2, c3 = st.columns(3)
        ne = c1.number_input("Encargados", 0, 5, 1)
        nb = c2.number_input("Bartenders", 0, 5, 1)
        na = c3.number_input("Ayudantes", 0, 5, 1)
        
        # Matriz vacía basada en plantilla
        plantilla_actual = st.session_state.db_eventos[curr_ev]['Staff_Convocado']
        if not plantilla_actual:
            st.warning("Primero define la plantilla arriba.")
        else:
            df_m = st.session_state.db_staff[st.session_state.db_staff['Nombre'].isin(plantilla_actual)].copy()
            df_m['Es_Encargado'] = False
            df_m['Es_Bartender'] = df_m['Cargo_Default'] == 'BARTENDER'
            df_m['Es_Ayudante'] = df_m['Cargo_Default'] == 'AYUDANTE'
            df_m = df_m[['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']] # Sin Rol aqui
            
            edited_m = st.data_editor(df_m, use_container_width=True, hide_index=True)
            
            if st.button("Guardar Barra"):
                new_bar = {
                    'nombre': bn,
                    'requerimientos': {'enc': ne, 'bar': nb, 'ayu': na},
                    'matriz_competencias': edited_m.to_dict(orient='records')
                }
                st.session_state.db_eventos[curr_ev]['Barras'].append(new_bar)
                save_data()
                st.rerun()

    # Listar Barras
    for i, barra in enumerate(ev_data['Barras']):
        with st.expander(f"✏️ {barra['nombre']}"):
            if st.button("Borrar Barra", key=f"del_{i}"):
                st.session_state.db_eventos[curr_ev]['Barras'].pop(i)
                save_data()
                st.rerun()
                
            # Edición simple
            df_curr = pd.DataFrame(barra['matriz_competencias'])
            # Sincronizar con plantilla actual (Si agregaste gente nueva a la plantilla, que aparezca aqui)
            df_plantilla = st.session_state.db_staff[st.session_state.db_staff['Nombre'].isin(ev_data['Staff_Convocado'])]
            
            # Merge inteligente
            df_merged = pd.merge(df_plantilla[['Nombre', 'Cargo_Default']], df_curr, on='Nombre', how='left')
            df_merged['Es_Encargado'] = df_merged['Es_Encargado'].fillna(False)
            df_merged['Es_Bartender'] = df_merged['Es_Bartender'].fillna(df_merged['Cargo_Default']=='BARTENDER')
            df_merged['Es_Ayudante'] = df_merged['Es_Ayudante'].fillna(df_merged['Cargo_Default']=='AYUDANTE')
            
            final_df = df_merged[['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
            
            edited_bar = st.data_editor(final_df, key=f"ed_{i}", use_container_width=True, hide_index=True)
            
            if st.button("Actualizar Matriz", key=f"btn_{i}"):
                st.session_state.db_eventos[curr_ev]['Barras'][i]['matriz_competencias'] = edited_bar.to_dict(orient='records')
                save_data()
                st.success("Guardado")

# --- TAB OPERACIÓN ---
with t3:
    c1, c2 = st.columns(2)
    op_date = c1.date_input("Fecha")
    op_ev = c2.selectbox("Seleccionar Evento", eventos, key="op_ev")
    
    if st.button("🚀 GENERAR / RE-GENERAR", type="primary", use_container_width=True):
        plan, banca = run_allocation(op_ev)
        st.session_state.temp_res = {'plan': plan, 'banca': banca, 'ev': op_ev, 'fecha': op_date}
    
    if 'temp_res' in st.session_state and st.session_state.temp_res['ev'] == op_ev:
        res = st.session_state.temp_res
        
        # Botones Export
        c_pdf, c_img = st.columns(2)
        pdf_b = get_pdf_bytes(res['ev'], str(res['fecha']), res['plan'])
        if pdf_b: c_pdf.download_button("📄 PDF (Limpio)", pdf_b, "plan.pdf", "application/pdf", use_container_width=True)
        
        img_b = get_img_bytes(res['ev'], str(res['fecha']), res['plan'])
        c_img.download_button("📷 IMG (Limpio)", img_b, "plan.png", "image/png", use_container_width=True)
        
        # Banca Alerta
        if res['banca']:
            st.warning(f"⚠️ **BANCA ({len(res['banca'])}):** {', '.join(res['banca'])}")
        else:
            st.success("✅ Todo el personal asignado.")
            
        # Apoyo Manual
        with st.expander("➕ Agregar Apoyo Manual"):
            all_staff = sorted(st.session_state.db_staff['Nombre'].unique())
            col_b, col_p = st.columns(2)
            dest_bar = col_b.selectbox("A Barra:", list(res['plan'].keys()))
            pers_add = col_p.selectbox("Persona:", all_staff)
            if st.button("Agregar"):
                st.session_state.temp_res['plan'][dest_bar].append(
                    {'Rol': 'Apoyo', 'Icon': '⚡', 'Nombre': pers_add, 'IsSupport': True}
                )
                if pers_add in st.session_state.temp_res['banca']:
                    st.session_state.temp_res['banca'].remove(pers_add)
                st.rerun()

        st.divider()
        
        # Obtener historial previo para Ghost Text
        prev_map = st.session_state.db_historial.get(op_ev, {})
        
        # Renderizado de Tarjetas
        edit_mode = st.toggle("✏️ Modo Edición")
        
        cols = st.columns(3)
        idx = 0
        
        for bar_name, team in res['plan'].items():
            with cols[idx % 3]:
                st.markdown(f"""
                <div class="plan-card">
                    <div class="barra-title">{bar_name}</div>
                """, unsafe_allow_html=True)
                
                for i, member in enumerate(team):
                    # Ghost Logic
                    p_name = member['Nombre']
                    prev_bar = prev_map.get(p_name, None)
                    ghost_str = ""
                    if prev_bar:
                        # Solo mostramos si estuvo en ESTA barra antes
                        if clean_str(prev_bar) == clean_str(bar_name):
                            ghost_str = f"(Repite: {prev_bar})"
                        else:
                            ghost_str = f"(Viene de: {prev_bar})"
                    
                    if edit_mode and not member.get('IsSupport'):
                        # Selectbox para cambiar
                        opts = [p_name] + sorted(res['banca'])
                        new_p = st.selectbox(f"{member['Icon']} {member['Rol']}", opts, key=f"s_{bar_name}_{i}")
                        if new_p != p_name:
                            # Logica intercambio banca
                            if p_name != "VACANTE": res['banca'].append(p_name)
                            if new_p != "VACANTE" and new_p in res['banca']: res['banca'].remove(new_p)
                            member['Nombre'] = new_p
                            st.rerun()
                    else:
                        # Render lectura
                        color = "#FF4B4B" if p_name == "VACANTE" else "#FFF"
                        if member.get('IsSupport'): color = "#FFA500"
                        
                        st.markdown(f"""
                        <div class="row-person">
                            <div class="role-badge">{member['Icon']} {member['Rol']}</div>
                            <div style="text-align:right">
                                <div class="name-text" style="color:{color}">{p_name}</div>
                                <div class="ghost-text">{ghost_str}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1
            
        if st.button("💾 CERRAR FECHA Y GUARDAR HISTORIAL", type="primary", use_container_width=True):
            # Guardar en logs visuales
            log_entry = {
                'Fecha': str(res['fecha']),
                'Evento': res['ev'],
                'Plan': res['plan'],
                'Banca': res['banca']
            }
            st.session_state.db_logs.append(log_entry)
            
            # GUARDAR HISTORIAL TECNICO (Sobrescribir mapa para evitar repeticiones futuras)
            new_history_map = {}
            for bar, team in res['plan'].items():
                for m in team:
                    if m['Nombre'] != "VACANTE" and not m.get('IsSupport'):
                        new_history_map[m['Nombre']] = bar
            
            st.session_state.db_historial[res['ev']] = new_history_map
            
            save_data()
            st.success("¡Guardado y Historial Actualizado!")

# --- TAB HISTORIAL ---
with t4:
    if not st.session_state.db_logs:
        st.info("No hay historial.")
    else:
        for i, log in enumerate(reversed(st.session_state.db_logs)):
            real_idx = len(st.session_state.db_logs) - 1 - i
            with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("🗑️ Eliminar", key=f"dh_{real_idx}"):
                    st.session_state.db_logs.pop(real_idx)
                    save_data()
                    st.rerun()
                
                # Re-imprimir
                pdf_h = get_pdf_bytes(log['Evento'], log['Fecha'], log['Plan'])
                if pdf_h: c2.download_button("📄 PDF", pdf_h, "h.pdf", "application/pdf", key=f"ph_{real_idx}")
                
                img_h = get_img_bytes(log['Evento'], log['Fecha'], log['Plan'])
                c3.download_button("📷 IMG", img_h, "h.png", "image/png", key=f"ih_{real_idx}")
                
                # Vista rápida
                for b, t in log['Plan'].items():
                    st.markdown(f"**{b}**")
                    for m in t:
                        st.caption(f"{m['Icon']} {m['Nombre']}")
