import numpy as np
import matplotlib.pyplot as plt
import scipy
import os

class Statistics(object):
    def __init__(self, x, y, header=True, txtpath=None):
        self.outpath = None
        self.txtpath = txtpath
        self.header = header
        self.x = x
        self.y = y
        self.slope, self.intercept, self.r_value, self.p_value, self.std_err = scipy.stats.linregress(x, y)
        if type(self.x) is not np.ndarray:
            xarr = np.array(self.x)
        self.regression_line = self.slope*xarr+self.intercept
        
    def fileOpener(self, path, mode):
        try:
            file = open(path, mode)
        except IOError:
            return None
        else:
            return file
    
    def writeStats(self):
        if self.txtpath is not None:
            path = self.txtpath + ".txt"
            if self.header and not os.path.isfile(path):
                fw = self.fileOpener(path, "w")
                fw.write("slope intercept r_value p_value std_err layer\n")
            else:
                fw = self.fileOpener(path, "a")
            towrite = [self.slope.astype(str), self.intercept.astype(str), self.r_value.astype(str), self.p_value.astype(str), self.std_err.astype(str)]
            towrite.append(self.outpath)
            fw.write(" ".join(towrite) + "\n")
            fw.close()
        else:
            path = self.outpath + ".txt"
            if self.header and not os.path.isfile(path):
                fw = self.fileOpener(path, "w")
                fw.write("slope intercept r_value p_value std_err layer\n")
            else:
                fw = self.fileOpener(path, "a")
            towrite = [self.slope.astype(str), self.intercept.astype(str), self.r_value.astype(str), self.p_value.astype(str), self.std_err.astype(str)]
            towrite.append(self.outpath)
            fw.write(" ".join(towrite) + "\n")
            fw.close()
            
    
    def writePlot(self):
        fig = plt.figure()
        plt.plot(self.x, self.y, "ro", self.x, self.regression_line, "--k")
        plt.savefig(self.outpath + ".png")
        plt.close(fig)
        
    def save(self, path):
        outpath, suffix = os.path.splitext(path) # get suffix and path to file
        self.outpath = outpath
        
        self.writeStats()
        self.writePlot()
        