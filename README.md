# platoon
Experimental multi-GPU mini-framework for Theano

It supports **data-parallelism** inside one compute node, not
model-parallelism. For model-parallelism check [Theano multiple GPUs
tutorial](http://deeplearning.net/software/theano/tutorial/using_multi_gpu.html).

This framework is still a prototype. It's interfaces is not polished and it is
likely to undergo changes in the future.

The framework allows multiple data-parallel algorithms, but only
[EASGD](http://arxiv.org/abs/1412.6651) is currently implemented.

There are working examples in the examples directory.

In Platoon, there are two main components : workers, and controllers.
Workers do the bulk of the work (training, monitoring, ...). Controllers
interact with multiple workers to coordinate their work, collect the results
and decide how to act on them. To use Platoon, you will need to implement both
your workers and your controller but Platoon provides helper classes to
facilitate this.

The steps below describe what needs to be done to use Platoon for
data-parallelism. The LSTM example in the folder 'example' was implemented
following these steps and should be referred to for guidance.

Timing of the LSTM example on 2 k80
-----------------------------------

The timing is about efficiency of computation, not efficiency of
training.  So the parameter alpha is constant. The number of minibatch
is fixed as the hyper-parameter. The sync is also fixed to be after 10
mini-batch of computation.

With 1 worker, Platoon does not give you any advantage. This is
there just to show the overhead of the EASGD implementation.  Normal
is without this framework and with SGD, also there for overhead evaluation.

Normal | 1 GPU | 2 GPUs | 3 GPUs | 4 GPUs
-------+-------+--------+--------+-------
  870s |  912s |  477s  |  329s  |  254s
 1.00x | 0.95x | 1.82x  | 2.65x  | 3.42x


Real usage consideration
------------------------

The optimal (as in more efficient for learning) hyper-parameters values are
dependant on the number of workers.  At least, consider tuning the
learning rate and the alpha parameter of EASGD.

How to change the alpha hyper-parameter isn't clear. An alpha of 0.5
for the LSTM example with 2 workers seem to have good training
efficency for this model/dataset/hyper-parameter combination.

Using alpha = 1/N (with N being the number of workers) might be a
reasonable guideline but the experiments performed with Platoon are
insufficient to conclude anything.

In the EASGD paper it is shown that in some cases a larger number of
workers can result in a better test error.

Implementing a controller
-------------------------

These steps describe how to implement the Python script that will launch
your controller. In the included LSTM example, both of these steps are done
in the file lstm_master.py

1) Define which commands your controller can receive and how it responds to
them.

This is done by creating a new class that inherits from channel.Lieutenant
and having it override the method 'handle_control()' which will be called
whenever your controller receives a request from a worker.

2) Instantiate and launch your custom controller.

Create a script that will instantiate your custom controller. Once this is
done, define the port on which the controller should listen by calling the
function 'init_control'. Finally, call your controller's 'serve' method which
will make him ready to receive requests from workers.

Implementing the workers
------------------------

These steps describe how to start with a script that performs stand-alone
training of a machine learning model and adapt it to serve as a worker in
Platoon.

1) Add a new parameter to the script which will be used during execution to
know whether the worker is the first one to be launched and should create the
central parameters or not.

2) Before entering the main loop, the script must create an instance of the
class channel.Soldier, providing it with the same port number as used to
initialize the controller. It is not necessary to sub-class Soldier, you can
instantiate it directly. This object will provide the necessary methods to
handle communication with the controller.

3) After the model has been built and the parameters initialized,
initialize the central parameters by calling the Soldier's
init_shared_params() method. Every worker should call this method but only
the first worker to be launched should provide the parameter cleanup=True,
the other workers should pass False or provide no value for this parameter.

4) In the main loop, instead of deciding when to train and when to monitor
performance, the worker should send control request to the controller to know
what action it should take, according to the communication protocol
established in the controller's 'handle_control()' method.

5) In the main loop, whenever the worker has performed 'N' (a hyper-parameter)
iterations of training, it should synchronize it's parameters with the central
parameters using it's Soldier's 'sync_params()' method.

Putting it all together
-----------------------

1) Launch your controller. Wait until it has reached the point where it is
ready to serve requests.

2) Launch the first worker. Wait until it has performed the initialization of
the central parameters.

3) Launch additional workers if desired.
