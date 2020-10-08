from scipy.spatial import Delaunay
import matplotlib.tri as tri
import numpy as np
from qgis.core import QgsPoint, QgsGeometry

class DelaunayPoints(object):
    def __init__(self, qgs_points):
        self.np_qgs_points = np.array(qgs_points)
        self.triangles = None
    
    def asQgsMultiPolygon(self):
        if self.triangles is not None:
            multi = []
            if self.triangles is not None:
                if hasattr(self.triangles, 'simplices'):
                    triangles = self.triangles.simplices
                else:
                    triangles = self.triangles.triangles
            else:
                return None
            polygons = self.np_qgs_points[triangles]
            for polygon in polygons:
                part = []
                ring = []
                for vertice in polygon:
                    ring.append(QgsPoint(vertice[0], vertice[1]))
                part.append(ring)
                multi.append(part)
            return multi
                    
                    
    def executeScipy(self):
        try:
            self.triangles = Delaunay(self.np_qgs_points)
        except:
            raise Exception("Change parameters or QHull error")
        return self.asQgsMultiPolygon()
    
    def executeMatplotlib(self):
        try:
            self.triangles = tri.Triangles(self.np_qgs_points[:, 0], self.np_qgs_points[:, 1])
        except:
            self.triangles = None
            raise Exception("Change parameters to Delaunay, Not success.")
        return self.asQgsMultiPolygon()