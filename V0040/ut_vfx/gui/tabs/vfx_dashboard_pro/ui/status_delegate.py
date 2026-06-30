from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFontMetrics

class StatusDelegate(QStyledItemDelegate):
    STATUS_COLORS = {
        "APPROVED": QColor("#2e7d32"),
        "WIP": QColor("#1976d2"),
        "RETAKE": QColor("#f57c00"),
        "SENT FOR REVIEW": QColor("#7b1fa2"),
        "YTS": QColor("#616161"),
        "OMIT": QColor("#b71c1c"),
        "DONE": QColor("#2e7d32"),
        "READY": QColor("#00796b")
    }

    def paint(self, painter: QPainter, option, index):
        status_text = index.data(Qt.ItemDataRole.DisplayRole)
        if not status_text:
            super().paint(painter, option, index)
            return

        painter.save()
        
        # Determine background color based on status
        bg_color = self.STATUS_COLORS.get(status_text.upper(), QColor("#555555"))
        
        # Draw cell selection background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        
        # Create bold font for status
        font = option.font
        font.setBold(True)
        
        # Calculate pill rect using bold font metrics
        fm = QFontMetrics(font)
        text_rect = fm.boundingRect(status_text)
        
        pill_width = text_rect.width() + 16
        pill_height = fm.height() + 8
        
        # Clamp pill width to cell width
        if pill_width > option.rect.width() - 4:
            pill_width = option.rect.width() - 4
            
        # Center pill in the cell
        x_pos = option.rect.left() + max(2, (option.rect.width() - pill_width) // 2)
        y_pos = option.rect.top() + (option.rect.height() - pill_height) // 2
        
        pill_rect = QRect(x_pos, y_pos, pill_width, pill_height)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # VERY IMPORTANT: Prevent drawing outside the cell!
        painter.setClipRect(option.rect)
        
        # Draw pill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(pill_rect, 10, 10)
        
        # Elide text if it's too long
        elided_text = fm.elidedText(status_text, Qt.TextElideMode.ElideRight, pill_width - 8)
        
        # Draw text inside pill
        painter.setPen(QColor(Qt.GlobalColor.white))
        painter.setFont(font)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, elided_text)
        
        painter.restore()
