import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

SHARDS_COUNT = 1

def get_shd_num(pkv, shd_cnt):
    return pkv % SHARDS_COUNT

def encode_pkv(pkv, shd_cnt, shd_num):
    return int((pkv - shd_num) / SHARDS_COUNT) #always integer, but have to converse

def decode_pkv(pkv, shd_cnt, shd_num):
    return pkv * SHARDS_COUNT + shd_num