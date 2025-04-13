from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def crear_pdf_mejorado():
    # Configuración del documento
    margen_izq = 20
    margen_der = 20
    ancho_total = letter[0] - margen_izq - margen_der
    
    doc = SimpleDocTemplate("cotizacion_final.pdf", pagesize=letter,
                          leftMargin=margen_izq, rightMargin=margen_der,
                          topMargin=20, bottomMargin=20)
    
    # 1. TABLA PRINCIPAL (logo y datos)
    try:
        logo = Image(r"C:\Users\HP\Desktop\Python\logo\LOGO.png", width=151, height=76)
    except:
        logo = ""
    
    data_principal = [
        [logo, "PAPELERA G & P", "RUC 20606751509"],
        ["", "AV ALFONSO UGARTE 252 INT 1023 -LIMA-LIMA", "COTIZACIÓN"],
        ["", "papeleragyp@gmail.com\n949 985 395", "N° 0001"]
    ]
    
    tabla_principal = Table(data_principal, colWidths=[
        ancho_total * 0.30,
        ancho_total * 0.50,
        ancho_total * 0.20
    ])
    
    estilo_principal = TableStyle([
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
    ])
    tabla_principal.setStyle(estilo_principal)

    # 2. TABLA CLIENTE (nuevo estilo)
    data_cliente = [
        ["Señores:", "QUAD/GRAPHICS PERU S.R.L.", " Emisión:", "10/04/2025"],
        ["RUC:", "20371828851", " Vencimiento:", "10/05/2024"],
        ["Dirección:", "AV. LOS FRUTALES NRO 344 URB. LOS ARTESANOS", " Moneda:", "SOLES"]
    ]
    
    tabla_cliente = Table(data_cliente, colWidths=[
        ancho_total * 0.10,
        ancho_total * 0.60,
        ancho_total * 0.15,
        ancho_total * 0.15
    ])
    
    estilo_cliente = TableStyle([
        # Alineación diferente para esta tabla
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alineación izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fuentes diferenciadas
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Datos cliente en negrita
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Tamaño ligeramente menor
        
        # Bordes completos
        ('LINEABOVE', (0, 0), (-1, 0), 1.5, colors.HexColor('#004aad')),
        
        # Espaciado mínimo
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])
    tabla_cliente.setStyle(estilo_cliente)

    # 3. TABLA PRODUCTOS (nuevo estilo)
    data_productos = [
        ["Descripción", "Cantidad", "P.Unit", "IGV", "Precio"],
        ["BOLSAS DE PAPEL", "450", "S/ 2.73", " S/ 270.00", "S/ 1,500.00"],
        ["BOLSAS DE PAPEL", "450", "S/ 2.73", " S/ 270.00", "S/ 1,500.00"]
    ]
    
    tabla_productos = Table(data_productos, colWidths=[
        ancho_total * 0.40,
        ancho_total * 0.15,
        ancho_total * 0.15,
        ancho_total * 0.15,
        ancho_total * 0.15
    ])
    
    estilo_productos = TableStyle([
        # Alineación diferente para esta tabla
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alineación izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fuentes diferenciadas
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Datos cliente en negrita
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Tamaño ligeramente menor
        
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004aad')),  # Azul corporativo
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # Texto blanco

        # Bordes completos
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#004aad')),
        
        # Espaciado mínimo
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])
    tabla_productos.setStyle(estilo_productos)

    # 4. TABLA TOTALES (nuevo estilo)
    data_total = [
        ["Total Gravado", "S/ 2,460.00"],
        ["Total IGV ", "S/ 540.00"],
        ["Importe Total", "S/ 3,000.00"]
    ]
    
    tabla_total = Table(data_total, colWidths=[
        ancho_total * 0.85,
        ancho_total * 0.15
    ])
    
    estilo_total = TableStyle([
        # Alineación diferente para esta tabla
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alineación izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),  # Alineación izquierda
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),

        # Fuentes diferenciadas
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Datos cliente en negrita
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Tamaño ligeramente menor       

        # Bordes completos
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#004aad')),
        
        # Espaciado mínimo
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])
    tabla_total.setStyle(estilo_total)

    # 4. TABLA TOTALES (nuevo estilo)
    data_monto = [
        ["IMPORTE TOTAL A PAGAR S/ 3,000.00"],
    ]
    
    tabla_monto = Table(data_monto, colWidths=[
        ancho_total * 1
    ])
    
    estilo_monto = TableStyle([
        # Alineación diferente para esta tabla
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alineación izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Fuentes diferenciadas
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),  # Datos cliente en negrita
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Tamaño ligeramente menor       

        # Bordes completos
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor('#004aad')),
        
        # Espaciado mínimo
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ])
    tabla_monto.setStyle(estilo_monto)

    # 4. TABLA TOTALES (nuevo estilo)
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
    
    estilo_banco = TableStyle([
        # Alineación diferente para esta tabla
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alineación izquierda
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Fuentes diferenciadas
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 1), 10),
        ('FONTNAME', (0, 0), (0, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, 1), 10),  
        ('FONTNAME', (0, 3), (0, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 3), (0, 3), 10),       
        
        # Espaciado mínimo
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ])
    tabla_banco.setStyle(estilo_banco)

    # 5. RECTÁNGULO AZUL (posición fija)
    azul_logo = colors.HexColor('#004aad')
    
    def agregar_rectangulo_azul(canvas, doc):
        canvas.saveState()
        x = margen_izq + (ancho_total * 0.80)  # 30% + 50% de las columnas
        y = doc.height - 62  # Posición fija desde arriba
        ancho = ancho_total * 0.20
        alto = 80
        
        canvas.setStrokeColor(azul_logo)
        canvas.setLineWidth(1.5)
        canvas.roundRect(x, y, ancho, alto, 5, stroke=1, fill=0)
        canvas.restoreState()
    
    # Construir PDF con separación entre tablas
    elementos = [
        tabla_principal,
        Spacer(1, 20),  # Espacio de 20 puntos entre tablas
        tabla_cliente,
        Spacer(1,20),
        tabla_productos,
        tabla_total,
        tabla_monto,
        Spacer(1,20),
        tabla_banco
    ]
    
    doc.build(elementos, 
             onFirstPage=agregar_rectangulo_azul, 
             onLaterPages=agregar_rectangulo_azul)
    
    print("PDF generado con ambas tablas y rectángulo preservado")

crear_pdf_mejorado()