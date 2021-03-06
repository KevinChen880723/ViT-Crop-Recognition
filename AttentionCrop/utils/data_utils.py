import torch
from torchvision import transforms
from torch.utils.data import DataLoader

import os
import numpy as np
import pandas as pd
import PIL.Image as Image
import torchvision.transforms.functional as F

class Crop_Divisible_By_N(object):
    def __init__(self, N) -> None:
        self.n = int(N)
    def __call__(self, img):
        (h, w) = img.shape[-2:]
        crop_size_h = (h // self.n) * self.n
        crop_size_w = (w // self.n) * self.n
        return F.crop(img, top=0, left=0, height=crop_size_h, width=crop_size_w)

class Cropping_Dataset_SplitByCSV(torch.utils.data.Dataset):
    def __init__(self, cfg, transforms, mode='train', return_file_name=False):
        super().__init__()
        if mode == 'train':
            df = pd.read_csv(cfg['data']['path_csv_train'], header=None)
        elif mode == 'val':
            df = pd.read_csv(cfg['data']['path_csv_val'], header=None)
        elif mode == 'test':
            df = pd.read_csv(cfg['test']['path_csv_test'], header=None)
        self.list_datapair = df.values
        self.transforms = transforms
        self.root_dataset_img = cfg['data']['root_dataset_img']
        self.root_dataset_attn = cfg['data']['root_dataset_attn']
        self.len = len(self.list_datapair)
        self.format_attn = cfg['data']['format_attn']
        self.classification_model_resolution = cfg['data']['classification_model_resolution']
        self.return_file_name = return_file_name

    def __getitem__(self, index):
        ''' Load the image '''
        path_img = os.path.join(self.root_dataset_img, self.list_datapair[index][1], self.list_datapair[index][0])
        img = Image.open(path_img)
        img.convert('RGB')
        if self.transforms != None:
            img = self.transforms(img)
        (img_h, img_w) = img.shape[-2:]
        ''' Load the label (attention map) '''
        file_name_attn = self.list_datapair[index][0][:self.list_datapair[index][0].rfind('.')]+self.format_attn
        path_attn = os.path.join(self.root_dataset_attn, self.list_datapair[index][1], file_name_attn)
        # Load the label, then normalize the map
        attn_map = np.fromfile(path_attn, np.float64)
        attn_map /= np.abs(attn_map).max()
        label = torch.from_numpy(attn_map).reshape((int(img_h/self.classification_model_resolution), int(img_w/self.classification_model_resolution)))
        if self.return_file_name:
            file_name_prefix = self.list_datapair[index][0][:self.list_datapair[index][0].rfind('.')]
            data = (img.to(torch.float32), label.to(torch.float32), self.list_datapair[index][1], file_name_prefix)
        else:
            data = (img.to(torch.float32), label.to(torch.float32))
        return data

    def __len__(self):
        return self.len

class Dataset_SplitByCSV(torch.utils.data.Dataset):
    def __init__(self, root_dataset, path_csv, transform=None, return_file_name=False, start_from=0, end_to=-1):
        super().__init__()
        self.className2idx = {
            'banana': 0, 
            'bareland': 1,
            'carrot': 2,
            'corn': 3,
            'dragonfruit': 4,
            'garlic': 5,
            'guava': 6,
            'inundated': 7,
            'peanut': 8,
            'pineapple': 9,
            'pumpkin': 10,
            'rice': 11,
            'soybean': 12,
            'sugarcane': 13,
            'tomato': 14 
        }

        df = pd.read_csv(path_csv, header=None)
        df.info()
        self.list_datapair = df.values
        if end_to == -1:
            self.list_datapair = self.list_datapair[start_from:]
        else:
            self.list_datapair = self.list_datapair[start_from:end_to]
        self.transform = transform
        self.root_dataset = root_dataset
        self.len = len(self.list_datapair)
        self.return_file_name = return_file_name

    def __getitem__(self, index):
        data_path = os.path.join(self.root_dataset, self.list_datapair[index][1], self.list_datapair[index][0])
        img = Image.open(data_path)
        img.convert('RGB')
        if self.transform != None:
            img = self.transform(img)
        label = torch.tensor(self.className2idx[self.list_datapair[index][1]])
        if self.return_file_name:
            file_name_prefix = self.list_datapair[index][0][:self.list_datapair[index][0].rfind('.')]
            data = (img, label, self.list_datapair[index][1], file_name_prefix)
        else:
            data = (img, label)
        return data

    def __len__(self):
        return self.len

def get_attn_loader(cfg):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    dataset = Dataset_SplitByCSV(cfg['directory']['data']['root-dir'], 
                                 cfg['directory']['data']['path-csv'],
                                 transform=transform,
                                 return_file_name=True,
                                 start_from=cfg['train']['index-start'],
                                 end_to=cfg['train']['index-end'])
    dataloader = DataLoader(dataset, 1, False)
    return dataloader

def get_cropping_model_loader(cfg, return_file_name=False, is_test=False):
    transforms_ = transforms.Compose([
        transforms.ToTensor(),
        Crop_Divisible_By_N(cfg['data']['classification_model_resolution']),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    if is_test:
        dataset = Cropping_Dataset_SplitByCSV(cfg, transforms_, mode='test', return_file_name=return_file_name)
        dataloader = DataLoader(dataset, cfg['train']['batch_size'], False)
        return dataloader
    else:
        dataset_train = Cropping_Dataset_SplitByCSV(cfg, transforms_, mode='train', return_file_name=return_file_name)
        dataset_val = Cropping_Dataset_SplitByCSV(cfg, transforms_, mode='val', return_file_name=return_file_name)
        dataloader_train = DataLoader(dataset_train, cfg['train']['batch_size'], True)
        dataloader_val = DataLoader(dataset_val, cfg['val']['batch_size'], False)
        return (dataloader_train, dataloader_val)