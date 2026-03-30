import io
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from logic.constants import IMG_CATALOGO_DIR, RUTA_FONT_FLYER, RUTA_LOGO_EMPRESA
from logic.financiero import format_currency # Usamos tu función existente

import re
from pathlib import Path


def obtener_ruta_imagen(row: dict):
    """
    Verifica si existe una imagen asociada al producto. 
    Busca de forma flexible por CÓDIGO o MODELO, manejando Floats de Pandas.
    """
    
    # 1. Obtener el valor crudo de CÓDIGO (con tilde), CODIGO, o MODELO
    val = row.get('CÓDIGO', row.get('CODIGO', row.get('MODELO')))
    
    # Checkeamos si es nulo (None o NaN de Pandas)
    if val is None or pd.isna(val) or str(val).strip() in ['', '-', 'None', 'nan']:
        return None

    # ---------------------------------------------------------
    # 🛠️ CORAZÓN DE LA SOLUCIÓN: MANEJO DE TIPOS DE DATOS 🛠️
    # ---------------------------------------------------------
    try:
        if isinstance(val, (float, int)):
            # --- EL ARREGLO PARA EL BUG DE BÚSQUEDA ---
            # Si val es 1000.0 (float) -> int(1000.0) es 1000 (int) -> str(1000) es "1000"
            identificador = str(int(float(val))).strip()
        else:
            # Es texto normal (como "GANI-100"), solo limpiamos espacios
            identificador = str(val).strip()
    except Exception as e:
        # Fallback de seguridad si la conversión numérica falla
        print(f"⚠️ Warning: Error convirtiendo ID '{val}': {e}")
        identificador = str(val).strip()
    # ---------------------------------------------------------

    if not identificador or identificador in ['0', 'nan']:
        return None
        
    # 2. Sanitizar nombre para Windows (quitar caracteres prohibidos \/*?:"<>|)
    nombre_seguro = re.sub(r'[\\/*?:"<>|]', "", identificador).strip()
    
    #  DIAGNÓSTICO (Opcional, descomenta si sigue fallando)
    # print(f"🔍 DEBUG FISICO: Buscando '{nombre_seguro}.png' en {IMG_CATALOGO_DIR}")
    
    # 3. Buscar soportando varias extensiones comunes
    for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG']:
        ruta = IMG_CATALOGO_DIR / f"{nombre_seguro}{ext}"
        if ruta.exists():
            return ruta
            
    return None


def draw_text_wrapped(draw, text, x, y, font, max_width, fill):
    """
    Dibuja un texto dividiéndolo en múltiples líneas si excede el max_width.
    Retorna la nueva coordenada Y después de dibujar.
    """
    lines = []
    words = text.split()
    
    while words:
        line = ''
        while words and draw.textbbox((0, 0), line + words[0], font=font)[2] <= max_width:
            line += (words.pop(0) + ' ')
        lines.append(line.strip())
    
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=fill)
        # Calculamos el alto de la línea para el siguiente salto
        bbox = draw.textbbox((x, current_y), line, font=font)
        line_height = bbox[3] - bbox[1]
        current_y += line_height + 10 # 10px de interlineado
        
    return current_y


def generar_flyer_producto(row: dict, ruta_imagen: Path, ruta_logo: Path = None) -> io.BytesIO:
    """
    Genera un flyer visual combinando foto del producto, logo de la empresa y texto completo.
    """
    canvas_width = 1200
    canvas_height = 800
    # Fondo blanco puro
    flyer = Image.new('RGB', (canvas_width, canvas_height), color='white')
    draw = ImageDraw.Draw(flyer)

    # Definir tipografía por defecto (puedes usar RUTA_FONT_FLYER si la tienes)
    # Aquí usaré fuentes genéricas para que no falle, ajústalas a tus .ttf si tienes
    try:
        # Asumiendo que RUTA_FONT_FLYER está definida en constants
        # font_path = str(RUTA_FONT_FLYER) 
        # Pero usaré una ruta por defecto por seguridad:
        font_path = "arial.ttf" # ReportLab/Pillow a veces encuentran arial
        font_main = ImageFont.truetype(font_path, 32)
        font_title = ImageFont.truetype(font_path, 45)
        font_price = ImageFont.truetype(font_path, 38)
    except Exception:
        # Fallback si no hay fuentes instaladas
        font_main = font_title = font_price = ImageFont.load_default()

    text_color = (44, 62, 80) # Azul oscuro elegante

    # ------------------------------------------------------------------------
    # 🆕 1.1 LOGO DE LA EMPRESA (Arriba a la derecha) 🆕
    # ------------------------------------------------------------------------
    if ruta_logo is None:
        ruta_logo = Path("data/recursos/elgalpon.png")

    # Mantenemos el cálculo del tamaño agrandado
    base_logo_width = 200
    base_logo_height = 100
    factor_escalado = 1.75
    logo_area_size = (int(base_logo_width * factor_escalado), int(base_logo_height * factor_escalado)) 
    
    # Mantenemos la posición en la esquina superior derecha
    logo_x = canvas_width - logo_area_size[0] - 50 
    # Definimos el margen superior (Y) de forma explícita
    margin_top_logo = 30
    logo_y = margin_top_logo 

    # Guardamos la coordenada Y inferior del logo para usarla de referencia
    # Y inferior = Coordenada Y superior + Altura del área asignada
    logo_bottom_y = logo_y + logo_area_size[1] 

    if ruta_logo.exists():
        try:
            logo_img = Image.open(ruta_logo)
            logo_img.thumbnail(logo_area_size, Image.Resampling.LANCZOS)
            
            if logo_img.mode == 'RGBA':
                flyer.paste(logo_img, (logo_x, logo_y), logo_img)
            else:
                flyer.paste(logo_img, (logo_x, logo_y))
            
            # print(f"✅ Logo '{ruta_logo.name}' incrustado. Y inferior: {logo_bottom_y}.")
        except Exception as e:
            print(f"❌ Error al incrustar el logo: {e}")
            # Si falla el logo, el fallback de logo_bottom_y sigue sirviendo
    else:
        print(f"⚠️ Warning: No se encontró el logo en {ruta_logo}. Flyer sin branding.")
        # Fallback de seguridad si no hay logo: simulamos que termina más arriba
        logo_bottom_y = margin_top_logo + 50 # Un margen pequeño

    # ------------------------------------------------------------------------


    # 2. Procesamiento de la Imagen del Colchón (Lado Izquierdo)
    image_area_size = (650, 650)
    image_x_offset = 50
    image_y_offset = (canvas_height - image_area_size[1]) // 2

    try:
        # Abrimos la ruta exacta que nos pasó el wrapper
        prod_img = Image.open(ruta_imagen)
        prod_img.thumbnail(image_area_size, Image.Resampling.LANCZOS)
        
        # Centrar la imagen en su recuadro
        img_w, img_h = prod_img.size
        paste_x = image_x_offset + (image_area_size[0] - img_w) // 2
        paste_y = image_y_offset + (image_area_size[1] - img_h) // 2
        
        # Pegar respetando transparencias (crucial para .png)
        if prod_img.mode == 'RGBA':
            flyer.paste(prod_img, (paste_x, paste_y), prod_img)
        else:
            flyer.paste(prod_img, (paste_x, paste_y))
            
    except Exception as e:
        print(f"❌ Error al incrustar la imagen del producto: {e}")

    # 🆕 3. Lógica de Texto (Lado Derecho)
    text_x = 750
    max_text_width = canvas_width - text_x - 50 # Margen de 50px a la derecha
    
    aire_texto = -10
    current_y = logo_bottom_y + aire_texto

    # --- Título con Auto-Wrap ---
    marca = str(row.get('PROVEEDOR', '-')).strip().upper()
    modelo = str(row.get('MODELO', '-')).strip()

    # Dibujamos la Marca (Normalmente es corta, pero por las dudas usamos wrap)
    current_y = draw_text_wrapped(draw, marca, text_x, current_y, font_title, max_text_width, text_color)
    
    # Espacio pequeño entre marca y modelo
    current_y += 10 
    
    # Dibujamos el Modelo (Aquí es donde suele pasarse de largo)
    current_y = draw_text_wrapped(draw, modelo, text_x, current_y, font_title, max_text_width, text_color)

    # Espacio después del título antes de los detalles
    current_y += 30 

    # --- Resto de Atributos (Medida, Material, etc.) ---
    # ... (Sigue dibujando Medida, Material, Soporta, Separador, Precios - SIN CAMBIOS) ...
    # (El resto del código ya funciona perfecto, solo asegúrate de que esté aquí)
    medida = row.get('MEDIDA (LARG-ANCH-ESP)')
    if pd.notna(medida) and str(medida) != '-':
        draw.text((text_x, current_y), f"Medida: {medida}", font=font_main, fill=text_color)
        current_y += 45

    material = row.get('MATERIAL')
    if pd.notna(material) and str(material) != '-':
        draw.text((text_x, current_y), f"Material: {material}", font=font_main, fill=text_color)
        current_y += 45

    soporta = row.get('SOPORTA (PORPLAZA)')
    if pd.notna(soporta) and str(soporta) != '-':
        soporta_str = str(soporta).replace('KG', '').replace('kg', '').strip()
        draw.text((text_x, current_y), f"Soporta: {soporta_str} KG", font=font_main, fill=text_color)
        current_y += 45

    current_y += 20
    draw.line([text_x, current_y, canvas_width-50, current_y], fill="lightgray", width=2)
    current_y += 40

    precio_efectivo = row.get('EFECTIVO/TRANSF')
    if pd.notna(precio_efectivo) and str(precio_efectivo).strip() not in ['', '-', 'None']:
        if isinstance(precio_efectivo, (int, float)):
            precio_efectivo = format_currency(precio_efectivo)
        draw.text((text_x, current_y), "Efectivo/Transf:", font=font_main, fill=text_color)
        current_y += 35
        draw.text((text_x, current_y), f"{precio_efectivo}", font=font_price, fill=(39, 174, 96))
        current_y += 60

    precio_tarjeta = row.get('DEBIT/CREDIT', row.get('LISTA/TARJETA'))
    if pd.notna(precio_tarjeta) and str(precio_tarjeta).strip() not in ['', '-', 'None']:
        if isinstance(precio_tarjeta, (int, float)):
            precio_tarjeta = format_currency(precio_tarjeta)
        draw.text((text_x, current_y), "Lista/Tarjeta:", font=font_main, fill=text_color)
        current_y += 35
        draw.text((text_x, current_y), f"{precio_tarjeta}", font=font_price, fill=text_color)

    # 4. Exportar a Bytes (Final)
    img_io = io.BytesIO()
    # Usamos PNG para preservar transparencias y calidad
    flyer.save(img_io, format='PNG')
    img_io.seek(0)
    
    return img_io

