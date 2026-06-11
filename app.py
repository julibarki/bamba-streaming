import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS PROFESIONAL (CLEAN UI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Fondo General y Fuente */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Limpieza de Textos */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: #1e293b !important;
    }

    /* Sidebar - Estilo Elegante */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Botón Cerrar Sesión */
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: 0.2s;
    }

    /* Tarjetas de Métricas (Dashboard) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }

    /* Formularios y Contenedores */
    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 25px !important;
    }

    /* Estilo de las Tablas (Dataframes) */
    .stDataFrame {
        background-color: #ffffff !important;
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
    }

    /* Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #f1f5f9;
        padding: 5px;
        border-radius: 10px;
        gap: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 7px;
        color: #64748b;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
    }

    /* Inputs (Cajas de texto) */
    input, .stSelectbox div {
        border-radius: 6px !important;
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

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,1.2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.title("🎙️ Bamba Admin")
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Ingresar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- MODULO: DASHBOARD ---
def mod_dashboard():
    st.title("📊 Resumen General")
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Datos rápidos
    ing = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    t_in = float(ing['t'][0] or 0)
    t_ga = float(gas['t'][0] or 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", f"$ {t_in:,.0f}")
    m2.metric("Gastos Fijos", f"$ {t_ga:,.0f}")
    m3.metric("Balance Parcial", f"$ {t_in - t_ga:,.0f}")

# --- MODULO: CONFIGURACIÓN ---
def mod_config():
    st.title("⚙️ Configuración")
    t1, t2, t3 = st.tabs(["👤 Staff", "💰 Sponsors", "🏠 Gastos"])
    
    with t1:
        with st.form("staff_form"):
            st.write("### Añadir Miembro")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre Completo")
            rol = c2.text_input("Rol")
            base = c1.number_input("Sueldo Base ($)", min_value=0)
            prog = c2.number_input("Pago por Programa ($)", min_value=0)
            if st.form_submit_button("Guardar Miembro"):
                if nombre:
                    run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nombre, rol, base, prog), is_select=False)
                    st.success("Guardado.")
                    st.rerun()

        st.write("### Plantel Activo")
        df = run_query("SELECT nombre, rol, sueldo_base, pago_por_programa FROM staff WHERE activo = TRUE")
        st.dataframe(df, use_container_width=True)

    with t2:
        with st.form("sponsor_form"):
            st.write("### Cargar Ingreso")
            c1, c2 = st.columns(2)
            emp = c1.text_input("Empresa/Sponsor")
            mon = c2.number_input("Monto ($)", min_value=0)
            fec = c1.date_input("Fecha", date.today())
            if st.form_submit_button("Registrar Sponsor"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, fec), is_select=False)
                st.success("Ingreso registrado.")
                st.rerun()

    with t3:
        with st.form("gasto_form"):
            st.write("### Cargar Gasto Fijo")
            cat = st.selectbox("Categoría", ["Estudio", "Marketing", "Servicios", "Otros"])
            desc = st.text_input("Descripción")
            mon = st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Cargar Gasto"):
                run_query("INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria) VALUES (%s, %s, %s, %s)", (mon, date.today(), desc, cat), is_select=False)
                st.success("Gasto guardado.")
                st.rerun()

# --- ORQUESTADOR ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.markdown("## 🎙️ Bamba Admin")
        menu = st.radio("Navegación:", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "⚙️ Configuración": mod_config()
    elif menu == "💰 Sueldos": 
        st.title("💰 Liquidación")
        st.info("Módulo de cálculo automático de sueldos.")
    elif menu == "📋 Asistencia":
        st.title("📋 Asistencia")
        st.info("Registro de programas y presentes.")

if __name__ == "__main__":
    main()
