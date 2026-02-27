try:
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCC.Core.Geom import Geom_BSplineSurface
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCC.Core.IFSelect import IFSelect_RetDone
    OCC_AVAILABLE = True
except Exception:
    OCC_AVAILABLE = False


class OCCExporter:

    def export_bspline(self, surface, filename="model.step"):
        face = BRepBuilderAPI_MakeFace(surface).Face()
        writer = STEPControl_Writer()
        writer.Transfer(face, 1)
        status = writer.Write(filename)
        return status == IFSelect_RetDone
