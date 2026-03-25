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


def generar_flyer_producto(row: dict, ruta_imagen: Path) -> io.BytesIO:
    """
    Genera un flyer visual combinando foto del producto y texto completo.
    """
    canvas_width = 1200
    canvas_height = 800
    flyer = Image.new('RGB', (canvas_width, canvas_height), color='white')
    draw = ImageDraw.Draw(flyer)

    # 1. Carga de Tipografía
    try:
        font_main = ImageFont.truetype(str(RUTA_FONT_FLYER), 32)
        font_title = ImageFont.truetype(str(RUTA_FONT_FLYER), 45)
        font_price = ImageFont.truetype(str(RUTA_FONT_FLYER), 38)
    except Exception:
        font_main = font_title = font_price = ImageFont.load_default()

    text_color = (44, 62, 80)

    # 2. Procesamiento de la Imagen (Lado Izquierdo)
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
        print(f"❌ Error al incrustar la imagen: {e}")

    # 3. Lógica de Texto (Lado Derecho)
    text_x = 750
    current_y = 120

    # --- Título ---
    marca = str(row.get('PROVEEDOR', '-')).strip().upper()
    modelo = str(row.get('MODELO', '-')).strip()
    draw.text((text_x, current_y), f"{marca}", font=font_title, fill=text_color)
    current_y += 50
    draw.text((text_x, current_y), f"{modelo}", font=font_title, fill=text_color)
    current_y += 80

    # --- Atributos ---
    medida = row.get('MEDIDA (LARG-ANCH-ESP)')
    if pd.notna(medida) and str(medida) != '-':
        draw.text((text_x, current_y), f"Medida: {medida}", font=font_main, fill=text_color)
        current_y += 45

    # AGREGADO: Material
    material = row.get('MATERIAL')
    if pd.notna(material) and str(material) != '-':
        draw.text((text_x, current_y), f"Material: {material}", font=font_main, fill=text_color)
        current_y += 45

    soporta = row.get('SOPORTA (PORPLAZA)')
    if pd.notna(soporta) and str(soporta) != '-':
        # Limpiamos posibles "KG" duplicados por si ya vienen en el Excel
        soporta_str = str(soporta).replace('KG', '').replace('kg', '').strip()
        draw.text((text_x, current_y), f"Soporta: {soporta_str} KG", font=font_main, fill=text_color)
        current_y += 45

    # Separador
    current_y += 20
    draw.line([text_x, current_y, canvas_width-50, current_y], fill="lightgray", width=2)
    current_y += 40

    # --- Precios ---
    precio_efectivo = row.get('EFECTIVO/TRANSF')
    if pd.notna(precio_efectivo) and str(precio_efectivo).strip() not in ['', '-', 'None']:
        if isinstance(precio_efectivo, (int, float)):
            precio_efectivo = format_currency(precio_efectivo)
            
        draw.text((text_x, current_y), "Efectivo/Transf:", font=font_main, fill=text_color)
        current_y += 35
        # Precio en verde para destacar
        draw.text((text_x, current_y), f"{precio_efectivo}", font=font_price, fill=(39, 174, 96))
        current_y += 60

    # Tu Excel parece usar DEBIT/CREDIT o LISTA/TARJETA, revisamos ambas
    precio_tarjeta = row.get('DEBIT/CREDIT', row.get('LISTA/TARJETA'))
    if pd.notna(precio_tarjeta) and str(precio_tarjeta).strip() not in ['', '-', 'None']:
        if isinstance(precio_tarjeta, (int, float)):
            precio_tarjeta = format_currency(precio_tarjeta)
            
        draw.text((text_x, current_y), "Lista/Tarjeta:", font=font_main, fill=text_color)
        current_y += 35
        draw.text((text_x, current_y), f"{precio_tarjeta}", font=font_price, fill=text_color)

    # 4. Exportar a Bytes
    img_io = io.BytesIO()
    flyer.save(img_io, format='PNG')
    img_io.seek(0)
    
    return img_io

