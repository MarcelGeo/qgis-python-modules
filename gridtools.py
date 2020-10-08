import os
import re
import texttools
from osgeo import gdal
import processing

def getFiles(directory, name, in_format):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            valid = re.findall(".*" + name + ".*\." + in_format + "$", filename)
            if len(valid) > 0:
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)
    print "Count of founded layers: " + str(len(file_paths))
    return file_paths

def createCompositsFind(directory, in_format):
    dirs = []
    for root, directories, files in os.walk(directory):
        for dir in directories:
            images = []
            images.append(getFiles(os.path.join(root, dir), "04", in_format))
            images.append(getFiles(os.path.join(root, dir), "03", in_format))
            images.append(getFiles(os.path.join(root, dir), "02", in_format))
            dirs.append(images)
    return dirs

def createComposits(directory, in_format):
    files = createCompositsFind(directory, in_format)
    for dir in files:
        images = []
        for file in dir:
            if len(file) > 0:
                images.append(file[0])
            else:
                break
        if len(images) == 3:
            dirname, filename = os.path.split(images[0])
            outputdir, output = os.path.split(dirname)
            try:
                imgstr = ";".join(images)
                print imgstr
                processing.runalg("gdalogr:merge", imgstr, False, True, 5, os.path.join(dirname, output + ".tif"))
            except:
                print "Not possible to run algorithm"
        else:
            print "Not foundeed bands in "
            print dir
                

def repairASCFromGrass(directory, NODATA_value=-999999, name=''):
    #gridtools.repairASCFromGrass('C:\\Transfer\\paraguay')
    ascs = getFiles(directory, name, 'asc')
    print ascs
    for asc in ascs:
        file = texttools.fileOpener(asc, 'r')
        source, suffix = os.path.splitext(asc) # get suffix and path to file
        fw = texttools.fileOpener(source + "export" + suffix, "w")
        for index, line in enumerate(file):
            if index == 4:
                # dx
                towrite = 'cellsize     ' + line[13:]
                fw.write(towrite)
                continue
            if index == 5:
                towrite = 'NODATA_value ' + str(NODATA_value) + '\n'
                fw.write(towrite)
                continue
            if index == 6:
                nodata = re.match('NODATA_value', line)
                if nodata is not None:
                    continue
                else:
                    fw.write(line)
            fw.write(line)
        print asc
        print source + 'export' + suffix
        fw.close()
        file.close()

def replaceInASC(directory, what, to, header = True, format='asc', skip=5):
    ascs = getFiles(directory, ".*", format)
    print ascs
    for asc in ascs:
        file = texttools.fileOpener(asc, 'r')
        source, suffix = os.path.splitext(asc) # get suffix and path to file
        fw = texttools.fileOpener(source + "export2" + suffix, "w")
        for index, line in enumerate(file):
            if(index > skip):
                newline = []
                linearr = line.split(" ")
                for cell in linearr:
                    cell = cell.rstrip()
                    if cell == what:
                        newline.append(to)
                    else:
                        newline.append(cell)
                fw.write(" ".join(newline) + "\n")
            else:
                if header:
                    fw.write(line)
        file.close()
        fw.close()

def appendToASC(directory, append = 60000, header = True, format='asc', skip=6):
    ascs = getFiles(directory, ".*", format)
    print ascs
    for asc in ascs:
        file = texttools.fileOpener(asc, 'r')
        source, suffix = os.path.splitext(asc) # get suffix and path to file
        fw = texttools.fileOpener(source + "appended" + suffix, "w")
        for index, line in enumerate(file):
            if(index > skip):
                newline = []
                lenght = len(line)
                calc = append - lenght
                if lenght >= append:
                    to = ""
                    appendedline = line[0:append]
                else:
                    to = " " * calc
                    appendedline = line
                linearr = appendedline.split(" ")
                for cell in linearr:
                    cell = cell.rstrip()
                    newline.append(cell)
                newline.append(to)
                towrite = " ".join(newline)
                if len(towrite) > append: # second iteration
                    towrite = towrite[0:append]
                fw.write(towrite + "\n")
            else:
                if header:
                    fw.write(line)
        file.close()
        fw.close()