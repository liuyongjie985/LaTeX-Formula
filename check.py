# -*- coding: UTF-8 -*-

# Author       : jiangweijw
# Email        : ...
# Created time : 2020-12-23
# Filename     : check.py
# Description  : ...


import argparse
import codecs
import os


with codecs.open('specific_symbols.txt', 'r', 'utf-8') as f:
    lines = [item.strip() for item in f.readlines()]
table = ''.join(lines)


def main(args):
    source = args.source
    dest = args.dest

    with codecs.open(source, 'r', 'utf-8') as f:    
        latex_formula = [item.strip() for item in f.readlines()]

    with codecs.open(dest, 'w', 'utf-8') as f:
        for line in latex_formula:
            for symbol in line:
                if symbol in table:
                    f.write('{} --- {}\n'.format(symbol, line))
                    break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()    
    parser.add_argument('-i', '--source', type=str)
    parser.add_argument('-o', '--dest', type=str)
    main(parser.parse_args())
