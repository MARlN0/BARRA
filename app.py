import streamlit as st
import pandas as pd
import random
from datetime import date
import json
import os
import base64

# Validación FPDF
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Error: FPDF no instalado. Crea requirements.txt en GitHub.")
    FPDF = None

# --- 1. CONFIGURACIÓN VISUAL (CSS AJUSTADO PARA ELIMINAR HUECOS) ---
st.set_page_config(page_title="Barra Staff V25", page_icon="🍸", layout="wide")

st.markdown("""
    <style>
    /* OCULTAR TOOLBAR */
    [data-testid="stElementToolbar"] { display: none !important; visibility: hidden !important; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem !important; }

    /* OPTIMIZACIÓN CELULAR EXTREMA */
    @media (max-width: 768px) {
        .block-container { 
            padding-left: 0.1rem !important; 
            padding-right: 0.1rem !important; 
            padding-bottom: 5rem !important; 
        }
        
        /* FUENTE Y ESPACIADO DE TABLA - ELIMINAR HUECOS */
        div[data-testid="stDataEditor"] table { font-size: 12px !important; }
        div[data-testid="stDataEditor"] th { 
            font-size: 10px !important; 
            padding: 2px !important; 
            text-align: left !important;
        }
        div[data-testid="stDataEditor"] td { 
            padding: 0px 1px !important; /* MÍNIMO PADDING */
            line-height: 1.1 !important;
        }
        
        /* Altura de fila */
        div[data-testid="stDataEditor"] div[role="gridcell"] { 
            min-height: 32px !important; 
            height: 32px !important; 
            display: flex; 
            align-items: center; 
        }
        
        /* BOTONES */
        .stButton button { width: 100% !important; height: 3.5rem !important; font-weight: bold !important; background-color: #FF4B4B; color: white; border: none; }
    }

    /* TARJETAS */
    .plan-card { border: 1px solid rgba(200, 200, 200, 0.3); border-radius: 12px; padding: 10px; margin-bottom: 8px; background-color: rgba(128, 128, 128, 0.05); }
    .barra-header { font-size: 1rem; font-weight: 800; text-transform: uppercase; color: var(--text-color); border-bottom: 3px solid #FF4B4B; margin-bottom: 5px; }
    .fila-rol { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; border-bottom: 1px solid rgba(128, 128, 128, 0.1); }
    .badge { padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; background-color: rgba(128, 128, 128, 0.15); }
    .apoyo-text { color: #FFA500 !important; font-weight: bold; font-style: italic; }
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

# --- 3. PDF ---
if FPDF:
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14); self.cell(0, 10, 'REPORTE OPERATIVO', 0, 1, 'C'); self.ln(5)
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Pag {self.page_no()}', 0, 0, 'C')

    def generar_pdf(evento, fecha, plan, banca):
        pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"EVENTO: {evento}  |  FECHA: {fecha}", 0, 1); pdf.ln(5)
        
        col_w = 90; gap = 10; x_left = 10; x_right = 10 + col_w + gap
        items = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True) # Ordenar por tamaño
        
        for i in range(0, len(items), 2):
            if pdf.get_y() > 240: pdf.add_page()
            y_start = pdf.get_y(); max_h = 0
            
            # IZQ
            b1, e1 = items[i]
            pdf.set_xy(x_left, y_start); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
            pdf.cell(col_w, 8, b1, 1, 1, 'L', fill=True)
            pdf.set_font("Arial", "", 10)
            for m in e1:
                r = m['Rol'].replace("👑", "Jefe").replace("🍺", "Bar").replace("🧊", "Ayu").replace("⚡", "Apoyo")
                pdf.set_x(x_left); pdf.cell(35, 7, r, 1); pdf.cell(55, 7, m['Nombre'], 1, 1)
            h1 = pdf.get_y() - y_start; max_h = max(max_h, h1)
            
            # DER
            if i+1 < len(items):
                b2, e2 = items[i+1]
                pdf.set_xy(x_right, y_start); pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
                pdf.cell(col_w, 8, b2, 1, 1, 'L', fill=True)
                pdf.set_font("Arial", "", 10)
                for m in e2:
                    r = m['Rol'].replace("👑", "Jefe").replace("🍺", "Bar").replace("🧊", "Ayu").replace("⚡", "Apoyo")
                    pdf.set_x(x_right); pdf.cell(35, 7, r, 1); pdf.cell(55, 7, m['Nombre'], 1, 1)
                h2 = pdf.get_y() - y_start; max_h = max(max_h, h2)
            
            pdf.set_y(y_start + max_h + 5)

        if pdf.get_y() > 250: pdf.add_page()
        pdf.set_x(10); pdf.set_fill_color(255, 200, 200); pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"BANCA ({len(banca)})", 1, 1, 'L', fill=True)
        pdf.set_font("Arial", "", 10); pdf.multi_cell(0, 7, ", ".join(banca), border=1)
        return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. MOTOR IMAGEN ---
from PIL import Image, ImageDraw, ImageFont
import io
def generar_imagen(evento, fecha, plan, banca):
    WIDTH = 800; PADDING = 20; COL_W = (WIDTH-(PADDING*3))//2; ROW_H = 30; HEAD_H = 35
    items = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
    cur_y = 100
    for i in range(0, len(items), 2):
        h1 = HEAD_H + (len(items[i][1])*ROW_H)
        h2 = HEAD_H + (len(items[i+1][1])*ROW_H) if i+1<len(items) else 0
        cur_y += max(h1, h2) + PADDING
    banca_h = ((len(", ".join(banca))//50)+1)*ROW_H
    tot_h = cur_y + HEAD_H + banca_h + PADDING
    
    img = Image.new('RGB', (WIDTH, tot_h), 'white'); draw = ImageDraw.Draw(img)
    try: font_b = ImageFont.truetype("arialbd.ttf", 14); font_r = ImageFont.truetype("arial.ttf", 14); font_t = ImageFont.truetype("arial.ttf", 24)
    except: font_b = font_r = font_t = ImageFont.load_default()
    
    draw.text((PADDING, 20), f"{evento} | {fecha}", fill="black", font=font_t)
    draw.line((PADDING, 60, WIDTH-PADDING, 60), fill="black", width=2)
    
    cur_y = 80
    for i in range(0, len(items), 2):
        max_row = 0
        # Izq
        b1, e1 = items[i]; x = PADDING
        draw.rectangle([x, cur_y, x+COL_W, cur_y+HEAD_H], fill="#E0E0E0", outline="black")
        draw.text((x+5, cur_y+8), b1, fill="black", font=font_b)
        cy = cur_y+HEAD_H
        for m in e1:
            r = m['Rol'].replace("👑","Jefe").replace("🍺","Bar").replace("🧊","Ayu").replace("⚡","Apoyo")
            draw.rectangle([x, cy, x+80, cy+ROW_H], outline="gray"); draw.text((x+5, cy+5), r, fill="black", font=font_r)
            draw.rectangle([x+80, cy, x+COL_W, cy+ROW_H], outline="gray")
            c_nm = "red" if m['Nombre']=="VACANTE" else ("#D2691E" if m.get('IsSupport') else "black")
            draw.text((x+85, cy+5), m['Nombre'], fill=c_nm, font=font_b)
            cy+=ROW_H
        max_row = max(max_row, cy-cur_y)
        
        # Der
        if i+1 < len(items):
            b2, e2 = items[i+1]; x = PADDING+COL_W+PADDING
            draw.rectangle([x, cur_y, x+COL_W, cur_y+HEAD_H], fill="#E0E0E0", outline="black")
            draw.text((x+5, cur_y+8), b2, fill="black", font=font_b)
            cy = cur_y+HEAD_H
            for m in e2:
                r = m['Rol'].replace("👑","Jefe").replace("🍺","Bar").replace("🧊","Ayu").replace("⚡","Apoyo")
                draw.rectangle([x, cy, x+80, cy+ROW_H], outline="gray"); draw.text((x+5, cy+5), r, fill="black", font=font_r)
                draw.rectangle([x+80, cy, x+COL_W, cy+ROW_H], outline="gray")
                c_nm = "red" if m['Nombre']=="VACANTE" else ("#D2691E" if m.get('IsSupport') else "black")
                draw.text((x+85, cy+5), m['Nombre'], fill=c_nm, font=font_b)
                cy+=ROW_H
            max_row = max(max_row, cy-cur_y)
        cur_y += max_row + PADDING
        
    draw.rectangle([PADDING, cur_y, WIDTH-PADDING, cur_y+HEAD_H], fill="#FFCCCC", outline="black")
    draw.text((PADDING+5, cur_y+8), f"BANCA ({len(banca)})", fill="black", font=font_b)
    draw.rectangle([PADDING, cur_y+HEAD_H, WIDTH-PADDING, cur_y+HEAD_H+banca_h], outline="black")
    draw.text((PADDING+5, cur_y+HEAD_H+5), ", ".join(banca), fill="black", font=font_r)
    
    b = io.BytesIO(); img.save(b, format="PNG"); return b.getvalue()

# --- 5. DATA ---
DB_FILE = "base_datos_staff.json"
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                d = json.load(f); df = pd.DataFrame(d['staff']); ev = d['eventos']
                for e in ev.values():
                    for b in e['Barras']: b['matriz_competencias'] = pd.DataFrame(b['matriz_competencias'])
                return df, ev, d['historial'], d['logs']
        except: pass
    return pd.DataFrame({'Nombre':['Ejemplo'],'Cargo_Default':['BARTENDER']}), {}, {}, []

def guardar_datos():
    s = st.session_state['db_staff'].to_dict(orient='records'); ev = {}
    for k, v in st.session_state['db_eventos'].items():
        bs = []
        for b in v['Barras']:
            bc = b.copy(); bc['matriz_competencias'] = b['matriz_competencias'].to_dict(orient='records'); bs.append(bc)
        ev[k] = {'Staff_Convocado': v['Staff_Convocado'], 'Barras': bs}
    with open(DB_FILE, 'w') as f: json.dump({'staff': s, 'eventos': ev, 'historial': st.session_state['db_historial_algoritmo'], 'logs': st.session_state['db_logs_visuales']}, f, indent=4)

if 'db_staff' not in st.session_state:
    s, e, h, l = cargar_datos()
    st.session_state['db_staff'] = s; st.session_state['db_eventos'] = e; st.session_state['db_historial_algoritmo'] = h; st.session_state['db_logs_visuales'] = l

# --- 6. FUNCIONES ---
def ordenar_staff(df):
    df['sort_key'] = df['Cargo_Default'].map({'BARTENDER': 0, 'AYUDANTE': 1})
    return df.sort_values(by=['sort_key', 'Nombre']).drop('sort_key', axis=1)

def agregar_indice(df):
    df = df.copy(); df.insert(0, "N°", range(1, len(df) + 1)); return df

def calc_altura(df): return (len(df) * 35) + 38

def ejecutar_algoritmo(nombre_evento):
    d = st.session_state['db_eventos'][nombre_evento]
    h = st.session_state['db_historial_algoritmo'].get(nombre_evento, {})
    asig = {}; tomados = set(); n_h = {}
    for barra in d['Barras']:
        nb = barra['nombre']; req = barra['requerimientos']; m = barra['matriz_competencias']
        eq = []; pool = m[~m['Nombre'].isin(tomados)].copy()
        
        def sortear(rol, icon, col_filtro, check_memoria=False):
            cands = pool[pool[col_filtro]==True]
            val = [r['Nombre'] for _, r in cands.iterrows() if h.get(r['Nombre'], "") != nb] if check_memoria else cands['Nombre'].tolist()
            if check_memoria and not val and not cands.empty: val = cands['Nombre'].tolist()
            if val:
                el = random.choice(val); eq.append({'Rol': rol, 'Icon': icon, 'Nombre': el, 'IsSupport': False}); tomados.add(el)
                if check_memoria: n_h[el] = nb
                return True
            else: eq.append({'Rol': rol, 'Icon': icon, 'Nombre': 'VACANTE', 'IsSupport': False}); return False

        for _ in range(req['enc']): 
            if sortear('Encargado', '👑', 'Es_Encargado', True): pool = m[~m['Nombre'].isin(tomados)].copy()
        for _ in range(req['bar']): 
            if sortear('Bartender', '🍺', 'Es_Bartender', False): pool = m[~m['Nombre'].isin(tomados)].copy()
        for _ in range(req['ayu']): 
            if sortear('Ayudante', '🧊', 'Es_Ayudante', False): pool = m[~m['Nombre'].isin(tomados)].copy()
        asig[nb] = eq
    return asig, [p for p in d['Staff_Convocado'] if p not in tomados], n_h

# --- 7. UI ---
st.title("🍸 Barra Staff V1")
t1, t2, t3, t4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

with t1:
    with st.expander("➕ Alta / Baja Personal", expanded=True):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="rh_nn")
        nr = c2.selectbox("Cargo", ["BARTENDER", "AYUDANTE"], key="rh_nr")
        if st.button("Guardar Personal", key="rh_sv", use_container_width=True):
            if nn:
                nom = nn.strip()
                if nom in st.session_state['db_staff']['Nombre'].values: st.error(f"🚫 '{nom}' ya existe.")
                else:
                    st.session_state['db_staff'] = pd.concat([st.session_state['db_staff'], pd.DataFrame({'Nombre':[nom],'Cargo_Default':[nr]})], ignore_index=True)
                    guardar_datos(); st.success(f"✅ {nom} agregado.")
            else: st.warning("Escribe nombre.")
        st.divider()
        df_d = ordenar_staff(st.session_state['db_staff'])
        ld = st.multiselect("Eliminar:", df_d['Nombre'].tolist(), key="rh_dl")
        if st.button("🚨 Eliminar", key="rh_bd", use_container_width=True):
            st.session_state['db_staff'] = st.session_state['db_staff'][~st.session_state['db_staff']['Nombre'].isin(ld)]; guardar_datos(); st.rerun()

    st.subheader("Nómina")
    df_v = agregar_indice(ordenar_staff(st.session_state['db_staff']))
    st.dataframe(df_v, use_container_width=True, hide_index=True, height=calc_altura(df_v),
                 column_config={"N°": st.column_config.NumberColumn("N°", width="small", format="%d")})

with t2:
    with st.expander("🆕 Evento"):
        ne = st.text_input("Nombre", key="cf_ne")
        if st.button("Crear", key="cf_bc", use_container_width=True):
            if ne not in st.session_state['db_eventos']:
                st.session_state['db_eventos'][ne] = {'Staff_Convocado': [], 'Barras': []}
                st.session_state['db_historial_algoritmo'][ne] = {}; guardar_datos(); st.rerun()

    lev = list(st.session_state['db_eventos'].keys())
    if not lev: st.stop()
    ev = st.selectbox("Evento:", lev, key="cf_se"); dat = st.session_state['db_eventos'][ev]
    
    st.markdown("##### 1. Plantilla (Selección)")
    df_b = ordenar_staff(st.session_state['db_staff'])
    conv = set(dat['Staff_Convocado'])
    df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    
    # CONTADOR DE SELECCIONADOS
    count_sel = len(dat['Staff_Convocado'])
    count_tot = len(df_b)
    st.caption(f"👥 Seleccionados: **{count_sel}** / {count_tot}")

    # FORZAR ORDEN DE COLUMNAS: N | Check | Nombre | Rol
    df_b = df_b[['OK', 'Nombre', 'Cargo_Default']] # Cargo_Default es el "Rol"
    df_b = agregar_indice(df_b) # Agrega N° al inicio
    
    with st.form("fp"):
        df_ed = st.data_editor(
            df_b,
            column_config={
                "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                "OK": st.column_config.CheckboxColumn("✅", width="small"),
                "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                "Cargo_Default": st.column_config.TextColumn("Rol", width="small", disabled=True) 
            },
            disabled=["N°", "Nombre", "Cargo_Default"], use_container_width=True, hide_index=True, height=calc_altura(df_b)
        )
        if st.form_submit_button("💾 Guardar Plantilla", use_container_width=True):
            st.session_state['db_eventos'][ev]['Staff_Convocado'] = df_ed[df_ed['OK']==True]['Nombre'].tolist(); guardar_datos(); st.rerun()

    st.markdown("##### 2. Barras")
    lok = dat['Staff_Convocado']
    if lok:
        with st.expander("➕ Crear Barra"):
            with st.form("fb"):
                nb = st.text_input("Nombre", key="bn"); c1, c2, c3 = st.columns(3)
                ne = c1.number_input("E", 0, 5, 1, key="be"); nba = c2.number_input("B", 0, 5, 1, key="bb"); nay = c3.number_input("A", 0, 5, 1, key="ba")
                
                df_m = df_b[df_b['Nombre'].isin(lok)].copy().drop(['OK', 'N°'], axis=1)
                # Renombramos Cargo para usarlo internamente pero no mostrarlo redundante si no quieres, pero aqui ayuda
                df_m['Es_Encargado'] = False; df_m['Es_Bartender'] = df_m['Cargo_Default']=='BARTENDER'; df_m['Es_Ayudante'] = df_m['Cargo_Default']=='AYUDANTE'
                
                # ORDEN ESTRICTO: Nombre | Rol | Checks
                df_m = df_m[['Nombre', 'Cargo_Default', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']]
                df_m = agregar_indice(df_m)
                
                mo = st.data_editor(df_m, use_container_width=True, hide_index=True, height=calc_altura(df_m),
                    column_config={
                        "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                        "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                        "Cargo_Default": st.column_config.TextColumn("Rol", width="small", disabled=True),
                        "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                        "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                        "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small")
                    })
                if st.form_submit_button("Guardar", use_container_width=True):
                    if nb:
                        # Guardamos sin N° y sin Rol (ya está en la base global, solo guardamos matriz)
                        mo_cl = mo.drop(['N°', 'Cargo_Default'], axis=1)
                        st.session_state['db_eventos'][ev]['Barras'].append({'nombre': nb, 'requerimientos': {'enc': ne, 'bar': nba, 'ayu': nay}, 'matriz_competencias': mo_cl})
                        guardar_datos(); st.rerun()

        for i, barra in enumerate(dat['Barras']):
            with st.expander(f"✏️ {barra['nombre']}"):
                with st.form(f"fe_{i}"):
                    nnb = st.text_input("Nombre", barra['nombre'], key=f"en_{i}"); c1, c2, c3 = st.columns(3); req = barra['requerimientos']
                    nne = c1.number_input("E", 0, 5, req['enc'], key=f"ee_{i}"); nnba = c2.number_input("B", 0, 5, req['bar'], key=f"eb_{i}"); nnay = c3.number_input("A", 0, 5, req['ayu'], key=f"ea_{i}")
                    
                    # Recuperar Rol para mostrarlo al editar
                    df_base = barra['matriz_competencias'].copy()
                    # Cruzar con staff global para traer el rol actualizado
                    staff_roles = st.session_state['db_staff'][['Nombre', 'Cargo_Default']]
                    df_base = df_base.merge(staff_roles, on='Nombre', how='left')
                    
                    # Ordenar
                    cols = ['Nombre', 'Cargo_Default', 'Es_Encargado', 'Es_Bartender', 'Es_Ayudante']
                    for c in cols: 
                        if c not in df_base.columns: df_base[c] = False
                    df_e = df_base[cols]
                    df_e = agregar_indice(df_e)
                    
                    me = st.data_editor(df_e, use_container_width=True, hide_index=True, height=calc_altura(df_e),
                        column_config={
                            "N°": st.column_config.NumberColumn("N°", width="small", format="%d"),
                            "Nombre": st.column_config.TextColumn("Nombre", width="medium", disabled=True),
                            "Cargo_Default": st.column_config.TextColumn("Rol", width="small", disabled=True),
                            "Es_Encargado": st.column_config.CheckboxColumn("👑", width="small"),
                            "Es_Bartender": st.column_config.CheckboxColumn("🍺", width="small"),
                            "Es_Ayudante": st.column_config.CheckboxColumn("🧊", width="small")
                        })
                    if st.form_submit_button("Actualizar", use_container_width=True):
                        st.session_state['db_eventos'][ev]['Barras'][i] = {'nombre': nnb, 'requerimientos': {'enc': nne, 'bar': nnba, 'ayu': nnay}, 'matriz_competencias': me.drop(['N°', 'Cargo_Default'], axis=1)}
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
        
        with st.expander("➕ Apoyo / After (Manual)", expanded=False):
            c_a1, c_a2 = st.columns(2)
            bar_add = c_a1.selectbox("Destino:", list(r['plan'].keys()), key="sba")
            all_s = sorted(st.session_state['db_staff']['Nombre'].tolist())
            per_add = c_a2.selectbox("Persona:", all_s, key="spa")
            if st.button("Agregar", use_container_width=True):
                st.session_state['res']['plan'][bar_add].append({'Rol': 'Apoyo', 'Icon': '⚡', 'Nombre': per_add, 'IsSupport': True})
                st.rerun()
        
        c_pdf, c_img = st.columns(2)
        if FPDF:
            pdf_data = generar_pdf(r['ev'], str(r['fecha']), r['plan'], r['banca'])
            c_pdf.download_button("📄 PDF", pdf_data, f"Plan.pdf", "application/pdf", type="primary", use_container_width=True)
        img_data = generar_imagen(r['ev'], str(r['fecha']), r['plan'], r['banca'])
        c_img.download_button("📷 IMG", img_data, f"Plan.png", "image/png", type="primary", use_container_width=True)
        
        edit_mode = st.toggle("✏️ Editar", key="op_tgl")
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
        if st.button("💾 CERRAR FECHA", key="op_save", use_container_width=True):
            nu = {}
            for b, eq in r['plan'].items():
                for m in eq:
                    if "Encargado" in m['Rol'] and m['Nombre'] != "VACANTE" and not m.get('IsSupport', False): nu[m['Nombre']] = b
            for n, b in nu.items(): st.session_state['db_historial_algoritmo'][r['ev']][n] = b
            log = {'Fecha': str(r['fecha']), 'Evento': r['ev'], 'Plan': r['plan'], 'Banca': list(r['banca'])}
            st.session_state['db_logs_visuales'].append(log); guardar_datos(); st.success("Guardado.")

with t4:
    logs = st.session_state['db_logs_visuales']
    if logs:
        for i, log in enumerate(reversed(logs)):
            ri = len(logs) - 1 - i
            with st.expander(f"📅 {log['Fecha']} - {log['Evento']}"):
                c1, c2, c3 = st.columns(3)
                if c1.button("🗑️", key=f"del_{ri}", type="primary", use_container_width=True):
                    st.session_state['db_logs_visuales'].pop(ri); guardar_datos(); st.rerun()
                if FPDF:
                    pdf_h = generar_pdf(log['Evento'], log['Fecha'], log['Plan'], log['Banca'])
                    c2.download_button("📄", pdf_h, f"Hist.pdf", "application/pdf", key=f"pdf_{ri}", use_container_width=True)
                img_h = generar_imagen(log['Evento'], log['Fecha'], log['Plan'], log['Banca'])
                c3.download_button("📷", img_h, f"Hist.png", "image/png", key=f"img_{ri}", use_container_width=True)
                for b, eq in log['Plan'].items():
                    st.markdown(f"**{b}**"); 
                    for m in eq: st.text(f"{m.get('Icon','')} {m['Rol']}: {m['Nombre']}")
                    st.divider()
                st.caption(f"Banca: {', '.join(log['Banca'])}")
    else: st.info("Sin historial.")

