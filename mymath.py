import math


def acosd(x):
    return math.degrees(math.acos(x))


def asind(x):
    return math.degrees(math.asin(x))


def atan2d(y, x):
    return math.degrees(math.atan2(y, x))


def atand(x):
    return math.degrees(math.atan(x))


def sind(x):
    return math.sin(math.radians(x))


def cosd(x):
    return math.cos(math.radians(x))


def tand(x):
    return math.tan(math.radians(x))


def alpha(l1, l2, r):
    return acosd((l1 ** 2 + r ** 2 - l2 ** 2) / (2 * l1 * r))
