# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Placeholder docstring"""
from __future__ import absolute_import

import logging
import struct
import sys

import numpy as np

from sagemaker.amazon.record_pb2 import Record
from sagemaker.utils import DeferredError


def _write_feature_tensor(resolved_type, record, vector):
    """Placeholder Docstring"""
    if resolved_type == "Int32":
        record.features["values"].int32_tensor.values.extend(vector)
    elif resolved_type == "Float64":
        record.features["values"].float64_tensor.values.extend(vector)
    elif resolved_type == "Float32":
        record.features["values"].float32_tensor.values.extend(vector)


def _write_label_tensor(resolved_type, record, scalar):
    """Placeholder Docstring"""
    if resolved_type == "Int32":
        record.label["values"].int32_tensor.values.extend([scalar])
    elif resolved_type == "Float64":
        record.label["values"].float64_tensor.values.extend([scalar])
    elif resolved_type == "Float32":
        record.label["values"].float32_tensor.values.extend([scalar])


def _write_keys_tensor(resolved_type, record, vector):
    """Placeholder Docstring"""
    if resolved_type == "Int32":
        record.features["values"].int32_tensor.keys.extend(vector)
    elif resolved_type == "Float64":
        record.features["values"].float64_tensor.keys.extend(vector)
    elif resolved_type == "Float32":
        record.features["values"].float32_tensor.keys.extend(vector)


def _write_shape(resolved_type, record, scalar):
    """Placeholder Docstring"""
    if resolved_type == "Int32":
        record.features["values"].int32_tensor.shape.extend([scalar])
    elif resolved_type == "Float64":
        record.features["values"].float64_tensor.shape.extend([scalar])
    elif resolved_type == "Float32":
        record.features["values"].float32_tensor.shape.extend([scalar])


def write_numpy_to_dense_tensor(file, array, labels=None):
    """Writes a numpy array to a dense tensor

    Args:
        file:
        array:
        labels:
    """

    # Validate shape of array and labels, resolve array and label types
    if not len(array.shape) == 2:
        raise ValueError("Array must be a Matrix")
    if labels is not None:
        if not len(labels.shape) == 1:
            raise ValueError("Labels must be a Vector")
        if labels.shape[0] not in array.shape:
            raise ValueError(
                "Label shape {} not compatible with array shape {}".format(
                    labels.shape, array.shape
                )
            )
        resolved_label_type = _resolve_type(labels.dtype)
    resolved_type = _resolve_type(array.dtype)

    # Write each vector in array into a Record in the file object
    record = Record()
    for index, vector in enumerate(array):
        record.Clear()
        _write_feature_tensor(resolved_type, record, vector)
        if labels is not None:
            _write_label_tensor(resolved_label_type, record, labels[index])
        _write_recordio(file, record.SerializeToString())


def write_spmatrix_to_sparse_tensor(file, array, labels=None):
    """Writes a scipy sparse matrix to a sparse tensor

    Args:
        file:
        array:
        labels:
    """
    try:
        import scipy
    except ImportError as e:
        logging.warning(
            "scipy failed to import. Sparse matrix functions will be impaired or broken."
        )
        # Any subsequent attempt to use scipy will raise the ImportError
        scipy = DeferredError(e)

    if not scipy.sparse.issparse(array):
        raise TypeError("Array must be sparse")

    # Validate shape of array and labels, resolve array and label types
    if not len(array.shape) == 2:
        raise ValueError("Array must be a Matrix")
    if labels is not None:
        if not len(labels.shape) == 1:
            raise ValueError("Labels must be a Vector")
        if labels.shape[0] not in array.shape:
            raise ValueError(
                "Label shape {} not compatible with array shape {}".format(
                    labels.shape, array.shape
                )
            )
        resolved_label_type = _resolve_type(labels.dtype)
    resolved_type = _resolve_type(array.dtype)

    csr_array = array.tocsr()
    n_rows, n_cols = csr_array.shape

    record = Record()
    for row_idx in range(n_rows):
        record.Clear()
        row = csr_array.getrow(row_idx)
        # Write values
        _write_feature_tensor(resolved_type, record, row.data)
        # Write keys
        _write_keys_tensor(resolved_type, record, row.indices.astype(np.uint64))

        # Write labels
        if labels is not None:
            _write_label_tensor(resolved_label_type, record, labels[row_idx])

        # Write shape
        _write_shape(resolved_type, record, n_cols)

        _write_recordio(file, record.SerializeToString())


def read_records(file):
    """Eagerly read a collection of amazon Record protobuf objects from file.

    Args:
        file:
    """
    records = []
    for record_data in read_recordio(file):
        record = Record()
        record.ParseFromString(record_data)
        records.append(record)
    return records


# MXNet requires recordio records have length in bytes that's a multiple of 4
# This sets up padding bytes to append to the end of the record, for diferent
# amounts of padding required.
padding = {}
for amount in range(4):
    if sys.version_info >= (3,):
        padding[amount] = bytes([0x00 for _ in range(amount)])
    else:
        padding[amount] = bytearray([0x00 for _ in range(amount)])

_kmagic = 0xCED7230A


def _write_recordio(f, data):
    """Writes a single data point as a RecordIO record to the given file.

    Args:
        f:
        data:
    """
    length = len(data)
    f.write(struct.pack("I", _kmagic))
    f.write(struct.pack("I", length))
    pad = (((length + 3) >> 2) << 2) - length
    f.write(data)
    f.write(padding[pad])


def read_recordio(f):
    """Placeholder Docstring"""
    while True:
        try:
            (read_kmagic,) = struct.unpack("I", f.read(4))
        except struct.error:
            return
        assert read_kmagic == _kmagic
        (len_record,) = struct.unpack("I", f.read(4))
        pad = (((len_record + 3) >> 2) << 2) - len_record
        yield f.read(len_record)
        if pad:
            f.read(pad)


def _resolve_type(dtype):
    """Placeholder Docstring"""
    if dtype == np.dtype(int):
        return "Int32"
    if dtype == np.dtype(float):
        return "Float64"
    if dtype == np.dtype("float32"):
        return "Float32"
    raise ValueError("Unsupported dtype {} on array".format(dtype))
