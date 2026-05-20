# 24_estructura_pantallas_y_navegacion_del_sistema.md

## Proyecto
**Simulación asincrónica de conflictos urbanos por roles**

## Propósito del documento
Este archivo traduce el flujo real de uso del sistema a una estructura concreta de pantallas y navegación.

Su función es dejar definido:
- qué pantallas tendrá el sistema;
- en qué orden aparecerán;
- qué ve el estudiante;
- qué ve el administrador;
- y cómo se articula el recorrido completo dentro de la app.

---

# 1. Criterio general

La interfaz no debe organizarse solo por “módulos”, sino por **momentos reales de uso**.

Por eso, la navegación debe responder al flujo pedagógico y operativo ya definido:

1. validación del usuario  
2. guía inicial del ejercicio  
3. contextualización del caso  
4. asignación y comprensión del rol  
5. construcción del perfil público  
6. panel principal del estudiante  
7. discusión  
8. seguimiento y resultados  
9. panel administrativo

---

# 2. Pantallas recomendadas

## Pantalla 0. Acceso y validación
**Archivo sugerido:** `00_acceso_y_validacion.py`

### Función
- validar correo institucional;
- verificar usuario autorizado;
- habilitar ingreso.

### Qué muestra
- formulario de ingreso;
- aviso de dominio institucional;
- mensaje de acceso permitido o no permitido.

---

## Pantalla 1. Guía inicial del ejercicio
**Archivo sugerido:** `01_guia_inicial_del_ejercicio.py`

### Función
- introducir el sentido del ejercicio;
- explicar propósito, lógica, etapas, guía de uso y evaluación.

### Qué muestra
- presentación general;
- propósito;
- lógica del trabajo;
- etapas;
- guía básica;
- estrategia general de evaluación.

### Regla
Debe ser obligatoria en el primer ingreso.

---

## Pantalla 2. Contexto del caso
**Archivo sugerido:** `02_contexto_del_caso.py`

### Función
- presentar el escenario del conflicto urbano.

### Qué muestra
- descripción del caso;
- ubicación;
- actores implicados;
- tensiones principales;
- materiales de apoyo;
- notas y referencias.

---

## Pantalla 3. Mi rol y preparación inicial
**Archivo sugerido:** `03_mi_rol_y_preparacion.py`

### Función
- mostrar el rol asignado;
- orientar la investigación inicial del actor.

### Qué muestra
- nombre del rol;
- misión;
- intereses;
- restricciones;
- recursos;
- puntos no negociables;
- criterio de éxito.

### Qué permite
- comprender el rol;
- preparar la construcción del perfil.

---

## Pantalla 4. Perfil público del actor
**Archivo sugerido:** `04_perfil_publico_del_actor.py`

### Función
- permitir construir la presentación pública del actor.

### Qué muestra o captura
- nombre visible;
- avatar o imagen;
- presentación breve;
- postura inicial;
- interés principal;
- punto no negociable;
- línea de acción.

---

## Pantalla 5. Panel principal del estudiante
**Archivo sugerido:** `05_panel_principal_estudiante.py`

### Función
- servir como panel recurrente de entrada del estudiante.

### Qué muestra
- saludo;
- caso activo;
- rol;
- fase actual;
- resumen de status;
- accesos a discusión, evidencias, resultados y guía inicial;
- prototipo simple del análisis relacional, cuando exista.

---

## Pantalla 6. Sala de discusión
**Archivo sugerido:** `06_sala_de_discusion.py`

### Función
- ser el entorno central de participación.

### Qué muestra
- hilos;
- intervenciones;
- respuestas encadenadas;
- autor, rol, fecha, tipo y evidencias.

### Qué permite
- publicar postura;
- responder;
- contraargumentar;
- negociar;
- cerrar intervención.

---

## Pantalla 7. Evidencias
**Archivo sugerido:** `07_evidencias.py`

### Función
- registrar y consultar soportes.

### Qué muestra
- lista de evidencias;
- tipo;
- descripción;
- relación con intervención.

### Qué permite
- crear evidencia;
- asociarla a una intervención.

---

## Pantalla 8. Resultados del estudiante
**Archivo sugerido:** `08_resultados_estudiante.py`

### Función
- mostrar los resultados del ejercicio al estudiante.

### Qué muestra
- nota final;
- descriptor global;
- resultados por componente;
- barras de desempeño;
- comentario final;
- posición global si se habilita.

---

## Pantalla 9. Panel administrativo
**Archivo sugerido:** `09_panel_admin.py`

### Función
- concentrar seguimiento, revisión y cierre del ejercicio.

### Qué muestra
- estado del caso;
- estudiantes;
- actividad;
- valoraciones preliminares;
- revisión por rúbrica;
- resultados consolidados;
- exportación.

---

# 3. Navegación recomendada

## Recorrido del estudiante
Acceso y validación  
→ Guía inicial  
→ Contexto del caso  
→ Mi rol y preparación inicial  
→ Perfil público del actor  
→ Panel principal del estudiante  
→ Sala de discusión / Evidencias / Resultados

## Recorrido del administrador
Acceso y validación  
→ Panel administrativo  
→ seguimiento del caso  
→ revisión y validación  
→ cierre y exportación

---

# 4. Menú lateral sugerido

## Para estudiante
- Guía inicial
- Contexto del caso
- Mi rol
- Mi perfil público
- Panel principal
- Discusión
- Evidencias
- Resultados

## Para administrador
- Panel admin
- Seguimiento del caso
- Evaluación
- Resultados globales
- Exportación

---

# 5. Decisión importante

Esta estructura **ajusta y mejora** la estructura de pantallas inicialmente prevista, porque incorpora dos elementos que no estaban lo bastante diferenciados:

- la **Guía inicial del ejercicio**
- y el **Contexto del caso**

Además, separa correctamente:

- comprensión del conflicto,
- comprensión del rol,
- construcción del perfil,
- y entrada al panel principal.

---

# 6. Cierre

Con este documento queda definida una estructura de pantallas y navegación más concreta y coherente con el flujo real de uso del sistema.

A partir de aquí, el siguiente paso lógico es construir el **arranque técnico de la app** con los primeros archivos base.
