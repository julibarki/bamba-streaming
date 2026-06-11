import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
from datetime import date
import hmac

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS PREMIUM (CORREGIDO PARA TODO MODO DE COLOR) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Configuración de Fondo y Fuentes */
    .main { background-color: #f4f7fb; font-family: 'Inter', sans-serif; }
    
    /* Tarjetas de Métricas (KPIs) */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    
    /* Forzar visibilidad de texto en métricas */
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

    /* Botones Pro */
    .stButton > button {
        border-radius: 10px;
        background-color: #4f46e5;
        color: white;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: 0.3s;
    }
    .stButton > button:hover { background-color: #4338ca; border: none; color: white; }

    /* Dataframes */
    .stDataFrame { border-radius: 12px; }
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
            if st.button("Entrar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- VISTA: DASHBOARD ---
def mod_dashboard():
    st.markdown('<div class="app-header"><h1>📊 Dashboard Financiero</h1><p>Control total de Bamba Streaming</p></div>', unsafe_allow_html=True)
    
    hoy = date.today()
    c1, c2 = st.columns([1, 4])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c1.selectbox("Año", [2024, 2025, 2026], index=0)

    # Datos rápidos
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    
    total_in = float(ing_df['t'][0] or 0)
    total_gas = float(gas_df['t'][0] or 0)

    # Dashboard Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ingresos", f"$ {total_in:,.0f}")
    m2.metric("Gastos Fijos", f"$ {total_gas:,.0f}")
    
    # Cálculo de nómina en tiempo real
    query_nom = """
        SELECT SUM(s.sueldo_base) + 
               SUM(s.pago_por_programa * (SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id WHERE a.staff_id = s.id AND a.presente = TRUE AND EXTRACT(MONTH FROM e.fecha) = %s))
               as t FROM staff s WHERE s.activo = TRUE
    """
    nom_df = run_query(query_nom, (mes,))
    total_nom = float(nom_df['t'][0] or 0)
    
    m3.metric("Nómina Staff", f"$ {total_nom:,.0f}")
    m4.metric("Utilidad Neta", f"$ {total_in - total_gas - total_nom:,.0f}")

    st.markdown("---")
    st.subheader("Ingresos del Periodo")
    ingresos_lista = run_query("SELECT fecha, nombre_empresa, tipo, monto FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s", (mes,))
    st.dataframe(ingresos_lista, use_container_width=True)

# --- VISTA: SUELDOS (LA GESTIÓN QUE NECESITÁS) ---
def mod_sueldos():
    st.title("💰 Liquidación de Staff")
    st.info("Esta tabla calcula automáticamente el pago sumando programas y extras, y restando adelantos.")
    
    mes = st.sidebar.selectbox("Mes Liquidación", range(1, 13), index=date.today().month-1)
    
    query = """
        SELECT 
            s.id, s.nombre as "Personal", s.rol as "Rol",
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
        
        # Estilizado
        st.dataframe(
            df.style.format({
                'Base': '$ {:,.0f}', 'Valor Prog': '$ {:,.0f}', 'Pago Progs': '$ {:,.0f}',
                'Extras (+)': '$ {:,.0f}', 'Adelantos (-)': '$ {:,.0f}', 'A PAGAR': '$ {:,.0f}'
            }).background_gradient(subset=['A PAGAR'], cmap='Greens'),
            use_container_width=True, hide_index=True
        )

# --- VISTA: ASISTENCIA ---
def mod_asistencia():
    st.title("📋 Control de Presentismo")
    
    with st.expander("➕ Cargar Nueva Emisión (Programa)"):
        col1, col2 = st.columns(2)
        fecha = col1.date_input("Fecha", date.today())
        titulo = col2.text_input("Título Episodio")
        estado = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
        if st.button("Crear Programa"):
            run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (fecha, titulo, estado), is_select=False)
            st.success("Programa registrado.")

    st.markdown("---")
    
    # Selector de emisión para marcar asistencia
    emisiones = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if not emisiones.empty:
        opciones = {row['id']: f"{row['fecha']} - {row['titulo_episodio']}" for _, row in emisiones.iterrows()}
        eid = st.selectbox("Seleccioná el programa para marcar quién vino:", options=opciones.keys(), format_func=lambda x: opciones[x])
        
        staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE")
        asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
        list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

        st.write("Marcar presentes:")
        updates = []
        for _, s in staff.iterrows():
            pres = st.checkbox(f"{s['nombre']} ({s['rol']})", value=(s['id'] in list_asist))
            updates.append((s['id'], pres))
        
        if st.button("Guardar Asistencia"):
            for sid, p in updates:
                run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
            st.success("Asistencia guardada.")

# --- ORQUESTADOR ---
def main():
    if not check_auth(): return

    with st.sidebar:
        st.title("🎙️ Bamba Menu")
        menu = st.radio("Navegación", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.markdown("---")
        if st.button("Cerrar Sesión"):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración":
        st.subheader("Configuración de Sistema")
        t1, t2, t3 = st.tabs(["👥 Staff", "🤝 Sponsors", "🏠 Gastos Fijos"])
        with t1:
            with st.form("alta"):
                c1, c2 = st.columns(2)
                nom = c1.text_input("Nombre")
                rol = c2.text_input("Rol")
                base = c1.number_input("Sueldo Base", min_value=0)
                pp = c2.number_input("Pago por Programa", min_value=0)
                if st.form_submit_button("Cargar Staff"):
                    run_query("INSERT INTO staff (nombre, rol, tipo_contrato, sueldo_base, pago_por_programa) VALUES (%s, %s, 'HÍBRIDO', %s, %s)", (nom, rol, base, pp), is_select=False)
                    st.success("Cargado.")

if __name__ == "__main__":
    main()
