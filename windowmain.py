import os
import sys
import numpy as np
import cv2
import matplotlib.pyplot as plt
import qdarkstyle

from PyQt5.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QIcon, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QListWidget, QToolBar, QFileDialog, QPushButton, QListWidgetItem,
    QApplication, QListView, QWidget, QHBoxLayout, QAction, QVBoxLayout,
    QLabel, QFrame, QDesktopWidget, QMenuBar, QScrollArea, QDialog, QMessageBox,
    QTextBrowser
)
from show import show3d


# 自定义 QLabel，用于显示图片并支持绘图
class EditableLabel(QLabel):
    # 当图片被编辑（一笔画完）时，发射此信号，携带当前全分辨率的 QPixmap
    edit_made_signal = pyqtSignal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScaledContents(False)  # 禁用 QLabel 自动缩放，我们手动在 paintEvent 中处理
        self.setAlignment(Qt.AlignCenter)  # 图片居中显示

        self._full_res_pixmap = QPixmap()  # 存储实际的全分辨率图片，用于绘图
        self.drawing_enabled = False  # 是否启用绘图模式
        self.last_point = QPoint()  # 记录鼠标上一个点，用于绘制连续线条
        self.pen = QPen(QColor(255, 0, 0), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)  # 红色画笔，5像素粗细
        self._is_modified = False  # 标记当前图片是否被用户绘制修改过

        self.setMouseTracking(True)  # 启用鼠标跟踪，用于实时更新光标

    def set_pixmap(self, pixmap: QPixmap):
        """设置要显示和编辑的全分辨率图片。"""
        self._full_res_pixmap = pixmap.copy()  # 复制一份，避免修改外部引用
        self._is_modified = False  # 重置修改状态
        self.update()  # 触发重绘

    def current_pixmap(self) -> QPixmap:
        """返回当前的全分辨率图片（可能已编辑）。"""
        return self._full_res_pixmap

    def is_modified(self) -> bool:
        """返回图片是否被绘制修改过。"""
        return self._is_modified

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        painter.setRenderHint(QPainter.SmoothPixmapTransform)  # 平滑缩放

        if not self._full_res_pixmap.isNull():
            # 计算缩放后的图片尺寸，以适应当前 QLabel 的大小，并保持纵横比
            scaled_pixmap = self._full_res_pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # 计算偏移量，使图片在 QLabel 中居中
            x_offset = (self.width() - scaled_pixmap.width()) // 2
            y_offset = (self.height() - scaled_pixmap.height()) // 2

            painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        else:
            # 如果没有图片，则显示默认文本
            painter.drawText(self.rect(), Qt.AlignCenter, "Hi! Put your mixed picture here!")

        painter.end()

    def mousePressEvent(self, event):
        # 如果启用绘图模式，且按下左键，且有图片可绘制
        if self.drawing_enabled and event.button() == Qt.LeftButton and not self._full_res_pixmap.isNull():
            self.last_point = event.pos()  # 记录起始点
            self._is_modified = True  # 标记图片已被修改
            event.accept()  # 接受事件，阻止其向父控件传播
        else:
            super().mousePressEvent(event)  # 否则，将事件传递给父控件 (ScrollArea viewport)

    def mouseMoveEvent(self, event):
        # 如果启用绘图模式，且左键被按下拖动，且有图片可绘制
        if self.drawing_enabled and event.buttons() & Qt.LeftButton and not self._full_res_pixmap.isNull():
            if not self.last_point.isNull():
                # 创建 QPainter 直接在全分辨率图片上绘图
                painter = QPainter(self._full_res_pixmap)
                painter.setPen(self.pen)

                # 将 QLabel 上的鼠标坐标映射到全分辨率图片的坐标
                # 1. 获取图片在 QLabel 中实际显示的缩放尺寸
                scaled_pixmap_size = self._full_res_pixmap.size().scaled(
                    self.size(), Qt.KeepAspectRatio
                )
                # 2. 计算缩放比例
                x_scale = self._full_res_pixmap.width() / scaled_pixmap_size.width()
                y_scale = self._full_res_pixmap.height() / scaled_pixmap_size.height()

                # 3. 计算图片在 QLabel 中的偏移量（因为居中显示）
                x_offset = (self.width() - scaled_pixmap_size.width()) // 2
                y_offset = (self.height() - scaled_pixmap_size.height()) // 2

                # 4. 映射鼠标点到图片坐标
                p1_x = (self.last_point.x() - x_offset) * x_scale
                p1_y = (self.last_point.y() - y_offset) * y_scale
                p2_x = (event.pos().x() - x_offset) * x_scale
                p2_y = (event.pos().y() - y_offset) * y_scale

                # 确保绘制点在图片边界内
                p1_x = max(0, min(p1_x, self._full_res_pixmap.width() - 1))
                p1_y = max(0, min(p1_y, self._full_res_pixmap.height() - 1))
                p2_x = max(0, min(p2_x, self._full_res_pixmap.width() - 1))
                p2_y = max(0, min(p2_y, self._full_res_pixmap.height() - 1))

                painter.drawLine(QPoint(int(p1_x), int(p1_y)), QPoint(int(p2_x), int(p2_y)))
                painter.end()

                self.last_point = event.pos()  # 更新上一个点
                self.update()  # 触发 QLabel 重绘，显示新的线条
                event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 如果启用绘图模式，且左键释放，且图片被修改过
        if self.drawing_enabled and event.button() == Qt.LeftButton and self._is_modified:
            # 发射信号，通知 MainWindow 图片已被编辑
            self.edit_made_signal.emit(self._full_res_pixmap.copy())
            # _is_modified 保持为 True，直到图片被切换或明确重置
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        # 鼠标进入 QLabel 区域时，根据绘图模式设置光标
        if self.drawing_enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            # 非绘图模式下，让父级（DraggableScrollArea）决定光标
            self.unsetCursor()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标离开 QLabel 区域时，恢复默认光标
        self.unsetCursor() # 总是unset，让父级决定
        super().leaveEvent(event)

    def set_drawing_enabled(self, enabled: bool):
        """启用/禁用绘图模式，并更新光标。"""
        self.drawing_enabled = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.unsetCursor() # 让父级（DraggableScrollArea）决定光标


# DraggableScrollArea 需要感知绘图模式，以决定是滚动还是让子控件绘图
class DraggableScrollArea(QScrollArea):
    def __init__(self, main_window_ref, parent=None):
        super().__init__(parent)
        self.main_window_ref = main_window_ref  # 存储 MainWindow 的引用
        self.setWidgetResizable(True)
        self._scrolling = False
        self._last_pos = QPoint()
        # 初始光标，由 set_scrolling_enabled 决定
        self.viewport().setCursor(Qt.ArrowCursor)

    # 新增方法：启用/禁用滚动功能
    def set_scrolling_enabled(self, enabled: bool):
        self.horizontalScrollBar().setEnabled(enabled)
        self.verticalScrollBar().setEnabled(enabled)

        # 根据绘图模式和滚动条启用状态设置视口光标
        if self.main_window_ref.overlay_label.drawing_enabled:
            self.viewport().setCursor(Qt.CrossCursor)
        elif enabled: # 滚动启用，绘图禁用
            self.viewport().setCursor(Qt.OpenHandCursor)
        else: # 滚动禁用，绘图禁用
            self.viewport().setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        # 如果绘图模式启用，则忽略此事件，让它传递给子控件 (EditableLabel)
        if self.main_window_ref.overlay_label.drawing_enabled:
            event.ignore()
            return

        # 只有在滚动功能启用时才处理滚动事件
        if self.horizontalScrollBar().isEnabled() or self.verticalScrollBar().isEnabled():
            if event.button() == Qt.LeftButton:
                self._scrolling = True
                self._last_pos = event.pos()
                self.viewport().setCursor(Qt.ClosedHandCursor)  # 按下时变为抓手光标
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)  # 如果滚动被禁用，但不是绘图模式，则正常传递

    def mouseMoveEvent(self, event):
        if self.main_window_ref.overlay_label.drawing_enabled:
            event.ignore()
            return

        if self._scrolling:
            delta = event.pos() - self._last_pos
            self._last_pos = event.pos()

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.main_window_ref.overlay_label.drawing_enabled:
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            self._scrolling = False
            # 只有在滚动功能启用时才恢复手型光标
            if self.horizontalScrollBar().isEnabled() or self.verticalScrollBar().isEnabled():
                self.viewport().setCursor(Qt.OpenHandCursor)
            else:
                self.viewport().setCursor(Qt.ArrowCursor)  # 否则是箭头
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:  # 检查是否按下了Ctrl键
            if event.angleDelta().y() > 0:  # 滚轮向上，放大
                self.main_window_ref.zoom_in_overlay()
            else:  # 滚轮向下，缩小
                self.main_window_ref.zoom_out_overlay()
            event.accept()
        else:
            super().wheelEvent(event)


# 用于双击放大图像的对话框
class EnlargedImageViewer(QDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)

        # 标题栏：关闭 + 最大化
        self.setWindowTitle("指标图")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.original_pixmap = pixmap

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        content_frame = QFrame(self)
        # 黑色半透明背景
        content_frame.setStyleSheet("background-color: rgba(0, 0, 0, 180); border: none;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(10, 10, 10, 10)

        self.image_label = QLabel(content_frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        content_layout.addWidget(self.image_label)
        main_layout.addWidget(content_frame)

        # ---- 设置初始大小 & 居中 ----
        self.setGeometry(100, 100, 900, 700)  # 初始大小
        self.setMinimumSize(800, 600)

        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry()
        center_point = screen_rect.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        # ---------------------------------

        self.setWindowModality(Qt.ApplicationModal)
        self.installEventFilter(self)

        self.update_image_display()

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and event.key() == Qt.Key_Escape:
            self.accept()
            return True
        return super().eventFilter(obj, event)

    def update_image_display(self):
        """按窗口大小缩放图像"""
        target_image_width = int(self.width() * 0.9)
        target_image_height = int(self.height() * 0.9)

        if target_image_width > 0 and target_image_height > 0:
            scaled_pixmap = self.original_pixmap.scaled(
                target_image_width, target_image_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image_display()

# 得到一个成员是图像文件路径的列表
def load_image_paths(directory):
    filenames = os.listdir(directory)
    image_paths = []
    for file in filenames:
        if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            image_paths.append(os.path.join(directory, file))
    image_paths.sort()
    return image_paths


# 定义缩略图列表部分
class ImageListWidget(QListWidget):
    def __init__(self):
        super(ImageListWidget, self).__init__()
        self.setFlow(QListView.LeftToRight)
        self.setIconSize(QSize(180, 120))
        self.setResizeMode(QListView.Adjust)
        self.setViewMode(QListView.IconMode)

    def add_image_items(self, image_paths=[]):
        self.clear()
        for img_path in image_paths:
            if os.path.isfile(img_path):
                img_name = os.path.basename(img_path)
                item = QListWidgetItem(QIcon(img_path), img_name)
                self.addItem(item)


# 帮助文档对话框
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用指南")
        # 确保有标准标题栏，包含最大化和关闭按钮，移除最小化按钮
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)

        # 初始大小调整为稍微大一点，例如 900x700
        self.setGeometry(100, 100, 900, 700)  # 初始大小调整为 900x700

        # 初始居中
        desktop = QApplication.desktop()
        # 计算屏幕中心点
        screen_center = desktop.screenGeometry().center()
        # 计算对话框的中心点
        dialog_center = self.rect().center()
        # 将对话框移动到屏幕中心
        self.move(screen_center - dialog_center)

        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        # 设置默认样式表，使图片宽度适应 QTextBrowser
        self.text_browser.document().setDefaultStyleSheet("img { max-width: 100%; height: auto; }")
        self.text_browser.setMarkdown(self._get_help_content())
        layout.addWidget(self.text_browser)

        # 允许按 ESC 键关闭对话框
        self.setWindowModality(Qt.ApplicationModal)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and event.key() == Qt.Key_Escape:
            self.accept()
            return True
        return super().eventFilter(obj, event)

    def _get_help_content(self):
        """返回帮助文档的 Markdown 格式内容。"""
        return """
欢迎使用 **智慧脑 | 脑出血诊断分析软件**！
本系统用于辅助医生快速查看脑部CT平扫图像，进行出血量分析和诊断参考。

---

## 1. 界面概览

主界面分为三部分：

*   **左侧面板**：图像导入与缩略图列表
*   **中间面板**：CT 图像显示与编辑
*   **右侧面板**：诊断结果与分析

以下是界面布局示意图：

![界面布局示意图](help_images/interface_overview.png)

---

## 2. 顶部工具栏

*   **主页 / 菜单**：返回主界面或图像列表
*   **编辑**：切换勾画模式
   *   开启后：用鼠标左键可在图像上画红色标记 (光标变为十字)
   *   关闭后：恢复拖动和缩放功能 (光标变为小手)
*   **撤销 / 重做**：撤销或恢复编辑
*   **放大 / 缩小**：调整图像大小（快捷键 `Ctrl + 滚轮`） 
*   **上一张 / 下一张**：切换图像
*   **帮助**：打开本指南 (按 `ESC` 键关闭)

以下是工具栏功能图：

![工具栏功能图](help_images/toolbar_functions.png)

---

## 3. 左侧面板：图像导入与列表

*   **导入原图**：选择图像所在文件夹，系统会自动加载常见格式（PNG、JPG、BMP 等）。
*   **缩略图列表**：点击缩略图即可在中间面板查看对应图像，右侧面板会同步更新诊断结果。

---

## 4. 中间面板：图像查看与编辑

*   **拖动**：非编辑模式下，按住左键拖动图像，光标显示为 **小手**。
*   **缩放**：工具栏按钮或 `Ctrl + 滚轮`。
*   **红笔勾画**：编辑模式下，用鼠标左键标注区域，光标显示为 **十字**。
*   **3D出血模型**：点击右下角的 **“3D”按钮**，显示该病例的三维出血区域。窗口支持鼠标旋转和滑动条精确旋转。

---

## 5. 右侧面板：诊断结果

*   **评估指标图**：显示 IOU、Dice 系数、准确率等指标（支持双击放大查看，放大比例为屏幕的 **50%**）。
*   **出血量图 & 数值**：显示患者出血量分布，并给出当前图像的出血量（mL）。
*   **诊断建议**：根据出血量自动提供轻度 / 中度 / 重度的诊断参考。

---

## 6. 注意事项

*   确认 `data/predict` 和 `data/mask` 目录下有对应文件。
*   支持常见图像格式（PNG、JPG、BMP、GIF）。
*   大量高分辨率图像时可能会有轻微延迟。
*   **提示**：系统结果仅供参考，最终诊断需由专业医生确认。
"""


# 布局窗体控件
class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        # 新增实例变量用于管理当前图片路径、缓存及撤销/重做堆栈
        self.current_image_path = None
        # image_data_cache 存储每张图片的 (original_pixmap, current_edited_pixmap, undo_stack, redo_stack, current_zoom_factor)
        self.image_data_cache = {}
        self.current_undo_stack = []  # 当前图片的撤销堆栈
        self.current_redo_stack = []  # 当前图片的重做堆栈
        self.max_undo_history = 20  # 最大撤销步数

        # _current_display_pixmap 存储当前显示在 overlay_label 上的全分辨率图片（可能已编辑）
        self._current_display_pixmap = None
        self.current_overlay_zoom_factor = 1.0  # 当前图片的缩放因子

        try:
            self.initUI()
        except Exception as e:
            print(f"Error during initialization: {e}")

    def initUI(self):
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry()  # 可用区域（不含任务栏）

        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # 直接用可用区域大小
        self.setGeometry(screen_rect)

        self.tool_bar = QToolBar(self)
        self.init_toolbar()

        self.buttonlist_frame = QFrame(self)
        self.buttonlist_frame.setStyleSheet(u"border: 1px solid blue;")
        self.list_widget = ImageListWidget()
        self.image_button = QPushButton("导入原图", self.buttonlist_frame)
        self.image_paths = []
        self.currentImgIdx = 0

        self.handle_frame = QFrame(self)
        self.handle_frame.setStyleSheet(u"border: 1px solid blue;")

        self.overlay_scroll_area = DraggableScrollArea(self, self.handle_frame)
        self.overlay_label = EditableLabel()
        self.overlay_scroll_area.setWidget(self.overlay_label)

        # —— 放在 initUI() 里，overlay_scroll_area 创建之后 ——
        # 把信息标签挂到“图片真正显示区域”的 viewport 上
        self.patient_info_label = QLabel(self.overlay_scroll_area.viewport())
        self.patient_info_label.setWordWrap(True)
        self.patient_info_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # 不阻挡鼠标操作（画笔/拖拽）
        self.patient_info_label.setStyleSheet("""
            QLabel {
                background-color: transparent;   /* 半透明黑底 */
                color: #FFFFFF;
                font-size: 9pt;
                padding: 8px 12px;
                border: none;
            }
        """)
        self.patient_info_label.raise_()  # 显示在最上层

        # 初始排版
        self._layout_patient_info()
        # 当图片区域尺寸变化时，跟着重排（比如窗口调整/左右面板变化）
        old_resize = self.overlay_scroll_area.resizeEvent

        def _on_scrollarea_resize(ev):
            self._layout_patient_info()  # 左上角信息标签跟随
            self._layout_show3d_button()  # 右下角3D按钮跟随
            if old_resize:
                old_resize(ev)

        self.overlay_scroll_area.resizeEvent = _on_scrollarea_resize

        # —— 3D按钮（挂在 viewport 上，保证浮在图像区域里） ——
        self.show3d_button = QPushButton("3D", self.overlay_scroll_area.viewport())
        self.show3d_button.setCursor(Qt.PointingHandCursor)
        self.show3d_button.setToolTip("查看该病例（三维）出血模型")
        self.show3d_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 150, 136, 180);
                color: white;
                border-radius: 20px;
                font-size: 12pt;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: rgba(0, 150, 136, 230);
            }
        """)
        self.show3d_button.setFixedSize(60, 60)
        self.show3d_button.raise_()  # 保证覆盖在最上层
        self.show3d_button.clicked.connect(self.show_current_case_3d)

        # 初始摆放到右下角
        self._layout_show3d_button()

        self.overlay_label.edit_made_signal.connect(self._record_edit)

        self.diagnosis_frame = QFrame(self)
        self.show1_label = QLabel(self.diagnosis_frame)
        self.show2_label = QLabel(self.diagnosis_frame)
        self.show3_label = QLabel(self.diagnosis_frame)
        self.diagnosis_frame.setStyleSheet(u"border: 1px solid blue;")
        self.show1_label.setStyleSheet(u"border: 1px solid blue;")
        self.show2_label.setStyleSheet(u"border: 1px solid blue;")
        self.show3_label.setStyleSheet("font-size: 13pt; font-family: Cursive; color: #009688;")
        self.show3_label.setAlignment(Qt.AlignCenter)
        self.show3_label.setWordWrap(True)

        self.show1_label.mouseDoubleClickEvent = lambda event: self.show_enlarged_chart(event, self.show1_label)
        self.show2_label.mouseDoubleClickEvent = lambda event: self.show_enlarged_chart(event, self.show2_label)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tool_bar)
        self.main_layout = QHBoxLayout(self)
        self.layout.addLayout(self.main_layout)

        self.main_layout.addWidget(self.buttonlist_frame)
        self.main_layout.addWidget(self.handle_frame)
        self.main_layout.addWidget(self.diagnosis_frame)

        self.vertical_layout = QVBoxLayout(self.buttonlist_frame)
        self.vertical_layout.addWidget(self.list_widget)
        self.vertical_layout.addWidget(self.image_button)

        self.vertical_layout = QVBoxLayout(self.handle_frame)
        self.vertical_layout.addWidget(self.overlay_scroll_area)

        self.vertical_layout = QVBoxLayout(self.diagnosis_frame)
        self.vertical_layout.addWidget(self.show1_label)
        self.vertical_layout.addWidget(self.show2_label)
        self.vertical_layout.addWidget(self.show3_label)

        self.buttonlist_frame.setMaximumHeight(screen_height)
        self.handle_frame.setMaximumHeight(screen_height)
        self.diagnosis_frame.setMaximumHeight(screen_height)
        self.buttonlist_frame.setMaximumWidth(screen_width // 6)
        self.handle_frame.setMaximumWidth(int(screen_width * 0.6))
        self.diagnosis_frame.setMaximumWidth(int(screen_width * 0.2333))

        self.list_widget.setMaximumHeight(screen_height // 9 * 6)
        self.image_button.setMaximumHeight(screen_height // 9)
        self.image_button.setMaximumWidth(screen_width // 6)

        self.list_widget.itemSelectionChanged.connect(self.on_image_selection_changed)
        self.list_widget.itemClicked.connect(self.diagnosis)
        self.image_button.clicked.connect(self.choose_folder)

        if not os.path.exists("data/predict"):
            os.makedirs("data/predict")
        if not os.path.exists("data/mask"):
            os.makedirs("data/mask")
        # Ensure help_images directory exists for help dialog images
        if not os.path.exists("help_images"):
            os.makedirs("help_images")

        predict_dir = r"data/predict"
        self.predict_paths = load_image_paths(predict_dir)
        mask_dir = r"data/mask"
        self.mask_paths = load_image_paths(mask_dir)

    def show_current_case_3d(self):
        if self.current_image_path:
            img_name = os.path.basename(self.current_image_path)
            show3d(img_name, 800, 600)
        else:
            QMessageBox.information(self, "提示", "请先选择一张病例图像！")

    def _layout_patient_info(self):
        """
        把左上角信息标签放到 viewport 内合适的位置 & 合适宽度。
        """
        vp = self.overlay_scroll_area.viewport()
        if not vp:
            return

        # 让宽度相对自适应：占 viewport 宽度的 26%~40% 之间（你可按喜好微调）
        vw = max(260, min(int(vp.width() * 0.32), 420))
        self.patient_info_label.setFixedWidth(vw)
        self.patient_info_label.adjustSize()  # 按内容自适应高度

        margin = 12
        self.patient_info_label.move(margin, margin)  # 左上角留点边距
        self.patient_info_label.raise_()

    def _update_patient_info_text(self, patient_id: str):
        """
        更新信息标签内容。姓名/性别/生日没有就用 ** 占位；PID 显示病例编号。
        """
        self.patient_info_label.setText(
            f"姓名: **\n性别/年龄: ** / **\n出生日期: **\nPID: {patient_id}"
        )
        self._layout_patient_info()

    def _layout_show3d_button(self):
        """把3D按钮放到 viewport 的右下角，并保持在最上层"""
        vp = self.overlay_scroll_area.viewport()
        if not vp or not hasattr(self, "show3d_button"):
            return
        margin = 15
        x = max(margin, vp.width() - self.show3d_button.width() - margin)
        y = max(margin, vp.height() - self.show3d_button.height() - margin)
        self.show3d_button.move(x, y)
        self.show3d_button.raise_()

    def init_toolbar(self):
        self.tool_bar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_label = QLabel()
        width = 60
        logo_label.setPixmap(
            QPixmap('icons/logo.jpg').scaled(width, width, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        text_label = QLabel('智慧脑 | 脑部CT平扫 ')
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(text_label)
        text_label.setFont(QFont("Helvetica", 16))
        text_label.setStyleSheet("color: white;")
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_widget.setLayout(logo_layout)

        self.tool_bar.addWidget(logo_widget)

        home_action = QAction(QIcon('icons/home.png'), '主页', self)
        list_action = QAction(QIcon('icons/list.png'), '菜单', self)

        self.edit_action = QAction(QIcon('icons/edit.png'), '编辑', self)
        self.edit_action.setCheckable(True)
        self.edit_action.toggled.connect(self._toggle_edit_mode)

        self.undo_action = QAction(QIcon('icons/undo.png'), '撤销', self)
        self.redo_action = QAction(QIcon('icons/redo.png'), '重做', self)
        self.undo_action.triggered.connect(self._undo_edit)
        self.redo_action.triggered.connect(self._redo_edit)
        self.undo_action.setEnabled(False)
        self.redo_action.setEnabled(False)

        zoomin_action = QAction(QIcon('icons/zoom-in.png'), '放大', self)
        zoomout_action = QAction(QIcon('icons/zoom-out.png'), '缩小', self)
        chevronsup_action = QAction(QIcon('icons/chevrons-up.png'), '上一张', self)
        chevronsdown_action = QAction(QIcon('icons/chevrons-down.png'), '下一张', self)

        help_action = QAction(QIcon('icons/help.png'), '帮助', self)
        help_action.triggered.connect(self.show_help_dialog)

        self.tool_bar.addAction(home_action)
        self.tool_bar.addAction(list_action)
        self.tool_bar.addAction(self.edit_action)
        self.tool_bar.addAction(self.undo_action)
        self.tool_bar.addAction(self.redo_action)
        self.tool_bar.addAction(zoomin_action)
        self.tool_bar.addAction(zoomout_action)
        self.tool_bar.addAction(chevronsup_action)
        self.tool_bar.addAction(chevronsdown_action)
        self.tool_bar.addAction(help_action)

        zoomin_action.triggered.connect(self.zoom_in_overlay)
        zoomout_action.triggered.connect(self.zoom_out_overlay)
        chevronsup_action.triggered.connect(self.go_to_previous_image)
        chevronsdown_action.triggered.connect(self.go_to_next_image)

    def _update_undo_redo_actions(self):
        """根据当前堆栈状态更新撤销/重做按钮的可用性。"""
        self.undo_action.setEnabled(len(self.current_undo_stack) > 1)
        self.redo_action.setEnabled(len(self.current_redo_stack) > 0)

    def _toggle_edit_mode(self, checked: bool):
        """切换编辑模式。"""
        self.overlay_label.set_drawing_enabled(checked)
        self.overlay_scroll_area.set_scrolling_enabled(not checked)

    def _record_edit(self, edited_pixmap: QPixmap):
        """记录一次编辑操作到撤销堆栈。"""
        if not self.current_image_path:
            return

        # 如果有新的编辑，清空重做堆栈
        self.current_redo_stack.clear()
        self.current_undo_stack.append(edited_pixmap.copy())

        # 限制撤销堆栈大小
        while len(self.current_undo_stack) > self.max_undo_history:
            self.current_undo_stack.pop(0) # 移除最旧的记录

        # 更新缓存中的当前编辑状态和堆栈
        original_px, _, _, _, current_zoom = self.image_data_cache[self.current_image_path]
        self.image_data_cache[self.current_image_path] = (
            original_px, edited_pixmap.copy(), self.current_undo_stack.copy(), self.current_redo_stack.copy(),
            current_zoom
        )
        self._current_display_pixmap = edited_pixmap.copy() # 更新当前显示的图片

        self._update_undo_redo_actions()

    def _undo_edit(self):
        """执行撤销操作。"""
        if len(self.current_undo_stack) > 1: # 至少需要保留一个初始状态
            last_state = self.current_undo_stack.pop()
            self.current_redo_stack.append(last_state)

            prev_state = self.current_undo_stack[-1]
            self._current_display_pixmap = prev_state.copy()
            self.overlay_label.set_pixmap(self._current_display_pixmap) # 直接设置给label

            # 更新缓存
            original_px, _, _, _, current_zoom = self.image_data_cache[self.current_image_path]
            self.image_data_cache[self.current_image_path] = (
                original_px, self._current_display_pixmap.copy(), self.current_undo_stack.copy(),
                self.current_redo_stack.copy(), current_zoom
            )

            self._update_overlay_display(force_update_label=False) # 仅更新尺寸，label已更新pixmap
            self._update_undo_redo_actions()
        else:
            QMessageBox.information(self, self.tr("提示"), self.tr("已经是最初状态了，无法再撤销！"))

    def _redo_edit(self):
        """执行重做操作。"""
        if self.current_redo_stack:
            next_state = self.current_redo_stack.pop()
            self.current_undo_stack.append(next_state)

            self._current_display_pixmap = next_state.copy()
            self.overlay_label.set_pixmap(self._current_display_pixmap) # 直接设置给label

            # 更新缓存
            original_px, _, _, _, current_zoom = self.image_data_cache[self.current_image_path]
            self.image_data_cache[self.current_image_path] = (
                original_px, self._current_display_pixmap.copy(), self.current_undo_stack.copy(),
                self.current_redo_stack.copy(), current_zoom
            )

            self._update_overlay_display(force_update_label=False) # 仅更新尺寸，label已更新pixmap
            self._update_undo_redo_actions()
        else:
            QMessageBox.information(self, self.tr("提示"), self.tr("没有可重做的操作！"))

    def choose_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图像文件夹", os.getcwd())
        if folder_path:
            img_paths = load_image_paths(folder_path)
            self.list_widget.add_image_items(img_paths)
            self.image_paths = img_paths
            if self.image_paths:
                self.list_widget.setCurrentRow(0)

    def cv_image_to_qimage(self, cv_image):
        """将 OpenCV 图像转换为 QImage。"""
        if cv_image.dtype != np.uint8:
            cv_image = cv2.normalize(cv_image, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

        if len(cv_image.shape) == 3:
            height, width, channel = cv_image.shape
            if channel == 3:
                rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
                bytes_per_line = 3 * width
                q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:
                raise ValueError(f"Unsupported image channel count: {channel} for QImage conversion.")
        elif len(cv_image.shape) == 2:
            height, width = cv_image.shape
            bytes_per_line = width
            q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        else:
            raise ValueError("Unsupported image format for QImage conversion.")
        return q_image

    def on_image_selection_changed(self):
        """当图片列表选择改变时触发。"""
        new_idx = self.list_widget.currentIndex().row()
        if not (0 <= new_idx < len(self.image_paths)):
            return

        # 保存当前图片的编辑状态和堆栈到缓存
        if self.current_image_path and self.current_image_path in self.image_data_cache:
            original_px, _, _, _, _ = self.image_data_cache[self.current_image_path]
            self.image_data_cache[self.current_image_path] = (
                original_px, self._current_display_pixmap.copy(),
                self.current_undo_stack.copy(), self.current_redo_stack.copy(),
                self.current_overlay_zoom_factor
            )

        self.currentImgIdx = new_idx
        new_image_path = self.image_paths[self.currentImgIdx]
        self.current_image_path = new_image_path
        filename = os.path.basename(new_image_path)  # 例： "049_15.png"
        patient_id = filename.split("_")[0]  # "049"
        self._update_patient_info_text(patient_id)  # 更新左上角信息

        # 从缓存加载新图片的编辑状态和堆栈
        if new_image_path in self.image_data_cache:
            original_px, edited_px, undo_s, redo_s, zoom_f = self.image_data_cache[new_image_path]
            self._current_display_pixmap = edited_px.copy()
            self.current_undo_stack = undo_s.copy()
            self.current_redo_stack = redo_s.copy()
            self.current_overlay_zoom_factor = zoom_f
        else:
            # 如果是新图片，则加载并初始化
            img_path = self.image_paths[self.currentImgIdx]
            predict_path = self.predict_paths[self.currentImgIdx]

            image = cv2.imread(img_path)
            predict = cv2.imread(predict_path, cv2.IMREAD_GRAYSCALE)

            predict_3d = cv2.cvtColor(predict, cv2.COLOR_GRAY2BGR)
            overlay = cv2.addWeighted(image, 0.7, predict_3d, 0.3, 0)

            contours, hierarchy = cv2.findContours(predict, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, (255, 0, 0), 1)

            q_image = self.cv_image_to_qimage(overlay)
            original_px = QPixmap.fromImage(q_image)

            self._current_display_pixmap = original_px.copy()
            self.current_undo_stack = [self._current_display_pixmap.copy()]
            self.current_redo_stack = []

            viewport_width = self.overlay_scroll_area.viewport().width()
            viewport_height = self.overlay_scroll_area.viewport().height()
            original_width = self._current_display_pixmap.width()
            original_height = self._current_display_pixmap.height()

            self.current_overlay_zoom_factor = 1.0
            if original_width > 0 and original_height > 0 and viewport_width > 0 and viewport_height > 0:
                scale_w = viewport_width / original_width
                scale_h = viewport_height / original_height
                if original_width < viewport_width or original_height < viewport_height:
                    self.current_overlay_zoom_factor = scale_w
                    if (original_height * self.current_overlay_zoom_factor) > viewport_height:
                        self.current_overlay_zoom_factor = scale_h
                    if self.current_overlay_zoom_factor > 2.0:
                        self.current_overlay_zoom_factor = 2.0
                else:
                    self.current_overlay_zoom_factor = min(scale_w, scale_h)

            self.image_data_cache[new_image_path] = (
                original_px.copy(), self._current_display_pixmap.copy(),
                self.current_undo_stack.copy(), self.current_redo_stack.copy(),
                self.current_overlay_zoom_factor
            )

        self._update_overlay_display(force_update_label=True)
        self._update_undo_redo_actions()

        self.showImage_original_for_diagnosis()
        self.parameter()
        self.diagnosis(None)

    def showImage_original_for_diagnosis(self):
        """在 show1_label 中显示原始图片（未叠加、未编辑）。"""
        if self.currentImgIdx in range(len(self.image_paths)):
            original_image_path = self.image_paths[self.currentImgIdx]
            original_pixmap = QPixmap(original_image_path)
            scaled_pixmap = original_pixmap.scaled(self.show1_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.show1_label.setPixmap(scaled_pixmap)
            self.show1_label.setAlignment(Qt.AlignCenter)

    def _update_overlay_display(self, force_update_label=False):
        """
        更新滚动区域中叠加图片的显示。
        `force_update_label` 为 True 时，会强制重设 EditableLabel 的内部 pixmap。
        """
        if self._current_display_pixmap and not self._current_display_pixmap.isNull():
            original_width = self._current_display_pixmap.width()
            original_height = self._current_display_pixmap.height()

            scaled_width = int(original_width * self.current_overlay_zoom_factor)
            scaled_height = int(original_height * self.current_overlay_zoom_factor)

            if scaled_width == 0: scaled_width = 1
            if scaled_height == 0: scaled_height = 1

            display_size = QSize(scaled_width, scaled_height)
            self.overlay_label.setFixedSize(display_size)

            if force_update_label:
                self.overlay_label.set_pixmap(self._current_display_pixmap)

            self.overlay_label.update()
        else:
            self.overlay_label.setFixedSize(self.overlay_scroll_area.viewport().size())
            self.overlay_label.setText("Hi!put your mixed picture here!")
            self.overlay_label.set_pixmap(QPixmap())

    def zoom_in_overlay(self):
        """放大叠加图片。"""
        if self._current_display_pixmap:
            self.current_overlay_zoom_factor *= 1.1
            self._update_overlay_display()
            if self.current_image_path and self.current_image_path in self.image_data_cache:
                original_px, edited_px, undo_s, redo_s, _ = self.image_data_cache[self.current_image_path]
                self.image_data_cache[self.current_image_path] = (
                    original_px, edited_px, undo_s, redo_s, self.current_overlay_zoom_factor)

    def zoom_out_overlay(self):
        """缩小叠加图片。"""
        if self._current_display_pixmap:
            self.current_overlay_zoom_factor /= 1.1
            if self.current_overlay_zoom_factor < 0.05:
                self.current_overlay_zoom_factor = 0.05
            self._update_overlay_display()
            if self.current_image_path and self.current_image_path in self.image_data_cache:
                original_px, edited_px, undo_s, redo_s, _ = self.image_data_cache[self.current_image_path]
                self.image_data_cache[self.current_image_path] = (
                    original_px, edited_px, undo_s, redo_s, self.current_overlay_zoom_factor)

    def go_to_previous_image(self):
        """切换到上一张图片。"""
        if not self.image_paths:
            return
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            new_row = current_row - 1
            self.list_widget.setCurrentRow(new_row)
        else:
            QMessageBox.information(self, self.tr("提示"), self.tr("已经是第一张图片了！"))

    def go_to_next_image(self):
        """切换到下一张图片。"""
        if not self.image_paths:
            return
        current_row = self.list_widget.currentRow()
        if current_row < len(self.image_paths) - 1:
            new_row = current_row + 1
            self.list_widget.setCurrentRow(new_row)
        else:
            QMessageBox.information(self, self.tr("提示"), self.tr("已经是最后一张图片了！"))

    def show_enlarged_chart(self, event, label: QLabel):
        if event.button() == Qt.LeftButton:
            # 直接加载保存的高清图文件，而不是 label 的缩略图
            if label is self.show1_label:
                pixmap = QPixmap("evaluation_metrics.png")
            elif label is self.show2_label:
                pixmap = QPixmap("calcut.png")
            else:
                pixmap = label.pixmap()

            if pixmap and not pixmap.isNull():
                self.viewer = EnlargedImageViewer(pixmap)  # 存到 self 避免被回收
                self.viewer.show()

    def show_help_dialog(self):
        """显示帮助文档对话框。"""
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def parameter(self):
        """计算并显示评估指标。"""
        self.currentImgIdx = self.list_widget.currentIndex().row()
        if self.currentImgIdx in range(len(self.mask_paths)):
            predict_path = self.predict_paths[self.currentImgIdx]
            mask_path = self.mask_paths[self.currentImgIdx]

            predict = cv2.imread(predict_path, cv2.IMREAD_GRAYSCALE)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            _, predict_binary = cv2.threshold(predict, 127, 255, cv2.THRESH_BINARY)
            _, mask_binary = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

            predict_image = predict_binary.astype(bool)
            mask_image = mask_binary.astype(bool)

            tp = np.sum(np.logical_and(predict_image, mask_image))
            tn = np.sum(np.logical_and(np.logical_not(predict_image), np.logical_not(mask_image)))
            fp = np.sum(np.logical_and(predict_image, np.logical_not(mask_image)))
            fn = np.sum(np.logical_and(np.logical_not(predict_image), mask_image))

            iou = tp / (tp + fn + fp + 1e-7)
            dice_coefficient = 2 * tp / (2 * tp + fn + fp + 1e-7)
            accuracy = (tp + tn) / (tp + fp + tn + fn + 1e-7)
            precision = tp / (tp + fp + 1e-7)
            recall = tp / (tp + fn + 1e-7)
            sensitivity = tp / (tp + fn + 1e-7)
            f1 = 2 * (precision * recall) / (precision + recall + 1e-7)
            specificity = tn / (tn + fp + 1e-7)

            metrics = ['IOU', 'Dice Coefficient', 'Accuracy', 'Precision', 'Recall', 'Sensitivity', 'F1-score',
                       'Specificity']
            values = [iou, dice_coefficient, accuracy, precision, recall, sensitivity, f1, specificity]
            x = np.arange(len(metrics))
            y = values
            plt.figure(figsize=(10, 8))
            plt.bar(x, y, color='skyblue')
            plt.title('Comparison of Evaluation Metrics')
            plt.xticks(x, metrics, rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('evaluation_metrics.png', dpi=300)
            plt.close()
            pixmap = QPixmap('evaluation_metrics.png')
            pixmap = pixmap.scaled(self.show1_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.show1_label.setPixmap(pixmap)
            self.show1_label.setAlignment(Qt.AlignCenter)

    def diagnosis(self, item):
        """计算出血量并给出诊断方案。"""
        diagnosis_plans = {
            "small": "这是一个轻度脑出血，建议进行轻度观察和监测，可以保守治疗,并采用降温毯、降温头盔等，进行全身、头部局部降温，可以减轻脑水肿，促进神经功能缺失恢复，改善患者预后。",
            "medium": "这是一个中度脑出血，可能需要进一步的检查和治疗中度脑出血，可以根据患者的生命体征，以及是否存在继续出血、出血量增加等现象，选择进行手术或保守治疗。",
            "large": "这是一个重度脑出血，需要立即采取措施，一般建议手术治疗，去除血肿，避免发生严重的后果，比如脑疝等，危及患者生命安全。通过治疗，同时加上控制血压的药物，可以避免脑出血复发。"
        }

        list_areas_px = [613.3888888888889, 535.5416666666666, 2041.9736842105262, 628.1111111111111, 625.15, 212.5,
                         1477.9166666666667, 140.1, 1306.95, 205.25, 2538.1785714285716, 6631.684210526316, 235.75,
                         826.1666666666666, 506.1923076923077, 6013.875, 1023.7142857142857, 2428.4166666666665,
                         386.40909090909093, 1.0, 956.5454545454545, 2550.5666666666666, 38.75, 567.3333333333334,
                         965.0,
                         1104.25, 401.92857142857144, 1610.6666666666667, 1038.0833333333333, 1026.0625, 849.875,
                         821.6428571428571, 714.9090909090909, 274.5, 4990.791666666667, 681.0555555555555]
        num_images = [9, 12, 19, 9, 10, 2, 12, 5, 10, 2, 14, 19, 2, 6, 13, 16, 14, 12, 11, 1, 11, 15, 2, 6, 4, 2, 7, 12,
                      6, 8, 4, 7, 11, 4, 12, 9]
        thickness_mm = 5

        volume_mm3 = [area * thickness_mm for area in list_areas_px]
        volume_ml = [volume / 1000 for volume in volume_mm3]

        current_row = self.list_widget.currentRow()

        patient_idx = -1
        image_count_sum = 0
        for i, num_img in enumerate(num_images):
            if current_row < image_count_sum + num_img:
                patient_idx = i
                break
            image_count_sum += num_img

        if patient_idx != -1 and patient_idx < len(volume_ml):
            avg_volume_ml = volume_ml[patient_idx]
            self.show2_label.setText(f"出血量: {avg_volume_ml:.2f} mL")

            if avg_volume_ml < 10:
                diagnosis = diagnosis_plans["small"]
            elif 10 <= avg_volume_ml < 30:
                diagnosis = diagnosis_plans["medium"]
            else:
                diagnosis = diagnosis_plans["large"]
            self.show3_label.setText(diagnosis)
        else:
            self.show2_label.setText(self.tr("无法计算出血量"))
            self.show3_label.setText(self.tr("无法提供诊断建议"))

        plt.figure(figsize=(10, 8))
        plt.bar(range(len(volume_ml)), volume_ml, color='skyblue')
        plt.xlabel('Patient Number')
        plt.ylabel('Bleeding Volume (mL)')
        plt.title('Bleeding Volume for All Patients')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig('calcut.png', dpi=300)
        plt.close()

        pixmap = QPixmap('calcut.png')
        pixmap = pixmap.scaled(self.show2_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.show2_label.setPixmap(pixmap)
        self.show2_label.setAlignment(Qt.AlignCenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    main_widget = MainWindow()
    main_widget.setWindowTitle("智慧脑 | 脑出血诊断分析软件")
    main_widget.show()
    sys.exit(app.exec_())
