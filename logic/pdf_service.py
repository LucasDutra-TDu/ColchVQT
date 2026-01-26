import os
from datetime import datetime, timedelta
from pathlib import Path
from num2words import num2words
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT

# Imports de formateo
from logic.financiero import format_currency

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output_docs"

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def num_a_letras(numero: float) -> str:
    try:
        texto = num2words(numero, lang='es').upper()
        return texto + " PESOS"
    except:
        return ""

def _sanitizar_nombre(nombre: str) -> str:
    return "".join([c if c.isalnum() else "_" for c in nombre])

def generar_documentacion_credito(cliente: dict, items: list, plan: dict) -> str:
    """
    Genera un único PDF con tres páginas:
    Pag 1: Contrato de Compraventa (Copia 1).
    Pag 2: Contrato de Compraventa (Copia 2 - Igual a la anterior).
    Pag 3: Desglose de Cuotas.
    """
    ensure_dirs()
    
    nombre_safe = _sanitizar_nombre(cliente['nombre'])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Credito_{nombre_safe}_{cliente['dni']}_{timestamp}.pdf"
    filepath = OUTPUT_DIR / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    # --- PÁGINA 1: CONTRATO (Original) ---
    _agregar_contenido_contrato(story, styles, cliente, items, plan)
    
    # Salto de página
    story.append(PageBreak())

    # --- PÁGINA 2: CONTRATO (Duplicado) ---
    # Volvemos a llamar a la misma función con los mismos datos
    _agregar_contenido_contrato(story, styles, cliente, items, plan)
    
    # Salto de página
    story.append(PageBreak())
    
    # --- PÁGINA 3: DESGLOSE ---
    _agregar_contenido_desglose(story, styles, cliente, plan)
    
    doc.build(story)
    return str(filepath)

def _agregar_contenido_contrato(story, styles, cliente, items, plan):
    # Estilos
    style_body = ParagraphStyle(name='Justify', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=10, leading=14)
    style_title = ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=20)

    # --- CÁLCULOS DE FECHAS ---
    hoy = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses[hoy.month - 1]
    
    # El primer vencimiento del SALDO es un mes después de hoy
    primer_vencimiento_saldo = hoy + timedelta(days=30)
    mes_vencimiento = meses[primer_vencimiento_saldo.month - 1]

    # --- CÁLCULOS FINANCIEROS PARA EL TEXTO ---
    monto_entrega_inicial = plan['valor_cuota'] # La 1ra cuota se paga ya
    monto_saldo_restante = plan['precio_final'] - monto_entrega_inicial
    cuotas_restantes = plan['num_cuotas'] - 1 # N-1

    # Formateo de productos
    texto_productos = "<br/>".join([f"- {i.get('MODELO', '')} ({i.get('cantidad', 1)})" for i in items])

    # Variables de texto formateadas
    v = {
        "nombre": cliente['nombre'],
        "dni": cliente['dni'],
        "domicilio": cliente['direccion'],
        "precio_total": format_currency(plan['precio_final']),
        "precio_letras": num_a_letras(plan['precio_final']),
        
        # Nuevas variables para el formato solicitado
        "entrega_inicial": format_currency(monto_entrega_inicial),
        "saldo_restante": format_currency(monto_saldo_restante),
        "cant_cuotas_rest": str(cuotas_restantes),
        "valor_cuota": format_currency(plan['valor_cuota']),
        
        "dia_venc": str(hoy.day), # Vence el mismo día numérico de cada mes
        "fecha_inicio_saldo": f"{primer_vencimiento_saldo.day} de {mes_vencimiento} de {primer_vencimiento_saldo.year}",
        
        "fecha_hoy_texto": f"{hoy.day} de {mes_actual} de {hoy.year}"
    }

    # --- REDACCIÓN DEL DOCUMENTO ---

    story.append(Paragraph("CONTRATO DE COMPRAVENTA DE BIEN MUEBLE", style_title))
    
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

    # --- CLÁUSULA SEGUNDA CORREGIDA ---
    texto_precio = f"""
    <b>SEGUNDA: Precio</b><br/>
    El precio total de la compraventa es de <b>{v['precio_total']}</b> ({v['precio_letras']}), el cual el COMPRADOR abona al VENDEDOR de la siguiente manera:<br/>
    - Entrega inicial de <b>{v['entrega_inicial']}</b> en este acto.<br/>
    - Saldo de <b>{v['saldo_restante']}</b> a pagar en <b>{v['cant_cuotas_rest']}</b> cuotas mensuales, iguales y consecutivas de <b>{v['valor_cuota']}</b>, con vencimiento cada 30 días, comenzando el <b>{v['fecha_inicio_saldo']}</b>.
    """
    story.append(Paragraph(texto_precio, style_body))
    story.append(Spacer(1, 12))
    # ----------------------------------

    texto_entrega = f"""
    <b>TERCERA: Entrega</b><br/>
    La entrega de los bienes se efectúa en el domicilio del VENDEDOR, en el día de la fecha ({v['fecha_hoy_texto']}).
    A partir de ese momento, el COMPRADOR asume la posesión, uso y riesgos de los bienes.
    """
    story.append(Paragraph(texto_entrega, style_body))
    story.append(Spacer(1, 12))

    texto_garantia = """
    <b>CUARTA: Garantía – Pagaré</b><br/>
    En garantía del cumplimiento del saldo de precio pactado, el COMPRADOR suscribe en este acto un pagaré sin protesto, por la suma total pendiente de pago, conforme a lo previsto en la Ley N° 5.965/63 (Ley de Letras de Cambio y Pagaré). 
    Renunciando expresamente al protesto, a cualquier beneficio de excusión y división, y sometiéndose a la competencia de los tribunales ordinarios de Oberá, Provincia de Misiones.
    """
    story.append(Paragraph(texto_garantia, style_body))
    story.append(Spacer(1, 12))

    texto_jurisdiccion = """
    <b>QUINTA: Jurisdicción</b><br/>
    Para cualquier controversia derivada del presente contrato, las partes se someten a la jurisdicción de los tribunales ordinarios de Oberá, Provincia de Misiones. Con renuncia expresa a cualquier otro fuero o jurisdicción.<br/>

    En prueba de conformidad, se firman dos (2) ejemplares de un mismo tenor y a un solo efecto, en el lugar y fecha indicados.
    """
    story.append(Paragraph(texto_jurisdiccion, style_body))
    story.append(Spacer(1, 30))

    tabla_firmas_data = [
        ["___________________________", "___________________________"],
        ["FIRMA VENDEDOR", "FIRMA COMPRADOR"],
        ["El Galpón S.R.L.", f"{v['nombre']}"],
        ["CUIT: 33-71080122-9", f"DNI: {v['dni']}"]
    ]
    t_firmas = Table(tabla_firmas_data, colWidths=[200, 200])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_firmas)

def _agregar_contenido_desglose(story, styles, cliente, plan):
    story.append(Paragraph("<b>EL GALPÓN</b>", styles['Title']))
    story.append(Paragraph("COLCHONERÍA Y BLANQUERÍA", styles['Heading3']))
    story.append(Paragraph("Av. Alberdi 950 - Oberá, Misiones", styles['Normal']))
    story.append(Paragraph("Tel: 424566 | Cel: +54 3755 688810", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("DETALLE DE CUOTAS", styles['Heading2']))
    story.append(Spacer(1, 10))

    story.append(Paragraph(f"<b>Cliente:</b> {cliente['nombre']}", styles['Normal']))
    story.append(Paragraph(f"<b>DNI:</b> {cliente['dni']}", styles['Normal']))
    story.append(Spacer(1, 15))

    data = [["NRO CUOTA", "FECHA VENCIMIENTO", "MONTO"]]
    hoy = datetime.now()
    
    for i in range(1, plan['num_cuotas'] + 1):
        venc = hoy + timedelta(days=30*i)
        data.append([
            str(i),
            venc.strftime("%d/%m/%Y"),
            format_currency(plan['valor_cuota'])
        ])

    t = Table(data, colWidths=[80, 150, 100])
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
    <b>CONDICIONES DEL CRÉDITO:</b><br/>
    - PAGOS EN EFECTIVO, TRANSFERENCIA O TARJETAS SEGÚN ACUERDO.<br/>
    - EN CASO DE RETRASO, PODRÁN APLICARSE INTERESES ADICIONALES.<br/>
    - FIRMAR PAGARÉ Y CONTRATO COMPRA-VENTA.
    """
    story.append(Paragraph(condiciones, styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph(f"Fecha de Emisión: {hoy.strftime('%d/%m/%Y')}", styles['Normal']))