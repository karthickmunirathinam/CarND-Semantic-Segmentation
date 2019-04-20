#!/usr/bin/env python3
import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))

# --------------------
#  Set Hyperparameters
# --------------------
EPOCHS = 25
BATCH_SIZE = 8
L2_REGULARIZER = 1e-3
STDDEV = 0.01
LEARNING_RATE = 0.0001
DROPOUT_PROB = 0.5

def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    # TODO: Implement function
    #   Use tf.saved_model.loader.load to load the model and weights
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0'
    vgg_keep_prob_tensor_name = 'keep_prob:0'
    vgg_layer3_out_tensor_name = 'layer3_out:0'
    vgg_layer4_out_tensor_name = 'layer4_out:0'
    vgg_layer7_out_tensor_name = 'layer7_out:0'

    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    graph = tf.get_default_graph()
    image_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer3_out = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer4_out = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer7_out = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)

    return image_input, keep_prob, layer3_out, layer4_out, layer7_out
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    layer7a_out = tf.layers.conv2d(vgg_layer7_out, num_classes, 1,
                                   padding= 'same',
                                   kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                   kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))

    layer4a_in1 = tf.layers.conv2d_transpose(layer7a_out, num_classes, 4,
                                             2,
                                             padding= 'same',
                                             kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                             kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))

    layer4a_in2 = tf.layers.conv2d(vgg_layer4_out, num_classes, 1,
                                   padding= 'same',
                                   kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                   kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))

    # Skip Connections
    layer4a_out = tf.add(layer4a_in1, layer4a_in2)

    layer3a_in1 = tf.layers.conv2d_transpose(layer4a_out, num_classes, 4,
                                             2,
                                             padding= 'same',
                                             kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                             kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))

    layer3a_in2 = tf.layers.conv2d(vgg_layer3_out, num_classes, 1,
                                   padding= 'same',
                                   kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                   kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))

    # Skip Connections
    layer3a_out = tf.add(layer3a_in1, layer3a_in2)

    # logits
    nn_last_layer = tf.layers.conv2d_transpose(layer3a_out, num_classes, 16,
                                               8,
                                               padding= 'same',
                                               kernel_initializer= tf.random_normal_initializer(stddev=STDDEV),
                                               kernel_regularizer= tf.contrib.layers.l2_regularizer(L2_REGULARIZER))
    return nn_last_layer
tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    correct_label = tf.reshape(correct_label, (-1, num_classes))

    # Loss
    cross_entropy_loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=correct_label))
    # Optimizer
    train_op = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cross_entropy_loss)

    return logits, train_op, cross_entropy_loss
tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    sess.run(tf.global_variables_initializer())

    print("Training.....")
    for i in range(epochs):
        print("Epoch {} .....".format(i+1))
        for image, label in get_batches_fn(batch_size):
            _, loss = sess.run([train_op, cross_entropy_loss],
                               feed_dict={input_image: image,
                                          correct_label: label,
                                          keep_prob: DROPOUT_PROB,
                                          learning_rate: LEARNING_RATE})
            print("Loss = {:.3f}".format(loss))
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)  # KITTI dataset uses 160x576 images
    data_dir = './data'
    runs_dir = './runs'
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    helper.maybe_download_pretrained_vgg(data_dir)

    correct_label = tf.placeholder(tf.int32, [None, None, None, num_classes], name='correct_label')
    learning_rate = tf.placeholder(tf.float32, name='learning_rate')

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        input_image, keep_prob, vgg_layer3_out, vgg_layer4_out, vgg_layer7_out = load_vgg(sess, vgg_path)
        nn_last_layer = layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes)
        logits, train_op, cross_entropy_loss = optimize(nn_last_layer, correct_label, learning_rate, num_classes)

        train_nn(sess, EPOCHS, BATCH_SIZE, get_batches_fn, train_op, cross_entropy_loss, input_image,
                 correct_label, keep_prob, learning_rate)

        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)

if __name__ == '__main__':
    run()
