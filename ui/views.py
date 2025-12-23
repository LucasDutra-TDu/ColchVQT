# ui/views.py

from typing import Callable, Dict, Any, List
from functools import partial
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, 
    QFrame, QSizePolicy, QLineEdit, QMessageBox, QInputDialog, QApplication
)
from PySide6.QtCore import Qt

# Imports Propios
from logic.constants import ESTILOS, CAMPOS_CATALOGO, CATALOGO_ANCHOS
from logic import catalogo_service
# Importamos la nueva lógica financiera
from logic.financiero import calcular_plan_cuotas, format_currency, generar_texto_clipboard
from logic.cart_service import CartService

# Definición del Mapeo para el Portapapeles (Constante)
MAPEO_CLIPBOARD = [
    ("PROVEEDOR", "Marca"),
    ("MODELO", "Modelo"),
    ("MEDIDA (LARG-ANCH-ESP)", "Medida"),
    ("MATERIAL", "Material"),
    ("SOPORTA (PORPLAZA)", "PesoSoportado"),
    ("CARACTERISTICAS", "Detalle")
]

def _handle_calculo_cuotas(parent: QWidget, fila_data: dict):
    """Manejador del evento de cálculo de cuotas (Controller Logic)."""
    
    # 1. Validación
    precio_base_val = fila_data.get("EFECTIVO/TRANSF")
    if not precio_base_val or pd.isna(precio_base_val):
        QMessageBox.warning(parent, "Error", "Sin precio base válido.")
        return

    try:
        precio_base = float(precio_base_val)
    except (ValueError, TypeError):
        QMessageBox.warning(parent, "Error", "Formato de precio inválido.")
        return

    # 2. Interacción Usuario
    cuotas_str, ok = QInputDialog.getItem(
        parent, "Calcular Cuotas", "Seleccione cuotas:",
        [str(i) for i in range(3, 13)], 0, False
    )

    if ok and cuotas_str:
        # 3. Delegación a Lógica Pura
        plan = calcular_plan_cuotas(precio_base, int(cuotas_str))

        # 4. Construcción de UI del Popup
        texto_html = (
            f"<b>Precio Lista:</b> {format_currency(plan['precio_base'])}<hr>"
            f"<b>Plan:</b> {plan['num_cuotas']} cuotas<br>"
            f"<b>Precio Final:</b> {format_currency(plan['precio_final'])}<hr>"
            f"<h3>Valor Cuota: {format_currency(plan['valor_cuota'])}</h3>"
        )

        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("Detalle de Financiación")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(texto_html)
        
        btn_copiar = msg_box.addButton("Copiar Plan", QMessageBox.ActionRole)
        msg_box.addButton("Cerrar", QMessageBox.RejectRole)
        msg_box.setDefaultButton(btn_copiar)
        msg_box.exec()

        if msg_box.clickedButton() == btn_copiar:
            texto_plano = generar_texto_clipboard(fila_data, plan, MAPEO_CLIPBOARD)
            QApplication.clipboard().setText(texto_plano)

def build_tabla_productos(parent_window, df, campos, copiar_callback, cart_service: CartService):
    """Construye la tabla con botón de Carrito incluido."""
    contenedor = QWidget()
    layout_principal = QVBoxLayout(contenedor)
    contenedor.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    layout_principal.setContentsMargins(0, 0, 0, 0)
    layout_principal.setSpacing(0)

    # --- Header ---
    header_layout = QHBoxLayout()
    
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

        # --- Botón Copiar ---
        btn_copiar = QPushButton("📋")
        btn_copiar.setStyleSheet(ESTILOS.get('boton_copiar', ''))
        btn_copiar.setFixedWidth(CATALOGO_ANCHOS.get("COPIAR", 30))
        # Usamos la nueva altura
        btn_copiar.setFixedHeight(altura_fila_mejorada)
        
        info_fila = {c: f"${v:,.0f}".replace(",", ".") if isinstance(v, (int, float)) else str(v) 
                     for c, v in fila.items()}
        btn_copiar.clicked.connect(partial(copiar_callback, info_fila))
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
    
    # Callback dinámico
    func_copiar_nombre = f"copiar_info_{tipo_producto}"
    copiar_callback = getattr(catalogo_service, func_copiar_nombre, None)
    
    if not copiar_callback:
        copiar_callback = lambda x: print("Función de copiado no encontrada")

    tabla = build_tabla_productos(parent_window, df, campos_visibles, copiar_callback, cart_service)
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

        # Lógica de columnas visibles (Mejorada)
        all_cols = []
        for tipo in ["colchones", "otros"]:
            all_cols.extend(CAMPOS_CATALOGO.get(tipo, []))
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        master_list = [x for x in all_cols if not (x in seen or seen.add(x))]
        
        campos_visibles = [c for c in master_list if c in df.columns]

        tabla = build_tabla_productos(parent_window, df, campos_visibles, catalogo_service.copiar_info_busqueda, cart_service)
        resultados_layout.addWidget(tabla)

    btn_buscar.clicked.connect(ejecutar_busqueda)
    # Trigger con Enter
    input_busqueda.returnPressed.connect(ejecutar_busqueda)

    btn_volver = QPushButton("Volver al Menú")
    btn_volver.setStyleSheet(ESTILOS.get('boton_volver', ''))
    btn_volver.clicked.connect(volver_callback)
    layout.addWidget(btn_volver)

    return vista