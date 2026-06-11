import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin Pro", page_icon="🎙️", layout="wide")

# --- CSS PREMIUM SaaS (ULTRA-MINIMALIST DARK) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp { background-color: #0b0f1a !important; font-family: 'Inter', sans-serif; }
    
    /* Headers */
    h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; letter-spacing: -0.04em; }
    p, label { color: #94a3b8 !important; }

    /* Dashboard Metrics */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.5) !important;
        border: 1px solid #334155 !important;
        border-radius: 24px !important;
        padding: 25px !important;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 2.4rem !important; font-weight: 800 !important; }

    /* --- NUEVA ASISTENCIA: GRID DE CONSOLA --- */
    .stToggle { margin-top: -15px; }
    .staff-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 10px;
    }
    .staff-card.active {
        border-color: #6366f1;
        background: rgba(99, 102, 241, 0.1);
        box-shadow: 0 0 30px rgba(99, 102, 241, 0.1);
    }
    .staff-name { color: #ffffff; font-weight: 700; font-size: 1.1rem; margin-bottom: 2px; }
    .staff-role { color: #64748b; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; }

    /* Botones y Tabs */
    .stButton > button {
        background: #6366f1 !important;
        color: white !important; border: none !important; border-radius: 14px !important;
        padding: 0.8rem !important; font-weight: 700 !important; width: 100%;
        transition: 0.3s;
    }
    .stButton > button:hover { background: #4f46e5 !important; transform: translateY(-2px); }

    /* Tables y Inputs */
    .stDataFrame { border: 1px solid #334155 !important; border-radius: 20px !important; }
    div[data-baseweb="select"], div[data-baseweb="input"] { background-color: #1e293b !important; border-radius: 12px !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0b0f1a !important; border-right: 1px solid #1e293b; }
    </style>
""", unsafe_allow_html=True)

# --- CAPA DE DATOS ---
def format_ars(val):
    return f"$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
        # En caso de error de columna inexistente, no matamos la app
        return pd.DataFrame()

def init_db():
    # 1. Crear tablas base
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT, rol TEXT, sueldo_base NUMERIC DEFAULT 0, pago_por_programa NUMERIC DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE, titulo_episodio TEXT, estado TEXT, UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id) ON DELETE CASCADE, emision_id INTEGER REFERENCES emisiones(id) ON DELETE CASCADE, 
        presente BOOLEAN, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS ingresos_sponsors (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, tipo TEXT, monto NUMERIC, fecha DATE
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id) ON DELETE CASCADE, monto NUMERIC, fecha DATE, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS pagos_sueldos (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), mes INTEGER, anio INTEGER, 
        monto_pagado NUMERIC, fecha_pago DATE, UNIQUE(staff_id, mes, anio)
    );
    """
    run_query(ddl, is_select=False)
    
    # 2. MIGRACIÓN: Agregar columna metodo_pago si no existe
    migration = "ALTER TABLE pagos_sueldos ADD COLUMN IF NOT EXISTS metodo_pago TEXT DEFAULT 'Efectivo';"
    run_query(migration, is_select=False)

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        _, col, _ = st.columns([1,1.2,1])
        with col:
            st.markdown("<h1 style='text-align:center; margin-top:50px;'>🎙️ BAMBA</h1>", unsafe_allow_html=True)
            pw = st.text_input("Acceso", type="password")
            if st.button("Entrar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.markdown("<h1>📊 Dashboard</h1>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2, _ = st.columns([1, 1, 2])
    mes, anio = c1.selectbox("Mes", range(1, 13), index=hoy.month-1), c2.selectbox("Año", [2024, 2025], index=0)

    # Datos financieros
    ing = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    pay = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    t_in, t_ga, t_pa = float(ing['t'][0] or 0), float(gas['t'][0] or 0), float(pay['t'][0] or 0)
    utilidad = t_in - t_ga - t_pa

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos", format_ars(t_in))
    m2.metric("Gtos. Fijos", format_ars(t_ga))
    m3.metric("Sueldos Pagados", format_ars(t_pa))
    m4.metric("Caja Real", format_ars(utilidad), delta=f"{utilidad:,.0f}")

    st.write("##")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Flujo de Salida")
        if (t_ga + t_pa) > 0:
            fig = px.pie(values=[t_pa, t_ga], names=['Sueldos', 'Operativos'], hole=0.7, 
                         color_discrete_sequence=['#6366f1', '#f43f5e'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.subheader("Ingresos por Sponsor")
        spon_df = run_query("SELECT nombre_empresa, SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s GROUP BY 1", (mes,))
        if not spon_df.empty:
            fig_bar = px.bar(spon_df, x='nombre_empresa', y='t', color_discrete_sequence=['#10b981'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)

# --- MODULO 2: ASISTENCIA (NEW MINIMALIST GRID) ---
def mod_asistencia():
    st.markdown("<h1>📋 Asistencia</h1>", unsafe_allow_html=True)
    em_df = run_query("SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if em_df.empty:
        st.info("Cargá una emisión en Configuración.")
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
                    <div class="staff-card {'active' if is_p else ''}">
                        <div class="staff-name">{s['nombre']}</div>
                        <div class="staff-role">{s['rol']}</div>
                    </div>
                """, unsafe_allow_html=True)
                pres = st.toggle("P", value=is_p, key=f"att_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

    if st.button("💾 GUARDAR ASISTENCIA"):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("Sincronizado.")

# --- MODULO 3: SUELDOS (WITH HISTORY) ---
def mod_sueldos():
    st.markdown("<h1>💰 Sueldos</h1>", unsafe_allow_html=True)
    c1, c2, _ = st.columns([1,1,2])
    mes, anio = c1.selectbox("Mes", range(1, 13), index=date.today().month-1), c2.selectbox("Año", [2024, 2025], index=0)

    t_pend, t_hist = st.tabs(["Pendientes", "Historial de Pagos"])

    with t_pend:
        query = """
            SELECT 
                s.id as staff_id, s.nombre, s.rol, CAST(s.sueldo_base AS FLOAT) as base,
                CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
                 WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado = 'FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s AND EXTRACT(YEAR FROM e.fecha) = %s) AS FLOAT) as progs,
                CAST(s.pago_por_programa AS FLOAT) as val_prog,
                CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as extras,
                CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as adelantos
            FROM staff s
            LEFT JOIN pagos_sueldos ps ON s.id = ps.staff_id AND ps.mes = %s AND ps.anio = %s
            WHERE s.activo = TRUE AND ps.id IS NULL
        """
        df = run_query(query, (mes, anio, mes, anio, mes, anio, mes, anio))

        if df.empty:
            st.success("Sin pagos pendientes.")
        else:
            for _, r in df.iterrows():
                total = r['base'] + (r['progs'] * r['val_prog']) + r['extras'] - r['adelantos']
                if total <= 0: continue
                with st.container():
                    st.markdown(f"""
                    <div style="background:#1e293b; padding:25px; border-radius:20px; border-left:6px solid #6366f1; margin-bottom:15px;">
                        <div style="color:white; font-size:1.2rem; font-weight:700;">{r['nombre']} <span style="float:right; color:#6366f1;">{format_ars(total)}</span></div>
                        <div style="color:#64748b; font-size:0.85rem; margin-top:5px;">Base: {format_ars(r['base'])} | Progs: {int(r['progs'])} | Extras: {format_ars(r['extras'])} | Adelantos: -{format_ars(r['adelantos'])}</div>
                    </div>""", unsafe_allow_html=True)
                    col_p1, col_p2 = st.columns([2,1])
                    metodo = col_p1.selectbox("Forma de Pago", ["Transferencia", "Efectivo"], key=f"met_{r['staff_id']}")
                    if col_p2.button("Confirmar Pago", key=f"p_{r['staff_id']}"):
                        run_query("INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago, metodo_pago) VALUES (%s, %s, %s, %s, %s, %s)", 
                                  (r['staff_id'], mes, anio, total, date.today(), metodo), is_select=False)
                        st.rerun()

    with t_hist:
        hist_df = run_query("SELECT s.nombre, p.monto_pagado, p.fecha_pago, p.metodo_pago FROM pagos_sueldos p JOIN staff s ON p.staff_id = s.id WHERE p.mes = %s AND p.anio = %s ORDER BY p.fecha_pago DESC", (mes, anio))
        if not hist_df.empty:
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay pagos registrados.")

# --- MODULO CONFIGURACIÓN ---
def mod_config():
    st.markdown("<h1>⚙️ Configuración</h1>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👥 Staff", "📺 Emisiones", "🤝 Sponsors", "💸 Extras"])
    with t1:
        st.subheader("Listado y Edición")
        staff_master = run_query("SELECT id, nombre, rol, sueldo_base, pago_por_programa, activo FROM staff ORDER BY nombre ASC")
        if not staff_master.empty:
            edited = st.data_editor(staff_master, column_config={"id": None}, use_container_width=True, num_rows="dynamic")
            if st.button("Guardar Cambios Staff"):
                for _, row in edited.iterrows():
                    if pd.isna(row['id']):
                        run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa, activo) VALUES (%s, %s, %s, %s, %s)", (row['nombre'], row['rol'], row['sueldo_base'], row['pago_por_programa'], row['activo']), is_select=False)
                    else:
                        run_query("UPDATE staff SET nombre=%s, rol=%s, sueldo_base=%s, pago_por_programa=%s, activo=%s WHERE id=%s", (row['nombre'], row['rol'], row['sueldo_base'], row['pago_por_programa'], row['activo'], row['id']), is_select=False)
                st.success("Personal actualizado.")
    with t2:
        with st.form("f_em"):
            f, t = st.date_input("Fecha", date.today()), st.text_input("Título")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear Emisión"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.rerun()
    with t4:
        with st.form("f_ex"):
            st_list = run_query("SELECT id, nombre FROM staff WHERE activo=TRUE")
            sid = st.selectbox("Personal", st_list['id'], format_func=lambda x: st_list[st_list['id']==x]['nombre'].values[0])
            cat = st.selectbox("Tipo", ["BONOS", "ADELANTOS", "VIÁTICOS"])
            mon = st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                st.rerun()

# --- MAIN ---
def main():
    init_db()
    if not check_auth(): return
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA</h2>", unsafe_allow_html=True)
        menu = st.radio("Secciones", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("🔒 Salir"): st.session_state.auth = False; st.rerun()
    
    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
