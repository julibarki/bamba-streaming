import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bamba Admin Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PROFESIONAL (CUSTOM UI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Estilo General del Fondo */
    .main { background-color: #f8fafc; }
    
    /* Tarjetas de Métricas */
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; color: #1e293b !important; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Botones Pro */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background-color: #4f46e5;
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #4338ca; transform: translateY(-2px); }

    /* Inputs y Selectores */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 10px !important;
    }

    /* Header Estilizado */
    .header-box {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* Status Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success { background-color: #dcfce7; color: #166534; }
    .badge-error { background-color: #fee2e2; color: #991b1b; }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS ---
def get_db_connection():
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        return conn
    except:
        st.error("❌ Error de conexión a la base de datos. Verifica tus st.secrets.")
        return None

def run_query(query, params=None, is_select=True):
    conn = get_db_connection()
    if conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            try:
                cur.execute(query, params)
                if is_select:
                    result = cur.fetchall()
                    conn.close()
                    return pd.DataFrame(result)
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                st.error(f"Error: {e}")
                conn.close()
                return None

# --- INICIALIZACIÓN DE TABLAS ---
def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT, rol TEXT, tipo_contrato TEXT, 
        sueldo_base NUMERIC DEFAULT 0, pago_por_programa NUMERIC DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE, titulo_episodio TEXT, estado TEXT, UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id), emision_id INTEGER REFERENCES emisiones(id),
        presente BOOLEAN, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), 
        monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS ingresos (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, monto NUMERIC, fecha DATE, tipo TEXT
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    """
    run_query(ddl, is_select=False)

# --- SEGURIDAD ---
def login():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.image("https://cdn-icons-png.flaticon.com/512/3661/3661313.png", width=100)
            st.title("Admin Login")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Acceder"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD FINANCIERO ---
def view_dashboard():
    st.markdown('<div class="header-box"><h1>📊 Tablero de Control Bamba</h1><p>Resumen financiero del mes en curso</p></div>', unsafe_allow_html=True)
    
    # Filtros de fecha rápidos
    hoy = date.today()
    col_a, col_b = st.columns(2)
    mes = col_a.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = col_b.selectbox("Año", [2024, 2025], index=0)

    # Queries de resumen
    ingresos_df = run_query("SELECT SUM(monto) as total FROM ingresos WHERE EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s", (mes, anio))
    gastos_op_df = run_query("SELECT SUM(monto) as total FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s", (mes, anio))
    
    # Cálculo de Nómina (Simulando lógica real de liquidación)
    nomina_query = """
        SELECT 
            COALESCE(SUM(s.sueldo_base), 0) + 
            COALESCE(SUM(s.pago_por_programa * (SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id WHERE a.staff_id = s.id AND a.presente = TRUE AND EXTRACT(MONTH FROM e.fecha) = %s)), 0) +
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) -
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0)
            as total_nomina
        FROM staff s WHERE s.activo = TRUE
    """
    nomina_df = run_query(nomina_query, (mes, mes, mes))

    total_in = float(ingresos_df['total'][0] or 0)
    total_op = float(gastos_op_df['total'][0] or 0)
    total_nom = float(nomina_df['total_nomina'][0] or 0)
    balance = total_in - total_op - total_nom

    # Métricas Visuales
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos Sponsors", f"$ {total_in:,.2f}")
    m2.metric("Gastos Operativos", f"$ {total_op:,.2f}")
    m3.metric("Costo Nómina", f"$ {total_nom:,.2f}")
    m4.metric("Utilidad Neta", f"$ {balance:,.2f}", delta=f"{balance:,.2f}")

    st.markdown("---")
    
    # Gráfico de flujo
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.subheader("Ingresos vs Egresos")
        fig_data = pd.DataFrame({
            'Categoría': ['Ingresos', 'Operativos', 'Nómina'],
            'Monto': [total_in, total_op, total_nom],
            'Color': ['#10b981', '#ef4444', '#f59e0b']
        })
        fig = px.bar(fig_data, x='Categoría', y='Monto', color='Categoría', 
                     color_discrete_map={'Ingresos':'#10b981', 'Operativos':'#ef4444', 'Nómina':'#f59e0b'})
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO 2: ASISTENCIA RÁPIDA ---
def view_attendance():
    st.subheader("📝 Control de Presentismo")
    
    with st.expander("🚀 Crear Nueva Emisión", expanded=True):
        c1, c2, c3 = st.columns([1,2,1])
        f_emision = c1.date_input("Fecha", date.today())
        t_emision = c2.text_input("Título", placeholder="Ej: Episodio #42 - Invitado Especial")
        e_emision = c3.selectbox("Estado", ["PROGRAMADO", "EN_VIVO", "FINALIZADO"])
        
        if st.button("Crear/Cargar Emisión"):
            run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", 
                      (f_emision, t_emision, e_emision), is_select=False)
            st.success("Emisión lista para marcar asistencia.")

    st.markdown("### Marcar Presentes")
    # Traer última emisión para editar
    ultima_em = run_query("SELECT * FROM emisiones ORDER BY id DESC LIMIT 1")
    if not ultima_em.empty:
        em_id = ultima_em['id'][0]
        st.info(f"Editando: {ultima_em['titulo_episodio'][0]} ({ultima_em['fecha'][0]})")
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        asist_prev = run_query("SELECT staff_id, presente FROM asistencia WHERE emision_id = %s", (int(em_id),))
        
        # Combinar staff con asistencia previa
        if not asist_prev.empty:
            staff = staff.merge(asist_prev, left_on='id', right_on='staff_id', how='left').fillna(False)
        else:
            staff['presente'] = False

        # El Data Editor es la clave de la UX
        edited_staff = st.data_editor(
            staff[['id', 'nombre', 'rol', 'presente']],
            column_config={"presente": st.column_config.CheckboxColumn("¿Asistió?", default=False)},
            disabled=["id", "nombre", "rol"],
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("💾 Guardar Asistencias"):
            for _, row in edited_staff.iterrows():
                run_query("""
                    INSERT INTO asistencia (staff_id, emision_id, presente) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente
                """, (int(row['id']), int(em_id), bool(row['presente'])), is_select=False)
            st.success("Asistencia actualizada.")

# --- MODULO 3: LIQUIDACIÓN DE SUELDOS ---
def view_payroll():
    st.subheader("💰 Liquidación Detallada de Staff")
    
    hoy = date.today()
    mes = st.sidebar.selectbox("Mes Liquidación", range(1, 13), index=hoy.month-1, key="pay_m")
    
    query = """
        SELECT 
            s.nombre, s.rol, s.tipo_contrato,
            s.sueldo_base,
            (SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND EXTRACT(MONTH FROM e.fecha) = %s) as programas_mes,
            s.pago_por_programa,
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'BONOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) as bonos,
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'VIÁTICOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) as viaticos,
            COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) as adelantos
        FROM staff s WHERE s.activo = TRUE
    """
    df = run_query(query, (mes, mes, mes, mes))
    
    if not df.empty:
        df['Pago Programas'] = df['programas_mes'] * df['pago_por_programa']
        df['Total Bruto'] = df['sueldo_base'] + df['Pago Programas'] + df['bonos'] + df['viaticos']
        df['NETO A PAGAR'] = df['Total Bruto'] - df['adelantos']
        
        # Estilo de tabla pro
        st.dataframe(df.style.format({
            'sueldo_base': '$ {:,.0f}', 'Pago Programas': '$ {:,.0f}', 
            'bonos': '$ {:,.0f}', 'viaticos': '$ {:,.0f}', 
            'adelantos': '$ {:,.0f}', 'NETO A PAGAR': '$ {:,.2f}'
        }).background_gradient(subset=['NETO A PAGAR'], cmap='BuGn'), use_container_width=True)

# --- MODULO 4: GESTIÓN DE STAFF Y OTROS (ABM) ---
def view_config():
    st.subheader("⚙️ Configuración del Sistema")
    t_staff, t_ingresos, t_gastos = st.tabs(["👥 Miembros Staff", "🤝 Sponsors/Ingresos", "🏠 Gastos Operativos"])
    
    with t_staff:
        with st.form("alta_staff"):
            c1, c2, c3 = st.columns(3)
            nom = c1.text_input("Nombre Completo")
            rol = c2.text_input("Rol (ej. Conductor)")
            tipo = c3.selectbox("Tipo Contrato", ["FIJO", "POR_PROGRAMA", "HÍBRIDO"])
            c4, c5 = st.columns(2)
            base = c4.number_input("Sueldo Base ($)", min_value=0)
            p_prog = c5.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Añadir al Staff"):
                run_query("INSERT INTO staff (nombre, rol, tipo_contrato, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s, %s)",
                          (nom, rol, tipo, base, p_prog), is_select=False)
                st.success("Staff añadido.")

    with t_ingresos:
        with st.form("nuevo_ingreso"):
            empresa = st.text_input("Nombre del Sponsor / Donante")
            monto = st.number_input("Monto ($)", min_value=0)
            tipo_i = st.selectbox("Tipo", ["Sponsor", "Donante"])
            fecha_i = st.date_input("Fecha de Cobro")
            if st.form_submit_button("Registrar Ingreso"):
                run_query("INSERT INTO ingresos (nombre_empresa, monto, fecha, tipo) VALUES (%s, %s, %s, %s)",
                          (empresa, monto, fecha_i, tipo_i), is_select=False)
                st.success("Ingreso registrado.")

# --- ORQUESTADOR ---
def main():
    if not login():
        return

    init_db()
    
    # Sidebar Navigation Moderna
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3661/3661313.png", width=80)
        st.title("Bamba Streaming")
        st.markdown("---")
        menu = st.radio("Navegación", 
                        ["📊 Dashboard", "📝 Asistencia", "💰 Sueldos", "💸 Gastos/Extras", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión"):
            st.session_state["authenticated"] = False
            st.rerun()

    if menu == "📊 Dashboard": view_dashboard()
    elif menu == "📝 Asistencia": view_attendance()
    elif menu == "💰 Sueldos": view_payroll()
    elif menu == "⚙️ Configuración": view_config()
    elif menu == "💸 Gastos/Extras":
        st.subheader("Extras y Adelantos")
        with st.form("extras"):
            staff_list = run_query("SELECT id, nombre FROM staff")
            id_s = st.selectbox("Personal", staff_list['id'], format_func=lambda x: staff_list[staff_list['id']==x]['nombre'].values[0])
            cat = st.selectbox("Categoría", ["VIÁTICOS", "BONOS", "ADELANTOS"])
            mon = st.number_input("Monto ($)", min_value=0)
            desc = st.text_input("Descripción")
            fec = st.date_input("Fecha")
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s, %s)",
                          (id_s, mon, fec, desc, cat), is_select=False)
                st.success("Registrado correctamente.")

if __name__ == "__main__":
    main()
