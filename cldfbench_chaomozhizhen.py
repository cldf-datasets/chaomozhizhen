from collections import ChainMap
from itertools import chain
import pathlib
import re
import sys
from clldutils.misc import slug
from collections import defaultdict

from cldfbench import CLDFSpec, Dataset as BaseDataset


# function is also in sinopy, for convenience reused here
def is_chinese(name):
    """
    Check if a symbol is a Chinese character.

    Note
    ----

    Taken from http://stackoverflow.com/questions/16441633/python-2-7-test-if-characters-in-a-string-are-all-chinese-characters
    """
    if not name:
        return False
    for ch in name:
        ordch = ord(ch)
        if not (0x3400 <= ordch <= 0x9fff) and not (0x20000 <= ordch <= 0x2ceaf) \
                and not (0xf900 <= ordch <= ordch) and not (0x2f800 <= ordch <= 0x2fa1f): 
                return False
    return True


def parse_data(data, text):
    examples = defaultdict(
            lambda : {
            "ID": "",
            "Number": 0,
            "Slip_ID": "",
            "Slip_Number": 0,
            "Text_ID": text,
            "Language_ID": "OldChinese",
            "Primary_Text": [],
            "Analyzed_Word": [],
            "Old_Chinese_Reading": [],
            "Middle_Chinese_Reading": [],
            "Gloss": [],
            "Word_IDS": [],
            "Cognacy": ""})
    entries = defaultdict(
            lambda : {
                "ID": "",
                "Language_ID": "OldChinese",
                "Headword": "",
                "Character": "",
                "Character_Variants": [],
                "Middle_Chinese": "",
                "Old_Chinese": "",
                "Gloss": "",
                "Glosses": [],
                "Middle_Chinese_Readings": [],
                "Old_Chinese_Readings": [],
                "Example_IDS": []})
    
    slip_number, phrase_number, word_number = 0, 0, 0
    slip_idx, phrase_idx, word_idx = "", "", ""
    previous_slip, previous_phrase = "", ""
    word2id, word_count = {}, 1
    for row in data:
        if previous_slip != row["Slip_ID"]:
            word_number += 1
            slip_number += 1
            slip_idx = text + "-" + row["Slip_ID"]
            previous_slip = row["Slip_ID"]
        if previous_phrase != row["Phrase_ID"]:
            phrase_number += 1
            phrase_idx = text + "-" + row["Slip_ID"] + "-" + row["Phrase_ID"]
            previous_phrase = row["Phrase_ID"]
            # fill in entries
            examples[phrase_idx]["ID"] = phrase_idx
            examples[phrase_idx]["Slip_ID"] = slip_idx
            examples[phrase_idx]["Number"] = phrase_number
            examples[phrase_idx]["Slip_Number"] = slip_number


        if row["Word"] not in word2id:
            word2id[row["Word"]] = "word-{0}".format(word_count)
            word_count += 1
            word_idx = word2id[row["Word"]]
            
            # fill in basic entries
            entries[word_idx]["ID"] = word_idx
            entries[word_idx]["Headword"] = row["Word"] 
            entries[word_idx]["Gloss"] = row["Gloss"]
            entries[word_idx]["Middle_Chinese"] = row["MC"]
            entries[word_idx]["Old_Chinese"] = row["OC"]
            entries[word_idx]["Character"] = row["Word"]
        
        # fill word dictionary
        entries[word_idx]["Character_Variants"] += [row["Raw_Word"]]
        entries[word_idx]["Middle_Chinese_Readings"] += row["OC"].split(" // ")
        entries[word_idx]["Old_Chinese_Readings"] += row["MC"].split(" ")
        entries[word_idx]["Glosses"] += [row["Gloss"]]
        entries[word_idx]["Example_IDS"] += [phrase_idx]

        # fill text examples
        examples[phrase_idx]["Old_Chinese_Reading"] += [row["OC"].split(" // ")[0]]
        examples[phrase_idx]["Middle_Chinese_Reading"] += [row["MC"].split(" ")[0]]
        examples[phrase_idx]["Primary_Text"] += [row["Raw_Word"]]
        examples[phrase_idx]["Analyzed_Word"] += [row["Word"]]
        examples[phrase_idx]["Gloss"] += [row["Gloss"].strip().replace(" ", ".")]
        examples[phrase_idx]["Word_IDS"] += [word_idx]
    
    # refine data
    for example in examples.values():
        example["Primary_Text"] = " ".join(example["Primary_Text"])
    for entry in entries.values():
        entry["Middle_Chinese_Readings"] = sorted(
                set(entry["Middle_Chinese_Readings"]),
                key=lambda x: entry["Middle_Chinese_Readings"].count(x),
                reverse=True)
        entry["Old_Chinese_Readings"] = sorted(
                set(entry["Old_Chinese_Readings"]),
                key=lambda x: entry["Old_Chinese_Readings"].count(x),
                reverse=True)
        entry["Glosses"] = sorted(
                set(entry["Glosses"]),
                key=lambda x: entry["Glosses"].count(x),
                reverse=True)


                
    
    return entries, examples




class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "chaomozhizhen"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(
                dir=self.cldf_dir, module='Generic',
                metadata_fname='cldf-metadata.json'
                )

        
    def cmd_download(self, args):
        """
        Download files to the raw/ directory. You can use helpers methods of `self.raw_dir`, e.g.

        >>> self.raw_dir.download(url, fname)
        """
        pass

        
    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.
        """
        
        # language table (Old Chinese)
        args.writer.cldf.add_component('LanguageTable')
        # entries, links to examples
        args.writer.cldf.add_component(
            "EntryTable",
            {"name": "Segments", "datatype": "string", "separator": " "},
            {"name": "Sound_Classes", "datatype": "string", "separator": " "},
            "Character",
            "Middle Chinese",
            "Old_Chinese",
            {"name": "Middle_Chinese_Readings", "datatype": "string", "separator": " "},
            {"name": "Old_Chinese_Readings", "datatype": "string", "separator": " "},
            {"name": "Glosses", "datatype": "string", "separator": " "},
            {"name": "Example_IDS", "datatype": "string", "separator": " "},
            )
        
        # examples (glossed text)
        args.writer.cldf.add_component(
            'ExampleTable',
            {"name": 'Number', "datatype": "integer"},
            'Slip_ID',
            {'name': 'Slip_Number', 'datatype': 'integer'},
            'Text_ID',
            {"name": "Word_IDS", "datatype": "string", "separator": " "},
            {"name": "Middle_Chinese_Reading", "datatype": "string", "separator": " "},
            {"name": "Old_Chinese_Reading", "datatype": "string", "separator": " "},
            "Cognacy"

        )


        args.writer.cldf.add_table('texts.csv', 'ID', 'Title')

        args.writer.cldf.add_foreign_key(
                'ExampleTable', 'Text_ID', 'texts.csv', 'ID'
                )
        args.writer.cldf.add_foreign_key(
                "EntryTable", "Example_IDS", "examples.csv", "ID")
        
        # fill language table
        args.writer.objects['LanguageTable'].append(
                {
                    'ID': 'OldChinese', 
                    'Name': 'Old Chinese', 
                    'Glottocode': ''}
                )
        
        texts = ["ad"]

        for text in texts:
            args.log.info('reading text {0}'.format(text))
            data = self.raw_dir.read_csv(text+".tsv", delimiter="\t", dicts=True)
            entries, examples = parse_data(data, text)
            for entry in entries.values():
                args.writer.objects["EntryTable"].append(entry)
            for example in examples.values():
                args.writer.objects["ExampleTable"].append(example)

