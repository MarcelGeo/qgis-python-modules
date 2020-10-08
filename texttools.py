import os
import re

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
    if f and fw:
        if len(fields) > 0:
            fw.write(outsep.join(fields) + "\n")
        for index, line in enumerate(f):
            if index > skip - 1:
                newline = []
                linearr = line.split(insep)
                for i in order:
                    newline.append(linearr[i - 1])
                fw.write(outsep.join(newline) + "\n")
        f.close()
        fw.close()
    else:
        print "here somethin bad"

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
                        return "Bad column"
                else: # selecting
                    value = float(linearr[foundedfield])
                    if(value >= min and value <= max):
                        fw.write(outsep.join(linearr) + "\n")
        f.close()
        fw.close()
    else:
        return "here something wrong"
#texttools.reorderFields("C:\marcel\ASH\linedata\Ashburton\wa\GSWA_P1134MAG.dat", [6,9,3,11,10,13,7,8],  ["lat", "lon", "east", "north", "microleveled", "resid", "line", "lineid"])
#texttools.selectBetween("C:\marcel\ASH\linedata\Ashburton\wa\mr.txt", "line", 100010, 100110, None, 0, None)
#texttools.selectBetween("C:\marcel\ASH\linedata\Ashburton\wa\GSWA_P1134MAGREORDERED.dat", "line", 100010, 100110)
