# ui/proveedores_window.py
import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QDialog, QLabel, QFormLayout, QComboBox, QDoubleSpinBox,
    QTextEdit, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QDoubleValidator

from logic.proveedores_service import ProveedoresService, FormaPago

class ProveedoresWindow(QMainWindow):
    def __init__(self, proveedores_service: ProveedoresService, parent=None):
        super().__init__(parent)
        self.proveedores_service = proveedores_service
        self.setWindowTitle("Gestión de Proveedores / Compras")
        self.resize(900, 600)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # --- Top Bar ---
        self.top_bar = QHBoxLayout()
        
        self.btn_eliminar = QPushButton("Eliminar Proveedor")
        self.btn_eliminar.setStyleSheet("color: red; font-weight: bold;")
        self.btn_eliminar.clicked.connect(self.eliminar_proveedor)
        self.top_bar.addWidget(self.btn_eliminar)
        
        self.top_bar.addStretch()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar proveedor...")
        self.search_input.textChanged.connect(self.actualizar_tabla)
        self.top_bar.addWidget(self.search_input)
        
        self.btn_agregar = QPushButton("+ Agregar Proveedor")
        self.btn_agregar.clicked.connect(self.abrir_dialogo_agregar)
        self.top_bar.addWidget(self.btn_agregar)
        
        self.main_layout.addLayout(self.top_bar)
        
        # --- Table ---
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nombre", "Teléfono", "Saldo"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 150)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.abrir_detalle_proveedor)
        self.main_layout.addWidget(self.table)
        
        self.actualizar_tabla()
        
    def actualizar_tabla(self):
        query = self.search_input.text()
        proveedores = self.proveedores_service.obtener_proveedores(query)
        
        self.table.setRowCount(0)
        for row, prov in enumerate(proveedores):
            self.table.insertRow(row)
            
            item_nombre = QTableWidgetItem(prov.nombre)
            item_nombre.setData(Qt.UserRole, prov.id) # Guardar ID
            self.table.setItem(row, 0, item_nombre)
            
            item_tel = QTableWidgetItem(prov.num_tel)
            self.table.setItem(row, 1, item_tel)
            
            saldo = prov.saldo
            item_saldo = QTableWidgetItem(f"${saldo:,.2f}")
            item_saldo.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            font = QFont()
            font.setPointSize(11)
            font.setBold(True)
            item_saldo.setFont(font)
            if saldo < 0:
                item_saldo.setForeground(QColor("red"))
            elif saldo > 0:
                item_saldo.setForeground(QColor("green"))
            self.table.setItem(row, 2, item_saldo)
            
    def abrir_dialogo_agregar(self):
        dialog = ProveedorFormDialog(self)
        if dialog.exec() == QDialog.Accepted:
            nombre, telefono = dialog.get_data()
            if not self.proveedores_service.crear_proveedor(nombre, telefono):
                QMessageBox.warning(self, "Error", "El proveedor ya existe o ocurrió un error.")
            else:
                self.actualizar_tabla()
                
    def eliminar_proveedor(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        prov_id = item.data(Qt.UserRole)
        nombre = item.text()
        
        reply = QMessageBox.question(self, "Eliminar Proveedor", f"¿Está seguro de que desea eliminar a '{nombre}' y todos sus movimientos?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.proveedores_service.eliminar_proveedor(prov_id):
                self.actualizar_tabla()

    def abrir_detalle_proveedor(self, row, column):
        item = self.table.item(row, 0)
        prov_id = item.data(Qt.UserRole)
        dialog = ProveedorDetailDialog(prov_id, self.proveedores_service, self)
        dialog.exec()
        self.actualizar_tabla()


class ProveedorFormDialog(QDialog):
    def __init__(self, parent=None, proveedor=None):
        super().__init__(parent)
        self.setWindowTitle("Datos del Proveedor")
        self.setModal(True)
        self.resize(300, 150)
        
        layout = QFormLayout(self)
        
        self.nombre_input = QLineEdit()
        self.tel_input = QLineEdit()
        
        if proveedor:
            self.nombre_input.setText(proveedor.nombre)
            self.tel_input.setText(proveedor.num_tel)
            
        layout.addRow("Nombre:", self.nombre_input)
        layout.addRow("Teléfono:", self.tel_input)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
        
    def get_data(self):
        return self.nombre_input.text().strip(), self.tel_input.text().strip()


class ProveedorDetailDialog(QDialog):
    def __init__(self, proveedor_id, proveedores_service: ProveedoresService, parent=None):
        super().__init__(parent)
        self.proveedor_id = proveedor_id
        self.proveedores_service = proveedores_service
        self.proveedor = self.proveedores_service.obtener_proveedor_por_id(self.proveedor_id)
        
        self.setWindowTitle(f"Detalle - {self.proveedor.nombre}")
        self.setModal(True)
        self.resize(900, 600)
        
        self.layout = QVBoxLayout(self)
        
        # --- Top Buttons ---
        top_layout = QHBoxLayout()
        btn_editar = QPushButton("Editar Datos del Proveedor")
        btn_editar.clicked.connect(self.editar_proveedor)
        top_layout.addWidget(btn_editar)
        top_layout.addStretch()
        self.layout.addLayout(top_layout)
        
        # --- Table ---
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Fecha", "Descripción", "Debe ($)", "Haber ($)", "Forma de Pago"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.editar_movimiento)
        self.layout.addWidget(self.table)
        
        # --- Balance & Bottom Buttons ---
        bottom_layout = QHBoxLayout()
        
        btn_agregar_mov = QPushButton("Agregar Movimiento")
        btn_agregar_mov.clicked.connect(self.agregar_movimiento)
        bottom_layout.addWidget(btn_agregar_mov)
        
        btn_eliminar_mov = QPushButton("Eliminar Movimiento")
        btn_eliminar_mov.clicked.connect(self.eliminar_movimiento)
        bottom_layout.addWidget(btn_eliminar_mov)
        
        bottom_layout.addStretch()
        
        self.lbl_saldo = QLabel("Saldo: $0.00")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.lbl_saldo.setFont(font)
        bottom_layout.addWidget(self.lbl_saldo)
        
        self.layout.addLayout(bottom_layout)
        
        self.actualizar_vista()
        
    def actualizar_vista(self):
        self.proveedor = self.proveedores_service.obtener_proveedor_por_id(self.proveedor_id)
        if not self.proveedor:
            self.reject()
            return
            
        self.setWindowTitle(f"Detalle - {self.proveedor.nombre} ({self.proveedor.num_tel})")
        
        movimientos = self.proveedor.obtener_movimientos_ordenados()
        self.table.setRowCount(0)
        for row, mov in enumerate(movimientos):
            self.table.insertRow(row)
            
            item_fecha = QTableWidgetItem(mov.fecha.strftime('%d-%m-%Y'))
            item_fecha.setData(Qt.UserRole, mov.id)
            self.table.setItem(row, 0, item_fecha)
            
            self.table.setItem(row, 1, QTableWidgetItem(mov.descripcion))
            
            item_debe = QTableWidgetItem(f"${mov.debe:,.2f}" if mov.debe != 0 else "")
            item_debe.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2, item_debe)
            
            item_haber = QTableWidgetItem(f"${mov.haber:,.2f}" if mov.haber != 0 else "")
            item_haber.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, item_haber)
            
            self.table.setItem(row, 4, QTableWidgetItem(mov.forma_pago.value))
            
            pass
                    
        saldo = self.proveedor.saldo
        self.lbl_saldo.setText(f"Saldo Total: ${saldo:,.2f}")
        if saldo < 0:
            self.lbl_saldo.setStyleSheet("color: red;")
        elif saldo > 0:
            self.lbl_saldo.setStyleSheet("color: green;")
        else:
            self.lbl_saldo.setStyleSheet("color: black;")
            
    def editar_proveedor(self):
        dialog = ProveedorFormDialog(self, self.proveedor)
        if dialog.exec() == QDialog.Accepted:
            nombre, telefono = dialog.get_data()
            if self.proveedores_service.editar_proveedor(self.proveedor_id, {"nombre": nombre, "num_tel": telefono}):
                self.actualizar_vista()
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar o el nombre ya existe.")

    def agregar_movimiento(self):
        dialog = MovimientoFormDialog(self)
        if dialog.exec() == QDialog.Accepted:
            datos = dialog.get_data()
            if self.proveedores_service.agregar_movimiento(self.proveedor_id, datos):
                self.actualizar_vista()
                
    def editar_movimiento(self, row, column):
        item = self.table.item(row, 0)
        mov_id = item.data(Qt.UserRole)
        movimiento = next((m for m in self.proveedor.movimientos if m.id == mov_id), None)
        if not movimiento:
            return
            
        dialog = MovimientoFormDialog(self, movimiento)
        if dialog.exec() == QDialog.Accepted:
            datos = dialog.get_data()
            self.proveedores_service.editar_movimiento(self.proveedor_id, mov_id, datos)
            self.actualizar_vista()

    def eliminar_movimiento(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        item = self.table.item(row, 0)
        mov_id = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "Eliminar", "¿Eliminar movimiento seleccionado?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.proveedores_service.eliminar_movimiento(self.proveedor_id, mov_id):
                self.actualizar_vista()


class MovimientoFormDialog(QDialog):
    def __init__(self, parent=None, movimiento=None):
        super().__init__(parent)
        self.setWindowTitle("Datos del Movimiento")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QFormLayout(self)
        
        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDate(QDate.currentDate())
        
        validator = QDoubleValidator(0.0, 999999999.0, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        
        self.debe_input = QLineEdit("0")
        self.debe_input.setValidator(validator)
        
        self.haber_input = QLineEdit("0")
        self.haber_input.setValidator(validator)
        
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("Detalle de productos y cantidades...")
        self.desc_input.setMaximumHeight(80)
        
        self.forma_pago_input = QComboBox()
        for fp in FormaPago:
            self.forma_pago_input.addItem(fp.value, fp.value)
            
        if movimiento:
            qdate = QDate(movimiento.fecha.year, movimiento.fecha.month, movimiento.fecha.day)
            self.fecha_input.setDate(qdate)
            self.debe_input.setText(str(movimiento.debe) if movimiento.debe != 0 else "0")
            self.haber_input.setText(str(movimiento.haber) if movimiento.haber != 0 else "0")
            self.desc_input.setText(movimiento.descripcion)
            index = self.forma_pago_input.findData(movimiento.forma_pago.value)
            if index >= 0:
                self.forma_pago_input.setCurrentIndex(index)
                
        layout.addRow("Fecha:", self.fecha_input)
        layout.addRow("Debe (Pago):", self.debe_input)
        layout.addRow("Haber (Compra):", self.haber_input)
        layout.addRow("Descripción:", self.desc_input)
        layout.addRow("Forma de Pago:", self.forma_pago_input)
        
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addRow(btn_layout)
        
    def get_data(self):
        qdate = self.fecha_input.date()
        fecha_obj = datetime.datetime(qdate.year(), qdate.month(), qdate.day(), datetime.datetime.now().hour, datetime.datetime.now().minute)
        return {
            "fecha": fecha_obj.isoformat(),
            "debe": float(self.debe_input.text().replace(',', '.') or 0.0),
            "haber": float(self.haber_input.text().replace(',', '.') or 0.0),
            "descripcion": self.desc_input.toPlainText().strip(),
            "forma_pago": self.forma_pago_input.currentData()
        }
