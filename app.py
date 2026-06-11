import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
import hmac
from datetime import date
from decimal import Decimal

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bamba Streaming | Gestión Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def local_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        :root {
            --primary: #6366f1;
            --background: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Contenedores de Tarjetas */
        .stMetric {
            background: white;
            padding: 15px !important;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #f1f5f9;
        }
        
        /* Botones Estilizados */
        .stButton>button {
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        /* Encabezados */
        .main-header {
            background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* Estilo para las Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f1f5f9;
            padding: 6px;
            border-radius: 12px;
        }

        .stTabs [data-baseweb="tab"] {
            height: 45px;
            border-radius: 8px;
            background-color: transparent;
            border: none;
            color: #64748b;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background-color: white !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            color: #4f46e5 !important;
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# -----------------------------------------------------------------------------
# 2. LÓGICA DE BASE DE DATOS
# -----------------------------------------------------------------------------
def get_connection():
    try:
        if "DATABASE_URL" in st.secrets:
            return psycopg2.connect(st.secrets["DATABASE_URL"])
        pg = st.secrets["postgres"]
        return psycopg2.connect(
            host=pg["host"], port=pg["port"], dbname=pg["dbname"],
            user=pg["user"], password=pg["password"], sslmode="require"
        )
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def run_query(query, params=None, fetch=False):
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                res = cur.fetchall()
                return pd.DataFrame(res) if res else pd.DataFrame()
            conn.commit()
    finally:
        conn.close()

def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, rol TEXT NOT NULL,
        tipo_contrato TEXT CHECK (tipo_contrato IN ('FIJO', 'POR_PROGRAMA', 'HÍBRIDO')),
        sueldo_base NUMERIC(14,2) DEFAULT 0, pago_por_programa NUMERIC(14,2) DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE NOT NULL, titulo_episodio TEXT NOT NULL,
        estado TEXT CHECK (estado IN ('PROGRAMADO', 'EN_VIVO', 'FINALIZADO')),
        UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id), emision_id INTEGER REFERENCES emisiones(id),
        presente BOOLEAN DEFAULT FALSE, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id),
        monto NUMERIC(14,2), fecha DATE, descripcion TEXT,
        categoria TEXT CHECK (categoria IN ('VIÁTICOS', 'BONOS', 'ADELANTOS'))
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC(14,2), fecha DATE,
        descripcion TEXT, categoria TEXT CHECK (categoria IN ('ESTUDIO', 'SERVICIOS', 'MARKETING'))
    );
    CREATE TABLE IF NOT EXISTS ingresos_sponsors (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, tipo TEXT, monto NUMERIC(14,2), fecha DATE
    );
    """
    run_query(ddl)

# -----------------------------------------------------------------------------
# 3. SEGURIDAD
# -----------------------------------------------------------------------------
def check_password():
    if st.session_state.get("authenticated"):
        return True

    with st.container():
        st.markdown("<div style='text-align: center; padding: 50px;'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/2991/2991201.png", width=80)
        st.title("Bamba Streaming Admin")
        password = st.text_input("Contraseña Maestra", type="password")
        if st.button("Ingresar"):
            if hmac.compare_digest(password, st.secrets["MASTER_PASSWORD"]):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
        st.markdown("</div>", unsafe_allow_html=True)
    return False

# -----------------------------------------------------------------------------
# 4. MÓDULOS DE LA APP
# -----------------------------------------------------------------------------

def mod_asistencia():
    st.header("📋 Registro de Emisión y Asistencia")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        fecha = st.date_input("Fecha del Programa", date.today())
    with col2:
        titulo = st.text_input("Título del Episodio", placeholder="Ej: Especial Lunes #01")
    
    estado = st.select_slider("Estado de la Emisión", options=["PROGRAMADO", "EN_VIVO", "FINALIZADO"])
    
    staff_df = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre", fetch=True)
    
    if staff_df.empty:
        st.warning("No hay staff registrado.")
        return

    st.write("---")
    st.subheader("Lista de Presentismo")
    
    # Check if exists
    emision_existente = run_query("SELECT id FROM emisiones WHERE fecha = %s AND titulo_episodio = %s", (fecha, titulo), fetch=True)
    
    asistencias_actuales = {}
    emision_id = None
    
    if not emision_existente.empty:
        emision_id = emision_existente.iloc[0]['id']
        asist_df = run_query("SELECT staff_id, presente FROM asistencia WHERE emision_id = %s", (emision_id,), fetch=True)
        if not asist_df.empty:
            asistencias_actuales = dict(zip(asist_df['staff_id'], asist_df['presente']))

    # UI Grilla para Staff
    asist_data = []
    cols = st.columns(3)
    for i, row in staff_df.iterrows():
        with cols[i % 3]:
            pres = st.toggle(f"{row['nombre']}", value=asistencias_actuales.get(row['id'], False), key=f"staff_{row['id']}")
            asist_data.append((row['id'], pres))
            st.caption(f"_{row['rol']}_")

    if st.button("💾 Guardar Datos de la Emisión", use_container_width=True, type="primary"):
        # Upsert Emision
        run_query("""
            INSERT INTO emisiones (fecha, titulo_episodio, estado) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (fecha, titulo_episodio) DO UPDATE SET estado = EXCLUDED.estado
        """, (fecha, titulo, estado))
        
        # Get ID
        e_id = run_query("SELECT id FROM emisiones WHERE fecha = %s AND titulo_episodio = %s", (fecha, titulo), fetch=True).iloc[0]['id']
        
        # Upsert Asistencias
        for s_id, pres in asist_data:
            run_query("""
                INSERT INTO asistencia (staff_id, emision_id, presente)
                VALUES (%s, %s, %s)
                ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente
            """, (s_id, e_id, pres))
        st.success("¡Datos guardados correctamente!")

def mod_gastos_extras():
    st.header("💸 Gastos Extras y Adelantos")
    staff_df = run_query("SELECT id, nombre FROM staff WHERE activo = TRUE", fetch=True)
    
    with st.form("form_extras", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            persona = st.selectbox("Personal", options=staff_df['id'].tolist(), format_func=lambda x: staff_df[staff_df['id']==x]['nombre'].values[0])
            categoria = st.selectbox("Categoría", ["VIÁTICOS", "BONOS", "ADELANTOS"])
        with col2:
            monto = st.number_input("Monto ($)", min_value=0.0)
            fecha = st.date_input("Fecha", date.today())
        
        desc = st.text_area("Descripción")
        if st.form_submit_button("Registrar Gasto"):
            run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s, %s)",
                      (persona, monto, fecha, desc, categoria))
            st.success("Registrado.")

def mod_tablero():
    st.header("📊 Tablero Financiero")
    
    # Filtros
    col_f1, col_f2 = st.columns(2)
    year = col_f1.selectbox("Año", [2024, 2025], index=0)
    month = col_f2.selectbox("Mes", list(range(1, 13)), index=date.today().month-1)
    
    # Data Loading
    ingresos = run_query("SELECT SUM(monto) as total FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s", (month, year), fetch=True)
    gastos_op = run_query("SELECT SUM(monto) as total FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s", (month, year), fetch=True)
    
    total_in = float(ingresos['total'][0] or 0)
    total_op = float(gastos_op['total'][0] or 0)
    
    # Cálculo Nómina Complejo
    payroll_query = """
        SELECT 
            s.id, s.nombre, s.sueldo_base, s.pago_por_programa,
            COUNT(a.emision_id) FILTER (WHERE a.presente = TRUE AND e.estado = 'FINALIZADO') as asistencias,
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) as extras,
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) as adelantos
        FROM staff s
        LEFT JOIN asistencia a ON s.id = a.staff_id
        LEFT JOIN emisiones e ON a.emision_id = e.id AND EXTRACT(MONTH FROM e.fecha) = %s AND EXTRACT(YEAR FROM e.fecha) = %s
        WHERE s.activo = TRUE
        GROUP BY s.id
    """
    df_payroll = run_query(payroll_query, (month, month, month, year), fetch=True)
    
    if not df_payroll.empty:
        df_payroll['pago_asistencias'] = df_payroll['asistencias'] * df_payroll['pago_por_programa']
        df_payroll['total_bruto'] = df_payroll['sueldo_base'].astype(float) + df_payroll['pago_asistencias'].astype(float) + df_payroll['extras'].astype(float)
        df_payroll['a_pagar'] = df_payroll['total_bruto'] - df_payroll['adelantos'].astype(float)
        total_nomina = df_payroll['total_bruto'].sum()
    else:
        total_nomina = 0

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ingresos", f"${total_in:,.2f}")
    k2.metric("Operativos", f"${total_op:,.2f}")
    k3.metric("Nómina", f"${total_nomina:,.2f}")
    balance = total_in - total_op - total_nomina
    k4.metric("Balance Neto", f"${balance:,.2f}", delta=f"{balance:,.2f}", delta_color="normal")

    st.write("---")
    
    # Gráfico
    st.subheader("Distribución de Gastos vs Ingresos")
    fig_df = pd.DataFrame({
        "Concepto": ["Ingresos", "Gastos Operativos", "Nómina"],
        "Monto": [total_in, total_op, total_nomina]
    })
    fig = px.bar(fig_df, x="Concepto", y="Monto", color="Concepto", color_discrete_sequence=["#22c55e", "#ef4444", "#f59e0b"])
    st.plotly_chart(fig, use_container_width=True)

    # Tabla Maestra Estilizada
    st.subheader("🧮 Liquidación Detallada")
    if not df_payroll.empty:
        st.dataframe(
            df_payroll[['nombre', 'sueldo_base', 'asistencias', 'pago_asistencias', 'extras', 'adelantos', 'a_pagar']],
            column_config={
                "nombre": "Nombre",
                "sueldo_base": st.column_config.NumberColumn("Sueldo Base", format="$ %.2f"),
                "asistencias": "Prog. Finalizados",
                "pago_asistencias": st.column_config.NumberColumn("Pago x Prog.", format="$ %.2f"),
                "extras": st.column_config.NumberColumn("Bonos/Viáticos", format="$ %.2f"),
                "adelantos": st.column_config.NumberColumn("Adelantos", format="$ %.2f"),
                "a_pagar": st.column_config.ProgressColumn("Total a Liquidar", format="$ %.2f", min_value=0, max_value=float(df_payroll['a_pagar'].max()))
            },
            hide_index=True,
            use_container_width=True
        )

def mod_config():
    st.header("⚙️ Gestión de Datos (ABM)")
    tab_staff, tab_sponsors, tab_op = st.tabs(["Personal", "Sponsors", "Gtos fijos"])
    
    with tab_staff:
        st.subheader("Nuevo Miembro")
        with st.form("add_staff", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            nombre = c1.text_input("Nombre")
            rol = c2.text_input("Rol")
            tipo = c3.selectbox("Contrato", ["FIJO", "POR_PROGRAMA", "HÍBRIDO"])
            
            c4, c5 = st.columns(2)
            base = c4.number_input("Sueldo Base ($)", min_value=0.0)
            por_prog = c5.number_input("Pago por Programa ($)", min_value=0.0)
            
            if st.form_submit_button("Dar de Alta"):
                run_query("INSERT INTO staff (nombre, rol, tipo_contrato, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s, %s)",
                          (nombre, rol, tipo, base, por_prog))
                st.success("Staff agregado.")
                st.rerun()

    with tab_sponsors:
        with st.form("add_sponsor", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            empresa = c1.text_input("Empresa")
            tipo_s = c2.selectbox("Tipo", ["Sponsor", "Donante"])
            monto_s = c3.number_input("Monto ($)", min_value=0.0)
            fecha_s = st.date_input("Fecha de Cobro", date.today())
            if st.form_submit_button("Registrar Ingreso"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, %s, %s, %s)",
                          (empresa, tipo_s, monto_s, fecha_s))
                st.success("Ingreso registrado.")

    with tab_op:
        with st.form("add_op", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Categoría", ["ESTUDIO", "SERVICIOS", "MARKETING"])
            monto_o = c2.number_input("Monto Gasto ($)", min_value=0.0)
            desc_o = st.text_input("Descripción")
            fecha_o = st.date_input("Fecha Gasto", date.today())
            if st.form_submit_button("Registrar Gasto Operativo"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s)",
                          (monto_o, fecha_o, desc_o, cat))
                st.success("Gasto guardado.")

# -----------------------------------------------------------------------------
# 5. MAIN
# -----------------------------------------------------------------------------
def main():
    if not check_password():
        return

    init_db()

    st.markdown("""
        <div class="main-header">
            <h1>🎙️ Bamba Streaming</h1>
            <p>Sistema Integral de Gestión de Producción y Finanzas</p>
        </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("Menu")
        if st.button("Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    t1, t2, t3, t4 = st.tabs(["Asistencia", "Extras", "Finanzas", "Config"])
    with t1: mod_asistencia()
    with t2: mod_gastos_extras()
    with t3: mod_tablero()
    with t4: mod_config()

if __name__ == "__main__":
    main()
