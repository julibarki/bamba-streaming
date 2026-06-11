import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS PREMIUM SaaS (DARK MINIMALIST) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #0f172a !important; font-family: 'Inter', sans-serif; }
    
    /* Títulos y textos */
    h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    p, label { color: #94a3b8 !important; }

    /* --- CARDS DE ASISTENCIA (TACTICAL GRID) --- */
    .staff-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: all 0.2s ease-in-out;
        margin-bottom: -35px; /* Compacta el toggle con la card */
    }

    .staff-box.active {
        border-color: #6366f1;
        background-color: rgba(99, 102, 241, 0.1);
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
    }

    .staff-name { color: #ffffff; font-weight: 600; font-size: 1.1rem; }
    .staff-role { color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }

    /* Botones y Formas */
    .stButton > button {
        background: #6366f1 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        width: 100%;
    }
    
    /* Tabs Minimalistas */
    .stTabs [data-baseweb="tab-list"] { background-color: #0f172a !important; gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b !important;
        border-radius: 10px 10px 0 0 !important;
        color: #94a3b8 !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] { color: #6366f1 !important; border-bottom: 2px solid #6366f1 !important; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0b0f1a !important; border-right: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- CAPA DE DATOS ---
def run_query(query, params=None, is_select=True):
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if is_select:
                res = cur.fetchall()
                conn.close()
                return pd.DataFrame(res)
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Error DB: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        _, c2, _ = st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center;'>🎙️ BAMBA</h1>", unsafe_allow_html=True)
            pw = st.text_input("Master Password", type="password")
            if st.button("Entrar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.title("📊 Dashboard")
    hoy = date.today()
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c2.selectbox("Año", [2024, 2025], index=0)

    ing = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    pay = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    t_in, t_ga, t_pa = float(ing['t'][0] or 0), float(gas['t'][0] or 0), float(pay['t'][0] or 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", f"$ {t_in:,.0f}")
    m2.metric("Egresos", f"$ {t_ga + t_pa:,.0f}")
    m3.metric("Caja Neta", f"$ {t_in - t_ga - t_pa:,.0f}")

# --- MODULO 2: ASISTENCIA (TACTICAL GRID) ---
def mod_asistencia():
    st.markdown("<h2>📋 Asistencia</h2>", unsafe_allow_html=True)
    
    em_df = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if em_df.empty:
        st.info("Cargá programas en Configuración.")
        return
    
    opcs = {r['id']: f"{r['fecha'].strftime('%d/%m')} — {r['titulo_episodio']}" for _, r in em_df.iterrows()}
    eid = st.selectbox("Seleccionar Programa", options=opcs.keys(), format_func=lambda x: opcs[x])
    
    st.write("##")
    
    staff_data = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
    asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
    list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

    updates = []
    n_cols = 4 
    for i in range(0, len(staff_data), n_cols):
        cols = st.columns(n_cols)
        for j, (_, s) in enumerate(staff_data.iloc[i:i+n_cols].iterrows()):
            with cols[j]:
                is_p = s['id'] in list_asist
                st.markdown(f"""
                    <div class="staff-box {'active' if is_p else ''}">
                        <div class="staff-name">{s['nombre']}</div>
                        <div class="staff-role">{s['rol']}</div>
                    </div>
                """, unsafe_allow_html=True)
                pres = st.toggle("Presente", value=is_p, key=f"t_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

    st.write("##")
    if st.button("💾 GUARDAR ASISTENCIA"):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("Asistencia Guardada")

# --- MODULO 3: SUELDOS (CLEAN VOUCHERS) ---
def mod_sueldos():
    st.title("💰 Liquidación")
    c1, c2, _ = st.columns([1,1,2])
    mes, anio = c1.selectbox("Mes", range(1, 13), index=date.today().month-1), c2.selectbox("Año", [2024, 2025], index=0)

    query = """
        SELECT 
            s.id as staff_id, s.nombre, s.rol,
            CAST(s.sueldo_base AS FLOAT) as base,
            CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado = 'FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s AND EXTRACT(YEAR FROM e.fecha) = %s) AS FLOAT) as progs,
            CAST(s.pago_por_programa AS FLOAT) as val_prog,
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as extras,
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as adelantos
        FROM staff s
        LEFT JOIN pagos_sueldos ps ON s.id = ps.staff_id AND ps.mes = %s AND ps.anio = %s
        WHERE s.activo = TRUE AND ps.id IS NULL
    """
    df_pay = run_query(query, (mes, anio, mes, anio, mes, anio, mes, anio))

    if df_pay.empty:
        st.success("Todo pagado.")
    else:
        for _, r in df_pay.iterrows():
            total = r['base'] + (r['progs'] * r['val_prog']) + r['extras'] - r['adelantos']
            with st.container():
                st.markdown(f"""
                <div style="background:#1e293b; padding:20px; border-radius:12px; border-left:5px solid #6366f1; margin-bottom:10px;">
                    <div style="color:white; font-size:1.1rem; font-weight:600;">{r['nombre']} • <span style="color:#6366f1;">Total: $ {total:,.0f}</span></div>
                    <div style="color:#64748b; font-size:0.85rem; margin-top:5px;">Base: ${r['base']:,.0f} | Progs: {int(r['progs'])} | Extras: ${r['extras']:,.0f} | Adelantos: -${r['adelantos']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Confirmar Pago: {r['nombre']}", key=f"pay_{r['staff_id']}"):
                    run_query("INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago) VALUES (%s, %s, %s, %s, %s)", 
                              (r['staff_id'], mes, anio, total, date.today()), is_select=False)
                    st.rerun()

# --- MODULO 4: CONFIGURACIÓN (REVISADO PARA EVITAR UNBOUNDLOCALERROR) ---
def mod_config():
    st.title("⚙️ Configuración")
    tab1, tab2, tab3, tab4 = st.tabs(["👤 Staff", "📺 Emisiones", "🤝 Sponsors", "💸 Extras"])
    
    with tab1:
        with st.form("f_staff", clear_on_submit=True):
            st.write("### Miembro")
            col_s1, col_s2 = st.columns(2)
            n, r = col_s1.text_input("Nombre"), col_s2.text_input("Rol")
            b, p = col_s1.number_input("Base ($)", min_value=0), col_s2.number_input("Pago x Prog ($)", min_value=0)
            if st.form_submit_button("Guardar"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (n, r, b, p), is_select=False)
                st.rerun()

    with tab2:
        with st.form("f_em", clear_on_submit=True):
            st.write("### Nueva Emisión")
            col_e1, col_e2 = st.columns(2)
            f, t = col_e1.date_input("Fecha", date.today()), col_e2.text_input("Título")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.rerun()

    with tab3:
        with st.form("f_sp", clear_on_submit=True):
            st.write("### Sponsor")
            emp, mon = st.text_input("Empresa"), st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Cargar"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, date.today()), is_select=False)
                st.rerun()

    with tab4:
        # AQUÍ ESTABA EL ERROR: se usó 'st' como nombre de variable
        staff_list_db = run_query("SELECT id, nombre FROM staff WHERE activo=TRUE")
        if not staff_list_db.empty:
            with st.form("f_extra", clear_on_submit=True):
                st.write("### Bono / Adelanto")
                sid = st.selectbox("Seleccionar Personal", staff_list_db['id'], format_func=lambda x: staff_list_db[staff_list_db['id']==x]['nombre'].values[0])
                cat = st.selectbox("Tipo", ["VIÁTICOS", "BONOS", "ADELANTOS"])
                monto_ex = st.number_input("Monto ($)", min_value=0)
                if st.form_submit_button("Registrar"):
                    run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, monto_ex, date.today(), cat), is_select=False)
                    st.rerun()

# --- MAIN ---
def main():
    # Inicializar tablas necesarias
    run_query("""CREATE TABLE IF NOT EXISTS pagos_sueldos (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), 
        mes INTEGER, anio INTEGER, monto_pagado NUMERIC, fecha_pago DATE, UNIQUE(staff_id, mes, anio)
    );""", is_select=False)
    
    if not check_auth(): return
    
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA</h2>", unsafe_allow_html=True)
        menu_choice = st.radio("Secciones", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("🔒 Salir", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    if menu_choice == "📊 Dashboard": mod_dashboard()
    elif menu_choice == "📋 Asistencia": mod_asistencia()
    elif menu_choice == "💰 Sueldos": mod_sueldos()
    elif menu_choice == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
