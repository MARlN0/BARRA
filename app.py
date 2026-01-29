import streamlit as st
import pandas as pd
import random
from datetime import datetime, date
import json
import os
import io
import base64
from PIL import Image, ImageDraw, ImageFont

# --- 0. VALIDACIÓN ---
try:
    from fpdf import FPDF
except ImportError:
    st.error("⚠️ Error Crítico: Falta FPDF. Crea requirements.txt")
    FPDF = None

# --- 1. CONFIG ---
st.set_page_config(page_title="Barra Staff V37", page_icon="🍸", layout="wide")
st.markdown("""
    <style>
    [data-testid="stElementToolbar"] { display: none !important; }
    header { visibility: hidden; }
    .main .block-container { padding-top: 1rem !important; }
    @media (max-width: 768px) {
        .block-container { padding-bottom: 6rem !important; padding-left: 0.2rem; padding-right: 0.2rem; }
        div[data-testid="stDataEditor"] table { font-size: 12px !important; }
        div[data-testid="stDataEditor"] th { padding: 2px !important; text-align: center !important; }
        div[data-testid="stDataEditor"] td { padding: 0px !important; }
        div[data-testid="stDataEditor"] div[role="gridcell"] { min-height: 35px !important; height: 35px !important; align-items: center; }
        .stButton button { width: 100% !important; height: 3.5rem !important; border-radius: 10px !important; font-weight: 700 !important; background-color: #FF4B4B; color: white; border: none; }
    }
    .plan-card { background-color: #1E1E1E; border: 1px solid #333; border-radius: 10px; padding: 10px; margin-bottom: 10px; }
    .barra-title { font-size: 1.1rem; font-weight: 800; color: #FFF; border-bottom: 2px solid #FF4B4B; padding-bottom: 5px; margin-bottom: 8px; text-transform: uppercase; }
    .row-person { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #333; }
    .role-badge { background-color: #333; color: #DDD; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    .name-text { font-weight: bold; font-size: 0.95rem; }
    .ghost-text { font-size: 0.65rem; color: #AAA; font-family: monospace; display: block; text-align: right; margin-top: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN ---
def check_login():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center'>🔐 Acceso QiuClub</h3>", unsafe_allow_html=True)
                u = st.text_input("Usuario"); p = st.text_input("Contraseña", type="password")
                if st.button("Ingresar", type="primary", use_container_width=True):
                    if u == "qiuclub" and p == "barra2026": st.session_state.logged_in = True; st.rerun()
                    else: st.error("Denegado")
        return False
    return True
if not check_login(): st.stop()

# --- 3. DATA ---
DB_FILE = "base_datos_staff.json"
def clean_str(s): return str(s).strip() if s else ""

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                d = json.load(f)
                df = pd.DataFrame(d['staff']); evs = d['eventos']
                for e in evs.values():
                    for b in e['Barras']: b['matriz_competencias'] = pd.DataFrame(b['matriz_competencias'])
                return df, evs, d.get('logs', [])
        except: pass
    return pd.DataFrame({'Nombre':['Ej'],'Cargo_Default':['BARTENDER']}), {}, []

def save_data():
    s = st.session_state.db_staff.to_dict(orient='records'); ev = {}
    for k, v in st.session_state.db_eventos.items():
        bs = []
        for b in v['Barras']:
            bc = b.copy(); bc['matriz_competencias'] = b['matriz_competencias'].to_dict(orient='records'); bs.append(bc)
        ev[k] = {'Staff_Convocado': v['Staff_Convocado'], 'Barras': bs}
    with open(DB_FILE, 'w') as f: json.dump({'staff': s, 'eventos': ev, 'logs': st.session_state.db_logs}, f, indent=4)

if 'db_staff' not in st.session_state:
    s, e, l = load_data()
    st.session_state.db_staff = s; st.session_state.db_eventos = e; st.session_state.db_logs = l

# --- 4. FUNCIÓN HISTORIAL (VERDAD ABSOLUTA) ---
def get_forbidden_map(event_name):
    """
    Construye un mapa {Persona: BarraProhibida} basado en el ÚLTIMO log guardado.
    Esto asegura que lo que ves en el historial es EXACTAMENTE lo que usa el algoritmo.
    """
    forbidden = {}
    last_log = None
    
    # Buscar el último log de este evento
    for log in reversed(st.session_state.db_logs):
        if log['Evento'] == event_name:
            last_log = log
            break
            
    if last_log:
        for bar_name, team in last_log['Plan'].items():
            for member in team:
                p_name = member['Nombre']
                # Si no es vacante y no es apoyo (los apoyos no cuentan para rotación obligatoria)
                if p_name != "VACANTE" and not member.get('IsSupport', False):
                    forbidden[p_name] = bar_name
                    
        # Formato fecha para visual
        try: d_str = datetime.strptime(last_log['Fecha'], '%Y-%m-%d').strftime('%d/%m')
        except: d_str = last_log['Fecha']
        return forbidden, d_str, last_log['Plan']
    
    return {}, "", {}

# --- 5. ALGORITMO ---
def run_allocation(event_name):
    ed = st.session_state.db_eventos[event_name]
    
    # 1. OBTENER MAPA DE PROHIBICIONES REAL
    forbidden_map, _, _ = get_forbidden_map(event_name)
    
    active = set(ed['Staff_Convocado'])
    allo = {}; assigned = set()
    
    for barra in ed['Barras']:
        bn = barra['nombre']; req = barra['requerimientos']; mat = barra['matriz_competencias']
        # Filtro de habilitados hoy
        mat = mat[mat['Nombre'].isin(active)]
        
        team = []
        
        def pick(role_l, role_i, check_col):
            # Filtro base: Tiene rol y no está asignado hoy
            cands = mat[(mat[check_col]==True) & (~mat['Nombre'].isin(assigned))]
            
            valid_candidates = []
            
            for _, r in cands.iterrows():
                p = r['Nombre']
                
                # --- CHECKEO CRÍTICO DE HISTORIAL ---
                # Si la persona está en el mapa de prohibidos Y la barra prohibida es ESTA
                bar_prohibida = forbidden_map.get(p, "")
                
                if clean_str(bar_prohibida) == clean_str(bn):
                    # ESTÁ REPETIDO -> DESCARTAR
                    continue 
                
                valid_candidates.append(p)
            
            if valid_candidates:
                ch = random.choice(valid_candidates)
                assigned.add(ch)
                team.append({'Rol': role_l, 'Icon': role_i, 'Nombre': ch, 'IsSupport': False})
            else:
                # Si todos los candidatos están "quemados" (repetidos), VACANTE.
                team.append({'Rol': role_l, 'Icon': role_i, 'Nombre': 'VACANTE', 'IsSupport': False})

        for _ in range(req['enc']): pick('Encargado', '👑', 'Es_Encargado')
        for _ in range(req['bar']): pick('Bartender', '🍺', 'Es_Bartender')
        for _ in range(req['ayu']): pick('Ayudante', '🧊', 'Es_Ayudante')
        allo[bn] = team

    banca = [p for p in ed['Staff_Convocado'] if p not in assigned]
    return allo, banca

# --- 6. EXPORT ---
def get_pdf_bytes(evento, fecha, plan):
    if not FPDF: return None
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"EVENTO: {evento} | {fecha}", 0, 1, 'L'); pdf.ln(5)
    
    sb = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
    pdf.set_text_color(0,0,0); col_w = 90; xl = 10; xr = 110
    
    for i in range(0, len(sb), 2):
        if pdf.get_y() > 250: pdf.add_page()
        yst = pdf.get_y()
        # I
        b1, t1 = sb[i]; pdf.set_xy(xl, yst); pdf.set_fill_color(220, 220, 220); pdf.set_font("Arial", "B", 11)
        pdf.cell(col_w, 8, b1, 1, 1, 'L', fill=True); pdf.set_font("Arial", "", 10)
        for m in t1:
            r = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apy")
            pdf.set_x(xl); pdf.cell(30, 7, r, 1); pdf.cell(60, 7, m['Nombre'], 1, 1)
        h1 = pdf.get_y() - yst
        # D
        h2 = 0
        if i+1 < len(sb):
            b2, t2 = sb[i+1]; pdf.set_xy(xr, yst); pdf.set_fill_color(220, 220, 220); pdf.set_font("Arial", "B", 11)
            pdf.cell(col_w, 8, b2, 1, 1, 'L', fill=True); pdf.set_font("Arial", "", 10)
            for m in t2:
                r = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apy")
                pdf.set_x(xr); pdf.cell(30, 7, r, 1); pdf.cell(60, 7, m['Nombre'], 1, 1)
            h2 = pdf.get_y() - yst
        pdf.set_y(yst + max(h1, h2) + 5)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def get_img_bytes(evento, fecha, plan):
    try: font_t = ImageFont.truetype("arialbd.ttf", 24); font_b = ImageFont.truetype("arialbd.ttf", 14); font_r = ImageFont.truetype("arial.ttf", 14)
    except: font_t = font_b = font_r = ImageFont.load_default()
    
    sb = sorted(plan.items(), key=lambda x: len(x[1]), reverse=True)
    curr_y = 80; row_h = 30; head_h = 35; P = 20
    for i in range(0, len(sb), 2):
        h_l = head_h + len(sb[i][1])*row_h
        h_r = head_h + len(sb[i+1][1])*row_h if i+1 < len(sb) else 0
        curr_y += max(h_l, h_r) + P
    
    img = Image.new('RGB', (800, curr_y), 'white'); draw = ImageDraw.Draw(img)
    draw.text((P, 20), f"{evento} | {fecha}", fill="black", font=font_t)
    draw.line((P, 60, 780, 60), fill="black", width=3)
    
    curr_y = 80; col_w = 370
    for i in range(0, len(sb), 2):
        def d_col(x, b, t):
            draw.rectangle([x, curr_y, x+col_w, curr_y+head_h], fill="#DDD", outline="black")
            draw.text((x+5, curr_y+8), b, fill="black", font=font_b)
            cy = curr_y + head_h
            for m in t:
                r = m['Rol'].replace("👑","").replace("🍺","").replace("🧊","").replace("⚡","Apy")
                draw.rectangle([x, cy, x+80, cy+row_h], outline="#999"); draw.text((x+5, cy+5), r, fill="black", font=font_r)
                draw.rectangle([x+80, cy, x+col_w, cy+row_h], outline="#999")
                c = "red" if m['Nombre']=="VACANTE" else "black"
                draw.text((x+85, cy+5), m['Nombre'], fill=c, font=font_b)
                cy+=row_h
            return cy-curr_y
        h1 = d_col(P, sb[i][0], sb[i][1])
        h2 = d_col(P+col_w+P, sb[i+1][0], sb[i+1][1]) if i+1 < len(sb) else 0
        curr_y += max(h1, h2) + P
    b = io.BytesIO(); img.save(b, format="PNG"); return b.getvalue()

# --- 7. UTILS ---
def ordenar_staff(df): return df.sort_values(by=['Cargo_Default', 'Nombre'], ascending=[True, True])
def agregar_indice(df): d = df.copy(); d.insert(0, "N°", range(1, len(d)+1)); return d
def calc_altura(df): return (len(df) * 35) + 38

# --- 8. UI ---
st.title("🍸 Barra Staff V37")
t1, t2, t3, t4 = st.tabs(["👥 RH", "⚙️ Config", "🚀 Operación", "📂 Hist"])

with t1:
    with st.expander("➕ Alta", expanded=True):
        c1, c2 = st.columns(2)
        nn = c1.text_input("Nombre", key="n_rh"); nr = c2.selectbox("Rol", ["BARTENDER", "AYUDANTE"], key="r_rh")
        if st.button("Guardar", use_container_width=True):
            if nn and clean_str(nn) not in st.session_state.db_staff['Nombre'].values:
                st.session_state.db_staff = pd.concat([st.session_state.db_staff, pd.DataFrame({'Nombre':[clean_str(nn)], 'Cargo_Default':[nr]})], ignore_index=True)
                save_data(); st.success("Ok"); st.rerun()
            else: st.error("Error")
    df_rh = st.session_state.db_staff.copy(); df_rh.insert(0, "N°", range(1, len(df_rh)+1))
    to_del = st.multiselect("Borrar:", df_rh['Nombre'].tolist())
    if st.button("🗑️"):
        st.session_state.db_staff = st.session_state.db_staff[~st.session_state.db_staff['Nombre'].isin(to_del)]; save_data(); st.rerun()
    st.dataframe(df_rh, use_container_width=True, hide_index=True)

with t2:
    c1, c2 = st.columns([3, 1]); ne = c1.text_input("Nuevo Evento")
    if c2.button("Crear") and ne:
        if ne not in st.session_state.db_eventos:
            st.session_state.db_eventos[ne] = {'Staff_Convocado': [], 'Barras': []}; save_data(); st.rerun()
    
    evs = list(st.session_state.db_eventos.keys())
    if not evs: st.stop()
    curr_ev = st.selectbox("Evento:", evs); evd = st.session_state.db_eventos[curr_ev]
    
    if st.button("🗑️ Borrar Evento"): del st.session_state.db_eventos[curr_ev]; save_data(); st.rerun()
    
    st.write("#### 1. Plantilla"); df_b = ordenar_staff(st.session_state.db_staff)
    conv = set(evd['Staff_Convocado']); df_b.insert(0, 'OK', df_b['Nombre'].apply(lambda x: x in conv))
    st.caption(f"Sel: **{len(evd['Staff_Convocado'])}**"); df_b = agregar_indice(df_b[['OK', 'Nombre', 'Cargo_Default']])
    with st.form("fp"):
        ed = st.data_editor(df_b, column_config={"OK": st.column_config.CheckboxColumn("✅", width="small")}, use_container_width=True, hide_index=True, height=calc_altura(df_b))
        if st.form_submit_button("💾 Guardar"):
            st.session_state.db_eventos[curr_ev]['Staff_Convocado'] = ed[ed['OK']==True]['Nombre'].tolist(); save_data(); st.rerun()

    st.write("#### 2. Barras")
    with st.expander("Añadir"):
        bn = st.text_input("Nombre"); c1, c2, c3 = st.columns(3)
        ne = c1.number_input("E", 0, 5, 1); nb = c2.number_input("B", 0, 5, 1); na = c3.number_input("A", 0, 5, 1)
        lok = evd['Staff_Convocado']
        if lok:
            dfm = st.session_state.db_staff[st.session_state.db_staff['Nombre'].isin(lok)].copy()
            dfm['Es_Encargado']=False; dfm['Es_Bartender']=dfm['Cargo_Default']=='BARTENDER'; dfm['Es_Ayudante']=dfm['Cargo_Default']=='AYUDANTE'
            em = st.data_editor(agregar_indice(dfm[['Nombre','Es_Encargado','Es_Bartender','Es_Ayudante']]), use_container_width=True, hide_index=True)
            if st.button("Guardar Barra"):
                st.session_state.db_eventos[curr_ev]['Barras'].append({'nombre': bn, 'requerimientos': {'enc': ne, 'bar': nb, 'ayu': na}, 'matriz_competencias': em.drop('N°', axis=1).to_dict(orient='records')}); save_data(); st.rerun()

    for i, b in enumerate(evd['Barras']):
        with st.expander(f"✏️ {b['nombre']}"):
            if st.button("X", key=f"d{i}"): st.session_state.db_eventos[curr_ev]['Barras'].pop(i); save_data(); st.rerun()
            # Sync
            dfc = pd.DataFrame(b['matriz_competencias']); dfr = st.session_state.db_staff[st.session_state.db_staff['Nombre'].isin(lok)][['Nombre', 'Cargo_Default']]
            m = pd.merge(dfr, dfc, on='Nombre', how='left')
            m['Es_Encargado'].fillna(False, inplace=True); m['Es_Bartender'].fillna(m['Cargo_Default']=='BARTENDER', inplace=True); m['Es_Ayudante'].fillna(m['Cargo_Default']=='AYUDANTE', inplace=True)
            eb = st.data_editor(agregar_indice(ordenar_staff(m)[['Nombre','Es_Encargado','Es_Bartender','Es_Ayudante']]), key=f"e{i}", use_container_width=True, hide_index=True)
            if st.button("Update", key=f"u{i}"):
                st.session_state.db_eventos[curr_ev]['Barras'][i]['matriz_competencias'] = eb.drop('N°', axis=1).to_dict(orient='records'); save_data(); st.rerun()

with t3:
    c1, c2 = st.columns(2); od = c1.date_input("Fecha"); oe = c2.selectbox("Evento", list(st.session_state.db_eventos.keys()), key="oe")
    
    if st.button("🚀 GENERAR", type="primary", use_container_width=True):
        p, b = run_allocation(oe)
        st.session_state.temp = {'p': p, 'b': b, 'e': oe, 'd': od}
    
    if 'temp' in st.session_state and st.session_state.temp['e'] == oe:
        res = st.session_state.temp
        
        # --- PREPARAR DATOS FANTASMA (Desde Logs) ---
        _, _, prev_plan_complete = get_forbidden_map(oe)
        
        # UI
        if res['b']: st.warning(f"⚠️ Banca: {', '.join(res['b'])}")
        else: st.success("✅ Full")
        
        with st.expander("➕ Apoyo"):
            c1, c2 = st.columns(2); ba = c1.selectbox("Barra", list(res['p'].keys())); pa = c2.selectbox("Per", sorted(st.session_state.db_staff['Nombre'].unique()))
            if st.button("Add"): 
                res['p'][ba].append({'Rol':'Apoyo','Icon':'⚡','Nombre':pa,'IsSupport':True})
                if pa in res['b']: res['b'].remove(pa)
                st.rerun()
        
        c1, c2 = st.columns(2)
        if FPDF: 
            pdf = get_pdf_bytes(res['e'], str(res['d']), res['p'])
            c1.download_button("📄 PDF", pdf, "p.pdf", "application/pdf", use_container_width=True)
        img = get_img_bytes(res['e'], str(res['d']), res['p'])
        c2.download_button("📷 IMG", img, "p.png", "image/png", use_container_width=True)
        
        em = st.toggle("✏️ Edit")
        cols = st.columns(3); idx = 0
        for bn, tm in res['p'].items():
            with cols[idx%3]:
                st.markdown(f"<div class='plan-card'><div class='barra-title'>{bn}</div>", unsafe_allow_html=True)
                for i, m in enumerate(tm):
                    pn = m['Nombre']
                    
                    # --- GHOST TEXT LOGIC ---
                    ghost = ""
                    if prev_plan_complete and bn in prev_plan_complete:
                        # Buscamos si esta persona estuvo en esta barra la vez pasada
                        # OJO: No por indice, sino por nombre
                        # Pero queremos mostrar QUIEN ocupaba este puesto? No, queremos saber donde estuvo EL.
                        
                        # Buscamos donde estuvo 'pn' la vez pasada
                        for p_bar, p_team in prev_plan_complete.items():
                            for p_mem in p_team:
                                if p_mem['Nombre'] == pn:
                                    # Fecha del log anterior
                                    _, d_str, _ = get_forbidden_map(oe)
                                    # Rol corto
                                    r = p_mem['Rol'][:3]
                                    ghost = f"({p_bar} • {r} • {d_str})"
                    
                    if em and not m.get('IsSupport'):
                        np = st.selectbox(f"{m['Icon']}", [pn]+sorted(res['b']), key=f"s_{bn}_{i}", label_visibility="collapsed")
                        if np != pn:
                            if pn!="VACANTE": res['b'].append(pn)
                            if np!="VACANTE" and np in res['b']: res['b'].remove(np)
                            m['Nombre'] = np; st.rerun()
                    else:
                        c = "#FF4B4B" if pn=="VACANTE" else ("#FFA500" if m.get('IsSupport') else "#FFF")
                        st.markdown(f"<div class='row-person'><span class='role-badge'>{m['Icon']} {m['Rol']}</span><div style='text-align:right'><div class='name-text' style='color:{c}'>{pn}</div><div class='ghost-text'>{ghost}</div></div></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            idx+=1
            
        if st.button("💾 CERRAR", type="primary", use_container_width=True):
            st.session_state.db_logs.append({'Fecha':str(res['d']), 'Evento':res['e'], 'Plan':res['p'], 'Banca':res['b']})
            save_data(); st.success("Guardado")

with t4:
    if not st.session_state.db_logs: st.info("Vacío")
    else:
        for i, l in enumerate(reversed(st.session_state.db_logs)):
            rx = len(st.session_state.db_logs)-1-i
            with st.expander(f"📅 {l['Fecha']} - {l['Evento']}"):
                if st.button("🗑️", key=f"d_{rx}"): st.session_state.db_logs.pop(rx); save_data(); st.rerun()
                if FPDF:
                    p = get_pdf_bytes(l['Evento'], l['Fecha'], l['Plan'])
                    st.download_button("📄", p, "h.pdf", "application/pdf", key=f"p_{rx}")
