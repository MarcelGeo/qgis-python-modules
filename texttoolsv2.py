import os
import re

def getFiles(directory, name, in_format):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            valid = re.findall(".*" + name + ".*\.(?:" + in_format + ")$", filename)
            if len(valid) > 0:
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)
    print("Count of founded layers: " + str(len(file_paths)))
    return file_paths

def fileOpener(path, mode):
    try:
        file = open(path, mode)
    except IOError:
        return None
    else:
        return file


# --- public

def splitToStrings(text):
    return re.split("\W+", text)

def splitStringToInt(text):
    arr = re.split('\D+', text)
    arrn = []
    for ch in arr:
        try:
            chf = int(ch)
        except:
            continue
        arrn.append(chf)
    return arrn

def reorderFields(path , order,  fields=[], outpath=None, skip=0, insep=None, outsep=None):
    if outsep is None: # main controling
        outsep = ";"
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(outpath or source + "REORDERED" + suffix, "w")
    fields = fields or []
    if f and fw:
        if len(fields) > 0:
            fw.write(outsep.join(fields) + "\n")
        for index, line in enumerate(f):
            if index > skip - 1:
                newline = []
                linearr = line.split(insep)
                for i in order:
                    striped = linearr[i - 1].rstrip()
                    newline.append(striped)
                fw.write(outsep.join(newline) + "\n")
        f.close()
        fw.close()
        return True
    else:
        return None

def selectBetween(path, column, min, max, outpath=None, skip=0, insep=";", outsep=";"):
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(outpath or source + "SELECTED" + suffix, "w")
    foundedfield = 0
    if f and fw:
        for index, line in enumerate(f):
            if index > skip - 1: # if 0 to skip, nothing
                linearr = [e.strip() for e in line.split(insep)]
                if index == skip:
                    fw.write(outsep.join(linearr) + "\n")
                    try: # try to find index with user defined column
                        foundedfield = linearr.index(column)
                    except ValueError:
                        return None
                else: # selecting
                    value = float(linearr[foundedfield])
                    if(value >= min and value <= max):
                        fw.write(outsep.join(linearr) + "\n")
        f.close()
        fw.close()
        return True
    else:
        return None

def repairToAnalysis(path, skip = 0):
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(source + "TEST" + ".ascii", "w")
    fw.write("! Seisnetics GeoPopulation file\n")
    fw.write("! Format: IL XL x y z\n")
    fw.write("! a2c\n")
    intervals = [[32, 41], [48, 57], [64, 74]]
#    intervals = [[5, 8], [10, 17], [19, 27]]
    for index, line in enumerate(f):
        if index > skip - 1:
            base = line[:intervals[0][0]]
            for iindex, interval in enumerate(intervals):
                next = iindex + 1
                number = line[interval[0]:interval[1]]
                strippedn = number.strip()
                spaces = len(number) - len(strippedn)
                resultspaces = spaces * " "
                result = resultspaces + strippedn
                if next >= len(intervals):
                    base += result
                else:
                    base = base + result + line[interval[1]:intervals[next][0]]
            fw.write(base + "\n")
    
    f.close()
    fw.close()
    
def repairElevationFromVelseis(path, skip=0, outsep=" "):
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(source + "Repaired" + ".xyz", "w")
    for index, line in enumerate(f):
        if index > skip:
            splitted = re.split(r'\t+', line.rstrip('\t'))
            fw.write(outsep.join(splitted))
    fw.close()
    f.close()

def convertFromVelseisToSeisnetics(path, indexesToAdd=None, indexesToConvert=None, skip=0, outsep="   ", surface="a2c", name="RepairedTWT"):
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(source + name + ".ascii", "w")
    fw.write("! Seisnetics GeoPopulation file\n")
    fw.write("! Format: IL XL x y z\n")
    fw.write("! "+ surface + "\n")
    for index, line in enumerate(f):
        if index > skip:
            splitted = re.split(r'\t+', line.rstrip())
            newsplitted = []
            if indexesToAdd is not None:
                for index in indexesToAdd:
                    newsplitted.append(splitted[index])
            else:
                newsplitted = splitted
            if indexesToConvert is not None:
                for index in indexesToConvert:
                    number = newsplitted[index]
                    number = float(number)
                    number = number * 1000
                    result = str(number)
                    newsplitted[index] = result
            for index, item in enumerate(newsplitted):
                multipier = 6 - len(item)
                newsplitted[index] = item + (" " * multipier)
            fw.write(outsep.join(newsplitted) + "\n")
    fw.close()
    f.close()

def addSpaceToColumn(index, path, name):
    f = fileOpener(path, "r")
    source, suffix = os.path.splitext(path) # get suffix and path to file
    fw = fileOpener(source + name + ".dat", "w")
    for i, line in enumerate(f):
        newline = [line[:index], line[index:]]
        fw.write(" ".join(newline))
    
    f.close()
    fw.close()

#        end = line[-16:]
#        number = end[0:9]
#        other = line[0: len(line) - 16]
#        strippedn = number.strip()
#        spacesleft = (9 - len(strippedn))
        
#texttools.reorderFields("C:\marcel\ASH\linedata\Ashburton\wa\GSWA_P1134MAG.dat", [6,9,3,11,10,13,7,8],  ["lat", "lon", "east", "north", "microleveled", "resid", "line", "lineid"])
#texttools.selectBetween("C:\marcel\ASH\linedata\Ashburton\wa\mr.txt", "line", 100010, 100110, None, 0, None)
#texttools.selectBetween("C:\marcel\ASH\linedata\Ashburton\wa\GSWA_P1134MAGREORDERED.dat", "line", 100010, 100110)

def copyFiles(directory, name, in_format, out_format='txt'):
    paths = getFiles(directory, name, in_format)
    for path in paths:
        f = fileOpener(path, "r")
        source, suffix = os.path.splitext(path) # get suffix and path to file
        fw = fileOpener(source + '.' + out_format, "w")
        for index, line in enumerate(f):
            fw.write(line)
        
        f.close()
        fw.close()
