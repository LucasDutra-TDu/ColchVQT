import math # <--- CAMBIO 1: Importar math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, 
    QFrame, QSizePolicy, QLineEdit, QMessageBox, QInputDialog, QApplication
)
from PySide6.QtCore import Qt
from logic.constants import ESTILOS, MENU_CONFIG, CAMPOS_CATALOGO, CATALOGO_ANCHOS
from logic import catalogo_utils_v2
from logic.catalogo_utils_v2 import obtener_df_por_hoja
from typing import Callable
from functools import partial
import re
import pandas as pd

def build_tabla_productos(parent_window, df, campos, copiar_callback):
    """
    Construye el widget de la tabla de productos.

    Args:
        parent_window (QWidget): La ventana principal (usualmente 'self')
                                 que actuará como padre de los diálogos.
        df (pd.DataFrame): El DataFrame con los datos.
        campos (list): Lista de columnas a mostrar.
        copiar_callback (function): Función a llamar al presionar "copiar".
    """
    contenedor = QWidget()
    layout_principal = QVBoxLayout(contenedor)
    # Ajuste de Póliza de Tamaño
    contenedor.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    layout_principal.setContentsMargins(0, 0, 0, 0) # Añadido para compactar
    layout_principal.setSpacing(0) # Añadido para compactar


    # Encabezados de columna
    header_layout = QHBoxLayout()
    copiar_header = QLabel("")
    copiar_header.setFixedWidth(CATALOGO_ANCHOS["COPIAR"])
    copiar_header.setFixedHeight(ESTILOS["altura_encabezado"])
    header_layout.addWidget(copiar_header)
    
    for campo in campos:
        label = QLabel(campo)
        label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))
        label.setStyleSheet(ESTILOS.get("titulo_columna", ""))
        label.setWordWrap(True)
        label.setFixedHeight(ESTILOS["altura_encabezado"])
        header_layout.addWidget(label)
        
    # Espacio para botón "..."
    btn_mas_header = QLabel("")
    btn_mas_header.setStyleSheet("border: none;") 
    # Asegúrate de tener un ancho fijo para alinear
    # Asumo que tienes un ancho en ESTILOS o CATALOGO_ANCHOS
    btn_mas_width = CATALOGO_ANCHOS.get("VER_MAS", 40) 
    btn_mas_header.setFixedWidth(btn_mas_width)
    header_layout.addWidget(btn_mas_header)

    layout_principal.addLayout(header_layout)


    # --- INICIO DE LA FUNCIÓN INTERNA (MODIFICADA CON BOTÓN COPIAR) ---
    def crear_funcion_detalle(parent_widget, fila_dict_local):
        """
        Calcula cuotas, muestra resultado y permite copiar al portapapeles.
        """
        
        def mostrar_calculo_cuotas():
            # --- 1. Obtener y validar el precio base ---
            precio_base_valor = fila_dict_local.get("EFECTIVO/TRANSF")

            if not precio_base_valor or pd.isna(precio_base_valor):
                QMessageBox.warning(parent_widget, "Error", "Sin precio base válido.")
                return

            try:
                precio_base = float(precio_base_valor)
            except (ValueError, TypeError):
                QMessageBox.warning(parent_widget, "Error", "Formato de precio inválido.")
                return

            # --- 2. Pedir cuotas ---
            cuotas_opciones = [str(i) for i in range(3, 13)]
            
            num_cuota_str, ok = QInputDialog.getItem(
                parent_widget, "Calcular Cuotas", "Seleccione cuotas:",
                cuotas_opciones, 0, False
            )

            if ok and num_cuota_str:
                num_cuotas = int(num_cuota_str)

                # --- 3. Lógica de Cálculo ---
                RECARGO_SIMPLE_POR_CUOTA = 0.08 
                tasa_interes_total = RECARGO_SIMPLE_POR_CUOTA * num_cuotas
                precio_total_financiado = precio_base * (1 + tasa_interes_total)
                                
                valor_cuota_raw = precio_total_financiado / num_cuotas
                
                # Redondeo a 100
                valor_cuota = math.ceil(valor_cuota_raw / 100) * 100

                precio_final = valor_cuota * num_cuotas

                
                # --- 4. Preparar Textos ---
                
                def format_currency(valor):
                    return f"${valor:,.0f}".replace(",", ".")

                # A) Texto Visual (HTML para el Popup)
                texto_visual = f"""
                    <b>Precio Lista:</b> {format_currency(precio_base)}
                    <hr>
                    <b>Plan:</b> {num_cuotas} cuotas
                    <b>Precio Final:</b> {format_currency(precio_final)}
                    <hr>
                    <h3>Valor Cuota: {format_currency(valor_cuota)}</h3>
                """

                # --- B) Texto para Copiar (ESTRICTO FORMATO LISTA) ---
                
                lineas_copiar = []

                # 1. Definimos el mapeo: (Columna_Excel_Mayusculas, Etiqueta_Salida)
                #    Esto asegura el orden exacto que quieres: Marca -> Modelo -> Medida -> Material -> Peso
                mapeo_campos = [
                    ("PROVEEDOR", "Marca"),
                    ("MODELO", "Modelo"),
                    ("MEDIDA (LARG-ANCH-ESP)", "Medida"),
                    ("MATERIAL", "Material"),
                    ("SOPORTA (PORPLAZA)", "PesoSoportado"),
                    ("CARACTERISTICAS", "Detalle")        # Para productos 'Otros'
                ]

                etiquetas_usadas = set() # Para evitar duplicados si hay columnas similares

                for col_excel, etiqueta in mapeo_campos:
                    # Si ya pusimos esta etiqueta (ej. ya pusimos Medida), saltamos
                    if etiqueta in etiquetas_usadas:
                        continue

                    # Buscamos el valor en el diccionario (que tiene claves en mayúsculas)
                    val = fila_dict_local.get(col_excel)

                    # Si existe valor y no es nulo/vacío
                    if val and pd.notna(val) and str(val).strip() != "":
                        # APLICAMOS FORMATO: Etiqueta: 'Valor'
                        lineas_copiar.append(f"{etiqueta}: '{val}'")
                        etiquetas_usadas.add(etiqueta)

                # 2. Agregamos la información del PLAN (Reemplazando Efectivo/Debito)
                #    Mantenemos el estilo visual limpio
                lineas_copiar.append(f"PLAN CRÉDITO DE LA CASA ({num_cuotas} PAGOS): {format_currency(precio_final)}")
                lineas_copiar.append(f"VALOR DE CUOTA: {format_currency(valor_cuota)}")

                # Unimos todo
                texto_copiar = "\n".join(lineas_copiar)

                # --- 5. Configurar el Popup con Botones (IGUAL QUE ANTES) ---
                msg_box = QMessageBox(parent_widget)
                
                # Icono y Título
                icon_str = ESTILOS["popup_detalle"].get("icono", "information")
                icon = {
                    "information": QMessageBox.Information,
                    # ... otros iconos ...
                }.get(icon_str, QMessageBox.Information)
                msg_box.setIcon(icon)
                msg_box.setWindowTitle(ESTILOS["popup_detalle"]["titulo"])
                msg_box.setTextFormat(Qt.RichText)
                msg_box.setText(texto_visual)

                # AÑADIMOS LOS BOTONES
                # Botón personalizado para copiar
                btn_copiar = msg_box.addButton("Copiar Plan", QMessageBox.ActionRole)
                # Botón estándar para cerrar
                btn_cerrar = msg_box.addButton("Cerrar", QMessageBox.RejectRole)
                
                msg_box.setDefaultButton(btn_copiar) # Enter activa copiar

                # Ejecutamos la caja
                msg_box.exec()

                # --- 6. Lógica Post-Clic ---
                if msg_box.clickedButton() == btn_copiar:
                    # Copiamos al portapapeles del sistema
                    clipboard = QApplication.clipboard()
                    clipboard.setText(texto_copiar)
                    
                    # Opcional: Feedback rápido (pequeño popup o nada)
                    # Como el msg_box se cierra al clicar, esto es suficiente.

        return mostrar_calculo_cuotas
    # --- FIN DE LA FUNCIÓN INTERNA ---

    # --- Bucle de filas (Sin cambios) ---
    for i, fila in df.iterrows():
        layout_fila = QHBoxLayout()
        estilo_fondo = ESTILOS['fila_par'] if i % 2 == 0 else ESTILOS['fila_impar']

        fila_widget = QWidget()
        fila_widget.setStyleSheet(f"background-color: {estilo_fondo};")
        fila_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

        info_fila = {} # Este diccionario es para el botón "copiar"

        # Botón de copiado de fila
        boton = QPushButton("📋")
        boton.setStyleSheet(ESTILOS['boton_copiar'])
        boton.setMaximumWidth(CATALOGO_ANCHOS["COPIAR"])
        boton.setMinimumWidth(CATALOGO_ANCHOS["COPIAR"])
        boton.setFixedHeight(ESTILOS["altura_celda"])
        boton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        layout_fila.addWidget(boton)

        for campo in campos:
            valor_raw = fila.get(campo, "") # Valor original
            valor_display = valor_raw # Valor para mostrar
            
            es_numerico = False
            if isinstance(valor_raw, (int, float)):
                es_numerico = True
                valor_display = f"${valor_raw:,.0f}".replace(",", ".")
            else:
                valor_display = str(valor_raw)

            label = QLabel(valor_display)
            label.setFixedWidth(CATALOGO_ANCHOS.get(campo, 100))
            label.setStyleSheet((ESTILOS.get("celda_numero") if es_numerico else ESTILOS.get("celda_texto")) or "")
            label.setFixedHeight(ESTILOS["altura_celda"])
            layout_fila.addWidget(label)
            
            # Guardamos el valor formateado para copiar
            info_fila[campo] = valor_display 

        # Conectar el botón de copiar (después de llenar info_fila)
        boton.clicked.connect(partial(copiar_callback, info_fila))


        # Botón para mostrar cálculo de cuotas
        btn_mas = QPushButton("⋯")
        btn_mas.setStyleSheet(ESTILOS.get("boton_ver_mas", ""))
        btn_mas.setFixedHeight(ESTILOS["altura_celda"])
        btn_mas.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        # Le damos el ancho fijo que definimos en el header
        btn_mas.setFixedWidth(btn_mas_width) 
        
        # 1. Pasamos 'parent_window' (el 'self' de tu app)
        # 2. Pasamos 'fila.to_dict()' (los datos *originales*, sin formatear)
        funcion_calculo = crear_funcion_detalle(parent_window, fila.to_dict())
        btn_mas.clicked.connect(funcion_calculo)
        
        layout_fila.addWidget(btn_mas)

        fila_widget.setLayout(layout_fila)
        layout_principal.addWidget(fila_widget)
    
    # Añadir un espaciador al final
    layout_principal.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(contenedor)
    scroll.setFrameShape(QFrame.NoFrame)

    return scroll


def build_categoria_view(parent_window: QWidget, key: str, sheets: dict, volver_callback: Callable, tipo_producto: str = "colchones") -> QWidget:
    vista = QWidget()
    layout = QVBoxLayout(vista)

    campos = [c for c in CAMPOS_CATALOGO[tipo_producto] if c != "COSTO"]
    copiar_callback = getattr(catalogo_utils_v2, f"copiar_info_{tipo_producto}")

    df = obtener_df_por_hoja(sheets, key)
    campos_visibles = [c for c in campos if c in df.columns]

    tabla = build_tabla_productos(parent_window, df, campos_visibles, copiar_callback)
    layout.addWidget(tabla)

    boton_volver = QPushButton("Volver al Menú")
    boton_volver.setStyleSheet(ESTILOS['boton_volver'])
    boton_volver.clicked.connect(volver_callback)
    layout.addWidget(boton_volver)

    return vista


def build_menu_view(opciones: dict, on_click: Callable[[str], None], estilo_boton: str, volver_callback: Callable = None) -> QWidget:
    menu = QWidget()
    layout = QVBoxLayout(menu)

    for key, config in opciones.items():
        nombre = config.get("nombre", key)
        boton = QPushButton(nombre)
        boton.setStyleSheet(estilo_boton)
        boton.clicked.connect(lambda _, k=key: on_click(k))
        layout.addWidget(boton)

    if volver_callback:
        boton_volver = QPushButton("Volver")
        boton_volver.setStyleSheet(ESTILOS['boton_volver'])
        boton_volver.clicked.connect(volver_callback)
        layout.addWidget(boton_volver)

    return menu


def build_busqueda_view(parent_window: QWidget, on_buscar: Callable[[str], pd.DataFrame], volver_callback: Callable) -> QWidget:
    vista = QWidget()
    layout = QVBoxLayout(vista)

    input_busqueda = QLineEdit()
    # ¡Cambié el placeholder de "nombre" a "modelo" para ser consistentes!
    input_busqueda.setPlaceholderText("Ingrese el MODELO del producto...") 
    layout.addWidget(input_busqueda)

    boton_buscar = QPushButton("Buscar")
    boton_buscar.setStyleSheet(ESTILOS["boton_volver"])
    layout.addWidget(boton_buscar)

    resultados_contenedor = QWidget()
    resultados_layout = QVBoxLayout(resultados_contenedor)
    layout.addWidget(resultados_contenedor)

    def ejecutar_busqueda():
        termino_busqueda = input_busqueda.text().strip()
        if termino_busqueda:
            df = on_buscar(termino_busqueda)
            
            # Limpiar resultados anteriores
            for i in reversed(range(resultados_layout.count())):
                widget = resultados_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
            
            if not df.empty:
                
                # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
                
                # 1. Creamos una "lista maestra" de todas las columnas posibles
                #    usando un dict para eliminar duplicados pero mantener el orden.
                columnas_deseadas = {}
                
                # Añadimos CÓDIGO (si lo usas, si no, puedes borrar estas líneas)
                columnas_deseadas["CÓDIGO"] = True
                columnas_deseadas["CODIGO"] = True
                
                # Añadimos todas las columnas de 'colchones' en orden
                for col in CAMPOS_CATALOGO.get("colchones", []):
                    columnas_deseadas[col] = True
                
                # Añadimos las columnas de 'otros' que no estén ya
                for col in CAMPOS_CATALOGO.get("otros", []):
                    columnas_deseadas[col] = True

                # Convertimos el dict (que mantiene el orden) a una lista
                master_list = list(columnas_deseadas.keys())

                # 2. Esta es la lógica CORRECTA:
                #    Iteramos nuestra lista maestra y nos quedamos solo
                #    con las columnas que existen en el DataFrame del resultado.
                campos_visibles = [col for col in master_list if col in df.columns]
                
                # --- FIN DE LA CORRECCIÓN ---

                # 3. Construimos la tabla con los campos visibles y ordenados
                tabla = build_tabla_productos(parent_window, df, campos_visibles, catalogo_utils_v2.copiar_info_busqueda)
                resultados_layout.addWidget(tabla)

    boton_buscar.clicked.connect(ejecutar_busqueda)

    boton_volver = QPushButton("Volver al Menú")
    boton_volver.setStyleSheet(ESTILOS['boton_volver'])
    boton_volver.clicked.connect(volver_callback)
    layout.addWidget(boton_volver)

    return vista