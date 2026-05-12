# Observatorio de Investigación UNAL Bogotá

Proyecto grupal para visualizar, filtrar, clasificar y gestionar información de proyectos de investigación de la Universidad Nacional de Colombia, Sede Bogotá.

El sistema parte de un archivo maestro en Excel, construye una base de datos local y expone un dashboard web con filtros, tarjetas, tabla de proyectos y formulario de registro.

## Objetivo

Desarrollar una plataforma web que permita:

- Consultar proyectos de investigación de forma organizada.
- Filtrar proyectos por departamento, año, estado y categoría.
- Preparar los datos para un modelo de clasificación automática.
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
│   ├── limpieza.py            
│   └── build_database.py       
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
Excel original
→ scripts/limpieza.py
→ data/processed/dataset_maestro_proyectos.xlsx
→ scripts/build_database.py
→ data/processed/proyectos.db
→ API FastAPI
→ Dashboard web
```

Archivos generados:

| Archivo | Uso |
|---------|-----|
| `data/processed/dataset_maestro_proyectos.xlsx` | Dataset limpio y agrupado por proyecto |
| `data/processed/proyectos.db` | Base de datos SQLite usada por el backend |
| `data/dashboard/proyectos_from_db.json` | JSON de respaldo para modo estático |
| `data/processed/ml_dataset.csv` | Dataset textual para el modelo de clasificación |

## Regenerar los datos

Desde la raíz del proyecto:

```bash
venv/bin/python scripts/limpieza.py
venv/bin/python scripts/build_database.py
```

El primer comando limpia el Excel original ubicado en `data/raw/`. El segundo comando reconstruye la base SQLite, el JSON del dashboard y el CSV para machine learning.

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
- Dataset preparado para una futura etapa de clasificación con machine learning.

## Notas técnicas

- La versión actual usa SQLite para facilitar el desarrollo local.
- Para producción o uso grupal permanente se recomienda migrar a PostgreSQL.
- El frontend intenta usar `/api/projects` y `/api/categories`. Si la API no está disponible, usa los JSON locales como respaldo.
- El archivo `data/processed/ml_dataset.csv` contiene el texto consolidado que puede alimentar el modelo de clasificación.

## Estado del proyecto

Versión funcional inicial con dashboard, pipeline de datos y backend básico. La siguiente etapa recomendada es conectar una base PostgreSQL y agregar autenticación o control de edición si el proyecto se usará por varios usuarios.
