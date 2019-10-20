from abc import ABC, abstractmethod
from typing import List, Set, Dict, Tuple, Optional, Union, Any, cast
import tensorflow as tf
import numpy as np

from Config import Config


class MultiHeadAttention(tf.keras.layers.Layer):
    def __init__(self, d_model, num_heads):
        super(MultiHeadAttention, self).__init__()
        self.num_heads = num_heads
        self.d_model = d_model

        assert d_model % self.num_heads == 0

        self.depth = d_model // self.num_heads

        self.wq = tf.keras.layers.Dense(d_model)
        self.wk = tf.keras.layers.Dense(d_model)
        self.wv = tf.keras.layers.Dense(d_model)

        self.attentation = tf.keras.layers.Attention()

        self.dense = tf.keras.layers.Dense(d_model)

    def split_heads(self, x, batch_size):
        """Split the last dimension into (num_heads, depth).
        Transpose the result such that the shape is (batch_size, num_heads, seq_len, depth)
        """
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.depth))

        return tf.transpose(x, perm=[0, 2, 1, 3])

    def call(self, v, k, q, mask):
        batch_size = tf.shape(q)[0]

        q = self.wq(q)  # (batch_size, seq_len, d_model)
        k = self.wk(k)  # (batch_size, seq_len, d_model)
        v = self.wv(v)  # (batch_size, seq_len, d_model)

        q = self.split_heads(q, batch_size)  # (batch_size, num_heads, seq_len_q, depth)
        k = self.split_heads(k, batch_size)  # (batch_size, num_heads, seq_len_k, depth)
        v = self.split_heads(v, batch_size)  # (batch_size, num_heads, seq_len_v, depth)

        mask = tf.expand_dims(mask, axis=1)
        scaled_attention = self.attentation([q, v, k], [mask, mask]) #(batch_size, num_heads, seq_len_q, depth)

        scaled_attention = tf.transpose(scaled_attention, perm=[0, 2, 1, 3])  # (batch_size, seq_len_q, num_heads, depth)

        concat_attention = tf.reshape(scaled_attention,(batch_size, -1, self.d_model))  # (batch_size, seq_len_q, d_model)

        output = self.dense(concat_attention)  # (batch_size, seq_len_q, d_model)

        return output


class EncoderLayer(tf.keras.layers.Layer):
    def __init__(self, d_model, num_heads, dff, rate=0.1):
        super(EncoderLayer, self).__init__()

        self.mha = MultiHeadAttention(d_model, num_heads)
        self.ffn_none_linear = tf.keras.layers.Dense(dff, activation='relu')
        self.ffn_linear = tf.keras.layers.Dense(d_model)

        self.layernorm1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)

        self.dropout1 = tf.keras.layers.Dropout(rate)
        self.dropout2 = tf.keras.layers.Dropout(rate)

    def call(self, inputs, **kwargs):
        x, mask = inputs
        attn_output = self.mha(x, x, x, mask)  # (batch_size, input_seq_len, d_model)
        attn_output = self.dropout1(attn_output, **kwargs) # (batch_size, input_seq_len, d_model)
        out1 = self.layernorm1(x + attn_output)  # (batch_size, input_seq_len, d_model)


        ffn_output = self.ffn_none_linear(out1) # (batch_size, input_seq_len, dff)
        ffn_output = self.ffn_linear(ffn_output) # (batch_size, input_seq_len, d_model)
        ffn_output = self.dropout2(ffn_output, **kwargs) # (batch_size, input_seq_len, d_model)
        out2 = self.layernorm2(out1 + ffn_output)  # (batch_size, input_seq_len, d_model)

        return out2 # (batch_size, input_seq_len, d_model)


if __name__ == '__main__':
    config = Config(set_defaults=True)
    ex_embedding = np.ones(shape=[10, config.MAX_CONTEXTS, config.CODE_VECTOR_SIZE,], dtype=np.float32) # (batch, max_contexts)
    ex_masks = np.ones(shape=[10, config.MAX_CONTEXTS,], dtype=np.float32) == 1  # (batch, max_contexts)
    embedding = tf.keras.layers.Input(shape=[config.MAX_CONTEXTS, config.CODE_VECTOR_SIZE,], dtype=tf.float32)
    masks = tf.keras.Input(shape=[config.MAX_CONTEXTS, ], dtype=tf.bool)
    #masks[0][-1] = False



    encoder1 = EncoderLayer(d_model=config.CODE_VECTOR_SIZE, dff=4 * config.CODE_VECTOR_SIZE, num_heads=8, rate=0.1)
    encoder2 = EncoderLayer(d_model=config.CODE_VECTOR_SIZE, dff=4 * config.CODE_VECTOR_SIZE, num_heads=8, rate=0.1)

    out1 = encoder1([embedding, masks])
    out2 = encoder2([out1, masks])
    model = tf.keras.Model(inputs=[embedding, masks], outputs=out2)
    #print(model.summary())
    print(model([ex_embedding, ex_masks]))
    