from typing import Optional

import numpy as np
import pandas as pd
from pynwb import NWBFile
from pynwb.ophys import Fluorescence

from allensdk.brain_observatory.behavior.data_files.demix_file import DemixFile
from allensdk.brain_observatory.behavior.data_objects import DataObject
from allensdk.brain_observatory.behavior.data_objects.base \
    .readable_interfaces import \
    DataFileReadableInterface, NwbReadableInterface
from allensdk.brain_observatory.behavior.data_objects.base \
    .writable_interfaces import \
    NwbWritableInterface


class CorrectedFluorescenceTraces(DataObject, DataFileReadableInterface,
                                  NwbReadableInterface, NwbWritableInterface):
    def __init__(self, traces: pd.DataFrame,
                 filter_to_roi_ids: Optional[np.array] = None):
        """

        Parameters
        ----------
        traces
            index cell_roi_id
            columns:
            - corrected_fluorescence
                list of float
        filter_to_roi_ids
            Filter traces to only these roi ids, for example to filter invalid
            rois
        """
        if filter_to_roi_ids is not None:
            if not np.in1d(filter_to_roi_ids, traces.index).all():
                raise RuntimeError('Not all roi ids to be filtered are in '
                                   'corrected fluorescence traces')
            traces = traces.loc[filter_to_roi_ids]

        super().__init__(name='corrected_fluorescence_traces', value=traces)

    @classmethod
    def from_nwb(cls, nwbfile: NWBFile,
                 filter_to_roi_ids: Optional[np.array] = None) \
            -> "CorrectedFluorescenceTraces":
        corr_fluorescence_nwb = nwbfile.processing[
            'ophys'].data_interfaces[
            'corrected_fluorescence'].roi_response_series['traces']
        # f traces stored as timepoints x rois in NWB
        # We want rois x timepoints, hence the transpose
        f_traces = corr_fluorescence_nwb.data[:].T
        df = pd.DataFrame({'corrected_fluorescence': f_traces.tolist()},
                          index=pd.Index(
                              data=corr_fluorescence_nwb.rois.table.id[:],
                              name='cell_roi_id'))
        return cls(traces=df, filter_to_roi_ids=filter_to_roi_ids)

    @classmethod
    def from_data_file(cls,
                       demix_file: DemixFile) \
            -> "CorrectedFluorescenceTraces":
        corrected_fluorescence_traces = demix_file.data
        return cls(traces=corrected_fluorescence_traces)

    def to_nwb(self, nwbfile: NWBFile) -> NWBFile:
        corrected_fluorescence_traces = self.value[['corrected_fluorescence']]

        # Create/Add corrected_fluorescence_traces modules and interfaces:
        assert corrected_fluorescence_traces.index.name == 'cell_roi_id'
        ophys_module = nwbfile.processing['ophys']
        # trace data in the form of rois x timepoints
        f_trace_data = np.array(
            [corrected_fluorescence_traces.loc[
                 cell_roi_id].corrected_fluorescence
             for cell_roi_id in corrected_fluorescence_traces.index.values])

        roi_table_region = \
            nwbfile.processing['ophys'].data_interfaces[
                'dff'].roi_response_series[
                'traces'].rois  # noqa: E501
        ophys_timestamps = ophys_module.get_data_interface(
            'dff').roi_response_series['traces'].timestamps
        f_interface = Fluorescence(name='corrected_fluorescence')
        ophys_module.add_data_interface(f_interface)

        f_interface.create_roi_response_series(
            name='traces',
            data=f_trace_data.T,  # Should be stored as timepoints x rois
            unit='NA',
            rois=roi_table_region,
            timestamps=ophys_timestamps)
        return nwbfile
