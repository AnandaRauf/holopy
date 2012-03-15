# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca
# W. Perry, Jerome Fung, and Ryan McGorty
#
# This file is part of Holopy.
#
# Holopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Holopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Holopy.  If not, see <http://www.gnu.org/licenses/>.

'''
Defines Sphere, a scattering primitive

.. moduleauthor:: Vinothan N. Manoharan <vnm@seas.harvard.edu>
'''

import numpy as np
from scatterpy.scatterer import Scatterer
from scatterpy.errors import ScattererDefinitionError
from .ellipsoid import SingleCenterScatterer

class Sphere(SingleCenterScatterer):
    '''
    Contains optical and geometrical properties of a sphere, a
    scattering primitive

    Attributes
    ----------
    n : float or complex
        Index of refraction of sphere
    r : float
        Radius of sphere
    x : float
        x-component of center
    y : float
        y-component of center
    z : float
        z-component of center
    center : 3-tuple, list or numpy array (optional)
        specifies coordinates of center of sphere

    '''

    def __init__(self, n = 1.59, r = 0.5e-6, x = 0.0, y = 0.0, z = 0.0, 
                 center = None):
        self.n = n
        self.r = r
        super(Sphere, self).__init__(x, y, z, center)

    parameter_names_list = ['n.real', 'n.imag', 'r', 'x', 'y', 'z']

    
    @property
    def parameter_list(self):
        """
        Return sphere parameters in order: n, r, x, y, z
        """
        return np.array([self.n.real, self.n.imag, self.r, self.x, self.y,
                         self.z])

    @classmethod
    def make_from_parameter_list(cls, params):
        n = params[0] + 1.0j * params[1]
        return cls(n, *params[2:])

