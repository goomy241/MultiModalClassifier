# MultiModalClassifier
## Bonus Work Selection
- Nvidia TensorRT inference
  - Colab link: https://colab.research.google.com/drive/1TkzjiZShs75KbB9PL47DF4urAvrPdyQo?usp=sharing
- TensorflowLite inference

## Changes
**1. Test Images Set**
- Downloaded 2 images for each of the 5 classes from Internet

**2. Code Changes**
- Used `flower_photos` dataset to train and save `xceptionmodel1` model
- Added inference testing for original trained model
- Benchmark inference testing for original trained model
- Added inference testing for TF-TRT optimized model
- Used `flower_photos` to generate TFRecord
- Converted original trained model to TensorflowLite
- Added inference testing for TFlite model

## Performance Comparison
**1. Original Trained Model - local without GPU**
- 1.1 Testing result
<img width="1433" alt="Original-model-testing-result" src="https://user-images.githubusercontent.com/90799662/166127426-a2af13fe-dbc5-4245-94a2-65e09ffa22f8.png">

- 1.2 Benchmark throughout
<img width="298" alt="Original-model-benchmark-result" src="https://user-images.githubusercontent.com/90799662/166127459-688a4305-4489-4d68-8286-a90f64501843.png">

**2. Original Trained Model - colab with GPU**
- 2.1 Testing result
<img width="535" alt="Original-model-testing-result-GPU" src="https://user-images.githubusercontent.com/90799662/166127566-08b2ad75-7968-4c28-b328-c4ec0b92c685.png">

- 2.2 Benchmark throughout
<img width="317" alt="Original-model-benchmark-result-GPU" src="https://user-images.githubusercontent.com/90799662/166127577-8ebdb242-2ad2-4718-9178-c067b5e15db7.png">

**3. TF-TRT Optimized Model**
- 3.1 Benchmark throughout - colab with GPU
<img width="284" alt="TFTRT-benchmark-result-GPU" src="https://user-images.githubusercontent.com/90799662/166127765-bd80ead5-c8cf-417e-bf6e-8e3c6931e949.png">

**4. TFlite Model**
- 4.1 Testing result - local without GPU
<img width="1439" alt="TFLite-testing-result" src="https://user-images.githubusercontent.com/90799662/166127607-3dcfc80e-1a1e-430c-bb15-d1d70900f8e7.png">

- 4.2 Testing result - colab with GPU
<img width="505" alt="TFLite-testing-result-GPU" src="https://user-images.githubusercontent.com/90799662/166127637-e769ba22-4c4f-4768-9f36-dc8217cdad73.png">

## Conclusion
- By enabling the GPU, testing speed got hugely improved for the original model. 
- The execution speed of TF-TRT optimized model is slightly better than the original one. 
- TFLite model has better performance in a local environment without GPU, but it has a longer execution time when GPU is enabled.
