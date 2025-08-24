import os
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QPixmap, QImage, QIcon, QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QListWidget, QToolBar, QFileDialog, QPushButton, QListWidgetItem, QApplication, QListView, QWidget, QHBoxLayout, QAction, QVBoxLayout, QLabel, QFrame, QDesktopWidget
import qdarkstyle
import matplotlib.pyplot as plt
import numpy as np
import cv2
import sys

# 得到一个成员是图像文件路径的列表
def load_image_paths(directory):
    filenames = os.listdir(directory)
    image_paths = []
    for file in filenames:
        if file.endswith((".png", ".jpg")):
            image_paths.append(os.path.join(directory, file))
    return image_paths

# 定义缩略图列表部分，继承自QListWidget。每一个QListWidgetItem可以设置QIcon图片和文本
class ImageListWidget(QListWidget):
    def __init__(self):
        super(ImageListWidget, self).__init__()
        self.setFlow(QListView.Flow(1))
        self.setIconSize(QSize(180, 120))

    def add_image_items(self, image_paths=[]):
        for img_path in image_paths:
            if os.path.isfile(img_path):
                img_name = os.path.basename(img_path)
                item = QListWidgetItem(QIcon(img_path), img_name)
                self.addItem(item)

# 布局窗体控件
class MainWindow(QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()
        try:#抛异常
            self.initUI()
        except Exception as e:
            print(f"Error during initialization: {e}")

    def initUI(self):
        # 设置窗口大小为桌面大小
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        self.resize(screen_width, screen_height)

        # 部件设置
        # 定义一个顶部菜单栏，初始化
        self.tool_bar = QToolBar(self)
        self.init_toolbar()

        # 第1个frame，显示列表和两个按钮
        self.buttonlist_frame = QFrame(self)
        self.buttonlist_frame.setStyleSheet(u"border: 1px solid blue;")
        self.list_widget = ImageListWidget()
        self.image_button = QPushButton("导入原图", self.buttonlist_frame)
        self.image_paths = []
        self.currentImgIdx = 0
        self.currentImg = None

        # 第2个frame，放叠加图
        self.handle_frame = QFrame(self)
        self.handle_frame.setStyleSheet(u"border: 1px solid blue;")
        self.overlay_label = QLabel(self.handle_frame)
        self.overlay_label.setText("Hi!put your mixed picture here!")
        self.overlay_label.setStyleSheet(u"border: 1px solid blue;")
        self.overlay_pixmap = QPixmap(self.overlay_label.size())
        self.overlay_pixmap.fill(Qt.transparent)
        self.overlay_label.setPixmap(self.overlay_pixmap)

        # 第3个frame，把三个诊断结果放在一起
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

        #页面布局
        #把整个页面layout划分成菜单栏和main_layout
        self.layout = QVBoxLayout(self)  # 使用 QVBoxLayout 使工具栏在顶部
        self.layout.addWidget(self.tool_bar)
        self.main_layout = QHBoxLayout(self)
        self.layout.addLayout(self.main_layout)
        # main_layout里面添加buttonlist_frame,handle_frame,diagnosis_frame
        self.main_layout.addWidget(self.buttonlist_frame)
        self.main_layout.addWidget(self.handle_frame)
        self.main_layout.addWidget(self.diagnosis_frame)
        # 在第1个frame里添加垂直布局
        self.vertical_layout = QVBoxLayout(self.buttonlist_frame)
        self.vertical_layout.addWidget(self.list_widget)
        self.vertical_layout.addWidget(self.image_button)
        # 在第2个frame里添加垂直布局
        self.vertical_layout = QVBoxLayout(self.handle_frame)
        self.vertical_layout.addWidget(self.overlay_label)
        # 在第3个frame里添加垂直布局
        self.vertical_layout = QVBoxLayout(self.diagnosis_frame)
        self.vertical_layout.addWidget(self.show1_label)
        self.vertical_layout.addWidget(self.show2_label)
        self.vertical_layout.addWidget(self.show3_label)
        # 设置3个主要大框架的大小策略，分别占据桌面大小的1/6, 1/2, 1/3
        self.buttonlist_frame.setMaximumHeight(screen_height)
        self.handle_frame.setMaximumHeight(screen_height)
        self.diagnosis_frame.setMaximumHeight(screen_height)
        self.buttonlist_frame.setMaximumWidth(screen_width // 6)
        self.handle_frame.setMaximumWidth(screen_width // 2)
        self.diagnosis_frame.setMaximumWidth(screen_width // 3)
        # 其中list占6/9,按钮占1/9
        self.list_widget.setMaximumHeight(screen_height // 9 * 6)
        self.image_button.setMaximumHeight(screen_height // 9)
        self.image_button.setMaximumWidth(screen_width // 6)

        # 信号与连接
        self.list_widget.itemSelectionChanged.connect(self.showImage)
        self.list_widget.itemSelectionChanged.connect(self.sepration)
        self.list_widget.itemSelectionChanged.connect(self.parameter)
        self.list_widget.itemClicked.connect(self.diagnosis)
        #self.list_widget.itemSelectionChanged.connect(self.show3d_picture)
        self.image_button.clicked.connect(self.choose_folder)

        predict_dir = r"data/predict"
        self.predict_paths = load_image_paths(predict_dir)
        mask_dir = r"data/mask"
        self.mask_paths = load_image_paths(mask_dir)

        self.drawing = False
        self.last_point = QPoint()

    def init_toolbar(self):
        self.tool_bar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # 创建一个包含图标和文本的QWidget
        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_label = QLabel()
        width = 60
        logo_label.setPixmap(QPixmap('icons/logo.jpg').scaled(width, width))  # 设置图标路径和大小
        text_label = QLabel('智慧脑 | 脑部CT平扫 ')
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(text_label)
        text_label.setFont(QFont("Helvetica", 16))  # 更改字体为 Arial，大小为 12，加粗
        text_label.setStyleSheet("color: white;")  # 更改文本颜色为蓝色
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_widget.setLayout(logo_layout)

        # 将自定义的QWidget添加到工具栏
        self.tool_bar.addWidget(logo_widget)

        home_action = QAction(QIcon('icons/home.png'), '主页', self)
        list_action = QAction(QIcon('icons/list.png'), '菜单', self)
        edit_action = QAction(QIcon('icons/edit.png'), '编辑', self)
        zoomin_action = QAction(QIcon('icons/zoom-in.png'), '放大', self)
        zoomout_action = QAction(QIcon('icons/zoom-out.png'), '缩小', self)
        chevronsup_action = QAction(QIcon('icons/chevrons-up.png'), '上一张', self)
        chevronsdown_action = QAction(QIcon('icons/chevrons-down.png'), '下一张', self)
        help_action = QAction(QIcon('icons/help.png'), '帮助', self)
        clear_action = QAction(QIcon('icons/clear.png'), '清屏', self)

        self.tool_bar.addAction(home_action)
        self.tool_bar.addAction(list_action)
        self.tool_bar.addAction(edit_action)
        self.tool_bar.addAction(zoomin_action)
        self.tool_bar.addAction(zoomout_action)
        self.tool_bar.addAction(chevronsup_action)
        self.tool_bar.addAction(chevronsdown_action)
        self.tool_bar.addAction(help_action)
        self.tool_bar.addAction(clear_action)

        edit_action.triggered.connect(self.edit)
        clear_action.triggered.connect(self.clear_drawing)

    def choose_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图像文件夹", os.getcwd())
        if folder_path:
            img_paths = [os.path.join(folder_path, filename) for filename in os.listdir(folder_path) if
                         filename.endswith((".png", ".jpg"))]
            self.list_widget.add_image_items(img_paths)
            self.image_paths = img_paths

    def cv_image_to_qimage(self, cv_image):
        height, width, channel = cv_image.shape
        bytes_per_line = 3 * width
        q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return q_image

    def showImage(self):
        self.currentImgIdx = self.list_widget.currentIndex().row()
        if self.currentImgIdx in range(len(self.image_paths)):
            self.currentImg = QPixmap(self.image_paths[self.currentImgIdx]).scaled(self.show1_label.width(),
                                                                                   self.show1_label.height())
            self.show1_label.setPixmap(self.currentImg)

    def sepration(self):
        self.currentImgIdx = self.list_widget.currentIndex().row()
        if self.currentImgIdx in range(len(self.image_paths)):
            img_path = self.image_paths[self.currentImgIdx]
            predict_path = self.predict_paths[self.currentImgIdx]
            image = cv2.imread(img_path)
            predict = cv2.imread(predict_path, cv2.IMREAD_GRAYSCALE)
            predict_3d = cv2.cvtColor(predict, cv2.COLOR_GRAY2BGR)
            overlay = cv2.addWeighted(image, 0.7, predict_3d, 0.3, 0)

            contours, hierarchy = cv2.findContours(predict, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, (255, 0, 0), 1)
            total_area = 0
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)
                total_area += area

            actual_area = total_area * 10 * 10 / 512 / 512
            print(actual_area)

            q_image = self.cv_image_to_qimage(overlay)
            pixmap = QPixmap.fromImage(q_image)
            pixmap = pixmap.scaled(self.overlay_label.width(), self.overlay_label.height())
            self.overlay_label.setPixmap(pixmap)

    def parameter(self):#分割并计算参数
        self.currentImgIdx = self.list_widget.currentIndex().row()
        if self.currentImgIdx in range(len(self.mask_paths)):
            predict_path = self.predict_paths[self.currentImgIdx]
            mask_path = self.mask_paths[self.currentImgIdx]
            # print(f"mask='{mask_name}', image='{image_name}'")#检验下是否串了
            predict = cv2.imread(predict_path)
            mask = cv2.imread(mask_path)
            # 将图像转换为二进制数组
            predict_image = np.array(predict, dtype=bool)
            mask_image = np.array(mask, dtype=bool)
            # 计算True Positive（TP）
            tp = np.sum(np.logical_and(predict_image, mask_image))
            # 计算True Negative（TN）
            tn = np.sum(np.logical_and(np.logical_not(predict_image), np.logical_not(mask_image)))
            # 计算False Positive（FP）
            fp = np.sum(np.logical_and(predict_image, np.logical_not(mask_image)))
            # 计算False Negative（FN）
            fn = np.sum(np.logical_and(np.logical_not(predict_image), mask_image))
            # 计算IOU（Intersection over Union）
            iou = tp / (tp + fn + fp + 1e-7)
            # 计算Dice Coefficient（Dice系数）
            dice_coefficient = 2 * tp / (2 * tp + fn + fp + 1e-7)
            # 计算Accuracy（准确率）
            accuracy = (tp + tn) / (tp + fp + tn + fn + 1e-7)
            # 计算precision（精确率）
            precision = tp / (tp + fp + 1e-7)
            # 计算recall（召回率）
            recall = tp / (tp + fn + 1e-7)
            # 计算Sensitivity（敏感度）
            sensitivity = tp / (tp + fn + 1e-7)
            # 计算F1-score
            f1 = 2 * (precision * recall) / (precision + recall + 1e-7)
            # 计算Specificity（特异度）
            specificity = tn / (tn + fp + 1e-7)

            metrics = ['IOU', 'Dice Coefficient', 'Accuracy', 'Precision', 'Recall', 'Sensitivity', 'F1-score', 'Specificity']
            values = [iou, dice_coefficient, accuracy, precision, recall, sensitivity, f1, specificity]
            x = np.arange(len(metrics))
            y = values
            plt.figure(figsize=(8, 7))
            plt.bar(x, y, color='skyblue')
            plt.title('Comparison of Evaluation Metrics')
            plt.xticks(x, metrics, rotation=45)
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            plt.tight_layout()
            plt.savefig('evaluation_metrics.png')
            plt.close() # 关闭图表，防止显示在界面上
            pixmap = QPixmap('evaluation_metrics.png')
            pixmap = pixmap.scaled(self.show1_label.width(), self.show1_label.height())
            self.show1_label.setPixmap(pixmap)

    def diagnosis(self, item):#计算出血量并给出诊断方案
        diagnosis_plans = {
            "small": "这是一个轻度脑出血，建议进行轻度观察和监测，可以保守治疗,并采用降温毯、降温头盔等，进行全身、头部局部降温，可以减轻脑水肿，促进神经功能缺失恢复，改善患者预后。",
            "medium": "这是一个中度脑出血，可能需要进一步的检查和治疗中度脑出血，可以根据患者的生命体征，以及是否存在继续出血、出血量增加等现象，选择进行手术或保守治疗。",
            "large": "这是一个重度脑出血，需要立即采取措施，一般建议手术治疗，去除血肿，避免发生严重的后果，比如脑疝等，危及患者生命安全。通过治疗，同时加上控制血压的药物，可以避免脑出血复发。"
        }

        list = [613.3888888888889, 535.5416666666666, 2041.9736842105262, 628.1111111111111, 625.15, 212.5,
                1477.9166666666667, 140.1, 1306.95, 205.25, 2538.1785714285716, 6631.684210526316, 235.75,
                826.1666666666666, 506.1923076923077, 6013.875, 1023.7142857142857, 2428.4166666666665,
                386.40909090909093, 1.0, 956.5454545454545, 2550.5666666666666, 38.75, 567.3333333333334, 965.0,
                1104.25, 401.92857142857144, 1610.6666666666667, 1038.0833333333333, 1026.0625, 849.875,
                821.6428571428571, 714.9090909090909, 274.5, 4990.791666666667, 681.0555555555555]
        num_images = [9, 12, 19, 9, 10, 2, 12, 5, 10, 2, 14, 19, 2, 6, 13, 16, 14, 12, 11, 1, 11, 15, 2, 6, 4, 2, 7, 12,
                      6, 8, 4, 7, 11, 4, 12, 9]
        thickness_mm = 5
        volume_mm3 = [area * thickness_mm for area in list]
        volume_ml = [volume / 1000 for volume in volume_mm3]

        current_row = self.list_widget.currentRow()
        print(current_row)# 打印平均出血面积列表
        max_images = num_images[0]
        count = 0
        if current_row > 0:
            # 提取元组中的名字部分
            for avg, num_img in zip(volume_ml, num_images):
                if (current_row + 1) <= max_images:
                    self.show2_label.setText(str(avg))
                    if avg < 10:
                        diagnosis = diagnosis_plans["small"]
                    elif 10 <= avg < 30:
                        diagnosis = diagnosis_plans["medium"]
                    else:
                        diagnosis = diagnosis_plans["large"]
                    self.show3_label.setText(diagnosis)
                    break
                else:
                    max_images += num_img
            plt.bar(range(len(volume_ml)), volume_ml, color='skyblue')
            plt.xlabel('Patient Number')
            plt.ylabel('Bleeding Volume (mL)')
            plt.savefig('calcut.png')
            plt.close()
            pixmap = QPixmap('calcut.png')
            pixmap = pixmap.scaled(self.show2_label.width(), self.show2_label.height())
            self.show2_label.setPixmap(pixmap)

    def edit(self):
        self.overlay_label.setMouseTracking(True)
        self.overlay_label.mousePressEvent = self.start_drawing
        self.overlay_label.mouseMoveEvent = self.keep_drawing
        self.overlay_label.mouseReleaseEvent = self.stop_drawing

    def start_drawing(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()

    def keep_drawing(self, event):
        if event.buttons() and Qt.LeftButton and self.drawing:
            painter = QPainter(self.overlay_pixmap)
            pen = QPen(Qt.red, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.overlay_label.setPixmap(self.overlay_pixmap)
            self.overlay_label.update()

    def stop_drawing(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False

    def clear_drawing(self):
        self.overlay_pixmap.fill(Qt.transparent)
        self.overlay_label.setPixmap(self.overlay_pixmap)
        self.overlay_label.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    main_widget = MainWindow()
    main_widget.setWindowTitle("脑出血诊断")
    main_widget.show()
    sys.exit(app.exec_())
