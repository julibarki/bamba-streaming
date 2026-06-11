# =============================================================================
# BAMBA STREAMING — Sistema de Gestión Financiera y Operativa
# Stack: Python + Streamlit + PostgreSQL (Neon.tech / Supabase)
# =============================================================================

import hmac
from datetime import date

import pandas as pd
import plotly.express as px
import psycopg2
import psycopg2.extras
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bamba Streaming | Gestión",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
CONTRATOS = ["FIJO", "POR_PROGRAMA", "HÍBRIDO"]
ESTADOS_EMISION = ["PROGRAMADO", "EN_VIVO", "FINALIZADO"]
CATEGORIAS_EXTRAS = ["VIÁTICOS", "BONOS", "ADELANTOS"]
CATEGORIAS_OPERATIVOS = ["ESTUDIO", "SERVICIOS", "MARKETING"]
TIPOS_INGRESO = ["Sponsor", "Donante"]

# -----------------------------------------------------------------------------
# ESTILOS CSS PREMIUM (LOOK SAAS CORPORATIVO)
# -----------------------------------------------------------------------------
CSS_PREMIUM = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, p, span, label, input, textarea, button {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.stApp { background-color: #f4f6fb; }

h1, h2, h3, h4, h5, h6 { color: #1e2a4a !important; font-weight: 700 !important; letter-spacing: -0.02em; }

/* Forzar legibilidad de textos sin importar el tema del navegador */
div[data-testid="stWidgetLabel"] p, div[data-testid="stWidgetLabel"] label,
.stRadio label p, .stCheckbox label p, .stToggle label p {
    color: #3b4a6b !important; font-weight: 600 !important;
}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] span {
    color: #1e2a4a !important;
}
div[data-testid="stCaptionContainer"] p { color: #6b7a99 !important; }
div[data-testid="stExpander"] summary p, div[data-testid="stExpander"] summary span {
    color: #1e2a4a !important; font-weight: 600 !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
    background: #ffffff !important; color: #1e2a4a !important;
    border: 1px solid #d4dbe8 !important; border-radius: 10px !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    background: #ffffff !important; color: #1e2a4a !important;
    border-color: #d4dbe8 !important; border-radius: 10px !important;
}
.stSelectbox div[data-baseweb="select"] span { color: #1e2a4a !important; }

/* Tarjetas KPI personalizadas */
.kpi-card {
    background: #ffffff;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 14px rgba(30, 42, 74, 0.08);
    border: 1px solid #e8ecf4;
    margin-bottom: 0.5rem;
}
.kpi-titulo {
    font-size: 0.8rem; font-weight: 600; color: #6b7a99;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.35rem;
}
.kpi-valor { font-size: 1.7rem; font-weight: 800; color: #1e2a4a; }
.kpi-positivo { color: #0e9f6e !important; }
.kpi-negativo { color: #e02424 !important; }

/* Pestañas */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px; background: #ffffff; padding: 6px; border-radius: 14px;
    box-shadow: 0 2px 8px rgba(30, 42, 74, 0.06); border: 1px solid #e8ecf4;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px; padding: 8px 18px; font-weight: 600; color: #6b7a99;
}
.stTabs [aria-selected="true"] {
    background: #1e2a4a !important; color: #ffffff !important;
}

/* Botones */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 10px; font-weight: 600; border: none;
    background: #1e2a4a; color: #ffffff;
    box-shadow: 0 2px 6px rgba(30, 42, 74, 0.25);
    transition: all 0.15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #2d3f6e; color: #ffffff; transform: translateY(-1px);
}

/* Contenedores tipo tarjeta */
div[data-testid="stForm"], div[data-testid="stExpander"] {
    background: #ffffff; border-radius: 16px; border: 1px solid #e8ecf4;
    box-shadow: 0 4px 14px rgba(30, 42, 74, 0.06);
}
div[data-testid="stDataFrame"] {
    border-radius: 14px; overflow: hidden; border: 1px solid #e8ecf4;
    box-shadow: 0 2px 10px rgba(30, 42, 74, 0.05);
}

/* Encabezado principal */
.encabezado-app {
    background: linear-gradient(135deg, #1e2a4a 0%, #34457c 100%);
    border-radius: 18px; padding: 1.4rem 2rem; margin-bottom: 1.2rem;
    box-shadow: 0 6px 20px rgba(30, 42, 74, 0.25);
}
.encabezado-app h1 { color: #ffffff !important; margin: 0; font-size: 1.6rem; }
.encabezado-app p { color: #b9c4e0; margin: 0.2rem 0 0 0; font-size: 0.9rem; }

/* Login */
.login-caja {
    background: #ffffff; border-radius: 20px; padding: 2.2rem;
    box-shadow: 0 10px 35px rgba(30, 42, 74, 0.12); border: 1px solid #e8ecf4;
    text-align: center; margin-top: 2rem;
}
</style>
"""
st.markdown(CSS_PREMIUM, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# UTILIDADES — FORMATO MONEDA ARS
# -----------------------------------------------------------------------------
def formato_ars(valor) -> str:
    """Formatea un número como Pesos Argentinos: $150.000,00"""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        v = 0.0
    signo = "-" if v < 0 else ""
    entero, decimales = f"{abs(v):,.2f}".split(".")
    entero = entero.replace(",", ".")
    return f"{signo}${entero},{decimales}"


def tarjeta_kpi(titulo: str, valor: str, clase_extra: str = "") -> str:
    return (
        f'<div class="kpi-card"><div class="kpi-titulo">{titulo}</div>'
        f'<div class="kpi-valor {clase_extra}">{valor}</div></div>'
    )


# -----------------------------------------------------------------------------
# CAPA DE DATOS — POSTGRESQL (st.secrets + queries parametrizadas)
# -----------------------------------------------------------------------------
def obtener_conexion():
    """Crea una conexión segura usando credenciales de st.secrets."""
    if "DATABASE_URL" in st.secrets:
        return psycopg2.connect(st.secrets["DATABASE_URL"], connect_timeout=10)
    pg = st.secrets["postgres"]
    return psycopg2.connect(
        host=pg["host"],
        port=int(pg.get("port", 5432)),
        dbname=pg["dbname"],
        user=pg["user"],
        password=pg["password"],
        sslmode=pg.get("sslmode", "require"),
        connect_timeout=10,
    )


def ejecutar(query: str, params=None):
    """Ejecuta una sentencia de escritura dentro de una transacción."""
    conn = obtener_conexion()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(query, params)
    finally:
        conn.close()


def consultar(query: str, params=None) -> pd.DataFrame:
    """Ejecuta una consulta de lectura y devuelve un DataFrame."""
    conn = obtener_conexion()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            filas = cur.fetchall()
            return pd.DataFrame(filas) if filas else pd.DataFrame()
    finally:
        conn.close()


DDL_TABLAS = """
CREATE TABLE IF NOT EXISTS staff (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL,
    tipo_contrato TEXT NOT NULL DEFAULT 'POR_PROGRAMA'
        CHECK (tipo_contrato IN ('FIJO', 'POR_PROGRAMA', 'HÍBRIDO')),
    sueldo_base NUMERIC(14,2) NOT NULL DEFAULT 0,
    pago_por_programa NUMERIC(14,2) NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS emisiones (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    titulo_episodio TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PROGRAMADO'
        CHECK (estado IN ('PROGRAMADO', 'EN_VIVO', 'FINALIZADO')),
    UNIQUE (fecha, titulo_episodio)
);

CREATE TABLE IF NOT EXISTS asistencia (
    staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    emision_id INTEGER NOT NULL REFERENCES emisiones(id) ON DELETE CASCADE,
    presente BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (staff_id, emision_id)
);

CREATE TABLE IF NOT EXISTS gastos_extras (
    id SERIAL PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    monto NUMERIC(14,2) NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT,
    categoria TEXT NOT NULL
        CHECK (categoria IN ('VIÁTICOS', 'BONOS', 'ADELANTOS'))
);

CREATE TABLE IF NOT EXISTS gastos_operativos (
    id SERIAL PRIMARY KEY,
    monto NUMERIC(14,2) NOT NULL,
    fecha DATE NOT NULL,
    descripcion TEXT,
    categoria TEXT NOT NULL
        CHECK (categoria IN ('ESTUDIO', 'SERVICIOS', 'MARKETING'))
);

CREATE TABLE IF NOT EXISTS ingresos_sponsors (
    id SERIAL PRIMARY KEY,
    nombre_empresa TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('Sponsor', 'Donante')),
    monto NUMERIC(14,2) NOT NULL,
    fecha DATE NOT NULL
);
"""


def inicializar_base_de_datos():
    """Auto-migración: crea las tablas si no existen (una vez por sesión)."""
    if st.session_state.get("db_inicializada"):
        return
    conn = obtener_conexion()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(DDL_TABLAS)
        st.session_state["db_inicializada"] = True
    finally:
        conn.close()


def guardar_asistencia_transaccional(emision_id, fecha, titulo, estado, asistencias):
    """Bloque transaccional: crea/actualiza la emisión y hace UPSERT de asistencia.

    asistencias: lista de tuplas (staff_id, presente)
    Devuelve el id de la emisión.
    """
    conn = obtener_conexion()
    try:
        with conn, conn.cursor() as cur:
            if emision_id is None:
                cur.execute(
                    """
                    INSERT INTO emisiones (fecha, titulo_episodio, estado)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (fecha, titulo_episodio)
                    DO UPDATE SET estado = EXCLUDED.estado
                    RETURNING id
                    """,
                    (fecha, titulo, estado),
                )
                emision_id = cur.fetchone()[0]
            else:
                cur.execute(
                    "UPDATE emisiones SET estado = %s WHERE id = %s",
                    (estado, emision_id),
                )
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO asistencia (staff_id, emision_id, presente)
                VALUES (%s, %s, %s)
                ON CONFLICT (staff_id, emision_id)
                DO UPDATE SET presente = EXCLUDED.presente
                """,
                [(sid, emision_id, pres) for sid, pres in asistencias],
            )
        return emision_id
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# MÓDULO DE SEGURIDAD — LOGIN CON CLAVE MAESTRA
# -----------------------------------------------------------------------------
def pantalla_login():
    col_izq, col_centro, col_der = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown(
            """
            <div class="login-caja">
                <h1>🎙️ Bamba Streaming</h1>
                <p style="color:#6b7a99; margin-top:0.3rem;">
                    Sistema de Gestión Financiera y Operativa
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("formulario_login"):
            clave = st.text_input(
                "Contraseña maestra", type="password",
                placeholder="Ingresá la contraseña de acceso",
            )
            enviar = st.form_submit_button("🔓 Ingresar al sistema", use_container_width=True)
        if enviar:
            clave_maestra = str(st.secrets.get("MASTER_PASSWORD", ""))
            if clave_maestra and hmac.compare_digest(clave, clave_maestra):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Verificá la clave e intentá nuevamente.")


# -----------------------------------------------------------------------------
# MÓDULO 1 — CONTROL DE ASISTENCIA
# -----------------------------------------------------------------------------
def modulo_asistencia():
    st.subheader("📋 Control de Asistencia por Emisión")

    df_staff = consultar(
        "SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre"
    )
    if df_staff.empty:
        st.warning("⚠️ Todavía no hay staff cargado. Agregá miembros en la pestaña **Configuración**.")
        return

    df_emisiones = consultar(
        "SELECT id, fecha, titulo_episodio, estado FROM emisiones ORDER BY fecha DESC, id DESC"
    )

    modo = st.radio(
        "¿Qué querés hacer?",
        ["➕ Crear nueva emisión", "✏️ Editar una emisión existente"],
        horizontal=True,
    )

    emision_id = None
    asistencia_previa = {}

    if modo == "➕ Crear nueva emisión":
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            fecha_emision = st.date_input("Fecha de la emisión", value=date.today(), format="DD/MM/YYYY")
        with col2:
            titulo_emision = st.text_input("Título del episodio", placeholder="Ej: Bamba Streaming #45 — Especial Invitados")
        with col3:
            estado_emision = st.selectbox("Estado", ESTADOS_EMISION)
    else:
        if df_emisiones.empty:
            st.info("No hay emisiones registradas todavía. Creá la primera con la opción «Crear nueva emisión».")
            return
        etiquetas = {
            int(fila["id"]): f"{fila['fecha'].strftime('%d/%m/%Y')} — {fila['titulo_episodio']} ({fila['estado']})"
            for _, fila in df_emisiones.iterrows()
        }
        emision_id = st.selectbox(
            "Seleccioná la emisión",
            options=list(etiquetas.keys()),
            format_func=lambda x: etiquetas[x],
        )
        fila_emision = df_emisiones[df_emisiones["id"] == emision_id].iloc[0]
        fecha_emision = fila_emision["fecha"]
        titulo_emision = fila_emision["titulo_episodio"]
        estado_emision = st.selectbox(
            "Estado de la emisión",
            ESTADOS_EMISION,
            index=ESTADOS_EMISION.index(fila_emision["estado"]),
        )
        df_asistencia = consultar(
            "SELECT staff_id, presente FROM asistencia WHERE emision_id = %s",
            (emision_id,),
        )
        if not df_asistencia.empty:
            asistencia_previa = dict(zip(df_asistencia["staff_id"], df_asistencia["presente"]))

    st.markdown("##### 👥 Lista del staff — marcá presentes y ausentes")
    clave_contexto = emision_id if emision_id is not None else "nueva"
    toggles = {}
    for _, persona in df_staff.iterrows():
        sid = int(persona["id"])
        c1, c2, c3 = st.columns([3, 2, 1.2])
        c1.markdown(f"**{persona['nombre']}**")
        c2.markdown(f"<span style='color:#6b7a99'>{persona['rol']}</span>", unsafe_allow_html=True)
        toggles[sid] = c3.toggle(
            "Presente",
            value=bool(asistencia_previa.get(sid, False)),
            key=f"toggle_asistencia_{clave_contexto}_{sid}",
        )

    presentes = sum(1 for v in toggles.values() if v)
    st.caption(f"✅ Presentes: {presentes} de {len(toggles)}")

    if st.button("💾 Guardar Control de Asistencia", use_container_width=True):
        if modo == "➕ Crear nueva emisión" and not titulo_emision.strip():
            st.error("❌ El título del episodio no puede estar vacío.")
            return
        try:
            guardar_asistencia_transaccional(
                emision_id,
                fecha_emision,
                titulo_emision.strip() if isinstance(titulo_emision, str) else titulo_emision,
                estado_emision,
                list(toggles.items()),
            )
            st.success("✅ Control de asistencia guardado correctamente.")
        except Exception as error:
            st.error(f"❌ Ocurrió un error al guardar la asistencia: {error}")


# -----------------------------------------------------------------------------
# MÓDULO 2 — GASTOS EXTRAS DEL STAFF
# -----------------------------------------------------------------------------
def modulo_gastos_extras():
    st.subheader("💸 Gastos Extras del Staff")
    st.caption("Viáticos y bonos **suman** a la liquidación. Los adelantos **se descuentan** del total a pagar del mes.")

    df_staff = consultar(
        "SELECT id, nombre, rol FROM staff WHERE activo = TRUE ORDER BY nombre"
    )
    if df_staff.empty:
        st.warning("⚠️ Todavía no hay staff cargado. Agregá miembros en la pestaña **Configuración**.")
        return

    nombres = {int(f["id"]): f"{f['nombre']} ({f['rol']})" for _, f in df_staff.iterrows()}

    with st.form("formulario_gasto_extra", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            staff_sel = st.selectbox(
                "Miembro del staff",
                options=list(nombres.keys()),
                format_func=lambda x: nombres[x],
            )
            categoria = st.selectbox("Categoría", CATEGORIAS_EXTRAS)
        with col2:
            monto = st.number_input("Monto (ARS)", min_value=0.0, step=1000.0, format="%.2f")
            fecha_gasto = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
        descripcion = st.text_input("Descripción", placeholder="Ej: Viáticos traslado al estudio")
        enviar = st.form_submit_button("➕ Registrar Gasto Extra", use_container_width=True)

    if enviar:
        if monto <= 0:
            st.error("❌ El monto debe ser mayor a cero.")
        else:
            try:
                ejecutar(
                    """
                    INSERT INTO gastos_extras (staff_id, monto, fecha, descripcion, categoria)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (staff_sel, monto, fecha_gasto, descripcion.strip(), categoria),
                )
                st.success(f"✅ Gasto extra de {formato_ars(monto)} registrado para {nombres[staff_sel]}.")
            except Exception as error:
                st.error(f"❌ Error al registrar el gasto: {error}")

    st.markdown("##### 🧾 Últimos gastos extras registrados")
    df_recientes = consultar(
        """
        SELECT ge.id, ge.fecha, s.nombre, ge.categoria, ge.monto, ge.descripcion
        FROM gastos_extras ge
        JOIN staff s ON s.id = ge.staff_id
        ORDER BY ge.fecha DESC, ge.id DESC
        LIMIT 15
        """
    )
    if df_recientes.empty:
        st.info("Todavía no hay gastos extras registrados.")
    else:
        df_recientes = df_recientes.copy()
        df_recientes["monto"] = df_recientes["monto"].astype(float).map(formato_ars)
        df_recientes["fecha"] = pd.to_datetime(df_recientes["fecha"]).dt.strftime("%d/%m/%Y")
        df_recientes.columns = ["ID", "Fecha", "Nombre", "Categoría", "Monto", "Descripción"]
        st.dataframe(df_recientes, use_container_width=True, hide_index=True)

        with st.expander("🗑️ Eliminar un gasto extra (correcciones)"):
            id_eliminar = st.selectbox("ID del gasto a eliminar", df_recientes["ID"].tolist())
            if st.button("Eliminar gasto seleccionado"):
                ejecutar("DELETE FROM gastos_extras WHERE id = %s", (id_eliminar,))
                st.success("✅ Gasto eliminado correctamente.")
                st.rerun()


# -----------------------------------------------------------------------------
# MÓDULO 3 — TABLERO FINANCIERO Y REPORTES
# -----------------------------------------------------------------------------
def modulo_tablero():
    st.subheader("📊 Tablero Financiero y Reportes")

    hoy = date.today()
    col_anio, col_mes, _ = st.columns([1, 1, 2])
    with col_anio:
        anios_disponibles = list(range(hoy.year + 1, 2023, -1))
        anio = st.selectbox("Año", anios_disponibles, index=anios_disponibles.index(hoy.year))
    with col_mes:
        mes_nombre = st.selectbox("Mes", MESES, index=hoy.month - 1)
    mes = MESES.index(mes_nombre) + 1

    # --- Ingresos del mes ---
    df_ingresos = consultar(
        """
        SELECT nombre_empresa, tipo, monto, fecha FROM ingresos_sponsors
        WHERE EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
        """,
        (anio, mes),
    )
    total_ingresos = float(df_ingresos["monto"].astype(float).sum()) if not df_ingresos.empty else 0.0

    # --- Gastos operativos del mes ---
    df_operativos = consultar(
        """
        SELECT categoria, SUM(monto) AS total FROM gastos_operativos
        WHERE EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
        GROUP BY categoria
        """,
        (anio, mes),
    )
    total_operativos = float(df_operativos["total"].astype(float).sum()) if not df_operativos.empty else 0.0

    # --- Nómina: staff + asistencia a emisiones FINALIZADAS + gastos extras ---
    df_staff = consultar(
        """
        SELECT id, nombre, rol, tipo_contrato, sueldo_base, pago_por_programa
        FROM staff WHERE activo = TRUE ORDER BY nombre
        """
    )
    df_programas = consultar(
        """
        SELECT a.staff_id, COUNT(*) AS programas
        FROM asistencia a
        JOIN emisiones e ON e.id = a.emision_id
        WHERE a.presente = TRUE
          AND e.estado = 'FINALIZADO'
          AND EXTRACT(YEAR FROM e.fecha) = %s
          AND EXTRACT(MONTH FROM e.fecha) = %s
        GROUP BY a.staff_id
        """,
        (anio, mes),
    )
    df_extras = consultar(
        """
        SELECT staff_id,
               SUM(CASE WHEN categoria <> 'ADELANTOS' THEN monto ELSE 0 END) AS extras,
               SUM(CASE WHEN categoria = 'ADELANTOS' THEN monto ELSE 0 END) AS adelantos
        FROM gastos_extras
        WHERE EXTRACT(YEAR FROM fecha) = %s AND EXTRACT(MONTH FROM fecha) = %s
        GROUP BY staff_id
        """,
        (anio, mes),
    )

    if df_staff.empty:
        df_liquidacion = pd.DataFrame()
        total_nomina = 0.0
    else:
        df_liq = df_staff.copy()
        df_liq["sueldo_base"] = df_liq["sueldo_base"].astype(float)
        df_liq["pago_por_programa"] = df_liq["pago_por_programa"].astype(float)

        if not df_programas.empty:
            df_liq = df_liq.merge(df_programas, left_on="id", right_on="staff_id", how="left").drop(columns=["staff_id"])
        else:
            df_liq["programas"] = 0
        if not df_extras.empty:
            df_liq = df_liq.merge(df_extras, left_on="id", right_on="staff_id", how="left").drop(columns=["staff_id"])
        else:
            df_liq["extras"] = 0.0
            df_liq["adelantos"] = 0.0

        df_liq["programas"] = df_liq["programas"].fillna(0).astype(int)
        df_liq["extras"] = df_liq["extras"].fillna(0).astype(float)
        df_liq["adelantos"] = df_liq["adelantos"].fillna(0).astype(float)

        df_liq["pago_programas"] = df_liq["programas"] * df_liq["pago_por_programa"]
        df_liq["devengado"] = df_liq["sueldo_base"] + df_liq["pago_programas"] + df_liq["extras"]
        df_liq["total_pagar"] = df_liq["devengado"] - df_liq["adelantos"]

        # Costo real de nómina del mes (los adelantos ya están incluidos en lo devengado)
        total_nomina = float(df_liq["devengado"].sum())
        df_liquidacion = df_liq

    balance_neto = total_ingresos - total_operativos - total_nomina

    # --- Tarjetas KPI ---
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(tarjeta_kpi("💰 Total Ingresos", formato_ars(total_ingresos)), unsafe_allow_html=True)
    k2.markdown(tarjeta_kpi("🏢 Gastos Operativos", formato_ars(total_operativos)), unsafe_allow_html=True)
    k3.markdown(tarjeta_kpi("👥 Costo de Nómina", formato_ars(total_nomina)), unsafe_allow_html=True)
    clase_balance = "kpi-positivo" if balance_neto >= 0 else "kpi-negativo"
    k4.markdown(tarjeta_kpi("📈 Balance Neto", formato_ars(balance_neto), clase_balance), unsafe_allow_html=True)

    st.divider()

    # --- Gráficos interactivos ---
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.markdown(f"##### Ingresos vs. Egresos — {mes_nombre} {anio}")
        df_barras = pd.DataFrame(
            {
                "Concepto": ["Ingresos", "Nómina", "Gastos Operativos"],
                "Monto": [total_ingresos, total_nomina, total_operativos],
                "Tipo": ["Ingreso", "Egreso", "Egreso"],
            }
        )
        fig_barras = px.bar(
            df_barras,
            x="Concepto",
            y="Monto",
            color="Tipo",
            color_discrete_map={"Ingreso": "#0e9f6e", "Egreso": "#e02424"},
            text=df_barras["Monto"].map(formato_ars),
        )
        fig_barras.update_traces(textposition="outside")
        fig_barras.update_layout(
            showlegend=True, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis_title="Monto (ARS)", xaxis_title="", margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    with col_graf2:
        st.markdown("##### Distribución de Egresos del mes")
        partes = []
        if total_nomina > 0:
            partes.append(("Nómina (Staff)", total_nomina))
        if not df_operativos.empty:
            for _, fila in df_operativos.iterrows():
                partes.append((f"Operativo — {fila['categoria'].title()}", float(fila["total"])))
        if partes:
            df_torta = pd.DataFrame(partes, columns=["Categoría", "Monto"])
            fig_torta = px.pie(
                df_torta, names="Categoría", values="Monto", hole=0.45,
                color_discrete_sequence=px.colors.sequential.Teal,
            )
            fig_torta.update_traces(textinfo="percent+label")
            fig_torta.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=10),
            )
            st.plotly_chart(fig_torta, use_container_width=True)
        else:
            st.info("No hay egresos registrados en el período seleccionado.")

    st.divider()

    # --- Tabla Maestra de Sueldos ---
    st.markdown(f"##### 🧮 Desglose de Liquidación — {mes_nombre} {anio}")
    st.caption(
        "Fórmula: **Total a Pagar = Sueldo Base + (Programas Asistidos × Pago por Programa) "
        "+ Viáticos y Bonos − Adelantos**. Solo cuentan emisiones FINALIZADAS con presencia confirmada."
    )

    if df_liquidacion.empty:
        st.info("No hay staff activo para liquidar.")
    else:
        df_vista = df_liquidacion[
            ["nombre", "rol", "tipo_contrato", "sueldo_base", "programas",
             "pago_por_programa", "pago_programas", "extras", "adelantos", "total_pagar"]
        ].copy()
        df_vista.columns = [
            "Nombre", "Rol", "Contrato", "Sueldo Base", "Programas Asistidos",
            "Pago por Programa", "Subtotal Programas", "Viáticos y Bonos",
            "Adelantos (−)", "Total a Pagar",
        ]
        columnas_moneda = [
            "Sueldo Base", "Pago por Programa", "Subtotal Programas",
            "Viáticos y Bonos", "Adelantos (−)", "Total a Pagar",
        ]

        def colorear_total(valor):
            color = "#0e9f6e" if valor >= 0 else "#e02424"
            return f"color: {color}; font-weight: 700;"

        estilo = (
            df_vista.style
            .format({col: formato_ars for col in columnas_moneda})
            .map(colorear_total, subset=["Total a Pagar"])
            .set_properties(**{"background-color": "#ffffff"})
        )
        st.dataframe(estilo, use_container_width=True, hide_index=True)

        total_a_pagar_mes = float(df_vista["Total a Pagar"].sum())
        st.markdown(
            f"**Total a desembolsar este mes (neto de adelantos): "
            f"<span style='color:#1e2a4a'>{formato_ars(total_a_pagar_mes)}</span>**",
            unsafe_allow_html=True,
        )

    # --- Detalle de ingresos del período ---
    with st.expander("🔍 Ver detalle de ingresos del período"):
        if df_ingresos.empty:
            st.info("No hay ingresos registrados en el período.")
        else:
            df_ing = df_ingresos.copy()
            df_ing["monto"] = df_ing["monto"].astype(float).map(formato_ars)
            df_ing["fecha"] = pd.to_datetime(df_ing["fecha"]).dt.strftime("%d/%m/%Y")
            df_ing.columns = ["Empresa", "Tipo", "Monto", "Fecha"]
            st.dataframe(df_ing, use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# MÓDULO 4 — CONFIGURACIÓN Y ABM
# -----------------------------------------------------------------------------
def modulo_configuracion():
    st.subheader("⚙️ Configuración y Administración")

    tab_staff, tab_sponsors, tab_operativos = st.tabs(
        ["👥 Staff y Contratos", "🤝 Sponsors y Donantes", "🏢 Gastos Operativos"]
    )

    # ---------------- STAFF ----------------
    with tab_staff:
        st.markdown("##### ➕ Alta de nuevo miembro del staff")
        with st.form("formulario_alta_staff", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre_nuevo = st.text_input("Nombre y apellido")
                rol_nuevo = st.text_input("Rol", placeholder="Ej: Conductor, Productora, Editor")
                contrato_nuevo = st.selectbox("Tipo de contrato", CONTRATOS, index=1)
            with c2:
                sueldo_nuevo = st.number_input("Sueldo base mensual (ARS)", min_value=0.0, step=10000.0, format="%.2f")
                pago_programa_nuevo = st.number_input("Pago por programa asistido (ARS)", min_value=0.0, step=1000.0, format="%.2f")
            alta_ok = st.form_submit_button("➕ Dar de alta", use_container_width=True)
        if alta_ok:
            if not nombre_nuevo.strip() or not rol_nuevo.strip():
                st.error("❌ Nombre y rol son obligatorios.")
            else:
                ejecutar(
                    """
                    INSERT INTO staff (nombre, rol, tipo_contrato, sueldo_base, pago_por_programa)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nombre_nuevo.strip(), rol_nuevo.strip(), contrato_nuevo, sueldo_nuevo, pago_programa_nuevo),
                )
                st.success(f"✅ {nombre_nuevo.strip()} fue dado de alta correctamente.")
                st.rerun()

        st.markdown("##### ✏️ Editar miembro existente")
        df_todo_staff = consultar(
            """
            SELECT id, nombre, rol, tipo_contrato, sueldo_base, pago_por_programa, activo
            FROM staff ORDER BY activo DESC, nombre
            """
        )
        if df_todo_staff.empty:
            st.info("Todavía no hay staff cargado.")
        else:
            etiquetas_staff = {
                int(f["id"]): f"{f['nombre']} — {f['rol']}" + ("" if f["activo"] else " (INACTIVO)")
                for _, f in df_todo_staff.iterrows()
            }
            id_editar = st.selectbox(
                "Seleccioná a quién editar",
                options=list(etiquetas_staff.keys()),
                format_func=lambda x: etiquetas_staff[x],
            )
            fila = df_todo_staff[df_todo_staff["id"] == id_editar].iloc[0]
            with st.form("formulario_editar_staff"):
                c1, c2 = st.columns(2)
                with c1:
                    nombre_ed = st.text_input("Nombre y apellido", value=fila["nombre"])
                    rol_ed = st.text_input("Rol", value=fila["rol"])
                    contrato_ed = st.selectbox(
                        "Tipo de contrato", CONTRATOS,
                        index=CONTRATOS.index(fila["tipo_contrato"]),
                    )
                with c2:
                    sueldo_ed = st.number_input(
                        "Sueldo base mensual (ARS)", min_value=0.0, step=10000.0,
                        value=float(fila["sueldo_base"]), format="%.2f",
                    )
                    pago_ed = st.number_input(
                        "Pago por programa asistido (ARS)", min_value=0.0, step=1000.0,
                        value=float(fila["pago_por_programa"]), format="%.2f",
                    )
                    activo_ed = st.toggle("Miembro activo", value=bool(fila["activo"]))
                editar_ok = st.form_submit_button("💾 Guardar cambios", use_container_width=True)
            if editar_ok:
                ejecutar(
                    """
                    UPDATE staff
                    SET nombre = %s, rol = %s, tipo_contrato = %s,
                        sueldo_base = %s, pago_por_programa = %s, activo = %s
                    WHERE id = %s
                    """,
                    (nombre_ed.strip(), rol_ed.strip(), contrato_ed, sueldo_ed, pago_ed, activo_ed, id_editar),
                )
                st.success("✅ Datos del miembro actualizados correctamente.")
                st.rerun()

            st.markdown("##### 📋 Plantel completo")
            df_mostrar = df_todo_staff.copy()
            df_mostrar["sueldo_base"] = df_mostrar["sueldo_base"].astype(float).map(formato_ars)
            df_mostrar["pago_por_programa"] = df_mostrar["pago_por_programa"].astype(float).map(formato_ars)
            df_mostrar["activo"] = df_mostrar["activo"].map(lambda v: "✅ Activo" if v else "⛔ Inactivo")
            df_mostrar = df_mostrar.drop(columns=["id"])
            df_mostrar.columns = ["Nombre", "Rol", "Contrato", "Sueldo Base", "Pago por Programa", "Estado"]
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    # ---------------- SPONSORS ----------------
    with tab_sponsors:
        st.markdown("##### ➕ Registrar ingreso de Sponsor o Donante")
        with st.form("formulario_sponsor", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                empresa = st.text_input("Nombre de la empresa o persona")
                tipo_ingreso = st.selectbox("Tipo", TIPOS_INGRESO)
            with c2:
                monto_ingreso = st.number_input("Monto (ARS)", min_value=0.0, step=10000.0, format="%.2f")
                fecha_ingreso = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
            sponsor_ok = st.form_submit_button("➕ Registrar ingreso", use_container_width=True)
        if sponsor_ok:
            if not empresa.strip():
                st.error("❌ El nombre de la empresa es obligatorio.")
            elif monto_ingreso <= 0:
                st.error("❌ El monto debe ser mayor a cero.")
            else:
                ejecutar(
                    """
                    INSERT INTO ingresos_sponsors (nombre_empresa, tipo, monto, fecha)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (empresa.strip(), tipo_ingreso, monto_ingreso, fecha_ingreso),
                )
                st.success(f"✅ Ingreso de {formato_ars(monto_ingreso)} registrado para {empresa.strip()}.")

        st.markdown("##### 🧾 Últimos ingresos registrados")
        df_sponsors = consultar(
            """
            SELECT id, fecha, nombre_empresa, tipo, monto FROM ingresos_sponsors
            ORDER BY fecha DESC, id DESC LIMIT 20
            """
        )
        if df_sponsors.empty:
            st.info("Todavía no hay ingresos registrados.")
        else:
            df_sp = df_sponsors.copy()
            df_sp["monto"] = df_sp["monto"].astype(float).map(formato_ars)
            df_sp["fecha"] = pd.to_datetime(df_sp["fecha"]).dt.strftime("%d/%m/%Y")
            df_sp.columns = ["ID", "Fecha", "Empresa", "Tipo", "Monto"]
            st.dataframe(df_sp, use_container_width=True, hide_index=True)

            with st.expander("🗑️ Eliminar un ingreso (correcciones)"):
                id_sp_eliminar = st.selectbox("ID del ingreso a eliminar", df_sp["ID"].tolist())
                if st.button("Eliminar ingreso seleccionado"):
                    ejecutar("DELETE FROM ingresos_sponsors WHERE id = %s", (id_sp_eliminar,))
                    st.success("✅ Ingreso eliminado correctamente.")
                    st.rerun()

    # ---------------- GASTOS OPERATIVOS ----------------
    with tab_operativos:
        st.markdown("##### ➕ Registrar gasto operativo del estudio")
        with st.form("formulario_gasto_operativo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                categoria_op = st.selectbox("Categoría", CATEGORIAS_OPERATIVOS)
                monto_op = st.number_input("Monto (ARS)", min_value=0.0, step=5000.0, format="%.2f")
            with c2:
                fecha_op = st.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
                descripcion_op = st.text_input("Descripción", placeholder="Ej: Alquiler del estudio — Junio")
            operativo_ok = st.form_submit_button("➕ Registrar gasto operativo", use_container_width=True)
        if operativo_ok:
            if monto_op <= 0:
                st.error("❌ El monto debe ser mayor a cero.")
            else:
                ejecutar(
                    """
                    INSERT INTO gastos_operativos (monto, fecha, descripcion, categoria)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (monto_op, fecha_op, descripcion_op.strip(), categoria_op),
                )
                st.success(f"✅ Gasto operativo de {formato_ars(monto_op)} registrado.")

        st.markdown("##### 🧾 Últimos gastos operativos")
        df_ops = consultar(
            """
            SELECT id, fecha, categoria, monto, descripcion FROM gastos_operativos
            ORDER BY fecha DESC, id DESC LIMIT 20
            """
        )
        if df_ops.empty:
            st.info("Todavía no hay gastos operativos registrados.")
        else:
            df_op_vista = df_ops.copy()
            df_op_vista["monto"] = df_op_vista["monto"].astype(float).map(formato_ars)
            df_op_vista["fecha"] = pd.to_datetime(df_op_vista["fecha"]).dt.strftime("%d/%m/%Y")
            df_op_vista.columns = ["ID", "Fecha", "Categoría", "Monto", "Descripción"]
            st.dataframe(df_op_vista, use_container_width=True, hide_index=True)

            with st.expander("🗑️ Eliminar un gasto operativo (correcciones)"):
                id_op_eliminar = st.selectbox("ID del gasto a eliminar", df_op_vista["ID"].tolist())
                if st.button("Eliminar gasto operativo seleccionado"):
                    ejecutar("DELETE FROM gastos_operativos WHERE id = %s", (id_op_eliminar,))
                    st.success("✅ Gasto operativo eliminado correctamente.")
                    st.rerun()


# -----------------------------------------------------------------------------
# APLICACIÓN PRINCIPAL
# -----------------------------------------------------------------------------
def main():
    if not st.session_state.get("autenticado", False):
        pantalla_login()
        return

    try:
        inicializar_base_de_datos()
    except Exception as error:
        st.error(
            "❌ No se pudo conectar a la base de datos. Verificá las credenciales "
            f"en los Secrets de la aplicación. Detalle técnico: {error}"
        )
        st.stop()

    st.markdown(
        """
        <div class="encabezado-app">
            <h1>🎙️ Bamba Streaming — Gestión Financiera y Operativa</h1>
            <p>Asistencia · Liquidación de sueldos · Sponsors · Reportes en tiempo real</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### 🎙️ Bamba Streaming")
        st.caption("Sesión activa")
        if st.button("🔒 Cerrar sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 Control de Asistencia",
            "💸 Gastos Extras",
            "📊 Tablero Financiero",
            "⚙️ Configuración",
        ]
    )
    with tab1:
        modulo_asistencia()
    with tab2:
        modulo_gastos_extras()
    with tab3:
        modulo_tablero()
    with tab4:
        modulo_configuracion()


if __name__ == "__main__":
    main()
