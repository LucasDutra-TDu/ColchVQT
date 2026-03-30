# ui/views.py

from typing import Callable, Dict, Any, List
from functools import partial
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, 
    QFrame, QSizePolicy, QLineEdit, QMessageBox, QInputDialog, QApplication
)
from PySide6.QtCore import Qt

from PySide6.QtGui import QClipboard, QImage, QPixmap
from logic.image_service import generar_flyer_producto # Importamos el servicio nuevo

# Imports Propios
from logic.constants import ESTILOS, CAMPOS_CATALOGO, CATALOGO_ANCHOS, MAPEO_CLIPBOARD
from logic import catalogo_service
from logic.catalogo_service import formatear_producto_para_clipboard
# Importamos la nueva lógica financiera
from logic.financiero import calcular_plan_cuotas, format_currency, generar_texto_clipboard
from logic.cart_service import CartService

# Importamos las lógicas
from logic.image_service import generar_flyer_producto, obtener_ruta_imagen
from ui.widgets import ImageViewerDialog

from functools import partial

def _handle_calculo_cuotas(parent: QWidget, fila_data: dict):
    """Manejador del evento de cálculo de cuotas (Controller Logic)."""
    
    # --- CORRECCIÓN: IMPORTAR AL INICIO ---
    # Esto evita el UnboundLocalError y asegura que las funciones estén disponibles desde la línea 1
    from logic.financiero import format_currency, generar_texto_clipboard, TASA_INTERES_MENSUAL
    import math # Necesario para el math.ceil
    
    # 1. Validación del Precio Base
    precio_base_val = fila_data.get("EFECTIVO/TRANSF")
    if not precio_base_val:
        precio_base_val = fila_data.get("PRECIO", fila_data.get("CONTADO", 0))

    try:
        precio_base = float(precio_base_val)
    except (ValueError, TypeError):
        QMessageBox.warning(parent, "Error de Datos", f"El producto no tiene un precio base válido.\nValor: {precio_base_val}")
        return

    # 2. Interacción Usuario (Seleccionar Cuotas)
    cuotas_opciones = [str(i) for i in range(3, 13)]
    
    # AHORA SÍ: format_currency ya está definido aquí
    cuotas_str, ok = QInputDialog.getItem(
        parent, "Calcular Cuotas", 
        f"Precio Base: {format_currency(precio_base)}\n\nSeleccione cantidad de cuotas:",
        cuotas_opciones, 0, False
    )

    if ok and cuotas_str:
        try:
            # 3. Lógica Financiera (Inline segura)
            num_cuotas = int(cuotas_str)
            tasa = TASA_INTERES_MENSUAL * num_cuotas # 8% mensual
            precio_final = precio_base * (1 + tasa)
            
            # Regla de redondeo a 100
            valor_cuota = math.ceil((precio_final / num_cuotas) / 100) * 100
            precio_final_redondeado = valor_cuota * num_cuotas

            plan = {
                "num_cuotas": num_cuotas,
                "precio_base": precio_base,
                "precio_final": precio_final_redondeado,
                "valor_cuota": valor_cuota
            }

            # 4. Construcción de UI del Popup
            texto_html = (
                f"<h3 style='color:#2c3e50;'>Plan Crédito de la Casa</h3>"
                f"<hr>"
                f"<b>Precio Lista:</b> {format_currency(precio_base)}<br>"
                f"<b>Recargo:</b> {int(tasa*100)}% ({num_cuotas} meses x {int(TASA_INTERES_MENSUAL*100)}%)"
                f"<hr>"
                f"<table width='100%'>"
                f"<tr><td><b>Cuotas:</b></td><td align='right'>{plan['num_cuotas']}</td></tr>"
                f"<tr><td><b>Valor Cuota:</b></td><td align='right' style='font-size:14px; color:blue;'><b>{format_currency(plan['valor_cuota'])}</b></td></tr>"
                f"<tr><td><b>Total Final:</b></td><td align='right'>{format_currency(plan['precio_final'])}</td></tr>"
                f"</table>"
            )

            msg_box = QMessageBox(parent)
            msg_box.setWindowTitle(f"Financiación {num_cuotas} Cuotas")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(texto_html)
            
            btn_copiar = msg_box.addButton("Copiar Plan", QMessageBox.ActionRole)
            msg_box.addButton("Cerrar", QMessageBox.RejectRole)
            msg_box.setDefaultButton(btn_copiar)
            
            msg_box.exec()

            # 5. Copiar
            if msg_box.clickedButton() == btn_copiar:
                # Usamos MAPEO_CLIPBOARD global del archivo views.py
                texto_plano = generar_texto_clipboard(fila_data, plan, MAPEO_CLIPBOARD)
                QApplication.clipboard().setText(texto_plano)

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(parent, "Error de Cálculo", f"Error:\n{str(e)}")

def copiar_callback(info_fila):
    """
    Recibe la fila (diccionario), genera el texto y lo manda al portapapeles.
    """
    try:
        texto_final = formatear_producto_para_clipboard(info_fila)
        
        # Copiar al portapapeles
        clipboard = QApplication.clipboard()
        clipboard.setText(texto_final)
        
        # Feedback visual sutil (Opcional: un print o un toast sería mejor, 
        # pero un cambio de cursor o mensaje en consola basta para no interrumpir)
        print(f"Copiado al portapapeles:\n{texto_final}")
        
    except Exception as e:
        print(f"Error al copiar: {e}")

def build_tabla_productos(parent_window, df, campos, copiar_callback, ver_imagen_callback, cart_service: CartService):
    """Construye la tabla con botón de Carrito incluido."""
    contenedor = QWidget()
    layout_principal = QVBoxLayout(contenedor)
    contenedor.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    layout_principal.setContentsMargins(0, 0, 0, 0)
    layout_principal.setSpacing(0)

    # --- Header ---
    header_layout = QHBoxLayout()
    
    # Columna Ver Foto
    lbl_foto_header = QLabel("")
    lbl_foto_header.setFixedWidth(40) # Ancho pequeño
    lbl_foto_header.setStyleSheet(ESTILOS.get("titulo_columna", ""))
    lbl_foto_header.setFixedHeight(ESTILOS["altura_encabezado"])
    header_layout.addWidget(lbl_foto_header)
    # ---------------------------------

    # Columna Copiar (Vacia en header)
    lbl_copiar = QLabel("")
    lbl_copiar.setFixedWidth(CATALOGO_ANCHOS.get("COPIAR", 30))
    header_layout.addWidget(lbl_copiar)

    for campo in campos:
        label = QLabel(campo)

        # 1. Mantenemos el ancho fijo por columna
        label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))

        # 2. ACTIVAMOS EL WRAPPING (Multilínea)
        label.setWordWrap(True) 

        # 3. Alineación centrada (se ve mejor en títulos de dos líneas)
        label.setAlignment(Qt.AlignCenter)

        # 4. Estilos
        label.setStyleSheet(ESTILOS.get("titulo_columna", ""))

        # 5. Usamos 'setMinimumHeight'
        # Esto permite que la celda crezca si el texto necesita 2 o 3 renglones.
        label.setMinimumHeight(ESTILOS["altura_encabezado"]) 
        
        header_layout.addWidget(label)

    # Columna Ver Más (Vacia en header)
    lbl_acciones = QLabel("Acciones") # O dejalo vacío si prefieres
    lbl_acciones.setFixedWidth(80) # 40px para carrito + 40px para ver más
    lbl_acciones.setStyleSheet(ESTILOS.get("titulo_columna", ""))
    lbl_acciones.setFixedHeight(ESTILOS["altura_encabezado"])
    header_layout.addWidget(lbl_acciones)
    
    layout_principal.addLayout(header_layout)

    # --- Helper para agregar al carrito con feedback ---
    def _agregar_click(fila_series):
        # Convertimos la Serie de Pandas a Diccionario para el servicio
        producto_dict = fila_series.to_dict()
        cart_service.agregar_producto(producto_dict)
        
        # Feedback Visual Rápido (Opcional: puedes usar un Toast o StatusBar)
        print(f"[CARRITO] Agregado: {producto_dict.get('MODELO')}")

    # --- Filas ---
    for i, fila in df.iterrows():
        layout_fila = QHBoxLayout()
        estilo_fondo = ESTILOS['fila_par'] if i % 2 == 0 else ESTILOS['fila_impar']
        
        fila_widget = QWidget()
        fila_widget.setStyleSheet(f"background-color: {estilo_fondo};")
        
        # 1. AJUSTE DE SEPARACIÓN VERTICAL (Márgenes)
        # Antes: (0, 2, 0, 2). Ahora: (0, 8, 0, 8) para dar más aire entre filas.
        layout_fila.setContentsMargins(0, 8, 0, 8) 

        # 2. DEFINIR ALTURA MEJORADA
        # Sumamos 10px a la altura base definida en constantes para hacer la fila "más ancha/alta"
        altura_fila_mejorada = ESTILOS.get("altura_celda", 30) + 12

        row_dict = fila.to_dict() # Convertimos a dict para usar los detectores
        
        # --- A. NUEVO: BOTÓN VER FOTO (👁️) ---
        ruta_img = obtener_ruta_imagen(row_dict)
        btn_ver_foto = QPushButton("👁️") # Puedes usar icono cámara 📷 si prefieres
        #btn_ver_foto.setIcon(QIcon("ruta/a/icono_ojo.png")) # Opcional con QIcon
        
        # Definir estilo del botón (pequeño, sin bordes raros)
        btn_ver_foto.setFixedWidth(40)
        btn_ver_foto.setFixedHeight(altura_fila_mejorada)
        btn_ver_foto.setCursor(Qt.PointingHandCursor)
        
        # DETECCIÓN DE IMAGEN: Si no hay, deshabilitamos el botón
        ruta_img = obtener_ruta_imagen(row_dict)
        if not ruta_img:
            btn_ver_foto.setEnabled(False)
            btn_ver_foto.setToolTip("Producto sin imagen disponible")
            # Estilo deshabilitado sutil
            btn_ver_foto.setStyleSheet("color: #bdc3c7; background-color: transparent; border: none; font-size: 18px;")
        else:
            btn_ver_foto.setToolTip("Click para ver imagen grande")
            btn_ver_foto.setStyleSheet("color: #3498db; background-color: transparent; border: none; font-size: 18px; font-weight: bold;")
            # Conectamos al nuevo callback pasando los datos necesarios
            btn_ver_foto.clicked.connect(partial(ver_imagen_callback, row_dict, ruta_img))
        
        layout_fila.addWidget(btn_ver_foto)
        # --------------------------------------

        # --- BOTÓN COPIAR (MODIFICADO) ---
        btn_copiar = QPushButton("📋")
        btn_copiar.setStyleSheet(ESTILOS.get('boton_copiar', ''))
        btn_copiar.setFixedWidth(CATALOGO_ANCHOS.get("COPIAR", 30))
        btn_copiar.setFixedHeight(altura_fila_mejorada)
        
        # ERROR ANTERIOR: Le pasábamos 'info_fila' (formateada con $)
        # SOLUCIÓN: Le pasamos 'row_dict' (la data pura del DataFrame)
        btn_copiar.clicked.connect(partial(copiar_callback, row_dict)) 
        
        layout_fila.addWidget(btn_copiar)
        
        # --- Celdas de Datos ---
        for campo in campos:
            valor_raw = fila.get(campo, "")
            texto_celda = str(valor_raw)
            estilo_celda = ESTILOS.get("celda_texto", "")

            if isinstance(valor_raw, (int, float)):
                texto_celda = format_currency(valor_raw)
                estilo_celda = ESTILOS.get("celda_numero", "")
            
            label = QLabel(texto_celda)
            label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))
            label.setStyleSheet(estilo_celda)
            
            # Ajuste de texto para las celdas también (importante si crecen)
            label.setWordWrap(True) 
            
            # Usamos setMinimumHeight para que nunca sean más chicas que nuestra altura mejorada
            label.setMinimumHeight(altura_fila_mejorada)
            
            # Alineación vertical centrada es clave ahora que son más altas
            label.setAlignment(Qt.AlignVCenter | (Qt.AlignRight if isinstance(valor_raw, (int, float)) else Qt.AlignLeft))
            
            layout_fila.addWidget(label)

        # --- SECCIÓN DE ACCIONES ---
        
        # Contenedor para agrupar botones a la derecha
        acciones_container = QWidget()
        acciones_layout = QHBoxLayout(acciones_container)
        acciones_layout.setContentsMargins(0, 0, 0, 0)
        acciones_layout.setSpacing(2) # Pegaditos

        # 1. BOTÓN AGREGAR AL CARRITO (NUEVO)
        btn_cart = QPushButton("🛒")
        btn_cart.setToolTip("Agregar al Carrito")
        btn_cart.setFixedWidth(35)
        # Reutilizamos estilo de "ver_mas" o creamos uno nuevo
        btn_cart.setStyleSheet(ESTILOS.get("boton_ver_mas", "background-color: #DDD;"))
        btn_cart.setFixedHeight(altura_fila_mejorada) # Usar la variable de altura que definimos antes
        
        # Conexión
        btn_cart.clicked.connect(partial(_agregar_click, fila))
        acciones_layout.addWidget(btn_cart)

        # 2. BOTÓN VER MÁS (EXISTENTE)
        btn_mas = QPushButton("⋯")
        btn_mas.setToolTip("Calcular Cuotas")
        btn_mas.setFixedWidth(35)
        btn_mas.setStyleSheet(ESTILOS.get("boton_ver_mas", ""))
        btn_mas.setFixedHeight(altura_fila_mejorada)
        
        btn_mas.clicked.connect(partial(_handle_calculo_cuotas, parent_window, fila.to_dict()))
        acciones_layout.addWidget(btn_mas)

        # Añadimos el contenedor de acciones al layout de la fila
        acciones_container.setFixedWidth(80) # Asegurar ancho fijo total
        layout_fila.addWidget(acciones_container)

        fila_widget.setLayout(layout_fila)
        layout_principal.addWidget(fila_widget)

    layout_principal.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(contenedor)
    scroll.setFrameShape(QFrame.NoFrame)
    return scroll

# --- Funciones Router (Sin cambios mayores, solo limpieza) ---

def build_categoria_view(parent_window: QWidget, key: str, sheets: dict, volver_callback: Callable, cart_service: CartService, tipo_producto: str = "colchones") -> QWidget:

    vista = QWidget()
    layout = QVBoxLayout(vista)
    
    # Obtener datos
    try:
        df = catalogo_service.obtener_df_por_hoja(sheets, key)
    except Exception as e:
        layout.addWidget(QLabel(f"Error cargando datos: {e}"))
        return vista

    campos = [c for c in CAMPOS_CATALOGO.get(tipo_producto, []) if c != "COSTO"]
    campos_visibles = [c for c in campos if c in df.columns]
    
    # 1. Definimos la nueva función de lógica (Handler)
    def mostrar_imagen_handler(row_dict, ruta_img_path):
        """
        Callback que se ejecuta al presionar el ojo 👁️.
        Abre el Dialog modal con la imagen grande.
        """
        try:
            modelo = row_dict.get('MODELO', 'Producto')
            # Instanciamos el visualizador pasando el parent_window (para que se centre)
            viewer = ImageViewerDialog(parent_window, modelo, ruta_img_path)
            # Abrimos de forma modal bloqueante
            viewer.exec() 
        except Exception as e:
            QMessageBox.warning(parent_window, "Error", f"No se pudo abrir la imagen:\n{e}")
            print(f"❌ Error al abrir visualizador: {e}")

    def copiar_universal_wrapper(fila_datos_series):
        """
        Decide dinámicamente si copiar un Flyer (si hay foto) 
        o Texto Formateado (si no hay foto).
        """
        try:
            # Poner cursor de carga por si la generación del flyer toma un instante
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            row_dict = fila_datos_series.to_dict() if hasattr(fila_datos_series, 'to_dict') else fila_datos_series
            clipboard = QApplication.clipboard()
            
            # 1. Detectamos si existe la foto
            ruta_img = obtener_ruta_imagen(row_dict)
            
            if ruta_img:
                # --- MODO FLYER ---
                # Modificamos generar_flyer_producto para que reciba la ruta_img directamente
                # y no tenga que buscarla de nuevo.
                img_bytes_io = generar_flyer_producto(row_dict, ruta_img) 
                
                q_image = QImage.fromData(img_bytes_io.getvalue())
                if not q_image.isNull():
                    clipboard.setImage(q_image)
                    print(f"✅ Flyer copiado: {row_dict.get('MODELO')}")
                else:
                    raise Exception("Fallo al convertir la imagen para el portapapeles.")
            else:
                # --- MODO TEXTO (Fallback) ---
                texto = formatear_producto_para_clipboard(row_dict)
                clipboard.setText(texto)
                print(f"✅ Texto copiado: {row_dict.get('MODELO')}")

        except Exception as e:
            QMessageBox.warning(parent_window, "Error de Copiado", f"No se pudo copiar el producto:\n{e}")
            print(f"❌ Error crítico en copiado: {e}")
        finally:
            # Asegurar que el cursor vuelva a la normalidad incluso si hay error
            QApplication.restoreOverrideCursor()

    # Asignamos esta función universal como el callback
    copiar_callback = copiar_universal_wrapper
    ver_imagen_callback = mostrar_imagen_handler

    tabla = build_tabla_productos(parent_window, df, campos_visibles, copiar_callback, ver_imagen_callback, cart_service)
    layout.addWidget(tabla)

    btn_volver = QPushButton("Volver al Menú")
    btn_volver.setStyleSheet(ESTILOS.get('boton_volver', ''))
    btn_volver.clicked.connect(volver_callback)
    layout.addWidget(btn_volver)

    return vista

def build_menu_view(opciones: dict, on_click: Callable, estilo_boton: str, volver_callback: Callable = None) -> QWidget:
    menu = QWidget()
    layout = QVBoxLayout(menu)

    for key, config in opciones.items():
        btn = QPushButton(config.get("nombre", key))
        btn.setStyleSheet(estilo_boton)
        btn.clicked.connect(partial(on_click, key))
        layout.addWidget(btn)

    if volver_callback:
        btn_volver = QPushButton("Volver")
        btn_volver.setStyleSheet(ESTILOS.get('boton_volver', ''))
        btn_volver.clicked.connect(volver_callback)
        layout.addWidget(btn_volver)

    return menu

def build_busqueda_view(parent_window: QWidget, on_buscar: Callable, volver_callback: Callable, 
                        cart_service: CartService) -> QWidget:
    vista = QWidget()
    layout = QVBoxLayout(vista)

    input_busqueda = QLineEdit()
    input_busqueda.setPlaceholderText("Ingrese el MODELO del producto...")
    layout.addWidget(input_busqueda)

    btn_buscar = QPushButton("Buscar")
    btn_buscar.setStyleSheet(ESTILOS.get("boton_volver", ""))
    layout.addWidget(btn_buscar)

    resultados_layout = QVBoxLayout()
    resultados_container = QWidget()
    resultados_container.setLayout(resultados_layout)
    layout.addWidget(resultados_container)

    def ejecutar_busqueda():
        termino = input_busqueda.text().strip()
        if not termino: return
        
        # Limpiar resultados previos
        for i in reversed(range(resultados_layout.count())): 
            resultados_layout.itemAt(i).widget().setParent(None)

        df = on_buscar(termino)
        if df.empty:
            resultados_layout.addWidget(QLabel("No se encontraron resultados."))
            return

        # Lógica de columnas visibles
        all_cols = []
        for tipo in ["colchones", "otros"]:
            all_cols.extend(CAMPOS_CATALOGO.get(tipo, []))

        seen = set()
        master_list = [x for x in all_cols if not (x in seen or seen.add(x))]
        campos_visibles = [c for c in master_list if c in df.columns]

        # --- HANDLER 1: COPIADO INTELIGENTE ---
        def copiar_desde_busqueda(fila_datos):
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                row_dict = fila_datos.to_dict() if hasattr(fila_datos, 'to_dict') else fila_datos
                clipboard = QApplication.clipboard()
                
                ruta_img = obtener_ruta_imagen(row_dict)
                
                if ruta_img:
                    img_bytes_io = generar_flyer_producto(row_dict, ruta_img) 
                    q_image = QImage.fromData(img_bytes_io.getvalue())
                    if not q_image.isNull():
                        clipboard.setImage(q_image)
                        print(f"✅ Flyer copiado desde búsqueda: {row_dict.get('MODELO')}")
                else:
                    texto = formatear_producto_para_clipboard(row_dict)
                    clipboard.setText(texto)
                    print(f"✅ Texto copiado desde búsqueda: {row_dict.get('MODELO')}")

            except Exception as e:
                QMessageBox.warning(parent_window, "Error al copiar", f"{e}")
            finally:
                QApplication.restoreOverrideCursor()

        # --- HANDLER 2: VISOR DE IMÁGENES (👁️) ---
        def mostrar_imagen_handler_busqueda(row_dict, ruta_img_path):
            try:
                modelo = row_dict.get('MODELO', 'Producto')
                viewer = ImageViewerDialog(parent_window, modelo, ruta_img_path)
                viewer.exec() 
            except Exception as e:
                QMessageBox.warning(parent_window, "Error", f"No se pudo abrir la imagen:\n{e}")

        # Construimos la tabla del buscador
        tabla = build_tabla_productos(
            parent_window, 
            df, 
            campos_visibles, 
            copiar_desde_busqueda,           # 4to argumento
            mostrar_imagen_handler_busqueda, # 5to argumento
            cart_service                     # 6to argumento
        )
        
        resultados_layout.addWidget(tabla)

    btn_buscar.clicked.connect(ejecutar_busqueda)
    input_busqueda.returnPressed.connect(ejecutar_busqueda)

    btn_volver = QPushButton("Volver al Menú")
    btn_volver.setStyleSheet(ESTILOS.get('boton_volver', ''))
    btn_volver.clicked.connect(volver_callback)
    layout.addWidget(btn_volver)

    return vista
