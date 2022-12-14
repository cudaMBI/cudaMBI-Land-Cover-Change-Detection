import datetime
import logging
from tensorboardX import SummaryWriter
import torch
from tqdm import tqdm
import random
import numpy as np
import os
from helper import (get_loaders, load_model, get_criterion, initialize_metrics,
                   set_metrics, get_mean_metrics)
from sklearn.metrics import precision_recall_fscore_support as prfs

"""
Initialize Parser and define arguments

import parse
from parse import get_parser_with_args

parser, metadata = get_parser_with_args()
opt = parser.parse_args()
"""
opt = {"augmentation": False,
        "num_gpus": 1,
        "num_workers": 0,
        "num_channel": 3,
        'loss_function':'bce',
        "epochs": 100,
        "batch_size": 16,
        "learning_rate": 1e-3,
        "dataset_dir": "D:/grad-project/datasets/CDData/Real/subset/",
        "log_dir": "./log/"
      }

"""
Initialize experiments log

logging.basicConfig(level=logging.INFO)
writer = SummaryWriter(opt['log_dir'] + f'/{datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")}/')

"""

"""
Set up environment: define paths, download data, and set device
"""
# os.environ["CUDA_VISIBLE_DEVICES"] = "0"
dev = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
#logging.info('GPU AVAILABLE? ' + str(torch.cuda.is_available())) == print(dev)

def seed_torch(seed=0):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    # torch.cuda.manual_seed_all(seed) # if you are using multi-GPU.
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True

seed_torch(seed=777)

train_loader, val_loader = get_loaders(opt)

"""
Load Model then define other aspects of the model
"""
logging.info('LOADING Model')
model = load_model(opt, dev)

criterion = get_criterion(opt)
optimizer = torch.optim.AdamW(model.parameters(), lr=opt['learning_rate']) # Be careful when you adjust learning rate, you can refer to the linear scaling rule
#scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=8, gamma=0.5)

"""
 Set starting values
 
best_metrics = {'cd_f1scores': -1, 'cd_recalls': -1, 'cd_precisions': -1}
logging.info('STARTING training')
total_step = -1
"""

logging.info('STARTING training')

for epoch in range(opt['epochs']):  # loop over the dataset multiple times
    
    train_metrics = initialize_metrics()

    for i, data in enumerate(train_loader, 0):
        # get the inputs; data is a list of [batch_img1, batch_img2, labels]
        batch_img1, batch_img2, labels = data
        
        # Set variables for training
        batch_img1 = batch_img1.float().to(dev)
        batch_img2 = batch_img2.float().to(dev)
        labels = labels.long().to(dev)

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        # Get model predictions, calculate loss, backprop
        cd_preds = model(batch_img1, batch_img2)

        cd_loss = criterion(cd_preds, labels)
        loss = cd_loss
        loss.backward()
        optimizer.step()
        
        cd_preds = cd_preds[-1]
        _, cd_preds = torch.max(cd_preds, 1)
        
        # Calculate and log other batch metrics
        cd_corrects = (100 *
                       (cd_preds.squeeze().byte() == labels.squeeze().byte()).sum() /
                       (labels.size()[0] * (opt['batch_size']**2)))
        
        cd_train_report = prfs(labels.data.cpu().numpy().flatten(),
                               cd_preds.data.cpu().numpy().flatten(),
                               average='binary',
                               zero_division=0,
                               pos_label=1)
        
        train_metrics = set_metrics(train_metrics,
                                    cd_loss,
                                    cd_corrects,
                                    cd_train_report,
                                    scheduler.get_last_lr())
        
        # log the batch mean metrics
        mean_train_metrics = get_mean_metrics(train_metrics)
        
        #for k, v in mean_train_metrics.items():
           # writer.add_scalars(str(k), {'train': v}, total_step)

        # clear batch variables from memory
        del batch_img1, batch_img2, labels
        
        
        # print statistics
        if i % 1000 == 0:    # print every 2000 mini-batches
            print(f"[{opt['epoch'] + 1}, {i + 1:5d}] loss: {mean_train_metrics['cd_losses']:.5f}")


logging.info('Finished training')





