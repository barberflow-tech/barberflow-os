# AGENTS.md - Contexto de Proyecto y Lineamientos para Agentes de IA

## 1. Visión General del Proyecto
- **Proyecto:** BarberFlow OS
- **Empresa Desarrolladora:** BarberFlow Technologies
- **Descripción:** Ecosistema SaaS B2B multitenant para el sector de cuidado personal y estética en Colombia (barberías de 3 a 10 sillas). Permite agendamiento en tiempo real, gestión POS/Caja, liquidación de comisiones y reducción de ausentismo (*No-Shows*) mediante scoring predictivo (*SmartGuard*).
- **Esfuerzo Total Planificado:** 240 horas divididas en 4 Épicas (20 Historias de Usuario) a lo largo de 5 Sprints (Sprint 0 a Sprint 4).

---

## 2. Asignación de Roles e Identidad de Integrantes

⚠️ **DESARROLLADOR ACTIVO ACTUAL EN ESTE REPOSITORIO / ENTORNO:**
- **Usuario Activo:** Brandon Stiven Jimenez Romero
- **Rol:** Scrum Master / Lead Full-Stack Developer
- **Enfoque de Trabajo:** Facilitador ágil, integración Full-Stack (React 19 / Django 5), orquestación de la arquitectura.

*(Nota para el equipo: Cada integrante debe cambiar el "Usuario Activo" anterior por su nombre en su rama/entorno local).*

| Nombre del Integrante | Rol Oficial | Responsabilidades & Alcance Principal |
| :--- | :--- | :--- |
| **Brandon Stiven Jimenez Romero** | Scrum Master / Lead Full-Stack Developer | Gestión de tableros (Jira/Notion), facilitador ágil, remoción de bloqueos e integración Full-Stack (React 19 / Django 5). |
| **Daniel Escobar Bahoz** | Product Owner / Frontend Specialist | Definición de criterios de aceptación, priorización del backlog, validación de entregas e implementación UI (React 19 / Tailwind v4). |
| **Reinel Fabián Vargas Méndez** | Tech Lead / Full-Stack Developer | Arquitectura API REST Django 5 (DRF), modelado de BD (PostgreSQL/Supabase), revisión de PRs y decisiones técnicas. |
| **Esteban Rivera González** | QA Engineer & DevOps Specialist | Pipelines CI/CD (GitHub Actions), pruebas automatizadas (Vitest / Pytest), contenedores Docker y despliegue (Render / Vercel). |
| **Jose Otoniel Henao Montes** | UI/UX Designer & Data Analyst | Prototipado en Figma, maquetación de componentes UI (Tailwind v4 / Shadcn) y desarrollo del modelo predictivo SmartGuard (`scikit-learn` / `pandas`). |

## 3. Regla Fundamental de Ejecución: Modo Tarea Finito (No Auto-Completar el Proyecto)

⚠️ **REGLA ESTRICTA DE TRABAJO EN PAREJA / ASISTENTE:**
1. **Paso a paso explícito:** EL AGENTE NO DEBE GENERAR NI INTENTAR RESOLVER TODO EL PROYECTO O MÓDULOS COMPLETOS DE UNA SOLA VEZ.
2. **Foco en Tareas de Jira:** El agente trabajará **únicamente** sobre la tarea o ticket de Jira específico que el desarrollador le indique en la solicitud (ej. `TSK-01`, `HU-06-T01`).
3. **Identificación del Tipo de Trabajo:** Antes de escribir código o proponer cambios, el agente debe clasificar la tarea y ajustar su respuesta al tipo correspondiente:
   - `feat:` (Nueva característica o funcionalidad)[cite: 16]
   - `fix:` (Corrección de un bug o error)[cite: 16]
   - `docs:` (Documentación, actas o comentarios)[cite: 16]
   - `test:` (Creación o ajuste de pruebas unitarias/integración)
4. **Respuesta Acotada:** Limítate a entregar **solo** el código o la solución del paso solicitado. No avances a la siguiente tarea ni asumas requerimientos no pedidos.

---

## 4. Stack Tecnológico Estándar
Cualquier código generado o sugerido DEBE ajustarse estrictamente a estas tecnologías:

- **Frontend:** React 19, Tailwind CSS v4, Shadcn/UI, Zustand (Estado global)[cite: 14, 16].
- **Backend API:** Python 3.12+ / Django 5 (Django REST Framework / Django Ninja)[cite: 14, 16].
- **Base de Datos & Auth:** PostgreSQL instanciado en Supabase, JWT (`djangorestframework-simplejwt`) con Control de Acceso Basado en Roles (RBAC: Admin, Barbero, Cliente)[cite: 12, 14, 16].
- **Módulo de Innovación (SmartGuard):** Python (`scikit-learn`, `pandas`) para el modelo predictivo de ausentismo y cálculo de *RiskScore*[cite: 14, 16].
- **Testing & Calidad:** Vitest / React Testing Library (Frontend), `pytest-django` (Backend), ESLint, Prettier, Black/Ruff[cite: 14, 16].
- **DevOps & Entorno:** Docker (`docker-compose.yml`), GitHub Actions (CI/CD), Vercel (Hosting Frontend), Render (Hosting API Backend)[cite: 14, 16, 17].

---

## 5. Gobernanza y Rúbricas de Calidad (DoR & DoD)

### Definition of Ready (DoR)
Una tarea/HU se inicia solo si posee:
1. Narrativa: *Como [Rol], quiero [Acción], para [Beneficio]*.
2. Criterios de Aceptación estructurados (*Dado/Cuando/Entonces*).
3. Estimación formal en horas (Jira).
4. Mockup o prototipo UI asignado (si aplica).

### Definition of Done (DoD)
Una tarea/HU está terminada únicamente si:
1. Pasa las pruebas en Vitest / Pytest sin errores.
2. Pasa revisión de código (Code Review) en GitHub por un par y merge a `develop`[cite: 11, 16].
3. Está desplegada y funcional en ambiente Staging (Vercel/Render).
4. Es validada manualmente por el QA Engineer (Esteban Rivera).

---

## 6. Convenciones de Desarrollo y Git

- **Estrategia de Ramas:** GitFlow (`main`, `develop`, ramas de característica `feature/HU-XX`).
- **Formato de Commits:** *Conventional Commits* obligatorio:
  - `feat: ...` (nuevas características)
  - `fix: ...` (corrección de errores)
  - `docs: ...` (documentación)
  - `test: ...` (adición o modificación de pruebas)
- **Flujo Docker Local:**
  - El entorno corre vía `docker compose up -d` (Backend en puerto 5000, PostgreSQL en puerto 5432).
  - Instalación de paquetes backend dentro de contenedor: `docker compose exec backend npm install <pkg>` o mediante reconstrucción.

---

## 7. Arquitectura y Módulos Clave (Las 4 Épicas)

1. **Épica 1: Agendamiento en Tiempo Real (HU-01 a HU-05)**
   - Reserva pública para clientes, selección de barberos, disponibilidad en vivo, reprogramación y bloqueos de agenda.
2. **Épica 2: Autenticación & RBAC (HU-06 a HU-10)**
   - Registro, login, gestión de perfiles, roles y asignación de permisos.
3. **Épica 3: POS & Caja Diaria (HU-11 a HU-15)**
   - Facturación en punto de venta, pasarela/métodos de pago, liquidación de comisiones por barbero, descuento automático de insumos y cierre de caja.
4. **Épica 4: Innovación & Analítica - SmartGuard (HU-16 a HU-20)**
   - Algoritmo de scoring predictivo basado en datos históricos (completadas vs. canceladas a última hora).
   - Si la puntuación de riesgo (*RiskScore*) es alta, exige confirmación previa (vía WhatsApp/SMS) o sugiere horarios de menor demanda; si es baja, confirma la reserva de inmediato.

---

## 8. Instrucciones Directas para Agentes de IA

Cuando trabajes en este repositorio, debes seguir los siguientes principios:
1. **Calidad de Respuesta:** No inventes arquitecturas, librerías ni dependencias distintas a las especificadas en la sección 3.
2. **Estilo de Código Backend:** Prioriza endpoints en Django REST Framework o Django Ninja estructurados con tipado estricto y código limpio.
3. **Estilo de Código Frontend:** Usa React 19 funcional con Hooks, Tailwind CSS v4 y manejo de estado claro con Zustand.
4. **Respeto a los Criterios de Aceptación:** Al escribir tests o implementar lógica de negocio, sigue la estructura *Dado/Cuando/Entonces*.
5. **Manejo de Respuestas HTTP:** La API debe responder con latencias `< 200 ms` y manejar respuestas JSON estándar.