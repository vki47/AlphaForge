from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
class PlaceholderView(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        l = QVBoxLayout(self)
        l.addWidget(QLabel(f"<h2>{title}</h2>"))
        b = QLabel(subtitle); b.setWordWrap(True)
        l.addWidget(b); l.addStretch()
