# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, Iterable, Union, Callable

import sympy

from cirq import value, protocols
from cirq.ops import (raw_types, common_gates, pauli_string as ps, pauli_gates,
                      op_tree, pauli_string_raw_types)


@value.value_equality(approximate=True)
class PauliStringPhasor(pauli_string_raw_types.PauliStringGateOperation):
    """An operation that phases a Pauli string."""

    def __init__(self,
                 pauli_string: ps.PauliString,
                 *,
                 exponent_neg: Union[int, float, sympy.Basic]=1,
                 exponent_pos: Union[int, float, sympy.Basic]=0) -> None:
        """Initializes the operation.

        At most one angle argument may be specified. If more are specified,
        the result is considered ambiguous and an error is thrown. If no angle
        argument is given, the default value of one half turn is used.

        Args:
            pauli_string: The PauliString to phase.
            exponent_neg: The amount that this operation should phase
                the -1 eigenstate of the observable specified by the given
                PauliString.
            exponent_pos: The amount that this operation should phase
                the +1 eigenstate of the observable specified by the given
                PauliString.
        """
        if pauli_string.coefficient == -1:
            pauli_string = -pauli_string
            exponent_pos, exponent_neg = exponent_neg, exponent_pos

        if pauli_string.coefficient != 1:
            raise ValueError(
                "Given PauliString doesn't have +1 and -1 eigenvalues. "
                "pauli_string.coefficient must be 1 or -1.")

        super().__init__(pauli_string)
        self.exponent_neg = value.canonicalize_half_turns(exponent_neg)
        self.exponent_pos = value.canonicalize_half_turns(exponent_pos)

    @property
    def exponent_relative(self) -> Union[int, float, sympy.Basic]:
        return value.canonicalize_half_turns(self.exponent_neg -
                                             self.exponent_pos)

    def _value_equality_values_(self):
        return (self.pauli_string, self.exponent_neg, self.exponent_pos,)

    def equal_up_to_global_phase(self, other):
        if isinstance(other, PauliStringPhasor):
            rel1 = self.exponent_relative
            rel2 = other.exponent_relative
            return rel1 == rel2 and self.pauli_string == other.pauli_string
        return False

    def map_qubits(self, qubit_map: Dict[raw_types.Qid, raw_types.Qid]):
        return PauliStringPhasor(
            self.pauli_string.map_qubits(qubit_map),
            exponent_neg=self.exponent_neg,
            exponent_pos=self.exponent_pos)

    def map_phases(self, phase_map: Callable[[float], float]):
        return PauliStringPhasor(
            self.pauli_string,
            exponent_neg=phase_map(self.exponent_neg),
            exponent_pos=phase_map(self.exponent_pos))

    def __pow__(self,
                exponent: Union[float, sympy.Symbol]) -> 'PauliStringPhasor':
        pn = protocols.mul(self.exponent_neg, exponent, None)
        pp = protocols.mul(self.exponent_pos, exponent, None)
        if pn is None or pp is None:
            return NotImplemented
        return PauliStringPhasor(
            self.pauli_string, exponent_neg=pn, exponent_pos=pp)

    def can_merge_with(self, op: 'PauliStringPhasor') -> bool:
        return self.pauli_string.equal_up_to_coefficient(op.pauli_string)

    def merged_with(self, op: 'PauliStringPhasor') -> 'PauliStringPhasor':
        if not self.can_merge_with(op):
            raise ValueError('Cannot merge operations: {}, {}'.format(self, op))
        pp = self.exponent_pos + op.exponent_pos
        pn = self.exponent_neg + op.exponent_neg
        return PauliStringPhasor(
            self.pauli_string, exponent_pos=pp, exponent_neg=pn)

    def _decompose_(self) -> op_tree.OP_TREE:
        if len(self.pauli_string) <= 0:
            return
        qubits = self.qubits
        any_qubit = qubits[0]
        to_z_ops = op_tree.freeze_op_tree(self.pauli_string.to_z_basis_ops())
        xor_decomp = tuple(xor_nonlocal_decompose(qubits, any_qubit))
        yield to_z_ops
        yield xor_decomp

        if self.exponent_neg:
            yield pauli_gates.Z(any_qubit)**self.exponent_neg
        if self.exponent_pos:
            yield pauli_gates.X(any_qubit)
            yield pauli_gates.Z(any_qubit)**self.exponent_pos
            yield pauli_gates.X(any_qubit)

        yield protocols.inverse(xor_decomp)
        yield protocols.inverse(to_z_ops)

    def _circuit_diagram_info_(self, args: protocols.CircuitDiagramInfoArgs
                              ) -> protocols.CircuitDiagramInfo:
        return self._pauli_string_diagram_info(
            args, exponent=self.exponent_relative)

    def _trace_distance_bound_(self) -> float:
        return protocols.trace_distance_bound(
            pauli_gates.Z**self.exponent_relative)

    def _is_parameterized_(self) -> bool:
        return (protocols.is_parameterized(self.exponent_neg) or
                protocols.is_parameterized(self.exponent_pos))

    def _resolve_parameters_(self, param_resolver) -> 'PauliStringPhasor':
        return PauliStringPhasor(
            self.pauli_string,
            exponent_neg=param_resolver.value_of(self.exponent_neg),
            exponent_pos=param_resolver.value_of(self.exponent_pos))

    def pass_operations_over(self,
                             ops: Iterable[raw_types.Operation],
                             after_to_before: bool=False
                            ) -> 'PauliStringPhasor':
        new_pauli_string = self.pauli_string.pass_operations_over(
            ops, after_to_before)
        pp = self.exponent_pos
        pn = self.exponent_neg
        return PauliStringPhasor(
            new_pauli_string, exponent_pos=pp, exponent_neg=pn)

    def __repr__(self):
        return ('cirq.PauliStringPhasor({!r}, '
                'exponent_neg={!r}, '
                'exponent_pos={!r})'.format(
                    self.pauli_string, self.exponent_neg, self.exponent_pos))

    def __str__(self):
        if self.exponent_pos == -self.exponent_neg:
            return 'exp({}iπ{}{})'.format('-' if self.exponent_pos < 0 else '',
                                          abs(self.exponent_pos),
                                          self.pauli_string)
        return '({})**{}'.format(self.pauli_string, self.exponent_relative)


def xor_nonlocal_decompose(qubits: Iterable[raw_types.Qid],
                           onto_qubit: raw_types.Qid
                          ) -> Iterable[raw_types.Operation]:
    """Decomposition ignores connectivity."""
    for qubit in qubits:
        if qubit != onto_qubit:
            yield common_gates.CNOT(qubit, onto_qubit)
