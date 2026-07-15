# LUKA Frontend

Plataforma web complementaria para el bot financiero LUKA en WhatsApp.
Provee un dashboard visual interactivo y detallado, utilizando Jinja2, HTMX, y Chart.js sobre FastAPI.

## Tecnologías Utilizadas

- **Backend**: Python 3 con [FastAPI](https://fastapi.tiangolo.com/) y SQLAlchemy.
- **Frontend**: Plantillas Jinja2 con HTML puro, [HTMX](https://htmx.org/) para reactividad del lado del servidor sin necesidad de recargar la página.
- **Estilos**: Vanilla CSS con diseño avanzado (Dark mode, Glassmorphism, CSS Grid).
- **Gráficos**: [Chart.js](https://www.chartjs.org/) para métricas dinámicas.
- **Base de Datos**: PostgreSQL vía Supabase (reutilizando los datos guardados por el bot LUKA).

## Contrato de base de datos compartido

Las migraciones de la base compartida pertenecen a `blob1618/luka`. Este repositorio
solo mantiene modelos SQLAlchemy consumidores compatibles; no debe usarse
`Base.metadata.create_all()` para modificar la instancia compartida de Supabase.

## Estructura del Proyecto

```text
luka_frontend/
├── app/
│   ├── main.py              # Entrypoint de FastAPI y rutas HTMX
│   ├── auth.py              # Generación y validación de tokens de sesión
│   ├── dashboard.py         # Consultas a la base de datos para armar las métricas
│   ├── models/
│   │   └── database.py      # Conexión SQLAlchemy y declaración de tablas
│   └── templates/
│       ├── base.html        # Layout principal (Sidebar, dependencias JS/CSS)
│       ├── dashboard.html   # Estructura del dashboard principal
│       ├── login.html       # Interfaz de "magic link"
│       └── partials/        # Archivos que se recargan vía HTMX
│           ├── charts.html
│           ├── stats.html
│           └── transactions.html
├── static/
│   └── css/
│       └── style.css        # Hoja de estilos del proyecto
├── .env                     # Variables de entorno locales
├── .env.example             # Plantilla de variables
├── render.yaml              # Configuración de despliegue como código
└── requirements.txt         # Dependencias Python
```

## Ejecutar en Local

1. Crea y activa tu entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura tu `.env` tomando como base `.env.example`. **Asegurate de que tu puerto en la URL de Supabase sea el `6543` (el transaction pooler para evitar errores de red).**
4. Arranca el servidor local en modo desarrollo:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```
5. Para probar sin necesidad del bot de WhatsApp, abrí `http://localhost:8001/dev-login` que iniciará sesión automáticamente.

## Despliegue en Producción (Render)

### Opción 1: Usar Render Blueprint (Automático)
Dado que el repositorio incluye un archivo `render.yaml`, solo tienes que conectar el repositorio de GitHub en el dashboard de Render en la sección "Blueprints".

### Opción 2: Web Service Manual
Si creas el Web Service manualmente en Render, utiliza la siguiente configuración:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Variables de entorno necesarias
No te olvides de configurar las siguientes **Environment Variables** en Render:
- `DATABASE_URL` (Debe ser idéntica a la que usás localmente).
- `SECRET_KEY` (Generá un texto largo, aleatorio y seguro para cifrar las cookies de los usuarios).
