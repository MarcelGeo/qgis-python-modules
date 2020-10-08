from qgis.core import QgsWkbTypes , QgsExpression, QgsFeatureRequest, QgsRaster, QgsFields, QgsField, QgsGeometry, QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsFeature, QgsCoordinateTransform, QgsVectorLayer, QgsRasterLayer, QgsDistanceArea, QgsPoint, QgsSpatialIndex
import qgis.analysis
import qgis.utils
import os

def getPath(source, name):
    source, suffix = os.path.splitext(source) # get suffix and path to file
    return source + name

def createEmptyVectorLayer(path, formatDriver, fields=None, srcCrs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId), shape=QgsWkbTypes.Polygon, encoding="UTF-8"):
    """
    Create empty vector layer.
    """
    validDriver = False
    drivers = QgsVectorFileWriter.ogrDriverList()
    for driver in drivers:
        validDriver = driver.longName == formatDriver
    if not formatDriver:
        print("Not applicable formatDriver" + str(drivers))
        return False
    writer = QgsVectorFileWriter(path, encoding, fields, shape, srcCrs, formatDriver)
    if writer.hasError() != QgsVectorFileWriter.NoError:
        print("Error when creating shapefile: ", writer.hasError())
        del writer
        return False
    return writer

def activeLayersIterator():
    canvas = qgis.utils.iface.mapCanvas()
    layers = canvas.layers()
    for layer in layers:
        yield layer.name(), layer

def removeAttributesFromLayer(inputlayer, fieldsToRemoveName, name="REMOVED", dataProvider = "ESRI Shapefile"):
    outpath = getPath(inputlayer.source(), name)
    fields = inputlayer.fields()
    newfields = QgsFields()
    for field in fields:
        toremove = False
        for remove in fieldsToRemoveName:
            if field.name() == remove:
                toremove = True
                break
        if not toremove:
            newfields.append(field)
    output = createEmptyVectorLayer(outpath, dataProvider, newfields, inputlayer.crs(), inputlayer.wkbType(), inputlayer.dataProvider().encoding())    
    if not output:
        return None, None
    return output, newfields
    
def removeAttributesFromLayers(fieldsToRemoveName, name="REMOVE", dataProvider = "ESRI Shapefile"):
    for layername, layer in activeLayersIterator():
        if not layer.type() < 1:
            continue
        provider = layer.dataProvider()
        if isinstance(layer, QgsVectorLayer):
            output, newfields = removeAttributesFromLayer(layer, fieldsToRemoveName, name, dataProvider)
            if output is None and newfields is None:
                print("Unable to create vector and fields")
            for feature in layer.getFeatures():
                attrs = feature.attributes()
                newattrs = []
                for index, attr in enumerate(attrs):
                    toremove = False
                    for remove in fieldsToRemoveName:
                        idx = feature.fieldNameIndex(remove)
                        if idx == index:
                            toremove = True
                            break
                    if not toremove:
                        newattrs.append(attr)
                featappend = QgsFeature(feature)
                print(newfields)
                featappend.setFields(newfields)
                featappend.setAttributes(newattrs)
                output.addFeature(featappend)
            del output