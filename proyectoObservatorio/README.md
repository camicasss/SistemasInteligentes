# Observatorio de Investigación UNAL Bogotá

Proyecto grupal para visualizar, filtrar y gestionar información de proyectos de investigación de la Universidad Nacional de Colombia, Sede Bogotá.

El sistema parte de los archivos Excel descargados desde la fuente institucional, construye una base de datos local consolidada y expone un dashboard web con filtros, tarjetas, tabla de proyectos y formulario de registro.

## Objetivo

Desarrollar una plataforma web que permita:

- Consultar proyectos de investigación de forma organizada.
- Filtrar proyectos por departamento, año, estado y categoría.
- Registrar nuevos proyectos desde una interfaz web.
- Evolucionar hacia una base de datos compartida para trabajo colaborativo.

## Estructura del proyecto

```text
investigacion-unal/
├── index.html                
├── css/
│   └── styles.css              
├── js/
│   └── app.js                
├── backend/
│   └── main.py                
├── data/
│   ├── raw/                   
│   ├── processed/              
│   └── dashboard/             
├── scripts/
│   └── process_raw_products.py
├── requirements.txt          
├── Procfile                  
└── README.md
```

## Ejecución local recomendada

La forma recomendada de ejecutar el proyecto es usando el backend FastAPI. De esta manera, el dashboard lee y escribe información en la base SQLite.

```bash
venv/bin/pip install -r requirements.txt
venv/bin/python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Luego abrir:

```text
http://localhost:8000
```

Si el entorno virtual no está creado, se puede crear con:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/projects` | Lista los proyectos desde SQLite |
| POST | `/api/projects` | Registra un proyecto nuevo en SQLite |
| POST | `/api/import-data` | Recibe los dos Excel raw, reconstruye SQLite y actualiza el JSON del dashboard |
| GET | `/api/categories` | Lista categorías, subcategorías y estados |
| GET | `/api/health` | Verifica que el backend esté activo |

## Ejecución estática

También es posible ejecutar solo el frontend:

```bash
python3 -m http.server 8080
```

Luego abrir:

```text
http://localhost:8080
```

En este modo el dashboard usa el archivo `data/dashboard/proyectos_from_db.json` como respaldo. Los proyectos agregados desde el formulario no se guardan en una base compartida; solo quedan en el navegador mediante `localStorage`.

## Pipeline de datos

El flujo de datos del proyecto es:

```text
Excel maestro de proyectos/grupos + Excel de productos
→ scripts/process_raw_products.py
→ data/processed/datos_limpios.xlsx
→ data/processed/proyectos.db
→ API FastAPI
→ Dashboard web
```

Archivos necesarios:

| Archivo | Uso |
|---------|-----|
| `data/raw/reporteProyectoCoordinacionBas.xlsx` | Archivo maestro de proyectos. De aquí salen datos generales, investigador principal y grupo de investigación |
| `data/raw/reporteProyectoCoordinacionBasProductos.xlsx` | Archivo de productos. De aquí salen productos propuestos/logrados y susceptibilidad de protección |
| `data/processed/datos_limpios.xlsx` | Excel limpio con los mismos campos que consume la visualización |
| `data/processed/proyectos.db` | Base de datos SQLite usada por el backend |
| `data/dashboard/proyectos_from_db.json` | JSON de respaldo para modo estático |
| `data/dashboard/categorias.json` | Catálogo de macrocategorías, subcategorías y estados |

## Regenerar los datos

Desde la raíz del proyecto:

```bash
venv/bin/python scripts/process_raw_products.py
```

El script lee ambos Excel ubicados en `data/raw/`, los une por `codigo_hermes`, agrupa los productos por proyecto y reconstruye el Excel limpio, la base SQLite y el JSON que usa el dashboard.

Si todavía no existe el archivo maestro `reporteProyectoCoordinacionBas.xlsx`, el script usa temporalmente `reporteProyectoCoordinacionBasProductos.xlsx` como respaldo para los datos generales. En ese caso los grupos de investigación quedarán vacíos hasta cargar el archivo maestro.

También se puede actualizar desde el dashboard con el botón `Actualizar Datos`. Este flujo requiere correr la app con FastAPI, seleccionar los dos Excel en el modal y confirmar la actualización.

## Registro de proyectos

Desde la interfaz:

1. Abrir el dashboard con FastAPI.
2. Seleccionar `Nuevo Proyecto`.
3. Completar el formulario.
4. Guardar.

Cuando el proyecto corre con FastAPI, el registro se guarda en `data/processed/proyectos.db`. Cuando corre como sitio estático, se usa `localStorage` como respaldo local.

## Sistema de categorías

Las categorías y subcategorías se encuentran en:

```text
data/dashboard/categorias.json
```

Macrocategorías disponibles:

| ID | Macrocategoría |
|----|----------------|
| M01 | Energía Sostenible y Transición Energética |
| M02 | Ingeniería de Sistemas Inteligentes y Digitalización |
| M03 | Gestión Integral del Agua y Recursos Ambientales |
| M04 | Nuevos Materiales y Manufactura Avanzada |
| M05 | Materiales Avanzados y Nanotecnología para la Salud |
| M06 | Bioeconomía y Tecnologías Agroindustriales |
| M07 | Infraestructura Sostenible y Territorios Resilientes |
| M08 | Tecnologías para la Salud y Bioinformática |
| M09 | Economía Circular y Eco-diseño |
| M10 | Inclusión Social y Calidad de Vida |

## Funcionalidades

- Dashboard web con vista de tarjetas y tabla.
- Búsqueda por nombre, objetivo y palabras clave.
- Filtros por departamento, macrocategoría, subcategoría, año y estado.
- Modal con detalle de cada proyecto.
- Formulario para registrar proyectos.
- Backend FastAPI con lectura y escritura en SQLite.

## Notas técnicas

- La versión actual usa SQLite para facilitar el desarrollo local.
- Para producción o uso grupal permanente se recomienda migrar a PostgreSQL.
- El frontend intenta usar `/api/projects` y `/api/categories`. Si la API no está disponible, usa los JSON locales como respaldo.

## Estado del proyecto

Versión funcional inicial con dashboard, pipeline de datos y backend básico. La siguiente etapa recomendada es conectar una base PostgreSQL y agregar autenticación o control de edición si el proyecto se usará por varios usuarios.
