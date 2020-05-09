# coding: utf-8
"""
Created on 22 Apr 2020
author: Dylan Jones
"""
import numpy as np
from numpy.testing import assert_array_equal, assert_array_almost_equal
from lattpy.base import Atom, BravaisLattice

chain = BravaisLattice.chain(a=1.0)
square = BravaisLattice.square(a=1.0)
rect = BravaisLattice.rectangular(a1=2.0, a2=1.0)
hexagonal = BravaisLattice.hexagonal(a=1)


def test_reciprocal_vectors():
    # Chain
    expected = np.array([[2 * np.pi]])
    actual = chain.reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Square
    expected = 2 * np.pi * np.eye(2)
    actual = square.reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Rectangular
    expected = np.pi * np.array([[1, 0], [0, 2]])
    actual = rect.reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Hexagonal
    expected = np.array([[-2.0943951, -2.0943951],
                         [-3.62759873, 3.62759873]])
    actual = hexagonal.reciprocal_vectors()
    assert_array_almost_equal(expected, actual)


def test_reciprocal_vectors_double():
    # Chain
    expected = chain.get_vectors()
    actual = chain.reciprocal_lattice().reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Square
    expected = square.get_vectors()
    actual = square.reciprocal_lattice().reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Rectangular
    expected = rect.get_vectors()
    actual = rect.reciprocal_lattice().reciprocal_vectors()
    assert_array_equal(expected, actual)

    # Hexagonal
    expected = hexagonal.get_vectors()
    actual = hexagonal.reciprocal_lattice().reciprocal_vectors()
    assert_array_equal(expected, actual)


def test_translate():
    # Square lattice
    expected = [2.0, 0.0]
    actual = square.translate([2, 0], [0.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0.0, 2.0]
    actual = square.translate([0, 2], [0.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [1.0, 2.0]
    actual = square.translate([1, 2], [0.0, 0.0])
    assert_array_equal(expected, actual)

    # Rectangular lattice
    expected = [4.0, 0.0]
    actual = rect.translate([2, 0], [0.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0.0, 2.0]
    actual = rect.translate([0, 2], [0.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [2.0, 2.0]
    actual = rect.translate([1, 2], [0.0, 0.0])
    assert_array_equal(expected, actual)


def test_itranslate():
    # Square lattice
    expected = [2, 0], [0.0, 0.0]
    actual = square.itranslate([2.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0, 2], [0.0, 0.0]
    actual = square.itranslate([0.0, 2.0])
    assert_array_equal(expected, actual)

    expected = [1, 2], [0.0, 0.0]
    actual = square.itranslate([1.0, 2.0])
    assert_array_equal(expected, actual)

    # Rectangular lattice
    expected = [1, 0], [0.0, 0.0]
    actual = rect.itranslate([2.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0, 2], [0.0, 0.0]
    actual = rect.itranslate([0.0, 2.0])
    assert_array_equal(expected, actual)

    expected = [1, 1], [0.0, 0.0]
    actual = rect.itranslate([2.0, 1.0])
    assert_array_equal(expected, actual)


def test_estimate_index():
    # Square lattice
    expected = [2, 0]
    actual = square.estimate_index([2.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0, 2]
    actual = square.estimate_index([0.0, 2.0])
    assert_array_equal(expected, actual)

    expected = [1, 2]
    actual = square.estimate_index([1.0, 2.0])
    assert_array_equal(expected, actual)

    # Rectangular lattice
    expected = [1, 0]
    actual = rect.estimate_index([2.0, 0.0])
    assert_array_equal(expected, actual)

    expected = [0, 2]
    actual = rect.estimate_index([0.0, 2.0])
    assert_array_equal(expected, actual)

    expected = [1, 1]
    actual = rect.estimate_index([2.0, 1.0])
    assert_array_equal(expected, actual)


def test_get_position():
    pass
