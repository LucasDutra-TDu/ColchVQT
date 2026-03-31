from PySide6.QtWidgets import QWidget, QSizePolicy, QHBoxLayout, QComboBox, QSpinBox, QLabel, QDialog, QVBoxLayout, QPushButton, QApplication, QMessageBox
from PySide6.QtCore import QDate, Signal, Qt
import os
from PySide6.QtGui import QPixmap, QIcon, QImage
from pathlib import Path


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
