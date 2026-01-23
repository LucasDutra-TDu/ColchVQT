import os
from datetime import datetime, timedelta
from pathlib import Path
from num2words import num2words
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT

# Imports de formateo
from logic.financiero import format_currency

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output_docs"

def ensure_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def num_a_letras(numero: float) -> str:
    """Convierte número a texto en Español (ej: 100 -> CIEN)."""
    try:
        texto = num2words(numero, lang='es').upper()
        return texto + " PESOS"
    except:
        return ""

def _sanitizar_nombre(nombre: str) -> str:
    """Reemplaza espacios y caracteres raros para usar en nombre de archivo."""
    # Ej: "Juan Perez" -> "Juan_Perez"
    return "".join([c if c.isalnum() else "_" for c in nombre])

def generar_contrato_pdf(cliente: dict, items: list, plan: dict) -> str:
    """
    Genera el Contrato de Compraventa.
    """
    ensure_dirs()
    
    # --- CAMBIO AQUÍ: Nombre en el archivo ---
    nombre_safe = _sanitizar_nombre(cliente['nombre'])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Contrato_{nombre_safe}_{cliente['dni']}_{timestamp}.pdf"
    # -----------------------------------------
    
    filepath = OUTPUT_DIR / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # Estilos
    style_body = ParagraphStyle(name='Justify', parent=styles['Normal'], alignment=TA_JUSTIFY, fontSize=10, leading=14)
    style_title = ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=14, spaceAfter=20)

    # Datos
    hoy = datetime.now()
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_actual = meses[hoy.month - 1]
    
    primer_vencimiento = hoy + timedelta(days=30)
    mes_vencimiento = meses[primer_vencimiento.month - 1]

    texto_productos = "<br/>".join([f"- {i.get('MODELO', '')} ({i.get('cantidad', 1)})" for i in items])

    v = {
        "nombre": cliente['nombre'],
        "dni": cliente['dni'],
        "domicilio": cliente['direccion'],
        "precio_total": format_currency(plan['precio_final']),
        "precio_letras": num_a_letras(plan['precio_final']),
        "valor_cuota": format_currency(plan['valor_cuota']),
        "saldo_restante": format_currency(plan['precio_final'] - plan['valor_cuota']),
        "cant_cuotas_rest": str(plan['num_cuotas']),
        "dia_venc": str(hoy.day),
        "fecha_1_venc": f"{primer_vencimiento.day} de {mes_vencimiento} de {primer_vencimiento.year}",
        "fecha_hoy": f"{hoy.day} de {mes_actual} de {hoy.year}"
    }

    # Contenido
    contenido = []
    contenido.append(Paragraph("CONTRATO DE COMPRAVENTA DE BIEN MUEBLE", style_title))
    
    texto_intro = f"""
    En Ciudad de Oberá, Provincia de Misiones, a los {hoy.day} días del mes de {mes_actual} del año {hoy.year}, entre:<br/><br/>
    <b>VENDEDOR:</b> El Galpón S.R.L., CUIT Nº 33-71080122-9, con domicilio en Av. Alberdi 950, en adelante "EL VENDEDOR"; y<br/><br/>
    <b>COMPRADOR:</b> {v['nombre']}, DNI Nº {v['dni']}, con domicilio en {v['domicilio']}, en adelante "EL COMPRADOR";<br/><br/>
    celebran el presente Contrato de Compraventa de Bien Mueble, conforme a las siguientes cláusulas:
    """
    contenido.append(Paragraph(texto_intro, style_body))
    contenido.append(Spacer(1, 12))

    contenido.append(Paragraph("<b>PRIMERA: Objeto</b>", style_body))
    contenido.append(Paragraph(f"El VENDEDOR vende al COMPRADOR, quien acepta, los siguientes artículos:<br/>{texto_productos}", style_body))
    contenido.append(Spacer(1, 12))

    texto_precio = f"""
    <b>SEGUNDA: Precio</b><br/>
    El precio total de la compraventa es de <b>{v['precio_total']}</b> ({v['precio_letras']}), el cual el COMPRADOR abonará en <b>{plan['num_cuotas']}</b> cuotas mensuales, iguales y consecutivas de <b>{v['valor_cuota']}</b>.<br/>
    El vencimiento operará el día {v['dia_venc']} de cada mes, comenzando el {v['fecha_1_venc']}.
    """
    contenido.append(Paragraph(texto_precio, style_body))
    contenido.append(Spacer(1, 12))

    texto_entrega = f"""
    <b>TERCERA: Entrega</b><br/>
    La entrega de los bienes se efectúa en el domicilio del VENDEDOR, en el día de la fecha ({v['fecha_hoy']}).
    A partir de ese momento, el COMPRADOR asume la posesión, uso y riesgos de los bienes.
    """
    contenido.append(Paragraph(texto_entrega, style_body))
    contenido.append(Spacer(1, 12))

    texto_garantia = """
    <b>CUARTA: Garantía – Pagaré</b><br/>
    En garantía del cumplimiento del saldo de precio pactado, el COMPRADOR suscribe en este acto un pagaré sin protesto, por la suma total pendiente de pago, conforme a lo previsto en la Ley N° 5.965/63.
    """
    contenido.append(Paragraph(texto_garantia, style_body))
    contenido.append(Spacer(1, 12))

    texto_jurisdiccion = """
    <b>QUINTA: Jurisdicción</b><br/>
    Para cualquier controversia derivada del presente contrato, las partes se someten a la jurisdicción de los tribunales ordinarios de Oberá, Provincia de Misiones.
    """
    contenido.append(Paragraph(texto_jurisdiccion, style_body))
    contenido.append(Spacer(1, 30))

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
    contenido.append(t_firmas)

    doc.build(contenido)
    return str(filepath)

def generar_desglose_pdf(cliente: dict, plan: dict) -> str:
    """
    Genera la tabla de cuotas.
    """
    ensure_dirs()
    
    # --- CAMBIO AQUÍ: Nombre en el archivo ---
    nombre_safe = _sanitizar_nombre(cliente['nombre'])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Desglose_{nombre_safe}_{cliente['dni']}_{timestamp}.pdf"
    # -----------------------------------------
    
    filepath = OUTPUT_DIR / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("<b>EL GALPÓN</b>", styles['Title']))
    elements.append(Paragraph("COLCHONERÍA Y BLANQUERÍA", styles['Heading3']))
    elements.append(Paragraph("Av. Alberdi 950 - Oberá, Misiones", styles['Normal']))
    elements.append(Paragraph("Tel: 424566 | Cel: +54 3755 688810", styles['Normal']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("DETALLE DE CUOTAS", styles['Heading2']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Cliente:</b> {cliente['nombre']}", styles['Normal']))
    elements.append(Paragraph(f"<b>DNI:</b> {cliente['dni']}", styles['Normal']))
    elements.append(Spacer(1, 15))

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
    elements.append(t)
    elements.append(Spacer(1, 20))

    condiciones = """
    <b>CONDICIONES DEL CRÉDITO:</b><br/>
    - PAGOS EN EFECTIVO, TRANSFERENCIA O TARJETAS SEGÚN ACUERDO.<br/>
    - EN CASO DE RETRASO, PODRÁN APLICARSE INTERESES ADICIONALES.<br/>
    - FIRMAR PAGARÉ Y CONTRATO COMPRA-VENTA.
    """
    elements.append(Paragraph(condiciones, styles['Normal']))
    elements.append(Spacer(1, 30))

    elements.append(Paragraph(f"Fecha de Emisión: {hoy.strftime('%d/%m/%Y')}", styles['Normal']))

    doc.build(elements)
    return str(filepath)