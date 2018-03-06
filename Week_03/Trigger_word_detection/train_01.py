#_*_coding:utf-8 _*_
import numpy as np
from pydub import AudioSegment
import random
import sys
import io
import os
import glob
import IPython
from td_utils import *

IPython.display.Audio("./raw_data/activates/1.wav")
IPython.display.Audio("./raw_data/negatives/4.wav")
IPython.display.Audio("./raw_data/backgrounds/1.wav")

IPython.display.Audio("audio_examples/example_train.wav")

x = graph_spectrogram("audio_examples/example_train.wav")

_, data = wavfile.read("audio_examples/example_train.wav")
print("Time steps in audio recording before spectrogram ", data[:, 0].shape)
print("Time steps in input after spectrogram ", x.shape)

Tx = 5511       # The number of time steps input to the model from the spectrogram
n_freq = 101        # Number of frequencies input to the model at each time step of the spectrogram.
Ty = 1375           # The number of time steps in the output of our model.

"""
Generating a single training example.
"""
activates, negatives, backgrounds = load_raw_audio()
print(len(activates))
print("background len: " + str(len(backgrounds[0])))
print("activate[0] len: " + str(len(activates[0])))
print("activate[1] len: " + str(len(activates[1])))

def get_random_time_segment(segment_ms):
    """
    Gets a random time segment of duration segment_ms in a 10,000 ms audio clip.
    :param segment_ms: -- the duration of the audio clip in ms("ms" stands for "milliseconds").
    :return:
    segment_time -- a tuple of (segment_start, segment_end) in ms.
    """
    segment_start = np.random.randint(low=0, high=10000-segment_ms)
    segment_end = segment_start + segment_ms - 1

    return (segment_start, segment_end)

def is_overlapping(segment_time, previous_segments):
    """
    Checks if the time of a segment overlaps with the times of existing segments.
    :param segment_time: -- a tuple of (segment_start, segment_end) for the new segment.
    :param previous_segments: -- a list of tuples of (segment_start, segment_end) for the existing segments.
    :return:
    True if the time segment overlaps with any of the existing segment, False otherwise.
    """
    segment_start, segment_end = segment_time
    # Step 1: Initialize overlap as a "False" flag.
    overlap = False
    # Step 2: loop over the previous_segments start and end times.
    # Compute start/end times and set the flag to True if there is an overlap.
    for previous_start, previous_end in previous_segments:
        if previous_start <= segment_end and previous_end >= segment_start:
            overlap = True

    return overlap

overlap1 = is_overlapping((950, 1430), [(2000, 2550), (260, 949)])
overlap2 = is_overlapping((2305, 2950), [(824, 1532), (1900, 2305), (3424, 3656)])
print("Overlap 1 = ", overlap1)
print("Overlap 2 = ", overlap2)

def insert_audio_clip(background, audio_clip, previous_segments):
    """
    Insert a new audio segment over the background noise at a random time step, ensuring that the
    audio segment dose not overlap with existing segments.
    :param backend: -- a 10 second background audio recording.
    :param audio_clip: -- the audio clip to be inserted/overlaid.
    :param previous_segments: -- times where audio segments have already been placed.
    :return:
    new_background -- the updated background audio.
    """
    # Get the duration of the audio clip in ms
    segment_ms = len(audio_clip)
    # Step 1: Use one of the helper functions to pick a random time segment onto which to insert the new audio clip.
    segment_time = get_random_time_segment(segment_ms)
    # Step 2: Check if the new segment_time overlaps with one of the previous_segments.
    # If so, keep picking new segment_time at random until it doesn't overlap.
    while is_overlapping(segment_time, previous_segments):
        segment_time = get_random_time_segment(segment_ms)
    # Step 3: Add the new segment_time to the list of previous_segments.
    previous_segments.append(segment_time)
    # Step 4: Superpose audio segment and background.
    new_background = background.overlay(audio_clip, position=segment_time[0])

    return new_background, segment_time

np.random.seed(5)
audio_clip, segment_time = insert_audio_clip(backgrounds[0], activates[0], [(3790, 4400)])
audio_clip.export("insert_test.wav", format="wav")
print("Segment Time: ", segment_time)
IPython.display.Audio("insert_test.wav")

IPython.display.Audio("audio_examples/insert_reference.wav")

def insert_ones(y, segment_end_ms):
    """
    Update the label vector y. The labels of the 50 output steps strictly after the end of the segment
    should be set to 1. By strictly we mean that the label of segment_end_y should be 0 while, the 50 followinf labels should be ones.
    :param y: -- numpy array of shape (1, Ty), the labels of the training example.
    :param segment_end_ms: -- the end time of the segment in ms.
    :return:
    y -- updated labels.
    """
    # Duration of the background (int terms of spectrogram time-steps)
    segment_end_y = int(segment_end_ms * Ty / 10000.0)
    # Add 1 to the correct index in the background label (y)
    for i in range(segment_end_y+1, segment_end_y + 51):
        if i < Ty:
            y[0, i] = 1
    return y

arr1 = insert_ones(np.zeros((1, Ty)), 9700)
plt.plot(insert_ones(arr1, 4251)[0, :])
print("santity checks: ", arr1[0][1333], arr1[0][634], arr1[0][635])

def create_training_example(background, activates, negatives):
    """
    Creates a training example with a given background, activates, and negatives.
    :param background: -- a 10 second background audio recording.
    :param activates: -- a list of audio segments of the word "activate".
    :param negatives: -- a list of audio segments of random words that are not "activate".
    :return:
    x -- the spectrogram of the training example.
    y -- the label at each time step of the spectrogram.
    """
    # Set the random seed
    np.random.seed(18)
    # Make background quieter.
    background = background - 20
    # Step 1: Initialize y (label vector) of zeros.
    y = np.zeros((1, Ty))
    # Step 2: Initialize segment time as empty list.
    previous_segments = []
    # Select 0-4 random "activate" audio clips from the entire list of "activates" recordings.
    number_of_activates = np.random.randint(0, 5)
    random_indices = np.random.randint(len(activates), size=number_of_activates)
    random_activates = [activates[i] for i in random_indices]
    # Step 3: Loop over randomly selected "activate" clips and insert in background.
    for random_activate in random_activates:
        # Insert the audio clip on the background
        background, segment_time = insert_audio_clip(background, random_activate, previous_segments)
        # Retrieve segment_start and segment_end from segment_time
        segment_start, segment_end = segment_time
        # Insert labels in "y"
        y = insert_ones(y, segment_end)

    # Select 0-2 random negatives audio recordings from the entire list of "negatives" recordings.
    number_of_negatives = np.random.randint(0, 3)
    random_indices = np.random.randint(len(negatives), size=number_of_negatives)
    random_negatives = [negatives[i] for i in random_indices]

    # Step 4: Loop over randomly selected negative clips and insert in background.
    for random_negative in random_negatives:
        # Insert the audio clip on the background.
        background, _ = insert_audio_clip(background, random_negative, previous_segments)
    # Standardize the volume of the audio clip.
    background = match_target_amplitude(background, -20.0)
    # Export new training example.
    file_handle = background.export("train" + ".wav", format="wav")
    print("File (train.wav) was saved in your directory.")

    # Get and plot spectrogram of the new recording (background with superposition of positive and negatives)
    x = graph_spectrogram("train.wav")

    return x, y

x, y = create_training_example(backgrounds[0], activates, negatives)

IPython.display.Audio("train.wav")
IPython.display.Audio("audio_examples/train_reference.wav")
plt.plot(y[0])

"""
Full training set.
"""
X = np.load("./XY_train/X.npy")
Y = np.load("./XY_train/Y.npy")

X_dev = np.load("./XY_dev/X_dev.npy")
Y_dev = np.load("./XY_dev/Y_dev.npy")

from keras.callbacks import ModelCheckpoint
from keras.models import Model, load_model, Sequential
from keras.layers import Dense, Activation, Dropout, Input, Masking, TimeDistributed, LSTM, Conv1D
from keras.layers import GRU, Bidirectional, BatchNormalization, Reshape
from keras.optimizers import Adam

def model(input_shape):
    """
    Function creating the model's graph in Keras.
    :param input_shape: -- shape of the model's input data(using Keras conventions).
    :return:
    model -- Keras model instance.
    """
    X_input = Input(shape=input_shape)
    # Step 1: Conv layer.
    X = Conv1D(filters=196, kernel_size=15, strides=4)(X_input)
    X = BatchNormalization()(X)
    X = Activation('relu')(X)
    X = Dropout(rate=0.8)(X)

    # Step 2: First GRU Layer.
    X = GRU(units=128, return_sequences=True)(X)
    X = Dropout(rate=0.8)(X)
    X = BatchNormalization()(X)

    # Step 3: Second GRU Layer.
    X = GRU(units=128, return_sequences=True)(X)
    X = Dropout(rate=0.8)(X)
    X = BatchNormalization()(X)
    X = Dropout(rate=0.8)(X)

    # Step 4: Time-distribted dense layer.
    X = TimeDistributed(Dense(units=1, activation="sigmoid"))(X)

    model = Model(inputs=X_input, outputs=X)

    return model

model = model(input_shape=(Tx, n_freq))
model.summary()
model = load_model('./models/tr_model.h5')
opt = Adam(lr=0.0001, beta_1=0.9, beta_2=0.999, decay=0.01)
model.compile(loss='binary_crossentropy', optimizer=opt, metrics=["accuracy"])
model.fit(X, Y, batch_size=5, epochs=1)
loss, acc = model.evaluate(X_dev, Y_dev)
print("Dev set accuracy = ", acc)

def detect_triggerword(filename):
    """

    :param filename:
    :return:
    """
    plt.subplot(2, 1, 1)
    x = graph_spectrogram(filename)
    # the spectrogram outputs (freqs, Tx) and we want (Tx, freqs) to input into the model.
    x = x.swapaxes(0, 1)
    x = np.expand_dims(x, axis=0)
    predictions = model.predict(x)

    plt.subplot(2, 1, 2)
    plt.plot(predictions[0, :, 0])
    plt.ylabel('probability')
    plt.show()

    return predictions

chime_file = "audio_examples/chime.wav"
def chime_on_activate(filename, predictions, threshold):
    """

    :param filename:
    :param predictions:
    :param threshold:
    :return:
    """
    audio_clip = AudioSegment.from_wav(filename)
    chime = AudioSegment.from_wav(chime_file)
    Ty = predictions.shape[1]
    # Step 1: Initialize the number of consecutive output steps to 0.
    consecutive_timesteps = 0
    # Step 2: Loop over the output steps in the y.
    for i in range(Ty):
        # Step 3: Increment consecutive output steps.
        consecutive_timesteps += 1
        # Step 4: If prediction is higher than the threshold and more than 75 consecutive output steps have passed.
        if predictions[0, i, 0] > threshold and consecutive_timesteps > 75:
            # Step 5: Superpose audio and background using pydub.
            audio_clip = audio_clip.overlay(chime, position=((i / Ty) * audio_clip.duration_seconds) * 1000)
            # Step 6: Reset consecutive output steps to 0.
            consecutive_timesteps = 0

    audio_clip.export("chime_output.wav", format='wav')

IPython.display.Audio("./raw_data/dev/1.wav")
IPython.display.Audio("./raw_data/dev/2.wav")

filename = "./raw_data/dev/1.wav"
prediction = detect_triggerword(filename)
chime_on_activate(filename, prediction, 0.5)
IPython.display.Audio("./chime_output.wav")

filename = "./raw_data/dev/2.wav"
prediction = detect_triggerword(filename)
chime_on_activate(filename, prediction, 0.5)
IPython.display.Audio("./chime_output.wav")
