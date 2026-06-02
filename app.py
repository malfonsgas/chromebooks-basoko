import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
SPREADSHEET_ID = "1VySytS2uHoOEFt_EHwMqZsJ6o9CF1vAJqwKSBo1tr7Y"

USUARIOS = {
    "maite": "basoko2024",
    "admin": "basoko2024"
}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Tabla de verdad: (estado_actual, accion) -> pasa_a_estado
TABLA_VERDAD = {
    ("Para reparar",       "Recibo-Estropeado, para reparar"):  "ERROR-Ya estaba para reparar",
    ("Para reparar",       "Recibo-Está reparado"):             "Disponible",
    ("Para reparar",       "Recibo-Devolución Usuario"):        "ERROR-Estaba para reparar",
    ("Para reparar",       "Entrega-Usuario"):                  "Asignado a usuario",
    ("Para reparar",       "Hacer seguimiento"):                "Para reparar",
    ("Para reparar",       "Dar de baja"):                      "Baja",
    ("Asignado a usuario", "Recibo-Estropeado, para reparar"):  "Para reparar",
    ("Asignado a usuario", "Recibo-Está reparado"):             "ERROR-Está asignado a usuario",
    ("Asignado a usuario", "Recibo-Devolución Usuario"):        "Disponible",
    ("Asignado a usuario", "Entrega-Usuario"):                  "ERROR-Ya está asignado a un usuario",
    ("Asignado a usuario", "Hacer seguimiento"):                "Asignado a usuario",
    ("Asignado a usuario", "Dar de baja"):                      "Baja",
    ("Disponible",         "Recibo-Estropeado, para reparar"):  "Para reparar",
    ("Disponible",         "Recibo-Está reparado"):             "ERROR-No estaba para reparar",
    ("Disponible",         "Recibo-Devolución Usuario"):        "ERROR-No estaba asignado a nadie",
    ("Disponible",         "Entrega-Usuario"):                  "Asignado a usuario",
    ("Disponible",         "Hacer seguimiento"):                "Disponible",
    ("Disponible",         "Dar de baja"):                      "Baja",
    ("En seguimiento",     "Recibo-Estropeado, para reparar"):  "Para reparar",
    ("En seguimiento",     "Recibo-Está reparado"):             "Disponible",
    ("En seguimiento",     "Recibo-Devolución Usuario"):        "Disponible",
    ("En seguimiento",     "Entrega-Usuario"):                  "Asignado a usuario",
    ("En seguimiento",     "Hacer seguimiento"):                "ERROR-Ya estaba en seguimiento",
    ("En seguimiento",     "Dar de baja"):                      "Baja",
    ("Baja",               "Recibo-Estropeado, para reparar"):  "ERROR",
    ("Baja",               "Recibo-Está reparado"):             "ERROR",
    ("Baja",               "Recibo-Devolución Usuario"):        "ERROR",
    ("Baja",               "Entrega-Usuario"):                  "ERROR",
    ("Baja",               "Hacer seguimiento"):                "ERROR",
    ("Baja",               "Dar de baja"):                      "ERROR",
}

TODAS_ACCIONES = [
    "Recibo-Estropeado, para reparar",
    "Recibo-Está reparado",
    "Recibo-Devolución Usuario",
    "Entrega-Usuario",
    "Hacer seguimiento",
    "Dar de baja",
]

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="Gestión Chromebooks · IES Basoko", page_icon="💻", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

:root {
    --bg: #f0f4f8;
    --surface: #ffffff;
    --surface2: #e8eef5;
    --border: #c8d6e5;
    --accent: #2563eb;
    --accent2: #4f46e5;
    --success: #16a34a;
    --error: #dc2626;
    --warning: #d97706;
    --text: #1e293b;
    --text2: #475569;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { display: none; }

.main .block-container {
    max-width: 720px;
    padding: 2rem 1.5rem;
}

h1, h2, h3 { font-family: 'DM Sans', sans-serif; font-weight: 600; }

.logo-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.logo-icon {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}
.logo-text { font-size: 1.1rem; font-weight: 600; color: var(--text); }
.logo-sub { font-size: 0.75rem; color: var(--text2); font-family: 'DM Mono', monospace; }

.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.field-label {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text2);
    margin-bottom: 0.3rem;
}

.estado-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    font-family: 'DM Mono', monospace;
}
.estado-disponible   { background: #14532d44; color: #4ade80; border: 1px solid #166534; }
.estado-asignado     { background: #1e3a5f44; color: #60a5fa; border: 1px solid #1e40af; }
.estado-reparar      { background: #7c2d1244; color: #fb923c; border: 1px solid #9a3412; }
.estado-seguimiento  { background: #4a1d9644; color: #a78bfa; border: 1px solid #5b21b6; }
.estado-baja         { background: #3f132444; color: #f87171; border: 1px solid #991b1b; }
.estado-error        { background: #7c1d1d44; color: #fca5a5; border: 1px solid #b91c1c; }
.estado-vacio        { background: #1f293744; color: var(--text2); border: 1px solid var(--border); }

.pasa-a-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.75rem 1rem;
    background: var(--surface2);
    border-radius: 10px;
    border: 1px solid var(--border);
    margin-top: 0.5rem;
}
.arrow { color: var(--text2); font-size: 1.2rem; }

.btn-registrar {
    width: 100%;
    padding: 0.9rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    margin-top: 1rem;
}

.success-msg {
    background: #14532d33;
    border: 1px solid #166534;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    color: #4ade80;
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
}
.error-msg {
    background: #7c1d1d33;
    border: 1px solid #b91c1c;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    color: #fca5a5;
    font-size: 0.9rem;
}

/* Streamlit widget overrides - tema claro */
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid #c8d6e5 !important;
    color: #1e293b !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] > div > div > input {
    background: #ffffff !important;
    border: 1px solid #c8d6e5 !important;
    color: #1e293b !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] > div > div > input::placeholder {
    color: #94a3b8 !important;
}
[data-testid="stTextArea"] textarea {
    background: #ffffff !important;
    border: 1px solid #c8d6e5 !important;
    color: #1e293b !important;
    border-radius: 8px !important;
}
[data-testid="stTextArea"] textarea::placeholder {
    color: #94a3b8 !important;
}
[data-testid="stCheckbox"] label { color: #1e293b !important; }
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stTextArea"] label {
    color: #475569 !important;
    font-weight: 500 !important;
}
/* Texto dentro del selectbox desplegado */
[data-testid="stSelectbox"] span {
    color: #1e293b !important;
}
.stButton > button {
    background: linear-gradient(135deg, #2563eb, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# AUTENTICACIÓN
# ─────────────────────────────────────────────
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
        <div class='logo-bar'>
            <div class='logo-icon'>💻</div>
            <div>
                <div class='logo-text'>Gestión Chromebooks</div>
                <div class='logo-sub'>IES BASOKO · ACCESO RESTRINGIDO</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Identificación")
        usuario = st.text_input("Usuario", placeholder="usuario")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        if st.button("Entrar"):
            if usuario in USUARIOS and USUARIOS[usuario] == password:
                st.session_state.logged_in = True
                st.session_state.usuario_actual = usuario
                st.rerun()
            else:
                st.markdown("<div class='error-msg'>Usuario o contraseña incorrectos.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

check_login()

# ─────────────────────────────────────────────
# CONEXIÓN A GOOGLE SHEETS
# ─────────────────────────────────────────────
@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def cargar_datos():
    client = get_client()
    ss = client.open_by_key(SPREADSHEET_ID)

    # Alumnado: col1=fila, col2=nombre, col3=curso, col4=grupo, col5=chromebook
    sh_alum = ss.worksheet("Alumnado")
    alum_data = sh_alum.get_all_values()
    alumnos = []
    for row in alum_data[1:]:
        if len(row) >= 2 and row[1].strip():
            grupo = row[3].strip() if len(row) > 3 else ""
            nombre = row[1].strip()
            label = f"{grupo}-{nombre}" if grupo else nombre
            alumnos.append({"fila": row[0], "nombre": nombre, "curso": row[2] if len(row)>2 else "", "grupo": grupo, "chromebook": row[4] if len(row)>4 else "", "label": label})

    # Chromebooks: col1=fila, col2=serie, col3=disponible, col4=usuario, col5=estado
    sh_chrome = ss.worksheet("Chromebook")
    chrome_data = sh_chrome.get_all_values()
    chromebooks = {}
    for row in chrome_data[1:]:
        if len(row) >= 2 and row[1].strip():
            estado = row[4].strip() if len(row) > 4 else "Disponible"
            usuario = row[3].strip() if len(row) > 3 else ""
            seguimiento = row[6].strip() if len(row) > 6 else "FALSE"
            chromebooks[row[1].strip()] = {
                "fila": row[0], "serie": row[1].strip(),
                "estado": estado, "usuario": usuario,
                "seguimiento": seguimiento
            }

    return alumnos, chromebooks

def get_badge_class(estado):
    if not estado: return "estado-vacio"
    e = estado.lower()
    if "disponible" in e: return "estado-disponible"
    if "asignado" in e: return "estado-asignado"
    if "reparar" in e: return "estado-reparar"
    if "seguimiento" in e: return "estado-seguimiento"
    if "baja" in e: return "estado-baja"
    if "error" in e: return "estado-error"
    return "estado-vacio"

# ─────────────────────────────────────────────
# LÓGICA DE REGISTRO
# ─────────────────────────────────────────────
def registrar_accion(alumno_nombre, num_chrome, estado_actual, accion, pasa_a_estado, pendiente_pago, observaciones):
    client = get_client()
    ss = client.open_by_key(SPREADSHEET_ID)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    alumnos, chromebooks = cargar_datos()
    chrome_info = chromebooks.get(num_chrome)
    if not chrome_info:
        return False, f"Chromebook {num_chrome} no encontrado en la hoja."

    # Buscar alumno
    alumno_info = None
    if alumno_nombre:
        for a in alumnos:
            if a["nombre"] == alumno_nombre:
                alumno_info = a
                break

    # Validaciones
    if accion == "Entrega-Usuario":
        if alumno_info and alumno_info["chromebook"] != "":
            return False, f"{alumno_nombre} ya tiene un Chromebook asignado ({alumno_info['chromebook']})."
    if accion in ["Recibo-Devolución Usuario", "Recibo-Estropeado, para reparar"]:
        if alumno_info and alumno_info["chromebook"] != num_chrome:
            return False, f"El Chromebook {num_chrome} no está asignado a {alumno_nombre}."

    # 1. Actualizar hoja Chromebook
    sh_chrome = ss.worksheet("Chromebook")
    fila_chrome = int(chrome_info["fila"])
    sh_chrome.update_cell(fila_chrome, 5, pasa_a_estado)  # col5 = estado
    if accion == "Hacer seguimiento":
        sh_chrome.update_cell(fila_chrome, 7, "TRUE")  # col7 = seguimiento

    # Actualizar historial Chromebook (col6)
    hist_chrome = sh_chrome.cell(fila_chrome, 6).value or ""
    nueva_linea = f"{fecha}-{alumno_nombre}-{num_chrome}-{accion}-{observaciones}"
    sh_chrome.update_cell(fila_chrome, 6, nueva_linea + "\n" + hist_chrome)

    # Actualizar usuario en Chromebook
    if accion == "Entrega-Usuario":
        sh_chrome.update_cell(fila_chrome, 4, alumno_nombre)
        sh_chrome.update_cell(fila_chrome, 3, "FALSE")
    elif accion in ["Recibo-Devolución Usuario", "Dar de baja"]:
        sh_chrome.update_cell(fila_chrome, 4, "-")
        sh_chrome.update_cell(fila_chrome, 3, "TRUE" if pasa_a_estado == "Disponible" else "FALSE")

    # 2. Actualizar hoja Alumnado
    if alumno_info:
        sh_alum = ss.worksheet("Alumnado")
        fila_alum = int(alumno_info["fila"])
        if accion == "Entrega-Usuario":
            sh_alum.update_cell(fila_alum, 5, num_chrome)
        elif accion in ["Recibo-Devolución Usuario", "Recibo-Estropeado, para reparar"]:
            sh_alum.update_cell(fila_alum, 5, "")
        # Historial alumno (col6)
        hist_alum = sh_alum.cell(fila_alum, 6).value or ""
        sh_alum.update_cell(fila_alum, 6, nueva_linea + "\n" + hist_alum)

    # 3. Añadir a REGISTRO ENTRADAS (inserta fila en posición 2)
    sh_registro = ss.worksheet("REGISTRO ENTRADAS")
    sh_registro.insert_row([
        "",           # col1 vacía
        "",           # ID
        "1",          # aux1
        "1",          # aux2
        "",           # aux3
        "",           # aux4
        fecha,        # FECHA
        alumno_nombre,# ENTIDAD/PERSONA
        num_chrome,   # Nº CHROMEBOOK
        estado_actual,# ESTADO ACTUAL
        accion,       # ACCIÓN
        pasa_a_estado,# PASA A ESTADO
        str(pendiente_pago),  # PENDIENTE PAGO
        observaciones,# OBSERVACIONES
        f"{fecha}-{alumno_nombre}-{num_chrome}-{accion}-{observaciones}",  # resumen
        "FALSE"       # Email Secretaría
    ], index=2)

    # 4. Añadir fila a ENTRADAS (con fondo gris simulado — solo datos)
    sh_entradas = ss.worksheet("ENTRADAS")
    sh_entradas.append_row([
        "", "", "", "", "", "",
        alumno_nombre,
        "",
        num_chrome,
        estado_actual,
        accion,
        pasa_a_estado,
        str(pendiente_pago),
        observaciones,
        "TRUE"
    ])

    cargar_datos.clear()
    return True, f"✓ Registrado correctamente — {num_chrome} · {accion} · {fecha}"

# ─────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ─────────────────────────────────────────────
st.markdown("""
<div class='logo-bar'>
    <div class='logo-icon'>💻</div>
    <div>
        <div class='logo-text'>Gestión Chromebooks</div>
        <div class='logo-sub'>IES BASOKO · PANEL DE CONTROL</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Cargar datos
try:
    alumnos, chromebooks = cargar_datos()
except Exception as e:
    st.error(f"Error conectando con Google Sheets: {e}")
    st.stop()

# Listas para selectores
lista_alumnos_labels = ["— Sin alumno (entidad externa) —"] + sorted([a["label"] for a in alumnos])
lista_chromebooks = sorted(chromebooks.keys())
lista_otros = ["CAU", "Gobierno de Navarra", "Microchip", "Otro"]

# ── FORMULARIO ──
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.markdown("### Nueva acción")

col1, col2 = st.columns([3, 1])
with col1:
    alumno_sel = st.selectbox("👤 Alumnado / Entidad", lista_alumnos_labels,
        help="Escribe para filtrar por nombre o grupo")
with col2:
    es_externo = st.checkbox("Entidad externa", value=False)

if es_externo:
    entidad_externa = st.selectbox("Entidad", lista_otros)
    alumno_nombre_final = entidad_externa
else:
    if alumno_sel == "— Sin alumno (entidad externa) —":
        alumno_nombre_final = ""
    else:
        # Extraer nombre del label (quitar el prefijo grupo-)
        partes = alumno_sel.split("-", 1)
        alumno_nombre_final = partes[1] if len(partes) > 1 else alumno_sel

st.markdown("---")

# Chromebook
chrome_sel = st.selectbox("🖥️ Nº Chromebook", ["— Selecciona —"] + lista_chromebooks)

# Estado actual (automático)
estado_actual = ""
if chrome_sel != "— Selecciona —":
    info = chromebooks.get(chrome_sel, {})
    estado_actual = info.get("estado", "")
    badge_class = get_badge_class(estado_actual)
    st.markdown(f"""
    <div style='margin: 0.5rem 0'>
        <div class='field-label'>Estado actual</div>
        <span class='estado-badge {badge_class}'>⬤ {estado_actual or 'Sin estado'}</span>
    </div>
    """, unsafe_allow_html=True)

    # Usuario actual
    usuario_actual = info.get("usuario", "")
    if usuario_actual and usuario_actual != "-":
        st.markdown(f"<div style='font-size:0.85rem; color: #475569; margin-bottom:0.5rem'>👤 Asignado a: <b style='color:#2563eb; font-size:0.95rem'>{usuario_actual}</b></div>", unsafe_allow_html=True)

st.markdown("---")

# Acción (filtrada según estado)
acciones_validas = []
if estado_actual:
    for accion in TODAS_ACCIONES:
        resultado = TABLA_VERDAD.get((estado_actual, accion), "")
        if not resultado.startswith("ERROR"):
            acciones_validas.append(accion)

accion_sel = st.selectbox(
    "⚡ Acción",
    ["— Selecciona —"] + (acciones_validas if acciones_validas else TODAS_ACCIONES)
)

# Pasa a estado (automático)
pasa_a_estado = ""
if estado_actual and accion_sel != "— Selecciona —":
    pasa_a_estado = TABLA_VERDAD.get((estado_actual, accion_sel), "")
    badge_class2 = get_badge_class(pasa_a_estado)
    st.markdown(f"""
    <div class='pasa-a-row'>
        <span class='estado-badge {get_badge_class(estado_actual)}'>⬤ {estado_actual}</span>
        <span class='arrow'>→</span>
        <span class='estado-badge {badge_class2}'>⬤ {pasa_a_estado or '?'}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

pendiente_pago = st.checkbox("💳 Pendiente de pago por reparación")
observaciones = st.text_area("📝 Observaciones", placeholder="Opcional...", height=80)

st.markdown("</div>", unsafe_allow_html=True)

# ── BOTÓN REGISTRAR ──
if st.button("✓ Registrar acción", use_container_width=True):
    # Validaciones previas
    if chrome_sel == "— Selecciona —":
        st.markdown("<div class='error-msg'>⚠ Selecciona un Chromebook.</div>", unsafe_allow_html=True)
    elif accion_sel == "— Selecciona —":
        st.markdown("<div class='error-msg'>⚠ Selecciona una acción.</div>", unsafe_allow_html=True)
    elif pasa_a_estado.startswith("ERROR"):
        st.markdown(f"<div class='error-msg'>⚠ Acción no válida: {pasa_a_estado}</div>", unsafe_allow_html=True)
    elif accion_sel in ["Entrega-Usuario", "Recibo-Devolución Usuario"] and not alumno_nombre_final:
        st.markdown("<div class='error-msg'>⚠ Esta acción requiere seleccionar un alumno o entidad.</div>", unsafe_allow_html=True)
    else:
        with st.spinner("Registrando..."):
            ok, msg = registrar_accion(
                alumno_nombre_final, chrome_sel, estado_actual,
                accion_sel, pasa_a_estado, pendiente_pago, observaciones
            )
        if ok:
            st.markdown(f"<div class='success-msg'>{msg}</div>", unsafe_allow_html=True)
            st.balloons()
        else:
            st.markdown(f"<div class='error-msg'>⚠ {msg}</div>", unsafe_allow_html=True)

# ── FOOTER ──
st.markdown(f"""
<div style='text-align:center; margin-top:3rem; color: #3d4466; font-size:0.75rem; font-family: DM Mono, monospace'>
    IES Basoko · Gestión Chromebooks · {st.session_state.get('usuario_actual','').upper()}
</div>
""", unsafe_allow_html=True)
