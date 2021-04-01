#!/usr/bin/python
import sys  # THese are modules used
import gzip
import multiprocessing as mp
import re
import glob
import os
import pandas as pd
from dataclasses import dataclass
import shutil

import pre_shared_segments_analysis_scripts.generate_indx_dict as generate_indx_dict

####################################################################################################


class newPOS:
    __slots__ = 'add', 'rem'

    def __init__(self, add, rem):
        self.add = add
        self.rem = rem


def generate_parameters(ibd_program: str) -> dict:
    """Function to generate a dictionary of the indices for the parameters 
    that you have
    Parameters
    __________
    ibd_program : str
        string containing the ibd program that the input is coming from. 
        This value should be ilash, hapibd, or germline
    """
    # using a dictionary to determine 
    ibd_handler_dict: dict = {
        "hapibd": generate_indx_dict.Hapibd_Indices(ibd_program),
        "ilash": generate_indx_dict.Ilash_Indices(ibd_program),
        "germine": generate_indx_dict.Germline_Indices(ibd_program)
    }

    param_class = ibd_handler_dict[ibd_program.lower()]

    # updating the indices for which ever option was chosen
    param_class.update_indices()

    return param_class.return_param_dict()

class Shared_Segment_Convert(newPOS):
    def __init__(self, shared_segment_file: str, pheno_file: str,
                 output_path: str, ibd_program_used: str,
                 min_cM_threshold: int, base_position,
                 variant_id):
        # This is the germline or hapibd or ilash file
        self.segment_file = str(shared_segment_file)
        # This will give the directory for where the chromosome files are found
        self.iid_file = str(pheno_file)
        # This will be the output directory. Need to add the ibd software to the end of it
        self.output_dir = output_path

        if not os.path.exists("".join([output_path, "reformatted_ibd_output/"
                                       ])):
            try:
                os.mkdir("".join([output_path, "reformatted_ibd_output/"]))
            except FileExistsError:
                pass

        self.output = "".join(
            [output_path, "reformatted_ibd_output/", ibd_program_used])
        self.format = str(ibd_program_used)
        self.min_cM = int(min_cM_threshold)
        self.bp = int(base_position)
        # This gets the name of the variant of interest assuming it is input as a text file
        self.variant_name = variant_id

    def build_id_pairs(self):
        '''This creates a two list of unique iids and duplicate iids'''

        # read phenotype and build possible ID pairs
        uniqID = {}  # creates empty dictionary
        dupID = []  # creates empty list

        IDnum = 0

        for iid in self.iid_file:  # This goes through each line and will get the id's

            if iid in uniqID:
                dupID.append(iid)
            else:

                uniqID[iid] = IDnum
                IDnum = IDnum + 1

        # print('identified ' + str(len(uniqID)) + ' unique IDs')

        # Closing the file

        return uniqID, dupID

    def create_ibd_arrays(self) -> dict:
        '''This creates two IBD arrays that will be used later'''

        # creating a dictionary with 22 key slots and 22 empty dictionaries
        # Also creating a dicitonary IBDindex with 22 dictionaries containing 'start': 999999999, 'end': 0, 'allpos': []
        # Using dictionary comprehension to make the two dictionaries. Just a little more concise than the for loop.
        # The 22 is for the different chromosomes.
        # the "allpos" is the breakpoints
        IBDdata = {str(i): {} for i in range(1, 23)}
        IBDindex = {
            str(i): {
                'start': 999999999,
                'end': 0,
                'allpos': []
            }
            for i in range(1, 23)
        }

        return IBDdata, IBDindex

    def IBDsumm(self, IBDdata: dict, IBDindex: dict, parameter_dict: dict,
                uniqID: dict, que_object):
        '''This function will be used in the parallelism function'''

        # undoing the parameter_dict
        id1_indx = int(parameter_dict["id1_indx"])
        id2_indx = int(parameter_dict["id2_indx"])
        chr_indx = int(parameter_dict["chr_indx"])
        str_indx = int(parameter_dict["str_indx"])
        end_indx = int(parameter_dict["end_indx"])
        cM_indx = int(parameter_dict["cM_indx"])

        # This catches the KeyError raised because unit is only found in GERMLINE files
        try:
            unit = parameter_dict["unit"]
        except KeyError:
            pass

        for chunk in pd.read_csv(self.segment_file,
                                 sep="\s+",
                                 header=None,
                                 chunksize=500000):
            # Checking to see if the ids are not in the uniqID dictionary
            chunk_not_in_uniqID = chunk[(chunk[id1_indx].isin(uniqID)) |
                                        (chunk[id2_indx].isin(uniqID))]

            # This is reducing the dataframe to only pairs greater than min_cM threshold
            chunk_greater_than_3_cm = chunk_not_in_uniqID[(
                chunk_not_in_uniqID[cM_indx] >= self.min_cM)]
            # Need to check if the unit doesn't equal cM. This only applies in the case of germline
            try:
                chunk_greater_than_3_cm = chunk_greater_than_3_cm[
                    chunk_greater_than_3_cm[unit] == "cM"]

            except NameError:
                pass

            chunk = chunk_greater_than_3_cm[
                (chunk_greater_than_3_cm[str_indx] < self.bp)
                & (chunk_greater_than_3_cm[end_indx] > self.bp)]
            # This will iterate through each row of the filtered chunk
            if not chunk.empty:
                for row in chunk.itertuples():

                    id1 = str(row[id1_indx + 1])
                    id2 = str(row[id2_indx + 1])
                    cM = str(row[cM_indx + 1])
                    CHR = str(row[chr_indx + 1])
                    start = min(int(row[str_indx + 1]), int(row[end_indx + 1]))
                    end = max(int(row[str_indx + 1]), int(row[end_indx + 1]))

                    if id1 in uniqID and id2 in uniqID:  # Checks to see if the ids are in the uniqID list

                        if uniqID[id1] < uniqID[id2]:
                            # If both ids are in the list then it writes the pairs to a variable pair

                            pair = '{0}:{1}-{2}'.format(cM, id1, id2)

                        else:
                            # this just puts the ids in order
                            pair = '{0}:{1}-{2}'.format(cM, id2, id1)

                    elif id1 in uniqID:  # If only one id is in the uniqID then it writes it this way with the matched id in

                        pair = '{0}:{1}-{2}'.format(cM, id1, id2)

                    elif id2 in uniqID:  # If only id 2 is in the uniqID then it write that pair to the list
                        pair = '{0}:{1}-{2}'.format(cM, id2, id1)

                # start and end not in identified breakpoints
                    if int(start) not in IBDindex[CHR]['allpos'] and int(
                            end) not in IBDindex[CHR]['allpos']:

                        IBDdata[CHR][str(start)] = newPOS([pair], [])
                        IBDdata[CHR][str(end)] = newPOS([], [pair])
                        IBDindex[CHR]['allpos'].append(int(start))
                        IBDindex[CHR]['allpos'].append(int(end))

                    # start is not in identified breakpoints but end is
                    elif int(start) not in IBDindex[CHR]['allpos'] and int(
                            end) in IBDindex[CHR]['allpos']:

                        IBDdata[CHR][str(start)] = newPOS([pair], [])
                        IBDdata[CHR][str(end)].rem.append(str(pair))
                        IBDindex[CHR]['allpos'].append(int(start))
                #
                # start is in identified breakpoints but end not
                    elif int(start) in IBDindex[CHR]['allpos'] and int(
                            end) not in IBDindex[CHR]['allpos']:

                        IBDdata[CHR][str(start)].add.append(str(pair))
                        IBDdata[CHR][str(end)] = newPOS([], [pair])
                        IBDindex[CHR]['allpos'].append(int(end))
            #
            # both start and end in identified breakpoints
                    elif int(start) in IBDindex[CHR]['allpos'] and int(
                            end) in IBDindex[CHR]['allpos']:

                        IBDdata[CHR][str(start)].add.append(str(pair))
                        IBDdata[CHR][str(end)].rem.append(str(pair))
        try:

            # print('identified ' + str(len(IBDindex[str(CHR)]['allpos'])) +
            #       ' breakpoints on chr' + str(CHR))

            # Opening the file .small/txt/gz file to write to
            # NEED TO FIX THIS LINE HERE
            write_path = "".join([
                self.output, '_', self.variant_name, '.chr',
                str(CHR), '.small.txt.gz'
            ])

            out = gzip.open(write_path, 'wt')

            # Writing the header line to the file
            out.write('chr\tpos\tsegments\tpairs\tadd\tdel\n')

            allibd = set([])

            for pos in sorted(IBDindex[str(CHR)]['allpos']):

                allibd = allibd | set(IBDdata[str(CHR)][str(pos)].add)
                allibd = allibd - set(IBDdata[str(CHR)][str(pos)].rem)

                allibdpair = {}

                if len(IBDdata[str(CHR)][str(pos)].add) == 0:
                    IBDdata[str(CHR)][str(pos)].add.append('NA')
                if len(IBDdata[str(CHR)][str(pos)].rem) == 0:
                    IBDdata[str(CHR)][str(pos)].rem.append('NA')

                nseg = str(len(allibd))

                for cM_pair in allibd:
                    pair = cM_pair.split(':')[1]
                    cM = cM_pair.split(':')[0]

                    if pair in allibdpair:

                        allibdpair[pair] = '{0};{1}'.format(
                            allibdpair[pair], cM)

                    else:

                        allibdpair[pair] = str(cM)

                npair = str(len(allibdpair))

                out.write('{0}\t{1}\t{2}\t{3}\t{4}\t{5}\n'.format(
                    str(CHR), str(pos), nseg, npair,
                    ' '.join(IBDdata[str(CHR)][str(pos)].add),
                    ' '.join(IBDdata[str(CHR)][str(pos)].rem)))

            IBDdata[str(CHR)] = []
            out.close()

        except UnboundLocalError:

            print(
                f"There were no pairs identified for the variant {self.variant_name}. This failure is written to a file at {''.join([self.output_dir, 'nopairs_identified.txt'])}"
            )

            que_object.put(f"{self.variant_name}")

    def run(self, IBDdata, IBDindex, parameter_dict, uniqID, que_object):

        self.IBDsumm(IBDdata, IBDindex, parameter_dict, uniqID, que_object)

        del (IBDdata)
        del (IBDindex)
