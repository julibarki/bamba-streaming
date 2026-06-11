import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Bamba Admin", page_icon="🎙️", layout="wide")

# --- CSS PREMUM SaaS (MINIMALISTA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #0f172a !important; font-family: 'Inter', sans-serif; }
    
    /* Títulos */
    h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    p, label { color: #94a3b8 !important; }

    /* --- CARDS DE ASISTENCIA (ESTILO CONSOLA) --- */
    .stToggle {
        padding-top: 10px;
        justify-content: center;
        display: flex;
    }
    
    .staff-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: all 0.2s ease-in-out;
        margin-bottom: -40px; /* Ajuste para pegar el toggle */
    }

    .staff-box.active {
        border-color: #6366f1;
        background-color: rgba(99, 102, 241, 0.1);
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
    }

    .staff-name { color: #ffffff; font-weight: 600; font-size: 1.1rem; }
    .staff-role { color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }

    /* Botones Pro */
    .stButton > button {
        background: #6366f1 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        width: 100%;
        transition: 0.3s;
    }
    .stButton > button:hover { background: #4f46e5 !important; transform: translateY(-1px); }

    /* Sidebar y Menús */
    [data-testid="stSidebar"] { background-color: #0b0f1a !important; border-right: 1px solid #334155; }
    div[data-baseweb="select"] { background-color: #1e293b !important; border-radius: 10px !important; }
    
    /* Tables */
    .stDataFrame { background-color: #1e293b !important; border-radius: 12px !important; }
    </style>
""", unsafe_allow_html=True)

# --- CAPA DE DATOS ---
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
            pw = st.text_input("Master Password", type="password")
            if st.button("Entrar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Clave Incorrecta")
        return False
    return True

# --- MODULO 1: DASHBOARD ---
def mod_dashboard():
    st.title("📊 Dashboard")
    hoy = date.today()
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Mes", range(1, 13), index=hoy.month-1)
    anio = c2.selectbox("Año", [2024, 2025, 2026], index=0)

    ing = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    pay = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    t_in, t_ga, t_pa = float(ing['t'][0] or 0), float(gas['t'][0] or 0), float(pay['t'][0] or 0)

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos", f"$ {t_in:,.0f}")
    m2.metric("Egresos", f"$ {t_ga + t_pa:,.0f}")
    m3.metric("Caja Real", f"$ {t_in - t_ga - t_pa:,.0f}")

# --- MODULO 2: ASISTENCIA (EL REDISEÑO UX) ---
def mod_asistencia():
    st.markdown("<h2>📋 Asistencia</h2>", unsafe_allow_html=True)
    
    # Selector de Emisión
    em_df = run_query("SELECT id, fecha, titulo_episodio FROM emisiones ORDER BY fecha DESC LIMIT 10")
    if em_df.empty:
        st.info("Cargá programas en Configuración.")
        return
    
    opcs = {r['id']: f"{r['fecha'].strftime('%d/%m')} — {r['titulo_episodio']}" for _, r in em_df.iterrows()}
    eid = st.selectbox("Seleccionar Programa", options=opcs.keys(), format_func=lambda x: opcs[x])
    
    st.write("##")
    
    staff = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
    asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
    list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

    # Grid de tarjetas
    updates = []
    n_cols = 4 # 4 personas por fila
    for i in range(0, len(staff), n_cols):
        cols = st.columns(n_cols)
        for j, (_, s) in enumerate(staff.iloc[i:i+n_cols].iterrows()):
            with cols[j]:
                is_p = s['id'] in list_asist
                # Tarjeta Visual
                st.markdown(f"""
                    <div class="staff-box {'active' if is_p else ''}">
                        <div class="staff-name">{s['nombre']}</div>
                        <div class="staff-role">{s['rol']}</div>
                    </div>
                """, unsafe_allow_html=True)
                # Interruptor pegado a la tarjeta
                pres = st.toggle("Presente", value=is_p, key=f"t_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

    st.write("##")
    if st.button("💾 GUARDAR PRESENTISMO"):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("✅ Asistencia Guardada")

# --- MODULO 3: SUELDOS (VALES DE PAGO) ---
def mod_sueldos():
    st.title("💰 Liquidación")
    c1, c2, _ = st.columns([1,1,2])
    mes, anio = c1.selectbox("Mes", range(1, 13), index=date.today().month-1), c2.selectbox("Año", [2024, 2025], index=0)

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
        st.success("Todo pagado.")
    else:
        for _, r in df.iterrows():
            total = r['base'] + (r['progs'] * r['val_prog']) + r['extras'] - r['adelantos']
            with st.container():
                st.markdown(f"""
                <div style="background:#1e293b; padding:20px; border-radius:12px; border-left:5px solid #6366f1; margin-bottom:10px;">
                    <span style="color:white; font-size:1.2rem; font-weight:600;">{r['nombre']}</span> • 
                    <span style="color:#6366f1; font-weight:600;">TOTAL: $ {total:,.0f}</span>
                    <div style="color:#64748b; font-size:0.8rem; margin-top:5px;">Base: ${r['base']:,.0f} | Progs: {int(r['progs'])} | Extras: ${r['extras']:,.0f} | Adelantos: -${r['adelantos']:,.0f}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Confirmar Pago a {r['nombre']}", key=f"pay_{r['staff_id']}"):
                    run_query("INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago) VALUES (%s, %s, %s, %s, %s)", 
                              (r['staff_id'], mes, anio, total, date.today()), is_select=False)
                    st.rerun()

# --- MODULO 4: CONFIGURACIÓN ---
def mod_config():
    st.title("⚙️ Configuración")
    t1, t2, t3, t4 = st.tabs(["👤 Staff", "📺 Emisiones", "🤝 Sponsors", "💸 Extras"])
    with t1:
        with st.form("f_s"):
            c1, c2 = st.columns(2)
            n, r = c1.text_input("Nombre"), c2.text_input("Rol")
            b, p = c1.number_input("Base ($)", min_value=0), c2.number_input("Pago x Prog ($)", min_value=0)
            if st.form_submit_button("Guardar"):
                run_query("INSERT INTO staff (nombre, rol, sueldo_base, pago_por_programa) VALUES (%s, %s, %s, %s)", (n, r, b, p), is_select=False)
                st.rerun()
    with t2:
        with st.form("f_e"):
            f, t = st.date_input("Fecha", date.today()), st.text_input("Título")
            e = st.selectbox("Estado", ["FINALIZADO", "PROGRAMADO", "EN_VIVO"])
            if st.form_submit_button("Crear"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f, t, e), is_select=False)
                st.rerun()
    with t4:
        with st.form("f_ex"):
            st = run_query("SELECT id, nombre FROM staff WHERE activo=TRUE")
            sid = st.selectbox("Personal", st['id'], format_func=lambda x: st[st['id']==x]['nombre'].values[0])
            cat = st.selectbox("Tipo", ["VIÁTICOS", "BONOS", "ADELANTOS"])
            mon = st.number_input("Monto ($)", min_value=0)
            if st.form_submit_button("Registrar"):
                run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon, date.today(), cat), is_select=False)
                st.rerun()

# --- MAIN ---
def main():
    # Asegurar tabla de pagos
    run_query("CREATE TABLE IF NOT EXISTS pagos_sueldos (id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), mes INTEGER, anio INTEGER, monto_pagado NUMERIC, fecha_pago DATE, UNIQUE(staff_id, mes, anio))", is_select=False)
    if not check_auth(): return
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA</h2>", unsafe_allow_html=True)
        m = st.radio("Menú", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        if st.button("🔒 Salir"): st.session_state.auth = False; st.rerun()
    if m == "📊 Dashboard": mod_dashboard()
    elif m == "📋 Asistencia": mod_asistencia()
    elif m == "💰 Sueldos": mod_sueldos()
    elif m == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
