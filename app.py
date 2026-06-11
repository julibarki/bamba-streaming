import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Bamba Admin",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS MINIMALISTA PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variables y Reset */
    :root {
        --indigo: #6366f1;
        --slate-900: #0f172a;
        --slate-800: #1e293b;
        --slate-700: #334155;
        --slate-400: #94a3b8;
        --emerald: #10b981;
    }

    .stApp { background-color: var(--slate-900) !important; font-family: 'Inter', sans-serif; }
    
    /* Tipografía */
    h1, h2, h3, h4 { color: #ffffff !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    p, label, [data-testid="stMetricLabel"] p { color: var(--slate-400) !important; font-weight: 400; }

    /* Cards Minimalistas */
    div[data-testid="stMetric"], div[data-testid="stForm"], div.stExpander, .stDataFrame {
        background-color: var(--slate-800) !important;
        border: 1px solid var(--slate-700) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: none !important;
    }

    /* Botones de Acción */
    .stButton > button {
        background: var(--indigo) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); opacity: 0.9; }

    /* Estilo de la Consola de Asistencia (Grid Minimalista) */
    .att-card {
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        transition: all 0.3s ease;
        border: 1px solid var(--slate-700);
        margin-bottom: 15px;
    }
    .att-card.present {
        border-color: var(--indigo);
        background-color: rgba(99, 102, 241, 0.1);
    }
    .att-name { color: white; font-weight: 600; font-size: 1.1rem; margin-bottom: 4px; }
    .att-role { color: var(--slate-400); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }

    /* Tarjetas de Sueldo */
    .salary-card {
        background: var(--slate-800);
        padding: 24px;
        border-radius: 16px;
        border-left: 4px solid var(--slate-700);
        margin-bottom: 12px;
    }
    .salary-card.pending { border-left-color: var(--indigo); }
    .salary-total { font-size: 1.8rem; font-weight: 700; color: white; }

    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0b0f1a !important; border-right: 1px solid var(--slate-700); }
    
    /* Inputs */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: var(--slate-900) !important;
        border-radius: 10px !important;
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
        st.error(f"Error DB: {e}")
        return pd.DataFrame()

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        _, c2, _ = st.columns([1,1.2,1])
        with c2:
            st.markdown("<br><br><h1 style='text-align:center;'>🎙️ BAMBA</h1>", unsafe_allow_html=True)
            pw = st.text_input("Clave", type="password")
            if st.button("Ingresar", use_container_width=True):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.markdown("<h2>📊 Dashboard</h2>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c2.selectbox("Año", [2024, 2025, 2026], index=0)

    # Queries resumidas
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    pay_df = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    t_in = float(ing_df['t'][0] or 0)
    t_ga = float(gas_df['t'][0] or 0)
    t_pa = float(pay_df['t'][0] or 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", format_ars(t_in))
    m2.metric("Egresos (Op + Nom)", format_ars(t_ga + t_pa))
    m3.metric("Caja Neta", format_ars(t_in - t_ga - t_pa))

# --- MODULO 2: ASISTENCIA (MINIMALISTA) ---
def mod_asistencia():
    st.markdown("<h2>📋 Asistencia</h2>", unsafe_allow_html=True)
    
    # Selector de Emisión Ultra-limpio
    em_df = run_query("SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if em_df.empty:
        st.info("Carga una emisión en Configuración para empezar.")
        return
    
    opcs = {r['id']: f"{r['fecha'].strftime('%d/%m')} — {r['titulo_episodio']}" for _, r in em_df.iterrows()}
    eid = st.selectbox("Seleccionar Programa", options=opcs.keys(), format_func=lambda x: opcs[x])
    
    st.write("##")
    
    staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
    asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
    list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

    # Grid de tarjetas
    updates = []
    n_cols = 4
    for i in range(0, len(staff), n_cols):
        cols = st.columns(n_cols)
        for j, (_, s) in enumerate(staff.iloc[i:i+n_cols].iterrows()):
            with cols[j]:
                is_p = s['id'] in list_asist
                # Card visual
                st.markdown(f"""
                    <div class="att-card {'present' if is_p else ''}">
                        <div class="att-name">{s['nombre']}</div>
                        <div class="att-role">{s['rol']}</div>
                    </div>
                """, unsafe_allow_html=True)
                # Switch de acción
                pres = st.toggle("Presente", value=is_p, key=f"att_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

    st.write("##")
    if st.button("💾 Guardar Presentismo", use_container_width=True):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("Asistencia actualizada")

# --- MODULO 3: SUELDOS (CLEAN VOUCHERS) ---
def mod_sueldos():
    st.markdown("<h2>💰 Liquidación</h2>", unsafe_allow_html=True)
    
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Mes", range(1, 13), index=date.today().month-1)
    anio = c2.selectbox("Año", [2024, 2025, 2026], index=0)

    t_pend, t_hist = st.tabs(["Pendientes", "Historial"])

    with t_pend:
        query = """
            SELECT 
                s.id as staff_id, s.nombre, s.rol,
                CAST(s.sueldo_base AS FLOAT) as base,
                CAST((SELECT COUNT(*) FROM asistencia a JOIN emisiones e ON a.emision_id = e.id 
                 WHERE a.staff_id = s.id AND a.presente = TRUE AND e.estado = 'FINALIZADO' AND EXTRACT(MONTH FROM e.fecha) = %s AND EXTRACT(YEAR FROM e.fecha) = %s) AS FLOAT) as progs,
                CAST(s.pago_por_programa AS FLOAT) as val_prog,
                CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria != 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as extras,
                CAST(COALESCE((SELECT SUM(monto) FROM gastos_extras WHERE staff_id = s.id AND categoria = 'ADELANTOS' AND EXTRACT(MONTH FROM fecha) = %s AND EXTRACT(YEAR FROM fecha) = %s), 0) AS FLOAT) as adelantos
            FROM staff s
            LEFT JOIN pagos_sueldos ps ON s.id = ps.staff_id AND ps.mes = %s AND ps.anio = %s
            WHERE s.activo = TRUE AND ps.id IS NULL
        """
        df = run_query(query, (mes, anio, mes, anio, mes, anio, mes, anio))

        if df.empty:
            st.markdown("<div style='text-align:center; padding: 40px; color:#94a3b8;'>Todo el equipo ha cobrado este mes.</div>", unsafe_allow_html=True)
        else:
            for _, row in df.iterrows():
                total = row['base'] + (row['progs'] * row['val_prog']) + row['extras'] - row['adelantos']
                if total <= 0: continue # No mostrar si no hay nada que pagar
                
                with st.container():
                    st.markdown(f"""
                        <div class="salary-card pending">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <div style="color:white; font-size:1.2rem; font-weight:600;">{row['nombre']}</div>
                                    <div style="color:var(--indigo); font-size:0.8rem; font-weight:600; text-transform:uppercase;">{row['rol']}</div>
                                    <div style="margin-top:8px; color:var(--slate-400); font-size:0.9rem;">
                                        Base: {format_ars(row['base'])} • 
                                        Progs: {int(row['progs'])} • 
                                        Extras: {format_ars(row['extras'])} • 
                                        Adelantos: -{format_ars(row['adelantos'])}
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="color:var(--slate-400); font-size:0.8rem;">TOTAL A PAGAR</div>
                                    <div class="salary-total">{format_ars(total)}</div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Confirmar Pago para {row['nombre']}", key=f"p_{row['staff_id']}"):
                        run_query("INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago) VALUES (%s, %s, %s, %s, %s)", 
                                  (row['staff_id'], mes, anio, total, date.today()), is_select=False)
                        st.balloons()
                        st.rerun()

    with t_hist:
        df_hist = run_query("SELECT s.nombre, s.rol, p.monto_pagado, p.fecha_pago FROM pagos_sueldos p JOIN staff s ON p.staff_id = s.id WHERE p.mes = %s AND p.anio = %s ORDER BY p.fecha_pago DESC", (mes, anio))
        if not df_hist.empty:
            st.dataframe(df_hist.style.format({'monto_pagado': '$ {:,.2f}'}), use_container_width=True, hide_index=True)
        else:
            st.write("Sin registros en este periodo.")

# --- MODULO CONFIGURACIÓN ---
def mod_config():
    st.markdown("<h2>⚙️ Configuración</h2>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👤 Staff", "📺 Emisiones", "🤝 Sponsors", "🏠 Gastos"])
    
    with t1:
        with st.form("f_staff", clear_on_submit=True):
            st.write("### Miembro")
            c1, c2 = st.columns(2)
            nom, rol = c1.text_input("Nombre"), c2.text_input("Rol")
            base, pp = c1.number_input("Sueldo Base ($)", min_value=0), c2.number_input("Pago x Prog ($)", min_value=0)
            if st.form_submit_button("Añadir"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (nom, rol, base, pp), is_select=False)
                st.rerun()
        st.dataframe(run_query("SELECT nombre, rol, sueldo_base, pago_por_programa FROM staff WHERE activo=TRUE"), use_container_width=True, hide_index=True)

    with t2:
        with st.form("f_em", clear_on_submit=True):
            st.write("### Nueva Emisión")
            c1, c2 = st.columns(2)
            f, t = c1.date_input("Fecha", date.today()), c2.text_input("Título")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.rerun()

    with t3:
        with st.form("f_sp", clear_on_submit=True):
            st.write("### Sponsor")
            emp, mon = st.text_input("Empresa"), st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Cargar"):
                run_query("INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha) VALUES (%s, 'Sponsor', %s, %s)", (emp, mon, date.today()), is_select=False)
                st.rerun()

    with t4:
        with st.form("f_extra", clear_on_submit=True):
            st.write("### Bono / Adelanto")
            staff = run_query("SELECT id, nombre FROM staff WHERE activo=TRUE")
            sid = st.selectbox("Personal", staff['id'], format_func=lambda x: staff[staff['id']==x]['nombre'].values[0])
            cat = st.selectbox("Tipo", ["VIÁTICOS", "BONOS", "ADELANTOS"])
            mon = st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                st.rerun()

# --- MAIN ---
def main():
    # Inicialización de la base (Asegura tabla pagos_sueldos)
    run_query("""CREATE TABLE IF NOT EXISTS pagos_sueldos (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), 
        mes INTEGER, anio INTEGER, monto_pagado NUMERIC, fecha_pago DATE, UNIQUE(staff_id, mes, anio)
    );""", is_select=False)
    
    if not check_auth(): return
    
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA</h2>", unsafe_allow_html=True)
        menu = st.radio("Secciones", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.write("---")
        if st.button("🔒 Salir", use_container_width=True):
            st.session_state.auth = False
            st.rerun()

    if menu == "📊 Dashboard": mod_dashboard()
    elif menu == "📋 Asistencia": mod_asistencia()
    elif menu == "💰 Sueldos": mod_sueldos()
    elif menu == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
