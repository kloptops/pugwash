# -*- coding: utf-8 -*-

# Copyright (C) 2017 Carlos Pérez Ramil

# This file is part of Thumbstick Deadzones project.

# The Thumbstick Deadzones project is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# The Thumbstick Deadzones project is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with the Thumbstick Deadzones project.
# If not, see <http://www.gnu.org/licenses/>.

## Code from: https://github.com/Minimuino/thumbstick-deadzones

import math

# Vector class
class Vector2:
    __slots__ = (
        'x',
        'y',
        )

    def __init__(self, x, y=None):
        if isinstance(x, (list, tuple, Vector2)):
            if len(x) != 2:
                raise ValueError()

            if not isinstance(x[0], (int, float)):
                raise ValueError(f"{x[0]} is not an int or float")

            if not isinstance(x[1], (int, float)):
                raise ValueError(f"{x[1]} is not an int or float")

            self.x = x[0]
            self.y = x[1]

        elif isinstance(x, (int, float)) and isinstance(y, (int, float)):
            self.x = x
            self.y = y

        else:
            raise ValueError(f"bad input {x} and {y}")

    def __len__(self):
        return 2

    def __getitem__(self, index):
        return (self.x, self.y)[index]

    def __setitem__(self, index, value):
        if not isinstance(value, (int, float)):
            raise ValueError("expected int or float")

        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        else:
            raise IndexError("vector assignment index out of range")

    def magnitude(self):
        return math.sqrt(pow(self.x, 2.0) + pow(self.y, 2.0))

    def to_zero(self):
        self.x = 0
        self.y = 0
        return self

# UTILS
def map_range(value, old_min, old_max, new_min, new_max):
    return (new_min + (new_max - new_min) * (value - old_min) / (old_max - old_min))

def get_sign(value):
    if value < 0:
        return -1

    return 1

# DEADZONE TYPES
def dz_axial(stick_input, deadzone):
    result = Vector2(stick_input)
    if (abs(result[0]) < deadzone)
        result.x = 0

    if (abs(result[1]) < deadzone)
        result.y = 0

    return result


def dz_radial(stick_input, deadzone):
    result = Vector2(stick_input)
    input_magnitude = result.magnitude()

    if input_magnitude < deadzone:
        return result.to_zero()

    return result


def dz_scaled_radial(stick_input, deadzone):
    result = Vector2(stick_input)

    input_magnitude = result.magnitude()
    if input_magnitude < deadzone:
        return result.to_zero()

    range_scale = map_range(input_magnitude, deadzone, 1.0, 0.0, 1.0);
    result.x /= input_magnitude
    result.y /= input_magnitude
    result.x *= range_scale
    result.y *= range_scale
    return result


def dz_sloped_axial(stick_input, deadzone):
    result = Vector2(stick_input)

    deadzone_x = deadzone * abs(result.y)
    deadzone_y = deadzone * abs(result.x)
    if (abs(result.x) < deadzone_x)
        result.x = 0

    if (abs(result.y) < deadzone_y)
        result.y = 0

    return result


def dz_sloped_scaled_axial(stick_input, deadzone):
    result = Vector2(stick_input)
    deadzone_x = deadzone * abs(result.y)
    deadzone_y = deadzone * abs(result.x)

    sign = Vector2(get_sign(result.x), get_sign(result.y))

    if (abs(result.x) > deadzone_x)
        result.x = sign.x * map_range(abs(result.x), deadzone_x, 1, 0, 1)

    if (abs(result.y) > deadzone_y)
        result.y = sign.y * map_range(abs(result.y), deadzone_y, 1, 0, 1)

    return result


def dz_hybrid(stick_input, deadzone):
    result = Vector2(stick_input)

    input_magnitude = result.magnitude()
    if input_magnitude < deadzone:
        return result.to_zero()

    partial_output = dz_scaled_radial(result, deadzone)

    final_output = dz_sloped_scaled_axial(partial_output, deadzone)

    return final_output
