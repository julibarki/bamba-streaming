import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin Pro", page_icon="🎙️", layout="wide")

# --- CSS DEEP DARK SaaS UI ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { background-color: #0f172a !important; font-family: 'Inter', sans-serif; }
    label, p, [data-testid="stMetricLabel"] p { color: #94a3b8 !important; font-size: 0.9rem !important; }
    h1, h2, h3, h4 { color: #ffffff !important; font-weight: 700 !important; }
    div[data-baseweb="input"], div[data-baseweb="select"], .stNumberInput div { background-color: #1e293b !important; border: 1px solid #334155 !important; border-radius: 10px !important; }
    input { color: #f1f5f9 !important; }
    .stButton > button { background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important; color: white !important; border-radius: 12px !important; font-weight: 600 !important; width: 100%; }
    div[data-testid="stMetric"] { background-color: #1e293b !important; border: 1px solid #334155 !important; border-radius: 16px !important; }
    [data-testid="stMetricValue"] div { color: #ffffff !important; font-weight: 700 !important; }
    .staff-card { border: 1px solid #334155; background-color: #1e293b; padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 10px; }
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
        st.error(f"Error: {e}")
        return pd.DataFrame()

def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT, rol TEXT, sueldo_base NUMERIC DEFAULT 0, pago_por_programa NUMERIC DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE, titulo_episodio TEXT, estado TEXT, UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id), emision_id INTEGER REFERENCES emisiones(id), presente BOOLEAN, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), monto NUMERIC, fecha DATE, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS ingresos_sponsors (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, tipo TEXT, monto NUMERIC, fecha DATE
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS pagos_sueldos (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), mes INTEGER, anio INTEGER, monto_pagado NUMERIC, fecha_pago DATE, UNIQUE(staff_id, mes, anio)
    );
    """
    run_query(ddl, is_select=False)

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        c1, c2, c3 = st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center;'>🎙️ BAMBA ADMIN</h1>", unsafe_allow_html=True)
            pw = st.text_input("Master Password", type="password")
            if st.button("Ingresar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- MODULO DASHBOARD ---
def mod_dashboard():
    st.markdown("<h1>📊 Dashboard General</h1>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    nom_df = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)
    total_nom = float(nom_df['t'][0] or 0) # Lo realmente pagado

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos Cobrados", format_ars(total_in))
    m2.metric("Gastos Operativos", format_ars(total_gas))
    m3.metric("Nómina Pagada", format_ars(total_nom))
    m4.metric("Caja Real", format_ars(total_in - total_gas - total_nom))

# --- MODULO ASISTENCIA ---
def mod_asistencia():
    st.markdown("<h1>📋 Consola de Asistencia</h1>", unsafe_allow_html=True)
    em_df = run_query("SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if em_df.empty:
        st.warning("Cargá una emisión en Configuración.")
        return
    
    opcs = {r['id']: f"{r['fecha']} — {r['titulo_episodio']} ({r['estado']})" for _, r in em_df.iterrows()}
    eid = st.selectbox("Seleccionar Emisión:", options=opcs.keys(), format_func=lambda x: opcs[x])
    
    staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
    asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
    list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

    updates = []
    cols = st.columns(4)
    for i, (_, s) in enumerate(staff.iterrows()):
        with cols[i % 4]:
            is_p = s['id'] in list_asist
            st.markdown(f"""<div class="staff-card" style="border-color: {'#6366f1' if is_p else '#334155'};">
                <div style="color: white; font-weight: 700;">{s['nombre']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">{s['rol']}</div>
            </div>""", unsafe_allow_html=True)
            pres = st.toggle("Presente", value=is_p, key=f"t_{eid}_{s['id']}", label_visibility="collapsed")
            updates.append((s['id'], pres))

    if st.button("💾 GUARDAR CAMBIOS", type="primary"):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("Asistencia guardada.")

# --- MODULO SUELDOS (REDISEÑADO) ---
def mod_sueldos():
    st.markdown("<h1>💰 Gestión de Pagos (Sueldos)</h1>", unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=date.today().month-1)
    anio = c2.selectbox("Año", [2024, 2025, 2026], index=0)

    tab_pendientes, tab_historial = st.tabs(["⏳ Pendientes de Pago", "✅ Historial de Pagos"])

    with tab_pendientes:
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
        df = run_query(query, (mes, anio, mes, anio, mes, anio, mes, anio))

        if df.empty:
            st.success(f"🎉 ¡Todo pagado en {mes}/{anio}!")
        else:
            df["Total"] = df["base"] + (df["progs"] * df["val_prog"]) + df["extras"] - df["adelantos"]
            
            for _, row in df.iterrows():
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"""
                        **{row['nombre']}** ({row['rol']})  
                        Base: {format_ars(row['base'])} | Progs: {row['progs']} ({format_ars(row['progs']*row['val_prog'])}) | Extras: {format_ars(row['extras'])} | Adelantos: -{format_ars(row['adelantos'])}
                        #### TOTAL: {format_ars(row['Total'])}
                        """)
                    with col_btn:
                        st.write("##")
                        if st.button(f"Confirmar Pago", key=f"pay_{row['staff_id']}"):
                            run_query("""
                                INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (row['staff_id'], mes, anio, row['Total'], date.today()), is_select=False)
                            st.success(f"Pago registrado para {row['nombre']}")
                            st.rerun()
                    st.markdown("---")

    with tab_historial:
        hist_query = """
            SELECT s.nombre, s.rol, p.monto_pagado, p.fecha_pago 
            FROM pagos_sueldos p 
            JOIN staff s ON p.staff_id = s.id 
            WHERE p.mes = %s AND p.anio = %s
            ORDER BY p.fecha_pago DESC
        """
        df_hist = run_query(hist_query, (mes, anio))
        if df_hist.empty:
            st.info("No hay registros de pagos para este mes.")
        else:
            st.dataframe(df_hist.style.format({'monto_pagado': '$ {:,.2f}'}), use_container_width=True)

# --- MODULO CONFIGURACIÓN ---
def mod_config():
    st.markdown("<h1>⚙️ Configuración</h1>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👤 Staff", "📺 Emisiones", "🤝 Sponsors", "🏠 Gastos"])
    
    with t1:
        with st.form("f_staff", clear_on_submit=True):
            st.write("### Alta Staff")
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre")
            rol = c2.text_input("Rol")
            base = c1.number_input("Sueldo Base ($)", min_value=0)
            pp = c2.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Guardar"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nom, rol, base, pp), is_select=False)
                st.success("Cargado.")

    with t2:
        with st.form("f_em", clear_on_submit=True):
            st.write("### Nueva Emisión")
            col1, col2 = st.columns(2)
            f = col1.date_input("Fecha", date.today())
            t = col2.text_input("Título Episodio")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear Programa"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.success("Creado.")

    with t4:
        with st.form("f_ga_fi", clear_on_submit=True):
            st.write("### Cargar Gasto Fijo")
            c1, c2 = st.columns(2)
            mon = c1.number_input("Monto ($)", min_value=0)
            desc = c2.text_input("Descripción")
            if st.form_submit_button("Guardar Gasto"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, 'Fijo')", (mon, date.today(), desc), is_select=False)
                st.success("Gasto guardado.")

# --- MAIN ---
def main():
    init_db()
    if not check_auth(): return
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA ADMIN</h2>", unsafe_allow_html=True)
        menu = st.radio("Menú", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("🔒 Cerrar Sesión"): st.session_state.auth = False; st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
