import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import date
import hmac
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Bamba Admin Pro", page_icon="🎙️", layout="wide")

# --- CSS PREMIUM SaaS (DARK & VIBRANT) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .stApp { background-color: #0b0f1a !important; font-family: 'Inter', sans-serif; }
    
    /* Headers y Texto */
    h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; letter-spacing: -0.03em; }
    p, label { color: #94a3b8 !important; }

    /* Dashboard Metrics (Modern Look) */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%) !important;
        border: 1px solid #334155 !important;
        border-radius: 20px !important;
        padding: 25px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
    }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 2.2rem !important; }

    /* Cards de Asistencia Rediseñadas */
    .attendance-card {
        background: #1e293b;
        border: 2px solid #334155;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: 0.3s;
    }
    .attendance-card.active {
        border-color: #6366f1;
        background: rgba(99, 102, 241, 0.15);
        box-shadow: 0 0 20px rgba(99, 102, 241, 0.2);
    }

    /* Botones y Tabs */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        padding: 0.8rem !important; font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #0f172a !important; gap: 10px; }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: #6366f1 !important; border-radius: 10px; }

    /* Inputs y Dataframes */
    div[data-baseweb="select"], div[data-baseweb="input"] { background-color: #1e293b !important; border-radius: 10px !important; }
    .stDataFrame { border: 1px solid #334155 !important; border-radius: 15px !important; overflow: hidden; }
    
    /* Status Badges */
    .badge { padding: 4px 12px; border-radius: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .badge-cash { background: #f59e0b; color: #451a03; }
    .badge-bank { background: #3b82f6; color: #eff6ff; }
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

def init_db():
    ddl = """
    CREATE TABLE IF NOT EXISTS staff (
        id SERIAL PRIMARY KEY, nombre TEXT, rol TEXT, sueldo_base NUMERIC DEFAULT 0, pago_por_programa NUMERIC DEFAULT 0, activo BOOLEAN DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS emisiones (
        id SERIAL PRIMARY KEY, fecha DATE, titulo_episodio TEXT, estado TEXT, UNIQUE(fecha, titulo_episodio)
    );
    CREATE TABLE IF NOT EXISTS asistencia (
        staff_id INTEGER REFERENCES staff(id) ON DELETE CASCADE, emision_id INTEGER REFERENCES emisiones(id) ON DELETE CASCADE, 
        presente BOOLEAN, PRIMARY KEY (staff_id, emision_id)
    );
    CREATE TABLE IF NOT EXISTS ingresos_sponsors (
        id SERIAL PRIMARY KEY, nombre_empresa TEXT, tipo TEXT, monto NUMERIC, fecha DATE
    );
    CREATE TABLE IF NOT EXISTS gastos_operativos (
        id SERIAL PRIMARY KEY, monto NUMERIC, fecha DATE, descripcion TEXT, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS gastos_extras (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id) ON DELETE CASCADE, monto NUMERIC, fecha DATE, categoria TEXT
    );
    CREATE TABLE IF NOT EXISTS pagos_sueldos (
        id SERIAL PRIMARY KEY, staff_id INTEGER REFERENCES staff(id), mes INTEGER, anio INTEGER, 
        monto_pagado NUMERIC, fecha_pago DATE, metodo_pago TEXT, UNIQUE(staff_id, mes, anio)
    );
    """
    run_query(ddl, is_select=False)

# --- SEGURIDAD ---
def check_auth():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        _, col, _ = st.columns([1,1.2,1])
        with col:
            st.markdown("<h1 style='text-align:center;'>🎙️ BAMBA LOGIN</h1>", unsafe_allow_html=True)
            pw = st.text_input("Contraseña Maestra", type="password")
            if st.button("Ingresar"):
                if hmac.compare_digest(pw, st.secrets["MASTER_PASSWORD"]):
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Acceso denegado")
        return False
    return True

# --- MODULO 1: DASHBOARD (COLORFUL & MODERN) ---
def mod_dashboard():
    st.markdown("<h1>📊 Dashboard Ejecutivo</h1>", unsafe_allow_html=True)
    hoy = date.today()
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Periodo Mes", range(1, 13), index=hoy.month-1)
    anio = c2.selectbox("Año", [2024, 2025], index=0)

    # Datos
    ing_df = run_query("SELECT SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    gas_df = run_query("SELECT SUM(monto) as t FROM gastos_operativos WHERE EXTRACT(MONTH FROM fecha)=%s AND EXTRACT(YEAR FROM fecha)=%s", (mes, anio))
    pay_df = run_query("SELECT SUM(monto_pagado) as t FROM pagos_sueldos WHERE mes=%s AND anio=%s", (mes, anio))

    total_in = float(ing_df['t'][0] or 0)
    total_op = float(gas_df['t'][0] or 0)
    total_nom = float(pay_df['t'][0] or 0)
    total_out = total_op + total_nom
    utilidad = total_in - total_out

    # KPIs con colores
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ingresos Totales", format_ars(total_in))
    k2.metric("Egresos (Op + Nom)", format_ars(total_out))
    k3.metric("Nómina Liquidada", format_ars(total_nom))
    k4.metric("Margen Neto", format_ars(utilidad), delta=f"{utilidad:,.0f}")

    st.write("##")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("Distribución de Salida")
        if total_out > 0:
            fig = px.pie(values=[total_nom, total_op], names=['Nómina', 'Operativos'], 
                         hole=0.6, color_discrete_sequence=['#6366f1', '#f43f5e'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        st.subheader("Histórico Mensual (Ingresos)")
        # Query rápida para el gráfico de barras del año
        hist_df = run_query("SELECT EXTRACT(MONTH FROM fecha) as mes, SUM(monto) as t FROM ingresos_sponsors WHERE EXTRACT(YEAR FROM fecha)=%s GROUP BY mes ORDER BY mes", (anio,))
        if not hist_df.empty:
            fig_bar = px.bar(hist_df, x='mes', y='t', color_discrete_sequence=['#10b981'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white', yaxis_title=None, xaxis_title="Mes")
            st.plotly_chart(fig_bar, use_container_width=True)

# --- MODULO 2: ASISTENCIA (ESTILO CONSOLA) ---
def mod_asistencia():
    st.markdown("<h1>📋 Control de Presentismo</h1>", unsafe_allow_html=True)
    
    em_df = run_query("SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC LIMIT 15")
    if em_df.empty:
        st.warning("No hay programas creados. Ir a Configuración.")
        return
    
    opcs = {r['id']: f"{r['fecha'].strftime('%d/%m')} — {r['titulo_episodio']} ({r['estado']})" for _, r in em_df.iterrows()}
    eid = st.selectbox("Seleccionar Emisión Activa", options=opcs.keys(), format_func=lambda x: opcs[x])
    
    st.write("---")
    
    staff_data = run_query("SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre ASC")
    asist_actual = run_query("SELECT staff_id FROM asistencia WHERE emision_id = %s AND presente = TRUE", (eid,))
    list_asist = asist_actual['staff_id'].tolist() if not asist_actual.empty else []

    # Panel de Control Staff
    updates = []
    n_cols = 4
    for i in range(0, len(staff_data), n_cols):
        cols = st.columns(n_cols)
        for j, (_, s) in enumerate(staff_data.iloc[i:i+n_cols].iterrows()):
            with cols[j]:
                is_p = s['id'] in list_asist
                st.markdown(f"""
                    <div class="attendance-card {'active' if is_p else ''}">
                        <div style="color: white; font-weight: 700; font-size: 1.1rem;">{s['nombre']}</div>
                        <div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; margin-top: 5px;">{s['rol']}</div>
                    </div>
                """, unsafe_allow_html=True)
                pres = st.toggle("Presente", value=is_p, key=f"att_{eid}_{s['id']}", label_visibility="collapsed")
                updates.append((s['id'], pres))

    st.write("##")
    if st.button("💾 GUARDAR ASISTENCIA DE HOY", use_container_width=True):
        for sid, p in updates:
            run_query("INSERT INTO asistencia (staff_id, emision_id, presente) VALUES (%s, %s, %s) ON CONFLICT (staff_id, emision_id) DO UPDATE SET presente = EXCLUDED.presente", (sid, eid, p), is_select=False)
        st.success("✅ Datos sincronizados.")
        st.balloons()

# --- MODULO 3: SUELDOS (GESTIÓN DE PAGOS E HISTORIAL) ---
def mod_sueldos():
    st.markdown("<h1>💰 Liquidación de Sueldos</h1>", unsafe_allow_html=True)
    
    c1, c2, _ = st.columns([1, 1, 2])
    mes = c1.selectbox("Mes Liquidar", range(1, 13), index=date.today().month-1)
    anio = c2.selectbox("Año", [2024, 2025], index=0)

    tab_pend, tab_hist = st.tabs(["⏳ Pagos Pendientes", "📜 Historial de Pagos"])

    with tab_pend:
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
        df_pay = run_query(query, (mes, anio, mes, anio, mes, anio, mes, anio))

        if df_pay.empty:
            st.success("¡Excelente! No hay sueldos pendientes para este mes.")
        else:
            for _, r in df_pay.iterrows():
                total = r['base'] + (r['progs'] * r['val_prog']) + r['extras'] - r['adelantos']
                if total <= 0: continue
                
                with st.container():
                    st.markdown(f"""
                    <div style="background:#1e293b; padding:20px; border-radius:15px; border-left:6px solid #6366f1; margin-bottom:15px;">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div style="color:white; font-size:1.2rem; font-weight:700;">{r['nombre']}</div>
                                <div style="color:#64748b; font-size:0.85rem;">Base: {format_ars(r['base'])} | Progs: {int(r['progs'])} | Extras: {format_ars(r['extras'])} | Adelantos: -{format_ars(r['adelantos'])}</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="color:#94a3b8; font-size:0.75rem;">SALDO A LIQUIDAR</div>
                                <div style="color:white; font-size:1.6rem; font-weight:800;">{format_ars(total)}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_p1, c_p2 = st.columns([2, 1])
                    metodo = c_p1.segmented_control("Método de Pago", ["Transferencia", "Efectivo"], default="Transferencia", key=f"met_{r['staff_id']}")
                    if c_p2.button(f"Confirmar Pago", key=f"btn_pay_{r['staff_id']}"):
                        run_query("INSERT INTO pagos_sueldos (staff_id, mes, anio, monto_pagado, fecha_pago, metodo_pago) VALUES (%s, %s, %s, %s, %s, %s)", 
                                  (r['staff_id'], mes, anio, total, date.today(), metodo), is_select=False)
                        st.rerun()

    with tab_hist:
        hist_df = run_query("""
            SELECT s.nombre as "Personal", s.rol as "Rol", p.monto_pagado as "Monto", p.fecha_pago as "Fecha", p.metodo_pago as "Metodo"
            FROM pagos_sueldos p JOIN staff s ON p.staff_id = s.id 
            WHERE p.mes = %s AND p.anio = %s ORDER BY p.fecha_pago DESC
        """, (mes, anio))
        if not hist_df.empty:
            st.dataframe(hist_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aún no hay pagos registrados en este periodo.")

# --- MODULO 4: CONFIGURACIÓN (LISTADO Y EDICIÓN DE STAFF) ---
def mod_config():
    st.markdown("<h1>⚙️ Centro de Configuración</h1>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["👤 Gestión de Staff", "📺 Programación", "🤝 Sponsors", "💸 Adelantos/Extras"])
    
    with t1:
        st.subheader("Listado Maestro de Staff")
        st.write("Podés editar los datos directamente en la tabla (Base, Pago x Prog, etc.)")
        
        staff_master = run_query("SELECT id, nombre, rol, sueldo_base, pago_por_programa, activo FROM staff ORDER BY id DESC")
        if not staff_master.empty:
            # EL DATA EDITOR ES LA CLAVE PARA TU PREGUNTA: permite editar y guardar cambios
            edited_staff = st.data_editor(
                staff_master,
                column_config={
                    "id": None,
                    "sueldo_base": st.column_config.NumberColumn("Sueldo Base ($)", format="$ %d"),
                    "pago_por_programa": st.column_config.NumberColumn("Valor Prog ($)", format="$ %d"),
                    "activo": st.column_config.CheckboxColumn("Activo")
                },
                use_container_width=True,
                num_rows="dynamic"
            )
            if st.button("💾 Guardar Cambios en Staff"):
                # Aquí se procesan los cambios de la tabla editada
                for _, row in edited_staff.iterrows():
                    run_query("""
                        UPDATE staff SET nombre=%s, rol=%s, sueldo_base=%s, pago_por_programa=%s, activo=%s
                        WHERE id=%s
                    """, (row['nombre'], row['rol'], row['sueldo_base'], row['pago_por_programa'], row['activo'], row['id']), is_select=False)
                st.success("✅ Plantel actualizado.")

    with t2:
        with st.form("f_nueva_emision", clear_on_submit=True):
            st.write("### Cargar Nueva Emisión")
            c_e1, c_e2 = st.columns(2)
            f_em = c_e1.date_input("Fecha", date.today())
            t_em = c_e2.text_input("Título Episodio")
            e_em = st.selectbox("Estado Actual", ["PROGRAMADO", "EN_VIVO", "FINALIZADO"])
            if st.form_submit_button("Crear Emisión"):
                run_query("INSERT INTO emisiones (fecha, titulo_episodio, estado) VALUES (%s, %s, %s)", (f_em, t_em, e_em), is_select=False)
                st.success("Registrado.")

    with t4:
        st.subheader("Carga de Bonos o Adelantos")
        staff_list_db = run_query("SELECT id, nombre FROM staff WHERE activo=TRUE")
        if not staff_list_db.empty:
            with st.form("f_extra_pago", clear_on_submit=True):
                sid = st.selectbox("Elegir Miembro", staff_list_db['id'], format_func=lambda x: staff_list_db[staff_list_db['id']==x]['nombre'].values[0])
                cat = st.selectbox("Tipo Movimiento", ["VIÁTICOS", "BONOS", "ADELANTOS"])
                mon_e = st.number_input("Monto en Pesos ($)", min_value=0)
                if st.form_submit_button("Registrar Movimiento"):
                    run_query("INSERT INTO gastos_extras (staff_id, monto, fecha, categoria) VALUES (%s, %s, %s, %s)", (sid, mon_e, date.today(), cat), is_select=False)
                    st.success("Registrado.")

# --- MAIN ---
def main():
    init_db()
    if not check_auth(): return
    
    with st.sidebar:
        st.markdown("<h2 style='text-align:center;'>🎙️ BAMBA ADMIN</h2>", unsafe_allow_html=True)
        m = st.radio("Navegación", ["📊 Dashboard", "📋 Asistencia", "💰 Sueldos", "⚙️ Configuración"])
        st.write("---")
        if st.button("🔒 Salir del Sistema"):
            st.session_state.auth = False
            st.rerun()

    if m == "📊 Dashboard": mod_dashboard()
    elif m == "📋 Asistencia": mod_asistencia()
    elif m == "💰 Sueldos": mod_sueldos()
    elif m == "⚙️ Configuración": mod_config()

if __name__ == "__main__":
    main()
