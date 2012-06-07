# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca W. Perry,
# Jerome Fung, and Ryan McGorty
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
"""
Routines for fitting a hologram to an exact solution

.. moduleauthor:: Thomas G. Dimiduk <tdimiduk@physics.harvard.edu>
.. moduleauthor:: Jerome Fung <jfung@physics.harvard.edu>
.. moduleauthor:: Rebecca W. Perry <rperry@seas.harvard.edu>

"""
from __future__ import division

import inspect
import time

import numpy as np

import scatterpy
from holopy.utility.helpers import _ensure_pair
from holopy.io.yaml_io import Serializable

def fit(model, data, algorithm='nmpfit'):
    time_start = time.time()

    minimizer = Minimizer(algorithm)
    fitted_pars, converged, minimizer_info =  minimizer.minimize(model.parameters, model.cost_func(data), model.selection)
    
    fitted_scatterer = model.make_scatterer_from_par_values(fitted_pars)
    fitted_alpha = model.alpha(fitted_pars)
    theory = model.theory(data.optics, data.shape)
    fitted_holo = theory.calc_holo(fitted_scatterer, fitted_alpha)
    
    chisq = float((((fitted_holo-data))**2).sum() / fitted_holo.size)
    rsq = float(1 - ((data - fitted_holo)**2).sum()/((data - data.mean())**2).sum())

    time_stop = time.time()

    return FitResult(fitted_scatterer, fitted_alpha, chisq, rsq, converged,
                     time_stop - time_start, model, minimizer, minimizer_info)

class FitResult(Serializable):
    def __init__(self, scatterer, alpha, chisq, rsq, converged, time, model,
                 minimizer, minimization_details):
        self.scatterer = scatterer
        self.alpha = alpha
        self.chisq = chisq
        self.rsq = rsq
        self.converged = converged
        self.time = time
        self.model = model
        self.minimizer = minimizer
        self.minimization_details = minimization_details
        
    def __repr__(self):
        return ("{s.__class__.__name__}(scatterer={s.scatterer}, "
                "alpha={s.alpha}, chisq={s.chisq}, rsq={s.rsq}, "
                "converged={s.converged}, time={s.time}, model={s.model}, "
                "minimizer={s.minimizer}, "
                "minimization_details={s.minimization_details})".format(s=self))  #pragma: no cover

class Model(Serializable):
    """
    Representation of a model to fit to data

    Parameters
    ----------
    parameters: list(:class:`Parameter`)
        The parameters which can be varied in this model
    theory: :class:`scatterpy.theory.ScatteringTheory`
        The theory that should be used to compute holograms
    scatterer: :class:`scatterpy.scatterer.AbstractScatterer`
        Scatterer to compute holograms of, ignored if make_scatterer is given
    make_scatterer: function(par_values) -> :class:`scatterpy.scatterer.AbstractScatterer`
        Function that returns a scatterer given parameters
    selection : array of integers (optional)
        An array with 1's in the locations of pixels where you
        want to calculate the field, defaults to 1 at all pixels

    Notes
    -----
    Any arbitrary parameterization can be used by simply specifying a
    make_scatterer function which can turn the parameters into a scatterer
    
    """
    def __init__(self, parameters, theory, scatterer=None, make_scatterer=None, selection=None):
        self.parameters = parameters
        self.theory = theory
        self.scatterer=scatterer
        self.make_scatterer = make_scatterer
        self.selection = selection

    def make_scatterer_from_par_values(self, par_values):
        all_pars = {}
        for i, p in enumerate(self.parameters):
            all_pars[p.name] = p.unscale(par_values[i])
        for_scatterer = {}
        for arg in inspect.getargspec(self.make_scatterer).args:
            for_scatterer[arg] = all_pars[arg] 
        return self.make_scatterer(**for_scatterer)
        
    # TODO: add a make_optics function so that you can have parameters
    # affect optics things (fit to beam divergence, lens abberations, ...)

    def compare(self, calc, data, selection = None):
        if selection == None:
                selection = np.ones(data.shape,dtype='int')
        return (calc*selection-data*selection).ravel()
    
    def alpha(self, par_values):
        for i, par in enumerate(self.parameters):
            if par.name == 'alpha':
                return par.unscale(par_values[i])
        return None
    
    def cost_func(self, data, selection = None): 
        if not isinstance(self.theory, scatterpy.theory.ScatteringTheory):
            theory = self.theory(data.optics, data.shape)
        else:
            theory = self.theory
            
        def cost(par_values, selection=None):
            if selection == None:
                selection = np.ones(data.shape,dtype='int')
            calc = theory.calc_holo(self.make_scatterer_from_par_values(par_values),
                             self.alpha(par_values), selection)
            return self.compare(calc, data, selection)
        return cost

    # TODO: make a user overridabel cost function that gets physical parameters
    # so that the unscaling happens only in one place (and as close to the
    # minimizer as possible).  

    # TODO: Allow a layer on top of theory to do things like moving sphere

class InvalidParameterSpecification(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
    
class Minimizer(object):
    def __init__(self, algorithm='nmpfit'):
        self.algorithm = algorithm

    def minimize(self, parameters, cost_func, selection=None):
        if self.algorithm == 'nmpfit':
            from holopy.third_party import nmpfit
            nmp_pars = []
            for i, par in enumerate(parameters):

                def resid_wrapper(p, fjac=None):
                    status = 0                    
                    return [status, cost_func(p, selection)]
    
                d = {'parname': par.name}
                if par.limit is not None:
                    d['limited'] = [par.scale(l) is not None for l in par.limit]
                    d['limits'] = par.scale(np.array(par.limit))
                else:
                    d['limited'] = [False, False]    
                if par.guess is not None:
                    d['value'] = par.scale(par.guess)
                else:
                    raise InvalidParameterSpecification("nmpfit requires an "
                                                        "initial guess for all "
                                                        "parameters")
                nmp_pars.append(d)
            fitresult = nmpfit.mpfit(resid_wrapper, parinfo=nmp_pars)
            converged = fitresult.status < 4
            return fitresult.params, converged, fitresult
    def __repr__(self):
        return "Minimizer(algorithm='{0}')".format(self.algorithm)

        

class Parameter(object):
    def __init__(self, name = None, guess = None, limit = None, misc = None):
        self.name = name
        self.guess = guess
        self.limit = limit
        self.misc = misc
        if guess is not None:
            self.scale_factor = guess
        elif limit is not None:
            self.scale_factor = np.sqrt(limit[0]*limit[1])
        else:
            raise InvalidParameterSpecification("In order to specify a parameter "
                                                "you must provide at least an "
                                                "initial guess or limit") 

    def scale(self, physical):
        """
        Scales parameters to approximately unity

        Parameters
        ----------
        physical: np.array(dtype=float)

        Returns
        -------
        scaled: np.array(dtype=float)
        """

        return physical / self.scale_factor

    def unscale(self, scaled):
        """
        Inverts scale's transformation

        Parameters
        ----------
        scaled: np.array(dtype=float)

        Returns
        -------
        physical: np.array(dtype=float)
        """
        return scaled * self.scale_factor

    def __repr__(self):
        args = []
        if self.guess is not None:
            args.append('guess={0}'.format(self.guess))
        if self.limit is not None:
            args.append('limit={0}'.format(self.limit))
        if self.misc is not None:
            args.append('misc={0}'.format(self.misc))
        return "Parameter(name='{0}', {1})".format(self.name, ', '.join(args))
        

class RigidSphereCluster(Model):
    def __init__(self, reference_scatterer, alpha, beta, gamma, x, y, z):
        self.parameters = [alpha, beta, gamma, x, y, z]
        self.theory = scatterpy.theory.Multisphere
        self.reference_scatterer = reference_scatterer

    def make_scatterer(self, par_values):
        unscaled = []
        for i, val in enumerate(par_values):
            unscaled.append(self.parameters[i].unscale(val))
        return self.reference_scatterer.rotated(unscaled[:3]).translated(unscaled[3:6])


# Archiving:
# Model (parameters, theory, cost function, 

################################################################
# Fitseries engine

# default
# Load, normalize, background
# fit
# archive

# provide customization hooks
# prefit - user supplied
# fit
# postfit - user supplied
# archive

# archive to a unique directory name (probably from time and hostname)