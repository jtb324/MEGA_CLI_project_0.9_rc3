#!/usr/bin/python

import sys  # THese are modules used
import gzip
import multiprocessing as mp
import re
import glob
import os
import pandas as pd
import shutil

import file_creator_scripts

####################################################################################################


class Pre_Shared_Segment_Converter:
    '''This class will prepare the input for all of the shared segment converter'''

    def __init__(self, ibd_output_directory: str, chromosome_files_dir: str,
                 ibd_software: str, output_dir: str, map_file_dir: str):
        self.segment_dir = ibd_output_directory
        self.chromosome_dir = chromosome_files_dir
        self.output = output_dir
        self.program_used = ibd_software
        self.cur_dir = os.getcwd()
        self.map_file_dir = map_file_dir

    def gather_segment_files(self, segment_file_suffix: str) -> list:

        os.chdir(self.segment_dir)

        segment_files_list = []

        for file in glob.glob("".join(["*", segment_file_suffix])):

            full_file_path = "".join([self.segment_dir, file])

            segment_files_list.append(full_file_path)

        os.chdir(self.cur_dir)

        return segment_files_list

    def gather_chromosome_files(self) -> list:
        os.chdir(self.chromosome_dir)

        chromo_file_list = []

        for file in glob.glob("*.single_variant_carrier.csv"):

            full_file_path = "".join([self.chromosome_dir, file])

            chromo_file_list.append(full_file_path)

        os.chdir(self.cur_dir)

        return chromo_file_list

    def get_map_files(self) -> list:
        '''This function returns a list of all the map files'''
        os.chdir(self.map_file_dir)

        map_file_list = []

        for file in glob.glob("*.map"):

            full_file_path = "".join([self.map_file_dir, file])

            map_file_list.append(full_file_path)

        os.chdir(self.cur_dir)

        return map_file_list

    # returns a dataframe and a string
    def create_variant_lists(self, chromo_var_file: str, map_file_path: str):
        '''This function will take a csv file of carriers and then forming txt files for list carriers for each variant.'''
        # this makes the directory name to output the files to
        var_list_dir = "".join([self.output, "variant_lists/"])

        # This attempts to make the directory for the list of IIDs per variant
        try:
            os.mkdir(var_list_dir)

        # This exception should never be raised
        except FileExistsError:
            pass

        # load in the csv file that list the IIDs of grids per variant on a specific chromosome
        carrier_df = pd.read_csv(chromo_var_file, sep=",")
        
        # Need to determine the # of rows of the carrier_df
        carrier_df_size = len(carrier_df)

        # reading in the map file
        map_file_df = pd.read_csv(map_file_path,
                                  sep="\t",
                                  header=None,
                                  names=["chr", "variant id", "cM", "site"])

        # bringing in the original variant excel file to get the variant site position
        # iterate through each row of the chromosome so that
        # going to create two list where one contains the variant_id, one contains a list of base positions,
        variant_id_list = []
        base_pos_list = []
        carrier_df_variants: list = list(set(
            carrier_df["Variant ID"].values.tolist()))

        for variant in carrier_df_variants:
        # for row in carrier_df.itertuples():
            # getting the subset of the carrier_df that corresponds
            # to the variant
            df_subset: pd.DateFrame = carrier_df[
                carrier_df["Variant ID"] == variant]

            # getting a list of all the iids that are associated 
            # with the variant

            iid_list: list = df_subset["IID"].values.tolist()

            # getting the list of variants and writing to a single text file for each variant in the chromosome.
            
            chr_num = map_file_df[map_file_df["variant id"] == variant[:(
                len(variant) - 2)]].chr.values[0]

            if carrier_df_size == 1 and iid_list[0] == "":

                # If this single variant has no carriers than the function returns empty strings for the
                #var_info_file_path, variant_directory
                # If the iid_list has no carriers thant eh first element would just be a ""
                no_carriers_file = open(
                    "".join([self.output, "no_carriers_in_file.txt"]),
                    "a+")
                no_carriers_file.write(variant)
                no_carriers_file.write("\t")
                no_carriers_file.write(str(chr_num))
                no_carriers_file.write("\n")
                no_carriers_file.close()
                return None, ""

            # If the carrier df has more than one carrier it will search through all rows and just skip any row
            # that has now carriers
            if iid_list[0] == "":
                no_carriers_file = open(
                    "".join([self.output, "no_carriers_in_file.txt"]), "a+")
                no_carriers_file.write(variant)
                no_carriers_file.write("\t")
                no_carriers_file.write(str(chr_num))
                no_carriers_file.write("\n")
                no_carriers_file.close()
                print(
                    f"There were no carriers found for the variant {variant}"
                )
                continue

            # Writing the variants to a txt file in a specific directory
            MyFile = open("".join([var_list_dir, variant, ".txt"]), 'w')

            for element in iid_list:
                MyFile.write(element)
                MyFile.write('\n')
            MyFile.close()

            # This next section will return a dataframe of values
            #####################################################################################################
            # getting the base pair position and writing that to a text file

            # append the variant_id
            variant_id_list.append(variant)

            # getting the base post
            base_pos = map_file_df[map_file_df["variant id"] == variant[:(
                len(variant) - 2)]].site.values[0]

            # appending the base position to the list
            base_pos_list.append(base_pos)

        variant_info_dict = {
            "variant_id": variant_id_list,
            "site": base_pos_list
        }

        variant_info_df = pd.DataFrame(variant_info_dict)

        return variant_info_df, var_list_dir

    def get_iid_files(self, iid_list_file_path: str) -> list:
        os.chdir(iid_list_file_path)

        iid_file_list = []

        for file in glob.glob("*.txt"):

            full_file_path = "".join([iid_list_file_path, file])

            iid_file_list.append(full_file_path)

        os.chdir(self.cur_dir)

        return iid_file_list


class newPOS:
    __slots__ = 'add', 'rem'

    def __init__(self, add, rem):
        self.add = add
        self.rem = rem


class Shared_Segment_Convert(newPOS):
    def __init__(self, shared_segment_file: str, pheno_file: str,
                 output_path: str, ibd_program_used: str,
                 min_cM_threshold: int, thread: int, base_position,
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
        self.thread = int(thread)
        self.bp = int(base_position)
        # This gets the name of the variant of interest assuming it is input as a text file
        self.variant_name = variant_id

    def generate_parameters(self) -> dict:
        '''This will get some of the parameters used later'''
        parameter_dict = {
            "id1_indx": 0,
            "id2_indx": 2,
            "chr_indx": 4,
            "str_indx": 5,
            "end_indx": 6
        }

        # This section checks the in_format argument to determine which software program was used for IBD detection
        if self.format.lower() == 'germline':
            parameter_dict["cM_indx"] = 10
            parameter_dict["unit"] = 11

        elif self.format.lower() == 'ilash':
            parameter_dict["cM_indx"] = 9

        elif self.format.lower() in ['hap-ibd', 'hapibd']:
            parameter_dict["cM_indx"] = 7

        elif self.format.lower() == 'rapid':
            parameter_dict["id1_indx"] = 1
            parameter_dict["id2_indx"] = 2
            parameter_dict["chr_indx"] = 0
            parameter_dict["cM_indx"] = 7

        else:
            if self.format.lower().split(':')[0] in ['other', 'others']:
                indx = self.format.lower().split(':')[1].split(';')
                parameter_dict["id1_indx"] = int(indx[0]) - 1
                parameter_dict["id2_indx"] = int(indx[1]) - 1
                parameter_dict["chr_indx"] = int(indx[2]) - 1
                parameter_dict["str_indx"] = int(indx[3]) - 1
                parameter_dict["end_indx"] = int(indx[4]) - 1
                parameter_dict["cM_indx"] = int(indx[5]) - 1

            else:
                sys.exit(
                    'unrecognized or incorrect format: GREMLINE/iLASH/RaPID/hap-ibd/other:id1;id2;chr;str;start bp;end bp;cM'
                )
        return parameter_dict

    def build_id_pairs(self):
        '''This creates a two list of unique iids and duplicate iids'''

        # read phenotype and build possible ID pairs
        uniqID = {}  # creates empty dictionary
        dupID = []  # creates empty list

        # Opens the file from for the list of IIDs to search through
        pheno_file = open(self.iid_file, 'r')

        IDnum = 0

        for line in pheno_file:  # This goes through each line and will get the id's
            line = line.strip()

            if line in uniqID:
                dupID.append(line[0])
            else:

                uniqID[line] = IDnum
                IDnum = IDnum + 1

        # print('identified ' + str(len(uniqID)) + ' unique IDs')

        # Closing the file
        pheno_file.close()

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