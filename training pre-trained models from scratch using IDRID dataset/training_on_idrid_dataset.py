# -*- coding: utf-8 -*-
"""training on IDRID dataset.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/18X87OIzwokFPfXGpuqX3uJFIbIE8I842
"""

import torch
import os
import pandas as pd
from torchvision.io import read_image
from torch.utils.data import Dataset, DataLoader
import torch.nn as nn
from torchvision import models, transforms
import torch.optim as optim
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import cv2
from PIL import Image

"""Main steps involved:<br>
1. Loading IDRID data<br>
2. Loading the ResNet/VGGNet/AlexNet model and modify the final layer
3. Evaluating the model and calculate performance metrics(accuracy, precision, recall, senstivity, specificity)

"""

from google.colab import drive
drive.mount('/content/drive')

train_image_dir = '/content/drive/MyDrive/B. Disease Grading/B. Disease Grading/1. Original Images/a. Training Set'
test_image_dir = '/content/drive/MyDrive/B. Disease Grading/B. Disease Grading/1. Original Images/b. Testing Set'
train_image_labels = '/content/drive/MyDrive/B. Disease Grading/B. Disease Grading/2. Groundtruths/a. IDRiD_Disease Grading_Training Labels.csv'
test_image_labels = '/content/drive/MyDrive/B. Disease Grading/B. Disease Grading/2. Groundtruths/b. IDRiD_Disease Grading_Testing Labels.csv'

train_csv = pd.read_csv(train_image_labels)
test_csv = pd.read_csv(test_image_labels)

# print(train_csv.columns)
# unique = train_csv['Retinopathy grade'].unique()
# print(unique)
# for grade in unique:
#     print(f"Images with retinopathy grade {grade}:")
#     images = train_csv[train_csv['Retinopathy grade'] == grade]['Image name']
#     for image in images:
#         print(image)
#         print("\n")

transform = transforms.Compose([
        transforms.RandomResizedCrop((224,224)), #resized to resnet input
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]) #normalize like ImageNet
    ])

class IDRIDDataset(Dataset):
    def __init__(self, img_dir, csv_data, transform, file_extension=".jpg"):
        self.img_dir = img_dir
        self.csv_data = csv_data
        self.transform = transform
        self.file_extension = file_extension

    def __len__(self):
        return len(self.csv_data)

    def __getitem__(self, idx):
        img_name = self.csv_data.iloc[idx, 0] + self.file_extension
        img_path = os.path.join(self.img_dir, img_name)
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)

        if self.transform:
            image = self.transform(image)

        label = self.csv_data.iloc[idx, 1]
        return image, label

train_dataset = IDRIDDataset(train_image_dir, train_csv, transform)
test_dataset = IDRIDDataset(test_image_dir, test_csv, transform)

batch_size = 64
train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size, shuffle = True)
test_loader = DataLoader(dataset=test_dataset, batch_size=batch_size, shuffle = False)

model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
num_features = model.fc.in_features
num_classes = len(set(train_csv['Retinopathy grade'].tolist()))
model.fc = nn.Linear(num_features,num_classes)

criteria = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr= 0.01)

num_epochs = 50
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

for epoch in range(num_epochs):
  train_loss = 0.0
  corr_pred = 0
  total_pred = 0
  model.train()
  for images, labels in train_loader:
    images, labels = images.to(device), labels.to(device)

    optimizer.zero_grad()
    outputs = model(images)
    loss = criteria(outputs, labels)
    loss.backward()
    optimizer.step()
    train_loss += loss.item() * images.size(0)

    _, predicted = torch.max(outputs.data, 1)
    total_pred += labels.size(0)
    corr_pred += (predicted == labels).sum().item()
    accuracy = corr_pred / total_pred

  train_loss = train_loss / len(train_dataset)
  print(f"Epoch [{epoch+1}/{num_epochs}], Loss: {train_loss: .4f}, Accuracy: {accuracy}")
print("Finished Training")

model.eval()
y_true = []
y_pred = []

with torch.no_grad():
  for images, labels in test_loader:
    images, labels = images.to(device), labels.to(device)
    outputs = model(images)
    _, predicted = torch.max(outputs.data, 1)
    y_true.extend(labels.cpu().numpy())
    y_pred.extend(predicted.cpu().numpy())

accuracy = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, average='macro')
recall = recall_score(y_true, y_pred, average='macro')
f1 = f1_score(y_true, y_pred, average='macro')

print(f'Classification Accuracy: {accuracy:.4f}')
print(f'Precision: {precision:.4f}')
print(f'Recall: {recall:.4f}')
print(f'F1-Score: {f1:.4f}')
print('Classification Report:')
print(classification_report(y_true, y_pred))

sensitivity = {}
specificity = {}
conf_mat = confusion_matrix(y_true, y_pred)
class_accuracies = conf_mat.diagonal() / conf_mat.sum(axis=1)
for idx, class_accuracy in enumerate(class_accuracies):
    print(f"Class {idx} Accuracy: {class_accuracy:.4f}")

for i in range(num_classes):
    tp = conf_mat[i, i]
    fn = conf_mat[i, :].sum() - tp
    fp = conf_mat[:, i].sum() - tp
    tn = conf_mat.sum() - (tp + fp + fn)
    sensitivity[i] = tp / (tp + fn)
    specificity[i] = tn / (tn + fp)

print(f'Sensitivity: {sensitivity}')
print(f'Specificity: {specificity}')

