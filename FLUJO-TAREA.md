# Flujo de trabajo por tarea de Jira (BarberFlow OS)

Procedimiento para trabajar una tarea de Jira con un asistente de IA (Claude Code, Codex, Cursor, Copilot, etc.). Aplica las reglas de `AGENTS.md` (§3 modo tarea finita, §4 stack, §5 DoR/DoD, §6 Git).

Tiene dos fases: **INICIAR** (al empezar la tarea) y **CERRAR** (al terminarla). El asistente trabaja **una sola tarea** y se detiene al final de cada fase.

> En Claude Code hay atajos: `/tarea <ID>` ejecuta INICIAR y `/cerrar-tarea` ejecuta CERRAR. Con otras herramientas, escribe por ejemplo: *"Inicia la tarea HU-06-T01 siguiendo FLUJO-TAREA.md"* o *"Cierra la tarea siguiendo FLUJO-TAREA.md"*.

---

## Fase INICIAR

### Paso 0. Identifica al programador y su rol
1. Lee `AGENTS.md` §2: "Usuario Activo" y tabla de roles.
2. Confirma con el usuario con una pregunta corta: "Veo que eres <nombre> (<rol>). ¿Es correcto?". Si dice que no, ubica a la persona correcta en la tabla y usa su rol. Si no está en la tabla, pregunta su rol.
3. Adapta el trabajo al rol:
   - Frontend / UI: React 19, Tailwind v4, Shadcn, Zustand, Vitest.
   - Backend: Django 5, DRF/Ninja, pytest-django.
   - QA / DevOps: pruebas, CI/CD, Docker.
   - Datos / SmartGuard: scikit-learn, pandas.
   - Scrum Master / Tech Lead: puede tocar todo el stack.
4. Si la tarea cae claramente fuera del rol, díselo y pregunta si continúa o la deja para quien corresponde. No decidas por él.

### Paso 1. Ticket y DoR (AGENTS.md §5)
El asistente no puede leer Jira: el usuario debe pegar el texto del ticket. Si falta el ID de la tarea, pregúntalo.
Verifica que el ticket tenga:
- [ ] Narrativa "Como [Rol], quiero [Acción], para [Beneficio]".
- [ ] Criterios de aceptación Dado/Cuando/Entonces.
- [ ] Estimación en horas.
- [ ] Mockup/prototipo, si es tarea de UI.

Si falta algo, **detente**: lista lo que falta, haz preguntas concretas y no escribas código hasta resolverlo.

### Paso 2. Clasifica y confirma el alcance
1. Clasifica la tarea: `feat:`, `fix:`, `docs:` o `test:`.
2. Resume en 3 a 5 líneas qué vas a hacer y qué NO vas a hacer.
3. Haz las preguntas que realmente cambien la solución (supuestos de negocio, casos borde, dependencias de otras HU). Máximo 3. Espera la respuesta antes de seguir.

### Paso 3. Rama
- Comprueba con `git status` que el árbol esté limpio.
- Parte de `develop` actualizado y crea `feature/<ID>` (ej. `feature/HU-06`). Si la rama ya existe, pregunta si continuar en ella.
- No trabajes sobre `develop` ni `main`.

### Paso 4. Tests primero
- Traduce cada criterio de aceptación a un test con estructura Dado/Cuando/Entonces (pytest-django o Vitest/React Testing Library).
- Ejecútalos y confirma que fallan por la razón correcta.

### Paso 5. Implementa solo esta tarea
- Usa únicamente el stack de `AGENTS.md` §4. No agregues librerías ni arquitecturas nuevas; si una dependencia es imprescindible, pregunta antes.
- Backend: endpoints tipados y limpios, respuestas JSON estándar, latencia objetivo < 200 ms. Dependencias nuevas en `backend/requirements.txt` o `requirements-dev.txt`.
- Frontend: componentes funcionales con Hooks, Tailwind v4, estado con Zustand.
- No toques archivos ajenos a la tarea ni refactorices de más.

### Paso 6. Verifica en local (igual que el CI)
- Backend: `black --check .`, `ruff check .`, `python manage.py check`, `python -m pytest -v` (en el contenedor con `docker compose exec backend ...` o en el entorno local).
- Frontend: `npm run lint`, `npm run format:check`, `npm run test`, `npm run build` (en el contenedor con `docker compose exec frontend ...` o en local).
- Si `docker compose ps` muestra los contenedores arriba, usa `docker compose exec -T <servicio> ...`: el Python/Node del host puede no tener las dependencias.
- Si `black`/`ruff`/`prettier` fallan en tus archivos, aplícalos (`black <archivo>`, `ruff check --fix <archivo>`) y vuelve a verificar.
- Ejecuta solo lo que corresponda a lo que tocaste. Si algo falla, corrígelo; si no puedes, repórtalo tal cual.

### Paso 7. Entrega y detente
Resume: qué cambió, qué tests lo cubren, qué comandos pasaron y cuáles no, y qué queda pendiente. Termina con: "Cuando estés listo, cierra la tarea." No hagas commit en esta fase y no pases a otra tarea.

---

## Fase CERRAR

### Paso 0. Identifica al programador
1. Lee `AGENTS.md` §2. Si ya confirmaste la identidad del usuario en esta misma sesión (fase INICIAR), no vuelvas a preguntar; si no, confirma: "Cierro esta tarea como <nombre> (<rol>), ¿correcto?".
2. Compara con `git config user.name`. Si no coinciden, avísalo y pregunta cuál usar para los datos del PR. No cambies la configuración de git.

### Paso 1. Revisa el estado
- `git status` y `git diff` contra `develop`.
- Confirma que estás en `feature/<ID>` y no en `develop` ni `main`. Si no, detente y pregunta.
- Si hay cambios que no pertenecen a la tarea, señálalos y pregunta qué hacer con ellos. No los incluyas por tu cuenta.

### Paso 2. Verifica el DoD comprobable en local (AGENTS.md §5)
Ejecuta las verificaciones del Paso 6 de INICIAR que correspondan y muestra el resultado real. Luego revisa cada criterio de aceptación Dado/Cuando/Entonces y di si hay un test que lo cubre. Si algo falla o falta cobertura, **detente**, explícalo y no hagas commit.

### Paso 3. Commit convencional
- Propón el mensaje: `feat|fix|docs|test: <descripción en español, imperativo>`, con el ID de Jira en el cuerpo.
- Muéstralo y pide confirmación antes de hacer el commit. Agrega solo los archivos de la tarea (nunca `git add .` a ciegas, nunca `.env`).
- No hagas push ni abras el PR sin confirmación del usuario.

### Paso 4. Prepara el PR hacia `develop`
Redacta la descripción con `.github/PULL_REQUEST_TEMPLATE.md`:
- Descripción del cambio.
- ID de Jira y tipo de cambio marcado.
- Checklist DoD: marca solo lo que realmente verificaste. Deja sin marcar la revisión de un par.
- Evidencia, si aplica.

Pregunta si el usuario quiere que hagas el push y abras el PR (por ejemplo con `gh`) o si prefiere hacerlo él.

### Paso 5. Lo que sigue es humano
Recuérdalo según el flujo de Jira (`To Do → In Progress → In Review → QA → Done`):
1. Mover el ticket a `In Review` cuando el PR esté abierto.
2. Code review de al menos un par (`AGENTS.md` §5). Sugiere a quién pedírselo según los roles (ej. Reinel Vargas como Tech Lead para backend), sin asignarlo tú. Revisor de respaldo: Brandon Jimenez (`@brandonjimenez21`), que GitHub solicita automáticamente vía `.github/CODEOWNERS`, para que el flujo no se trabe. Si el PR es de Brandon, GitHub no le permite aprobarlo: debe revisarlo otro compañero.
3. Despliegue en Staging y validación manual de QA (Esteban Rivera).

Termina ahí. No empieces otra tarea.
