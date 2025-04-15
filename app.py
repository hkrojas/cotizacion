import os
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer, Paragraph
from reportlab.lib import colors
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sys
import io
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

app = Flask(__name__, template_folder='templates')
load_dotenv()

# Configuración de la base de datos PostgreSQL en Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')  # Usamos la variable de entorno DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Usuario y contraseña para el login básico
USUARIO = 'hhugo'
CONTRASEÑA = '22673061'

class Cotizacion(db.Model):
    __tablename__ = 'cotizacion'  # Asegúrate de usar el nombre correcto de la tabla en minúsculas
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    numero_cotizacion = db.Column(db.String(20), unique=True)
    tipo_documento = db.Column(db.String(10))
    nro_documento = db.Column(db.String(20))
    nombre_cliente = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.now())
    monto_total = db.Column(db.Float)
    pdf_data = db.Column(db.LargeBinary)

# Configuración para Windows
if sys.platform == 'win32':
    import mimetypes
    mimetypes.add_type('application/pdf', '.pdf')

# Configuración de API
API_TOKEN = os.getenv("API_TOKEN")  # Usamos la variable de entorno para el token de API
SUNAT_API_URL = "https://api.apis.net.pe/v2/sunat/ruc?numero="
RENIEC_API_URL = "https://api.apis.net.pe/v2/reniec/dni?numero="

# Configuración de rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, 'logo', 'logo.png')
PDF_DIR = os.path.join(BASE_DIR, 'temp_pdf')
os.makedirs(PDF_DIR, exist_ok=True)

# Estilo corporativo
COLOR_PRINCIPAL = colors.HexColor('#004aad')

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
        fragmento = ' '.join(palabras[:max_palabras])  # Se toma un fragmento de 'max_palabras' palabras.
        fragmentos.append(fragmento)
        palabras = palabras[max_palabras:]  # Se eliminan las palabras ya procesadas.

    return fragmentos

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    usuario = request.form['username']
    contrasena = request.form['password']
    
    if usuario == USUARIO and contrasena == CONTRASEÑA:
        return render_template('index.html') # Redirige a la página de cotizaciones
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
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

def obtener_siguiente_numero_cotizacion():
    try:
        ultima_cotizacion = Cotizacion.query.order_by(Cotizacion.id.desc()).first()
        
        if not ultima_cotizacion or not ultima_cotizacion.numero_cotizacion:
            return "0001"
        
        ultimo_numero = ultima_cotizacion.numero_cotizacion
        if ultimo_numero.isdigit():
            siguiente_numero = int(ultimo_numero) + 1
        else:
            import re
            digitos = re.findall(r'\d+', ultimo_numero)
            if digitos and digitos[-1].isdigit():
                siguiente_numero = int(digitos[-1]) + 1
            else:
                siguiente_numero = 1
                
        return f"{siguiente_numero:04d}"
        
    except Exception as e:
        print(f"Error al obtener número de cotización: {str(e)}")
        return "0001"

@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    try:
        tipo_documento = request.form['documento']
        nro_documento = request.form['nro_documento']
        nombre_cliente = request.form['nombre_cliente']
        direccion_cliente = request.form['direccion_cliente']
        moneda = request.form['moneda']
        
        descripciones = request.form.getlist('descripcion[]')
        unidades = request.form.getlist('unidades[]')
        totales = request.form.getlist('total[]')

        if not all([nombre_cliente, direccion_cliente, descripciones]):
            return jsonify({'success': False, 'error': 'Datos incompletos'})

        numero_cotizacion = obtener_siguiente_numero_cotizacion()
        
        fecha_emision = datetime.now().strftime("%d/%m/%Y")
        fecha_vencimiento = (datetime.now() + relativedelta(months=1)).strftime("%d/%m/%Y")
        importe_total = sum(float(total) for total in totales)
        igv = importe_total * 0.18
        total_gravado = importe_total - igv
        simbolo = "S/" if moneda == "SOLES" else "$"

        buffer = io.BytesIO()
        margen_izq = 20
        margen_der = 20
        ancho_total = letter[0] - margen_izq - margen_der
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=margen_izq,
            rightMargin=margen_der,
            topMargin=20,
            bottomMargin=20
        )
        
        elementos = []
        
        try:
            logo = Image(LOGO_PATH, width=151, height=76)
        except Exception as e:
            print(f"Error al cargar logo: {str(e)}")
            logo = ""
        
        data_principal = [
            [logo, "PAPELERA G & P", "RUC 20606751509"],
            ["", "AV ALFONSO UGARTE 252 INT 1023 -LIMA-LIMA", "COTIZACIÓN"],
            ["", "papeleragyp@gmail.com\n949 985 395", f"N° {numero_cotizacion}"]
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

        # Cambié aquí: ahora se muestra correctamente el nombre del cliente y la dirección dividida
        data_cliente = [
            ["Señores:", nombre_cliente, " Emisión:", fecha_emision],
            [f"{tipo_documento}:", nro_documento, " Vencimiento:", fecha_vencimiento],
            ["Dirección:", direccion_cliente, " Moneda:", moneda]
        ]
        
        # Dividir la dirección si es necesario
        fragmentos_direccion = dividir_direccion(direccion_cliente)
        direccion_completa = '\n'.join(fragmentos_direccion)

        data_cliente[2][1] = direccion_completa  # Cambié solo la dirección aquí

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

        # Generación de la tabla de productos
        data_productos = [["Descripción", "Cantidad", "P.Unit", "IGV", "Precio"]]
        
        for i in range(len(descripciones)):
            unidad = float(unidades[i])
            total = float(totales[i])
            precio_unit = total / unidad if unidad != 0 else 0
            igv_producto = total * 0.18
            
            # Dividir la descripción si es demasiado larga
            fragmentos_descripcion = dividir_texto(descripciones[i])
            descripcion_completa = '\n'.join(fragmentos_descripcion)

            data_productos.append([  
                descripcion_completa,  # Descripción dividida en fragmentos
                f"{unidad}",
                f"{simbolo} {precio_unit:.2f}",
                f"{simbolo} {igv_producto:.2f}",
                f"{simbolo} {total:.2f}"
            ])
        
        tabla_productos = Table(data_productos, colWidths=[  
            ancho_total * 0.45,
            ancho_total * 0.10,
            ancho_total * 0.15,
            ancho_total * 0.15,
            ancho_total * 0.15
        ])
        
        tabla_productos.setStyle(TableStyle([  
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRINCIPAL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, COLOR_PRINCIPAL),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('WORDWRAP', (0, 0), (-1, -1), True),  # Asegura el salto de línea en las celdas
            ('SPLITBY', (0, 0), (-1, -1), True),   # Forzar salto de línea si es necesario
            ('VALIGN', (0, 0), (-1, -1), 'TOP')    # Asegura que el texto quede alineado en la parte superior
        ]))
        
        elementos.append(tabla_productos)

        data_total = [  
            ["Total Gravado", f"{simbolo} {total_gravado:.2f}"],
            ["Total IGV ", f"{simbolo} {igv:.2f}"],
            ["Importe Total", f"{simbolo} {importe_total:.2f}"]
        ]
        
        tabla_total = Table(data_total, colWidths=[  
            ancho_total * 0.85,
            ancho_total * 0.15
        ])
        
        tabla_total.setStyle(TableStyle([  
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
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
        
        tabla_monto = Table(data_monto, colWidths=[  
            ancho_total * 1
        ])
        
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

        data_banco = [  
            ["Datos para la Transferencia Beneficiario PAPELERÍA GRÁFICA Y PUBLICITARIA"],
            ["Banco de la Nación"],
            ["Cuenta Detracción en Soles: 00045115666"],
            ["Banco de Crédito del Perú"],
            ["Cta Ahorro en Soles: 1919870450013 CCI: 00219100987045001355"]
        ]
        
        tabla_banco = Table(data_banco, colWidths=[  
            ancho_total * 1
        ])
        
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

        def agregar_rectangulo_azul(canvas, doc):
            canvas.saveState()
            x = margen_izq + (ancho_total * 0.80)
            y = doc.height - 62
            ancho = ancho_total * 0.20
            alto = 80
            
            canvas.setStrokeColor(COLOR_PRINCIPAL)
            canvas.setLineWidth(1.5)
            canvas.roundRect(x, y, ancho, alto, 5, stroke=1, fill=0)
            canvas.restoreState()

        doc.build(elementos, onFirstPage=agregar_rectangulo_azul, onLaterPages=agregar_rectangulo_azul)
        buffer.seek(0)

        # Guardar en la base de datos
        nueva_cotizacion = Cotizacion(
            numero_cotizacion=numero_cotizacion,
            tipo_documento=tipo_documento,
            nro_documento=nro_documento,
            nombre_cliente=nombre_cliente,
            monto_total=importe_total,
            pdf_data=buffer.getvalue()
        )
        db.session.add(nueva_cotizacion)
        db.session.commit()

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='cotizacion.pdf'
        )

    except Exception as e:
        db.session.rollback()
        print(f"Error al generar PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al generar PDF: {str(e)}'
        }), 500

@app.route('/ver_cotizaciones')
def ver_cotizaciones():
    cotizaciones = Cotizacion.query.all()  # Obtener todas las cotizaciones
    return render_template('ver_cotizaciones.html', cotizaciones=cotizaciones)

@app.route('/descargar_pdf/<int:cotizacion_id>') 
def descargar_pdf(cotizacion_id):
    cotizacion = Cotizacion.query.get_or_404(cotizacion_id)  # Obtener la cotización por ID
    pdf_data = cotizacion.pdf_data  # Obtener el archivo PDF guardado en la base de datos
    
    # Enviar el archivo PDF como respuesta
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'cotizacion_{cotizacion.numero_cotizacion}.pdf'
    )

if __name__ == '__main__':
    os.makedirs(os.path.join(BASE_DIR, 'logo'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)
    
    with app.app_context():
        try:
            db.create_all()
            print("Tablas creadas correctamente")
        except Exception as e:
            print(f"Error al crear tablas: {str(e)}")
            raise
    
    app.run(debug=True)
