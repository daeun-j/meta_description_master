import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0,1'
import torch
import torch.utils.data
import torch.nn as nn
from torch.utils.data import DataLoader
from datetime import datetime
import torch.optim as optim
from sklearn.metrics import confusion_matrix, classification_report
import pandas as pd
import numpy as np
import csv
from dataloader import Dataset
from utils import validate
from models import MulticlassClassification_CUDA
# parser = argparse.ArgumentParser()
#
# parser.add_argument('--window_size', type=int, default=30)
# parser.add_argument('--epoch', type=int, default=5)
# parser.add_argument('--lr', type=float, default=1e-4)
# parser.add_argument('--batch_size', type=int, default=1024)
#
# parser.add_argument('--fft', type=int, default=3)
# parser.add_argument('--stat', type=int, default=1)
# parser.add_argument('--MERGE', type=int, default=0)
# parser.add_argument('--layer_dim', type=int, default=1)
# parser.add_argument('--split_ratio', type=float, default=0.9)
# parser.add_argument('--n_iters', type=int, default=100000)
# parser.add_argument('--hidden_dim', type=int, default=512)
# parser.add_argument('--num_epochs', type=int, default=2)

input_dim = 20
output_dim = 3
seq_dim = 1
split_ratio = 0.9
batch_size = 5000
n_iters = 10000000
input_dim = 20
hidden_dim = 100
layer_dim = 1
output_dim = 3
seq_dim = 1
lr = 0.00001
window_size=50
fft_num =3
stat = 1
MERGE = 6



#args = parser.parse_args()
#print(f'Training configs: {args}')
name = "f{}_stt{}_merge{}_w{}_lr{}_bs{}".format(args.fft, args.stat, args.MERGE, args.window_size, args.lr, args.batch_size)
# hyper_params = {"fft": args.fft, "stat" : args.stat, "MERGE" : args.MERGE, "window_size": args.window_size,"lr" : args.lr, "batch_size" : args.batch_size
#                 ,"epoch": args.epoch, "hidden_dim": args.hidden_dim, "n_iters": args.n_iters, "split_ratio": args.split_ratio, "layer_dim": args.layer_dim}


"""STEP 2: load data"""

df = pd.DataFrame()

df = pd.read_csv("./dataset/Telegram_1hour_7.csv")
df.insert(2, "label", int(0))
df_0 = df[["Time", "Length", "label"]].to_numpy()

df = pd.read_csv("./dataset/Zoom_1hour_5.csv")
df.insert(2, "label", int(1))
df_1 = df[["Time", "Length", "label"]].to_numpy()

df = pd.read_csv("./dataset/YouTube_1hour_2.csv")
df.insert(2, "label", int(2))
df_2 = df[["Time", "Length", "label"]].to_numpy()

df_set = np.vstack((df_0, df_1, df_2))

df_set = Dataset(df_set, window_size= window_size,
                 fft_num= fft_num, stat=stat, MERGE= MERGE)

train_dataset, val_dataset = torch.utils.data.random_split(
    df_set, [int(len(df_set) *split_ratio),
             len(df_set) - int(len(df_set) * split_ratio)])

val_dataset, test_dataset = torch.utils.data.random_split(
    val_dataset, [int(len(val_dataset) * split_ratio),
                  len(val_dataset) - int(len(val_dataset) * split_ratio)])

print("train_dataset:", len(train_dataset))
print("val_dataset:", len(val_dataset))
print("test_dataset:", len(test_dataset))

"""STEP 3: Make data iterable"""
# num_epochs = int(num_epochs)
# num_epochs = 100
#num_epochs = int(args.n_iters / (len(train_dataset) / args.batch_size))
num_epochs = 2
print("num_epochs:", int(num_epochs))

train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size, drop_last=False, shuffle=True, num_workers=0)
val_loader = DataLoader(dataset=val_dataset, batch_size=batch_size, drop_last=False, shuffle=True, num_workers=0)
test_loader = DataLoader(dataset=test_dataset, batch_size=batch_size, drop_last=False, shuffle=True, num_workers=0)



x, y = next(iter(test_loader))
input_dim = x.size()[1]
# name = "test_dnn"
# first_batch = train_loader.__iter__().__next__()
# print('{:15s} | {:<25s} | {}'.format('name', 'type', 'size'))
# print('{:15s} | {:<25s} | {}'.format('Num of Batch', '', len(train_loader)))
# print('{:15s} | {:<25s} | {}'.format('first_batch', str(type(first_batch)), len(first_batch)))
# print('{:15s} | {:<25s} | {}'.format('first_batch[0]', str(type(first_batch[0])), first_batch[0].shape))
# print('{:15s} | {:<25s} | {}'.format('first_batch[1]', str(type(first_batch[1])), first_batch[1].shape))
# # 총 데이터의 개수는 len(train_loader) *  len(first_batch[0])이다.


#
L1 = 128
L2 = 32
L3 = 128


#LO = 16
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


model = MulticlassClassification_CUDA(num_feature =input_dim, num_class=output_dim,
                                      L1=L1,  L2=L2,  L3=L3)
model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=lr)
print(model)


def multiclass_accuracy(outputs, batch_size):
    _, predicted = torch.max(outputs.data, 1)
    acc = ((predicted == labels)*1).sum()/batch_size *100
    return acc

accuracy_stats = {
    'train': [],
    "val": []
}
loss_stats = {
    'train': [],
    "val": []
}
print("Begin training.")
result_eval_dict = {}
#result_eval_dict.update(hyper_params)
num_epochs = 1
for epoch in range(num_epochs):
    train_epoch_loss = 0
    train_epoch_acc = 0
    model.train()
    for tr_i, (inputs, labels) in enumerate(train_loader):
        labels = labels.type(torch.LongTensor)
        inputs, labels = inputs.to(device), labels.to(device)
        inputs = inputs.view(-1, seq_dim, input_dim).requires_grad_()
        optimizer.zero_grad()
        outputs = model(inputs)
        #outputs = outputs.reshape([batch_size,output_dim])
        outputs = outputs.view( -1, 3)

        train_loss = criterion(outputs, labels)
        train_loss.backward()
        train_acc = multiclass_accuracy(outputs, labels.size(0))

        optimizer.step()

        train_epoch_loss += train_loss.item()
        train_epoch_acc += train_acc.item()
        if tr_i % 50 == 0:
            print(f'Train Epoch {tr_i + 0:05}: | Train Loss: {train_loss:.5f} | Train Acc: {train_acc:.3f}')
            torch.save({'epoch': tr_i,
                        'model_state_dict': model.state_dict(),
                        'optimizer_state_dict': optimizer.state_dict(),
                        "loss": train_loss}, "./Weights/"+name+".pt")

    val_outputs_sets = torch.tensor([]).to(device)
    start = datetime.now()
    valid_name = str(epoch)+"val_eval_"+name
    for inputs, labels in val_loader:
        labels = labels.type(torch.LongTensor)
        inputs, labels = inputs.to(device), labels.to(device)
        inputs = inputs.view(-1, seq_dim, input_dim)
        outputs = model(inputs)
        outputs = outputs.view(-1, 3)
        val_loss = criterion(outputs, labels)
        outputs = outputs.data.max(1)[1]
        val_outputs_pairs = torch.vstack((labels, outputs))
        val_outputs_sets = torch.hstack((val_outputs_pairs, val_outputs_sets))
    end = datetime.now()
    torch.save({'epoch': tr_i, 'model_state_dict': model.state_dict(),'optimizer_state_dict': optimizer.state_dict(),
                "loss": train_loss}, "./Weights/final_"+name+".pt")
    result_valid_file = "result/valid_"+name
    valid_dict = validate(val_outputs_sets[0].to("cpu").numpy(), val_outputs_sets[0].to("cpu").numpy(), result_valid_file)
    valid_time = "{}".format(end-start)
    valid_dict["valid time"] = valid_time
    result_iter_eval_dict = {valid_name: valid_dict}
    result_eval_dict.update(result_iter_eval_dict)
#STEP 8: TEST

y_pred_list, y_test_list = [], []
with torch.no_grad():
    #model.eval()
    start = datetime.now()
    for inputs, y_test in test_loader:
        inputs, y_test = inputs.to(device), y_test.to(device)
        inputs = inputs.view(-1, seq_dim, input_dim)
        y_test_pred = model(inputs)
        y_test_pred = y_test_pred.view(-1, 3)
        y_test_pred = torch.log_softmax(y_test_pred, 1)
        _,y_test_pred = torch.max(y_test_pred, 1)
        y_pred_list.append(y_test_pred.cpu().numpy())
        y_test_list.append(y_test.cpu().numpy())
    end = datetime.now()
    y_pred_list = [a.squeeze().tolist() for a in y_pred_list]
    y_test_list = [a.squeeze().tolist() for a in y_test_list]
    #print(y_pred_list, y_test_list)
y_pred_list = [j for sub in y_pred_list for j in sub]
y_test_list = [j for sub in y_test_list for j in sub]
y_test_list = list(map(round, y_test_list))
print(confusion_matrix(y_pred_list,  y_test_list, labels=[0, 1, 2]))
print(classification_report(y_test_list, y_pred_list))


test_name = "test_eval_"+name
result_test_file = "result/test_"+name
test_dict = validate(np.asarray(y_test_list), np.asarray(y_pred_list), result_test_file)
test_time = "{}".format(end-start)
test_dict["test time"] = test_time
result_test_dict = {test_name: test_dict}
result_eval_dict.update(result_test_dict)
result_eval_dict_name = "param_eval_"+name

with open(result_eval_dict_name+'.csv', 'w') as f:
    w = csv.writer(f)
    w.writerow(result_eval_dict.keys())
    w.writerow(result_eval_dict.values())