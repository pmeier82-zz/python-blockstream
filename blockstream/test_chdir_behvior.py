'''
Created on 10 May 2011

@author: phil
'''

import os

def do_something():
    """do something and change the dir to here"""

    print __file__
    target_dir = os.path.dirname(__file__)
    if os.getcwd() != target_dir:
        os.chdir(target_dir)


if __name__ == '__main__':

    print os.getcwd()
    do_something()
    print os.getcwd()
