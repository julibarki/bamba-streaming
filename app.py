import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS PREMIUM (PROTECCIÓN TOTAL MODO OSCURO/CLARO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .main { background-color: #f4f7fb; font-family: 'Inter', sans-serif; }
    
    /* Estilo de Tarjetas KPI */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e1e4e8 !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02) !important;
    }
    
    /* Forzar visibilidad de texto en KPIs */
    [data-testid="stMetricLabel"] > div { color: #64748b !important; font-size: 14px !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] > div { color: #1e293b !important; font-size: 28px !important; }

    /* Encabezado Principal */
    .app-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
    }

    /* Botones y Formularios */
    .stButton > button {
        border-radius: 10px;
        background-color: #4f46e5;
        color: white;
        font-weight: 600;
        border: none;
        transition: 0.3s;
    }
    .stButton > button:hover { background-color: #4338ca; color: white; }
    
    div[data-testid="stForm"] {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #e1e4e8;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f8fafc;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE BASE DE DATOS ---
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

# Inicialización de Tablas (Por seguridad)
def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT, rol TEXT, sueldo_base NUMERIC DEFAULT 0, pago_por_programa NUMERIC DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE, titulo_episodio TEXT, estado TEXT DEFAULT 'PROGRAMADO', UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id), emision_id INTEGER REFERENCES emisiones(id), presente BOOLEAN DEFAULT FALSE, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS ingresos_sponsors (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, tipo TEXT, monto NUMERIC, fecha DATE
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    """
    run_query(ddl, is_select=False)

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,1.2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.title("🎙️ Bamba Admin")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Entrar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.markdown('<div class="app-header"><h1>📊 Dashboard Financiero</h1><p>Resumen de salud del negocio</p></div>', unsafe_allow_html=True)
    
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Carga de datos reales
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    # Cálculo de nómina automática
    query_nom = """
        SELECT SUM(s.sueldo_base) + 
               SUM(s.pago_por_programa * (SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado='FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s))
               as t FROM staff s WHERE s.activo = TRUE
    """
    nom_df = run_query(query_nom, (mes,))

    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)
    total_nom = float(nom_df['t'][0] or 0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos", f"$ {total_in:,.0f}")
    m2.metric("Gastos Fijos", f"$ {total_gas:,.0f}")
    m3.metric("Nómina Estimada", f"$ {total_nom:,.0f}")
    utilidad = total_in - total_gas - total_nom
    m4.metric("Utilidad Neta", f"$ {utilidad:,.0f}", delta=f"{utilidad:,.0f}")

    st.markdown("---")
    st.subheader("Ingresos y Gastos del Mes")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Detalle de Ingresos:**")
        st.dataframe(run_query("SELECT nombre_empresa, tipo, monto, fecha FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s", (mes,)), use_container_width=True)
    with col_b:
        st.write("**Detalle de Gastos Fijos:**")
        st.dataframe(run_query("SELECT categoria, descripcion, monto, fecha FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s", (mes,)), use_container_width=True)

# --- MODULO 2: SUELDOS ---
def mod_sueldos():
    st.title("💰 Liquidación de Staff")
    mes = st.sidebar.selectbox("Mes Liquidación", range(1, 13), index=date.today().month-1)
    
    query = """
        SELECT 
            s.nombre as "Personal", s.rol as "Rol",
            CAST(s.sueldo_base AS FLOAT) as "Base",
            CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado = 'FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s) AS FLOAT) as "Progs",
            CAST(s.pago_por_programa AS FLOAT) as "Valor Prog",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Extras (+)",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Adelantos (-)"
        FROM staff s WHERE s.activo = TRUE
    """
    df = run_query(query, (mes, mes, mes))
    
    if not df.empty:
        df["Pago Progs"] = df["Progs"] * df["Valor Prog"]
        df["Total Bruto"] = df["Base"] + df["Pago Progs"] + df["Extras (+)"]
        df["A PAGAR"] = df["Total Bruto"] - df["Adelantos (-)"]
        
        st.dataframe(
            df.style.format({
                'Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}',
                'Extras (+)': '$ {:,.0f}', 'Adelantos (-)': '$ {:,.0f}', 'A PAGAR': '$ {:,.0f}'
            }).background_gradient(subset=['A PAGAR'], cmap='Greens'),
            use_container_width=True, hide_index=True
        )

# --- MODULO 3: ASISTENCIA ---
def mod_asistencia():
    st.title("📋 Control de Asistencia")
    with st.expander("➕ Cargar Nueva Emisión (Programa)"):
        c1, c2 = st.columns(2)
        f = c1.date_input("Fecha", date.today())
        t = c2.text_input("Título Episodio")
        e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
        if st.button("Crear Programa"):
            run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (f, t, e), is_select=False)
            st.success("Programa registrado.")

    st.markdown("---")
    em_df = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if not em_df.empty:
        opcs = {r['id']: f"{r['fecha']} - {r['titulo_episodio']}" for _, r in em_df.iterrows()}
        eid = st.selectbox("Seleccionar Programa:", options=opcs.keys(), format_func=lambda x: opcs[x])
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
        list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

        updates = []
        for _, s in staff.iterrows():
            pres = st.checkbox(f"{s['nombre']} ({s['rol']})", value=(s['id'] in list_asist))
            updates.append((s['id'], pres))
        
        if st.button("Guardar Asistencia"):
            for sid, p in updates:
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
            st.success("Asistencia guardada.")

# --- MODULO 4: CONFIGURACIÓN (ABM) ---
def mod_config():
    st.markdown('<div class="app-header"><h1>⚙️ Configuración</h1><p>Gestión de Staff, Sponsors y Gastos Fijos</p></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["👥 Staff", "🤝 Sponsors e Ingresos", "🏠 Gastos Operativos Fijos"])
    
    with t1:
        st.subheader("Gestión del Equipo")
        with st.form("form_staff"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre Completo")
            rol = c2.text_input("Rol en el programa")
            base = c1.number_input("Sueldo Base Mensual ($)", min_value=0)
            pp = c2.number_input("Pago por cada Programa ($)", min_value=0)
            if st.form_submit_button("Añadir al Staff"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nom, rol, base, pp), is_select=False)
                st.success("Miembro cargado.")
        
        st.write("---")
        st.write("**Lista de Staff Activo:**")
        st.dataframe(run_query("SELECT nombre, rol, sueldo_base, pago_por_programa FROM staff WHERE activo = TRUE"), use_container_width=True)

    with t2:
        st.subheader("Registro de Sponsors y Donantes")
        with st.form("form_sponsors"):
            c1, c2 = st.columns(2)
            empresa = c1.text_input("Nombre de la Marca / Persona")
            tipo = c2.selectbox("Tipo de Ingreso", ["Sponsor", "Donante", "Otro"])
            monto = c1.number_input("Monto acordado ($)", min_value=0)
            f_ing = c2.date_input("Fecha de pago", date.today())
            if st.form_submit_button("Registrar Ingreso"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, %s, %s, %s)", (empresa, tipo, monto, f_ing), is_select=False)
                st.success("Ingreso registrado correctamente.")
        
        st.write("---")
        st.write("**Historial de Ingresos:**")
        st.dataframe(run_query("SELECT fecha, nombre_empresa, tipo, monto FROM ingresos_sponsors ORDER BY fecha DESC"), use_container_width=True)

    with t3:
        st.subheader("Gastos Operativos (Estudio, Alquiler, etc.)")
        with st.form("form_gastos"):
            c1, c2 = st.columns(2)
            categoria = c1.selectbox("Categoría", ["Estudio", "Servicios", "Marketing", "Limpieza", "Otros"])
            monto_g = c2.number_input("Monto del Gasto ($)", min_value=0)
            desc = c1.text_input("Descripción (Ej: Pago Alquiler Junio)")
            f_gas = c2.date_input("Fecha de gasto", date.today())
            if st.form_submit_button("Registrar Gasto Fijo"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s)", (monto_g, f_gas, desc, categoria), is_select=False)
                st.success("Gasto registrado.")

        st.write("---")
        st.write("**Historial de Gastos Operativos:**")
        st.dataframe(run_query("SELECT fecha, categoria, descripcion, monto FROM gastos_operativos ORDER BY fecha DESC"), use_container_width=True)

# --- ORQUESTADOR ---
def main():
    init_db() # Asegura que las tablas existan
    if not check_auth(): return

    with st.sidebar:
        st.title("🎙️ Bamba ERP")
        menu = st.radio("Menú", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión"):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
