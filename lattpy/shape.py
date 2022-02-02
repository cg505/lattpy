# coding: utf-8
#
# This code is part of lattpy.
#
# Copyright (c) 2022, Dylan Jones
#
# This code is licensed under the MIT License. The copyright notice in the
# LICENSE file in the root directory and this permission notice shall
# be included in all copies or substantial portions of the Software.

"""Objects for representing the shape of a finite lattice."""

import numpy as np
import scipy.spatial
import matplotlib.pyplot as plt
import itertools
from abc import ABC, abstractmethod
from .plotting import draw_lines, draw_surfaces


class AbstractShape(ABC):
    """Abstract shape object."""

    def __init__(self, dim, pos=None):
        self.dim = dim
        self.pos = np.zeros(dim) if pos is None else np.array(pos)

    @abstractmethod
    def limits(self):
        pass

    @abstractmethod
    def contains(self, points):
        """Checks if the given points are contained in the shape."""
        pass

    @abstractmethod
    def plot(self, ax, color="k", lw=1.0, alpha=0.2, **kwargs):
        """Plots the contour of the shape."""
        pass

    def __repr__(self):
        return self.__class__.__name__


class Shape(AbstractShape):
    """General shape object."""

    def __init__(self, shape, pos=None):
        if not hasattr(shape, "__len__"):
            shape = [shape]
        super().__init__(len(shape), pos)
        self.shape = np.array(shape)

    def limits(self):
        lims = self.pos + np.array([np.zeros(self.dim), self.shape])
        return lims.T

    def contains(self, points):
        mask = np.logical_and(self.pos <= points, points <= self.pos + self.shape)
        return np.all(mask, axis=1)

    def plot(self, ax, color="k", lw=1.0, alpha=0.2, **kwargs):
        pos = self.pos
        size = self.shape
        if self.dim == 2:
            vertices = pos + np.array([
                [0, 0], [size[0], 0], [size[0], size[1]], [0, size[1]]
            ])
            edges = np.array([[0, 1], [1, 2], [2, 3], [3, 0]])

            segments = vertices[edges]
            lines = draw_lines(ax, segments, color=color, lw=lw)

            surf = [0, 1, 2, 3, 0]
            segments = vertices[surf]
            surfaces = ax.fill(*segments.T, color="k", alpha=alpha)

        elif self.dim == 3:
            # Build vertices
            vertices = pos + np.array(list(itertools.product(*self.limits())))
            # Edge indices
            edges = np.array([
                [0, 2], [2, 3], [3, 1], [1, 0],
                [4, 6], [6, 7], [7, 5], [5, 4],
                [0, 4], [2, 6], [3, 7], [1, 5]
            ])
            segments = vertices[edges]
            lines = draw_lines(ax, segments, color=color, lw=lw)

            surfaces = None
            if alpha > 0:
                # Surface indices
                surfs = np.array([
                    [0, 2, 3, 1],
                    [4, 6, 7, 5],
                    [0, 4, 6, 2],
                    [2, 6, 7, 3],
                    [3, 7, 5, 1],
                    [1, 5, 4, 0]
                ])
                segments = vertices[surfs]
                surfaces = draw_surfaces(ax, segments, color=color, alpha=alpha)
        else:
            raise NotImplementedError("Can't plot shape in D>3!")
        return lines, surfaces


class Circle(AbstractShape):
    """Circle shape."""

    def __init__(self, pos, radius):
        super().__init__(len(pos), pos)
        self.radius = radius

    def limits(self):
        rad = np.full(self.dim, self.radius)
        lims = self.pos + np.array([-rad, +rad])
        return lims.T

    def contains(self, points):
        return np.sqrt(np.sum(np.square(points - self.pos), axis=1)) <= self.radius

    def plot(self, ax, color="k", lw=1.0, alpha=0.2, **kwargs):
        xy = tuple(self.pos)
        line = plt.Circle(xy, self.radius, lw=lw, color=color, fill=False)
        ax.add_artist(line)
        surf = plt.Circle(xy, self.radius, lw=0, color=color, alpha=alpha, fill=True)
        ax.add_artist(surf)
        return line, surf


class Donut(AbstractShape):
    """Circle shape with cut-out in the middle."""

    def __init__(self, pos, radius_outer, radius_inner):
        super().__init__(len(pos), pos)
        self.radii = np.array([radius_inner, radius_outer])

    def limits(self):
        rad = np.full(self.dim, self.radii[1])
        lims = self.pos + np.array([-rad, +rad])
        return lims.T

    def contains(self, points):
        dists = np.sqrt(np.sum(np.square(points - self.pos), axis=1))
        return np.logical_and(self.radii[0] <= dists, dists <= self.radii[1])

    def plot(self, ax, color="k", lw=1.0, alpha=0.2, **kwargs):
        n = 100

        theta = np.linspace(0, 2 * np.pi, n, endpoint=True)
        xs = np.outer(self.radii, np.cos(theta))
        ys = np.outer(self.radii, np.sin(theta))
        # in order to have a closed area, the circles
        # should be traversed in opposite directions
        xs[1, :] = xs[1, ::-1]
        ys[1, :] = ys[1, ::-1]

        line1 = ax.plot(xs[0], ys[0], color=color, lw=lw)[0]
        line2 = ax.plot(xs[1], ys[1], color=color, lw=lw)[0]
        surf = ax.fill(np.ravel(xs), np.ravel(ys), fc=color, alpha=alpha, ec=None)

        return [line1, line2], surf


# noinspection PyUnresolvedReferences
class ConvexHull(AbstractShape):
    """Shape defined by convex hull of arbitrary points."""

    def __init__(self, points):
        dim = len(points[0])
        super().__init__(dim)
        self.hull = scipy.spatial.ConvexHull(points)

    def limits(self):
        points = self.hull.points
        return np.array([np.min(points, axis=0), np.max(points, axis=0)]).T

    def contains(self, points, tol=1e-10):
        return np.all(np.add(np.dot(points, self.hull.equations[:, :-1].T),
                             self.hull.equations[:, -1]) <= tol, axis=1)

    def plot(self, ax, color="k", lw=1.0, alpha=0.2, **kwargs):

        if self.dim == 2:
            segments = self.hull.points[self.hull.simplices]
            lines = draw_lines(ax, segments, color=color, lw=lw)
            # segments = self.hull.points[surf]
            segments = self.hull.points[self.hull.vertices]
            surfaces = ax.fill(*segments.T, fc=color, alpha=alpha, ec=None)

        elif self.dim == 3:

            segments = np.array(
                [self.hull.points[np.append(i, i[0])] for i in self.hull.simplices]
            )
            lines = draw_lines(ax, segments, color=color, lw=lw)

            surfaces = np.array([self.hull.points[i] for i in self.hull.simplices])
            draw_surfaces(ax, surfaces, color=color, alpha=alpha)
        else:
            raise NotImplementedError("Can't plot shape in D>3!")

        return lines, surfaces