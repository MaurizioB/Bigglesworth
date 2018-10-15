MAJ_VERSION = 0
MIN_VERSION = 15
REV_VERSION = 3
__version__ = '{}.{}.{}'.format(MAJ_VERSION, MIN_VERSION, REV_VERSION)

def getUniqueVersion():
    #REV_VERSION has bitmask 4095 (0b111111111111)
    #MIN_VERSION has bitmask 1044480, or 255 << 12 (0b11111111000000000000)
    #MAJ_VERSION has bitmask << 20
    return REV_VERSION + (MIN_VERSION << 12) + (MAJ_VERSION << 20)

def getUniqueVersionToMin():
    return MIN_VERSION + (MAJ_VERSION << 8)

def decodeVersion(unique):
    revVersion = unique & 4095
    minVersion = (unique >> 12) & 255
    majVersion = unique >> 20
    return majVersion, minVersion, revVersion

def decodeVersionToMin(unique):
    minVersion = unique & 255
    majVersion = unique >> 8
    return majVersion, minVersion
