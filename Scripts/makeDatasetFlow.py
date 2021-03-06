import os
import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np
import random
import glob
import sys


def gen_split(root_dir, stackSize, LSTA=False):
    DatasetX = []
    DatasetY = []
    Labels = []
    #actionLabels = [] 
    NumFrames = []
    root_dir = os.path.join(root_dir, 'flow_x_processed')
    for dir_user in sorted(os.listdir(root_dir)):
        if not dir_user.startswith('.') and dir_user:
            class_id = 0
            directory = os.path.join(root_dir, dir_user)
            action = sorted(os.listdir(directory))

            if LSTA is True:
              action_only = [a.split("_")[0] for a in action]

            targets = sorted(os.listdir(directory))


            for i, target in enumerate(sorted(os.listdir(directory))):
                
                if LSTA is True:
                  target_only = target.split("_")[0]
                  #print(target, target_only)

                if not target.startswith('.'):
                    directory1 = os.path.join(directory, target)
                    insts = sorted(os.listdir(directory1))
                    if insts != []:
                        for inst in insts:
                            if not inst.startswith('.'): 
                                inst_dir = os.path.join(directory1, inst)
                                numFrames = len(glob.glob1(inst_dir, '*.png'))
                                if numFrames >= stackSize:
                                    DatasetX.append(inst_dir)
                                    DatasetY.append(inst_dir.replace('flow_x', 'flow_y'))
                                    Labels.append(class_id)
                                    NumFrames.append(numFrames)

                if LSTA is True:
                  if i < len(targets)-1:
                    if targets[i+1].split("_")[0] != target_only:
                      class_id += 1
                else:
                  class_id += 1

    if LSTA is True:
      return DatasetX, DatasetY, Labels, NumFrames, action_only
    else:
      return DatasetX, DatasetY, Labels, NumFrames, action



class makeDatasetFlow(Dataset):
    def __init__(self, root_dir, spatial_transform=None, sequence=False, stackSize=5,
                 train=True, numSeg = 1, fmt='.png', phase='train', LSTA=False):
        """
        Args:
            root_dir (string): Directory with all the images.
            transform (callable, optional): Optional transform to be applied
                on a sample.
        """
        self.imagesX, self.imagesY, self.labels, self.numFrames, self.action = gen_split(root_dir, stackSize, LSTA)
        self.spatial_transform = spatial_transform
        self.train = train
        self.numSeg = numSeg
        self.sequence = sequence
        self.stackSize = stackSize
        self.fmt = fmt
        self.phase = phase

    def __len__(self):
        return len(self.imagesX)

    def __getitem__(self, idx):
        vid_nameX = self.imagesX[idx]
        vid_nameY = self.imagesY[idx]
        #print(len(self.labels), self.labels)
        #print(idx)

        label = self.labels[idx]
        numFrame = self.numFrames[idx]
        inpSeqSegs = []
        self.spatial_transform.randomize_parameters()
        if self.sequence is True:
            if numFrame <= self.stackSize:
                frameStart = np.ones(self.numSeg)
            else:
                frameStart = np.linspace(1, numFrame - self.stackSize + 1, self.numSeg, endpoint=False)
            for startFrame in frameStart:
                inpSeq = []
                for k in range(self.stackSize):
                    i = k + int(startFrame)
                    fl_name = vid_nameX + '/flow_x_' + str(int(round(i))).zfill(5) + self.fmt
                    img = Image.open(fl_name)
                    inpSeq.append(self.spatial_transform(img.convert('L'), inv=True, flow=True))
                    # fl_names.append(fl_name)
                    fl_name = vid_nameY + '/flow_y_' + str(int(round(i))).zfill(5) + self.fmt
                    img = Image.open(fl_name)
                    inpSeq.append(self.spatial_transform(img.convert('L'), inv=False, flow=True))
                inpSeqSegs.append(torch.stack(inpSeq, 0).squeeze())
            inpSeqSegs = torch.stack(inpSeqSegs, 0)
            return inpSeqSegs, label
        else:
            if numFrame <= self.stackSize:
                startFrame = 1
            else:
                if self.phase == 'train':
                    startFrame = random.randint(1, numFrame - self.stackSize)
                else:
                    startFrame = np.ceil((numFrame - self.stackSize)/2)
            inpSeq = []
            for k in range(self.stackSize):
                i = k + int(startFrame)
                fl_name = vid_nameX + '/flow_x_' + str(int(round(i))).zfill(5) + self.fmt
                img = Image.open(fl_name)
                inpSeq.append(self.spatial_transform(img.convert('L'), inv=True, flow=True))
                # fl_names.append(fl_name)
                fl_name = vid_nameY + '/flow_y_' + str(int(round(i))).zfill(5) + self.fmt
                img = Image.open(fl_name)
                inpSeq.append(self.spatial_transform(img.convert('L'), inv=False, flow=True))
            inpSeqSegs = torch.stack(inpSeq, 0).squeeze(1)
            return inpSeqSegs, label#, fl_name
    def __getLabel__(self):
        return self.action
