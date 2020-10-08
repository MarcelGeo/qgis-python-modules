import threading
from Queue import Queue
import time

class abstracting(object):
    def __init__(self, abstract):
        print 'Abstracting %s : ' % abstract
            # instead of really downloading the URL,
            # we just pretend and sleep
        time.sleep(2)

class abstractThreader(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            abstract= self.queue.get()
            abstractClass = abstracting(abstract)
            self.queue.task_done()

def Main(abstracts):
    mainQ = Queue()
    for x in range(8):
        thread = abstractThreader(mainQ)
        thread.setDaemon(True)
        thread.start()
    for abstract in abstracts:
        print "Queuweueueing : " + abstract
        mainQ.put(abstract)
    print "Waiting"
    mainQ.join()
    print "main complete"