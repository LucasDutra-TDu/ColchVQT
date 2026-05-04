from PySide6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QComboBox, QSpinBox, QLabel, QDialog, QVBoxLayout, QPushButton, QApplication, QMessageBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QInputDialog, QComboBox
from PySide6.QtCore import QDate, Signal, Qt
import os
from PySide6.QtGui import QPixmap, QIcon, QImage
from pathlib import Path
import pandas as pd
# Importamos el actualizador de la DB
from logic.stock_db_handler import registrar_movimiento_stock

class MonthYearSelector(QWidget):
    # Señal para avisar a la ventana padre que cambió la fecha
    dateChanged = Signal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Selector de Mes
        self.combo_mes = QComboBox()
        self.meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        self.combo_mes.addItems(self.meses)
        
        # Selector de Año
        self.spin_anio = QSpinBox()
        self.spin_anio.setRange(2020, 2040)
        
        # Setear fecha actual por defecto
        hoy = QDate.currentDate()
        self.combo_mes.setCurrentIndex(hoy.month() - 1)
        self.spin_anio.setValue(hoy.year())
        
        # Conectar señales
        self.combo_mes.currentIndexChanged.connect(lambda: self.dateChanged.emit())
        self.spin_anio.valueChanged.connect(lambda: self.dateChanged.emit())
        
        layout.addWidget(self.combo_mes)
        layout.addWidget(self.spin_anio)

    def get_date(self):
        """Devuelve (mes, anio) como enteros."""
        return self.combo_mes.currentIndex() + 1, self.spin_anio.value()
    
class SuccessDialog(QDialog):
    def __init__(self, titulo, mensaje, ruta_archivo=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(450, 200)
        self.ruta_archivo = ruta_archivo
        
        layout = QVBoxLayout(self)
        
        # Icono y Mensaje
        lbl_msg = QLabel(mensaje)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl_msg)
        
        if ruta_archivo:
            # Caja con la ruta para que se vea bien
            lbl_path = QLabel(ruta_archivo)
            lbl_path.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; font-family: Consolas;")
            lbl_path.setWordWrap(True)
            lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse) # Permitir seleccionar texto
            layout.addWidget(lbl_path)

        # Botones
        btn_layout = QHBoxLayout()
        
        if ruta_archivo:
            btn_copy = QPushButton("📋 Copiar Ruta")
            btn_copy.clicked.connect(self.copiar_ruta)
            btn_layout.addWidget(btn_copy)
            
            btn_open = QPushButton("📂 Abrir Carpeta")
            btn_open.clicked.connect(self.abrir_carpeta)
            btn_layout.addWidget(btn_open)

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def copiar_ruta(self):
        if self.ruta_archivo:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.ruta_archivo)
            QMessageBox.information(self, "Copiado", "Ruta copiada al portapapeles.")

    def abrir_carpeta(self):
        if self.ruta_archivo:
            try:
                folder = os.path.dirname(self.ruta_archivo)
                os.startfile(folder)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo abrir la carpeta: {e}")

class ImageViewerDialog(QDialog):
    # Agregamos row_dict a la firma del __init__
    def __init__(self, parent, titulo_producto: str, ruta_imagen: Path, row_dict: dict):
        super().__init__(parent)
        self.row_dict = row_dict # Guardamos los datos del producto
        self.setWindowTitle(f"Ver Imagen - {titulo_producto}")
        self.setWindowModality(Qt.WindowModal) 
        self.setStyleSheet("background-color: #1e1e1e;") 
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. EL CONTENEDOR DE IMAGEN
        self.lbl_imagen = QLabel()
        self.lbl_imagen.setAlignment(Qt.AlignCenter)
        self.lbl_imagen.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        self.lbl_imagen.setMinimumSize(1, 1) 
        layout.addWidget(self.lbl_imagen)

        self.ruta_imagen = str(ruta_imagen)
        self.original_pixmap = QPixmap(self.ruta_imagen)
        
        # ---------------------------------------------------------
        # 2. NUEVA ZONA DE BOTONES (Copiar Flyer + Cerrar)
        # ---------------------------------------------------------
        
        # Botón Copiar Flyer (Verde/Llamativo)
        self.btn_copiar_flyer = QPushButton("📸 Copiar Flyer Publicitario")
        self.btn_copiar_flyer.setFixedWidth(280)
        self.btn_copiar_flyer.setFixedHeight(45)
        self.btn_copiar_flyer.setCursor(Qt.PointingHandCursor)
        self.btn_copiar_flyer.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold; font-size: 15px;
                border-radius: 10px; margin-bottom: 20px; border: 2px solid #2ecc71;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_copiar_flyer.clicked.connect(self.generar_y_copiar_flyer)

        # Botón de Cerrar (Rojo)
        btn_cerrar = QPushButton("Cerrar Imagen (Esc)")
        btn_cerrar.setFixedWidth(200)
        btn_cerrar.setFixedHeight(45)
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; font-weight: bold; font-size: 15px;
                border-radius: 10px; margin-bottom: 20px; border: 2px solid #c0392b;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_cerrar.clicked.connect(self.close)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.btn_copiar_flyer)
        button_layout.addSpacing(20) # Espacio entre los botones
        button_layout.addWidget(btn_cerrar)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 3. MAXIMIZAR Y CARGAR CON RETRASO
        self.showMaximized()
                
        # El truco maestro: Esperamos 100ms a que Windows termine de estirar la ventana
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.actualizar_imagen_escalada)

    def keyPressEvent(self, event):
        # Si presionan Esc, cerramos (por si el FramelessWindowHint quita el comportamiento por defecto)
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Usamos un timer singleShot para no saturar el procesador mientras arrastras, 
        # pero que siempre actualice al tamaño final.
        self.actualizar_imagen_escalada()

    def actualizar_imagen_escalada(self):
        # Forzamos a procesar eventos para que width() y height() sean reales
        QApplication.processEvents()
        
        ancho = self.lbl_imagen.width()
        alto = self.lbl_imagen.height()

        if ancho <= 10 or alto <= 10:
            return
        
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            # Escalado suave a pantalla completa
            scaled_pixmap = self.original_pixmap.scaled(
                ancho,
                alto,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.lbl_imagen.setPixmap(scaled_pixmap)

    def generar_y_copiar_flyer(self):
        """Genera el flyer on-demand y lo manda al portapapeles."""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Cambiamos temporalmente el texto para dar feedback al vendedor
            self.btn_copiar_flyer.setText("⏳ Generando Flyer...")
            self.btn_copiar_flyer.repaint() # Forzamos a que se dibuje el cambio de texto
            
            # Importación diferida para evitar referencias circulares
            from logic.image_service import generar_flyer_producto 
            
            img_bytes_io = generar_flyer_producto(self.row_dict, self.ruta_imagen) 
            q_image = QImage.fromData(img_bytes_io.getvalue())
            
            if not q_image.isNull():
                QApplication.clipboard().setImage(q_image)
                self.btn_copiar_flyer.setText("✅ ¡Flyer Copiado!")
                self.btn_copiar_flyer.setStyleSheet("""
                    QPushButton {
                        background-color: #2980b9; color: white; font-weight: bold; font-size: 15px;
                        border-radius: 10px; margin-bottom: 20px; border: 2px solid #3498db;
                    }
                """) # Lo ponemos azul para confirmar éxito
            else:
                raise Exception("La imagen generada es nula.")

        except Exception as e:
            self.btn_copiar_flyer.setText("❌ Error al copiar")
            print(f"Error crítico en copiado de flyer: {e}")
        finally:
            QApplication.restoreOverrideCursor()
            # Restauramos el texto original después de 3 segundos
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self._restaurar_boton_flyer)

    def _restaurar_boton_flyer(self):
        """Devuelve el botón a su estado original verde."""
        self.btn_copiar_flyer.setText("📸 Copiar Flyer Publicitario")
        self.btn_copiar_flyer.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; font-weight: bold; font-size: 15px;
                border-radius: 10px; margin-bottom: 20px; border: 2px solid #2ecc71;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)

class StockManagerDialog(QDialog):
    """
    Ventana para buscar productos del Sheets e ingresarlos a la Base de Datos local.
    Funciona como un "Carrito de Compras" pero para ingresos de mercadería.
    """
    def __init__(self, parent, sheets_data: dict, menu_config: dict):
        super().__init__(parent)
        self.setWindowTitle("📦 Carrito de Ingreso de Mercadería")
        self.resize(950, 650)
        
        self.sheets_data = sheets_data
        self.menu_config = menu_config
        self.df_actual = pd.DataFrame() # Aquí guardaremos la categoría seleccionada
        
        self.ingresos_pendientes = {} 

        self.setup_ui()
        self.cargar_opciones_categoria() # Llenamos el desplegable

    def setup_ui(self):
        layout_principal = QHBoxLayout(self)

        # --- PANEL IZQUIERDO: BUSCADOR Y CATÁLOGO ---
        panel_izq = QVBoxLayout()
        
        # 🆕 NUEVO: Menú Desplegable de Categorías 🆕
        self.combo_categoria = QComboBox()
        self.combo_categoria.setStyleSheet("font-size: 15px; font-weight: bold; padding: 5px;")
        self.combo_categoria.currentIndexChanged.connect(self.al_cambiar_categoria)
        panel_izq.addWidget(self.combo_categoria)
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Filtrar modelo dentro de la categoría...")
        self.txt_buscar.setStyleSheet("font-size: 14px; padding: 5px;")
        self.txt_buscar.textChanged.connect(self.filtrar_catalogo)
        panel_izq.addWidget(self.txt_buscar)

        self.tabla_busqueda = QTableWidget()
        self.tabla_busqueda.setColumnCount(4)
        self.tabla_busqueda.setHorizontalHeaderLabels(["Código", "Modelo", "Stock Actual", "Acción"])
        self.tabla_busqueda.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla_busqueda.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_busqueda.setEditTriggers(QTableWidget.NoEditTriggers)
        panel_izq.addWidget(self.tabla_busqueda)

        layout_principal.addLayout(panel_izq, 2)

        # --- PANEL DERECHO: CARRITO DE INGRESOS ---
        # (Este bloque queda exactamente igual)
        panel_der = QVBoxLayout()
        lbl_titulo_carrito = QLabel("🛒 Productos a Ingresar:")
        lbl_titulo_carrito.setStyleSheet("font-size: 16px; font-weight: bold;")
        panel_der.addWidget(lbl_titulo_carrito)

        self.lista_ingresos = QListWidget()
        self.lista_ingresos.setStyleSheet("font-size: 14px;")
        panel_der.addWidget(self.lista_ingresos)

        self.btn_confirmar = QPushButton("✅ Confirmar Ingreso a Depósito")
        self.btn_confirmar.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 5px;}
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_confirmar.clicked.connect(self.procesar_ingresos)
        panel_der.addWidget(self.btn_confirmar)

        layout_principal.addLayout(panel_der, 1)

# ---------------------------------------------------------
    # 🆕 NUEVAS FUNCIONES DE LÓGICA DE CATEGORÍAS 🆕
    # ---------------------------------------------------------

    def cargar_opciones_categoria(self):
        """Lee el MENU_CONFIG y llena el desplegable."""
        self.combo_categoria.blockSignals(True) # Pausamos eventos mientras llenamos
        
        for key, config in self.menu_config.items():
            if config.get("tipo") == "categoria":
                grupo_nombre = config.get("nombre", "")
                for hoja in config.get("hojas", []):
                    # Mostramos al usuario "Colchones > 1 PLAZA"
                    nombre_mostrar = f"{grupo_nombre} > {hoja}"
                    
                    # El segundo parámetro (hoja) es la "Data" oculta que usaremos 
                    # para saber qué pedirle al catalogo_service.
                    self.combo_categoria.addItem(nombre_mostrar, hoja)
                    
        self.combo_categoria.blockSignals(False)
        
        # Forzamos la carga de la primera categoría disponible
        if self.combo_categoria.count() > 0:
            self.al_cambiar_categoria()

    def al_cambiar_categoria(self, *args):
        """Se dispara al elegir una opción del ComboBox."""
        from logic.catalogo_service import obtener_df_por_hoja
        
        # Recuperamos el nombre de la hoja seleccionada (ej: "1 PLAZA")
        hoja_nombre = self.combo_categoria.currentData()
        if not hoja_nombre: return
        
        # Le pedimos al servicio el DF ya inyectado con el stock
        self.df_actual = obtener_df_por_hoja(self.sheets_data, hoja_nombre)
        
        # Limpiamos el texto de búsqueda y mostramos la tabla completa de la categoría
        self.txt_buscar.blockSignals(True)
        self.txt_buscar.clear()
        self.txt_buscar.blockSignals(False)
        
        self.popular_tabla(self.df_actual)

    def filtrar_catalogo(self, texto):
        if not texto:
            self.popular_tabla(self.df_actual)
            return
            
        texto = texto.lower()
        if 'MODELO' in self.df_actual.columns:
            mask = self.df_actual['MODELO'].astype(str).str.lower().str.contains(texto, na=False)
            df_filtrado = self.df_actual[mask]
            self.popular_tabla(df_filtrado)

    def popular_tabla(self, df_a_mostrar):
        self.tabla_busqueda.setRowCount(0)
        
        col_codigo = 'CÓDIGO' if 'CÓDIGO' in df_a_mostrar.columns else 'CODIGO'
        if col_codigo not in df_a_mostrar.columns:
            return

        # 🔥 ¡HEMOS QUITADO EL .head(50)! Ahora muestra todos los de la categoría
        for i, fila in df_a_mostrar.iterrows():
            row_idx = self.tabla_busqueda.rowCount()
            self.tabla_busqueda.insertRow(row_idx)
            
            codigo = str(fila.get(col_codigo, 'S/C')).strip()
            if codigo.endswith('.0'): codigo = codigo[:-2] 
                
            modelo = str(fila.get('MODELO', 'Sin Nombre'))
            stock_act = str(fila.get('STOCK_ACTUAL', '0'))

            self.tabla_busqueda.setItem(row_idx, 0, QTableWidgetItem(codigo))
            self.tabla_busqueda.setItem(row_idx, 1, QTableWidgetItem(modelo))
            
            item_stock = QTableWidgetItem(stock_act)
            item_stock.setTextAlignment(Qt.AlignCenter)
            # Pinta el número de rojo si es 0 en esta vista
            if stock_act == '0':
                item_stock.setForeground(Qt.red)
                
            self.tabla_busqueda.setItem(row_idx, 2, item_stock)

            btn_add = QPushButton("➕ Agregar")
            btn_add.setStyleSheet("background-color: #3498db; color: white; border-radius: 3px;")
            btn_add.clicked.connect(lambda checked, c=codigo, m=modelo: self.solicitar_cantidad(c, m))
            self.tabla_busqueda.setCellWidget(row_idx, 3, btn_add)

    def solicitar_cantidad(self, codigo, modelo):
        if codigo == "S/C":
            QMessageBox.warning(self, "Error", "No se puede ingresar stock de un producto sin código identificador en el Sheets.")
            return

        # -------------------------------------------------------------
        # ARREGLO: Creamos un mini-diálogo manual para evitar el bug
        # de QInputDialog.getInt y de paso mejoramos el diseño.
        # -------------------------------------------------------------
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Ingresar Stock")
        dlg.setFixedSize(380, 160)
        
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel(f"¿Cuántas unidades de <b>{modelo}</b> ingresan al depósito?")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(lbl)
        
        # El "SpinBox" es el control de números con flechitas
        spin = QSpinBox(dlg)
        spin.setRange(1, 1000)
        spin.setValue(1)
        spin.setStyleSheet("font-size: 16px; padding: 5px;")
        layout.addWidget(spin)
        
        btn_layout = QHBoxLayout()
        
        btn_ok = QPushButton("✅ Confirmar")
        btn_ok.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        
        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        # -------------------------------------------------------------
        # Procesamiento del resultado
        # -------------------------------------------------------------
        if dlg.exec() == QDialog.Accepted:
            cantidad = spin.value()
            if codigo in self.ingresos_pendientes:
                self.ingresos_pendientes[codigo]['cantidad'] += cantidad
            else:
                self.ingresos_pendientes[codigo] = {'modelo': modelo, 'cantidad': cantidad}
            
            self.actualizar_vista_carrito()

    def actualizar_vista_carrito(self):
        self.lista_ingresos.clear()
        for cod, datos in self.ingresos_pendientes.items():
            self.lista_ingresos.addItem(f"{datos['cantidad']}x | {datos['modelo']} (Cod: {cod})")

    def procesar_ingresos(self):
        if not self.ingresos_pendientes:
            QMessageBox.warning(self, "Aviso", "El carrito de ingresos está vacío.")
            return

        try:
            for codigo, datos in self.ingresos_pendientes.items():
                detalle = f"Ingreso manual ({datos['modelo']})"
                # Registramos con cantidad positiva (INGRESO)
                registrar_movimiento_stock(codigo, datos['cantidad'], "INGRESO", detalle)

            QMessageBox.information(self, "Éxito", "¡Mercadería ingresada correctamente al inventario!")
            self.accept() # Cierra la ventana
            
        except Exception as e:
            QMessageBox.critical(self, "Error Fatal", f"Fallo al guardar en la base de datos:\n{e}")