# Copyright 2017 Google LLC
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

"""Gates that can be directly described to the API, without decomposition."""

import abc

from cirq.apis.google.v1 import operations_pb2
from cirq.ops import gate_features, raw_types


class NativeGate(raw_types.Gate, metaclass=abc.ABCMeta):
    """A gate with a known mechanism for encoding into API protos."""

    @abc.abstractmethod
    def to_proto(self, *qubits) -> operations_pb2.Operation:
        raise NotImplementedError()


class MeasurementGate(NativeGate, gate_features.AsciiDiagrammableGate):
    """Indicates that a qubit should be measured, and where the result goes."""

    def __init__(self, key: str = ''):
        self.key = key

    def to_proto(self, *qubits):
        if len(qubits) != 1:
            raise ValueError('Wrong number of qubits.')

        q = qubits[0]
        op = operations_pb2.Operation()
        op.measurement.target.x = q.x
        op.measurement.target.y = q.y
        op.measurement.key = self.key
        return op

    def ascii_wire_symbols(self):
        return 'M',

    def __repr__(self):
        return 'MeasurementGate({})'.format(repr(self.key))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.key == other.key

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((MeasurementGate, self.key))


class Exp11Gate(NativeGate, gate_features.PhaseableGate):
    """A two-qubit interaction that phases the amplitude of the 11 state."""

    def __init__(self, turns_param_key: str = '',
                 turns_offset: float = 0.0):
        self.turns_param_key = turns_param_key
        self.half_turns = _signed_mod_unity(turns_offset) * 2.0

    def phase_by(self, phase_turns, qubit_index):
        return self

    def to_proto(self, *qubits):
        if len(qubits) != 2:
            raise ValueError('Wrong number of qubits.')

        p, q = qubits
        op = operations_pb2.Operation()
        op.cz.target1.x = p.x
        op.cz.target1.y = p.y
        op.cz.target2.x = q.x
        op.cz.target2.y = q.y
        op.cz.turns.raw = self.half_turns / 4
        op.cz.turns.parameter_key = self.turns_param_key
        return op

    def __repr__(self):
        return 'ParameterizedCZGate(turns_param_key={}, half_turns={})'.format(
            repr(self.turns_param_key), repr(self.half_turns))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.turns_param_key == other.turns_param_key and
                self.half_turns == other.half_turns)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((Exp11Gate,
                     self.turns_param_key,
                     self.half_turns))


class ExpWGate(NativeGate, gate_features.PhaseableGate):
    """A rotation around an axis in the XY plane of the Bloch sphere."""

    def __init__(self,
                 turns_param_key: str = '',
                 turns_offset: float = 0.0,
                 axis_phase_turns_key: str = '',
                 axis_phase_turns_offset: float = 0.0):
        self.turns_param_key = turns_param_key
        self.axis_phase_turns_key = axis_phase_turns_key
        t = _signed_mod_unity(turns_offset)
        p = _signed_mod_unity(axis_phase_turns_offset)

        if (not turns_param_key and not axis_phase_turns_key and
                not 0 <= p < 0.5):
            # Canonicalize to negative rotation around positive axis.
            p = _signed_mod_unity(p + 0.5)
            t = _signed_mod_unity(-turns_offset)

        self.half_turns = t * 2.0
        self.axis_half_turns = p * 2.0

    def to_proto(self, *qubits):
        if len(qubits) != 1:
            raise ValueError('Wrong number of qubits.')

        q = qubits[0]
        op = operations_pb2.Operation()
        op.xy.target.x = q.x
        op.xy.target.y = q.y
        op.xy.rotation_axis_turns.raw = self.axis_half_turns / 2
        op.xy.rotation_axis_turns.parameter_key = self.axis_phase_turns_key
        op.xy.turns.raw = self.half_turns / 4
        op.xy.turns.parameter_key = self.turns_param_key
        return op

    def phase_by(self, phase_turns, qubit_index):
        return ExpWGate(
            turns_param_key=self.turns_param_key,
            turns_offset=self.half_turns / 2,
            axis_phase_turns_key=self.axis_phase_turns_key,
            axis_phase_turns_offset=self.axis_half_turns / 2 + phase_turns)

    def __repr__(self):
        return ('ParameterizedXYGate(turns_param_key={}, '
                'half_turns={}, '
                'axis_phase_turns_key={}, '
                'axis_half_turns={})'.format(
                    repr(self.turns_param_key),
                    repr(self.half_turns),
                    repr(self.axis_phase_turns_key),
                    repr(self.axis_half_turns)))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return (self.turns_param_key == other.turns_param_key and
                self.half_turns == other.half_turns and
                self.axis_phase_turns_key == other.axis_phase_turns_key and
                self.axis_half_turns == other.axis_half_turns)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((ExpWGate,
                     self.turns_param_key,
                     self.half_turns,
                     self.axis_phase_turns_key,
                     self.axis_half_turns))


class ExpZGate(NativeGate, gate_features.PhaseableGate):
    """A rotation around the Z axis of the Bloch sphere."""

    def __init__(self, turns_param_key: str = '',
                 turns_offset: float = 0.0):
        self.turns_param_key = turns_param_key
        self.half_turns = _signed_mod_unity(turns_offset) * 2.0

    def phase_by(self, phase_turns, qubit_index):
        return self

    def to_proto(self, *qubits):
        if len(qubits) != 1:
            raise ValueError('Wrong number of qubits.')

        q = qubits[0]
        op = operations_pb2.Operation()
        op.z.target.x = q.x
        op.z.target.y = q.y
        op.z.turns.raw = self.half_turns / 4
        op.z.turns.parameter_key = self.turns_param_key
        return op

    def __repr__(self):
        return 'ParameterizedZGate(turns_param_key={}, half_turns={})'.format(
            repr(self.turns_param_key), repr(self.half_turns))

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.turns_param_key == other.turns_param_key and
                self.half_turns == other.half_turns)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((ExpZGate,
                     self.turns_param_key,
                     self.half_turns))


def _signed_mod_unity(r):
    """Returns a number from (0.5, 0.5], equivalent to r modulo 1.0."""
    r %= 1.0
    if r > 0.5:
        r -= 1.0
    return r