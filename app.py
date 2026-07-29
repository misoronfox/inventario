
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)

# Configuración de base de datos SQLite y subida de archivos

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Carpeta donde vivirá la base de datos
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = \
    f"sqlite:///{os.path.join(DATA_DIR, 'inventario.db')}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Carpeta para imágenes
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

db = SQLAlchemy(app)


# Helper para determinar el estado según las reglas
def get_stock_status(quantity, min_quantity):
    qty = int(quantity)
    min_q = int(min_quantity)
    if qty < min_q:
        return 'red'
    elif qty >= min_q and qty <= min_q * 1.3:
        return 'yellow'
    return 'green'

# --- MODELOS DE BASE DE DATOS (RELACIONALES) ---

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id', ondelete='CASCADE'), nullable=True)
    
    # Relación jerárquica para subcategorías
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade="all, delete")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id
        }

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Integer, nullable=False, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    min_quantity = db.Column(db.Integer, nullable=False, default=0)
    image_filename = db.Column(db.String(255), nullable=True)
    
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

    category = db.relationship('Category', foreign_keys=[category_id])
    subcategory = db.relationship('Category', foreign_keys=[subcategory_id])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'quantity': self.quantity,
            'min_quantity': self.min_quantity,
            'image_url': f"/static/uploads/{self.image_filename}" if self.image_filename else None,
            'category_id': self.category_id,
            'subcategory_id': self.subcategory_id,
            'category_name': self.category.name if self.category else '',
            'subcategory_name': self.subcategory.name if self.subcategory else '',
            'status': get_stock_status(self.quantity, self.min_quantity)
        }

class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id', ondelete='CASCADE'), nullable=False)
    completed = db.Column(db.Boolean, default=False)

    product = db.relationship('Product', backref=db.backref('shopping_items', lazy=True, cascade="all, delete"))

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'name': self.product.name if self.product else '',
            'category_name': self.product.category.name if self.product and self.product.category else 'Otros',
            'price': self.product.price if self.product else 0.0,
            'completed': self.completed
        }

class ConsumptionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    category_name = db.Column(db.String(100), nullable=False)
    quantity_consumed = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- RUTAS DE LAS APIS ---

@app.route('/')
def home():
    return render_template('index.html')

# Obtener categorías (principales o subcategorías)
@app.route('/api/categories', methods=['GET'])
def get_categories():
    parent_id = request.args.get('parent_id')
    if parent_id == 'null' or parent_id is None:
        categories = Category.query.filter(Category.parent_id == None).all()
    else:
        categories = Category.query.filter_by(parent_id=int(parent_id)).all()
    return jsonify([c.to_dict() for c in categories])

# Crear una categoría
@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id') # Puede ser None para categoría principal
    
    if not name:
        return jsonify({'error': 'El nombre es obligatorio'}), 400

    existing = Category.query.filter_by(name=name, parent_id=parent_id).first()
    if existing:
        return jsonify(existing.to_dict()), 200

    new_cat = Category(name=name, parent_id=parent_id)
    db.session.add(new_cat)
    db.session.commit()
    return jsonify(new_cat.to_dict()), 201

# Obtener productos (con soporte de filtros)
@app.route('/api/products', methods=['GET'])
def get_products():
    category_id = request.args.get('category_id')
    subcategory_id = request.args.get('subcategory_id')
    status = request.args.get('status') # 'red', 'yellow', 'green'

    query = Product.query
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    if subcategory_id:
        query = query.filter_by(subcategory_id=int(subcategory_id))

    products = query.all()
    output = []
    for p in products:
        p_status = get_stock_status(p.quantity, p.min_quantity)
        if status and p_status != status:
            continue
        output.append(p.to_dict())

    return jsonify(output)

# Guardar o Editar Producto (Soporta multipart/form-data para carga de archivos)
@app.route('/api/products', methods=['POST'])
def save_product():
    p_id = request.form.get('id')
    name = request.form.get('name')
    description = request.form.get('description')
    price = int(request.form.get('price', 0))
    quantity = int(request.form.get('quantity', 0))
    min_quantity = int(request.form.get('min_quantity', 0))
    category_id = int(request.form.get('category_id'))
    
    subcategory_id_raw = request.form.get('subcategory_id')
    subcategory_id = int(subcategory_id_raw) if subcategory_id_raw and subcategory_id_raw != 'null' else None

    # Procesar archivo de imagen
    image_file = request.files.get('image')
    filename = None
    if image_file and image_file.filename != '':
        filename = secure_filename(f"{datetime.now().timestamp()}_{image_file.filename}")
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if p_id:
        # Editar existente
        product = Product.query.get(p_id)
        if not product:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        product.name = name
        product.description = description
        product.price = price
        product.quantity = quantity
        product.min_quantity = min_quantity
        product.category_id = category_id
        product.subcategory_id = subcategory_id
        if filename:
            product.image_filename = filename
    else:
        # Nuevo producto
        product = Product(
            name=name, description=description, price=price,
            quantity=quantity, min_quantity=min_quantity,
            category_id=category_id, subcategory_id=subcategory_id,
            image_filename=filename
        )
        db.session.add(product)

    db.session.commit()
    return jsonify(product.to_dict()), 200

# Cambiar stock y registrar logs de consumo
@app.route('/api/products/<int:id>/quantity', methods=['PATCH'])
def update_quantity(id):
    data = request.json
    change = int(data.get('change', 0))
    product = Product.query.get(id)
    if not product:
        return jsonify({'error': 'No encontrado'}), 404

    old_qty = product.quantity
    product.quantity = max(0, product.quantity + change)

    # Registrar el consumo si disminuyó el stock
    if change < 0 and old_qty > product.quantity:
        diff = old_qty - product.quantity
        log = ConsumptionLog(
            product_name=product.name,
            category_name=product.category.name,
            quantity_consumed=diff
        )
        db.session.add(log)

    db.session.commit()
    return jsonify(product.to_dict())

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({'error': 'No encontrado'}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({'success': True})

# --- RUTAS DE LISTA DE COMPRAS ---

@app.route('/api/shopping', methods=['GET'])
def get_shopping_list():
    items = ShoppingList.query.all()
    return jsonify([i.to_dict() for i in items])

@app.route('/api/shopping', methods=['POST'])
def add_to_shopping_list():
    data = request.json
    product_id = int(data.get('product_id'))
    
    # Validar si ya está en la lista sin completar
    exists = ShoppingList.query.filter_by(product_id=product_id, completed=False).first()
    if exists:
        return jsonify({'error': 'El artículo ya se encuentra en la lista'}), 400

    item = ShoppingList(product_id=product_id)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@app.route('/api/shopping/<int:id>', methods=['PATCH'])
def toggle_shopping_item(id):
    item = ShoppingList.query.get(id)
    if not item:
        return jsonify({'error': 'No encontrado'}), 404
    item.completed = not item.completed
    db.session.commit()
    return jsonify(item.to_dict())

@app.route('/api/shopping/<int:id>', methods=['DELETE'])
def delete_shopping_item(id):
    item = ShoppingList.query.get(id)
    if not item:
        return jsonify({'error': 'No encontrado'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

# --- APIS PARA LOS REPORTES ---

@app.route('/api/reports', methods=['GET'])
def get_reports_data():
    # Agrupado de existencias actuales por categoría principal
    categories = Category.query.filter(Category.parent_id == None).all()
    stock_distribution = {}
    for cat in categories:
        total_qty = db.session.query(db.func.sum(Product.quantity)).filter(Product.category_id == cat.id).scalar() or 0
        stock_distribution[cat.name] = total_qty

    # Consumos históricos de ConsumptionLog agrupados por categoría
    consumption_logs = db.session.query(
        ConsumptionLog.category_name,
        db.func.sum(ConsumptionLog.quantity_consumed)
    ).group_by(ConsumptionLog.category_name).all()
    
    consumption_distribution = {row[0]: row[1] for row in consumption_logs}

    # Contadores globales de estado
    all_products = Product.query.all()
    stats = {'red': 0, 'yellow': 0, 'green': 0}
    for p in all_products:
        p_status = get_stock_status(p.quantity, p.min_quantity)
        stats[p_status] += 1

    return jsonify({
        'stock_distribution': stock_distribution,
        'consumption_distribution': consumption_distribution,
        'stats': stats
    })

# --- INICIALIZACIÓN DE LA BASE DE DATOS CON CATEGORÍAS PRECONFIGURADAS ---
with app.app_context():
    db.create_all()
    if not Category.query.first():
        # Crear estructura de prueba inicial
        comida = Category(name='Comida')
        aseo = Category(name='Aseo Personal')
        limpieza = Category(name='Limpieza')
        otros = Category(name='Otros')
        db.session.add_all([comida, aseo, limpieza, otros])
        db.session.commit()

        # Crear subcategorías para Comida
        db.session.add_all([
            Category(name='Carbohidratos', parent_id=comida.id),
            Category(name='Proteínas', parent_id=comida.id),
            Category(name='Verduras', parent_id=comida.id),
            Category(name='Lácteos', parent_id=comida.id),
        ])
        db.session.commit()

if __name__ == '__main__':
    # Se expone en el puerto 5000 de manera predeterminada para pruebas locales
    app.run(host='0.0.0.0', port=5000, debug=True)