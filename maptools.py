from qgis.core import QGis , QgsExpression, QgsFeatureRequest, QgsRaster, QgsMapLayerRegistry, QgsFields, QgsField, QgsGeometry, QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsFeature, QgsCoordinateTransform, QgsVectorLayer, QgsRasterLayer, QgsDistanceArea, QgsWKBTypes, QgsPoint, QgsSpatialIndex
import qgis.analysis
import qgis.utils
import qgscustom
from PyQt4.QtCore import QVariant, QPyNullVariant, QTimer
import os
import processing
import math
from numpy import mean as npmean
import numpy as np
import delaunay
import time
import sys
import noa
import texttoolsv2
import stats
reload(stats)
import math

def maptools_Stats_average(vlist):
    try:
        mean = npmean(vlist)
    except:
        return None
    return mean

maptools_Stats = {
"AVG": maptools_Stats_average
}

#errors

QgsGeometryaddPart_errors = {0: "success", 
1: "not a multipolygon", 
2: "ring is not a valid geometry", 
3: "new polygon ring not disjoint with existing polygons of the feature"}

# q variant types

def toQVariant(value):
    if isinstance(value, (str, unicode)):
        return QVariant.String
    elif isinstance(value, (int)):
        return QVariant.Int
    elif isinstance(value, float):
        return QVariant.Double
    else:
        return QVariant.Invalid

#paths

def getPath(source, name):
    source, suffix = os.path.splitext(source) # get suffix and path to file
    return source + name

# wkb types

def convertWKB(wkb, to3D = True, toOld = False):
    '''
    new: if False, False
    '''
    try:
        wkbT = QGis.fromOldWkbType(wkb)
    except:
        wkbT = wkb
    if to3D and not QgsWKBTypes.hasZ(wkbT):
        wkbT = QgsWKBTypes.addZ(wkbT)
    if toOld:
        wkbT = QGis.fromNewWkbType(wkbT)
    print wkbT
    return wkbT

# vectors

def createEmptyVectorLayer(path, formatDriver, fields=None, srcCrs = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId), shape=QGis.WKBPolygon, encoding="UTF-8"):
    """
    Create empty vector layer.
    """
    drivers = QgsVectorFileWriter.ogrDriverList().values()
    if formatDriver not in drivers:
        print "Not applicable formatDriver" + str(drivers)
        return False
    writer = QgsVectorFileWriter(path, encoding, fields, shape, srcCrs, formatDriver)
    if writer.hasError() != QgsVectorFileWriter.NoError:
        print "Error when creating shapefile: ", writer.hasError()
        del writer
        return False
    return writer

def filterRingsToHoles(to, rings, minArea, maxArea, holesfw, *holesFeatureAttributes):
    codes = []
    for ring in rings:
        ringFeature = QgsFeature()
        ring_polygon = QgsGeometry.fromPolygon([ring])
        area = ring_polygon.area()
        if area <= maxArea and area >= minArea: # add to holes
            ringFeature.setGeometry(ring_polygon)
            newfieldsvalues = [value for value in holesFeatureAttributes] # add tuple of attributes from parameter to array
            ringFeature.setAttributes(newfieldsvalues)
            holesfw.addFeature(ringFeature)
        else: # not in treshold interval, write ring to polygon (valid holes)
            code = to.addRing(ring)
            codes.append(code)
    return to, codes
# layers

def addVectorLayer(path, name, dataProvider="ogr"):
    vec = QgsVectorLayer(path, name, dataProvider)
    if vec.isValid():
        QgsMapLayerRegistry.instance().addMapLayer(vec)
        return vec
    else:
        return False

def layersIterator():
    layers = QgsMapLayerRegistry.instance().mapLayers()
    for layer in layers:
        yield layer, layers

def activeLayersIterator():
    canvas = qgis.utils.iface.mapCanvas()
    layers = canvas.layers()
    for layer in layers:
        yield layer.name(), layer

def transformGeometry(geometry, srcCrs, destCrs=QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId)):
    """
    @param geometry QgsGeometry
    """
    xform = QgsCoordinateTransform(srcCrs, destCrs)
    transformed = geometry.transform(xform)
    return transformed

def calculateArea(geom, layerCrs):
    """
    Calculate area in square km for Geographic and Projected systems.
    Dont recalculate units into meters (if feet)
    """
    area = 0
    if layerCrs.geographicFlag(): # if geographic system, need to calculate in meters
        calculator = QgsDistanceArea()
        calculator.setEllipsoid(layerCrs.ellipsoidAcronym())
        calculator.setEllipsoidalMode(True)
        calculator.computeAreaInit()
        if geom.isMultipart() is False: # if only simple polygon, calculate only for this
            polyg = geom.asPolygon() # transform to list of points
            if len(polyg) > 0:
                area = calculator.measurePolygon(polyg[0])
        else: # is multipart
            multi = geom.asMultiPolygon()
            for polyg in multi:
                area = area + calculator.measurePolygon(polyg[0])
    else:
        area = geom.area()
    return round(area/1e6, 2)
    
def getFirstOccurence():
    raster = None
    vector = None
    for layername, layer in activeLayersIterator():
        if isinstance(layer, QgsRasterLayer) and raster is None:
            raster = layer
        elif isinstance(layer, QgsVectorLayer) and vector is None:
            vector = layer
        if vector is not None and raster is not None:
            break
    return vector, raster

# PUBLIC
def layerFromLayerExtent(name="BBOX", dataProvider="ESRI Shapefile"):
    fieldsarr = [QgsField("name", QVariant.String), QgsField("xmax" ,QVariant.Double), QgsField("xmin" ,QVariant.Double), QgsField("ymax" ,QVariant.Double), QgsField("ymin" ,QVariant.Double)] 
    fields = QgsFields()
    for fild in fieldsarr:
        fields.append(fild)
    for layername, layer in activeLayersIterator():
        path = getPath(layer.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, fields, layer.crs(), QGis.WKBPolygon, layer.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        extent = layer.extent()
        extentpolyg = QgsGeometry.fromWkt(extent.asWktPolygon())
        print layername
        fet = QgsFeature()
        fet.setGeometry(extentpolyg)
        fet.setAttributes([layername ,extent.xMaximum(), extent.xMinimum(), extent.yMaximum(), extent.yMinimum()])
        output.addFeature(fet)
        del output
        
def addLayerFromLayerExtent(path, name="BBoxes", formatDriver="ESRI Shapefile"):
    """
    Create layer with geometry of active layers extents.
    @param path path of new .shp
    """
    fieldsarr = [QgsField("name", QVariant.String), QgsField("xmax" ,QVariant.Double), QgsField("xmin" ,QVariant.Double), QgsField("ymax" ,QVariant.Double), QgsField("ymin" ,QVariant.Double), QgsField("area", QVariant.Double)] 
    fields = QgsFields()
    for fild in fieldsarr:
        fields.append(fild)
    newvector = createEmptyVectorLayer(path, formatDriver, fields)
    if newvector:
        for layername, layer in activeLayersIterator():
            refcrs = layer.crs()
            extent = layer.extent()
            extentpolyg = QgsGeometry.fromWkt(extent.asWktPolygon())
            area = calculateArea(extentpolyg, refcrs)
            print layername + " - " + str(area)
            fet = QgsFeature()
            transformed = transformGeometry(extentpolyg, refcrs)
            if transformed == 0:
                fet.setGeometry(extentpolyg)
            else:
                print "its not possible to transform extent of layer to EPSG:4326"
                continue
            fet.setAttributes([layername ,extent.xMaximum(), extent.xMinimum(), extent.yMaximum(), extent.yMinimum(), area])
            newvector.addFeature(fet)
        added = addVectorLayer(path, name)
        if added:
            "Vector Layer added."
        else:
            "Its not possible to add vector layer to map canvas"
    else:
        print "IS not possible to creaate new vector (exists?)"
    del newvector
    
#    maptools.addLayerFromLayerExtent("C:\\marcel\\KML\\surveysbboxes.kml")

def transformActiveVectorLayers(destCrs, name="TRANSFORMED", dataProvider="ESRI Shapefile"):
    """
    copy all active layers and add spcifed name to path of layer. Not for memory layers.
    @param destCrs {String} WKT, PROJ4, EPSG: ... 
    """
    count = 0
    for layername, layer in activeLayersIterator():
        provider= layer.dataProvider()
        if layer.type() < 1 and provider.name() != "memory" and layer.hasGeometryType(): #if vector
            source, suffix = os.path.splitext(layer.source()) # get suffix and path to file
            path = source + name
            print path
            destCrsS = QgsCoordinateReferenceSystem(destCrs)
            newvector = createEmptyVectorLayer(path, dataProvider, layer.pendingFields(), destCrsS, layer.wkbType(), layer.dataProvider().encoding())
            if newvector:
                srcCrs = layer.crs()
                for feature in layer.getFeatures(): # iter over features in active layer
                    fet = QgsFeature(feature)
                    transform = transformGeometry(fet.geometry(), srcCrs, destCrsS)
                    if transform > 0:
                        print "not possible to transform geometry of feature" + feature.id() + "in " + layername
                        continue
                    newvector.addFeature(fet)
#                added = addVectorLayer(path, name + layername)
#                if added:
                print "Vector layer " + layername + " transformed"
                count += 1
#                else:
#                    print "Vector " + path + "not found."
            else:
                print "IS not possible to creaate new vector (exists?)"
            del newvector
            print "Count of transformed layers: " + str(count)
        else:
            print layername + "is not valid Vector"
            
def drapeAndAddZAttribute():
    invector, inraster = getFirstOccurence()
    if invector is None or inraster is None:
        raise Exception("In map canvas arent vector or raster")
    processing.runalg("grass:v.drape", invector, inraster, 0, None, None, -9999999, None, None, None, 1, "C:\\marcel\\draped.shp")

def extractZFromRaster(name="EXTRACTED", attributeFieldName="TWT_SEIS", fieldType = QVariant.Double, band=1, precision=6, invert=True, dataProvider="ESRI Shapefile"):
    invector, inraster = getFirstOccurence()
    path = getPath(invector.source(), name)
    newfields = QgsFields(invector.pendingFields())
    newfields.append(QgsField(attributeFieldName, fieldType))
    if invector.type() < 1 and invector.dataProvider().name() != "memory" and invector.hasGeometryType(): #if vector
         layerWkbType = invector.wkbType()
         if layerWkbType == QGis.WKBPoint or layerWkbType == QGis.WKBPoint25D:
            newvector = createEmptyVectorLayer(path, dataProvider, newfields, invector.crs(), invector.wkbType(), invector.dataProvider().encoding())
            if newvector:
                features = invector.getFeatures()
                for feature in features:
                    oldfeatureattr = feature.attributes()
                    newfeature = QgsFeature(feature)
                    oldgeom = feature.geometry().asPoint()
#                newfeature.setGeometry(QgsGeometry.fromPoint(oldgeom))
                    newfeature.setFields(newfields)
                    ident = inraster.dataProvider().identify(oldgeom, QgsRaster.IdentifyFormatValue)
                    result = ident.results()
                    value = result[band]
                    if value is not None:
                        if fieldType == QVariant.Double:
                            value = round(value, precision)
                        if invert:
                            value = value * -1
                        oldfeatureattr.append(value)
                    newfeature.setAttributes(oldfeatureattr)
                    newvector.addFeature(newfeature)
            else:
                print "IS not possible to creaate new vector "+ path + "(exists?)"
         else:
                print invector.name() + " is not point Vector"
    else:
        print invector.name() + "is not valid vector"
                    
                

def fillHoles(minArea, maxArea,output = "FILLEDHOLES" , holesname="HOLES", dataProvider="ESRI Shapefile"):
    fieldsarr = [QgsField("polygonId", QVariant.Int)] 
    fieldsholes = QgsFields()
    holes = None
    filled = None
    for fild in fieldsarr:
        fieldsholes.append(fild)
    for layername, layer in activeLayersIterator():
        if not layer.type() < 1:
            continue
        provider = layer.dataProvider()
        if provider.name() != "memory" and layer.hasGeometryType(): #if vector
            layerWkbType = layer.wkbType()
            if layerWkbType == QGis.WKBPolygon or layerWkbType == QGis.WKBMultiPolygon or layerWkbType ==  QGis.WKBPolygon25D or layerWkbType == QGis.WKBMultiPolygon25D:
                destCrs = layer.crs()
                features = layer.getFeatures()
                lsource = layer.source()
                filledpath = getPath(lsource, output + "_" + str(minArea) + "_" + str(maxArea))
                holespath = getPath(lsource, holesname  + "_" + str(minArea) + "_" + str(maxArea))
                holes = createEmptyVectorLayer(holespath, dataProvider, fieldsholes, destCrs, layer.wkbType(), provider.encoding())
                filled = createEmptyVectorLayer(filledpath, dataProvider, layer.pendingFields(), destCrs, layer.wkbType(), provider.encoding())
                if filled and holes:
                    for feature in features:
                        filledFeature = QgsFeature(feature)
                        geom = feature.geometry()
                        if not geom.isMultipart():
                            polygon = geom.asPolygon()
                            mainring = QgsGeometry.fromPolygon([polygon[0]]) # add first main ring polygon
                            filteredpolygon, ringscodes = filterRingsToHoles(mainring, polygon[1:], minArea, maxArea, holes, filledFeature.id())
                            filledFeature.setGeometry(filteredpolygon)
                        else:
                            multipolyg = geom.asMultiPolygon()
                            print str(feature.id()) + " is multipart"
                            filledGeometry = filledFeature.geometry() # multipolygon
                            for polygon in multipolyg:
                                deleteParterror = filledGeometry.deletePart(0) # delete actual first part
                                if deleteParterror:
                                    part = QgsGeometry.fromPolygon([polygon[0]])
                                    filteredpart, ringscodes = filterRingsToHoles(part, polygon[1:], minArea, maxArea, holes, filledFeature.id())
                                    partcode = filledGeometry.addPartGeometry(filteredpart) # toggle actual part
                                    if partcode > 0:
                                        print "Part of polygon with index " + partindex + " is not valid added, error: " + QgsGeometryaddPart_errors[partcode]
                                else:
                                    print "Unable to delete part " + partindex + " from multipolygon with id " + filledFeature.id() 
                        filled.addFeature(filledFeature)
                    del holes
                    del filled
                    print "Created layer with filled holes " + filledpath
                    print "Created layer with holes " + holespath
                else:
                    print "IS not possible to creaate new vectors "+ holespath + "and" + filledpath +  "(exists?)"
            else:
                print layername + " is not polygonal valid Vector"
        else:
            layername + "is not valid vector"

def statsFromRasterToPolygon():
    invector, inraster = getFirstOccurence()
    zonalstats = qgis.analysis.QgsZonalStatistics(invector, inraster.source(), stats=qgis.analysis.QgsZonalStatistics.All)
    code = zonalstats.calculateStatistics(None)
    if code > 0:
        print "By calculating occured error " + code
    return code
    
# # selecting # #
def selectByGeometry(feature, selectFunction):
    pass

def addaptiveIntersectPrivate(layerGeometryType, intersectLayer, inputFeature, addaptive):
    output = []
    ingeom = inputFeature.geometry()
    for interf in intersectLayer.getFeatures():
        newfeature = QgsFeature(inputFeature)
        intersectgeom = interf.geometry()
        diffgeom = ingeom.difference(intersectgeom)
        intersection = ingeom.intersection(intersectgeom)
        if layerGeometryType == QGis.Line:
            if intersection.asPolyline() != [] or intersection.asMultiPolyline() != []:
                if not intersection.isEmpty(): # if is not empty after difference
#                                newfeature.setGeometry(intersection)
                                ## here filter for length of intersected
                    newfeature.setGeometry(intersection) # for default is intersection geometry
                    if intersection.isMultipart() and diffgeom.isMultipart(): # only for multiparts
                        diffpoly = diffgeom.asGeometryCollection()
                        for index, diff in enumerate(diffpoly):# for every line from difference
                            len = diff.length() # check length
                            if len < addaptive and intersection.touches(diff):
                                intersection.addPart(diff.geometry(), diff.type())
                        newfeature.setGeometry(intersection)
                    else:
                        len = diffgeom.length()
                        if len < addaptive and intersection.touches(diffgeom):
                            newfeature.setGeometry(QgsGeometry.unaryUnion([intersection, diffgeom]))
                    output.append(newfeature)
    return output

# # addaptive intersect # #

def addaptiveIntersect(inputLayer, intersectLayer, addaptive=50, name = "INTERSECTED", dataProvider = "ESRI Shapefile"):
    outputpath = getPath(inputLayer.source(), name)
    output = None
    layerGeometryType = inputLayer.geometryType()
    if inputLayer.type() < 1 and inputLayer.name() != "memory" and inputLayer.hasGeometryType() and intersectLayer.type() < 1 and intersectLayer.name() != "memory" and intersectLayer.hasGeometryType(): #if vector
        for feature in inputLayer.getFeatures():
            outputs = addaptiveIntersectPrivate(layerGeometryType, intersectLayer, feature, addaptive)
            if len(outputs) > 0: # if we have features
                if output is None:
                    firstWkb = convertWKB(outputs[0].geometry().wkbType(), False, True)
                    output = createEmptyVectorLayer(outputpath, dataProvider, inputLayer.pendingFields(), inputLayer.crs(), firstWkb, inputLayer.dataProvider().encoding())
                    if not output:
                        print "IS not possible to creaate new vectors "+ outputpath + "and(exists?)"
                        return None
                    print outputpath + " Created "
                for feat in outputs:
                    output.addFeature(feat)
    else:
        inputLayer.name() + " is not valid Vector"
    del output
    
def joinLayers(inputlayer, layer, index_field, name = "JOINED", attributeName = "J", fieldsNames = None, dataProvider = "ESRI Shapefile"):
    outpath = getPath(inputlayer.source(), name)
    inputfields = inputlayer.pendingFields()
    toappend = layer.pendingFields()
    reordered = []
    
    if fieldsNames is None:
        fieldsNames = [field.name() for field in toappend]
    
    nameoflayer = layer.name()
    
    indexlayer = inputlayer.fieldNameIndex(index_field)
    if indexlayer == -1:
        print index_field + " is not in inputlayer and layer"
        return None
    
    for fild in toappend:
        fildname = fild.name()
        if fildname in fieldsNames:
            reordered.append(fildname)
            fild.setName(unicode(attributeName + fildname))
            inputfields.append(fild)
    output = createEmptyVectorLayer(outpath, dataProvider, inputfields, inputlayer.crs(), layer.wkbType(), inputlayer.dataProvider().encoding())
    
    for infeat in inputlayer.getFeatures():
        in_value = infeat.attributes()[indexlayer]
        exp = QgsExpression(index_field + ' LIKE \'' + in_value + '\'')
        reqq = QgsFeatureRequest(exp)
        for layfeat in layer.getFeatures(reqq):
            attrs = infeat.attributes()
            featappend = QgsFeature(infeat)
            for layfield in reordered:
                attrs.append(layfeat.attribute(layfield))
            featappend.setFields(inputfields)
            featappend.setAttributes(attrs)
            output.addFeature(featappend)
    del output

def addAttributesToLayer(inputlayer, newFields, name="EXTENDED", dataProvider = "ESRI Shapefile"):
    outpath = getPath(inputlayer.source(), name)
    fields = inputlayer.pendingFields()
    newfields = QgsFields(fields)
    for newfield in newFields:
        newfields.append(newfield)
    output = createEmptyVectorLayer(outpath, dataProvider, newfields, inputlayer.crs(), convertWKB(inputlayer.wkbType(), False), inputlayer.dataProvider().encoding())
    if not output:
        return None, None
    return output, newfields
    
def removeAttributesFromLayer(inputlayer, fieldsToRemoveName, name="REMOVED", dataProvider = "ESRI Shapefile"):
    outpath = getPath(inputlayer.source(), name)
    fields = inputlayer.pendingFields()
    newfields = QgsFields()
    for field in fields:
        toremove = False
        for remove in fieldsToRemoveName:
            if field.name() == remove:
                toremove = True
                break
        if not toremove:
            newfields.append(field)
    output = createEmptyVectorLayer(outpath, dataProvider, newfields, inputlayer.crs(), convertWKB(inputlayer.wkbType(), False), inputlayer.dataProvider().encoding())    
    if not output:
        return None, None
    return output, newfields
    
def removeAttributesFromLayers(fieldsToRemoveName, name="REMOVE", dataProvider = "ESRI Shapefile"):
    for layername, layer in activeLayersIterator():
        if not layer.type() < 1:
            continue
        provider = layer.dataProvider()
        if layer.hasGeometryType():
            output, newfields = removeAttributesFromLayer(layer, fieldsToRemoveName, name, dataProvider)
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
                featappend.setFields(newfields)
                featappend.setAttributes(newattrs)
                output.addFeature(featappend)
            del output
                    

def findAttributesInLayersIterator(fieldsToFind):
    for layername, layer in activeLayersIterator():
        result = []
        fields = layer.pendingFields()
        for field in fields:
            if field.name() not in fieldsToFind:
                result.append(True)
            else:
                result.append(False)
        if False not in result:
            yield layer
            

def removeLayerFromLayerTree(fieldsToFind = []):
    for layer in findAttributesInLayersIterator(fieldsToFind):
        QgsMapLayerRegistry.instance().removeMapLayer(layer.id())

def findAttributesInLayers(fieldsToFind):
    for layername, layer in activeLayersIterator():
        fields = layer.pendingFields()
        for field in fields:
            if field.name() in fieldsToFind:
                print layername + " contains " + field.name()

def checkNullInAttributes(fieldsToFind):
    for layername, layer in activeLayersIterator():
        for field in fieldsToFind:
            for feature in layer.getFeatures():
                try:
                    name = feature.attribute(field)
                except:
                    print layername + " does not contain " + field
                    break
                
                if isinstance(name, QPyNullVariant):
                    print layername + " contains NODATA in field " + field
                    break


def addMetadataToLayer(inputlayer, name="METADATA", dataProvider = "ESRI Shapefile"):
    # use: addAttributesToLayer function
    outpath = getPath(inputlayer.source(), name)
    fields = inputlayer.pendingFields()
    metafields = [QgsField("xmax" ,QVariant.Double), QgsField("xmin" ,QVariant.Double), QgsField("ymax" ,QVariant.Double), QgsField("ymin" ,QVariant.Double), QgsField("area2", QVariant.Double)] 
    newfields = QgsFields(fields)
    for meta in metafields:
        newfields.append(meta)
    refcrs = inputlayer.crs()
    output = createEmptyVectorLayer(outpath, dataProvider, newfields, refcrs, convertWKB(inputlayer.wkbType(), False), inputlayer.dataProvider().encoding())
    if not output:
        print "IS not possible to creaate new vectors "+ outpath + "and(exists?)"
        return None
    for feature in inputlayer.getFeatures():
        featappend = QgsFeature(feature)
        
        attrs = featappend.attributes()
        featappend.setFields(newfields)
        geom = featappend.geometry()
        extent = geom.boundingBox()
        area = calculateArea(geom, refcrs)
        newattrs = [extent.xMaximum(), extent.xMinimum(), extent.yMaximum(), extent.yMinimum(), area]
        for newattr in newattrs:
            attrs.append(newattr)
        featappend.setAttributes(attrs)
        output.addFeature(featappend)
    del output

def countVerticesInPolygon(layer):
    count = 0
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom.isMultipart():
            multi = geom.asMultiPolygon()
            for part in multi:
                for vertexes in part:
                    count += len(vertexes)
        else:
            pol = geom.asPolygon()
            for vertexes in pol:
                count += len(vertexes)
    return count

def addZFromAttribute(layer, fieldNames, name="Z", dataProvider = "ESRI Shapefile"):
    for fieldName in fieldNames:
        path = getPath(layer.source(), name + fieldName)
        zoutput = createEmptyVectorLayer(path, dataProvider, layer.pendingFields(), layer.crs(), convertWKB(layer.wkbType(), True), layer.dataProvider().encoding())
        if not zoutput:
            print "IS not possible to creaate new vectors "+ path + "and(exists?)"
            continue
        zindex = layer.fieldNameIndex(fieldName)
        if zindex < 0:
            print fieldName + "not founded in " + layer.name()
            del zoutput
            break
        for feature in layer.getFeatures():
            zfeature = QgsFeature(feature)
            z = zfeature.attribute(fieldName)
            if z is None or isinstance(z ,QPyNullVariant):
                success = zfeature.geometry().geometry().addZValue()
                if not success:
                    "It is not possible to add Z value to " + layer.name()
                    break
                newgeom = zfeature.geometry().exportToWkt()
                zfeature.setGeometry(QgsGeometry.fromWkt(newgeom))
                zoutput.addFeature(zfeature)
                continue
            success = zfeature.geometry().geometry().addZValue(z)
            if not success:
                "It is not possible to add Z value to " + layer.name()
                break
            newgeom = zfeature.geometry().exportToWkt()
            zfeature.setGeometry(QgsGeometry.fromWkt(newgeom))
            zoutput.addFeature(zfeature)
        print "Z layer " + path + " created."
        del zoutput

def removeDuplicateByAttributes(inputlayer, field_name, dataProvider = "ESRI Shapefile"):
    pass
    
def extractLayersFromAttribute(inputlayer, attribute, dataProvider = "ESRI Shapefile"):
    fields = inputlayer.pendingFields()
    idx = inputlayer.fieldNameIndex(attribute)
    values = inputlayer.uniqueValues( idx )
    print values
    for attr in values:
        if isinstance(attr, QPyNullVariant):
            path = getPath(inputlayer.source(), 'NULL')
        else:
            path = getPath(inputlayer.source(), attr)
        output = createEmptyVectorLayer(path, dataProvider, fields, inputlayer.crs(), inputlayer.wkbType(), inputlayer.dataProvider().encoding())
        
        for feature in inputlayer.getFeatures():
            outfeature = QgsFeature(feature)
            attr_value = outfeature.attribute(attribute) # get value of user defined atttribute
            # select equal values
            if attr_value == attr:
                output.addFeature(outfeature)
        del output
        
def generateNPDStructure(inputlayer, parentFolder, nameField="WBNAME"):
    idx = inputlayer.fieldNameIndex(nameField)
    default = os.getcwd()
    if os.path.isdir(parentFolder):
        os.chdir(parentFolder)
    if idx < 0:
        print fieldName + "not founded in " + layer.name()
        return None
    for feature in inputlayer.getFeatures():
        name = feature.attribute(nameField)
        if isinstance(name, QPyNullVariant):
            print "Name in Well with id " + str(feature.id()) + " not found."
        else:
            name = str(int(name))
            name = name.replace("/", "_")
            name = name.replace(" ", "_")
            if os.path.isdir(name):
                print "Directory " + name + "already exists."
                continue
            try:
                os.mkdir(name)
            except:
                print "Could not create directory " + name + " in " + os.getcwd()
                continue
            os.mkdir(os.path.join(name, "FactPages"))
            os.mkdir(os.path.join(name, "Documents"))
    os.chdir(default)
    print "Complete."

def statisticsFromIntersectedLayer(inlayer, intersectlayer, statField, name="STAT", stat = "AVG", dataProvider = "ESRI Shapefile"):
    idx = intersectlayer.fieldNameIndex(statField)
    if idx < 0:
        print statField + " not founded in " + intersectlayer.name()
        return None
    
    newfields = QgsFields()
    newfields.append(QgsField(stat, QVariant.Double))
    output, fields = addAttributesToLayer(inlayer, newfields, name + statField)
    if output is None:
        print "IS not possible to creaate new vectors (exists?)"
        return None
    index =QgsSpatialIndex()
    for feature in intersectlayer.getFeatures():
        index.insertFeature(feature)
    
    for feature in inlayer.getFeatures():
        intersectedValues = []
        intersected = index.intersects(feature.geometry().boundingBox())
        geom = feature.geometry()
        # select features in index
        intersectlayer.setSelectedFeatures(intersected)
        
        for intersect in intersectlayer.selectedFeaturesIterator():
            if intersect.geometry().intersects(geom):
                name = intersect.attribute(statField)
                if isinstance(name, QPyNullVariant):
                    print "Value in " + intersectlayer.name() + " with id " + str(intersect.id()) + " not found."
                else:
                    #append value
                    intersectedValues.append(name)
        
        featappend = QgsFeature(feature)
        attrs = feature.attributes()
        featappend.setFields(fields)
        mean = maptools_Stats[stat](intersectedValues)
        if mean is not None or not math.isnan(mean):
            attrs.append(float(mean))
        else:
            attrs.append(None)
        featappend.setAttributes(attrs)
        intersectlayer.setSelectedFeatures([])
        output.addFeature(featappend)
    print "Output created"
    del output
    
def queryForLayers(query, name="QUERY", dataProvider="ESRI Shapefile"):
    for layername, layer in activeLayersIterator():
        if not layer.type() < 1:
            continue
        provider = layer.dataProvider()
        if layer.hasGeometryType():
            path = getPath(layer.source(), name)
            output = createEmptyVectorLayer(path, dataProvider, layer.pendingFields(), layer.crs(), convertWKB(layer.wkbType(), False), provider.encoding())
            if not output:
                print "IS not possible to creaate new vectors "+ path + "and(exists?)"
                continue
            exp = QgsExpression(query)
            reqq = QgsFeatureRequest(exp)
            for layfeat in layer.getFeatures(reqq):
                featappend = QgsFeature(layfeat)
                output.addFeature(featappend)
            
            print "Layer " + path +" created."
            del output
 
def addIntersectionField(inputlayer, intersectlayer, fieldName="mask", name="INTER", dataProvider="ESRI Shapefile"):
    # create new layer with new attributes
    new = QgsFields()
    new.append(QgsField(fieldName, QVariant.String))
    output, newfields = addAttributesToLayer(inputlayer, new, name)
    if not output:
        print "IS not possible to creaate new vectors  (exists?)"
        return None
    # spatial index
    index =QgsSpatialIndex()
    for feature in intersectlayer.getFeatures():
        index.insertFeature(feature)
    
    for feature in inputlayer.getFeatures():
        appended = False
        geom = feature.geometry()
        featappend = QgsFeature(feature)
        attrs = feature.attributes()
        featappend.setFields(newfields)
        
        intersected = index.intersects(geom.boundingBox())
        intersectlayer.setSelectedFeatures(intersected)
        # iterate over features in index intersectlayer
        for intersect in intersectlayer.selectedFeaturesIterator():
            if geom.intersects(intersect.geometry()):
                # write attribute True
                attrs.append("Y")
                appended = True
                break
        if not appended:
            attrs.append("N")
        featappend.setAttributes(attrs)
        intersectlayer.setSelectedFeatures([])
        output.addFeature(featappend)
    print "Output created"
    del output

def difference(inputlayer, difflayer, name="DIFF", dataProvider="ESRI Shapefile"):
    gidx = qgscustom.QgsSpatialIndexC(difflayer)
    gidx.addFromLayer()
    path = getPath(inputlayer.source(), name)
    output = createEmptyVectorLayer(path, dataProvider, inputlayer.pendingFields(), inputlayer.crs(), inputlayer.wkbType(), inputlayer.dataProvider().encoding())
    if not output:
        print "IS not possible to creaate new vectors  (exists?)"
        return None
    for feature in inputlayer.getFeatures():
        diff = feature.geometry()
        featappend = QgsFeature(feature)
        intersected = gidx.intersectsBBox(diff)
        difflayer.setSelectedFeatures(intersected)
        for interf in difflayer.selectedFeaturesIterator():
            if diff is not None and not diff.isEmpty():
                diff = diff.difference(interf.geometry()) # difference between unioned interesected difflayer and inputlayer
            else:
                break
        difflayer.setSelectedFeatures([])
        if diff is not None and not diff.isEmpty():
            featappend.setGeometry(diff)
            output.addFeature(featappend)
    print path
    del output
        
def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def centroidsAndVertexes(selfIntersect = True, name="VertexesCentroids", dataProvider = "ESRI Shapefile"):
    for layername, layer in activeLayersIterator():
        path = getPath(layer.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, layer.pendingFields(), layer.crs(), QGis.WKBPoint, layer.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            return None
        for feature in layer.getFeatures():
            # get centroid
            attrs = feature.attributes()
            geom = feature.geometry()
            centroid = geom.centroid()
            if selfIntersect:
                if centroid.within(geom):
                    cfeature = QgsFeature()
                    cfeature.setAttributes(attrs)
                    cfeature.setGeometry(centroid)
                    output.addFeature(cfeature)
            else:
                cfeature = QgsFeature()
                cfeature.setAttributes(attrs)
                cfeature.setGeometry(centroid)
                output.addFeature(cfeature)
            
            if geom.type() == QGis.Polygon:
                
                if geom.isMultipart():
                    parts = geom.asMultiPolygon()
                    for part in parts:
                        for vertexs in part:
                            for vertex in vertexs:
                                nfeature = QgsFeature()
                                point = QgsGeometry.fromPoint(vertex)
                                nfeature.setGeometry(point)
                                nfeature.setAttributes(attrs)
                                output.addFeature(nfeature)
                else:
                    parts = geom.asPolygon()
                    for ring in parts:
                        for vertex in ring:
                            nfeature = QgsFeature()
                            point = QgsGeometry.fromPoint(vertex)
                            nfeature.setGeometry(point)
                            nfeature.setAttributes(attrs)
                            output.addFeature(nfeature)
        del output

def singlesToMultiIterator(geom, opt_feature=None):
    collection = geom.asGeometryCollection()
    for part in collection:
        if opt_feature is not None:
            featappend = QgsFeature(opt_feature)
            featappend.setGeometry(part)
            yield featappend
        else:
            yield part

def singlePolygonsToMulti(geom_list):
    multi = []
    print "line"
    print geom_list[0].asPolyline()
    print geom_list[0].asPolygon()
    for geom in geom_list:
        if geom.isMultipart():
            print geom.asMultiPolygon()
            multiout = geom.asMultiPolygon()
            for m in multiout:
                multi.append(m)
        else:
            multi.append(geom.asPolygon())
    return QgsGeometry.fromMultiPolygon(multi)
    
def splitByLinesDifference(inputfolder, splitfolder = None, tileslist=[], splitLayer = None, name="SPLITED", dataProvider = "ESRI Shapefile"):
    if len(tileslist) < 1:
        print "Please specify the numbers of layers."
        return None
    split = splitLayer
    if split is not None and splitfolder is None:
        index =QgsSpatialIndex()
        for feature in split.getFeatures():
            index.insertFeature(feature)
            
    for number in tileslist:
        if split is None and splitfolder is not None:
            splitpath = "LDR141209_Gabcikovo_" + str(number) + "_txt_Max_z_convex.shp"
            split = QgsVectorLayer(os.path.join(splitfolder, splitpath), "split", "ogr")
            print split.source()
            index =QgsSpatialIndex()
            for feature in split.getFeatures():
                index.insertFeature(feature)
            
        inpath = "dr141209_gabcikovo_" + str(number) + "_txt_profcur_lod5.shp"
        input = QgsVectorLayer(os.path.join(inputfolder, inpath), "input", "ogr")
        
        print input.source()
        
        path = getPath(input.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, input.pendingFields(), input.crs(), input.wkbType(), input.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        
        for feature in input.getFeatures():
            geom = feature.geometry()
            if geom.type() != QGis.Polygon:
                print "Specify input geometry as Polygon"
                return None
                
            featappend = QgsFeature(feature)
            intersected = index.intersects(geom.boundingBox())
            split.setSelectedFeatures(intersected)
        # iterate over features in index intersectlayer
            intersected = []
            for intersect in split.selectedFeaturesIterator():
                intersected.append(intersect.geometryAndOwnership().buffer(0.001, 2, 2, 2, 5.0))
            if len(intersected) < 1: # if nothing selected by index, only copy feature
                output.addFeature(featappend)
                continue
            else:
                union = QgsGeometry.unaryUnion(intersected)
                diff = geom.difference(union) # difference between unioned interesected difflayer and inputlayer
                if diff is None:
                    output.addFeature(featappend) # if difference succedd or not, append feature
                    print "Difference is none"
                    continue
                for single in singlesToMultiIterator(diff, featappend):
                    output.addFeature(single)
                        
            
            split.setSelectedFeatures([]) # clear selection
            
        del output
        input = None
    split = None
    index = None

def differenceForest(tilelist=[], name="Cl", dataProvider = "ESRI Shapefile"):
    
    for tile in tilelist:
        cvx = QgsMapLayerRegistry.instance().mapLayersByName("Smooth - ldr141209_gabcikovo_" + tile + "_max_1_cvx_curvature_zQUERYVertexesCentroids_Tile_Triangles_polygons")[0]
        smallpx = QgsMapLayerRegistry.instance().mapLayersByName("Smooth - LDR141209_Gabcikovo_" + tile + "_Difference_1_Tile_Triangles_polygons")[0]
        morepx = QgsMapLayerRegistry.instance().mapLayersByName("Smooth - LDR141209_Gabcikovo_" + tile + "_Difference_1_Tile_Triangles_polygons")[1]
        
        cvxgeom = []
        for feature in cvx.getFeatures():
            cvxgeom.append(feature.geometryAndOwnership())
        print "teraz"
        cvxunion = QgsGeometry.unaryUnion(cvxgeom)
        print "bol"
        
        morepath = getPath(morepx.source(), name)
        print morepath
        outmorepx = createEmptyVectorLayer(morepath, dataProvider, morepx.pendingFields(), morepx.crs(), morepx.wkbType(), morepx.dataProvider().encoding())
        if not outmorepx:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        
        smallgeom = []
        for feature in morepx.getFeatures():
            smallgeom.append(feature.geometryAndOwnership())
            featappend = QgsFeature(feature)
            diff = feature.geometry().difference(cvxunion)
            if diff is None:
                outmorepx.addFeature(featappend) # if difference succedd or not, append feature
                print "Difference is none"
            else:
                for single in singlesToMultiIterator(diff, featappend):
                    outmorepx.addFeature(single)
        del outmorepx
        cvxsmallunion = QgsGeometry.unaryUnion(cvxgeom + smallgeom)
        
        smallpath = getPath(smallpx.source(), name)
        outsmallpx = createEmptyVectorLayer(smallpath, dataProvider, smallpx.pendingFields(), smallpx.crs(), smallpx.wkbType(), smallpx.dataProvider().encoding())
        if not outsmallpx:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        print smallpath
        for feature in smallpx.getFeatures():
            geom = feature.geometry()
            featappend = QgsFeature(feature)
            diff = geom.difference(cvxsmallunion)
            if diff is None:
                outsmallpx.addFeature(featappend) # if difference succedd or not, append feature
                print "Difference is none"
            else:
                for single in singlesToMultiIterator(diff, featappend):
                    outsmallpx.addFeature(single)
        del outsmallpx

def unionLayers(name="union", dataProvider = "ESRI Shapefile"):
    metafields = [QgsField("PolyId" ,QVariant.Int)] 
    newfields = QgsFields()
    for meta in metafields:
        newfields.append(meta)
    
    for layername, layer in activeLayersIterator():
        path = getPath(layer.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, newfields, layer.crs(), layer.wkbType(), layer.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        uniongeom = []
        for feature in layer.getFeatures():
            uniongeom.append(feature.geometryAndOwnership())
            
        unioned = QgsGeometry.unaryUnion(uniongeom)
        print unioned.exportToWkt()
        iter = -1
        for part in singlesToMultiIterator(unioned):
            iter += 1
            featappend = QgsFeature(iter)
            featappend.setGeometry(part)
            featappend.setAttributes([iter])
            output.addFeature(featappend)
            
        del output

def withinDistance(distance, distlayer, name="DIST", dataProvider = "ESRI Shapefile"):
    
    gidx = qgscustom.QgsSpatialIndexC(distlayer)
    gidx.addFromLayer()
    
    for layername, layer in activeLayersIterator():
        path = getPath(layer.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, layer.pendingFields(), layer.crs(), layer.wkbType(), layer.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        
        for feature in layer.getFeatures():
            geom = feature.geometry()
            intersected = gidx.intersectsBBox(geom, distance)
            distlayer.setSelectedFeatures(intersected)
            for distfeature in distlayer.selectedFeaturesIterator():
                if geom.distance(distfeature.geometry()) < distance:
                    output.addFeature(feature)
                    break
            distlayer.setSelectedFeatures([])
        
        del output
        
def selectNotIntersected(tilestart, tileend, name="NOTINT", dataProvider = "ESRI Shapefile"):
    """
    Input layers must be activated.
    """
    for layname, lay in activeLayersIterator():
        tilename = layname[tilestart:tileend]
        intersect = QgsMapLayerRegistry.instance().mapLayersByName("ldr150613_safarikovo_" + tilename + "_les_max_cvx_curvature_zmean2VertexesCentroids_Tile_Triangles_polygons_SPL_SPLQUERY")
        if len(intersect) > 0:
            intersectlayer = intersect[0]
        else:
            print "For layer " + layname + "is not possible to find intersect layer."
            continue
        gidx = qgscustom.QgsSpatialIndexC(intersectlayer)
        gidx.addFromLayer()
        path = getPath(lay.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, lay.pendingFields(), lay.crs(), lay.wkbType(), lay.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            del output
            continue
        
        for feature in lay.getFeatures():
            ofinter = False
            geom = feature.geometry()
            intersected = gidx.intersectsBBox(geom)
            intersectlayer.setSelectedFeatures(intersected)
            for interf in intersectlayer.selectedFeaturesIterator():
                intergeom = interf.geometry()
                if geom.intersects(intergeom):
                    ofinter = True
                    break
            if not ofinter: # if nothing is intersected with input feature, write it
                outfeature = QgsFeature(feature)
                output.addFeature(outfeature)
            intersectlayer.setSelectedFeatures([])
        del output

def differenceTiles(tilestart, tileend, name="DIFF", dataProvider= "ESRI Shapefile"):
    for layname, lay in activeLayersIterator():
        tilename = layname[tilestart:tileend]
        diff = QgsMapLayerRegistry.instance().mapLayersByName("ldr150613_safarikovo_" + tilename + "_les_max_cvx_curvature_zmean2VertexesCentroids_Tile_Triangles_polygons_SPL_SPLQUERY")
        if len(diff) > 0:
            difflayer = diff[0]
        else:
            print "For layer " + layname + "is not possible to find difference layer."
            continue
        
        difference(lay, difflayer, name, dataProvider)

def bufferLayers(size, diss = False, name="BUFFER", dataProvider= "ESRI Shapefile"):
    if diss:
        metafields = [QgsField("PolyId" ,QVariant.Int)] 
        newfields = QgsFields()
        for meta in metafields:
            newfields.append(meta)
        
    for layname, lay in activeLayersIterator():
        path = getPath(lay.source(), name)
        if not diss:
            newfields = lay.pendingFields()
        output = createEmptyVectorLayer(path, dataProvider, newfields, lay.crs(), lay.wkbType(), lay.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            del output
            continue
        print path
        if diss:
            buffered = []
            for feature in lay.getFeatures():
                geom = feature.geometryAndOwnership()
                buff = geom.buffer(size, 2, 2, 2, 5.0)
                buffered.append(buff)
            unioned = QgsGeometry.unaryUnion(buffered)
            iter = -1
            for part in singlesToMultiIterator(unioned):
                iter += 1
                featappend = QgsFeature(iter)
                featappend.setGeometry(part)
                featappend.setAttributes([iter])
                output.addFeature(featappend)
        else:
            for feature in lay.getFeatures():
                geom = QgsGeometry(feature.geometry())
                featappend = QgsFeature(feature)
                buff = geom.buffer(size, 2, 2, 2, 5.0)
                featappend.setGeometry(buff)
                output.addFeature(featappend)
        del output
        
def multiToSinglesLayers(name="SIN",dataProvider= "ESRI Shapefile"):
    metafields = [QgsField("PolyId" ,QVariant.Int)] 
    newfields = QgsFields()
    for meta in metafields:
        newfields.append(meta)
        
    for layname, lay in activeLayersIterator():
        path = getPath(lay.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, newfields, lay.crs(), lay.wkbType(), lay.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            del output
            continue
        print path
        for feature in lay.getFeatures():
            geom = feature.geometry()
            iter = -1
            for part in singlesToMultiIterator(geom):
                iter += 1
                featappend = QgsFeature(iter)
                featappend.setGeometry(part)
                featappend.setAttributes([iter])
                output.addFeature(featappend)
        del output

def addHolesFromLayer(input, holes, query, name="FILLED",dataProvider= "ESRI Shapefile"):
    layerWkbType = input.wkbType()
    holesWkbType = holes.wkbType()
    if layerWkbType != QGis.WKBPolygon or holesWkbType != QGis.WKBPolygon:
        "One or two input layers are not polygon type."
        return None
    path = getPath(holes.source(), name)
    output = createEmptyVectorLayer(path, dataProvider, holes.pendingFields(), holes.crs(), holes.wkbType(), holes.dataProvider().encoding())
    if not output:
        print "IS not possible to creaate new vectors  (exists?)"
        del output
        return None
    exp = QgsExpression(query)
    reqq = QgsFeatureRequest(exp)
    for feature in input.getFeatures():
        featappend = QgsFeature(feature)
        geom = QgsGeometry(featappend.geometry())
        for hfeature in holes.getFeatures(reqq):
            hgeom = hfeature.geometry()
            if hgeom.within(geom):
                geom.addRing(hgeom.asPolygon()[0])
        featappend.setGeometry(geom)
        output.addFeature(featappend)
    del output
    return True
    
def addHolesFromLayersTiles(tilestart, tileend, query, name="FILLEDREF", dataProvider= "ESRI Shapefile"):
    for layname, lay in activeLayersIterator():
        tilename = layname[tilestart:tileend]
        holes = QgsMapLayerRegistry.instance().mapLayersByName("Smooth 1 2 of ldr150613_safarikovo_" + tilename + "_les_max_cvx_curvature_zQUERYVertexesCentroids_Tile_Triangles_polygonsHOLES_0_1000")
        if len(holes) > 0:
            holeslayer = holes[0]
        else:
            print "For layer " + layname + "is not possible to find difference layer."
            continue
        
        result = addHolesFromLayer(lay, holeslayer, query, name, dataProvider)
        # USE EXCEPTIONS IS BETTER TACTIC
        if result:
            print "SUCCESS"
        else:
            print "SOMETHING WRONG"

def differenceLayers(difflayer, name="FILLED",dataProvider= "ESRI Shapefile"):
    for layname, lay in activeLayersIterator():
        difference(lay, difflayer, name="DIFF", dataProvider="ESRI Shapefile")

def getVerticesOfPolygonToList(geom):
    exporter = []
    if geom.type() == QGis.Polygon:
        if geom.isMultipart():
            parts = geom.asMultiPolygon()
            for part in parts:
                for vertexs in part:
                    for vertex in vertexs:
                        exporter.append(vertex)
        else:
            parts = geom.asPolygon()
            for ring in parts:
                for vertex in ring:
                    exporter.append(vertex)
    else:
        return None
    
    return exporter

def delaunay_(qgs_points):
    pois = delaunay.DelaunayPoints(qgs_points)
    try:
        triangles = pois.executeMatplotlib()
    except Exception as inst:
        print inst
        return None
    if triangles is None:
        return None
    return triangles

def delaunayPolygonLayerWithPoints(input, pointlayer, name="TINIZE", dataProvider= "ESRI Shapefile"):
    
    gidx = qgscustom.QgsSpatialIndexC(pointlayer)
    gidx.addFromLayer()
    
    idx = input.fieldNameIndex("epsilon")
    if idx < 0:
        print statField + " not founded in " + input.name()
        return None
    metafields = [QgsField("epsilon" ,QVariant.Int)] 
    newfields = QgsFields()
    for meta in metafields:
        newfields.append(meta)
    
    path = getPath(input.source(), name)
    output = createEmptyVectorLayer(path, dataProvider, newfields, input.crs(), QGis.WKBMultiPolygon, input.dataProvider().encoding())
    if not output:
        print "IS not possible to creaate new vectors  (exists?)"
        del output
        return None
    
    for feature in input.getFeatures():
        featappend = QgsFeature()
        geom = feature.geometry()
        intersected = gidx.intersectsBBox(geom)
        pointlayer.setSelectedFeatures(intersected)
        if not geom.isEmpty():
            vertices = getVerticesOfPolygonToList(geom)
            for interf in pointlayer.selectedFeaturesIterator():
                igeom = interf.geometry()
                if igeom.intersects(geom):
                    vertices.append(igeom.asPoint())
            if vertices is not None:
                multi = delaunay_(vertices)
                if multi is None:
                    print "Not possible to Delaunay for " + str(feature.id())
                    continue
                multioutput = []
                # check outside triangles
                for polygon in multi:
                    polygeom = QgsGeometry.fromPolygon(polygon)
                    if polygeom.intersects(geom):
                        multioutput.append(polygon)
                
                multioutputgeom = QgsGeometry.fromMultiPolygon(multioutput)
                featappend.setAttributes([feature.attributes()[idx]])
                featappend.setGeometry(multioutputgeom)
                output.addFeature(featappend)
        pointlayer.setSelectedFeatures([])
    
    del output
    

def activeLayersToFormat(format=".csv" , dataProvider="CSV"):
    # TODO OTHER THAN CSV
    for layname, lay in activeLayersIterator():
        if dataProvider == "CSV":
            source, suffix = os.path.splitext(lay.source()) # get suffix and path to file
            path = source + format
            print QgsVectorFileWriter.writeAsVectorFormat(lay, path, "utf-8", None, "CSV", False, "", "", ['GEOMETRY=AS_XYZ'])
        else:
            path = getPath(lay.source(), layname)
            QgsVectorFileWriter.writeAsVectorFormat(lay, path, "utf-8", None, dataProvider)

#TODO class
counter = 0
features = []
def _createScreenshot():
    global counter
    print "som taka aka som"
    qgis.utils.iface.mapCanvas().saveAsImage("D:\\\\mapycz\\testing\\tete" + str(counter) + ".png")


def alignCenter():
    global counter
    global features
    
    point = features[counter].geometry().asPoint()
    qgis.utils.iface.mapCanvas().setCenter(point)
    qgis.utils.iface.mapCanvas().refreshAllLayers()
    counter += 1

def createScreenshots(layer):
    global counter
    counter = 0
#    qgis.utils.iface.mapCanvas().extentsChanged.connect(_createScreenshot)
    qgis.utils.iface.mapCanvas().mapCanvasRefreshed.connect(_createScreenshot)
    features = [feature for feature in layer.getFeatures()]
    for feature in features[0:3]:
        time.sleep(2)
        point = feature.geometry().asPoint()
        qgis.utils.iface.mapCanvas().setCenter(point)
        qgis.utils.iface.mapCanvas().refreshAllLayers()
#        qgis.utils.iface.mapCanvas().refresh()
#        qgis.utils.iface.mapCanvas().extentsChanged.emit()
    qgis.utils.iface.mapCanvas().mapCanvasRefreshed.disconnect(_createScreenshot)

def createScreenshots3(layer):
    counter = 0

    def saveMap():
        qgis.utils.iface.mapCanvas().saveAsImage("D:\\\\mapycz\\testing\\hejnovran" + str(counter) + ".png")

    for feature in layer.getFeatures():
        counter += 1
        point = feature.geometry().asPoint()
        qgis.utils.iface.mapCanvas().setCenter(point)
        qgis.utils.iface.mapCanvas().refreshAllLayers()
        QTimer.singleShot(2000, saveMap)
    
ids = None

def createScreenshot4(layer):
    global ids
    ids = layer.allFeatureIds()

    def exportMap():
        global ids
        qgis.utils.iface.mapCanvas().saveAsImage( "D:\\\\mapycz\\bozejovice\\{}.png".format( ids.pop() ) )
        if ids:
            setNextFeatureExtent()
        else: # We're done
            qgis.utils.iface.mapCanvas().mapCanvasRefreshed.disconnect( exportMap )

    def setNextFeatureExtent():
        reqq = QgsFeatureRequest()
        reqq.setFilterFid(ids[-1])
        for feature in layer.getFeatures(reqq):
            point = feature.geometry().asPoint()
            qgis.utils.iface.mapCanvas().setCenter(point)
            qgis.utils.iface.mapCanvas().refreshAllLayers()
        

    qgis.utils.iface.mapCanvas().mapCanvasRefreshed.connect( exportMap )
    setNextFeatureExtent() # Let's start

def addZMtoAttributes(name="_ZM", dataProvider="ESRI Shapefile"):
    new = QgsFields()
    new.append(QgsField("Z", QVariant.Double))
    new.append(QgsField("M", QVariant.Double))
    
    for layname, lay in activeLayersIterator():
        outpath = getPath(lay.source(), name)
        fields = lay.pendingFields()
        newfields = QgsFields(fields)
        for newfield in new:
            newfields.append(newfield)
        output = createEmptyVectorLayer(outpath, dataProvider, newfields, lay.crs(), convertWKB(QGis.WKBPoint, True), lay.dataProvider().encoding())
        if not output:
            continue
        for feature in lay.getFeatures():
            featappend = QgsFeature(feature)
            geom = featappend.geometry().geometry()
            seq = geom.coordinateSequence()
            for s in seq:
                for ring in s:
                    for point in ring:
                        newfeat = QgsFeature()
                        attrs = featappend.attributes()
                        attrs.append(point.z())
                        attrs.append(point.m())
                        newgeom = point.asWkt()
                        newfeat.setGeometry(QgsGeometry.fromWkt(newgeom))
                        newfeat.setAttributes(attrs)
                        output.addFeature(newfeat)
        
        del output

def getNoaLazFromActiveLayer(directory, urlField):
    for layname, layer in activeLayersIterator():
        if layer.type() < 1 and layer.hasGeometryType(): #if vector
            indexlayer = layer.fieldNameIndex(urlField)
            if indexlayer == -1:
                print urlField + " is not in inputlayer and layer"
                return None
            
            for feature in layer.getFeatures():
                url = feature.attributes()[indexlayer]
                url = url.rstrip("\n")
                n = noa.noa(url)
                n.writeLaz(directory)
            

def overlayStatistics(intersectlayer, query=None, name="STAT", dataProvider = "ESRI Shapefile"):
    
    index =QgsSpatialIndex()
    for feature in intersectlayer.getFeatures():
        index.insertFeature(feature)
    
    for layname, inlayer in activeLayersIterator():
        if layer.type() < 1 and layer.hasGeometryType(): #if vector
            
            if query is None:
                reqq = None
            else:
                exp = QgsExpression(query)
                reqq = QgsFeatureRequest(exp)
            
            for feature in inlayer.getFeatures(reqq):
                geom = feature.geometry()
                intersected = index.intersects(geom.boundingBox())
                # select features in index
                intersectlayer.setSelectedFeatures(intersected)
        
                for intersect in intersectlayer.selectedFeaturesIterator():
                    if intersect.geometry().intersects(geom):
                        name = intersect.attribute(statField)
                if isinstance(name, QPyNullVariant):
                    print "Value in " + intersectlayer.name() + " with id " + str(intersect.id()) + " not found."
                else:
                    #append value
                    intersectedValues.append(name)
        
        featappend = QgsFeature(feature)
        attrs = feature.attributes()
        featappend.setFields(fields)
        mean = maptools_Stats[stat](intersectedValues)
        if mean is not None or not math.isnan(mean):
            attrs.append(float(mean))
        else:
            attrs.append(None)
        featappend.setAttributes(attrs)
        intersectlayer.setSelectedFeatures([])
        output.addFeature(featappend)
    print "Output created"
    del output

def joinStatisticsPerimeter(perimeterLayer, indexField = "indexL", name = "MAXPERIM", dataProvider = "ESRI Shapefile"):
    indexlayer = perimeterLayer.fieldNameIndex(indexField)
    if indexlayer == -1:
        print indexField + " is not in inputlayer and layer"
        return None
    
    for layername, layer in activeLayersIterator():
        if layer.type() < 1 and layer.hasGeometryType(): #if vector
            lfields = layer.pendingFields()
            fields = QgsFields()
            for lfield in lfields:
                fields.append(lfield)
            fields.append(QgsField("joinP5i", QVariant.Double))
            path = getPath(layer.source(), name)
            output = createEmptyVectorLayer(path, dataProvider, fields, layer.crs(), layer.wkbType(), layer.dataProvider().encoding())
            if not output:
                print "Not possible to create vector layer " + path
                continue
            
            for feature in layer.getFeatures():
                id = feature.id()
                exp = QgsExpression(indexField + '=' + str(id))
                reqq = QgsFeatureRequest(exp)
                perims = []
                for perimfeature in perimeterLayer.getFeatures(reqq):
                    geom = perimfeature.geometry().geometry()
                    perimeter = geom.perimeter()
                    perims.append(perimeter)
                
                if len(perims) < 1:
                    maximum = None
                else:
                    maximum = float(max(perims))
                featappend = QgsFeature(feature)
                attrs = feature.attributes()
                featappend.setFields(fields)
                if maximum is not None:
                    attrs.append(float(maximum))
                else:
                    attrs.append(None)
                featappend.setAttributes(attrs)
                output.addFeature(featappend)
                perimeterLayer.setSelectedFeatures([])
            print "Output created"
            del output

def withinDistanceAddAttr(distance, distlayer, name="DIST", dataProvider = "ESRI Shapefile"):
    
    gidx = qgscustom.QgsSpatialIndexC(distlayer)
    gidx.addFromLayer()
    
    for layername, layer in activeLayersIterator():
        lfields = layer.pendingFields()
        fields = QgsFields()
        for lfield in lfields:
            fields.append(lfield)
        fields.append(QgsField("poly_id", QVariant.Int))
        path = getPath(layer.source(), name)
        output = createEmptyVectorLayer(path, dataProvider, fields, layer.crs(), layer.wkbType(), layer.dataProvider().encoding())
        if not output:
            print "IS not possible to creaate new vectors  (exists?)"
            continue
        
        for feature in layer.getFeatures():
            newfeature = QgsFeature(feature)
            geom = feature.geometry()
            attributes = feature.attributes()
            intersected = gidx.intersectsBBox(geom, distance)
            distlayer.setSelectedFeatures(intersected)
            for distfeature in distlayer.selectedFeaturesIterator():
                if geom.distance(distfeature.geometry()) < distance:
                    distid = distfeature.id()
                    attributes.append(distid)
                    newfeature.setAttributes(attributes)
                    output.addFeature(newfeature)
                    break
            distlayer.setSelectedFeatures([])
        
        del output

def exportSelectedToSeisnetics(outpath):
    fw = texttoolsv2.fileOpener(outpath, "w")
    fw.write("! Seisnetics GeoPopulation file\n")
    fw.write("! Format: IL XL x y z\n")
    fw.write("! a2c 201708\n")
    
    for layername, layer in activeLayersIterator():
        for feature in layer.selectedFeaturesIterator():
            attrs = feature.attributes()
            result = []
            for attr in attrs:
                result.append(str(attr))
            attrstext = " ".join(result)
            fw.write(attrstext + "\n")
    
    fw.close()

def statsFromRasterToPolygons(inraster):
    for layername, layer in activeLayersIterator():
        zonalstats = qgis.analysis.QgsZonalStatistics(layer, inraster.source(), stats=qgis.analysis.QgsZonalStatistics.All)
        code = zonalstats.calculateStatistics(None)
        if code > 0:
            print "By calculating occured error " + code

def regressionAnalysis(xfield, yfield, reclass=False):
    count = 0
    first = None
    for layername, layer in activeLayersIterator():
        xindex = layer.fieldNameIndex(xfield)
        yindex = layer.fieldNameIndex(yfield)
        if xindex == -1 or yindex == -1:
            print "In layer " + layername + " is not possible to find fields with names."
            break
        source = getPath(layer.source(), xfield + "_" + yfield)
        xvalues = []
        yvalues = []
        for feature in layer.getFeatures():
            attrs = feature.attributes()
            x = attrs[xindex]
            y = attrs[yindex]
            if reclass:
                ydeg = math.degrees(y)
                if ydeg >= 315 and ydeg < 45:
                    y = 0
                elif ydeg >= 45 and ydeg < 135:
                    y = 1
                elif ydeg >= 135 and ydeg < 225:
                    y = 2
                else:
                    y = 3
            
            xvalues.append(x)
            yvalues.append(y)
        
        header = count < 1 and True or False
        first = count < 1 and source or first
        stat = stats.Statistics(xvalues, yvalues, header, first)
        stat.save(source)
        count += 1