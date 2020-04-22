# coding: utf-8
"""
Created on 08 Apr 2020
author: Dylan Jones
"""
import pickle
import itertools
import numpy as np
from .utils import vrange, distance, cell_size, cell_volume, ConfigurationError
from .plotting import LatticePlot


class Atom:

    COUNTER = itertools.count()

    def __init__(self, name=None, color=None, size=10, **kwargs):
        idx = next(self.COUNTER)
        name = name or str(idx)
        self.name = name
        self.col = color
        self.size = size
        self.kwargs = kwargs

    def __getitem__(self, item):
        return self.kwargs[item]

    def label(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Atom):
            return self.name == other.name
        else:
            return self.name == other

    def __repr__(self):
        return f"Atom({self.name}, {self.col}, {self.size})"


class BravaisLattice:

    DIST_DECIMALS = 5
    MIN_DISTS = 3

    def __init__(self, vectors):
        vectors = np.atleast_2d(vectors).T
        dim = len(vectors)

        # Lattice data
        self.dim = dim
        self.vectors = vectors
        self._vectors_inv = np.linalg.inv(self.vectors)
        self.cell_size = cell_size(vectors)
        self.cell_volume = cell_volume(vectors)
        self.origin = np.zeros(self.dim)

        # Atom data
        self.n_base = 0
        self.atoms = list()
        self.atom_positions = list()
        self.n_dist = 0
        self.distances = list()
        self._base_neighbors = list()

    @classmethod
    def chain(cls, a=1.0):
        return cls(a)

    @classmethod
    def square(cls, a=1.0):
        return cls(a * np.eye(2))

    @classmethod
    def rectangular(cls, a1=1.0, a2=1.0):
        return cls(np.array([[a1, 0], [0, a2]]))

    @classmethod
    def hexagonal(cls, a=1.0):
        # vectors = a * np.array([[np.sqrt(3), np.sqrt(3) / 2], [0, 3 / 2]])
        vectors = a/2 * np.array([[3, np.sqrt(3)], [3, -np.sqrt(3)]])
        return cls(vectors)

    @classmethod
    def sc(cls, a=1.0):
        return cls(a * np.eye(3))

    @classmethod
    def fcc(cls, a=1.0):
        vectors = a/2 * np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1]])
        return cls(vectors)

    @classmethod
    def bcc(cls, a=1.0):
        vectors = a/2 * np.array([[1, 1, 1], [1, -1, 1], [-1, 1, 1]]).T
        return cls(vectors)

    def copy(self):
        """ Creates a (deep) copy of the lattice instance"""
        latt = self.__class__(self.vectors.copy().T)
        if self.n_base:
            latt.n_base = self.n_base
            latt.atoms = self.atoms.copy()
            latt.atom_positions = self.atom_positions.copy()
            latt.distances = self.distances.copy()
            latt._base_neighbors = self._base_neighbors.copy()
        return latt

    def save(self, file='lattice.pkl'):
        with open(file, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, file='lattice.pkl'):
        with open(file, "rb") as f:
            latt = pickle.load(f)
        return latt

    # =========================================================================

    def reciprocal_vectors(self):
        """ Computes the reciprocal basis vectors of the bravais lattice.

        Returns
        -------
        v_rec: np.ndarray
        """
        # Convert basis vectors of the bravais lattice to 3D
        vecs = np.eye(3)
        vecs[:self.dim, :self.dim] = self.vectors
        a1, a2, a3 = vecs
        # Compute reziprocal vectors
        factor = 2 * np.pi / self.cell_volume
        b1 = factor * np.cross(a2, a3)
        b2 = factor * np.cross(a3, a1)
        b3 = factor * np.cross(a1, a2)
        rvecs = np.asarray([b1, b2, b3])
        # Return the needed vectors for the input dimension
        return rvecs[:self.dim, :self.dim]

    def reciprocal_lattice(self):
        """ Creates the lattice in reciprocal space """
        latt = self.__class__(self.reciprocal_vectors().T)
        if self.n_base:
            latt.n_base = self.n_base
            latt.atoms = self.atoms.copy()
            latt.atom_positions = self.atom_positions.copy()
            latt.calculate_distances(self.n_dist)
        return latt

    def translate(self, nvec, r=0):
        """ Translates the given postion vector r by the translation vector n.

        Parameters
        ----------
        nvec: (N) array_like
            Translation vector in the lattice basis.
        r: (N) array_like, optional
            The position in real-space. If no vector is passed only the translation is returned.

        Returns
        -------
        r_trans: (N) array_like
        """
        return r + (self.vectors @ nvec)

    def itranslate(self, v):
        """ Returns the lattice index and cell position leading to the given position in real space.

        Parameters
        ----------
        v: (N) array_like
            Position vector in real-space.

        Returns
        -------
        nvec: (N) array_like
            Translation vector in the lattice basis.
        r: (N) array_like, optional
            The position in real-space.
        """
        itrans = self._vectors_inv @ v
        nvec = np.floor(itrans)
        r = v - self.translate(nvec)
        return nvec, r

    def estimate_index(self, pos):
        """ Returns the nearest matching lattice index (n, alpha) for global position.

        Parameters
        ----------
        pos: array_like
            global site position.

        Returns
        -------
        n: np.ndarray
            estimated translation vector n
        """
        pos = np.asarray(pos)
        n = np.asarray(np.round(self._vectors_inv @ pos, decimals=0), dtype="int")
        return n

    def get_position(self, n=None, alpha=0):
        """ Returns the position for a given translation vector and site index

        The position is defined by

        Parameters
        ----------
        n: (N) array_like
            translation vector.
        alpha: int, optional
            site index, default is 0.
        Returns
        -------
        pos: (N) np.ndarray
        """
        r = self.atom_positions[alpha]
        if n is None:
            return r
        return r + (self.vectors @ n)  # self.translate(n, r)

    def translate_cell(self, n):
        """ Translates all sites of the unit cell

        Parameters
        ----------
        n: np.ndarray
            translation vector.

        Yields
        -------
        pos: np.ndarray
            positions of the sites in the translated unit cell
        """
        for alpha in range(self.n_base):
            yield self.get_position(n, alpha)

    def distance(self, idx0, idx1):
        """ Calculate distance between two sites

        Parameters
        ----------
        idx0: tuple
            lattice vector (n, alpha) of first site
        idx1: tuple
            lattice index (n, alpha) of second site

        Returns
        -------
        distance: float
        """
        r1 = self.get_position(*idx0)
        r2 = self.get_position(*idx1)
        return distance(r1, r2)

    def _neighbour_range(self, n=None, cell_range=1):
        """ Get all neighbouring translation vectors of a given cell position

        Parameters
        ----------
        n: array_like, optional
            translation vector of unit cell, the default is the origin.
        cell_range: int, optional
            Range of neighbours, the default is 1.
        Returns
        -------
        trans_vectors: list
        """
        n = np.zeros(self.dim) if n is None else n
        offset = cell_range + 2
        ranges = [np.arange(n[d] - offset, n[d] + offset + 1) for d in range(self.dim)]
        n_vecs = vrange(ranges)
        for n in n_vecs:
            for alpha in range(self.n_base):
                yield (n, alpha)

    def calculate_neighbours(self, n=None, alpha=0, dist_idx=0, array=False):
        """ Find all neighbours of given site and return the lattice indices.

        Parameters
        ----------
        n: array_like, optional
            translation vector of site, the default is the origin.
        alpha: int, optional
            site index, default is 0.
        dist_idx: int, default
            index of distance to neighbours, defauzlt is 0 (nearest neighbours).
        array: bool, optional
            if true, return lattice index (n, alpha) as single array.
            The default is False.

        Returns
        -------
        indices: list
        """
        n = np.zeros(self.dim) if n is None else n
        idx = n, alpha
        dist = self.distances[dist_idx]
        indices = list()
        for idx1 in self._neighbour_range(n, dist_idx):
            # if np.isclose(self.distance(idx, idx1), dist, atol=1e-5):
            if np.round(abs(self.distance(idx, idx1) - dist), decimals=self.DIST_DECIMALS) == 0.0:
                if array:
                    idx1 = [*idx1[0], idx1[1]]
                indices.append(idx1)
        return indices

    def calculate_distances(self, num_dist=1):
        """ Calculates the ´n´ lowest distances between sites in the lattice and the neighbours of the cell.

        Checks distances between all sites of the bravais lattice and saves n lowest values.
        The neighbor lattice-indices of the unit-cell are also stored for later use.
        This speeds up many calculations like finding nearest neighbours.

        Raises
        ------
        ConfigurationError
            Raised if no atoms where added to the lattice.
            The atoms in the unit cell are needed for computing the distances in the lattice.

        Parameters
        ----------
        num_dist: int, optional
            Number of distances of lattice structure to calculate. If 'None' the number of atoms is used.
            The default is 1 (nearest neighbours).
        """
        if len(self.atoms) == 0:
            raise ConfigurationError("No atoms found in the lattice!", "Use 'add_atom' to add an 'Atom'-object")
        if num_dist is None:
            num_dist = len(self.atoms)
        # Calculate n lowest distances of lattice structure
        n = num_dist + 1
        n = max(n, self.MIN_DISTS)
        n_vecs = vrange(self.dim * [np.arange(-n, n)])
        r_vecs = list()
        for nvec in n_vecs:
            for alpha in range(self.n_base):
                r_vecs.append(self.get_position(nvec, alpha))
        pairs = list(itertools.product(r_vecs, self.atom_positions))
        distances = list(set(np.round([distance(r1, r2) for r1, r2 in pairs], decimals=self.DIST_DECIMALS)))
        distances.sort()
        distances.remove(0.0)
        self.distances = distances[0:n - 1]
        self.n_dist = num_dist

        # Calculate cell-neighbors.
        neighbours = list()
        for alpha in range(self.n_base):
            site_neighbours = list()
            for i_dist in range(len(self.distances)):
                # Get neighbour indices of site for distance level
                site_neighbours.append(self.calculate_neighbours(alpha=alpha, dist_idx=i_dist, array=True))
            neighbours.append(site_neighbours)
        self._base_neighbors = neighbours

    def add_atom(self, pos=None, atom=None, neighbours=0, **kwargs):
        """ Adds a site to the basis of the lattice unit-cell.

        Parameters
        ----------
        pos: (N) array_like, optional
            Position of site in the unit-cell. The default is the origin of the cell.
            The size of the array has to match the dimension of the lattice.
        atom: str or Atom
            Identifier of the site. If a string is passed, a new Atom instance is created.
        neighbours: int, optional
            The number of neighbor distance to calculate. If the number is ´0´ the distances have
            to be calculated manually after configuring the lattice basis.
        **kwargs
            Keyword arguments for ´Atom´ constructor. Only used if a new Atom instance is created.
        """
        if pos is None:
            pos = np.zeros(self.vectors.shape[0])
        else:
            pos = np.asarray(pos)
        if any(np.all(pos == x) for x in self.atom_positions):
            raise ValueError(f"Position {pos} already occupied!")
        if isinstance(atom, Atom):
            atom = atom
        else:
            atom = Atom(atom, **kwargs)
        self.atoms.append(atom)
        self.atom_positions.append(np.asarray(pos))
        self.n_base = len(self.atom_positions)
        if neighbours:
            self.calculate_distances(neighbours)
        return atom

    def get_neighbours(self, idx, dist_idx=0):
        """ Returns the neighours of a given site by transforming stored neighbour indices.

        Raises
        ------
        ConfigurationError
            Raised if the lattice distances haven't been computed.

        Parameters
        ----------
        idx: tuple
            lattice vector (n, alpha) of first site
        dist_idx: int, default
            index of distance to neighbours, defauzlt is 0 (nearest neighbours).
        """
        if not self._base_neighbors:
            hint = "Use the 'neighbours' keyword of 'add_atom' or call 'calculate_distances' after adding the atoms!"
            raise ConfigurationError("Base neighbours not configured.", hint)
        n, alpha = np.array(idx[:-1]), idx[-1]
        transformed = list()
        for idx in self._base_neighbors[alpha][dist_idx]:
            idx_t = idx.copy()
            idx_t[:-1] += n
            transformed.append(idx_t)
        return transformed

    def get_neighbour_vectors(self, alpha=0, dist_idx=0, include_zero=False):
        """ Returns the neighours of a given site by transforming stored neighbour indices.

        Raises
        ------
        ConfigurationError
            Raised if the lattice distances haven't been computed.

        Parameters
        ----------
        alpha: int, optional
            Index of the base atom. The default is the first atom in the unit cell.
        dist_idx: int, default
            Index of distance to neighbours, defauzlt is 0 (nearest neighbours).
        include_zero: bool, optional
            Flag if zero-vector is included in result. The default is False.
        """
        if not self._base_neighbors:
            hint = "Use the 'neighbours' keyword of 'add_atom' or call 'calculate_distances' after adding the atoms!"
            raise ConfigurationError("Base neighbours not configured.", hint)
        pos0 = self.atom_positions[alpha]
        vectors = list()
        if include_zero:
            vectors.append(np.zeros(self.dim))
        for idx in self._base_neighbors[alpha][dist_idx]:
            pos1 = self.get_position(idx[:-1], idx[-1])
            vectors.append(pos1 - pos0)
        return vectors

    # =========================================================================

    def plot_cell(self, show=True, reziprocal=False, color='k', lw=2, legend=True, margins=0.25,
                  show_atoms=True, plot=None):

        plot = plot or LatticePlot(dim3=self.dim == 3)
        plot.set_equal_aspect()

        # Plot vectors
        if reziprocal:
            vecs = self.reciprocal_vectors() / (2 * np.pi)
            s = r'2 \pi \cdot '
            labels = f'${s}k_x$', f'${s}k_y$', f'${s}k_z$' if self.dim == 3 else None
        else:
            vecs = self.vectors
            labels = 'x', 'y', 'z' if self.dim == 3 else None
        plot.draw_vectors(vecs, color=color, lw=lw)
        if self.dim == 2:
            v1, v2 = vecs
            plot.draw_vector(v1, pos=v2, color=color, ls='--', lw=1)
            plot.draw_vector(v2, pos=v1, color=color, ls='--', lw=1)

        # Plot atoms in the unit cell
        if show_atoms and self.n_base:
            atom_pos = dict()
            for atom, pos in zip(self.atoms, self.atom_positions):
                if atom.name in atom_pos.keys():
                    atom_pos[atom].append(pos)
                else:
                    atom_pos[atom] = [pos]

            for atom, positions in atom_pos.items():
                plot.draw_sites(atom, positions)

        plot.set_margins(margins)
        if legend:
            plot.legend()
        plot.setup()
        plot.set_labels(*labels)
        plot.show(show)
        return plot