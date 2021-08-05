# -*- coding: UTF-8 -*-

# Author       : jiangweijw
# Email        : ...
# Created time : 2020-12-23
# Filename     : generator.py
# Description  : ...


import argparse
import codecs
import cv2
import imgaug.augmenters as iaa
import math
import numpy as np
import os
import random
import time
from pdf2image import convert_from_path
from subprocess import check_call, DEVNULL 
from threading import Thread, Lock


# 背景图
background_files = [os.path.join('backgrounds', item)
                    for item in os.listdir('backgrounds')]
# LaTex 文件模板
with codecs.open('template.txt', 'r', 'utf-8') as f:
    template = f.read()

# 常见的中文符号，需要特殊处理
with codecs.open('chinese_symbols.txt', 'r', 'utf-8') as f:
    chinese_symbols = [item.strip() for item in f.readlines()]
chinese_symbols = ''.join(chinese_symbols)
chinese_symbols = chinese_symbols.replace(' ', '')

labels = []


def run_cmd(command):
    """
    执行系统命令

    Args:
        command: 具体的命令
    Return:
        None
    """
    check_call(command, shell=True, encoding='utf-8',
               stdout=DEVNULL, stderr=DEVNULL, timeout=10) 

def gen_tex(formula, latex_output_path):
    """
    根据模板生成 LaTeX 文件

    Args:
        formula: LaTeX 公式
        latex_output_path: LaTeX 文件的存储位置
    Return:
        None
    """
    latex = ''
    for ch in formula:
        if (('\u4e00' <= ch and ch <= '\u9fa5') or
            ('\u3400' <= ch and ch <= '\u4dbf') or
            (ch in chinese_symbols)):
            latex += r'\mbox{' + ch + '}'
        else:
            latex += ch

    with codecs.open(latex_output_path, 'w', 'utf-8') as f:
        f.write(template.format(latex))

def gen_pdf(latex_save_path, pdf_output_path):
    """
    根据 LaTeX 文件生成 PDF 文件

    Args:
        latex_save_path: LaTeX 文件的存储位置
        pdf_output_path: PDF 文件的输出位置
    Return:
        None
    """
    command = 'pdflatex --output-directory={} {}'\
              .format(os.path.dirname(pdf_output_path), latex_save_path)
    run_cmd(command)

def random_background(width, height):
    """
    随机选取一张背景图，并调整至合适尺寸

    Args:
        width: 所需背景图的宽度
        height: 所需背景图的高度
    Return:
        None
    """
    background_file = random.choice(background_files)
    orig_img = cv2.imread(background_file, cv2.IMREAD_COLOR)
    
    if orig_img.shape[0] > height and orig_img.shape[1] > width:
        random_x = random.randint(0, orig_img.shape[0] - height)
        random_y = random.randint(0, orig_img.shape[1] - width)
        img = orig_img[random_x:random_x+height, random_y:random_y+width]
    else:
        img = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(0, height, orig_img.shape[0]):
            for j in range(0, width, orig_img.shape[1]):
                for x in range(orig_img.shape[0]):
                    for y in range(orig_img.shape[1]):
                        if i + x >= height or j + y >= width:
                            continue
                        img[i+x, j+y] = orig_img[x, y]
    return img

def gen_png(pdf_save_path, png_output_path):
    """
    根据 PDF 文件生成 PNG 文件

    Args:
        pdf_save_path: PDF 文件的存储位置
        png_output_path: PNG 文件的输出位置
    """
    img = convert_from_path(pdf_save_path, dpi=300, fmt='png')[0]
    img = np.array(img)
    idx = np.where(img < 255)
    img = img[min(idx[0]):max(idx[0])+1, min(idx[1]):max(idx[1])+1, :]
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) 

    height, width = img.shape
    background = random_background(width, height)
    for i in range(height):
        for j in range(width):
            gray = img[i, j] 
            if gray < 128:
                background[i, j] = [random.randint(64, 96)] * 3
    
    def aug(image):
        sometimes = lambda aug: iaa.Sometimes(0.80, aug)
        seq = iaa.Sequential(iaa.SomeOf((1, 1), [
            iaa.LogContrast(gain=(0.95, 1.0)),
            iaa.imgcorruptlike.JpegCompression(severity=(1, 2))
        ], random_order=True))
        return seq.augment_image(image)
        
    if height < 32 or width < 32:
        pass
    else:
        background = aug(background)

    cv2.imwrite(png_output_path, background)

def batch_process(tid, tasks, prefix, output):
    for task in tasks:
        try:
            tex_path = os.path.join(output, 'tmp', str(task[0]) + '.tex') 
            pdf_path = os.path.join(output, 'tmp', str(task[0]) + '.pdf') 
            png_path = os.path.join(output, 'images', 
                                    prefix + str(task[0]) + '.png') 

            gen_tex(task[1], tex_path)
            gen_pdf(tex_path, pdf_path)
            gen_png(pdf_path, png_path)
            labels[tid].append((os.path.basename(png_path), task[1]))
        except Exception as e:
            print(e)

def main(args):
    global labels
    latex_file = args.source
    output = args.dest
    thread_num = args.thread
    prefix = args.prefix + '_'

    os.makedirs(os.path.join(output, 'images'), exist_ok=True)
    os.makedirs(os.path.join(output, 'tmp'), exist_ok=True)

    with codecs.open(latex_file, 'r', 'utf-8') as f:
        latexs = [(idx, item.strip()) 
                  for idx, item in enumerate(f.readlines())]

    batch_size = math.ceil(len(latexs) / thread_num)
    threads = []
    for i in range(thread_num):
        tasks = latexs[i*batch_size:(i+1)*batch_size]
        threads.append(
            Thread(target=batch_process, args=(i, tasks, prefix, output)))
    
    labels = [[]] * thread_num

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with codecs.open(os.path.join(output, 'labels.txt'), 'w', 'utf-8') as f:
        for bucket in labels: 
            for img_name, latex in bucket:
                f.write('{} {}\n'.format(img_name, latex))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()    
    parser.add_argument('-i', '--source', type=str)
    parser.add_argument('-o', '--dest', type=str)
    parser.add_argument('-t', '--thread', type=int)
    parser.add_argument('-p', '--prefix', type=str)
    main(parser.parse_args())
