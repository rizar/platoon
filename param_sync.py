class ParamSyncRule(object):
    """
    Abstract parameter synchronisation rule.

    This abstract class defines the interface that should be followed by
    implementations of parameter synchronization rules for distributed
    training.
    """

    def update_params(self, local_params, master_params):
        """
        Perform an inplace update of the master parameters and returns the
        parameters based on a certain parameter synchronisation rule.
        """
        raise NotImplementedError()


class EASGD(ParamSyncRule):
    """
    Implementation of the EASGD parameter sync rule.

    According to this rule, every N iterations, a worker synchronises his
    parameters with the master parameters. This is done by moving each set of
    parameters toward the other by an amount proportional to the difference
    between the individual params (this proportion is parametrized by `alpha`).

    The sync equations are as follow:
    diff = w_worker - w_master
    w_worker = w_worker - alpha * diff
    w_master = w_master + alpha * diff

    NOTE : if alpha=0 is used, there is no synchronization of the
    parameters meaning that each worker is independently training using SGD.

    This algorithm is described in more details in the following paper:
    http://arxiv.org/abs/1412.6651
    """

    def __init__(self, alpha):
        self.set_alpha(alpha)

    def get_alpha(self):
        return self.alpha

    def set_alpha(self, alpha):
        self.alpha = alpha

    def update_params(self, local_params, master_params):
        """
        Perform an inplace update of the worker parameters and the central
        parameters based on a certain parameter synchronisation rule.
        """
        for p_local, p_master in zip(local_params, master_params):
            diff = self.alpha * (p_local - p_master)

            # The -= and += operations are inplace for nupy arrays
            p_local -= diff
            p_master += diff
