import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bamba Admin | Gestión de Streaming",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DISEÑO UI/UX PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Configuración General */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
    
    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 20px !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    /* Header Corporativo */
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* Botones Pro */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Tablas */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXIÓN A BASE DE DATOS ---
def run_query(query, params=None, is_select=True):
    try:
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if is_select:
                result = cur.fetchall()
                conn.close()
                return pd.DataFrame(result)
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        col1, col2, col3 = st.columns([1,1.2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.title("🎙️ Bamba Login")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Ingresar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Clave incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def view_dashboard():
    st.markdown('<div class="main-header"><h1>📊 Tablero Financiero</h1><p>Control de ingresos, egresos y utilidad neta</p></div>', unsafe_allow_html=True)
    
    hoy = date.today()
    c1, c2 = st.columns([1, 3])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Carga de datos
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)

    # Métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos Totales", f"$ {total_in:,.0f}")
    m2.metric("Gastos Operativos", f"$ {total_gas:,.0f}")
    m3.metric("Resultado Parcial", f"$ {total_in - total_gas:,.0f}", delta=f"{total_in - total_gas:,.0f}")

    st.markdown("---")
    
    if total_in > 0 or total_gas > 0:
        fig = px.pie(values=[total_in, total_gas], names=['Ingresos', 'Gastos'], 
                     hole=0.5, color_discrete_sequence=['#10b981', '#f43f5e'])
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO 2: ASISTENCIA (UX MEJORADA) ---
def view_attendance():
    st.subheader("📝 Control de Asistencia por Emisión")
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.info("Primero crea la emisión:")
        f_em = st.date_input("Fecha Programa", date.today())
        t_em = st.text_input("Título del Episodio", placeholder="Ej: Especial #05")
        if st.button("Registrar / Cargar Emisión"):
            run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, 'PROGRAMADO') ON CONFLICT DO NOTHING", (f_em, t_em), is_select=False)
            st.success("Emisión cargada. Ahora marca el presentismo abajo.")

    st.markdown("---")
    
    # Traer última emisión para cargar asistencia
    ult_em = run_query("SELECT * FROM emisiones ORDER BY id DESC LIMIT 1")
    if not ult_em.empty:
        eid = int(ult_em['id'][0])
        st.subheader(f"Lista para: {ult_em['titulo_episodio'][0]} ({ult_em['fecha'][0]})")
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        
        # Data Editor (La mejor herramienta de UX de Streamlit)
        staff['asistio'] = False
        edited_df = st.data_editor(
            staff, 
            column_config={"id": None, "asistio": st.column_config.CheckboxColumn("¿Presente?", default=False)},
            disabled=["nombre", "rol"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("💾 Guardar Presentismo"):
            for _, row in edited_df.iterrows():
                run_query("""
                    INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s)
                    ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente
                """, (int(row['id']), eid, bool(row['asistio'])), is_select=False)
            st.success("Asistencia guardada correctamente.")

# --- MODULO 3: SUELDOS (CORRECCIÓN DE ERROR MATPLOTLIB) ---
def view_payroll():
    st.subheader("💰 Liquidación Mensual de Staff")
    mes = st.sidebar.selectbox("Mes Liquidación", range(1, 13), index=date.today().month-1)
    
    # Query robusta convirtiendo tipos Decimal a Float para Pandas
    query = """
        SELECT 
            s.nombre as "Personal",
            CAST(s.sueldo_base AS FLOAT) as "Base",
            CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND EXTRACT(MONTH FROM e.fecha) = %s) AS FLOAT) as "Progs",
            CAST(s.pago_por_programa AS FLOAT) as "Valor x Prog",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Extras",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Adelantos"
        FROM staff s WHERE s.activo = TRUE
    """
    df = run_query(query, (mes, mes, mes))
    
    if df.empty:
        st.warning("No hay personal registrado o activo.")
        return

    # Cálculos en Python (Más estable)
    df["Pago Progs"] = df["Progs"] * df["Valor x Prog"]
    df["Total Bruto"] = df["Base"] + df["Pago Progs"] + df["Extras"]
    df["NETO A PAGAR"] = df["Total Bruto"] - df["Adelantos"]

    # Visualización con Estilo (Aquí es donde matplotlib soluciona el error)
    st.dataframe(
        df.style.format({
            'Base': '$ {:,.0f}', 'Valor x Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}',
            'Extras': '$ {:,.0f}', 'Adelantos': '$ {:,.0f}', 'NETO A PAGAR': '$ {:,.0f}'
        }).background_gradient(subset=['NETO A PAGAR'], cmap='Greens'),
        use_container_width=True,
        hide_index=True
    )
    
    total_mes = df["NETO A PAGAR"].sum()
    st.markdown(f"### Total a desembolsar: **$ {total_mes:,.2f}**")

# --- ORQUESTADOR ---
def main():
    if not check_auth(): return

    # Sidebar Pro
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3661/3661313.png", width=80)
        st.title("Bamba Admin")
        st.markdown("---")
        menu = st.radio("Menú", ["📊 Dashboard", "📝 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("Cerrar Sesión"):
            st.session_state.authenticated = False
            st.rerun()

    if menu == "📊 Dashboard": view_dashboard()
    elif menu == "📝 Asistencia": view_attendance()
    elif menu == "💰 Sueldos": view_payroll()
    elif menu == "⚙️ Configuración":
        st.info("Módulo de alta de Staff y Gastos Operativos (ABM)")
        # Aquí puedes poner los formularios de alta del staff que ya tenías

if __name__ == "__main__":
    main()
