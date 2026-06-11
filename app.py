import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bamba Admin Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS DEEP DARK SaaS UI (CORREGIDO Y OPTIMIZADO) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Configuración de Fondo */
    .stApp {
        background-color: #0f172a !important;
        font-family: 'Inter', sans-serif;
    }

    /* Limpieza total de Etiquetas (Labels) y Textos */
    label, p, .stMarkdown, [data-testid="stMetricLabel"] {
        background-color: transparent !important;
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        border: none !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Inputs y Selectores */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"], .stNumberInput div {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
        color: white !important;
    }
    
    input, textarea {
        color: #f1f5f9 !important;
        background-color: transparent !important;
    }

    /* Botones Pro con Gradiente Indigo */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        transition: 0.3s all ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4);
    }

    /* Tarjetas KPI (Dashboard) */
    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 2rem !important; font-weight: 700 !important; }

    /* Formularios y Card Containers */
    div[data-testid="stForm"], div.stExpander {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 16px !important;
        padding: 25px !important;
    }

    /* Pestañas (Tabs) Estilizadas */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0f172a !important;
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b !important;
        border-radius: 10px 10px 0 0 !important;
        color: #94a3b8 !important;
        padding: 12px 24px !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #6366f1 !important;
        border-bottom: 2px solid #6366f1 !important;
        background-color: #1e293b !important;
    }

    /* Sidebar Dark */
    [data-testid="stSidebar"] {
        background-color: #0b0f1a !important;
        border-right: 1px solid #334155;
    }

    /* Estilo para las Cards de Staff en Asistencia */
    .staff-card {
        border: 1px solid #334155;
        background-color: #1e293b;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
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
        st.error(f"Error de Base de Datos: {e}")
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
    """
    run_query(ddl, is_select=False)

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        c1, c2, c3 = st.columns([1,1.2,1])
        with col2 := c2:
            st.markdown("<br><br><h1 style='text-align:center;'>🎙️ BAMBA ADMIN</h1>", unsafe_allow_html=True)
            pw = st.text_input("Master Password", type="password")
            if st.button("Ingresar al Sistema"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- MÓDULO 1: DASHBOARD ---
def mod_dashboard():
    st.markdown("<h1>📊 Dashboard General</h1>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Lógica de cálculo
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    query_nom = """
        SELECT 
            SUM(s.sueldo_base) + 
            SUM(s.pago_por_programa * (SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado='FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s)) +
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0)
            as t FROM staff s WHERE s.activo = TRUE
    """
    nom_df = run_query(query_nom, (mes, mes))

    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)
    total_nom = float(nom_df['t'][0] or 0)
    resultado = total_in - total_gas - total_nom

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos", format_ars(total_in))
    m2.metric("Gastos Fijos", format_ars(total_gas))
    m3.metric("Nómina Staff", format_ars(total_nom))
    m4.metric("Utilidad Neta", format_ars(resultado), delta=format_ars(resultado))

    st.markdown("---")
    st.subheader("Flujo de Caja del Mes")
    if total_nom > 0 or total_gas > 0:
        fig = px.pie(values=[total_nom, total_gas, max(0, resultado)], 
                     names=['Nómina', 'Gastos Fijos', 'Ganancia'], 
                     hole=0.6, color_discrete_sequence=['#6366f1', '#f43f5e', '#10b981'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

# --- MÓDULO 2: ASISTENCIA REDISEÑADA ---
def mod_asistencia():
    st.markdown("<h1>📋 Consola de Asistencia</h1>", unsafe_allow_html=True)

    col_em1, col_em2 = st.columns([2, 1])
    with col_em1:
        st.markdown("#### 📺 Seleccionar Emisión")
        em_df = run_query("SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC LIMIT 10")
        if not em_df.empty:
            opcs = {r['id']: f"{r['fecha']} — {r['titulo_episodio']} ({r['estado']})" for _, r in em_df.iterrows()}
            eid = st.selectbox("Emisión activa:", options=opcs.keys(), format_func=lambda x: opcs[x], label_visibility="collapsed")
            current_em = em_df[em_df['id'] == eid].iloc[0]
        else:
            st.warning("No hay emisiones creadas.")
            eid = None

    with col_em2:
        st.markdown("#### ➕ Nueva Emisión")
        with st.popover("Crear Programa", use_container_width=True):
            with st.form("quick_em", clear_on_submit=True):
                f = st.date_input("Fecha", date.today())
                t = st.text_input("Título")
                e = st.selectbox("Estado", ["PROGRAMADO", "EN_VIVO", "FINALIZADO"])
                if st.form_submit_button("Crear"):
                    run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                    st.rerun()

    if eid:
        st.write("---")
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
        asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
        list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

        col_t1, col_t2 = st.columns([3, 1])
        col_t1.markdown(f"### 👥 Staff para: <span style='color:#6366f1'>{current_em['titulo_episodio']}</span>", unsafe_allow_html=True)
        if col_t2.button("✅ Todos Presentes"):
            for _, s in staff.iterrows():
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (s['id'], eid, True), is_select=False)
            st.rerun()

        updates = []
        cols = st.columns(4)
        for i, (_, s) in enumerate(staff.iterrows()):
            with cols[i % 4]:
                is_present = s['id'] in list_asist
                border = "#6366f1" if is_present else "#334155"
                bg = "rgba(99, 102, 241, 0.15)" if is_present else "transparent"
                st.markdown(f"""<div class="staff-card" style="border-color: {border}; background-color: {bg};">
                    <div style="color: white; font-weight: 700;">{s['nombre']}</div>
                    <div style="color: #94a3b8; font-size: 0.8rem;">{s['rol']}</div>
                </div>""", unsafe_allow_html=True)
                pres = st.toggle("Presente", value=is_present, key=f"t_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

        if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
            for sid, p in updates:
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
            st.success("✅ Asistencia Guardada.")
            st.balloons()

# --- MÓDULO 3: SUELDOS ---
def mod_sueldos():
    st.markdown("<h1>💰 Liquidación de Staff</h1>", unsafe_allow_html=True)
    mes = st.sidebar.selectbox("Mes", range(1, 13), index=date.today().month-1)
    
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
        st.dataframe(df.style.format({'Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}', 'Extras (+)': '$ {:,.0f}', 'Adelantos (-)': '$ {:,.0f}', 'A PAGAR': '$ {:,.0f}'}).background_gradient(subset=['A PAGAR'], cmap='YlGn'), use_container_width=True)

# --- MÓDULO 4: CONFIGURACIÓN COMPLETA ---
def mod_config():
    st.markdown("<h1>⚙️ Configuración</h1>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👤 Staff", "🤝 Sponsors", "🏠 Gastos Fijos", "💸 Extras"])
    
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
        with st.form("f_spon", clear_on_submit=True):
            st.write("### Cargar Sponsor")
            c1, c2 = st.columns(2)
            emp = c1.text_input("Empresa")
            mon = c2.number_input("Monto ($)", min_value=0)
            fec = c1.date_input("Fecha", date.today())
            if st.form_submit_button("Cargar Ingreso"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, fec), is_select=False)
                st.success("Registrado.")

    with t3:
        with st.form("f_ga_fi", clear_on_submit=True):
            st.write("### Gastos Operativos (Alquiler, Estudio, Internet)")
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Categoría", ["ESTUDIO", "MARKETING", "SERVICIOS", "OTROS"])
            mon = c2.number_input("Monto ($)", min_value=0)
            desc = c1.text_input("Descripción (Ej: Alquiler de Estudio)")
            if st.form_submit_button("Guardar Gasto"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s)", (mon, date.today(), desc, cat), is_select=False)
                st.success("Gasto guardado.")

    with t4:
        st.write("### Cargar Bonos o Adelantos")
        staff_list = run_query("SELECT id, nombre FROM staff WHERE activo = TRUE")
        if not staff_list.empty:
            with st.form("f_extra", clear_on_submit=True):
                sid = st.selectbox("Personal", staff_list['id'], format_func=lambda x: staff_list[staff_list['id']==x]['nombre'].values[0])
                cat = st.selectbox("Tipo", ["VIÁTICOS", "BONOS", "ADELANTOS"])
                mon = st.number_input("Monto ($)", min_value=0)
                if st.form_submit_button("Cargar Movimiento"):
                    run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                    st.success("Registrado.")

# --- MAIN ---
def main():
    init_db()
    if not check_auth(): return
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA ADMIN</h2>", unsafe_allow_html=True)
        menu = st.radio("Secciones", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("Cerrar Sesión"):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
