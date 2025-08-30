import os
import sys
import itk
import vtk

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSlider, QApplication
from PyQt5.QtCore import Qt

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersGeneral import vtkDiscreteMarchingCubes
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer


class VTK3DViewer(QDialog):
    """
    Qt + VTK 三维窗口
    - 底部横向 slider：绕竖轴 (Azimuth)
    - 右侧竖向 slider：绕横轴 (Elevation)
    """
    def __init__(self, nifti_file, w=1000, h=800, parent=None):
        super().__init__(parent)

        # ✅ 标题栏样式
        self.setWindowFlags(Qt.Window |
                            Qt.WindowMinimizeButtonHint |
                            Qt.WindowMaximizeButtonHint |
                            Qt.WindowCloseButtonHint)

        self.setWindowTitle("3D 出血区域模型")
        self.resize(w, h)

        # --- 布局：上面 VTK + 右边竖条；下面横条 ---
        main = QVBoxLayout(self)
        top = QHBoxLayout()
        main.addLayout(top, stretch=1)

        # VTK 小部件
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        top.addWidget(self.vtk_widget, stretch=1)

        # 右侧竖向滑条
        self.slider_elev = QSlider(Qt.Vertical, self)
        self.slider_elev.setRange(-180, 180)
        self.slider_elev.setValue(0)
        self.slider_elev.setSingleStep(1)
        self.slider_elev.setPageStep(10)
        self.slider_elev.setFixedWidth(30)
        top.addWidget(self.slider_elev)

        # 底部横向滑条
        self.slider_azi = QSlider(Qt.Horizontal, self)
        self.slider_azi.setRange(-180, 180)
        self.slider_azi.setValue(0)
        self.slider_azi.setSingleStep(1)
        self.slider_azi.setPageStep(10)
        self.slider_azi.setFixedHeight(30)
        main.addWidget(self.slider_azi)

        # --- VTK 场景 ---
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        self._setup_scene(nifti_file)

        # 保存上一次滑条值
        self._prev_azi = self.slider_azi.value()
        self._prev_elev = self.slider_elev.value()

        # 事件绑定
        self.slider_azi.valueChanged.connect(self._on_azimuth_changed)
        self.slider_elev.valueChanged.connect(self._on_elevation_changed)

        # 初始化
        self.show()
        self.interactor.Initialize()
        self.vtk_widget.GetRenderWindow().Render()

    def _setup_scene(self, nifti_file):
        if not os.path.exists(nifti_file):
            raise FileNotFoundError(f"NIfTI 不存在: {nifti_file}")

        # 读取 NIfTI
        itk_img = itk.imread(filename=nifti_file)
        arr = itk.array_from_image(itk_img)
        vmax = arr.max()
        print(f"[DEBUG] nii 值范围: {arr.min()} ~ {arr.max()}")

        vtk_img = itk.vtk_image_from_image(l_image=itk_img)

        # 轮廓提取
        contour = vtkDiscreteMarchingCubes()
        contour.SetInputData(vtk_img)

        # 自动选择等值面阈值
        if vmax > 1:
            contour.SetValue(0, 255)
        else:
            contour.SetValue(0, 1)

        contour.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(contour.GetOutputPort())
        mapper.ScalarVisibilityOff()

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)  # 红色

        colors = vtkNamedColors()
        self.renderer.SetBackground(colors.GetColor3d("black"))
        self.renderer.AddActor(actor)

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.vtk_widget.GetRenderWindow().Render()

        # 保存
        self.actor = actor
        self.camera = self.renderer.GetActiveCamera()

        # 鼠标交互风格
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        # 调试信息
        print("Actor bounds:", actor.GetBounds())

    def _on_azimuth_changed(self, val):
        delta = val - self._prev_azi
        if delta != 0:
            self.camera.Azimuth(delta)
            self.renderer.ResetCameraClippingRange()
            self.vtk_widget.GetRenderWindow().Render()
            self._prev_azi = val

    def _on_elevation_changed(self, val):
        delta = val - self._prev_elev
        if delta != 0:
            self.camera.Elevation(delta)
            self.camera.OrthogonalizeViewUp()
            self.renderer.ResetCameraClippingRange()
            self.vtk_widget.GetRenderWindow().Render()
            self._prev_elev = val


# 保持和 windowmain 调用一致
def show3d(image_name, w=800, h=600):
    nifti = os.path.join("./mask_nii/", image_name.split("_")[0] + ".nii.gz")
    dlg = VTK3DViewer(nifti, w=w, h=h, parent=None)
    dlg.exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    show3d("049_15.png", 800, 600)
    sys.exit(app.exec_())
