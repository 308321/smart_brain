import itk
import vtk
import os
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersGeneral import vtkDiscreteMarchingCubes
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer, \
    vtkRenderWindow, vtkRenderWindowInteractor


def show_3d_nifti_image(nifti_file_name, w, h):
    if not os.path.exists(nifti_file_name):
        raise FileNotFoundError(f"The file {nifti_file_name} does not exist.")

    # Read NIFTI file
    itk_img = itk.imread(filename=nifti_file_name)

    # Convert itk to vtk
    vtk_img = itk.vtk_image_from_image(l_image=itk_img)

    # Extract vtkImageData contour to vtkPolyData
    contour = vtkDiscreteMarchingCubes()
    contour.SetInputData(vtk_img)

    # Define colors, mapper, actor, renderer, renderWindow, renderWindowInteractor
    colors = vtkNamedColors()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(contour.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)

    renderer = vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(colors.GetColor3d("black"))

    renderWindow = vtkRenderWindow()

    renderWindow.SetSize(int(w), int(h))  # Ensure size parameters are integers
    renderWindow.AddRenderer(renderer)
    renderWindow.SetBorders(False)

    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.Initialize()

    # Get the screen size
    screen_width = renderWindowInteractor.GetRenderWindow().GetScreenSize()[0]
    screen_height = renderWindowInteractor.GetRenderWindow().GetScreenSize()[1]

    # Calculate position to center the window
    pos_x = (screen_width - w) // 2
    pos_y = (screen_height - h) // 2

    renderWindow.SetPosition(int(pos_x), int(pos_y))  # Center the window on the screen

    renderWindowInteractor.Start()


def show3d(image_name, w, h):
    image_name = image_name.split("_")[0] + ".nii.gz"
    show_3d_nifti_image(os.path.join("./mask_nii/", image_name), int(w), int(h))
    print(os.path.join("./mask_nii/", image_name))


if __name__ == '__main__':
    show3d("049_15.png", 800, 600)  # Example call with width and height
