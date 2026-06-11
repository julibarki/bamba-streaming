import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS DEFINITIVO (DISEÑO ANTI-ERRORES) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Fondo general */
    .stApp { background-color: #f8fafc !important; }
    
    /* Forzar color de etiquetas (Labels) - ESTO ARREGLA LO QUE SE VEÍA MAL */
    label, .stText, p, span, .stMarkdown {
        color: #1e293b !important;
        font-weight: 500 !important;
    }

    /* Títulos */
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }

    /* Contenedores Blancos (Cards) */
    div[data-testid="stForm"], div.stExpander {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }

    /* Estilo de Inputs (Cuadros de texto y números) */
    input, .stSelectbox div, .stNumberInput div {
        background-color: #ffffff !important;
        color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Botón Principal */
    .stButton > button {
        background-color: #4f46e5 !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        width: 100% !important;
    }
    .stButton > button:hover { background-color: #4338ca !important; }

    /* Diseño de Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px !important;
        background-color: #f1f5f9 !important;
        padding: 8px !important;
        border-radius: 12px !important;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px !important;
        background-color: transparent !important;
        border-radius: 8px !important;
        color: #64748b !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* Métricas (Dashboard) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        padding: 1.5rem !important;
        border-radius: 16px !important;
    }
    [data-testid="stMetricValue"] { color: #1e293b !important; font-weight: 700 !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
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
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,1.2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.title("🎙️ Bamba Admin")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Entrar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- MODULO: DASHBOARD ---
def mod_dashboard():
    st.title("📊 Resumen Mensual")
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", f"$ {total_in:,.0f}")
    m2.metric("Gastos Fijos", f"$ {total_gas:,.0f}")
    m3.metric("Margen Parcial", f"$ {total_in - total_gas:,.0f}")

# --- MODULO: CONFIGURACIÓN ---
def mod_config():
    st.title("⚙️ Configuración")
    t1, t2, t3 = st.tabs(["👥 Equipo (Staff)", "🤝 Sponsors", "🏠 Gastos Fijos"])
    
    with t1:
        st.subheader("Añadir Miembro")
        with st.form("staff_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre Completo")
            rol = col2.text_input("Rol / Función")
            base = col1.number_input("Sueldo Base Mensual ($)", min_value=0)
            pp = col2.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Añadir al Staff"):
                if nombre:
                    run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nombre, rol, base, pp), is_select=False)
                    st.success("Cargado correctamente")
                    st.rerun()

        st.markdown("### Plantel Activo")
        df_staff = run_query("SELECT nombre, rol, sueldo_base, pago_por_programa FROM staff WHERE activo = TRUE")
        st.dataframe(df_staff, use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Cargar Sponsor o Donante")
        with st.form("sponsor_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            emp = c1.text_input("Nombre de la Marca")
            tipo = c2.selectbox("Tipo", ["Sponsor", "Donante"])
            mon = c1.number_input("Monto ($)", min_value=0)
            fec = c2.date_input("Fecha de Cobro", date.today())
            if st.form_submit_button("Registrar Ingreso"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, %s, %s, %s)", (emp, tipo, mon, fec), is_select=False)
                st.success("Registrado")
                st.rerun()

    with t3:
        st.subheader("Gastos Fijos del Estudio")
        with st.form("gasto_form", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Estudio", "Servicios", "Marketing", "Otros"])
            desc = st.text_input("Descripción (Ej: Alquiler Junio)")
            mon_g = st.number_input("Monto ($)", min_value=0)
            fec_g = st.date_input("Fecha", date.today())
            if st.form_submit_button("Cargar Gasto"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s)", (mon_g, fec_g, desc, cat), is_select=False)
                st.success("Gasto cargado")
                st.rerun()

# --- ORQUESTADOR ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.markdown(f"<h2 style='color:#1e293b'>🎙️ Bamba Admin</h2>", unsafe_allow_html=True)
        menu = st.radio("Ir a:", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión"):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "⚙️ Configuración": mod_config()
    elif menu == "💰 Sueldos": 
        st.title("💰 Liquidación")
        st.info("Módulo de sueldos automático")
    elif menu == "📋 Asistencia":
        st.title("📋 Asistencia")
        st.info("Marcá quién vino a cada programa")

if __name__ == "__main__":
    main()
