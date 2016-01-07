import numpy
import time

import sys
sys.path.append('..')

import channel


class LSTMLieutenant(channel.Lieutenant):
    """
    This multi-process controller implements patience-based early-stopping SGD
    """

    def __init__(self, max_mb, patience, validFreq):
        """
        Initialize the LSTMLieutenant

        Parameters
        ----------
        max_mb : int
            Max number of minibatches to train on.
        patience: : int
            Training stops when this many minibatches have been trained on
            without any reported improvement.
        validFreq : int
            Number of minibatches to train on between every monitoring step.
        """

        channel.Lieutenant.__init__(self)
        self.patience = patience
        self.max_mb = int(max_mb)

        self.validFreq = validFreq
        self.uidx = 0
        self.eidx = 0
        self.history_errs = []
        self.bad_counter = 0

        self.stop = False
        self.valid = False
        self.start_time = None

    def handle_control(self, req):
        """
        Handles a control_request received from a worker

        Parameters
        ----------
        req : str or dict
            Control request received from a worker.
            The control request can be one of the following
            1) "next" : request by a worker to be informed of its next action
               to perform. The answers from the server can be 'train' (the
               worker should keep training on its training data), 'valid' (the
               worker should perform monitoring on its validation set and test
               set) or 'stop' (the worker should stop training).
            2) dict of format {"done":N} : used by a worker to inform the
                server that is has performed N more training iterations and
                synced its parameters. The server will respond 'stop' if the
                maximum number of training minibatches has been reached.
            3) dict of format {"valid_err":x, "test_err":x2} : used by a worker
                to inform the server that it has performed a monitoring step
                and obtained the included errors on the monitoring datasets.
                The server will respond "best" if this is the best reported
                validation error so far, otherwise it will respond 'stop' if
                the patience has been exceeded.
        """

        if req == 'next':
            if self.start_time is None:
                self.start_time = time.time()
            if self.stop:
                return 'stop'
            if self.valid:
                self.valid = False
                return 'valid'
            return 'train'
        if isinstance(req, dict):
            if 'done' in req:
                self.uidx += req['done']
                if self.uidx > self.max_mb:
                    self.stop = True
                    self.stop_time = time.time()
                    print "Training time (max_mb)  %fs" % (self.stop_time - self.start_time,)
                    print "Number of samples", self.uidx
                    return 'stop'
                if numpy.mod(self.uidx, self.validFreq) == 0:
                    self.valid = True
            if 'valid_err' in req:
                valid_err = req['valid_err']
                test_err = req['test_err']
                self.history_errs.append([valid_err, test_err])
                harr = numpy.array(self.history_errs)[:, 0]
                if valid_err <= harr.min():
                    self.bad_counter = 0
                    print "Best error valid:", valid_err, "test:", test_err
                    return 'best'
                if (len(self.history_errs) > self.patience and
                        valid_err >= harr[:-self.patience].min()):
                    self.bad_counter += 1
                    if self.bad_counter > self.patience:
                        self.stop_time = time.time()
                        print "Training time (patience) %fs" % (self.stop_time - self.start_time,)
                        print "Number of samples:", self.uidx
                        self.stop = True
                        return 'stop'


def lstm_control(dataset='imdb',
                 patience=10,
                 max_epochs=5000,
                 validFreq=370,
                 saveFreq=1110,
                 saveto=None,
                 ):

    # TODO: have a better way to set max_mb
    l = LSTMLieutenant(max_mb=(5000*1998)/10, patience=patience,
                       validFreq=validFreq)

    l.init_control(port=5567)
    print "Lieutenant is ready"
    l.serve()

if __name__ == '__main__':
    lstm_control()
