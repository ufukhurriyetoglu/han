from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import tempfile
import log_helper
from log_helper import log
from data_reader import read_data_sets
from data_reader import get_real_images
from data_reader import dense_to_one_hot
import tensorflow as tf
import tensorflow.contrib.slim as slim
from time import gmtime, strftime
import numpy as np
np.set_printoptions(threshold=np.inf)

log_helper.initLogging('log/' + strftime("%Y-%m-%d-%H:%M:%S", gmtime()) + '.log')

FLAGS = None
# CHAR_NUM = 205
CHAR_NUM = 8877

def deepnn(x):
    batch_norm_params = {'is_training': True, 'decay': 0.9, 'updates_collections': None}
    with slim.arg_scope([slim.conv2d, slim.fully_connected], normalizer_fn=slim.batch_norm, normalizer_params=batch_norm_params):
        keep_prob = tf.placeholder(dtype=tf.float32, shape=[], name='keep_prob')
        x_image = tf.reshape(x, [-1, 64, 64, 1])
        conv_1 = slim.conv2d(x_image, 64, [3, 3], 1, padding='SAME', scope='conv1')
        max_pool_1 = slim.max_pool2d(conv_1, [2, 2], [2, 2], padding='SAME')
        conv_2 = slim.conv2d(max_pool_1, 128, [3, 3], padding='SAME', scope='conv2')
        max_pool_2 = slim.max_pool2d(conv_2, [2, 2], [2, 2], padding='SAME')
        conv_3 = slim.conv2d(max_pool_2, 256, [3, 3], padding='SAME', scope='conv3')
        max_pool_3 = slim.max_pool2d(conv_3, [2, 2], [2, 2], padding='SAME')
        conv_4 = slim.conv2d(max_pool_3, 512, [3, 3], padding='SAME', scope='conv4')
        conv_5 = slim.conv2d(conv_4, 1024, [3, 3], padding='SAME', scope='conv5')
        conv_6 = slim.conv2d(conv_5, 1024, [3, 3], padding='SAME', scope='conv6')
        conv_7 = slim.conv2d(conv_6, 1024, [3, 3], padding='SAME', scope='conv7')
        max_pool_7 = slim.max_pool2d(conv_7, [2, 2], [2, 2], padding='SAME')

        flatten = slim.flatten(max_pool_7)
        fc1 = slim.fully_connected(slim.dropout(flatten, keep_prob), 2048, activation_fn=tf.nn.relu, scope='fc1')
        logits = slim.fully_connected(slim.dropout(fc1, keep_prob), CHAR_NUM, activation_fn=None, scope='fc2')
    return logits, keep_prob

def main(_):
  # Import data
  mnist = read_data_sets(FLAGS.data_dir)

  # Create the model
  x = tf.placeholder(tf.float32, [None, 4096])

  # Define loss and optimizer
  y_ = tf.placeholder(tf.float32, [None, CHAR_NUM])

  # Build the graph for the deep net
  y_conv, keep_prob = deepnn(x)

  with tf.name_scope('loss'):
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(labels=y_,
                                                            logits=y_conv)
  cross_entropy = tf.reduce_mean(cross_entropy)

  with tf.name_scope('adam_optimizer'):
    global_step = tf.get_variable("step", [], initializer=tf.constant_initializer(0.0), trainable=False)
    rate = tf.train.exponential_decay(1e-4, global_step, decay_steps=2000, decay_rate=0.99, staircase=True)
    train_step = tf.train.AdamOptimizer(rate).minimize(cross_entropy, global_step=global_step)

  with tf.name_scope('accuracy'):
    correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(y_, 1))
    correct_prediction = tf.cast(correct_prediction, tf.float32)
  accuracy = tf.reduce_mean(correct_prediction)

  graph_location = tempfile.mkdtemp()
  log('Saving graph to: %s' % graph_location)
  train_writer = tf.summary.FileWriter(graph_location)
  train_writer.add_graph(tf.get_default_graph())

  with tf.Session() as sess:
      saver = tf.train.Saver()

      if FLAGS.read_from_checkpoint:
          ckpt = tf.train.get_checkpoint_state(FLAGS.checkpoint_dir)
          if ckpt and ckpt.model_checkpoint_path:
              saver.restore(sess, ckpt.model_checkpoint_path)
          else:
              sess.run(tf.global_variables_initializer())
      else:
          sess.run(tf.global_variables_initializer())

      for i in range(10000):
          batch = mnist.train.next_batch(20)
          if i % 100 == 0:
              train_accuracy = accuracy.eval(feed_dict={x: batch[0], y_: batch[1], keep_prob: 1.0})
              log('step %d, training accuracy %g' % (i, train_accuracy))
          _, loss_val = sess.run([train_step, cross_entropy], feed_dict={x: batch[0], y_: batch[1], keep_prob: 0.5})
          if i % 100 == 0:
              log('loss is %g' % loss_val)
              saver.save(sess, FLAGS.checkpoint_dir + 'model.ckpt', global_step=i+1)

      log('test accuracy %g' % accuracy.eval(feed_dict={x: get_real_images(mnist.test.images), y_: dense_to_one_hot(mnist.test.labels), keep_prob: 1.0}))

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('--data_dir', type=str, default='/Users/croath/Desktop/sample/data2', help='Directory for storing input data')
  parser.add_argument('--checkpoint_dir', type=str, default='/Users/croath/Desktop/checkpoint/', help='Directory for stroing checkpoint')
  parser.add_argument('--graph_dir', type=str, help='Directory to save graph')
  parser.add_argument('--read_from_checkpoint', type=bool, default=False, help='Load from a checkpoint or not')
  FLAGS, unparsed = parser.parse_known_args()
  tf.app.run(main=main, argv=[sys.argv[0]] + unparsed)
