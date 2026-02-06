# Reporte Técnico del Proyecto: Scraper BoxMagic

## 1. Visión General

Este proyecto es una solución robusta de web scraping automatizado diseñada para extraer, procesar y servir datos de la plataforma BoxMagic. El sistema monitorea reservas de clases (Check-in) y horarios (Calendario), exponiendo esta información a través de una API RESTful para su consumo por el frontend.

## 2. Arquitectura del Sistema

El núcleo del sistema está construido en **Python** utilizando **Playwright** para la navegación y **Flask** para el servidor API.

### Componentes Principales:

- **Scraper Engine:** Motor de navegación automatizada (Playwright Sync).
- **API Server:** Servidor HTTP (Flask) que gestiona los datos y endpoints.
- **Scheduler:** Planificador de tareas (APScheduler) para actualizaciones automáticas.
- **Persistencia:** Sistema de archivos JSON y Volúmenes Docker.

## 3. Funcionalidades Detalladas

### A. Módulo de Scraping (`src/scraper_playwright.py`)

El scraper implementa una lógica avanzada para interactuar con BoxMagic:

- **Login Robusto & Persistencia de Sesión:**
  - Manejo de múltiples selectores CSS para campos de usuario/contraseña, asegurando compatibilidad ante cambios en la UI.
  - Detección y navegación automática de páginas intermedias ("Admin Panel").
  - **Persistencia:** Guarda el estado de autenticación (cookies/storage) en `session.json`. Al reiniciar, intenta reutilizar la sesión; si falla, realiza un login automático y actualiza el archivo.
- **Scraping de Calendario (Horarios):**
  - Navegación filtrada por "Coach" (Profesor).
  - Interacción con modales: Abre cada evento individualmente para extraer detalles profundos (capacidad, profesores asignados, tipo de clase).
- **Scraping de Check-in (Reservas):**
  - **Estrategia Híbrida Inteligente:** Navega a la página de check-in una sola vez y luego manipula el DOM (JavaScript/jQuery) para cambiar fechas sin recargas completas.
  - **Probing de API Interna:** Intercepta/invoca directamente los endpoints internos de BoxMagic (`get_alumnos_clase`) para obtener la lista de alumnos, eludiendo la necesidad de parsear tablas HTML complejas y propensas a errores. Esto garantiza datos estructurados (IDs, teléfonos, emails, estado de pago).
- **Resiliencia:**
  - Reintentos automáticos en selectores fallidos.
  - Manejo de `ZoneInfo` para asegurar consistencia horaria (America/Santiago).

### B. Servidor API & Scheduling (`api_server.py`)

- **API REST Client-Facing:**
  - `GET /api/checkin`: Datos históricos y futuros de reservas.
  - `GET /api/calendar`: Datos de horarios de clases.
  - `GET /api/status`: Estado de salud del scraper y timestamps de última ejecución.
  - `GET /api/all-data`: Payload completo para sincronización inicial.
  - `POST /api/scrape/now`: Trigger para actualización manual inmediata.
- **Automatización (APScheduler):**
  - **Check-in:** Se ejecuta cada **15 minutos** (ventana de 7 días). Fusiona datos nuevos con existentes para no perder historial.
  - **Calendario:** Se ejecuta diariamente a las **3:00 AM**.
- **Keep-Alive:** Un mecanismo de "auto-ping" que evita que el servicio se duerma en el Free Tier de Render, golpeando su propio endpoint `/health` cada 14 minutos.

### C. Infraestructura y Despliegue (Docker/Render)

- **Dockerización (`Dockerfile`):**
  - Imagen base: `mcr.microsoft.com/playwright/python:v1.46.0-jammy`.
  - Incluye navegadores Chromium y dependencias de sistema necesarias.
- **Persistencia de Volúmenes (`render.yaml`):**
  - Disco `scraper-data` montado en `/opt/render/project/src/data`.
  - **Función:** Almacena `latest_checkin.json`, `latest_calendar.json` y `session.json`. Esto permite que el scraper recuerde sus datos y login incluso si el contenedor se reinicia o redeploya.
  - **Navegadores Persistentes:** Configura `PLAYWRIGHT_BROWSERS_PATH` en el disco persistente para evitar descargar el navegador en cada reinicio, acelerando el arranque.

## 4. Pruebas Locales

El sistema está diseñado para ser probado localmente:

- Mecanismo `if __name__ == '__main__':` en scripts para ejecución aislada.
- Configuración de entorno flexible que detecta si corre en Render o Local para ajustar rutas de archivos.

## 5. Estimación de Tiempos y Esfuerzo de Desarrollo

Basado en la complejidad de las funcionalidades y el historial de iteraciones:

| Funcionalidad                    | Tiempo Estimado | Detalles                                                                                |
| :------------------------------- | :-------------- | :-------------------------------------------------------------------------------------- |
| **Scraper Core & Login**         | ~5 horas        | Lógica de selectores dinámicos, manejo de sesión, navegación resiliente.                |
| **Check-in Logic (API Probing)** | ~4 horas        | Investigación de API interna de BoxMagic, lógica de inyección JS para cambio de fechas. |
| **Calendario & Modales**         | ~3 horas        | Iteración sobre selectores de modales, extracción de datos anidados.                    |
| **API Server & Scheduler**       | ~3 horas        | Setup de Flask, endpoints, integración de APScheduler, lógica de fusión de datos JSON.  |
| **Docker & Render Config**       | ~2 horas        | Configuración de volúmenes, rutas de navegadores, debugging de entorno Cloud.           |
| **Pruebas y Depuración**         | ~3 horas        | Ajustes de timeouts, corrección de selectores en producción, manejo de zonas horarias.  |
| **Total Aproximado**             | **~20 horas**   | Desarrollo acelerado con foco en funcionalidades core.                                  |

## 6. Tecnologías Clave

- **Lenguaje:** Python 3.10+
- **Scraping:** Playwright Sync, BeautifulSoup (auxiliar implícito en lógica)
- **Web Server:** Flask, Flask-CORS
- **Scheduling:** APScheduler
- **Infraestructura:** Docker, Render (Web Service + Persistent Disk)
