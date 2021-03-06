from Layer import Layer
import numpy as np
import Activation
import Loss
from keras.datasets import mnist
from Utils import Utils
from keras.utils import to_categorical
from sklearn.metrics import *
from Optimaziers import *

import time

class ANN:
    def __init__(self):
        np.random.seed(int(time.time()))
        self.Layers = list()

    def add(self,L:Layer):
        if not isinstance(L,Layer):
            raise TypeError

        if len(self.Layers)>0 :
            if L.Input_shape is None:
                L.delayed = False
                L.Input_shape = self.Layers[-1].n_mem
                L.fill_delayed_value()

            if L.Input_shape != self.Layers[-1].n_mem:
                raise Exception("Layer Dimesion doesn't matched")
        else:
            if L.Input_shape is None:
                raise Exception("Layer Dimesion doesn't matched")

        self.Layers.append(L)

    def compile(self,Loss_function,optimizer='default',learning_rate = 0.01,lr_decay=1): #
        self.lr = learning_rate
        self.Loss_function = Loss_function[0]
        self.dLoss_function = Loss_function[1]
        self.lr_decay = lr_decay
        self.optimizer = Optimizers(optimizer.lower());


    def predict(self,input_data):
        for i in self.Layers:
            if not i.delayed:
                input_data = i.forwardprop(input_data)
            else:
                raise Exception("Somevalue doesn't filled")
        return input_data

    def train(self,train_X,train_y,epochs = 200, batch_size=None,verbose = False,validation=0.2):
        v_size = int(train_y.shape[0] * validation)
        selected = np.random.choice(np.arange(train_y.shape[0]),v_size)
        unselected = np.array([True] * train_y.shape[0]);
        unselected[selected] = False;


        validation_X = train_X[selected]
        train_X = train_X[unselected]

        validation_y = train_y[selected]
        train_y = train_y[unselected]


        if train_X.shape[1] != self.Layers[0].Input_shape:
            raise Exception("input_data & input_layer dimension is not equal")

        if batch_size is None: # batch-size가 안주어지면 mini-batch를 사용하지않음
            batch_size = train_X.shape[0]

        for iter_num in range(epochs):
            if iter_num%100 == 0:
                print('iter:',iter_num)
            if(verbose):
                print('epochs' + str(iter_num))
                print('*'*50)

            start_ind = 0
            while(start_ind < train_X.shape[0]):

                end_idx = min(train_X.shape[0]+1,start_ind+batch_size)
                mini_batchX = train_X[start_ind:end_idx]
                mini_batchy =  train_y[start_ind:end_idx]

                predicted_y = self.predict(mini_batchX) # 예측해서
                Loss = self.Loss_function(mini_batchy,predicted_y) #Loss 계산하고

                if verbose:
                    Utils.progress_bar(start_ind+batch_size,train_X.shape[0],Loss)

                self.backprop(mini_batchy,predicted_y) # backpropagation 돌린다.
                start_ind += batch_size


            #validation set 을가지고 검증
            predicted_y = np.argmax(self.predict(validation_X),axis=1)
            vali = np.argmax(validation_y,axis=1)
            acc =  (vali == predicted_y)

            print("validation acc: {}".format(np.sum(acc)/acc.shape[0] *100))

            #learning rate decay
            self.lr = self.lr * self.lr_decay


    def backprop(self,train_y,predicted_y):
        minibatch_dout = self.dLoss_function(train_y,predicted_y)  #최초 dL/yi
        dLayers = list()

        for d_out_num,cur_d_out in enumerate(minibatch_dout):
            for layer_num,cur_layer in enumerate(reversed(self.Layers)):
                doutb_dwij = np.full(cur_layer.W.shape,1) * cur_layer.prev[d_out_num:d_out_num+1].T # outb/wij 를 구함

                softmax_d_S = None
                temp_result = None

                if(cur_layer.dActivation != Activation.softmax[1]):
                    douta_doutb = cur_layer.dActivation(x=cur_layer.bout[d_out_num:d_out_num+1]) # outa/outb를 구함
                else:
                    if Activation.using_final_result and d_out_num == 0 and self.dLoss_function == Loss.categorical_cross_entropy[1]:
                        temp_result=  predicted_y[d_out_num:d_out_num+1] - train_y[d_out_num:d_out_num+1] # softmax 하고 categorical 이 같이 있으면 최종 미분결과는 이것
                    else:
                        douta_doutb, softmax_d_S = cur_layer.dActivation(x=cur_layer.bout[d_out_num:d_out_num + 1],
                                                                         prev_out_d=cur_d_out)
                if temp_result is None:
                    temp_result = cur_d_out * douta_doutb # dL/dyi_a * dyi_a/dyi_b -> dL/dyi_b
                    if softmax_d_S is not None:
                        temp_result = temp_result + softmax_d_S

                dlayer =  temp_result * doutb_dwij # dL/dyi_b * dyi_b/dWij -> dL/dWij
                cur_d_out = temp_result * cur_layer.W

                cur_d_out = cur_d_out.sum(axis=1)
                dlayer = dlayer / minibatch_dout.shape[0]
                if d_out_num==0:
                    dLayers.append(dlayer)
                else:
                    dLayers[layer_num] += dlayer

        self.optimizer.optimizer(self.lr,self.Layers,dLayers)


if __name__ == '__main__':
    (x_train, y_train), (x_test, y_test) = mnist.load_data()
    x_train = x_train.reshape(x_train.shape[0],-1) / 255
    y_train = to_categorical(y_train)
    x_test = x_test.reshape(x_test.shape[0],-1) / 255
    y_test = to_categorical(y_test)
    print(y_train.shape)
    print(x_train.shape)

    model = ANN()
    model.add(Layer(64,Input_shape=28*28,Activation=Activation.tanh,Weight_param='xavier'))
    model.add(Layer(64,Activation=Activation.Relu,Weight_param='he'))
    model.add(Layer(128,Activation=Activation.tanh,Weight_param='xavier'))
    model.add(Layer(128,Activation=Activation.Relu,Weight_param='he'))
    model.add(Layer(10,Activation=Activation.softmax))
    model.compile(Loss_function=Loss.categorical_cross_entropy,learning_rate=0.001,lr_decay=0.95,optimizer='adam')
    model.train(x_train,y_train,epochs=10,batch_size=512,verbose=True,validation=0.3)
    pred = model.predict(x_test)

    pred = np.argmax(pred,axis=1)
    y_test = np.argmax(y_test,axis=1)

    print(pred)
    print(y_test)



    print('======not matched==============')
    np.set_printoptions(threshold=np.nan)

    for i,j in zip(pred[pred != y_test],y_test[pred != y_test]):
        print("predicted : {} , actual {}".format(i,j))


    precision, recall, fscore, support = precision_recall_fscore_support(y_test.tolist(),pred.tolist())

    print('precision: {}'.format(precision))
    print('recall: {}'.format(recall))
    print('fscore: {}'.format(fscore))
    print('support: {}'.format(support))
    print('accuracy: {}'.format(accuracy_score(y_test.tolist(),pred.tolist())))