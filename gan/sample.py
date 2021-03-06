import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import glob
import argparse
import torch
import torchvision
from torch.autograd import Variable
from dataset import VQADataset

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",
                        choices=("stage1", "stage2"))
    parser.add_argument("--cuda",
                        action="store_true")
    parser.add_argument("--dataset_dir",
                        type=str,
                        default="dataset/")
    parser.add_argument("--model_dir",
                        type=str,
                        default="model/")
    parser.add_argument("--sample_dir",
                        type=str,
                        default="sample/stage1")
    return parser.parse_args()


def _load(generator, directory):
    paths = glob.glob(os.path.join(directory, "*.pth"))
    gen_path = [path for path in paths if "generator" in path][0]
    generator.load_state_dict(torch.load(gen_path))
    print("Load pretrained [{}]".format(gen_path))


def _sample(indices, config):
    dataset = VQADataset(config.dataset_dir, output_shape=[256, 256], train=False)
    
    if config.action == "stage1":
        stage1_generator = Generator()
        _load(stage1_generator, os.path.join(config.model_dir, "stage1"))
    else:
        stage1_generator = Stage1Generator()
        stage2_generator = Stage2Generator()
        _load(stage1_generator, os.path.join(config.model_dir, "stage1"))
        _load(stage2_generator, os.path.join(config.model_dir, "stage2"))

    ims, embeds, captions = [], [], []
    for idx in indices:
        im, embed, caption = dataset[idx]
        ims.append(im)
        embeds.append(embed)
        captions.append(caption)

    ims    = torch.stack(ims, 0)
    embeds = torch.stack(embeds, 0)
    noise  = Variable(torch.randn(len(indices), 100))

    if config.cuda:
        noise = noise.cuda()
        embeds = Variable(embeds).cuda()
    else:
        embeds = Variable(embeds)
    embeds = embeds.view(len(indices), -1)
    
    fake_ims_stage1 = stage1_generator(noise, embeds)
    torchvision.utils.save_image(ims,
                                 "{}/real.png".format(config.sample_dir),
                                 normalize=True)
    torchvision.utils.save_image(fake_ims_stage1.data,
                                 "{}/fake_stage1.png".format(config.sample_dir),
                                 normalize=True)

    if config.action == "stage2":
        fake_ims_stage2 = stage2_generator(fake_ims_stage1, embeds)
        torchvision.utils.save_image(fake_ims_stage2.data,
                                     "{}/fake_stage2.png".format(config.sample_dir),
                                     normalize=True)
        
    _file = open("{}/captions.txt".format(config.sample_dir), "w")
    for i, caption in enumerate(captions):
        _file.write("index: {}\n".format(indices[i]))
        for c in caption:
            _file.write(c+"\n")
        _file.write("\n")
    _file.close()
    


def main(config):
    random_index = list(range(16, 32))
    _sample(random_index, config)

if __name__ == "__main__":
    config = parse_args()

    if config.action == "stage1":
        from stage1.model import Generator
    elif config.action == "stage2":
        from stage2.model import Stage1Generator, Stage2Generator

    main(config)
