# import statements
import sys
import gzip
from numpy.core.numeric import NaN
import pandas as pd
import itertools
import argparse


class Output_Comparer:

    def __init__(self, output, variant_position, var_of_interest, input_dir):
        self.output = output
        self.variant_pos = variant_position
        self.var_of_interest = var_of_interest
        self.input_dir = input_dir

    def check_arguments(self, args_list):
        if len(args_list) == 0:
            sys.exit('this.py output format1:file1 format2:file2 ... ...')

    def create_file_dict(self, args_list, var_of_interest):
        print(len(args_list))
        files = {}
        for f in range(0, len(args_list)):
            print(args_list[f])
            # making the files match the variant
            underscore_pos = args_list[f].split(":")[1].find("_")
            dot_pos = args_list[f].split(":")[1].find(".")
            software_name = args_list[f].split(":")[1][:underscore_pos]
            file_tag = args_list[f].split(":")[1][dot_pos:]

            filename = "".join([software_name, "_", var_of_interest, file_tag])

            full_filename = "".join([self.input_dir, "/", filename])

            # writing the software name and file name to a dictionary
            files[args_list[f].split(':')[0]] = full_filename

        print('input {0} files: {1}'.format(
            len(files), ' '.join(files.keys())))

        return files

    def read_first_line(self, files):
        curr_pair = {}
        curr_pos = {}
        curr_ibd = {}
        newpos = {}
        newline = {}
        openfile = {}
        endtest = {}
        endline = {}
        # read first line for all input files
        for f in files:
            openfile[f] = gzip.open(files[f], 'rt')
            openfile[f].seek(0, 2)
            endline[f] = openfile[f].tell()
            openfile[f].seek(0)
            line0 = openfile[f].readline()
            curr_pos[f] = 0
            curr_ibd[f] = set([])
            curr_pair[f] = set([])
            line1 = openfile[f].readline()
            line1 = line1.strip()
            newpos[f] = int(line1.split('\t')[1])
            newline[f] = line1
            endtest[f] = 0

        first_line_dict = {
            "curr_pair": curr_pair,
            "curr_pos": curr_pos,
            "curr_ibd": curr_ibd,
            "newpos": newpos,
            "newline": newline,
            "openfile": openfile,
            "endtest": endtest,
            "endline": endline
        }

        return first_line_dict

    def define_input_combinations(self, file_dict):
        allcomb = {}
        for i in range(len(file_dict.keys()), 0, -1):

            for item in list(itertools.combinations(file_dict.keys(), i)):

                allcomb['+'.join(item)] = item

        combtab = pd.DataFrame(
            0, columns=file_dict.keys(), index=allcomb.keys())

        for item in allcomb:
            combtab.loc[item, allcomb[item]] = len(allcomb[item])

        return allcomb, combtab

    def findkey(self, i, new_pos_dict):
        result = []
        offset = -1
        while True:
            try:
                offset = list(new_pos_dict.values()).index(i, offset+1)
            except ValueError:
                return list(map(lambda i: list(new_pos_dict.keys())[i], result))
            result.append(offset)

    def allinter(self, mylist, curr_pair):
        intu = curr_pair[mylist[0]]
        for f in mylist[1:]:
            intu = intu & curr_pair[f]

        return intu

    def get_uniqrow(self, i, allcomb, combtab, curr_pair_dict):
        uniqdic = {}
        for comb in allcomb.keys():
            raw_n = len(self.allinter(allcomb[comb], curr_pair_dict))
            octab = pd.DataFrame(
                map(lambda ff: combtab[ff] > combtab.loc[comb, ff], allcomb[comb])).all()
            overcount = octab.index[octab == True].tolist()
            uniqdic[comb] = raw_n - \
                sum(list(map(lambda oc: uniqdic[oc], overcount)))

        return list(uniqdic.values())

    def all_agree_pair(self, pair_list):
        unionpair = list(pair_list.values())[0]
        for f in pair_list.keys():
            unionpair = unionpair.union(pair_list[f])
        return unionpair

    def write_to_file(self, allcomb, combtab, first_line_dict):

        # Pulling parameters from first_line_dict
        curr_pair = first_line_dict["curr_pair"]
        curr_pos = first_line_dict["curr_pos"]
        curr_ibd = first_line_dict["curr_ibd"]
        newpos = first_line_dict["newpos"]
        newline = first_line_dict["newline"]
        openfile = first_line_dict["openfile"]
        endtest = first_line_dict["endtest"]
        endline = first_line_dict["endline"]

        sumtab = open(self.output+'.sum.txt', 'w')

        uniqtab = open(self.output+'.uniquq.txt', 'w')

        allagree = open(self.output+'.allpair.txt', 'w')

        allagree_path = "".join([self.output, '.allpair.txt'])

        sumtab.write('chr\tpos\tsource\t{}\n'.format(
            '\t'.join(allcomb.keys())))
        uniqtab.write('chr\tpos\tsource\t{}\n'.format(
            '\t'.join(allcomb.keys())))
        allagree.write('chr\tpos\tsegments\tnpair\tpair.list\n')

        oldallpair = set([])
        while sum(list(map(lambda f: endtest[f], endtest.keys()))) < len(endtest):

            pos = min(newpos.values())

            nowf = self.findkey(pos, newpos)
        #    print('{0} from {1}'.format(str(pos), ' '.join(nowf)))
            for f in nowf:
                CHR = str(newline[f].split('\t')[0])
                if newline[f].split('\t')[4] != 'NA':
                    addibd = set(newline[f].split('\t')[4].split(' '))
                else:
                    addibd = set([])
                if newline[f].split('\t')[5] != 'NA':
                    delibd = set(newline[f].split('\t')[5].split(' '))
                else:
                    delibd = set([])
                curr_ibd[f] = set(set(curr_ibd[f] | addibd) - delibd)
                if len(curr_ibd[f]) > 0:
                    curr_pair[f] = set(
                        map(lambda x: x.split(':')[1], curr_ibd[f]))
                else:
                    curr_pair[f] = set([])
                nextline = openfile[f].readline()
                nextline = nextline.strip()
                if nextline == '' and openfile[f].tell() == endline[f]:
                    endtest[f] = 1
                    newpos[f] = float('inf')
                else:
                    #            nextline = nextline.strip()
                    newpos[f] = int(nextline.split('\t')[1])
                    newline[f] = nextline

            sumrow = list(map(lambda comb: len(
                self.allinter(comb, curr_pair)), allcomb.values()))
            uniqrow = self.get_uniqrow(1, allcomb, combtab, curr_pair)
            newallpair = self.all_agree_pair(curr_pair)
            outpair = []
            for pp in newallpair:
                tool = []
                for f in curr_pair.keys():
                    if pp in curr_pair[f]:
                        tool.append(f)
                outpair.append('{0}:{1}'.format(','.join(tool), pp))
            if len(outpair) == 0:
                outpair = ['NA']
            allagree.write('{0}\t{1}\tNA\t{2}\t{3}\n'.format(
                str(CHR), str(pos), len(newallpair), ' '.join(outpair)))
            oldallpair = set(newallpair)
            sumtab.write('{0}\t{1}\t{2}\t{3}\n'.format(str(CHR), str(
                pos), ",".join(nowf), '\t'.join(map(str, sumrow))))
            uniqtab.write('{0}\t{1}\t{2}\t{3}\n'.format(str(CHR), str(
                pos), ",".join(nowf), '\t'.join(map(str, uniqrow))))

        sumtab.close()
        uniqtab.close()
        allagree.close()

        self.identify_most_pairs(allagree_path)

    def identify_most_pairs(self, allpair_file_path):
        print(f"using file at {allpair_file_path}")
        allpairs_df = pd.read_csv(allpair_file_path, sep="\t")

        max_pairs = allpairs_df["npair"].max()

        allpair_df_max_pairs = allpairs_df[allpairs_df["npair"] == max_pairs]

        start_variant_position_df = allpair_df_max_pairs[(
            allpair_df_max_pairs["pos"] < int(self.variant_pos))]["pos"]

        bp_before_variant = start_variant_position_df.iloc[len(
            start_variant_position_df)-1]

        variant_after_position_df = allpairs_df[(
            allpairs_df["pos"] > int(self.variant_pos))]["pos"]

        bp_after_variant = variant_after_position_df.iloc[0]

        dataframe_to_write = allpair_df_max_pairs[allpair_df_max_pairs["pos"]
                                                  == bp_before_variant]

        write_path = "".join([self.output, ".", str(bp_before_variant),
                              "_", str(bp_after_variant), ".allpair.txt"])

        print(f"writing to {write_path}")

        dataframe_to_write.to_csv(
            write_path, header=False, sep=" ", index=None, mode='a', na_rep='NA')

        self.reformat_file(allpair_file_path, str(
            bp_before_variant), str(bp_after_variant))

    def reformat_file(self, file: str, bp_before_variant: str, bp_after_variant: str):

        shared_segment_file = None

        write_path = "".join([self.output, ".", bp_before_variant,
                              "_", bp_after_variant, ".allpair.new.txt"])

        print(write_path)

        try:
            shared_segment_file = pd.read_csv(file, sep=" ", header=None)

        except FileNotFoundError:
            print("The file {} was not found.".format(file))

        except:
            print("The file {} requires a different delimiter".format(file))

            shared_segment_file = pd.read_csv(file, sep="\t", header=None)

        shared_segment_file = shared_segment_file.dropna()

        new_df = pd.DataFrame()

        for i in range(0, len(shared_segment_file)):

            row = shared_segment_file.iloc[i]

            top_df = row[:4].to_frame().rename({i: "Pairs"}, axis=1)

            if row[4] == NaN:
                continue

            row2 = row[4].split(" ")

            bottom_df = pd.DataFrame(row2, columns=["Pairs"])

            total_df = pd.concat([top_df, bottom_df], axis=0)

            if new_df.empty:
                new_df = total_df

            else:
                new_df = pd.concat([new_df, total_df], axis=0)

        new_df = new_df.reset_index().drop(["index"], axis=1)

        # new_df.to_csv(input("Enter File name: "), na_rep="NA")

        shared_segment_file = shared_segment_file.T.reset_index()
        shared_segment_file = shared_segment_file.drop(["index"], axis=1)

        first_row = shared_segment_file.iloc[0].str.split(
            "\t")

        first_row_df = pd.DataFrame(first_row[0])
        first_row_df = first_row_df.rename(columns={0: "Pairs"})

        shared_segment_file = shared_segment_file.rename(columns={
            0: "Pairs"})

        new_df = pd.concat(
            [first_row_df, shared_segment_file.iloc[1:]], axis=0)

        new_df.to_csv(write_path)
