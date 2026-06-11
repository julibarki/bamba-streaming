import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bamba Streaming | Gestión Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DISEÑO UI PREMIUM (CSS) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fcfcfd; }
    
    /* Contenedor principal de métricas */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #f0f2f6;
        padding: 1.25rem !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* Header corporativo */
    .header-container {
        background: linear-gradient(95deg, #1e293b 0%, #4338ca 100%);
        padding: 2.5rem;
        border-radius: 24px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.2);
    }

    /* Tablas y Dataframes */
    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid #eef2f6; }
    
    /* Botones Sidebar */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }

    /* Inputs estilizados */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        border-radius: 10px !important;
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
        st.error(f"Error de base de datos: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        c1, c2, c3 = st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.title("🎙️ Bamba Admin")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Ingresar al Sistema", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("❌ Acceso denegado")
        return False
    return True

# --- VISTA: DASHBOARD ---
def mod_dashboard():
    st.markdown('<div class="header-container"><h1>🚀 Dashboard Ejecutivo</h1><p>Resumen de salud financiera y operativa</p></div>', unsafe_allow_html=True)
    
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Datos
    ing = run_query("SELECT SUM(monto) as t FROM ingresos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    total_ing = float(ing['t'][0] or 0)
    total_gas = float(gas['t'][0] or 0)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos Totales", f"$ {total_ing:,.0f}")
    m2.metric("Gastos Operativos", f"$ {total_gas:,.0f}")
    m3.metric("Ebitda Parcial", f"$ {total_ing - total_gas:,.0f}", delta=f"{total_ing - total_gas:,.0f}")

    st.markdown("---")
    if total_ing > 0 or total_gas > 0:
        fig = px.bar(x=['Ingresos', 'Gastos'], y=[total_ing, total_gas], 
                     color=['Ingresos', 'Gastos'], color_discrete_map={'Ingresos':'#10b981','Gastos':'#f43f5e'})
        fig.update_layout(showlegend=False, height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# --- VISTA: SUELDOS (CORREGIDA) ---
def mod_sueldos():
    st.subheader("💰 Liquidación Detallada de Staff")
    mes = st.sidebar.selectbox("Mes Liquidación", range(1, 13), index=date.today().month-1)
    
    # Query robusta convirtiendo a FLOAT para evitar errores de tipos Decimal
    query = """
        SELECT 
            s.nombre as "Nombre", 
            s.rol as "Rol",
            CAST(s.sueldo_base AS FLOAT) as "Sueldo Base",
            CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND EXTRACT(MONTH FROM e.fecha) = %s) AS FLOAT) as "Progs",
            CAST(s.pago_por_programa AS FLOAT) as "Valor Prog",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Bonos/Ext",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Adelantos"
        FROM staff s WHERE s.activo = TRUE
    """
    df = run_query(query, (mes, mes, mes))
    
    if df.empty:
        st.info("No hay personal activo para liquidar en este periodo.")
        return

    # Cálculos en Pandas (Garantiza estabilidad)
    df["Pago Progs"] = df["Progs"] * df["Valor Prog"]
    df["Subtotal"] = df["Sueldo Base"] + df["Pago Progs"] + df["Bonos/Ext"]
    df["NETO A PAGAR"] = df["Subtotal"] - df["Adelantos"]

    # ESTILIZADO PROFESIONAL (Aquí es donde Matplotlib y Jinja2 actúan)
    st.dataframe(
        df.style.format({
            'Sueldo Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}',
            'Bonos/Ext': '$ {:,.0f}', 'Adelantos': '$ {:,.0f}', 'NETO A PAGAR': '$ {:,.0f}'
        }).background_gradient(subset=['NETO A PAGAR'], cmap='YlGn'),
        use_container_width=True,
        hide_index=True
    )
    
    st.success(f"Monto total a desembolsar en el mes: $ {df['NETO A PAGAR'].sum():,.2f}")

# --- VISTA: ASISTENCIA ---
def mod_asistencia():
    st.subheader("📝 Registro de Programas")
    
    with st.expander("🆕 Registrar Nueva Emisión", expanded=True):
        c1, c2, c3 = st.columns([1,2,1])
        f = c1.date_input("Fecha", date.today())
        t = c2.text_input("Título Episodio")
        e = c3.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
        if st.button("Guardar Programa", use_container_width=True):
            if t:
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (f, t, e), is_select=False)
                st.balloons()
                st.success("Programa registrado.")
            else: st.error("El título es obligatorio.")

    st.markdown("---")
    st.subheader("Marcar Presentismo")
    
    # Obtener última emisión para cargar asistencia
    last_em = run_query("SELECT id, titulo_episodio, fecha FROM emisiones ORDER BY id DESC LIMIT 1")
    if not last_em.empty:
        eid = int(last_em['id'][0])
        st.info(f"Cargando staff para: {last_em['titulo_episodio'][0]} ({last_em['fecha'][0]})")
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        
        # Usamos st.data_editor para una UX de "Excel" rápida
        edited_staff = st.data_editor(
            staff, 
            column_config={"id": None, "nombre": "Nombre", "rol": "Rol", "presente": st.column_config.CheckboxColumn("¿Asistió?")},
            use_container_width=True,
            hide_index=True,
            key="asist_editor"
        )
        
        if st.button("💾 Guardar Asistencias", type="primary"):
            # Lógica de guardado masivo
            st.warning("Implementando guardado de datos...")

# --- ORQUESTADOR PRINCIPAL ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/8202/8202951.png", width=80)
        st.title("Bamba ERP")
        st.markdown("<br>", unsafe_allow_html=True)
        menu = st.radio("Navegación", ["📊 Dashboard", "📝 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "📝 Asistencia": mod_asistencia()
    else: st.info("Módulo de configuración: Aquí puedes dar de alta staff, sponsors y gastos operativos.")

if __name__ == "__main__":
    main()
