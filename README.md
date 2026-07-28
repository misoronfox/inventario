# Inventario Hogar

Aplicación web desarrollada con Flask para administrar el inventario de un hogar, controlar el stock de productos, generar listas de compras y visualizar reportes de consumo.

## Características

- Gestión de categorías y subcategorías.
- Registro de productos.
- Control de stock mínimo.
- Indicadores visuales de estado del inventario.
- Subida de imágenes para cada producto.
- Lista de compras integrada.
- Registro histórico de consumos.
- Reportes por categoría y estadísticas generales.
- Base de datos SQLite.

---

## Tecnologías utilizadas

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Gunicorn
- HTML
- CSS
- JavaScript

---

## Instalación local

Clonar el repositorio:

```bash
git clone https://github.com/misoronfox/inventario.git
cd inventario
```

Crear un entorno virtual:

```bash
python -m venv venv
```

Activarlo:

### Linux / macOS

```bash
source venv/bin/activate
```

### Windows

```powershell
venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar la aplicación:

```bash
python app.py
```

La aplicación estará disponible en:

```
http://localhost:5000
```

---

## Docker

Construir y levantar el proyecto:

```bash
docker compose up --build
```

La aplicación quedará disponible en:

```
http://localhost:5000
```

---

## Persistencia

La aplicación utiliza SQLite y almacena la información en:

```
data/inventario.db
```

Las imágenes de los productos se almacenan en:

```
static/uploads/
```

Ambos directorios se montan como volúmenes para conservar la información entre reinicios y actualizaciones del contenedor.

---

## Estructura del proyecto

```
.
├── app.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── templates/
├── static/
│   └── uploads/
└── data/
    └── inventario.db
```

---

## Licencia

Proyecto desarrollado para uso personal.