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

from cirq import circuits
from cirq import ops


def assert_optimizes(before, after):
    opt = circuits.MergeInteractions()
    opt.optimize_circuit(before)

    # Ignore differences that would be caught by follow-up optimizations.
    followup_optimizations = [
        circuits.MergeRotations(),
        circuits.DropNegligible(),
        circuits.DropEmptyMoments()
    ]
    for opt in followup_optimizations:
        opt.optimize_circuit(before)
        opt.optimize_circuit(after)

    assert before == after


def test_clears_paired_cnot():
    q1 = ops.QubitId(0, 0)
    q2 = ops.QubitId(0, 1)
    assert_optimizes(
        before=circuits.Circuit([
            circuits.Moment([ops.CNOT(q1, q2)]),
            circuits.Moment([ops.CNOT(q1, q2)]),
        ]),
        after=circuits.Circuit())


def test_ignores_czs_separated_by_parameterized():
    q0 = ops.QubitId(0, 0)
    q1 = ops.QubitId(0, 1)
    assert_optimizes(
        before=circuits.Circuit([
            circuits.Moment([ops.CZ(q0, q1)]),
            circuits.Moment([ops.ExpZGate('boo')(q0)]),
            circuits.Moment([ops.CZ(q0, q1)]),
        ]),
        after=circuits.Circuit([
            circuits.Moment([ops.CZ(q0, q1)]),
            circuits.Moment([ops.ExpZGate('boo')(q0)]),
            circuits.Moment([ops.CZ(q0, q1)]),
        ]))


def test_ignores_czs_separated_by_outer_cz():
    q00 = ops.QubitId(0, 0)
    q01 = ops.QubitId(0, 1)
    q10 = ops.QubitId(1, 0)
    assert_optimizes(
        before=circuits.Circuit([
            circuits.Moment([ops.CZ(q00, q01)]),
            circuits.Moment([ops.CZ(q00, q10)]),
            circuits.Moment([ops.CZ(q00, q01)]),
        ]),
        after=circuits.Circuit([
            circuits.Moment([ops.CZ(q00, q01)]),
            circuits.Moment([ops.CZ(q00, q10)]),
            circuits.Moment([ops.CZ(q00, q01)]),
        ]))