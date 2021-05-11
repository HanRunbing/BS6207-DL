# -*- coding: utf-8 -*-
"""Runbing_code.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16itAKd91dMbQfeLfKiD7y2QG1kGPOUBD
"""

import numpy as np 
import pandas as pd 
import os
from tqdm import tqdm_notebook as tqdm
from sklearn.preprocessing import LabelEncoder
from PIL import Image
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data.sampler import SubsetRandomSampler
from torch.utils.data import Dataset
import torchvision
import torchvision.transforms as transforms
import re
import pickle
import torch
from torch.autograd import Variable
from torch.optim import Adam, SGD
from tqdm import tqdm
import seaborn as sns
# from sparse import COO





"""# Download the dataset"""

def read_train_pdb(filename):
	
	with open(filename, 'r') as file:
		strline_L = file.readlines()
		# print(strline_L)

	X_list = list()
	Y_list = list()
	Z_list = list()
	atomtype_list = list()
	for strline in strline_L:
		# removes all whitespace at the start and end, including spaces, tabs, newlines and carriage returns
		stripped_line = strline.strip()

		line_length = len(stripped_line)
		# print("Line length:{}".format(line_length))
		if line_length < 78:
			print("ERROR: line length is different. Expected>=78, current={}".format(line_length))
		
		X_list.append(float(stripped_line[30:38].strip()))
		Y_list.append(float(stripped_line[38:46].strip()))
		Z_list.append(float(stripped_line[46:54].strip()))

		atomtype = stripped_line[76:78].strip()
		if atomtype == 'C':
			atomtype_list.append('h') # 'h' means hydrophobic
		else:
			atomtype_list.append('p') # 'p' means polar

	return X_list, Y_list, Z_list, atomtype_list

def read_test_pdb(filename):
    '''
    Read a original pdb file and extract the data.
    The information of one atom is represented as a line in the array.
    Result is returned as a numpy array
    '''
    # Storing X, Y, Z coordinates of the atom and the atom type into lists
    X_list = list()
    Y_list = list()
    Z_list = list()
    atom_list = list()
    
    with open(filename, 'r') as file:
        for strline in file.readlines():    
            # Removes all the white spaces
            stripped_line = strline.strip()
            # Split a tabs
            splitted_line = stripped_line.split('\t')            
            # Append to list
            X_list.append(float(splitted_line[0])),
            Y_list.append(float(splitted_line[1])),
            Z_list.append(float(splitted_line[2])),
            atom_list.append(str(splitted_line[3]))
            
    return X_list, Y_list, Z_list, atom_list

# Load training data into dictionary
train_data = {
    'proteins': list(),
    'ligands': list()
}

for i in range(1,3001):
    train_data['proteins'].append(
        read_train_pdb('/content/drive/MyDrive/BS6207/Project/training_data/{:04d}_pro_cg.pdb'.format(i)))
    train_data['ligands'].append(
        read_train_pdb('/content/drive/MyDrive/BS6207/Project/training_data/{:04d}_lig_cg.pdb'.format(i)))

# Load testing data into dictionary
test_data = {
    'proteins': list(),
    'ligands': list()
}

for i in range(1,825):
    test_data['proteins'].append(
        read_test_pdb('/content/drive/MyDrive/BS6207/Project/testing_data/{:04d}_pro_cg.pdb'.format(i)))
    test_data['ligands'].append(
        read_test_pdb('/content/drive/MyDrive/BS6207/Project/testing_data/{:04d}_lig_cg.pdb'.format(i)))

"""# Visualize the data"""

# Define location visulazation function
def visulazation(protein,ligand):
    '''
    Plots a 3D plot to visualize the protein-ligand pairing
    '''  
    plt.rcParams['figure.figsize'] = (16,10)
    fig = plt.figure() 
    sns.set(style = "darkgrid")

    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(protein[0], protein[1], protein[2], c='r', marker='o')
    ax.scatter(ligand[0], ligand[1], ligand[2], c='b', marker='o')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    plt.show()

len(train_data['proteins'][0][0])

"""The location of the strcture is not in the center"""

visulazation(train_data['proteins'][0],train_data['ligands'][0])

visulazation(train_data['proteins'][0],train_data['ligands'][9])

"""# Pre-processing

## Scale
"""

# Move the whole cube to the center. The center is mean of the centers of 'ligands'
scaled_data = {
    'proteins': list(),
    'ligands': list()
}
for i in range(len(train_data['proteins'])):
  mean_center = np.expand_dims(np.mean(train_data['ligands'][i][:3],axis = 1),axis = 1)
  temp_pro = np.array(train_data['proteins'][i][:3]) - mean_center
  scaled_data['proteins'].append([temp_pro,train_data['proteins'][i][3]])
  temp_gli = np.array(train_data['ligands'][i][:3]) - mean_center
  scaled_data['ligands'].append([temp_gli,train_data['ligands'][i][3]])

"""After scaling, the cube location is in the center. """

visulazation(scaled_data['proteins'][0][0],scaled_data['ligands'][0][0])

"""## Check the cube **size**"""

lis =[]
lis.append(max(abs(scaled_data['ligands'][0][0][0])))

# Record the maximum size of each asix to estimate the size of cube
x_max = []
y_max = []
z_max = []
for i in range(len(train_data['proteins'])):
  x_max.append(max(abs(scaled_data['proteins'][i][0][0])))
  y_max.append(max(abs(scaled_data['proteins'][i][0][1])))
  z_max.append(max(abs(scaled_data['proteins'][i][0][2])))

max_size = pd.DataFrame({'x_max':x_max,'y_max':y_max,'z_max':z_max})
max_size

max_size.describe()

"""Set cube size as (100,100,100), which enables 75% cell remain all atoms. For the rest of 25%, we need to crop the outliers. since the (3000,2,100,100,100) is too large and fail to run. Thus I need to rescale them or down sample the dataset

# Generate cubes

## Positive_pairing cube
"""



def positive_cubes_downsampling(cubes_size, scaled_data,n):
  # in order to convert to tensor the datatype should be float32
  cubes = []
  points = []
  # the oringal size of cubes should be 100 * 100 * 100
  shiftL = (cubes_size - 1 ) // 2
  discard_num = [0,0]
  overlap_num = [0,0]
  # protein:
  for i in range(n):
    point_1 = 0
    point_2 = 0
    cube = np.zeros((2,cubes_size,cubes_size,cubes_size),dtype=np.float32)
     # ligands:  
    for k in range(len(scaled_data['ligands'][i][0][0])):
      x_l, y_l,z_l = scaled_data['ligands'][i][0][0][k],scaled_data['ligands'][i][0][1][k],scaled_data['ligands'][i][0][2][k]
      x_l, y_l,z_l = int(x_l + shiftL),int(y_l + shiftL),int(z_l + shiftL)
      if x_l >= cubes_size or  y_l >= cubes_size or z_l >= cubes_size or x_l < 0 or  y_l < 0 or z_l < 0 :
        discard_num[1] += 1
        continue
      if cube[0,x_l, y_l,z_l] !=0 or cube[1,x_l, y_l,z_l] !=0:
        overlap_num[1] += 1
        continue
      # first channel
      cube[0,x_l, y_l,z_l] = 1
      point_1 += 1
      # second channel
      if scaled_data['ligands'][i][1][k] == 'h':
        cube[1,x_l, y_l,z_l] = 1
        point_2 += 1
      else:
        cube[1,x_l, y_l,z_l] = -1
        point_2 += 1
    # protein:
    for j in range(len(scaled_data['proteins'][i][0][0])):
      x_p, y_p,z_p = scaled_data['proteins'][i][0][0][j],scaled_data['proteins'][i][0][1][j],scaled_data['proteins'][i][0][2][j]
      # and convert the data type of (x,y,z) into int
      x_p, y_p,z_p = int(x_p + shiftL),int(y_p + shiftL),int(z_p + shiftL)
      # crop the cube 
      if x_p >= cubes_size or  y_p >= cubes_size or z_p >= cubes_size or x_p < 0 or  y_p < 0 or z_p < 0 :
        discard_num[0] += 1
        continue
      # check the overlaping atoms
      if cube[0,x_p, y_p,z_p] !=0 or cube[1,x_p, y_p,z_p] !=0:
        overlap_num[0] += 1
        continue
      # first channel
      cube[0,x_p, y_p,z_p] = -1
      point_1 += 1
      # second channel
      if scaled_data['proteins'][i][1][j] == 'h':
        cube[1,x_p, y_p,z_p] = 1
        point_2 += 1
      else:
        cube[1,x_p, y_p,z_p] = -1
        point_2 += 1
    cubes.append(cube)
    points.append([point_1,point_2])
  return np.array(cubes,dtype=np.float32),  discard_num, overlap_num,shiftL,np.array(points)

positive_cubes,  discard_num, overlap_num ,shiftL,points= positive_cubes_downsampling(25, scaled_data,3000)

"""## Negative pairing cube"""

import random
def neg_cubes_building(cubes_size, scaled_data,n):
  cubes = []
  # the oringal size of cubes should be 100 * 100 * 100
  shiftL = (cubes_size - 1 ) // 2
  discard_num = [0,0]
  overlap_num = [0,0]
  # protein:
  for i in range(n):
    cube = np.zeros((2,cubes_size,cubes_size,cubes_size),dtype=np.float32)
    # ligands:  
     # random select a 'ligands'
    ii = random.randint(0,n-1)
    for k in range(len(scaled_data['ligands'][ii][0][0])):
      x_l, y_l,z_l = scaled_data['ligands'][ii][0][0][k],scaled_data['ligands'][ii][0][1][k],scaled_data['ligands'][ii][0][2][k]
      x_l, y_l,z_l = int(x_l + shiftL),int(y_l + shiftL),int(z_l + shiftL)
      if x_l >= cubes_size or  y_l >= cubes_size or z_l >= cubes_size or x_l < 0 or  y_l < 0 or z_l < 0 :
        discard_num[1] += 1
        continue
      if cube[0,x_l, y_l,z_l] !=0 or cube[1,x_l, y_l,z_l] !=0:
        overlap_num[1] += 1
        continue
      # first channel
      cube[0,x_l, y_l,z_l] = 1
      # second channel
      if scaled_data['ligands'][ii][1][k] == 'h':
        cube[1,x_l, y_l,z_l] = 1
      else:
        cube[1,x_l, y_l,z_l] = -1
    # protein:
    for j in range(len(scaled_data['proteins'][i][0][0])):
      x_p, y_p,z_p = scaled_data['proteins'][i][0][0][j],scaled_data['proteins'][i][0][1][j],scaled_data['proteins'][i][0][2][j]
      # Shift all the atoms by 25 such that the center could be 25,25,25
      # and convert the data type of (x,y,z) into int
      x_p, y_p,z_p = int(x_p + shiftL),int(y_p + shiftL),int(z_p + shiftL)
      # crop the cube size with 50*50*50
      if x_p >= cubes_size or  y_p >= cubes_size or z_p >= cubes_size or x_p < 0 or  y_p < 0 or z_p < 0 :
        discard_num[0] += 1
        continue
      # check the overlaping atoms
      if cube[0,x_p, y_p,z_p] !=0 or cube[1,x_p, y_p,z_p] !=0:
        overlap_num[0] += 1
        continue
      # first channel
      cube[0,x_p, y_p,z_p] = -1
      # second channel
      if scaled_data['proteins'][i][1][j] == 'h':
        cube[1,x_p, y_p,z_p] = 1
      else:
        cube[1,x_p, y_p,z_p] = -1
    
    cubes.append(cube)
  return np.array(cubes,dtype=np.float32)

negetive_cube = neg_cubes_building(25,scaled_data,3000)



"""# Training Process

## Split Data into Training and Validation
- 6000 cubes in total  (3000 positive pairs/3000 negative pairs)
- 80% traing_data  (4800 samples of protein-ligand pairs)
- 20% validation_data (1200 samples of protein-ligand pairs)
"""

batch_size = 64
validation_split = .2
shuffle_dataset = True
random_seed= 42

train_set = np.append(positive_cubes[:2400],negetive_cube[:2400],axis=0)
train_y = np.array([1] * 2400 + [0] * 2400)
train_indices = list(range(4800))
val_set = np.append(positive_cubes[:600],negetive_cube[:600],axis=0)
val_y = np.array([1] * 600 + [0] * 600)
val_indices = list(range(1200))
if shuffle_dataset :
    np.random.seed(random_seed)
    np.random.shuffle(train_indices)
    np.random.shuffle(val_indices)

train_sampler = SubsetRandomSampler(train_indices)
valid_sampler = SubsetRandomSampler(val_indices)

transform = transforms.Compose(
    [transforms.ToTensor(),
     transforms.RandomRotation(90)])

class cube_Dataset(Dataset):
    def __init__(self, cube_data,cube_label,transform=None):
        self.cube_data = cube_data
        self.cube_label = cube_label
        self.transform = transform
    def __len__(self):
        return len(self.cube_data)
    
    def __getitem__(self, index):
        cube = self.cube_data[index]
        # cube = cube.resize((128,128))
        label = self.cube_label[index]
        if self.transform is not None:
            cube[0] = self.transform(cube[0])
            cube[1] = self.transform(cube[1])
        return cube, label

val_dataset = cube_Dataset(val_set,val_y)
train_dataset = cube_Dataset(train_set,train_y, transform)

train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, 
                                           sampler=train_sampler)
validation_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size,
                                                sampler=valid_sampler)

"""## CNN """

class CNN_3(nn.Module):
    def __init__(self):
        super(CNN_3, self).__init__()
        # 3 input image channel, 16 output channels, 3x3 square convolution kernel
        self.conv1 = nn.Conv3d(2,64,kernel_size=3,stride=1,padding=1)
        self.conv2 = nn.Conv3d(64, 128,kernel_size=3,stride=1, padding=1)
        self.conv3 = nn.Conv3d(128, 256,kernel_size=3,stride=1, padding=1)
        self.pool = nn.MaxPool3d(2, 2)
        self.dropout = nn.Dropout3d(0.4)
        self.batchnorm1 = nn.BatchNorm3d(64)
        self.batchnorm2 = nn.BatchNorm3d(128)
        self.batchnorm3 = nn.BatchNorm3d(256)
        self.fc1 = nn.Linear(256*1*1,1024)
        self.fc2 = nn.Linear(1024, 256)
        self.fc3 = nn.Linear(256, 2)
        
    def forward(self, x):
        x = self.batchnorm1(self.pool(F.relu(self.conv1(x))))
        x = self.batchnorm2(self.pool(F.relu(self.conv2(x))))
        x = self.batchnorm3(self.pool(F.relu(self.conv3(x))))
        x = self.dropout(x)
        # print(x.size())
        x = x.view(x.size(0), -1) # Flatten layer
        # x = self.fc1(x)
        # x = self.dropout(x)
        # x = self.fc2(x)
        x = self.dropout(x)
        x = F.log_softmax(self.fc3(x),dim = 1)
        return x

"""##Train"""

model = CNN_3()
print(model)

def accuracy(out, labels):
    _,pred = torch.max(out, dim=1)
    return torch.sum(pred==labels).item()

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
valid_loss_min = np.Inf
val_loss = []
val_acc = []
train_loss = []
train_acc = []
total_step = len(train_loader)
best_acc = 0
for epoch in range(1, 20 + 1):
    running_loss = 0.0
    # scheduler.step(epoch)
    correct = 0
    total=0 
    train_dataset = cube_Dataset(train_set,train_y, transform)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, 
                                          sampler=train_sampler)
    for batch_idx, (data_, target_) in enumerate(train_loader):
        # zero the parameter gradients
        optimizer.zero_grad()
        # forward + backward + optimize
        outputs = model(data_)
        loss = criterion(outputs, target_)
        loss.backward()
        optimizer.step()
        # print statistics
        running_loss += loss.item()
        _,pred = torch.max(outputs, dim=1)
        correct += torch.sum(pred==target_).item()
        total += target_.size(0)
        if (batch_idx) % 20 == 0:
            print ('------------Epoch [{}/{}]----------- Loss: {:.4f}' 
                  .format(epoch, 20, loss.item()))
    train_acc.append(100 * correct / total)
    train_loss.append(running_loss/total_step)
    print(f'\ntrain loss: {np.mean(train_loss):.4f}, train acc: {(100 * correct / total):.4f}')
    batch_loss = 0
    total_t=0
    correct_t=0
    with torch.no_grad():
        model.eval()
        for data_t, target_t in (validation_loader):
            #data_t, target_t = data_t.to(device), target_t.to(device)# on GPU
            outputs_t = model(data_t)
            loss_t = criterion(outputs_t, target_t)
            batch_loss += loss_t.item()
            _,pred_t = torch.max(outputs_t, dim=1)
            correct_t += torch.sum(pred_t==target_t).item()
            total_t += target_t.size(0)
        cur_acc = 100 * correct_t / total_t
        val_acc.append(cur_acc)
        val_loss.append(batch_loss/len(validation_loader))
        network_learned = batch_loss < valid_loss_min
        print(f'validation loss: {np.mean(val_loss):.4f}, validation acc: {(cur_acc):.4f}\n')
        if cur_acc > best_acc:
          best_acc = cur_acc
          es = 0
        else:
          es += 1
        if es == 5:
          print('Early stopping with best acc: ',best_acc)
          break
    model.train()

train_acc

val_acc

torch.save(model.state_dict(), '/content/drive/MyDrive/BS6207/Project/final_model.pt')

"""## Model prefermance """

confusion_matrix = torch.zeros(2, 2)
device = torch.device( "cpu")
with torch.no_grad():
    for i, (inputs, classes) in enumerate(validation_loader):
        inputs = inputs.to(device)
        classes = classes.to(device)
        outputs = model(inputs)
        _, preds = torch.max(outputs, 1)
        for t, p in zip(classes.view(-1), preds.view(-1)):
                confusion_matrix[t.long(), p.long()] += 1

print(confusion_matrix)



"""# Test Processure"""

# sacle the test data
scaled_test = {
    'proteins': list(),
    'ligands': list()
}
for i in range(len(test_data['proteins'])):
  mean_center = np.expand_dims(np.mean(test_data['ligands'][i][:3],axis = 1),axis = 1)
  temp_pro = np.array(test_data['proteins'][i][:3]) - mean_center
  scaled_test['proteins'].append([temp_pro,test_data['proteins'][i][3]])
  temp_gli = np.array(test_data['ligands'][i][:3]) - mean_center
  scaled_test['ligands'].append([temp_gli,test_data['ligands'][i][3]])

# build the protein cubes
def test_cubes_protein(cubes_size, scaled_data,n):
  # in order to convert to tensor the datatype should be float32
  cube = np.zeros((2,cubes_size,cubes_size,cubes_size),dtype=np.float32)
  cubes = []
  # the oringal size of cubes should be 100 * 100 * 100
  ratio = 100/cubes_size
  shiftL = (cubes_size - 1 ) // 2
  discard_num = [0,0]
  overlap_num = [0,0]
  # protein:
  for i in range(n):
    for j in range(len(scaled_data['proteins'][i][0][0])):
      x_p, y_p,z_p = scaled_data['proteins'][i][0][0][j],scaled_data['proteins'][i][0][1][j],scaled_data['proteins'][i][0][2][j]
      # and convert the data type of (x,y,z) into int
      x_p, y_p,z_p = int(x_p/ratio + shiftL),int(y_p/ratio + shiftL),int(z_p/ratio + shiftL)
      # crop the cube 
      if x_p >= cubes_size or  y_p >= cubes_size or z_p >= cubes_size or x_p < 0 or  y_p < 0 or z_p < 0 :
        discard_num[0] += 1
        continue
      # check the overlaping atoms
      if cube[0,x_p, y_p,z_p] !=0 or cube[1,x_p, y_p,z_p] !=0:
        overlap_num[0] += 1
        continue
      # first channel
      cube[0,x_p, y_p,z_p] = -1
      # second channel
      if scaled_data['proteins'][i][1][j] == 'h':
        cube[1,x_p, y_p,z_p] = 1
      else:
        cube[1,x_p, y_p,z_p] = -1
    cubes.append(cube)
  return np.array(cubes,dtype=np.float32),  discard_num, overlap_num

test_cubes,  discard_num, overlap_num = test_cubes_protein(25, scaled_test,824)

# connet the different ligands with curtain protein
def march_with_ligand(cubes_size,protein_cube,start,end,scaled_data):
  matched_cube = []
  ratio = 100/cubes_size
  shiftL = (cubes_size - 1 ) // 2
  discard_num = [0,0]
  overlap_num = [0,0]
  for i in range(start,end):
    for k in range(len(scaled_data['ligands'][i][0][0])):
      x_l, y_l,z_l = scaled_data['ligands'][i][0][0][k],scaled_data['ligands'][i][0][1][k],scaled_data['ligands'][i][0][2][k]
      x_l, y_l,z_l = int(x_l/ratio + shiftL),int(y_l/ratio + shiftL),int(z_l/ratio + shiftL)
      if x_l >= cubes_size or  y_l >= cubes_size or z_l >= cubes_size or x_l < 0 or  y_l < 0 or z_l < 0 :
        discard_num[1] += 1
        continue
      if protein_cube[0,x_l, y_l,z_l] !=0 or protein_cube[1,x_l, y_l,z_l] !=0:
        overlap_num[1] += 1
        continue
      # first channel
      protein_cube[0,x_l, y_l,z_l] = 1
      # second channel
      if scaled_data['ligands'][i][1][k] == 'h':
        protein_cube[1,x_l, y_l,z_l] = 1
      else:
        protein_cube[1,x_l, y_l,z_l] = -1

    matched_cube.append(protein_cube)
  return np.array(matched_cube)

test_tensor = torch.from_numpy(test_cubes)
test_tensor.shape

# generate the result and save them in the top10_res list
top10_res = []
for i in range(824):
  pred_lis = []
  matched_cube = march_with_ligand(25,test_cubes[i],0,64,scaled_test)
  matched_cube = torch.from_numpy(matched_cube)
  out = model(matched_cube)
  pre_prob,pre_pred = torch.max(out, dim=1)
  # 64 for one batch 13batch in total
  for j in range(1,13):
    if j == 12:
      batch_size = 56
    else:
      batch_size = 64 
    start = j*batch_size
    end = (j + 1) * batch_size
    matched_cube = march_with_ligand(25,test_cubes[i],start, end,scaled_test)
    matched_cube = torch.from_numpy(matched_cube)
    out = model(matched_cube)
    cur_prob,cur_pred = torch.max(out, dim=1)
    cur_prob = torch.cat((pre_prob,cur_prob))
    pre_prob,pre_pred = cur_prob,cur_pred
  top_pro, top10_index = torch.topk(cur_prob,10)
  top10_res.append(top10_index.numpy())

top10_res = np.concatenate((first1,first2,first3,first4,first5,first6))
top10_res[0]

# build the data frame
df = pd.DataFrame(top10_res,columns=['lig1_id','lig2_id','lig3_id','lig4_id','lig5_id','lig6_id','lig7_id','lig8_id','lig9_id','lig10_id'])
df['pro_id'] = range(1,825)
df = df.set_index('pro_id')
df

# save to txt
df.to_csv('test_predictions.txt',sep=" ")