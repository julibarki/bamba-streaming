import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin | Premium", page_icon="🎙️", layout="wide")

# --- CSS DEEP DARK (CLEAN VERSION - SIN ERRORES VISUALES) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Configuración Base */
    .stApp {
        background-color: #0f172a !important;
        font-family: 'Inter', sans-serif;
    }

    /* Limpieza de Etiquetas (Labels) - ARREGLA EL ERROR DE LA FOTO */
    label {
        background-color: transparent !important;
        color: #94a3b8 !important; /* Gris suave para labels */
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        margin-bottom: 5px !important;
        border: none !important;
    }

    /* Input Fields (Text, Number, Select) */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    
    input, textarea {
        color: #f1f5f9 !important;
        background-color: transparent !important;
    }

    /* Dropdown de los Selectboxes */
    div[data-baseweb="popover"] {
        background-color: #1e293b !important;
        color: white !important;
    }

    /* Botones Premium */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: 0.3s all ease;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.4);
    }

    /* Tarjetas de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 15px !important;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; }

    /* Formularios y Card Containers */
    div[data-testid="stForm"], div.stExpander {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }

    /* Tabs (Pestañas) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0f172a !important;
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b !important;
        border-radius: 8px 8px 0 0 !important;
        color: #94a3b8 !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #6366f1 !important;
        border-bottom: 2px solid #6366f1 !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0b0f1a !important;
        border-right: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# --- UTILIDADES DE NEGOCIO ---
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
            st.markdown("<br><br><h1 style='text-align:center; color:white;'>🎙️ Bamba Admin</h1>", unsafe_allow_html=True)
            pw = st.text_input("Contraseña Maestra", type="password", key="login_pw")
            if st.button("Ingresar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.markdown("<h2 style='color:white;'>📊 Resumen Ejecutivo</h2>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    # Query de Nómina Real
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
    m1.metric("Ingresos Sponsors", format_ars(total_in))
    m2.metric("Gastos Fijos", format_ars(total_gas))
    m3.metric("Nómina Staff", format_ars(total_nom))
    balance = total_in - total_gas - total_nom
    m4.metric("Utilidad Neta", format_ars(balance), delta=format_ars(balance))

# --- MODULO 2: ASISTENCIA ---
def mod_asistencia():
    st.markdown("<h2 style='color:white;'>📋 Control de Asistencia</h2>", unsafe_allow_html=True)
    
    with st.expander("🆕 Registrar Nueva Emisión"):
        with st.form("new_em", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f = col1.date_input("Fecha", date.today())
            t = col2.text_input("Título del Episodio", placeholder="Ej: Episodio #45")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear Programa"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.success("✅ Emisión creada.")

    st.write("---")
    em_df = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 5")
    if not em_df.empty:
        opciones = {r['id']: f"{r['fecha']} - {r['titulo_episodio']}" for _, r in em_df.iterrows()}
        sel = st.selectbox("Seleccionar Emisión para Presentismo", options=opciones.keys(), format_func=lambda x: opciones[x])
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (sel,))
        list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

        updates = []
        cols = st.columns(3)
        for i, (idx, s) in enumerate(staff.iterrows()):
            with cols[i % 3]:
                pres = st.toggle(f"{s['nombre']}", value=(s['id'] in list_asist), key=f"staff_{s['id']}")
                updates.append((s['id'], pres))
        
        if st.button("Guardar Cambios de Asistencia", type="primary", use_container_width=True):
            for sid, p in updates:
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, sel, p), is_select=False)
            st.success("✅ Asistencia actualizada.")

# --- MODULO 3: SUELDOS (LA GESTIÓN CLAVE) ---
def mod_sueldos():
    st.markdown("<h2 style='color:white;'>💰 Liquidación de Staff</h2>", unsafe_allow_html=True)
    mes = st.sidebar.selectbox("Mes de Pago", range(1, 13), index=date.today().month-1)
    
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
        df["NETO A PAGAR"] = df["Total Bruto"] - df["Adelantos (-)"]
        
        st.dataframe(
            df.style.format({
                'Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}',
                'Extras (+)': '$ {:,.0f}', 'Adelantos (-)': '$ {:,.0f}', 'NETO A PAGAR': '$ {:,.0f}'
            }).background_gradient(subset=['NETO A PAGAR'], cmap='YlGn'),
            use_container_width=True
        )
        st.write(f"### Total a pagar este mes: {format_ars(df['NETO A PAGAR'].sum())}")

# --- MODULO 4: CONFIGURACIÓN ---
def mod_config():
    st.markdown("<h2 style='color:white;'>⚙️ Configuración del Sistema</h2>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👥 Staff", "🤝 Sponsors", "🏠 Gastos Fijos", "💸 Cargar Extras"])
    
    with t1:
        with st.form("f_staff", clear_on_submit=True):
            st.write("### Alta de Miembro")
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nombre Completo")
            rol = c2.text_input("Rol / Función")
            base = c1.number_input("Sueldo Base Mensual ($)", min_value=0)
            pp = c2.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Añadir al Staff"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nom, rol, base, pp), is_select=False)
                st.success("✅ Miembro añadido.")

    with t2:
        with st.form("f_spon", clear_on_submit=True):
            st.write("### Registro de Sponsor")
            c1, c2 = st.columns(2)
            emp = c1.text_input("Empresa Sponsor")
            mon = c2.number_input("Monto del Contrato ($)", min_value=0)
            fec = c1.date_input("Fecha de Cobro", date.today())
            if st.form_submit_button("Cargar Ingreso"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, fec), is_select=False)
                st.success("✅ Ingreso registrado.")

    with t4:
        st.write("### Cargar Bonos, Viáticos o Adelantos")
        staff_list = run_query("SELECT id, nombre FROM staff WHERE activo = TRUE")
        if not staff_list.empty:
            with st.form("f_extra", clear_on_submit=True):
                sid = st.selectbox("Seleccionar Personal", staff_list['id'], format_func=lambda x: staff_list[staff_list['id']==x]['nombre'].values[0])
                cat = st.selectbox("Tipo de Movimiento", ["VIÁTICOS", "BONOS", "ADELANTOS"])
                mon = st.number_input("Monto ($)", min_value=0)
                if st.form_submit_button("Registrar Movimiento"):
                    run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                    st.success("✅ Movimiento registrado.")

# --- MAIN ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.markdown("<h2 style='text-align:center; color:white;'>🎙️ BAMBA ADMIN</h2>", unsafe_allow_html=True)
        menu = st.radio("Secciones", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
