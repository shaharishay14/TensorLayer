#! /usr/bin/python
# -*- coding: utf-8 -*-

import tensorflow as tf

import tensorlayer as tl
from tensorlayer import logging
from tensorlayer.decorators import deprecated_alias
from tensorlayer.layers.core import Layer
from tensorlayer.layers.utils import (quantize_active_overflow, quantize_weight_overflow)

__all__ = [
    'QuanDense',
]


class QuanDense(Layer):
    """The :class:`QuanDense` class is a quantized fully connected layer with BN, which weights are 'bitW' bits and the output of the previous layer
    are 'bitA' bits while inferencing.

    Parameters
    ----------
    n_units : int
        The number of units of this layer.
    act : activation function
        The activation function of this layer.
    bitW : int
        The bits of this layer's parameter
    bitA : int
        The bits of the output of previous layer
    use_gemm : boolean
        If True, use gemm instead of ``tf.matmul`` for inference. (TODO).
    W_init : initializer
        The initializer for the weight matrix.
    b_init : initializer or None
        The initializer for the bias vector. If None, skip biases.
    in_channels: int
        The number of channels of the previous layer.
        If None, it will be automatically detected when the layer is forwarded for the first time.
    name : None or str
        A unique layer name.

    """

    def __init__(
            self,
            n_units=100,
            act=None,
            bitW=8,
            bitA=8,
            use_gemm=False,
            W_init=tl.initializers.truncated_normal(stddev=0.05),
            b_init=tl.initializers.constant(value=0.0),
            in_channels=None,
            name=None,  #'quan_dense',
    ):
        super().__init__(name, act=act)
        self.n_units = n_units
        self.bitW = bitW
        self.bitA = bitA
        self.use_gemm = use_gemm
        self.W_init = W_init
        self.b_init = b_init
        self.in_channels = in_channels

        if self.in_channels is not None:
            self.build((None, self.in_channels))
            self._built = True

        logging.info(
            "QuanDense  %s: %d %s" %
            (self.name, n_units, self.act.__name__ if self.act is not None else 'No Activation')
        )

    def __repr__(self):
        actstr = self.act.__name__ if self.act is not None else 'No Activation'
        s = ('{classname}(n_units={n_units}, ' + actstr)
        s += ', bitW={bitW}, bitA={bitA}'
        if self.in_channels is not None:
            s += ', in_channels=\'{in_channels}\''
        if self.name is not None:
            s += ', name=\'{name}\''
        s += ')'
        return s.format(classname=self.__class__.__name__, **self.__dict__)

    def build(self, inputs_shape):
        if len(inputs_shape) != 2:
            raise Exception("The input dimension must be rank 2, please reshape or flatten it")

        if self.in_channels is None:
            self.in_channels = inputs_shape[1]

        if self.use_gemm:
            raise Exception("TODO. The current version use tf.matmul for inferencing.")

        n_in = inputs_shape[-1]
        self.W = self._get_weights("weights", shape=(n_in, self.n_units), init=self.W_init)
        if self.b_init is not None:
            self.b = self._get_weights("biases", shape=int(self.n_units), init=self.b_init)

    def forward(self, inputs):

        inputs = quantize_active_overflow(inputs, self.bitA)

        W_ = quantize_weight_overflow(self.W, self.bitW)

        # outputs = tf.matmul(inputs, self.W)
        outputs = tf.matmul(inputs, W_)  # hao dong change to this

        if self.b_init is not None:
            outputs = tf.nn.bias_add(outputs, self.b, name='bias_add')
        if self.act:
            outputs = self.act(outputs)
        return outputs
