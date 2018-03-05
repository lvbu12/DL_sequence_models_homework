# _*_coding:utf-8_*_
from __future__ import print_function
import IPython
import sys
from music21 import *
import numpy as np
from grammar import *
from qa import *
from preprocess import *
from music_utils import *
from data_utils import load_music_utils, generate_music, predict_and_sample
from keras.models import load_model, Model
from keras.layers import Dense, Activation, Dropout, Input, LSTM, Reshape, Lambda, RepeatVector
# from keras.initializers import glorot_uniform
from keras.utils import to_categorical
from keras.optimizers import Adam
# from keras import backend as K

X, Y, n_values, indices_values = load_music_utils()
# print("n_values ", n_values)
# print(indices_values.keys())
# print(indices_values.values())
# print('shape of X: ', X.shape)
# print('number of train examples: ', X.shape[0])
# print('Tx (length of sequence): ', X.shape[1])
# print('total # of unique value: ', n_values)
# print('Shape of Y: ', Y.shape)
n_a = 64
reshapor = Reshape((1, 78))
LSTM_cell = LSTM(n_a, return_state=True)
densor = Dense(n_values, activation='softmax')

def djmodel(Tx, n_a, n_values):
    """
    Implement the model.
    :param Tx: -- length of the sequence in a corpus.
    :param n_a: -- the number of activations used in our model.
    :param n_values: -- number of unique values in the music data.
    :return:
    model -- a keras model with the
    """
    # Define the input of your model in a shape
    X = Input(shape=(Tx, n_values))
    # Define s0, initial hidden state for the decoder LSTM
    a0 = Input(shape=(n_a,), name='a0')
    c0 = Input(shape=(n_a,), name='c0')
    a = a0
    c = c0
    # Step 1: Create empty list append the outputs while you iterate.
    outputs = []
    # Step 2: Loop
    for t in range(Tx):
        # Step 2.A: select the "t"th time step vector from X.
        x = Lambda(lambda x: X[:, t, :])(X)
        # Step 2.B: Use reshapor to reshape x to be (1, n_values)
        x = reshapor(x)
        # Step 2.C: Perform one step of the LSTM_cell
        a, _, c = LSTM_cell(x, initial_state=[a, c])
        # Step 2.D: apply densor to the hidden state output of LSTM_cell
        out = densor(a)
        # Step 2.E: add the output to "outputs"
        outputs.append(out)

    # Step 3: Create model instance.
    model = Model(inputs=[X, a0, c0], outputs=outputs)
    return model

model = djmodel(Tx=30, n_a=64, n_values=78)
opt = Adam(lr=0.01, beta_1=0.9, beta_2=0.999, decay=0.01)
model.compile(optimizer=opt, loss='categorical_crossentropy')

# Initialize a0 and c0 for the LSTM's initial state to be zero.
m = 60
a0 = np.zeros((m, n_a))
c0 = np.zeros((m, n_a))

model.fit([X, a0, c0], list(Y), epochs=100)

def music_inference_model(LSTM_cell, densor, n_values=78, n_a=64, Ty=100):
    """
    Uses the trained "LSTM_cell" and "densor" from model() to generate a sequence of values.

    :param LSTM_cell: -- the trained "LSTM_cell" from model(), Keras layer object.
    :param densor: -- the trained "densor" from model(), Keras layer object.
    :param n_values: -- integer, number of unique values.
    :param n_a: -- number of units in the LSTM_cell.
    :param Ty: -- integer, number of time steps to generate.
    :return:
    inference_model -- Keras model instance.
    """
    # Define the input your model with a shape.
    x0 = Input(shape=(1, n_values))
    # Define s0, initial hidden state for decoder LSTM
    a0 = Input(shape=(n_a,), name='a0')
    c0 = Input(shape=(n_a,), name='c0')
    a = a0
    c = c0
    x = x0
    # Step 1: Create an emtpy list of "outputs" to later store your predicted values.
    outputs = []
    # Step 2: Loop over Ty and generate a value at every time step
    for t in range(Ty):
        # Step 2.A: Perform one step of LSTM_cell
        a, _, c = LSTM_cell(x, initial_state=[a, c])
        # Step 2.B: Apply Dense layer to the hidden state output of the LSTM_cell
        out = densor(a)
        # Step 2.C: Append the prediction "out" to "outputs".
        outputs.append(out)
        # Step 2.D: Select the next value according to "out", and set "x" to be the one-hot representation of the
        # selected value, which will be passed as the input to LSTM_cell on the next step.
        # We have provided the line of code you need to do this.
        x = Lambda(one_hot)(out)
    # Step 3: Create model instance with the correct "inputs" and "outputs"
    inference_model = Model(inputs=[x0, a0, c0], outputs=outputs)
    return inference_model

inference_model = music_inference_model(LSTM_cell, densor, n_values=78, n_a=64, Ty=50)
inference_model.predict()

x_initializer = np.zeros((1, 1, 78))
a_initializer = np.zeros((1, n_a))
c_initializer = np.zeros((1, n_a))

def predict_and_sample(inference_model, x_initializer=x_initializer, a_initializer=a_initializer, c_initializer=c_initializer):
    """
    Predicts the next value of values using the inference model
    :param inference_model:
    :param x_initializer:-- numpy array of shape (1, 1, 78), one-hot vector initializing the values generation.
    :param a_initializer:-- numpy array of shape (1, n_a), initializing the hidden state of LSTM_cell.
    :param c_initializer:-- numpy array of shape (1, n_a), initializing the cell state of the LSTM_cell.
    :return:
    results -- numpy array of shape (Ty, 78), matrix of one-hot vectors representing the values generation.
    indices -- numpy array of shape (Ty, 1), matrix of indices representing the values generation.
    """
    # Step 1: Use your inference model to predict an output sequence given x_initializer.
    pred = inference_model.predict([x_initializer, a_initializer, c_initializer])
    # Step 2: Convert "Pred" into an np.array() of indices with the maximum probability.
    indices = np.argmax(pred, axis=1)
    # # Step 3: Convert indices to one-hot vectors, the shape of the results should be (1, )
    results = to_categorical(indices, num_classes=n_values)

    return results, indices

results, indices = predict_and_sample(inference_model, x_initializer, a_initializer, c_initializer)

print("np.argmax(results[12]) = ", np.argmax(results[12]))
print("np.argmax(results[17]) =", np.argmax(results[17]))
print("list(indices[12:18]) =", list(indices[12:18]))

out_stream = generate_music(inference_model)

IPython.display.Audio('./data/30s_trained_model.mp3')

