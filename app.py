import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin | Dark", page_icon="🎙️", layout="wide")

# --- CSS DEEP DARK MODE (SaaS LOOK) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Fondo y Colores Base */
    :root {
        --bg-main: #0f172a;
        --bg-card: #1e293b;
        --text-main: #f1f5f9;
        --text-muted: #94a3b8;
        --accent: #6366f1;
    }

    .stApp { background-color: var(--bg-main) !important; font-family: 'Inter', sans-serif; }
    
    /* Forzar textos a blanco/gris claro */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricLabel"] {
        color: var(--text-main) !important;
    }
    small, .stCaption { color: var(--text-muted) !important; }

    /* Sidebar Dark */
    [data-testid="stSidebar"] {
        background-color: #0b0f1a !important;
        border-right: 1px solid #334155;
    }

    /* Tarjetas y Contenedores */
    div[data-testid="stMetric"], div[data-testid="stForm"], div.stExpander, .stDataFrame {
        background-color: var(--bg-card) !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2) !important;
    }
    
    /* Inputs Estilizados */
    input, .stSelectbox div, .stNumberInput div, textarea {
        background-color: #0f172a !important;
        color: white !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }

    /* Botones Premium */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4);
    }

    /* Tabs (Pestañas) Dark */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b !important;
        border-radius: 10px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted) !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #334155 !important;
        color: var(--accent) !important;
        border-radius: 7px;
    }

    /* Ajuste de Tablas (Dataframes) para Dark */
    [data-testid="stTable"] { color: var(--text-main); }
    
    /* Metric Value */
    [data-testid="stMetricValue"] { color: #ffffff !important; }

    </style>
""", unsafe_allow_html=True)

# --- UTILIDADES ---
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
        st.error(f"Error DB: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,1.2,1])
        with col2:
            st.markdown("<br><br><h1 style='text-align:center;'>🎙️ Bamba Admin</h1>", unsafe_allow_html=True)
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Ingresar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.title("📊 Resumen Ejecutivo")
    
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Lógica de Datos
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos Totales", format_ars(total_in))
    m2.metric("Gastos Operativos", format_ars(total_gas))
    balance = total_in - total_gas
    m3.metric("Margen Operativo", format_ars(balance), delta=format_ars(balance))

    st.markdown("---")
    st.subheader("Flujo de Caja")
    if total_in > 0 or total_gas > 0:
        fig = px.pie(values=[total_in, total_gas], names=['Ingresos', 'Egresos'], 
                     hole=0.7, color_discrete_sequence=['#10b981', '#f43f5e'])
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
        st.plotly_chart(fig, use_container_width=True)

# --- MODULO 2: ASISTENCIA ---
def mod_asistencia():
    st.title("📋 Control de Asistencia")
    
    with st.expander("🆕 Registrar Nueva Emisión"):
        with st.form("new_em", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f = col1.date_input("Fecha", date.today())
            t = col2.text_input("Título del Episodio")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear Programa"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.success("Emisión creada.")

    st.write("### Marcar Presentismo")
    em_df = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 5")
    if not em_df.empty:
        sel = st.selectbox("Seleccionar Emisión", em_df['id'], format_func=lambda x: f"{em_df[em_df['id']==x]['fecha'].values[0]} - {em_df[em_df['id']==x]['titulo_episodio'].values[0]}")
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (sel,))
        list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

        # Grilla de selección
        updates = []
        cols = st.columns(3)
        for i, (idx, s) in enumerate(staff.iterrows()):
            with cols[i % 3]:
                pres = st.toggle(f"{s['nombre']}", value=(s['id'] in list_asist), key=f"s_{s['id']}")
                updates.append((s['id'], pres))
        
        if st.button("Guardar Cambios de Asistencia"):
            for sid, p in updates:
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, sel, p), is_select=False)
            st.success("Asistencia actualizada.")

# --- MODULO 3: LIQUIDACIÓN DE SUELDOS ---
def mod_sueldos():
    st.title("💰 Liquidación de Staff")
    mes = st.sidebar.selectbox("Mes", range(1, 13), index=date.today().month-1)
    
    query = """
        SELECT 
            s.nombre as "Personal", s.rol as "Rol",
            CAST(s.sueldo_base AS FLOAT) as "Base",
            CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
             WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado = 'FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s) AS FLOAT) as "Progs",
            CAST(s.pago_por_programa AS FLOAT) as "Valor Prog",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Bonos/Extra",
            CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s), 0) AS FLOAT) as "Adelantos"
        FROM staff s WHERE s.activo = TRUE
    """
    df = run_query(query, (mes, mes, mes))
    
    if not df.empty:
        df["Pago x Prog"] = df["Progs"] * df["Valor Prog"]
        df["Total Bruto"] = df["Base"] + df["Pago x Prog"] + df["Bonos/Extra"]
        df["NETO A PAGAR"] = df["Total Bruto"] - df["Adelantos"]
        
        st.dataframe(
            df.style.format({
                'Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago x Prog': '$ {:,.0f}',
                'Bonos/Extra': '$ {:,.0f}', 'Adelantos': '$ {:,.0f}', 'NETO A PAGAR': '$ {:,.0f}'
            }).background_gradient(subset=['NETO A PAGAR'], cmap='Greens'),
            use_container_width=True
        )

# --- MODULO 4: CONFIGURACIÓN ---
def mod_config():
    st.title("⚙️ Configuración")
    t1, t2, t3, t4 = st.tabs(["👥 Staff", "🤝 Sponsors", "🏠 Gastos Fijos", "💸 Cargar Extras"])
    
    with t1:
        with st.form("f_staff"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre Completo")
            rol = c2.text_input("Rol")
            base = c1.number_input("Sueldo Base ($)", min_value=0)
            pp = c2.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Añadir al Staff"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nom, rol, base, pp), is_select=False)
                st.success("Personal añadido.")

    with t2:
        with st.form("f_spon"):
            c1, c2 = st.columns(2)
            emp = c1.text_input("Sponsor")
            mon = c2.number_input("Monto ($)", min_value=0)
            fec = c1.date_input("Fecha", date.today())
            if st.form_submit_button("Cargar Sponsor"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, fec), is_select=False)
                st.success("Ingreso cargado.")

    with t4:
        st.write("### Cargar Bonos o Adelantos")
        staff_list = run_query("SELECT id, nombre FROM staff WHERE activo = TRUE")
        if not staff_list.empty:
            with st.form("f_extra"):
                sid = st.selectbox("Personal", staff_list['id'], format_func=lambda x: staff_list[staff_list['id']==x]['nombre'].values[0])
                cat = st.selectbox("Categoría", ["VIÁTICOS", "BONOS", "ADELANTOS"])
                mon = st.number_input("Monto ($)", min_value=0)
                if st.form_submit_button("Registrar Movimiento"):
                    run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                    st.success("Registrado.")

# --- MAIN ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA ADMIN</h2>", unsafe_allow_html=True)
        menu = st.radio("Navegación", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
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
