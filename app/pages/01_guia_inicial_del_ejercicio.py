from __future__ import annotations

import streamlit as st

from config import settings
from services.progress_service import upsert_student_progress

try:
    from ui_styles import apply_compact_academic_style
except ModuleNotFoundError:
    from app.ui_styles import apply_compact_academic_style

st.set_page_config(
    page_title="Guía inicial del ejercicio",
    page_icon="🧭",
    layout="wide",
)

apply_compact_academic_style()

st.title("Guía inicial del ejercicio")
st.write(
    "Esta guía presenta las instrucciones básicas para participar en la simulación "
    "académica del conflicto urbano del Corredor Verde de la Carrera Séptima, "
    "en el tramo comprendido entre las calles 32 y 45 de Bogotá D. C."
)

# ---------------------------------------------------------
# Validación básica del flujo
# ---------------------------------------------------------
access_validated = st.session_state.get("access_validated", False)
validated_user = st.session_state.get("validated_user_record", {})

if not access_validated:
    st.warning(
        "Antes de continuar con esta guía, primero debe completarse la "
        "pantalla de acceso y validación."
    )
    st.stop()

if validated_user.get("is_admin") is True:
    st.info(
        "Este usuario tiene perfil administrativo. Para continuar, ingrese al "
        "Panel administrativo."
    )
    st.stop()

if "guide_completed" not in st.session_state:
    st.session_state["guide_completed"] = False

st.caption(
    f"Usuario validado: {validated_user.get('full_name', 'Usuario')} "
    f"({st.session_state.get('validated_user_email', 'sin correo registrado')})"
)

st.divider()

# ---------------------------------------------------------
# Bloque 1. Propósito del ejercicio
# ---------------------------------------------------------
st.header("1. Propósito del ejercicio")
st.write(
    "El ejercicio propone una simulación académica de conflicto urbano. Cada "
    "estudiante asume un actor específico vinculado al caso del Corredor Verde "
    "de la Carrera Séptima y participa desde sus intereses, preocupaciones y "
    "límites de negociación."
)

st.markdown(
    """
    **El propósito central es que usted pueda:**
    - comprender el conflicto urbano desde una posición situada;
    - argumentar con coherencia frente al rol asignado;
    - usar evidencias, referencias y materiales del caso;
    - responder a otros actores de manera respetuosa y estratégica;
    - reconocer tensiones sociales, territoriales, técnicas y normativas.
    """
)

# ---------------------------------------------------------
# Bloque 2. Ruta obligatoria del estudiante
# ---------------------------------------------------------
st.header("2. Ruta obligatoria del estudiante")
st.markdown(
    """
    **Secuencia mínima de trabajo:**
    1. leer esta guía inicial;
    2. revisar el contexto del caso;
    3. consultar los materiales de apoyo;
    4. revisar cuidadosamente el rol asignado;
    5. construir el perfil público del actor;
    6. publicar una intervención inicial;
    7. leer activamente las intervenciones de otros actores;
    8. responder al menos a otro actor;
    9. registrar evidencias cuando corresponda;
    10. elaborar un cierre estratégico de postura.
    """
)

st.info(
    "Este no es un foro libre. Es una simulación estructurada: importa participar, "
    "pero también hacerlo desde el rol asignado, con argumentos, evidencias y "
    "capacidad de respuesta frente a otros actores."
)

# ---------------------------------------------------------
# Bloque 3. Perfil público del actor
# ---------------------------------------------------------
st.header("3. Perfil público del actor")
st.write(
    "Antes de intervenir, debe construir el perfil público del actor que representa. "
    "Ese perfil debe expresar quién es el actor, qué intereses defiende, cuál es "
    "su postura inicial y qué puntos considera sensibles o no negociables."
)

st.markdown(
    """
    - Puede guardar el perfil como **borrador** mientras lo ajusta.
    - Cuando use la opción de **envío definitivo**, el perfil quedará bloqueado para edición.
    - El perfil debe ser coherente con el rol asignado y con el conflicto del caso.
    """
)

# ---------------------------------------------------------
# Bloque 4. Sala de discusión
# ---------------------------------------------------------
st.header("4. Sala de discusión")
st.markdown(
    """
    En la sala de discusión deberá publicar una intervención inicial coherente con
    su rol y, luego, responder al menos a otro actor. La réplica no debe limitarse
    a decir que está de acuerdo o en desacuerdo: debe explicar por qué, reconocer
    tensiones y, cuando sea posible, apoyarse en evidencias.

    **Señales visibles en la discusión:**
    - **🟢 Tu intervención:** identifica las intervenciones publicadas por usted.
    - **🔴 Pendiente:** hay una interacción ajena que todavía no ha atendido.
    - **🟡 En proceso:** otro actor intervino después y conviene revisar la conversación.
    - **🟢 Atendida:** usted ya respondió o gestionó esa interacción.
    """
)

# ---------------------------------------------------------
# Bloque 5. Evidencias
# ---------------------------------------------------------
st.header("5. Evidencias")
st.write(
    "Las evidencias sirven para respaldar los argumentos. Pueden provenir de "
    "documentos del caso, notas de prensa, normativa, datos territoriales, mapas, "
    "referencias académicas o fuentes externas pertinentes."
)

st.markdown(
    """
    **Use evidencias cuando necesite:**
    - sostener una afirmación importante;
    - mostrar un impacto social, territorial, técnico o normativo;
    - responder a otro actor con mayor sustento;
    - fortalecer su cierre estratégico.
    """
)

# ---------------------------------------------------------
# Bloque 6. Cierre estratégico
# ---------------------------------------------------------
st.header("6. Cierre estratégico")
st.write(
    "Al finalizar el proceso, deberá elaborar un cierre estratégico de postura. "
    "Ese cierre no es un resumen mecánico: debe mostrar cómo evolucionó su "
    "posición dentro del conflicto."
)

st.markdown(
    """
    **El cierre debe sintetizar:**
    - qué defendió desde su rol;
    - qué tensiones reconoció durante la discusión;
    - qué acuerdos o condiciones considera aceptables;
    - qué no está dispuesto a negociar desde la posición del actor.
    """
)

st.warning(
    "Después del cierre estratégico no se exigirán nuevas respuestas, salvo "
    "indicación expresa del docente."
)

# ---------------------------------------------------------
# Bloque 7. Evaluación
# ---------------------------------------------------------
st.header("7. Evaluación")
st.write(
    "La evaluación considerará la calidad del proceso, no solo la cantidad de "
    "intervenciones. Las revisiones docentes tendrán en cuenta el desempeño "
    "argumentativo y la coherencia del trabajo realizado."
)

st.markdown(
    """
    **Se valorará especialmente:**
    - coherencia con el rol asignado;
    - calidad argumentativa;
    - uso pertinente de evidencias;
    - capacidad de responder a otros actores;
    - comprensión del conflicto urbano;
    - pertinencia técnica o normativa cuando corresponda;
    - claridad comunicativa.
    """
)

# ---------------------------------------------------------
# Bloque 8. Reglas básicas de participación
# ---------------------------------------------------------
st.header("8. Reglas básicas de participación")
st.markdown(
    """
    - Argumente siempre desde el rol asignado.
    - Evite intervenciones genéricas o desconectadas del caso.
    - Responda con respeto, incluso cuando exista desacuerdo.
    - Use evidencias cuando sea posible.
    - No se limite a decir “estoy de acuerdo” o “no estoy de acuerdo”.
    - Reconozca tensiones, impactos diferenciados y posibles condiciones de negociación.
    """
)

# ---------------------------------------------------------
# Confirmación de lectura
# ---------------------------------------------------------
st.divider()
st.subheader("Confirmación de lectura")

st.write(
    "Cuando considere que ya comprendió el sentido general del ejercicio, "
    "puede marcar esta guía como leída para continuar con el siguiente paso del flujo."
)

if st.button("He leído y comprendido la guía inicial"):
    st.session_state["guide_completed"] = True
    profile_id = st.session_state.get("profile_id", "")
    case_id = st.session_state.get("case_id", "")
    if profile_id and case_id:
        ok_progress, _saved_progress, progress_message = upsert_student_progress(
            profile_id,
            case_id,
            guide_completed=True,
        )
        if not ok_progress:
            st.warning(progress_message)
    st.success(
        "La guía inicial quedó marcada como leída. "
        "El siguiente paso recomendado es revisar el contexto del caso."
    )

if st.session_state["guide_completed"]:
    st.info(
        "Estado actual: guía inicial completada. "
        "Siguiente pantalla sugerida: contexto del caso."
    )

# ---------------------------------------------------------
# Nota técnica
# ---------------------------------------------------------
st.divider()
st.caption(
    "Nota técnica: esta guía forma parte del onboarding del estudiante. "
    "El contexto del caso, los materiales, el rol, el perfil público, la discusión, "
    "las evidencias y los resultados se gestionan en sus respectivas pantallas del flujo."
)
