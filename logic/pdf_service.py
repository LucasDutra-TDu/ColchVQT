import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from logic.financiero import format_currency
from num2words import num2words
from logic.constants import RECURSOS_DIR

# --- BRÚJULA UNIVERSAL (RUTAS) ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_path()
DOCS_ROOT = BASE_DIR / "documentos_generados"
DIR_CONTRATOS = DOCS_ROOT / "contratos_credito"
DIR_COMPROBANTES = DOCS_ROOT / "comprobantes_venta"

# Ruta del Logo
LOGO_PATH = BASE_DIR / "elgalpon.png"

def ensure_dirs():
    if not DOCS_ROOT.exists(): DOCS_ROOT.mkdir(parents=True)
    if not DIR_CONTRATOS.exists(): DIR_CONTRATOS.mkdir(parents=True)
    if not DIR_COMPROBANTES.exists(): DIR_COMPROBANTES.mkdir(parents=True)

def _sanitizar_nombre(nombre):
    return "".join([c for c in nombre if c.isalnum() or c in (' ', '_')]).strip()

def _obtener_logo_flowable():
    """Devuelve el objeto Imagen si el archivo existe, o None."""
    if LOGO_PATH.exists():
        img = Image(str(LOGO_PATH), width=120, height=70)
        img.hAlign = 'LEFT'
        return img
    return None

# ==============================================================================
# SECCIÓN 1: GENERACIÓN DE DOCUMENTACIÓN PARA CRÉDITOS
# ==============================================================================

def generar_documentacion_credito(cliente: dict, items: list, plan: dict) -> str:
    ensure_dirs()
    
    nombre_safe = _sanitizar_nombre(cliente['nombre'])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Credito_{nombre_safe}_{cliente['dni']}_{timestamp}.pdf"
    filepath = DIR_CONTRATOS / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # Pag 1: Contrato Original
    _agregar_contenido_contrato(story, styles, cliente, items, plan)
    story.append(PageBreak())

    # Pag 2: Contrato Duplicado
    _agregar_contenido_contrato(story, styles, cliente, items, plan)
    story.append(PageBreak())
    
    # Pag 3: Desglose
    _agregar_contenido_desglose(story, styles, cliente, plan)
    
    doc.build(story)
    return str(filepath)

def _agregar_contenido_contrato(story, styles, cliente, items, plan):
    style_body = ParagraphStyle(name='Justify', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=10, leading=14)
    # El estilo Title ya viene centrado por defecto en getSampleStyleSheet()

    # --- ENCABEZADO: LOGO + TÍTULO ALINEADOS (NUEVO) ---
    logo = _obtener_logo_flowable()
    
    # Creamos el párrafo del título
    titulo_p = Paragraph("CONTRATO DE COMPRAVENTA DE BIEN MUEBLE", styles['Title'])
    
    # Datos de la tabla: [Columna 1 (Logo), Columna 2 (Título)]
    data_header = [[logo if logo else "", titulo_p]]
    
    # Creamos la tabla invisible. Anchos aproximados: 150pts logo, 300pts texto.
    t_header = Table(data_header, colWidths=[150, 300])
    
    # Estilo para alinear verticalmente al medio y horizontalmente cada celda
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), # Centrado vertical
        ('ALIGN', (0,0), (0,0), 'LEFT'),      # Logo a la izquierda
        ('ALIGN', (1,0), (1,0), 'CENTER'),    # Título centrado en su espacio
        # ('GRID', (0,0), (-1,-1), 1, colors.red), # <-- Descomentar para debug de bordes
    ]))
    
    story.append(t_header)
    story.append(Spacer(1, 30))
    # ---------------------------------------------------

    # CÁLCULOS Y VARIABLES (Igual que antes)
    hoy = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses[hoy.month - 1]
    primer_vencimiento_saldo = hoy + timedelta(days=30)
    mes_vencimiento = meses[primer_vencimiento_saldo.month - 1]

    monto_entrega_inicial = plan['valor_cuota']
    monto_saldo_restante = plan['precio_final'] - monto_entrega_inicial
    cuotas_restantes = plan['num_cuotas'] - 1

    texto_productos = "<br/>".join([f"- {i.get('MODELO', '')} ({i.get('cantidad', 1)})" for i in items])

    v = {
        "nombre": cliente['nombre'],
        "dni": cliente['dni'],
        "domicilio": cliente['direccion'],
        "precio_total": format_currency(plan['precio_final']),
        "precio_letras": num2words(plan['precio_final'], lang='es').upper() + " PESOS",
        "entrega_inicial": format_currency(monto_entrega_inicial),
        "saldo_restante": format_currency(monto_saldo_restante),
        "cant_cuotas_rest": str(cuotas_restantes),
        "valor_cuota": format_currency(plan['valor_cuota']),
        "dia_venc": str(hoy.day),
        "fecha_inicio_saldo": f"{primer_vencimiento_saldo.day} de {mes_vencimiento} de {primer_vencimiento_saldo.year}",
        "fecha_hoy_texto": f"{hoy.day} de {mes_actual} de {hoy.year}"
    }

    # TEXTO DEL CONTRATO (Igual que antes)
    texto_intro = f"""
    En Ciudad de Oberá, Provincia de Misiones, a los {hoy.day} días del mes de {mes_actual} del año {hoy.year}, entre:<br/><br/>
    <b>VENDEDOR:</b> El Galpón S.R.L., CUIT Nº 33-71080122-9, con domicilio en Av. Alberdi 950, en adelante "EL VENDEDOR"; y<br/><br/>
    <b>COMPRADOR:</b> {v['nombre']}, DNI Nº {v['dni']}, con domicilio en {v['domicilio']}, en adelante "EL COMPRADOR";<br/><br/>
    celebran el presente Contrato de Compraventa de Bien Mueble, conforme a las siguientes cláusulas:
    """
    story.append(Paragraph(texto_intro, style_body))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>PRIMERA: Objeto</b>", style_body))
    story.append(Paragraph(f"El VENDEDOR vende al COMPRADOR, quien acepta, los siguientes artículos:<br/>{texto_productos}", style_body))
    story.append(Spacer(1, 12))

    texto_precio = f"""
    <b>SEGUNDA: Precio</b><br/>
    El precio total de la compraventa es de <b>{v['precio_total']}</b> ({v['precio_letras']}), el cual el COMPRADOR abona al VENDEDOR de la siguiente manera:<br/>
    - Entrega inicial de <b>{v['entrega_inicial']}</b> en este acto.<br/>
    - Saldo de <b>{v['saldo_restante']}</b> a pagar en <b>{v['cant_cuotas_rest']}</b> cuotas mensuales, iguales y consecutivas de <b>{v['valor_cuota']}</b>, con vencimiento el día <b>{v['dia_venc']}</b> de cada mes, comenzando el <b>{v['fecha_inicio_saldo']}</b>.
    """
    story.append(Paragraph(texto_precio, style_body))
    story.append(Spacer(1, 12))

    texto_entrega = f"""
    <b>TERCERA: Entrega</b><br/>
    La entrega de los bienes se efectúa en el domicilio del VENDEDOR, en el día de la fecha ({v['fecha_hoy_texto']}).
    A partir de ese momento, el COMPRADOR asume la posesión, uso y riesgos de los bienes.
    """
    story.append(Paragraph(texto_entrega, style_body))
    story.append(Spacer(1, 12))

    texto_garantia = """
    <b>CUARTA: Garantía – Pagaré</b><br/>
    En garantía del cumplimiento del saldo de precio pactado, el COMPRADOR suscribe en este acto un pagaré sin protesto, por la suma total pendiente de pago, conforme a lo previsto en la Ley N° 5.965/63.
    """
    story.append(Paragraph(texto_garantia, style_body))
    story.append(Spacer(1, 12))

    texto_jurisdiccion = """
    <b>QUINTA: Jurisdicción</b><br/>
    Para cualquier controversia derivada del presente contrato, las partes se someten a la jurisdicción de los tribunales ordinarios de Oberá, Provincia de Misiones.
    """
    story.append(Paragraph(texto_jurisdiccion, style_body))
    story.append(Spacer(1, 40)) # Un buen espacio antes de las firmas

    # --- NUEVA LÓGICA DE FIRMA DIGITAL ---
    
    # 1. Definimos la ruta de la firma
    ruta_firma = RECURSOS_DIR / "firma_zacharuk.png"
    
    # Preparamos el objeto de imagen o un placeholder si no existe
    img_firma_vendedor = None
    
    if ruta_firma.exists():
        try:
            # Creamos el objeto Image de ReportLab
            # Ajustamos el tamaño (width=120px) para que no sea gigante. 
            # height='auto' mantiene la proporción.
            img_firma_vendedor = Image(str(ruta_firma), width=120, height=40)
            
            # Alineación horizontal centrada dentro de la celda de la tabla
            img_firma_vendedor.hAlign = 'CENTER' 
            
        except Exception as e:
            print(f"❌ Error cargando imagen de firma: {e}")
            img_firma_vendedor = "___________________________" # Fallback si falla
    else:
        print(f"⚠️ Warning: No se encontró la firma en {ruta_firma}")
        # Si no existe, volvemos a la línea de subrayado tradicional
        img_firma_vendedor = "___________________________"

    # 2. Reestructuramos la tabla de firmas
    # Ahora la primera fila contiene el Objeto Imagen (izquierda) 
    # y la línea de subrayado (derecha).
    tabla_firmas_data = [
        [img_firma_vendedor, "___________________________"], # Fila 1: Firma e Hilo
        ["FIRMA VENDEDOR", "FIRMA COMPRADOR"],               # Fila 2: Etiquetas
        ["El Galpón S.R.L.", f"{v['nombre']}"],               # Fila 3: Nombres
        ["CUIT: 33-71080122-9", f"DNI: {v['dni']}"]           # Fila 4: IDs
    ]
    
    # Mantenemos los anchos de columna
    t_firmas = Table(tabla_firmas_data, colWidths=[200, 200])
    
    # 3. Ajustamos los estilos de la tabla
    estilos_firmas = [
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        # Ajustamos los paddings para que la imagen se "acerque" al texto de abajo
        ('TOPPADDING', (0,0), (0,0), 0),      # Cero padding superior para la imagen
        ('BOTTOMPADDING', (0,0), (0,0), -10), # Padding negativo para "pegar" la firma a la etiqueta
        ('TOPPADDING', (0,1), (-1,-1), 2),    # Padding normal para el resto de las celdas
    ]
    
    t_firmas.setStyle(TableStyle(estilos_firmas))
    
    # Agregamos la tabla al story final
    story.append(t_firmas)

def _agregar_contenido_desglose(story, styles, cliente, plan):
    # --- ENCABEZADO: LOGO + DATOS EMPRESA ALINEADOS (NUEVO) ---
    logo = _obtener_logo_flowable()
    
    # Agrupamos los datos de la empresa en una lista para una sola celda
    datos_empresa = [
        Paragraph("Av. Alberdi 950 - Oberá, Misiones", styles['Normal']),
        Paragraph("Tel: 424566 | Cel: +54 3755 688810", styles['Normal'])
    ]
    
    data_header = [[logo if logo else "", datos_empresa]]
    t_header = Table(data_header, colWidths=[150, 300])
    
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    
    story.append(t_header)
    story.append(Spacer(1, 20))
    # ----------------------------------------------------------

    story.append(Paragraph("<br/>DETALLE DE CUOTAS", styles['Heading2']))
    story.append(Spacer(1, 10))

    story.append(Paragraph(f"<br/><b>Cliente:</b> {cliente['nombre']}", styles['Normal']))
    story.append(Paragraph(f"<b>DNI:</b> {cliente['dni']}", styles['Normal']))
    story.append(Spacer(1, 15))

    # TABLA DE CUOTAS (Igual que antes, con la corrección de fechas)
    data = [["NRO CUOTA", "FECHA VENCIMIENTO", "MONTO"]]
    hoy = datetime.now()
    
    for i in range(plan['num_cuotas']):
        numero_cuota = i + 1
        if i == 0:
            venc = hoy
            texto_extra = " (Entrega)"
        else:
            venc = hoy + timedelta(days=30 * i)
            texto_extra = ""

        data.append([
            str(numero_cuota) + texto_extra,
            venc.strftime("%d/%m/%Y"),
            format_currency(plan['valor_cuota'])
        ])

    t = Table(data, colWidths=[100, 130, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    condiciones = """
    <br/><b>CONDICIONES DEL CRÉDITO:</b><br/>
    - PAGOS EN EFECTIVO, TRANSFERENCIA O TARJETAS SEGÚN ACUERDO.<br/>
    - EN CASO DE RETRASO, PODRÁN APLICARSE INTERESES ADICIONALES.<br/>
    - FIRMAR PAGARÉ Y CONTRATO COMPRA-VENTA.<br/>
    """
    story.append(Paragraph(condiciones, styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Fecha de Emisión: {hoy.strftime('%d/%m/%Y')}", styles['Normal']))

# ==============================================================================
# SECCIÓN 2: GENERACIÓN DE COMPROBANTES DE VENTA (CONTADO/TARJETA)
# ==============================================================================

def generar_comprobante_venta(factura: dict) -> str:
    ensure_dirs()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Recibo_Venta_{factura['id']}_{timestamp}.pdf"
    filepath = DIR_COMPROBANTES / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # --- ENCABEZADO ---
    logo = _obtener_logo_flowable()
    
    titulo_p = Paragraph("COMPROBANTE DE VENTA", styles['Heading2'])
    
    # Agrupamos texto
    datos_texto = [titulo_p]

    data_header = [[logo if logo else "", datos_texto]]
    t_header = Table(data_header, colWidths=[150, 300])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 12))
    # ------------------------------------------------------------------
    
    p_header = f"""
    <b>Fecha:</b> {factura.get('fecha', '')}<br/>
    <b>Comprobante N°:</b> {factura['id']}<br/>
    <b>Método de Pago:</b> {factura.get('metodo_pago', '-')}<br/>
    """
    story.append(Paragraph(p_header, styles['Normal']))
    story.append(Spacer(1, 20))
    # --- TABLA DE ITEMS ---
    data = [["CANT", "DESCRIPCIÓN", "P. UNIT", "SUBTOTAL"]]
    items = factura.get('items', [])
    
    # 1. Definimos un estilo para la celda de descripción
    # Esto permite que el texto haga "salto de línea" si es muy largo
    estilo_celda = ParagraphStyle(name='CeldaDesc', parent=styles['Normal'], fontSize=10, leading=12)

    for item in items:
        cant = int(item.get('cantidad', 1))
        modelo = item.get('modelo', item.get('MODELO', 'Articulo'))
        desc = item.get('descripcion', '')
        
        nombre_completo = f"{modelo} {desc}".strip()
        
        # 2. Envolvemos el texto en un Paragraph
        p_descripcion = Paragraph(nombre_completo, estilo_celda)
        
        p_unit = float(item.get('precio_unitario', 0))
        subtotal = p_unit * cant
        
        data.append([
            str(cant), 
            p_descripcion,
            format_currency(p_unit), 
            format_currency(subtotal)
        ])

    data.append(["", "", "TOTAL", format_currency(factura['total'])])

    t = Table(data, colWidths=[50, 250, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),     # Alineación Horizontal Global: Centro
        ('ALIGN', (1,1), (1,-1), 'LEFT'),        # Alineación Horizontal Descripción: Izquierda
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),    # Alineación Vertical: Medio (IMPORTANTE para celdas multilínea)
        
        ('GRID', (0,0), (-1,-2), 1, colors.black),
        ('lineabove', (0,-1), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (-2,-1), (-1,-1), colors.whitesmoke),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 40))

    pie = """
    Gracias por su compra.<br/>
    El Galpón - Colchonería y Blanquería<br/>
    <i>Documento no válido como factura fiscal</i>
    """
    estilo_pie = ParagraphStyle('Pie', parent=styles['Normal'], alignment=1)
    story.append(Paragraph(pie, estilo_pie))

    doc.build(story)
    return str(filepath)

# ==============================================================================
# SECCIÓN 3: GENERACIÓN DE COMPROBANTES DE CRÉDITO
# ==============================================================================

def generar_detalle_credito_pdf(credito: dict, cuotas: list) -> str:
    """
    Genera un PDF con el estado actual del crédito y el cronograma de cuotas
    basado en los datos reales guardados en la BD.
    """
    ensure_dirs()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Estado_Credito_{credito['id']}_{timestamp}.pdf"
    filepath = DIR_COMPROBANTES / filename # Lo guardamos en comprobantes o podrías crear otra carpeta

    doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # --- ENCABEZADO: LOGO + DATOS EMPRESA ---
    logo = _obtener_logo_flowable()
    
    datos_empresa = [
        Paragraph("<b>EL GALPÓN</b>", styles['Title']),
        Paragraph("ESTADO DE CUENTA / CRÉDITO", styles['Heading3']),
        Paragraph(f"Crédito N°: {credito['id']}", styles['Normal']),
        Paragraph(f"Fecha Venta: {credito.get('fecha_venta', '-')}", styles['Normal'])
    ]
    
    data_header = [[logo if logo else "", datos_empresa]]
    t_header = Table(data_header, colWidths=[150, 300])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 20))

    # --- DATOS CLIENTE ---
    story.append(Paragraph(f"<b>Cliente:</b> {credito['nombre']}", styles['Normal']))
    story.append(Paragraph(f"<b>DNI:</b> {credito['dni']}", styles['Normal']))
    story.append(Spacer(1, 15))

    # --- TABLA DE CUOTAS (Desde la BD) ---
    # Columnas: Cuota | Vencimiento | Monto | Estado
    data = [["CUOTA", "VENCIMIENTO", "MONTO", "ESTADO"]]
    
    for c in cuotas:
        # Formateo de estado
        estado = c['estado']
        if estado == 'PAGADO':
            estado_fmt = f"PAGADO ({c.get('fecha_pago', '')})"
            color_text = colors.green
        elif estado == 'MORA': # Si usas este estado
            estado_fmt = "VENCIDA / IMPAGA"
            color_text = colors.red
        else:
            # Verificamos vencimiento manual si sigue como Pendiente
            hoy_str = datetime.now().strftime("%Y-%m-%d")
            if c['fecha_vencimiento'] < hoy_str and estado == 'PENDIENTE':
                estado_fmt = "VENCIDA"
                color_text = colors.red
            else:
                estado_fmt = "A VENCER"
                color_text = colors.black

        # Formateo de fecha (YYYY-MM-DD a DD/MM/YYYY)
        try:
            fecha_obj = datetime.strptime(c['fecha_vencimiento'], '%Y-%m-%d')
            fecha_fmt = fecha_obj.strftime("%d/%m/%Y")
        except:
            fecha_fmt = c['fecha_vencimiento']

        row = [
            str(c['numero_cuota']),
            fecha_fmt,
            format_currency(c['monto']),
            estado_fmt
        ]
        data.append(row)

    # Estilos de tabla
    t = Table(data, colWidths=[60, 100, 100, 150])
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ])
    
    # Colorear filas según estado (opcional, avanzado)
    # Aquí lo dejamos simple, pero podríamos iterar para pintar textos específicos
    
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 20))

    # --- PIE DE PÁGINA ---
    pie = """
    Documento emitido para control interno y seguimiento del cliente.<br/>
    El Galpón - Colchonería y Blanquería
    """
    estilo_pie = ParagraphStyle('Pie', parent=styles['Normal'], alignment=1)
    story.append(Paragraph(pie, estilo_pie))

    doc.build(story)
    return str(filepath)