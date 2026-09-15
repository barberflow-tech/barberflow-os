# Proyecto de Software: BarberFlow OS

**Asignatura:** Introducción a la Gestión de Proyectos de Software (Código 750031C)
**Rol:** Lead Project Manager, Scrum Master y Principal Software Architect

---

## SECCIÓN 1: FICHAS DE IDENTIFICACIÓN Y MODELO DE NEGOCIO

* **Nombre de la Empresa Desarrolladora:** BarberFlow Technologies
* **Nombre del Proyecto / SaaS:** **BarberFlow OS**
* **Planteamiento del Problema:** Las barberías modernas enfrentan una fuga de ingresos crítica debido a los *no-shows* (citas a las que el cliente no asiste), gestión caótica a través de WhatsApp que deriva en cruces de horarios, cálculo manual propenso a errores para las comisiones de los barberos (dependiendo del tipo de servicio), y un nulo seguimiento del ciclo de vida del cliente (fidelización).
* **Propuesta de Valor:** BarberFlow OS es una plataforma B2B integral que automatiza el ciclo operativo de la barbería. Reduce el ausentismo mediante inteligencia predictiva, garantiza el cálculo milimétrico y transparente de comisiones en tiempo real, y centraliza el agendamiento y el punto de venta (POS) en una única interfaz unificada de alta disponibilidad.
* **Cliente Objetivo:** Barberías de segmento medio-alto y cadenas emergentes (entre 3 y 15 barberos por sucursal).
* **Integrantes del Equipo (5 Roles):**

  1. **Scrum Master / Lead Full-Stack Developer (Brandon Stiven Jiménez Romero):** Garante de la metodología ágil, eliminación de bloqueos, gestión de tableros Jira/Notion y desarrollo transversal Full-Stack (React 19 / Django 5).
  2. **Product Owner / Frontend Specialist (Daniel Escobar Bahoz):** Interfaz con el cliente (stakeholders), definición y priorización del Backlog, y desarrollo de interfaces de usuario responsivas en React 19 / Tailwind CSS v4.
  3. **Tech Lead / Full-Stack Developer (Reinel Fabián Vargas Méndez):** Diseño de arquitectura (API REST en Django 5 DRF, bases de datos relacionales PostgreSQL/Supabase), revisión de PRs y desarrollo Full-Stack.
  4. **QA Engineer & DevOps Specialist (Esteban Rivera González):** Diseño de pruebas automatizadas (unitarias e integración con Pytest-Django y Vitest), pipelines de CI/CD en GitHub Actions, Dockerización y despliegue en Render/Vercel.
  5. **UI/UX Designer & Data Analyst (Jose Otoniel Henao Montes):** Prototipado interactivo en Figma, maquetación UI con Tailwind v4 / Shadcn y diseño/entrenamiento del modelo predictivo *SmartGuard* utilizando Python (`scikit-learn` / `pandas`).

---

## SECCIÓN 2: ESTRUCTURA DE ÉPICAS Y BACKLOG PARA JIRA (20 HUs)

El esfuerzo total estimado es de **exactamente 240 horas** distribuidas en el equipo.

### ÉPICA 1: Gestión Centralizada de Agenda y Citas (60 Horas)

* **HU-01: Visualización de disponibilidad en tiempo real** (10h)

  * *Narrativa:* Como Cliente, quiero ver el calendario de disponibilidad de mi barbero preferido, para elegir un horario que se ajuste a mi día.
  * *Criterios de Aceptación:*

    * **Dado** que un cliente selecciona un barbero, **Cuando** carga la vista de calendario, **Entonces** el sistema debe mostrar únicamente los bloques de 30/60 minutos disponibles del mes en curso, bloqueando descansos y citas previas.
* **HU-02: Creación de reserva de servicio** (14h)

  * *Narrativa:* Como Cliente, quiero reservar una cita seleccionando el servicio y el barbero, para asegurar mi atención sin llamar al local.
  * *Criterios de Aceptación:*

    * **Dado** que el cliente ha seleccionado un horario válido, **Cuando** confirma la cita y acepta las políticas, **Entonces** el sistema registra la reserva en estado "Pendiente" y bloquea el espacio en la base de datos concurrente.
* **HU-03: Cancelación y reprogramación de citas** (12h)

  * *Narrativa:* Como Cliente, quiero poder cancelar o cambiar la hora de mi cita desde mi perfil, para gestionar imprevistos sin penalización.
  * *Criterios de Aceptación:*

    * **Dado** que el cliente tiene una cita activa, **Cuando** selecciona "Reprogramar" con más de 12 horas de antelación, **Entonces** el sistema libera el slot anterior y reserva el nuevo horario exitosamente.
* **HU-04: Sincronización de bloqueos de agenda por el Administrador** (14h)

  * *Narrativa:* Como Administrador, quiero bloquear horarios específicos de forma manual, para gestionar ausencias imprevistas del personal.
  * *Criterios de Aceptación:*

    * **Dado** que un barbero reporta incapacidad, **Cuando** el administrador bloquea su agenda del día, **Entonces** el sistema notifica a los clientes afectados y deshabilita la reserva web para ese periodo.
* **HU-05: Sistema de notificaciones transaccionales** (10h)

  * *Narrativa:* Como Cliente, quiero recibir un recordatorio de mi cita, para evitar olvidos.
  * *Criterios de Aceptación:*

    * **Dado** que faltan 24 y 2 horas para una cita confirmada, **Cuando** se ejecuta el cronjob del sistema, **Entonces** se envía un mensaje de texto/email al cliente con los detalles de la reserva.

### ÉPICA 2: Autenticación, Perfiles y Catálogo de Servicios (58 Horas)

* **HU-06: Autenticación segura de usuarios y personal** (12h)

  * *Narrativa:* Como Usuario (Cliente/Personal), quiero iniciar sesión de forma segura, para acceder a mis funcionalidades correspondientes.
  * *Criterios de Aceptación:*

    * **Dado** que un usuario ingresa credenciales válidas, **Cuando** presiona "Login", **Entonces** el sistema retorna un token JWT válido y redirige según su rol (Admin, Barbero, Cliente).
* **HU-07: Gestión del portafolio del Barbero** (10h)

  * *Narrativa:* Como Barbero, quiero actualizar mi perfil con fotos de mis cortes, para atraer más clientes a mi agenda.
  * *Criterios de Aceptación:*

    * **Dado** que el barbero accede a su perfil, **Cuando** sube una imagen (máx 5MB), **Entonces** el sistema optimiza y guarda la imagen asociándola a su galería pública.
* **HU-08: Configuración de horarios laborales de barberos** (14h)

  * *Narrativa:* Como Administrador, quiero definir los días laborables y turnos de cada barbero, para que la disponibilidad web sea precisa.
  * *Criterios de Aceptación:*

    * **Dado** que se contrata un nuevo barbero, **Cuando** el admin le asigna un turno (ej. L-V, 9am a 5pm), **Entonces** la interfaz de reservas genera slots únicamente dentro de esa franja.
* **HU-09: Control de acceso basado en roles (RBAC)** (10h)

  * *Narrativa:* Como Tech Lead, quiero restringir rutas y acciones en el sistema según el rol, para proteger los datos financieros del negocio.
  * *Criterios de Aceptación:*

    * **Dado** que un Barbero intenta acceder a la ruta `/admin/finanzas`, **Cuando** el servidor procesa la petición, **Entonces** se debe retornar un error HTTP 403 Forbidden.
* **HU-10: Mantenimiento del catálogo de servicios** (12h)

  * *Narrativa:* Como Administrador, quiero crear, editar o eliminar servicios (ej. Corte, Barba, Cejas) con sus precios, para mantener la oferta actualizada.
  * *Criterios de Aceptación:*

    * **Dado** que un administrador modifica el precio del servicio "Corte Clásico" a $25.000, **Cuando** guarda los cambios, **Entonces** las nuevas reservas reflejan el nuevo precio (sin alterar el histórico financiero).

### ÉPICA 3: Punto de Venta (POS) y Gestión Financiera (62 Horas)

* **HU-11: Módulo de Checkout y facturación de servicios** (16h)

  * *Narrativa:* Como Administrador, quiero procesar el pago de un servicio finalizado, para registrar el ingreso y liberar al barbero.
  * *Criterios de Aceptación:*

    * **Dado** que un servicio marcado como "Finalizado" es seleccionado en el POS, **Cuando** el admin procesa el pago (Efectivo/Tarjeta), **Entonces** el estado cambia a "Pagado" y se genera un recibo digital.
* **HU-12: Motor de cálculo de comisiones automatizadas** (16h)

  * *Narrativa:* Como Barbero, quiero que mis comisiones se calculen automáticamente tras cada pago, para tener control exacto de mis ingresos diarios.
  * *Criterios de Aceptación:*

    * **Dado** que el barbero tiene un % de comisión asignado (ej. 40%), **Cuando** un cliente paga un servicio de $50.000 realizado por él, **Entonces** el sistema acredita $20.000 al saldo pendiente del barbero.
* **HU-13: Historial de transacciones y auditoría** (10h)

  * *Narrativa:* Como Administrador, quiero visualizar todas las transacciones diarias, para cuadrar la caja al final del día.
  * *Criterios de Aceptación:*

    * **Dado** que el admin consulta la fecha actual, **Cuando** visualiza el panel de transacciones, **Entonces** ve un listado detallado con métodos de pago, totales y servicios asociados.
* **HU-14: Descuento de insumos por servicio** (10h)

  * *Narrativa:* Como Administrador, quiero que que ciertos servicios descuenten unidades de inventario, para evitar mermas ocultas.
  * *Criterios de Aceptación:*

    * **Dado** que el servicio "Mascarilla" requiere 1 unidad de insumo, **Cuando** se factura este servicio, **Entonces** el inventario del producto "Mascarilla Negra" se reduce en 1 unidad.
* **HU-15: Cierre de caja y liquidación de barberos** (10h)

  * *Narrativa:* Como Administrador, quiero ejecutar un cierre de caja, para emitir los pagos a los barberos y resetear la jornada financiera.
  * *Criterios de Aceptación:*

    * **Dado** que el admin hace clic en "Cerrar Caja", **Cuando** confirma la acción, **Entonces** el sistema consolida los ingresos, marca las comisiones como "Liquidadas" y genera un reporte inmutable en PDF.

### ÉPICA 4: Innovación, Fidelización y Analítica (60 Horas)

* **HU-16: Dashboard analítico para toma de decisiones** (12h)

  * *Narrativa:* Como Administrador, quiero un panel gráfico con KPIs (Servicios más vendidos, ingresos por mes, barbero más productivo), para evaluar la salud del negocio.
  * *Criterios de Aceptación:*

    * **Dado** que el admin accede al Dashboard, **Cuando** se carga la vista, **Entonces** visualiza gráficos estadísticos actualizados que cruzan los datos de los últimos 30 días.
* **HU-17: Historial de preferencias del cliente** (10h)

  * *Narrativa:* Como Barbero, quiero ver el histórico de cortes y notas de un cliente, para brindarle un servicio hiper-personalizado.
  * *Criterios de Aceptación:*

    * **Dado** que el barbero revisa el perfil del cliente, **Cuando** visualiza su historial, **Entonces** puede ver fechas anteriores, servicios tomados y leer notas internas (ej. "Alergia a la loción X").
* **HU-18: Sistema de calificación y feedback** (8h)

  * *Narrativa:* Como Cliente, quiero poder calificar de 1 a 5 estrellas el servicio recibido, para ayudar a mantener el estándar de calidad.
  * *Criterios de Aceptación:*

    * **Dado** que un servicio ha sido facturado, **Cuando** el cliente recibe el enlace web de evaluación, **Entonces** puede dejar su puntuación, la cual promediará el rating público del barbero.
* **HU-19: \[INNOVACIÓN] Motor Predictivo de No-Shows (Parte 1: Recolección y Scoring)** (16h)

  * *Narrativa:* Como Sistema, requiero perfilar a los clientes basándome en su historial de asistencia, para clasificar su riesgo de inasistencia.
  * *Criterios de Aceptación:*

    * **Dado** que un cliente intenta agendar, **Cuando** el sistema evalúa su perfil, **Entonces** calcula un `RiskScore` basado en cancelaciones tardías previas y no-shows históricos utilizando algoritmos de machine learning (`scikit-learn` / `pandas`).
* **HU-20: \[INNOVACIÓN] Motor Predictivo (Parte 2: Mitigación Activa)** (14h)

  * *Narrativa:* Como Administrador, quiero que el sistema requiera automáticamente un pago por adelantado a clientes de alto riesgo, para proteger los ingresos de la barbería.
  * *Criterios de Aceptación:*

    * **Dado** que un cliente tiene un `RiskScore` superior al 30%, **Cuando** selecciona "Confirmar Reserva", **Entonces** el sistema le exige un abono del 50% vía pasarela de pagos antes de asegurar su slot.

*(Suma Total de Horas: 60 + 58 + 62 + 60 = 240 Horas Exactas).*

---

## SECCIÓN 3: PROPUESTA DE INNOVACIÓN (DESIGN THINKING - ENTREGA 2)

**Funcionalidad Innovadora:** *SmartGuard: Algoritmo Predictivo de Riesgo de No-Shows y Cobro Dinámico (HU-19 y HU-20).*
Esta característica no es un requerimiento típico de un cliente convencional (quien suele pedir solo una "agenda web"), pero ataca directamente la mayor métrica de dolor del negocio.

**Ciclo de Design Thinking Aplicado:**

1. **Empatizar:** Mediante entrevistas contextuales a dueños de barberías, descubrimos que el 25% de las reservas web nunca se presentan, generando lucro cesante. Los barberos se frustran al estar inactivos, perdiendo el dinero que ganarían a comisión.
2. **Definir:** El problema principal no es la falta de clientes, sino la falta de "compromiso" en las reservas digitales gratuitas, combinado con el temor del dueño de exigir pagos por adelantado a *todos* los clientes y perder volumen de agendamientos.
3. **Idear:** En lugar de exigir cobros a todos, ideamos un sistema de *Scoring de Confianza*. Los clientes nuevos o con historial de inasistencias requerirán un abono de garantía (50%); los clientes VIP o recurrentes con buena reputación podrán agendar "a un solo clic" gratis.
4. **Prototipar:** Se diseñará el diagrama de flujo lógico y la interfaz (UI) utilizando Shadcn/UI y Tailwind CSS v4, donde en la pasarela de confirmación, una regla de negocio en el backend (Python 3.12 / Django 5 + DRF) verifica el historial relacional (PostgreSQL) y condicionalmente renderiza un módulo de cobro o una confirmación directa.
5. **Evaluar:** Desplegaremos este módulo en modo *Shadow* (sólo calculando el riesgo sin cobrar) durante el primer mes para calibrar los falsos positivos antes de activar el cobro forzoso y medir la reducción real del porcentaje de No-Shows frente a la retención de usuarios.

---

## SECCIÓN 4: HOJA DE RUTA POR SPRINTS (Sprints de 2 semanas)

* **Sprint 0 (Setup y Arquitectura):** Inicialización de repositorios, configuración de CI/CD (GitHub Actions a Vercel/Render), modelado de la base de datos (PostgreSQL/Supabase), setup del framework base (React 19, Python 3.12 / Django 5, Zustand) y Dockerización del entorno.
* **Sprint 1 - Entrega 5 (Cimientos y Auth):**

  * HUs a desarrollar: HU-06, HU-07, HU-10, HU-01, HU-02.
  * *Objetivo:* El cliente puede registrarse, ver servicios, ver disponibilidad del barbero y crear una reserva en la base de datos.
* **Sprint 2 - Entrega 6 (Gestión Operativa y Core de Innovación):**

  * HUs a desarrollar: HU-08, HU-09, HU-03, HU-04, HU-19.
  * *Objetivo:* Los administradores pueden gestionar horarios, roles y ausencias, y el backend comienza a registrar y calcular el `RiskScore` de inasistencias.
* **Sprint 3 - Entrega 7 (Transacciones y Automatización):**

  * HUs a desarrollar: HU-05, HU-11, HU-12, HU-14, HU-20.
  * *Objetivo:* Se implementan notificaciones, el módulo de POS (Check-out), el descuento de inventario, el cálculo de la nómina de barberos y el cobro dinámico para clientes riesgosos.
* **Sprint 4 - Entrega 8 (Estabilización, Analítica y Cierre):**

  * HUs a desarrollar: HU-13, HU-15, HU-16, HU-17, HU-18.
  * *Objetivo:* Implementación del Dashboard analítico, cierre de cajas, feedback del cliente, pruebas de integración (Pytest-Django / Vitest), acta de aceptación y despliegue del release v1.0.

---

## SECCIÓN 5: ESTRATEGIA DE HERRAMIENTAS Y DOCUMENTACIÓN

**a) Stack Tecnológico Definitivo:**

* **Frontend:** React 19 + Tailwind CSS v4 + Zustand
* **Backend & IA:** Python 3.12 / Django 5 (Django REST Framework) + `scikit-learn` / `pandas` (*SmartGuard*)
* **Base de Datos & Auth:** PostgreSQL (Supabase) + JWT (`djangorestframework-simplejwt`) + Django ORM
* **Testing & Calidad:** Vitest (Frontend) + Pytest-Django (Backend) + ESLint / Ruff / Black
* **DevOps & Hosting:** Vercel (Frontend) + Render (Backend Django API) + Docker & GitHub Actions

**b) NotebookLM (Motor de Conocimiento y Q&A del Proyecto):**

* **Fuentes a Cargar:** Syllabus y rúbricas de la materia 750031C, actas de requerimientos en PDF, especificaciones técnicas de la arquitectura, y transcripciones de las reuniones de Planning/Retrospectiva.
* **Uso/Prompts Sugeridos:** Utilizar NotebookLM como asistente del Scrum Master con prompts como: *"Basado en los requerimientos de la Entrega 6 y el acta de reunión de ayer, ¿qué criterios de aceptación faltan por definir para el módulo de horarios?"* o *"Resume los riesgos técnicos documentados sobre la integración de la pasarela de pagos"*.

**c) Jira (Tableros Scrum y Flujo de Trabajo):**

* **Estructura:** Tipo de Proyecto: *Scrum de Software*. Crear las 4 Épicas y asociar las 20 Historias de Usuario correspondientes.
* **Flujo de Estados:** `To Do` → `In Progress` (desarrollo activo) → `In Review` (Pull Request abierto en GitHub, code review) → `QA` (Pruebas en entorno staging) → `Done`.
* **Etiquetas/Componentes:** Utilizar etiquetas obligatorias: `frontend`, `backend`, `database`, `innovation`, `bug`.

**d) Notion / Confluence (Bitácora Activa y Documentación Formal):**

* **Carpeta 1 - Planificación e Inicio:** Acta de Constitución (Project Charter), Matriz de Riesgos y Matriz de Stakeholders.
* **Carpeta 2 - Ceremonias Ágiles:** Actas de Sprint Planning, Daily Scrum logs (bloqueos identificados), Sprint Review y minutas de Retrospectivas.
* **Carpeta 3 - Arquitectura y QA:** Diagramas C4 (Contexto y Contenedores), Modelo Entidad-Relación de la base de datos relacional, Diccionario de datos y Reportes de Coevaluación del equipo para las entregas de la universidad.