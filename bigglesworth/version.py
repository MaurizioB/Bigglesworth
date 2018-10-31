MAJ_VERSION = 0
MIN_VERSION = 16
REV_VERSION = 1
__version__ = '{}.{}.{}'.format(MAJ_VERSION, MIN_VERSION, REV_VERSION)

def isNewer(*version):
    if len(version) == 1 and isinstance(version[0], (str, unicode)):
        version = map(int, version[0].split('.'))
    return getUniqueVersion(*version) > getUniqueVersion()

def getUniqueVersion(majVersion=MAJ_VERSION, minVersion=MIN_VERSION, revVersion=REV_VERSION):
    #REV_VERSION has bitmask 4095 (0b111111111111)
    #MIN_VERSION has bitmask 1044480, or 255 << 12 (0b11111111000000000000)
    #MAJ_VERSION has bitmask << 20
    return revVersion + (minVersion << 12) + (majVersion << 20)

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
