import streamlit as st
import pandas as pd
import random
from datetime import date
import json
import os
import base64

# Validación de librería PDF
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Error Crítico: FPDF no instalado. Crea el archivo requirements.txt en GitHub.")
    FPDF = None

# --- 1. CONFIGURACIÓN VISUAL (ESTILO FINAL) ---
st.set_page_config(page_title="Barra Staff Pro V23", page_icon="🍸", layout="wide")

st.markdown("""
    <style>
    /* OCULTAR ELEMENTOS QUE MOLESTAN */
    [data-testid="stElementToolbar"] { display: none !important; visibility: hidden !important; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem !important; }

    /* OPTIMIZACIÓN CELULAR */
    @media (max-width: 768px) {
        .block-container { 
            padding-bottom: 5rem !important; 
            padding-left: 0.2rem !important; 
            padding-right: 0.2rem !important; 
        }
        /* TABLAS COMPACTAS Y LEGIBLES */
        div[data-testid="stDataEditor"] table { font-size: 13px !important; }
        div[data-testid="stDataEditor"] th { font-size: 11px !important; padding: 2px !important; text-align: center !important; }
        div[data-testid="stDataEditor"] td { padding: 0px 2px !important; line-height: 1.2 !important; }
        
        /* FILAS ALTAS PARA QUE NO HAYA SCROLL INTERNO */
        div[data-testid="stDataEditor"] div[role="gridcell"] { 
            min-height: 40px !important; 
            height: 40px !important; 
            display: flex; 
            align-items: center; 
        }
        
        /* BOTONES GRANDES */
        .stButton button { 
            width: 100% !important; 
            height: 3.5rem !important; 
            border-radius: 8px !important; 
            font-weight: bold !important; 
            background-color: #FF4B4B; 
            color: white; 
            border: none;
        }
    }

    /* ESTILOS DE TARJETAS */
    .plan-card {
        border: 1px solid rgba(200, 200, 200, 0.3); border-radius: 12px; 
        padding: 10px; margin-bottom: 8px; background-color: rgba(128, 128, 128, 0.05);
    }
    .barra-header {
        font-size: 1rem; font-weight: 800; text-transform: uppercase; 
        color: var(--text-color); border-bottom: 3px solid #FF4B4B; margin-bottom: 5px;
    }
    .fila-rol {
        display: flex; justify-content: space-between; align-items: center; 
        padding: 4px 0; border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    .badge { 
        padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; 
        font-weight: bold; background-color: rgba(128, 128, 128, 0.15); 
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN ---
def check_password():
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
    if not st.session_state['logged_in']:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='text-align: center;'>🔐 Acceso QiuClub</h3>", unsafe_allow_html=True)
                user = st.text_input("Usuario", key="login_user")
                password = st.text_input("Contraseña", type="password", key="login_pass")
                if st.button("Ingresar", type="primary", use_container_width=True):
                    if user == "qiuclub" and password == "barra2026":
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else: st.error("Incorrecto")
        return False
    return True

if not check_password(): st.stop()

# --- 3. MOTOR PDF INTELIGENTE (ORDENADO POR TAMAÑO) ---
if FPDF:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'REPORTE OPERATIVO - BARRA STAFF', 0, 1, 'C')
            self.ln(5)
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Pag {self.page_no()}', 0, 0, 'C')

    def generar_pdf(evento, fecha, plan, banca):
        pdf = PDF(); pdf.add_page()
        
        # Titulo
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"EVENTO: {evento}  |  FECHA: {fecha}", 0, 1); pdf.ln(5)
        
        col_w = 90; gap = 10; x_left = 10; x_right = 10 + col_w + gap
        
        # --- ALGORITMO DE ORDENAMIENTO VISUAL ---
        # Ordenamos las barras por cantidad de personal (Mayor a menor)
        # Esto hace que "General" y "JW" (grandes) queden juntas arriba.
        items_ordenados = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
        
        for i in range(0, len(items_ordenados), 2):
            if pdf.get_y() > 240: pdf.add_page()
            
            y_start = pdf.get_y()
            max_h = 0
            
            # IZQUIERDA
            bar1, eq1 = items_ordenados[i]
            pdf.set_xy(x_left, y_start)
            pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
            pdf.cell(col_w, 8, bar1, 1, 1, 'L', fill=True)
            pdf.set_font("Arial", "", 10)
            for m in eq1:
                rol = m['Rol'].replace("👑", "Jefe").replace("🍺", "Bar").replace("🧊", "Ayu").replace("⚡", "Apoyo")
                pdf.set_x(x_left)
                pdf.cell(35, 7, rol, 1); pdf.cell(55, 7, m['Nombre'], 1, 1)
            h1 = pdf.get_y() - y_start
            if h1 > max_h: max_h = h1
            
            # DERECHA (Si hay par)
            if i + 1 < len(items_ordenados):
                bar2, eq2 = items_ordenados[i+1]
                pdf.set_xy(x_right, y_start)
                pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
                pdf.cell(col_w, 8, bar2, 1, 1, 'L', fill=True)
                pdf.set_font("Arial", "", 10)
                for m in eq2:
                    rol = m['Rol'].replace("👑", "Jefe").replace("🍺", "Bar").replace("🧊", "Ayu").replace("⚡", "Apoyo")
                    pdf.set_x(x_right)
                    pdf.cell(35, 7, rol, 1); pdf.cell(55, 7, m['Nombre'], 1, 1)
                h2 = pdf.get_y() - y_start
                if h2 > max_h: max_h = h2
            
            pdf.set_y(y_start + max_h + 5)

        # Banca al final
        if pdf.get_y() > 250: pdf.add_page()
        pdf.set_x(10)
        pdf.set_fill_color(255, 200, 200); pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"BANCA ({len(banca)})", 1, 1, 'L', fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, ", ".join(banca), border=1)
        
        return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. DATA ---
DB_FILE = "base_datos_staff.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                df = pd.DataFrame(data['staff'])
                evs = data['eventos']
                for e_n, e_d in evs.items():
                    for b in e_d['Barras']: b['matriz_competencias'] = pd.DataFrame(b['matriz_competencias'])
                return df, evs, data['historial'], data['logs']
        except: pass
    df = pd.DataFrame({'Nombre': ['Ejemplo'], 'Cargo_Default': ['BARTENDER']})
    return df, {}, {}, []

def guardar_datos():
    s_json = st.session_state['db_staff'].to_dict(orient='records')
    e_json = {}
    for en, ed in st.session_state['db_eventos'].items():
        bc = []
        for b in ed['Barras']:
            bc_ = b.copy(); bc_['matriz_competencias'] = b['matriz_competencias'].to_dict(orient='records')
            bc.append(bc_)
        e_json[en] = {'Staff_Convocado': ed['Staff_Convocado'], 'Barras': bc}
    data = {'staff': s_json, 'eventos': e_json, 'historial': st.session_state['db_historial_algoritmo'], 'logs': st.session_state['db_logs_visuales']}
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

if 'db_staff' not in st.session_state:
    s, e, h, l = cargar_datos()
    st.session_state['db_staff'] = s; st.session_state['db_eventos'] = e; st.session_state['db_historial_algoritmo'] = h; st.session_state['db_logs_visuales'] = l

# --- 5. LOGICA ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    df = df.sort_values(by=['sort_key', 'Nombre'])
    return df.drop('sort_key', axis=1)

def agregar_indice(df):
    df_new = df.copy(); df_new.insert(0, "N°", range(1, len(df_new) + 1)); return df_new

def calc_altura(df):
    # Fórmula ajustada para filas de 40px (más espacio para dedos)
    return (len(df) * 40) + 41

def ejecutar_algoritmo(nombre_evento):
    d = st.session_state['db_eventos'][nombre_evento]
    h = st.session_state['db_historial_algoritmo'].get(nombre_evento, {})
    asig = {}; tomados = set(); n_h = {}
    
    for barra in d['Barras']:
        nb = barra['nombre']; req = barra['requerimientos']; m = barra['matriz_competencias']
        eq = []; pool = m[~m['Nombre'].isin(tomados)].copy()
        
        def sortear(rol, icon, col_filtro, check_memoria=False):
            cands = pool[pool[col_filtro]==True]
            val = []
            if check_memoria:
                val = [r['Nombre'] for _, r in cands.iterrows() if h.get(r['Nombre'], "") != nb]
            if check_memoria and not val and not cands.empty: val = cands['Nombre'].tolist()
            elif not check_memoria: val = cands['Nombre'].tolist()
            
            if val:
                el = random.choice(val)
                eq.append({'Rol': rol, 'Icon': icon, 'Nombre': el, 'IsSupport': False})
                tomados.add(el)
                if check_memoria: n_h[el] = nb
                return el
            else:
                eq.append({'Rol': rol, 'Icon': icon, 'Nombre': 'VACANTE', 'IsSupport': False})
                return None

        for _ in range(req['enc']): 
            if sortear('Encargado', '👑', 'Es_Encargado', True): pool = m[~m['Nombre'].isin(tomados)].copy()
        for _ in range(req['bar']): 
            if sortear('Bartender', '🍺', 'Es_Bartender', False): pool = m[~m['Nombre'].isin(tomados)].copy()
        for _ in range(req['ayu']): 
            if sortear('Ayudante', '🧊', 'Es_Ayudante', False): pool = m[~m['Nombre'].isin(tomados)].copy()
            
        asig[nb] = eq
    
    banca = [p for p in d['Staff_Convocado'] if p not in tomados]
    return asig, banca, n_h

# --- 6. APP ---
st.title("🍸 Barra Staff V23")

t1, t2, t3, t4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

with t1:
    with st.expander("➕ Alta / Baja Personal", expanded=True):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="rh_nn")
        nr = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"], key="rh_nr")
        
        if st.button("Guardar Personal", key="rh_sv", use_container_width=True):
            if nn:
                # NORMALIZACIÓN Y CONTROL DUPLICADOS
                nombre_limpio = nn.strip() # Quitar espacios extra
                nombres_existentes = st.session_state['db_staff']['Nombre'].values
                
                # Buscamos si existe (ignorando mayusculas/minusculas si quieres, aquí es exacto)
                if nombre_limpio in nombres_existentes:
                    st.error(f"🚫 Error: '{nombre_limpio}' ya existe en la lista.")
                else:
                    nuevo = pd.DataFrame({'Nombre': [nombre_limpio], 'Cargo_Default': [nr]})
                    st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], nuevo], ignore_index=True)
                    guardar_datos()
                    st.success(f"✅ {nombre_limpio} agregado exitosamente.")
            else: st.warning("Escribe un nombre.")

        st.divider()
        df_del = ordenar_staff(st.session_state['db_staff'])
        list_del = st.multiselect("Eliminar:", df_del['Nombre'].tolist(), key="rh_dl")
        if st.button("🚨 Eliminar Seleccionados", key="rh_bd", use_container_width=True):
            st.session_state['db_staff'] = st.session_state['db_staff'][~st.session_state['db_staff']['Nombre'].isin(list_del)]
            guardar_datos(); st.rerun()

    st.subheader("Nómina")
    df_v = ordenar_staff(st.session_state['db_staff'])
    df_v = agregar_indice(df_v)
    h_n = calc_altura(df_v)
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=h_n,
                 column_config={
                     "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                     "Nombre": st.column_config.TextColumn("Nombre", width="medium"),
                     "Cargo_Default": st.column_config.TextColumn("Cargo", width="small")
                 })

with t2:
    with st.expander("🆕 Evento"):
        ne = st.text_input("Nombre", key="cf_ne")
        if st.button("Crear", key="cf_bc", use_container_width=True):
            if ne and ne not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][ne] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][ne] = {}
                guardar_datos(); st.rerun()

    lev = list(st.session_state['db_eventos'].keys())
    if not lev: st.stop()
    ev = st.selectbox("Evento:", lev, key="cf_se")
    dat = st.session_state['db_eventos'][ev]
    
    st.markdown("##### 1. Plantilla (Habilitar)")
    df_b = ordenar_staff(st.session_state['db_staff'])
    conv = set(dat['Staff_Convocado'])
    df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    df_b = agregar_indice(df_b)
    h_p = calc_altura(df_b)
    
    with st.form("fp"):
        # COLUMNAS ESTÁTICAS PARA QUE NO SE MUEVAN
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
            guardar_datos(); st.rerun()

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
                
                # FORZAR ORDEN DE COLUMNAS
                cols_order = ['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']
                df_m = df_m[cols_order]
                df_m = agregar_indice(df_m)
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
                        guardar_datos(); st.rerun()

        for i, barra in enumerate(dat['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"fe_{i}"):
                    nnb = st.text_input("Nombre", barra['nombre'], key=f"en_{i}")
                    c1, c2, c3 = st.columns(3)
                    req = barra['requerimientos']
                    nne = c1.number_input("E", 0, 5, req['enc'], key=f"ee_{i}")
                    nnba = c2.number_input("B", 0, 5, req['bar'], key=f"eb_{i}")
                    nnay = c3.number_input("A", 0, 5, req['ayu'], key=f"ea_{i}")
                    
                    df_base = barra['matriz_competencias']
                    cols_order = ['Nombre', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']
                    for c in cols_order:
                        if c not in df_base.columns: df_base[c] = False
                    df_e = df_base[cols_order]
                    df_e = agregar_indice(df_e)
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
                        guardar_datos(); st.rerun()
                if st.button("Borrar", key=f"bd_{i}", use_container_width=True):
                    st.session_state['db_eventos'][ev]['Barras'].pop(i); guardar_datos(); st.rerun()

with t3:
    c1, c2 = st.columns(2)
    fec = c1.date_input("Fecha", date.today(), key="op_dt")
    evr = c2.selectbox("Evento Op.", lev, key="op_sl")
    
    if st.button("🚀 GENERAR ROTACIÓN", type="primary", key="op_go", use_container_width=True):
        if not st.session_state['db_eventos'][evr]['Barras']: st.error("Faltan barras.")
        else:
            p, b, u = ejecutar_algoritmo(evr)
            st.session_state['res'] = {'plan': p, 'banca': b, 'up': u, 'ev': evr, 'fecha': fec}
    
    if 'res' in st.session_state and st.session_state['res']['ev'] == evr:
        r = st.session_state['res']; st.divider()
        
        with st.expander("➕ Agregar Apoyo / After (Manual)", expanded=False):
            c_a1, c_a2 = st.columns(2)
            bar_add = c_a1.selectbox("Barra destino:", list(r['plan'].keys()), key="sel_bar_add")
            all_staff = sorted(st.session_state['db_staff']['Nombre'].tolist())
            per_add = c_a2.selectbox("Persona:", all_staff, key="sel_per_add")
            
            if st.button("Agregar a la Barra", type="secondary", use_container_width=True):
                st.session_state['res']['plan'][bar_add].append({'Rol': 'Apoyo', 'Icon': '⚡', 'Nombre': per_add, 'IsSupport': True})
                st.success(f"{per_add} agregado a {bar_add}"); st.rerun()
        
        st.divider()
        if FPDF:
            pdf_data = generar_pdf(r['ev'], str(r['fecha']), r['plan'], r['banca'])
            st.download_button("📄 Descargar PDF (Ordenado)", pdf_data, f"Plan_{r['ev']}.pdf", "application/pdf", type="primary", use_container_width=True)
        
        edit_mode = st.toggle("✏️ Editar Asignación", key="op_tgl")
        banca_act = sorted(r['banca'])
        cols = st.columns(3); idx = 0
        for b_nom, eq in r['plan'].items():
            with cols[idx % 3]: 
                st.markdown(f"""<div class="plan-card"><div class="barra-header">{b_nom}</div>""", unsafe_allow_html=True)
                for i, m in enumerate(eq):
                    rol = m['Rol']; ic = m.get('Icon', ''); nm = m['Nombre']; is_supp = m.get('IsSupport', False)
                    if edit_mode and not is_supp:
                        ops = [nm] + banca_act
                        nnm = st.selectbox(f"{ic} {rol}", ops, index=0, key=f"sl_{b_nom}_{i}", label_visibility="collapsed")
                        if nnm != nm:
                            if nnm != "VACANTE" and nnm in r['banca']: r['banca'].remove(nnm)
                            if nm != "VACANTE": r['banca'].append(nm)
                            r['plan'][b_nom][i]['Nombre'] = nnm
                            st.rerun()
                    else:
                        color = "#FF4B4B" if nm == "VACANTE" else ("#FFA500" if is_supp else "var(--text-color)")
                        st.markdown(f"""<div class="fila-rol"><span class="badge">{ic} {rol}</span><span style="font-weight:bold; color:{color}">{nm}</span></div>""", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            idx += 1
        st.info(f"Banca: {', '.join(r['banca'])}")
        if st.button("💾 CERRAR FECHA Y GUARDAR", key="op_save", use_container_width=True):
            nu = {}
            for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE" and not m.get('IsSupport', False): nu[m['Nombre']] = b
            for n, b in nu.items(): st.session_state['db_historial_algoritmo'][r['ev']][n] = b
            log = {'Fecha': str(r['fecha']), 'Evento': r['ev'], 'Plan': r['plan'], 'Banca': list(r['banca'])}
            st.session_state['db_logs_visuales'].append(log)
            guardar_datos(); st.success("Guardado.")

with t4:
    logs = st.session_state['db_logs_visuales']
    if logs:
        for i, log in enumerate(reversed(logs)):
            ri = len(logs) - 1 - i
            with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                if st.button("🗑️ Eliminar Registro", key=f"del_h_{ri}", type="primary", use_container_width=True):
                    st.session_state['db_logs_visuales'].pop(ri); guardar_datos(); st.rerun()
                if FPDF:
                    pdf_h = generar_pdf(log['Evento'], log['Fecha'], log['Plan'], log['Banca'])
                    st.download_button("📄 Descargar PDF", pdf_h, f"Hist_{log['Fecha']}.pdf", "application/pdf", key=f"pdf_h_{ri}", use_container_width=True)
                for b, eq in log['Plan'].items():
                    st.markdown(f"**{b}**"); 
                    for m in eq: st.text(f"{m.get('Icon','')} {m['Rol']}: {m['Nombre']}")
                    st.divider()
                st.caption(f"Banca: {', '.join(log['Banca'])}")
    else: st.info("Sin historial.")
