import configargparse #pip install configargparse
import tensorflow as tf
import PIL
import PIL.Image
import matplotlib.pyplot as plt
import numpy as np
import time
import os
print(tf.__version__)

from TFClassifier.Datasetutil.TFdatasetutil import loadTFdataset #loadtfds, loadkerasdataset, loadimagefolderdataset
from TFClassifier.myTFmodels.CNNsimplemodels import createCNNsimplemodel
from TFClassifier.Datasetutil.Visutil import plot25images, plot9imagesfromtfdataset, plot_history
from TFClassifier.myTFmodels.optimizer_factory import build_learning_rate, setupTensorboardWriterforLR
from TFClassifier.exportTFlite import loadimage

model = None 
# import logger

parser = configargparse.ArgParser(description='myTFDistributedClassify')
parser.add_argument('--data_name', type=str, default='flower',
                    help='data name: mnist, fashionMNIST, flower')
parser.add_argument('--data_type', default='imagefolder', choices=['tfds', 'kerasdataset', 'imagefolder', 'customtfrecordfile'],
                    help='the type of data')  # gs://cmpelkk_imagetest/*.tfrec
parser.add_argument('--data_path', type=str, default='/Users/daijunq/.keras/datasets/flower_photos',
                    help='path to get data') #'/home/lkk/.keras/datasets/flower_photos'
parser.add_argument('--img_height', type=int, default=180,
                    help='resize to img height')
parser.add_argument('--img_width', type=int, default=180,
                    help='resize to img width')
parser.add_argument('--save_path', type=str, default='./outputs',
                    help='path to save the model')
# network
parser.add_argument('--model_name', default='xceptionmodel1', choices=['cnnsimple1', 'cnnsimple2', 'cnnsimple3', 'cnnsimple4','mobilenetmodel1', 'xceptionmodel1'],
                    help='the network')
parser.add_argument('--arch', default='Tensorflow', choices=['Tensorflow', 'Pytorch'],
                    help='Model Name, default: Tensorflow.')
parser.add_argument('--learningratename', default='warmupexpdecay', choices=['fixedstep', 'fixed', 'warmupexpdecay'],
                    help='path to save the model')
parser.add_argument('--batchsize', type=int, default=32,
                    help='batch size')
parser.add_argument('--epochs', type=int, default=8,
                    help='epochs')
parser.add_argument('--GPU', type=bool, default=True,
                    help='use GPU')
parser.add_argument('--TPU', type=bool, default=False,
                    help='use TPU')
parser.add_argument('--MIXED_PRECISION', type=bool, default=False,
                    help='use MIXED_PRECISION')


args = parser.parse_args()


# Callback for printing the LR at the end of each epoch.
class PrintLR(tf.keras.callbacks.Callback):
  def on_epoch_end(self, epoch, logs=None):
    print('\nLearning rate for epoch {} is {}'.format(epoch + 1,
                                                      model.optimizer.lr.numpy()))


def main():
    print("Tensorflow Version: ", tf.__version__)
    print("Keras Version: ", tf.keras.__version__)

    TAG="0712"
    args.save_path=args.save_path+'/'+args.data_name+'_'+args.model_name+'_'+TAG
    print("Output path:", args.save_path)

    # mixed precision
    # On TPU, bfloat16/float32 mixed precision is automatically used in TPU computations.
    # Enabling it in Keras also stores relevant variables in bfloat16 format (memory optimization).
    # On GPU, specifically V100, mixed precision must be enabled for hardware TensorCores to be used.
    # XLA compilation must be enabled for this to work. (On TPU, XLA compilation is the default)
    if args.MIXED_PRECISION:
        if args.tpu: 
            policy = tf.keras.mixed_precision.experimental.Policy('mixed_bfloat16')
        else: #
            policy = tf.keras.mixed_precision.experimental.Policy('mixed_float16')
            tf.config.optimizer.set_jit(True) # XLA compilation
        tf.keras.mixed_precision.experimental.set_policy(policy)
        print('Mixed precision enabled')

    if args.GPU:
        physical_devices = tf.config.list_physical_devices('GPU')
        num_gpu = len(physical_devices)
        print("Num GPUs:", num_gpu)
        # Create a MirroredStrategy object. This will handle distribution, and provides a context manager (tf.distribute.MirroredStrategy.scope) to build your model inside.
        strategy = tf.distribute.MirroredStrategy()  # for GPU or multi-GPU machines
        #strategy = tf.distribute.get_strategy()
    elif args.TPU:
        #TPU detection, do together
        try: # detect TPUs
            tpu = None
            tpu = tf.distribute.cluster_resolver.TPUClusterResolver() # TPU detection
            tf.config.experimental_connect_to_cluster(tpu)
            tf.tpu.experimental.initialize_tpu_system(tpu)
            strategy = tf.distribute.experimental.TPUStrategy(tpu)
        except ValueError: # detect GPUs
            #strategy = tf.distribute.MirroredStrategy() # for GPU or multi-GPU machines
            strategy = tf.distribute.get_strategy() # default strategy that works on CPU and single GPU
            #strategy = tf.distribute.experimental.MultiWorkerMirroredStrategy() # for clusters of multi-GPU machines
    else:
        print("No GPU and TPU enabled")

    print("Number of accelerators: ", strategy.num_replicas_in_sync)
    BUFFER_SIZE = 10000
    BATCH_SIZE_PER_REPLICA = args.batchsize #32
    BATCH_SIZE = BATCH_SIZE_PER_REPLICA * strategy.num_replicas_in_sync

    #train_ds, val_ds, class_names, imageshape = loadTFdataset(args.data_name, args.data_type)
    train_ds, val_ds, class_names, imageshape = loadTFdataset(args.data_name, args.data_type, args.data_path, args.img_height, args.img_width, BATCH_SIZE)
    #train_ds, test_data, num_train_examples, num_test_examples, class_names=loadimagefolderdataset('flower')
    #train_data, test_data, num_train_examples, num_test_examples =loadkerasdataset('cifar10')
    #train_data, test_data, num_train_examples, num_test_examples = loadtfds(args.tfds_dataname)
    # train_data, test_data, num_train_examples, num_test_examples = loadtfds(
    #     args.tfds_dataname)

    #Tune for performance, Use buffered prefetching to load images from disk without having I/O become blocking
    AUTOTUNE = tf.data.AUTOTUNE #tf.data.experimental.AUTOTUNE
    train_ds = train_ds.cache().shuffle(BUFFER_SIZE).prefetch(buffer_size=AUTOTUNE)
    val_ds = val_ds.cache().prefetch(buffer_size=AUTOTUNE)

    numclasses=len(class_names)

    global model
    metricname='accuracy'
    metrics=[metricname]
    with strategy.scope():
        model = createCNNsimplemodel(args.model_name, numclasses, imageshape, metrics)
    #model = create_model(strategy,numclasses, metricname)
    model.summary()

    # Define the checkpoint directory to store the checkpoints
    checkpoint_dir = args.save_path #'./training_checkpoints'
    # Name of the checkpoint files
    checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt_{epoch}")

    setupTensorboardWriterforLR(args.save_path)

    callbacks = [
        tf.keras.callbacks.TensorBoard(log_dir=args.save_path),
        tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_prefix,
                                        save_weights_only=True),
        build_learning_rate(args.learningratename),
        #tf.keras.callbacks.LearningRateScheduler(learningratefn),
        PrintLR()
    ]

    print("Initial learning rate: ", round(model.optimizer.lr.numpy(), 5))

    #steps_per_epoch = num_train_examples // BATCH_SIZE  # 2936 is the length of train data
    #print("steps_per_epoch:", steps_per_epoch)
    start_time = time.time()
    #train the model 
    history = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs, callbacks=callbacks)
    # history = model.fit(train_ds, validation_data=val_ds,
    #                     steps_per_epoch=steps_per_epoch, epochs=EPOCHS, callbacks=[lr_callback])

    valmetricname="val_"+metricname
    final_accuracy = history.history[valmetricname][-5:]
    print("FINAL ACCURACY MEAN-5: ", np.mean(final_accuracy))
    print("TRAINING TIME: ", time.time() - start_time, " sec")

    plot_history(history, metricname, valmetricname, args.save_path)

    #Export the graph and the variables to the platform-agnostic SavedModel format. After your model is saved, you can load it with or without the scope.
    model.save(args.save_path, save_format='tf')

    eval_loss, eval_acc = model.evaluate(val_ds)
    print('Eval loss: {}, Eval Accuracy: {}'.format(eval_loss, eval_acc))


def testing():
    load_path = '/Users/daijunq/Desktop/dee/github/MultiModalClassifier/TFClassifier/outputs/flower_xceptionmodel1_0712/'
    reloaded = tf.keras.models.load_model(load_path)
    reloaded.summary()
    # reloaded_model = reloaded.signatures["serving_default"]

    my_image_path = '/Users/daijunq/Desktop/dee/github/MultiModalClassifier/tests/imgdata'
    from PIL import Image
    file_name = []
    pred_result = []
    class_names = ['daisy', 'dandelion', 'roses', 'sunflowers', 'tulips']

    idx = 1
# ref: https://stackoverflow.com/questions/33369832/read-multiple-images-on-a-folder-in-opencv-python
    for image_name in os.listdir(my_image_path):   
        # print(os.path.basename(image)) 
        file_name.append(image_name)
        image_p = my_image_path + "/" + image_name
        # print(image_p)
        
        image = Image.open(image_p).resize((180, 180))
        # imgplot = plt.imshow(image)
        # plt.show()  

        image = np.array(image)
        image = np.array(image)/255.0

        tic = time.perf_counter()
        if idx == 1:
            or_tic = tic 
        pred = reloaded.predict(image[np.newaxis, ...])
        toc = time.perf_counter()
        
        print(f"Finish predict image {idx} in {toc - tic:0.4f} seconds")

        predict_id = np.argmax(pred[0], axis=-1)
        pred_result.append(class_names[predict_id])
        idx += 1

    print("\nFinal prediction result is shown as below:\n")
# ref: https://stackoverflow.com/questions/55290527/python-print-two-lists-with-string-format-operator
    print('\n'.join(f'file name: {f},  predict class: {p}' for f,p in zip(file_name, pred_result)))
    print(f"\nTotal testing time: {toc - or_tic:0.4f} seconds")

    from tensorflow.keras.preprocessing import image
    batch_size = len(file_name)
    batched_input = np.zeros((batch_size, 180, 180, 3), dtype=np.float32)

    from tensorflow.keras.applications.resnet50 import preprocess_input
    for i in range(batch_size):
        img_path = my_image_path + "/" + file_name[i]
        # print(img_path)
        img = image.load_img(img_path, target_size=(180, 180))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        batched_input[i, :] = x
    batched_input = tf.constant(batched_input)
    print('-------------------------------------')
    print('batched_input shape: ', batched_input.shape)

    # Benchmarking throughput
    N_warmup_run = 50
    N_run = 1000
    elapsed_time = []

    for i in range(N_warmup_run):
        preds = reloaded.predict(batched_input)

    for i in range(N_run):
        start_time = time.time()
        preds = reloaded.predict(batched_input)
        end_time = time.time()
        elapsed_time = np.append(elapsed_time, end_time - start_time)
        if i % 50 == 0:
            print('Step {}: {:4.1f}ms'.format(i, (elapsed_time[-50:].mean()) * 1000))

    print('Throughput: {:.0f} images/s'.format(N_run * batch_size / elapsed_time.sum()))

if __name__ == '__main__':
    testing()
