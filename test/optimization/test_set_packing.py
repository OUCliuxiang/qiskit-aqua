# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

""" Test Set Packing """

import json
from test.optimization import QiskitOptimizationTestCase
import numpy as np

from qiskit.optimization.ising import set_packing
from qiskit.optimization.ising.common import sample_most_likely
from qiskit.aqua import QuantumInstance, aqua_globals
from qiskit.aqua.algorithms import ExactEigensolver, VQE
from qiskit.aqua.components.optimizers import SPSA
from qiskit.aqua.components.variational_forms import RY


class TestSetPacking(QiskitOptimizationTestCase):
    """Cplex Ising tests."""

    def setUp(self):
        super().setUp()
        input_file = self.get_resource_path('sample.setpacking')
        with open(input_file) as file:
            self.list_of_subsets = json.load(file)
            self.qubit_op, _ = set_packing.get_operator(self.list_of_subsets)

    def _brute_force(self):
        # brute-force way: try every possible assignment!
        def bitfield(n, length):
            result = np.binary_repr(n, length)
            return [int(digit) for digit in result]  # [2:] to chop off the "0b" part

        subsets = len(self.list_of_subsets)
        maximum = 2**subsets
        max_v = -np.inf
        for i in range(maximum):
            cur = bitfield(i, subsets)
            cur_v = set_packing.check_disjoint(cur, self.list_of_subsets)
            if cur_v:
                if np.count_nonzero(cur) > max_v:
                    max_v = np.count_nonzero(cur)
        return max_v

    def test_set_packing(self):
        """ set packing test """
        algo = ExactEigensolver(self.qubit_op, k=1, aux_operators=[])
        result = algo.run()
        x = sample_most_likely(result['eigvecs'][0])
        ising_sol = set_packing.get_solution(x)
        np.testing.assert_array_equal(ising_sol, [0, 1, 1])
        oracle = self._brute_force()
        self.assertEqual(np.count_nonzero(ising_sol), oracle)

    def test_set_packing_vqe(self):
        """ set packing vqe test """
        try:
            # pylint: disable=import-outside-toplevel
            from qiskit import Aer
        except Exception as ex:  # pylint: disable=broad-except
            self.skipTest("Aer doesn't appear to be installed. Error: '{}'".format(str(ex)))
            return

        aqua_globals.random_seed = 50
        result = VQE(self.qubit_op,
                     RY(self.qubit_op.num_qubits, depth=5, entanglement='linear'),
                     SPSA(max_trials=200),
                     max_evals_grouped=2).run(
                         QuantumInstance(Aer.get_backend('qasm_simulator'),
                                         seed_simulator=aqua_globals.random_seed,
                                         seed_transpiler=aqua_globals.random_seed))
        x = sample_most_likely(result['eigvecs'][0])
        ising_sol = set_packing.get_solution(x)
        oracle = self._brute_force()
        self.assertEqual(np.count_nonzero(ising_sol), oracle)
