import os
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet # Importamos los estilos básicos para Paragraph
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
import io
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from flask_migrate import Migrate
import re # Importar el módulo re para la función de número de cotización
import logging # Importar el módulo logging para mejor manejo de errores
from werkzeug.exceptions import NotFound # Importar NotFound


# Configurar logging básico
logging.basicConfig(level=logging.INFO)
app = Flask(__name__, template_folder='templates')
load_dotenv()

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL") # Corregido de 'DATABASE_URL' a "DATABASE_URL"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


USUARIO = 'hhugo' # Considera usar variables de entorno o un método más seguro para credenciales
CONTRASEÑA = '22673061' # Considera usar variables de entorno o un método más seguro para credenciales

class Cotizacion(db.Model):
    __tablename__ = 'cotizacion'

    id = db.Column(db.Integer, primary_key=True)
    numero_cotizacion = db.Column(db.String(20), unique=True)
    tipo_documento = db.Column(db.String(10))
    nro_documento = db.Column(db.String(20))
    nombre_cliente = db.Column(db.String(100))
    direccion_cliente = db.Column(db.String(200))
    moneda = db.Column(db.String(10), default='SOLES')
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    monto_total = db.Column(db.Float)
    pdf_data = db.Column(db.LargeBinary)

    productos = db.relationship('Producto', backref='cotizacion', cascade='all, delete-orphan')

class Producto(db.Model):
    __tablename__ = 'productos_cotizacion'

    id = db.Column(db.Integer, primary_key=True)
    # Eliminada la coma extra que causaba el error SQLAlchemy
    cotizacion_id = db.Column(db.Integer, db.ForeignKey('cotizacion.id'), nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    unidades = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)


if sys.platform == 'win32':
    import mimetypes
    mimetypes.add_type('application/pdf', '.pdf')


API_TOKEN = os.getenv("API_TOKEN")
SUNAT_API_URL = "https://api.apis.net.pe/v2/sunat/ruc?numero="
RENIEC_API_URL = "https://api.apis.net.pe/v2/reniec/dni?numero="


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, 'logo', 'logo.png')
PDF_DIR = os.path.join(BASE_DIR, 'temp_pdf') # Este directorio ya no es estrictamente necesario si guardas PDF en DB
os.makedirs(PDF_DIR, exist_ok=True)


COLOR_PRINCIPAL = colors.HexColor('#004aad')

# La función dividir_texto ya no se llama directamente en generate_pdf_content
# pero la mantenemos por si la usas en otro lugar o por si la quieres adaptar
def dividir_texto(texto, max_palabras=7):
    """
    Divide un texto en fragmentos, asegurando que cada fragmento no supere el número máximo de palabras.
    """
    palabras = texto.split()
    fragmentos = []

    while palabras:
        fragmento = ' '.join(palabras[:max_palabras])
        fragmentos.append(fragmento)
        palabras = palabras[max_palabras:]

    return fragmentos

def dividir_direccion(direccion, max_palabras=9):
    """
    Divide una dirección en fragmentos, asegurando que cada fragmento no supere el número máximo de palabras.
    """
    palabras = direccion.split()
    fragmentos = []

    while palabras:
        fragmento = ' '.join(palabras[:max_palabras])
        fragmentos.append(fragmento)
        palabras = palabras[max_palabras:]

    return fragmentos

# --- Función para generar el contenido binario del PDF (reutilizable) ---
def generate_pdf_content(cotizacion_obj, productos_list, importe_total):
    """Genera el contenido binario de un PDF de cotización."""
    buffer = io.BytesIO()
    margen_izq = 20
    margen_der = 20
    ancho_total = letter[0] - margen_izq - margen_der

    # Ajusta el ancho total para las columnas de la tabla de productos
    # El ancho de la columna de descripción es ancho_total * 0.45
    ancho_columna_descripcion = ancho_total * 0.45

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=margen_izq,
        rightMargin=margen_der,
        topMargin=20,
        bottomMargin=20
    )

    elementos = []

    # --- Header (Logo, Company Info, Quote Number) ---
    try:
        logo = Image(LOGO_PATH, width=151, height=76)
    except Exception as e:
        app.logger.error(f"Error al cargar logo para PDF: {str(e)}")
        logo = ""

    data_principal = [
        [logo, "PAPELERA G & P", "RUC 20606751509"],
        ["", "AV ALFONSO UGARTE 252 INT 1023 -LIMA-LIMA", "COTIZACIÓN"],
        ["", "papeleragyp@gmail.com\n949 985 395", f"N° {cotizacion_obj.numero_cotizacion}"]
    ]

    tabla_principal = Table(data_principal, colWidths=[
        ancho_total * 0.30,
        ancho_total * 0.50,
        ancho_total * 0.20
    ])
    tabla_principal.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (0, -1)),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 2), (2, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMMARGIN', (0, 0), (-1, -1), 0),
        ('TOPMARGIN', (0, 0), (-1, -1), 0),
    ]))
    elementos.append(tabla_principal)
    elementos.append(Spacer(1, 20))

    # --- Client Info ---
    fecha_emision = cotizacion_obj.fecha_creacion.strftime("%d/%m/%Y")
    # Calcular fecha de vencimiento a partir de la fecha de creación de la cotización
    fecha_vencimiento = (cotizacion_obj.fecha_creacion + relativedelta(months=1)).strftime("%d/%m/%Y")

    fragmentos_direccion = dividir_direccion(cotizacion_obj.direccion_cliente)
    direccion_completa = '\n'.join(fragmentos_direccion)
    simbolo = "S/" if cotizacion_obj.moneda == "SOLES" else "$"

    data_cliente = [
        ["Señores:", cotizacion_obj.nombre_cliente, " Emisión:", fecha_emision],
        [f"{cotizacion_obj.tipo_documento}:", cotizacion_obj.nro_documento, " Vencimiento:", fecha_vencimiento],
        ["Dirección:", direccion_completa, " Moneda:", cotizacion_obj.moneda]
    ]

    tabla_cliente = Table(data_cliente, colWidths=[
        ancho_total * 0.10,
        ancho_total * 0.60,
        ancho_total * 0.15,
        ancho_total * 0.15
    ])
    tabla_cliente.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, COLOR_PRINCIPAL),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, COLOR_PRINCIPAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_cliente)
    elementos.append(Spacer(1, 20))

    # --- Products Table ---
    # Define el estilo base del Paragraph para la descripción
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleN.leading = 12 # Espacio entre líneas, ajusta si es necesario
    styleN.fontName = 'Helvetica' # Asegura la fuente
    styleN.fontSize = 10 # Asegura el tamaño de fuente
    styleN.textColor = colors.black # Asegura el color del texto para los datos de la descripción

    data_productos = [["Descripción", "Cantidad", "P.Unit", "IGV", "Precio"]]

    # products_list will be the list of Producto objects passed to this function
    for producto in productos_list:
        # Usamos Paragraph para la descripción
        descripcion_texto = producto.descripcion.strip()

        unidad = producto.unidades
        total = producto.total
        precio_unit = producto.precio_unitario if producto.precio_unitario is not None else (total / unidad if unidad > 0 else 0.0)
        igv_producto = total * (0.18/1.18)

        # Crea un objeto Paragraph para la descripción
        descripcion_paragraph = Paragraph(descripcion_texto, styleN)

        data_productos.append([
            descripcion_paragraph, # Usamos el objeto Paragraph aquí
            f"{unidad}",
            f"{simbolo} {precio_unit:.2f}",
            f"{simbolo} {igv_producto:.2f}",
            f"{simbolo} {total:.2f}"
        ])

    tabla_productos = Table(data_productos, colWidths=[
        ancho_columna_descripcion,
        ancho_total * 0.10,
        ancho_total * 0.15,
        ancho_total * 0.15,
        ancho_total * 0.15
    ])
    tabla_productos.setStyle(TableStyle([
        # Alineación general para todas las celdas (puede ser CENTER o LEFT)
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), # Generalmente centramos todo primero
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Generalmente alineamos al medio

        # Estilos específicos para la FILA DE ENCABEZADO (fila 0)
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'), # --> CENTRAMOS la fila de encabezado horizontalmente <--
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'), # Alineación vertical para el encabezado
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), # Fuente en negrita para el encabezado
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), # Color del texto en el encabezado

        # Estilos específicos para las FILAS DE DATOS (desde la fila 1 hacia abajo)
        # Alineación para la PRIMERA columna (Descripción) en las filas de datos
        ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Alineamos a la IZQUIERDA la descripción en las filas de datos
        ('VALIGN', (0, 1), (0, -1), 'TOP'), # Alineamos arriba la descripción (para que el texto envuelto empiece arriba)
        ('TEXTCOLOR', (0, 1), (0, -1), colors.black), # Color del texto en la columna de descripción

        # Alineación para las OTRAS columnas de datos (Cantidad, P.Unit, IGV, Precio)
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'), # Centramos horizontalmente el resto de columnas de datos
        ('VALIGN', (1, 1), (-1, -1), 'MIDDLE'), # Alineamos al medio verticalmente el resto de columnas de datos

        # Otros estilos generales que aplican a rangos específicos o a toda la tabla
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'), # Fuente para las filas de datos (excepto encabezado)
        ('FONTSIZE', (0, 1), (-1, -1), 10), # Tamaño de fuente para las filas de datos
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, COLOR_PRINCIPAL), # Línea azul debajo de la última fila de datos
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_productos)

    # --- Totals ---
    igv_total = importe_total * (0.18/1.18)
    total_gravado = importe_total - igv_total
    data_total = [
        ["Total Gravado", f"{simbolo} {total_gravado:.2f}"],
        ["Total IGV ", f"{simbolo} {igv_total:.2f}"],
        ["Importe Total", f"{simbolo} {importe_total:.2f}"]
    ]
    tabla_total = Table(data_total, colWidths=[
        ancho_total * 0.85,
        ancho_total * 0.15
    ])
    tabla_total.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'), # Alineamos a la derecha el texto "Total Gravado", "Total IGV", "Importe Total"
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, COLOR_PRINCIPAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_total)

    data_monto = [
        [f"IMPORTE TOTAL A PAGAR {simbolo} {importe_total:.2f}"],
    ]
    tabla_monto = Table(data_monto, colWidths=[ ancho_total * 1 ])
    tabla_monto.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, COLOR_PRINCIPAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_monto)


    # --- Bank Info ---
    data_banco = [
        ["Datos para la Transferencia Beneficiario PAPELERÍA GRÁFICA Y PUBLICITARIA"],
        ["Banco de la Nación"],
        ["Cuenta Detracción en Soles: 00045115666"],
        ["Banco de Crédito del Perú"],
        ["Cta Ahorro en Soles: 1919870450013 CCI: 00219100987045001355"]
    ]
    tabla_banco = Table(data_banco, colWidths=[ ancho_total * 1 ])
    tabla_banco.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 1), 10),
        ('FONTNAME', (0, 0), (0, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 1), 10),
        ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 3), (0, 3), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elementos.append(tabla_banco)

    # --- PDF Build and Rectangle ---
    def agregar_rectangulo_azul(canvas, doc):
        canvas.saveState()
        x = margen_izq + (ancho_total * 0.80)
        # La posición Y puede necesitar ajuste fino dependiendo del contenido
        y = doc.height - 62
        ancho = ancho_total * 0.20
        alto = 80
        canvas.setStrokeColor(COLOR_PRINCIPAL)
        canvas.setLineWidth(1.5)
        canvas.roundRect(x, y, ancho, alto, 5, stroke=1, fill=0)
        canvas.restoreState()

    # Build the PDF
    try:
        doc.build(elementos, onFirstPage=agregar_rectangulo_azul, onLaterPages=agregar_rectangulo_azul)
        buffer.seek(0) # Rewind buffer to the beginning

        return buffer.getvalue() # Return binary PDF data
    except Exception as e:
        app.logger.error(f"Error al construir el PDF con ReportLab: {str(e)}")
        # Podrías retornar None o lanzar una excepción específica
        raise # Relanzar la excepción para que el manejador de errores de la ruta la capture


@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    usuario = request.form['username']
    contrasena = request.form['password']

    if usuario == USUARIO and contrasena == CONTRASEÑA:
        return render_template('index.html')
    else:
        return 'Credenciales incorrectas, por favor intente de nuevo.'

@app.route('/consultar_api', methods=['POST'])
def consultar_api():
    try:
        data = request.get_json()
        tipo_doc = data.get('tipo_documento')
        numero_doc = data.get('numero_documento')

        if not numero_doc:
            return jsonify({'success': False, 'message': 'Número de documento requerido'})

        headers = {'Authorization': f'Bearer {API_TOKEN}'}

        if tipo_doc == 'DNI':
            if len(numero_doc) != 8:
                return jsonify({'success': False, 'message': 'DNI debe tener 8 dígitos'})

            response = requests.get(f"{RENIEC_API_URL}{numero_doc}", headers=headers)
            if response.status_code == 200:
                datos = response.json()
                nombre = f"{datos.get('nombres', '')} {datos.get('apellidoPaterno', '')} {datos.get('apellidoMaterno', '')}"
                return jsonify({'success': True, 'nombre': nombre.strip(), 'direccion': ''})

        elif tipo_doc == 'RUC':
            if len(numero_doc) != 11:
                return jsonify({'success': False, 'message': 'RUC debe tener 11 dígitos'})

            response = requests.get(f"{SUNAT_API_URL}{numero_doc}", headers=headers)
            if response.status_code == 200:
                datos = response.json()
                direccion_completa = f"{datos.get('direccion', '')}, {datos.get('distrito', '')}, {datos.get('provincia', '')}, {datos.get('departamento', '')}"
                return jsonify({
                    'success': True,
                    'nombre': datos.get('razonSocial', ''),
                    'direccion': direccion_completa
                })

        return jsonify({'success': False, 'message': 'No se encontraron datos'})

    except Exception as e:
        app.logger.error(f"Error en consultar_api: {str(e)}")
        return jsonify({'success': False, 'message': 'Error interno del servidor al consultar API'}), 500

def obtener_siguiente_numero_cotizacion():
    try:
        ultima_cotizacion = Cotizacion.query.order_by(Cotizacion.id.desc()).first()

        if not ultima_cotizacion or not ultima_cotizacion.numero_cotizacion:
            return "0001"

        ultimo_numero = ultima_cotizacion.numero_cotizacion
        digitos = re.findall(r'\d+$', ultimo_numero)

        if digitos:
            siguiente_numero = int(digitos[0]) + 1
        else:
            siguiente_numero = 1

        return f"{siguiente_numero:04d}"

    except Exception as e:
        app.logger.error(f"Error al obtener número de cotización: {str(e)}")
        return "0001"

@app.route('/index')
def index():
    # Aquí puedes añadir lógica si necesitas pasar datos a index.html
    # Por ahora, simplemente renderizamos la plantilla
    return render_template('index.html')

@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    try:
        # Esta ruta sigue generando un PDF a partir de un formulario HTML y guarda una NUEVA cotización
        tipo_documento = request.form['documento']
        nro_documento = request.form['nro_documento']
        nombre_cliente = request.form['nombre_cliente']
        direccion_cliente = request.form['direccion_cliente']
        moneda = request.form['moneda']

        descripciones = request.form.getlist('descripcion[]')
        unidades = request.form.getlist('unidades[]')
        totales = request.form.getlist('total[]')

        if not nombre_cliente or not direccion_cliente or not descripciones:
             return jsonify({'success': False, 'error': 'Datos incompletos: Nombre, dirección o productos faltantes'}), 400

        productos_para_db = [] # Lista para almacenar Producto objects para DB
        importe_total = 0
        for desc, unid, tot in zip(descripciones, unidades, totales):
             try:
                unid_int = int(float(unid))
                tot_float = float(tot)
                if desc.strip() and unid_int > 0 and tot_float >= 0:
                    precio_unit = tot_float / unid_int if unid_int > 0 else 0.0
                    productos_para_db.append(Producto(
                         descripcion=desc.strip(),
                         unidades=unid_int,
                         precio_unitario=precio_unit,
                         total=tot_float
                    ))
                    importe_total += tot_float
             except (ValueError, TypeError):
                 app.logger.warning(f"Producto inválido omitido en generación: Desc: {desc}, Unid: {unid}, Tot: {tot}")
                 continue

        if not productos_para_db:
             return jsonify({'success': False, 'error': 'No se pudieron procesar productos válidos para la cotización'}), 400

        numero_cotizacion = obtener_siguiente_numero_cotizacion()

        # Crear la cotización en la DB *antes* de generar el PDF para obtener el ID
        nueva_cotizacion_db = Cotizacion(
            numero_cotizacion=numero_cotizacion,
            tipo_documento=tipo_documento,
            nro_documento=nro_documento,
            nombre_cliente=nombre_cliente,
            direccion_cliente=direccion_cliente,
            moneda=moneda,
            monto_total=importe_total # Monto total calculado aquí
            # pdf_data se añadirá después de generarlo
        )
        db.session.add(nueva_cotizacion_db)
        db.session.flush() # Obtiene nueva_cotizacion_db.id

        # Asignar el cotizacion_id a los productos antes de guardarlos
        for producto in productos_para_db:
            producto.cotizacion_id = nueva_cotizacion_db.id
            db.session.add(producto) # Añadir los productos a la sesión


        # Generar el contenido del PDF usando la nueva cotización y la lista de productos
        # Nota: generate_pdf_content espera una lista de objetos Producto, no diccionarios
        pdf_data_binary = generate_pdf_content(nueva_cotizacion_db, productos_para_db, importe_total)

        # Guardar los datos binarios del PDF en la cotización
        nueva_cotizacion_db.pdf_data = pdf_data_binary

        db.session.commit() # Confirmar todos los cambios


        # Devolver el PDF
        return send_file(
            io.BytesIO(pdf_data_binary),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'cotizacion_{numero_cotizacion}.pdf'
        )

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al generar PDF y guardar cotización: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno del servidor al generar la cotización: {str(e)}'
        }), 500


@app.route('/ver_cotizaciones')
def ver_cotizaciones():
    try: # Añadido try-except para capturar errores al cargar la página de cotizaciones
        cotizaciones = Cotizacion.query.all()
        return render_template('ver_cotizaciones.html', cotizaciones=cotizaciones)
    except Exception as e:
        app.logger.error(f"Error al cargar la página de cotizaciones: {str(e)}")
        return f"Error al cargar las cotizaciones: {str(e)}", 500


@app.route('/obtener_cotizacion/<int:cotizacion_id>')
def obtener_cotizacion(cotizacion_id):
    try:
        # get_or_404 lanza NotFound si la cotización no existe
        cotizacion = Cotizacion.query.get_or_404(cotizacion_id)
        productos = Producto.query.filter_by(cotizacion_id=cotizacion_id).all()

        productos_data = []
        for producto in productos:
            productos_data.append({
                'id': producto.id,
                'descripcion': producto.descripcion,
                'unidades': producto.unidades,
                'precio_unitario': producto.precio_unitario,
                'total': producto.total
            })

        # Si todo va bien, devuelve JSON
        return jsonify({
            'success': True,
            'id': cotizacion.id,
            'numero_cotizacion': cotizacion.numero_cotizacion,
            'nombre_cliente': cotizacion.nombre_cliente,
            'tipo_documento': cotizacion.tipo_documento,
            'nro_documento': cotizacion.nro_documento,
            'direccion': cotizacion.direccion_cliente,
            'moneda': cotizacion.moneda,
            'productos': productos_data
        })
    except NotFound: # <--- Captura específica de la excepción NotFound
        # Si la cotización no se encuentra, devuelve un error JSON 404
        app.logger.warning(f"Cotización con ID {cotizacion_id} no encontrada.")
        return jsonify({'success': False, 'error': 'Cotización no encontrada'}), 404
    except Exception as e: # <--- Captura otros errores inesperados
        # Para cualquier otro error, devuelve un error JSON 500
        app.logger.error(f"Error general al obtener cotización {cotizacion_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


@app.route('/descargar_pdf/<int:cotizacion_id>')
def descargar_pdf(cotizacion_id):
    try:
        # get_or_404 lanza NotFound si la cotización no existe
        cotizacion = Cotizacion.query.get_or_404(cotizacion_id)
        pdf_data = cotizacion.pdf_data

        if pdf_data is None:
             # Si el PDF no está en la DB, devuelve un error 404 (JSON)
             app.logger.warning(f"PDF no disponible para cotización {cotizacion_id}.")
             return jsonify({'success': False, 'error': 'El PDF para esta cotización no está disponible.'}), 404

        # Si todo está bien, envía el archivo PDF
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'cotizacion_{cotizacion.numero_cotizacion}.pdf'
        )
    except NotFound: # <--- Captura específica si la cotización no existe
        app.logger.warning(f"Intento de descarga de PDF para cotización {cotizacion_id} no encontrada.")
        return jsonify({'success': False, 'error': 'Cotización para descarga no encontrada'}), 404 # Devuelve JSON 404
    except Exception as e: # <--- Captura otros errores inesperados
        app.logger.error(f"Error general al descargar PDF para cotización {cotizacion_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Error interno del servidor al descargar PDF'}), 500 # Devuelve JSON 500


# --- Definición corregida y ÚNICA de actualizar_cotizacion con regeneración de PDF ---
@app.route('/actualizar_cotizacion/<int:cotizacion_id>', methods=['POST'])
def actualizar_cotizacion(cotizacion_id):
    try:
        data = request.get_json()
        cotizacion = Cotizacion.query.get_or_404(cotizacion_id)

        # Actualizar datos básicos de la cotización
        cotizacion.nombre_cliente = data.get('nombre_cliente', cotizacion.nombre_cliente)
        cotizacion.tipo_documento = data.get('tipo_documento', cotizacion.tipo_documento)
        cotizacion.nro_documento = data.get('nro_documento', cotizacion.nro_documento)
        cotizacion.direccion_cliente = data.get('direccion', cotizacion.direccion_cliente)
        cotizacion.moneda = data.get('moneda', cotizacion.moneda)

        # --- Procesar y actualizar productos ---
        productos_enviados = data.get('productos', [])

        # Eliminar productos existentes asociados a esta cotización
        # Esto es seguro porque el cascade 'all, delete-orphan' en Cotizacion.productos
        # asegura que los objetos Producto se eliminen de la sesión cuando se borran
        # las referencias, PERO delete() es más eficiente para borrar en masa
        Producto.query.filter_by(cotizacion_id=cotizacion_id).delete()

        monto_total = 0
        productos_para_db = [] # Lista para almacenar los NUEVOS objetos Producto para la DB
        # Agregar los nuevos productos (o los productos modificados enviados)
        for producto_data in productos_enviados:
             try:
                descripcion = producto_data.get('descripcion', '').strip()
                unidades_val = producto_data.get('unidades', 0)
                total_val = producto_data.get('total', 0)

                # Convertir unidades a int y total a float con manejo de errores
                unidades = int(float(unidades_val)) if unidades_val is not None else 0
                total = float(total_val) if total_val is not None else 0.0


                if descripcion and unidades > 0 and total >= 0:
                    precio_unitario = total / unidades if unidades > 0 else 0.0
                    # Crear una NUEVA instancia de Producto para la base de datos
                    productos_para_db.append(Producto(
                         cotizacion_id=cotizacion_id, # Asegurar la relación
                         descripcion=descripcion,
                         unidades=unidades,
                         precio_unitario=precio_unitario,
                         total=total
                    ))
                    monto_total += total
                else:
                     app.logger.warning(f"Producto inválido omitido en actualización (datos recibidos): {producto_data}")

             except (ValueError, TypeError) as e:
                 app.logger.error(f"Error al procesar producto {producto_data} para cotización {cotizacion_id}: {str(e)}")
                 # Continuar con el siguiente producto

        # Añadir los nuevos objetos Producto a la sesión
        db.session.add_all(productos_para_db)

        # Actualizar el monto total de la cotización basado en los productos enviados
        cotizacion.monto_total = monto_total

        # --- Regenerar PDF con datos actualizados ---
        # Llama a la función auxiliar con el objeto cotización actualizado
        # y la lista de objetos Producto recién creados/procesados
        updated_pdf_data = generate_pdf_content(cotizacion, productos_para_db, cotizacion.monto_total)

        # Guardar los datos binarios del PDF actualizado en la cotización
        cotizacion.pdf_data = updated_pdf_data

        db.session.commit() # Confirmar todos los cambios

        return jsonify({'success': True, 'message': 'Cotización actualizada correctamente. PDF regenerado.'})

    except Exception as e:
        db.session.rollback() # Deshacer cambios si ocurre un error
        app.logger.error(f'Error general al actualizar cotización {cotizacion_id} incluyendo PDF: {str(e)}')
        # Devolver un mensaje de error más descriptivo para el frontend si es posible
        return jsonify({'success': False, 'error': f'Error al actualizar cotización y regenerar PDF: {str(e)}'}), 500


@app.route('/eliminar_cotizacion/<int:cotizacion_id>', methods=['POST'])
def eliminar_cotizacion(cotizacion_id):
    if not (request.headers.get('X-Requested-With') == 'XMLHttpRequest'):
        return jsonify({'success': False, 'error': 'Solicitud no válida'}), 400

    try:
        cotizacion = Cotizacion.query.get_or_404(cotizacion_id)
        db.session.delete(cotizacion)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cotización eliminada'})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error eliminando cotización {cotizacion_id}: {str(e)}')
        return jsonify({'success': False, 'error': 'Error del servidor'}), 500

if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'logo'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)

    with app.app_context():
        try:
            # Si estás usando migraciones (Flask-Migrate), NO llames db.create_all() aquí.
            # Ejecuta 'flask db upgrade' desde tu terminal para crear/actualizar la DB.
            # Si NO usas migraciones, descomenta la línea de abajo:
            # db.create_all()
            print("Verificando/inicializando la base de datos...")
            # Puedes añadir lógica aquí para verificar si las tablas existen
            # Si usas migraciones, confías en que 'flask db upgrade' lo hizo.

        except Exception as e:
            app.logger.error(f"Error al inicializar la base de datos en el startup: {str(e)}")
            # Dependiendo de si la DB es esencial para iniciar, podrías querer salir o continuar
            # sys.exit(1) # Descomentar para salir si la DB es esencial

    app.run(debug=True)