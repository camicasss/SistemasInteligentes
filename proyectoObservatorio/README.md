# Observatorio de Investigación UNAL Bogotá

Proyecto grupal para visualizar, filtrar, clasificar y gestionar información de proyectos de investigación de la Universidad Nacional de Colombia, Sede Bogotá.

El sistema parte de reportes en Excel, construye una base de datos y expone un dashboard web con filtros, tarjetas, tabla de proyectos, gráficas e importación de datos.

## Objetivo

Desarrollar una plataforma web que permita:

- Consultar proyectos de investigación de forma organizada.
- Filtrar proyectos por departamento, año, estado y categoría.
- Preparar los datos para un modelo de clasificación automática.
- Actualizar la base desde los reportes GRU y Productos.
- Revisar y ajustar manualmente la clasificación de proyectos cuando sea necesario.
- Trabajar en local con SQLite y en Railway con PostgreSQL.

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
│   ├── build_database.py
│   ├── update_from_excel.py
│   └── ml_classifier/
├── requirements.txt          
├── Procfile                  
└── README.md
```

## Ejecución local recomendada

La forma recomendada de ejecutar el proyecto es usando el backend FastAPI. De esta manera, el dashboard lee y escribe información en la base SQLite local.

```bash
venv/bin/pip install -r requirements.txt
venv/bin/python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Alternativamente, para abrir el proyecto automáticamente en tu navegador:

```bash
python run.py
```

Luego abrirá:

```text
http://localhost:8000
```

## Acceso y permisos

El dashboard se muestra inicialmente sin iniciar sesión y puede ser consultado por cualquier visitante. El usuario común no necesita cuenta ni credenciales: solo consulta la información pública. Únicamente el administrador inicia sesión, ve y puede usar la opción **Actualizar Excel**; esta restricción también se valida en la API.

Antes de desplegar, configure estas variables de entorno con valores seguros:

```bash
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="una-contrasena-segura"
export SESSION_SECRET="una-clave-aleatoria-larga"
export COOKIE_SECURE="true" # usar en HTTPS/producción
```

Para facilitar pruebas locales, si no se definen variables se usan `admin` / `admin123`. No use estas credenciales predeterminadas en producción.

Si el entorno virtual no está creado, se puede crear con:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Endpoints principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/projects` | Lista los proyectos |
| POST | `/api/auth/login` | Inicia una sesión de administrador |
| POST | `/api/auth/logout` | Cierra la sesión actual |
| POST | `/api/projects/import-excel` | Previsualiza o confirma una actualización desde los Excel GRU y Productos |
| PATCH | `/api/projects/{id}/classification` | Guarda una clasificación manual |
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

En este modo el dashboard usa el archivo `data/dashboard/proyectos_from_db.json` como respaldo. Sirve para consultar la información, pero la importación de Excel y los cambios de clasificación requieren el backend.

## Pipeline de datos

El flujo de datos del proyecto es:

```text
Excel original / reportes GRU y Productos
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

## Actualización desde Excel

Para actualizar la base sin reconstruirla desde cero, se puede usar el script:

```bash
venv/bin/python scripts/update_from_excel.py data/raw/reporteProyectoCoordinacionBasProductos.xlsx
```

Desde la interfaz se usa el botón `Actualizar Excel`. Allí se cargan dos archivos:

```text
GRU: reporte principal de proyectos
Productos: reporte con productos propuestos, logrados y protección
```

Primero se muestra una vista previa con proyectos nuevos, actualizados, sin cambios y sin código. Si todo está bien, se confirma la importación.

También se puede probar por consola sin guardar cambios:

```bash
venv/bin/python scripts/update_from_excel.py data/raw/reporteProyectoCoordinacionBasProductos.xlsx --dry-run
```

El script compara los proyectos por `codigo_hermes`, inserta los nuevos y actualiza los existentes solo cuando encuentra cambios reales. También conserva las categorías revisadas manualmente. En Railway la misma lógica corre sobre PostgreSQL.

## Clasificación manual

Al abrir el detalle de un proyecto, la interfaz permite ajustar su macrocategoría y subcategoría cuando haga falta. Esa revisión queda guardada para que futuras importaciones desde Excel no la sobrescriban automáticamente.

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
- Filtros por departamento, grupo de investigación, macrocategoría, subcategoría, año, estado y protección.
- Modal con detalle de cada proyecto.
- Edición manual de clasificación desde el detalle del proyecto.
- Importación de reportes Excel desde la interfaz con vista previa.
- Backend FastAPI con lectura y escritura en SQLite o PostgreSQL.
- Clasificación automática de proyectos con modelo local cuando está disponible.

## Notas técnicas

- En local se usa SQLite para facilitar el desarrollo.
- En Railway se usa PostgreSQL mediante la variable `DATABASE_URL`.
- El frontend intenta usar `/api/projects` y `/api/categories`. Si la API no está disponible, usa los JSON locales como respaldo.
- El archivo `data/processed/ml_dataset.csv` contiene el texto consolidado que puede alimentar el modelo de clasificación.
- La importación compara productos y palabras clave sin depender del orden en que los devuelva la base de datos.

## Estado del proyecto

Versión funcional con dashboard, API, importación de Excel, base local y despliegue en Railway. Una siguiente mejora razonable sería agregar autenticación o control de edición si el proyecto se usa por varias personas.
