from collections import ChainMap
from itertools import chain
import pathlib
import re
import sys
from clldutils.misc import slug
from collections import defaultdict

from cldfbench import CLDFSpec, Dataset as BaseDataset

# Linse segment function
def segment(word, segments):
    """
    Use
    """
    if len(word) == 0:
        return [word]
    queue = [[[], word, ""]]
    while queue:
        segmented, current, rest = queue.pop(0)
        if current in segments and not rest:
            return segmented + [current]
        elif len(current) == 1 and current not in segments:
            if rest:
                queue += [[segmented + [current], rest, ""]]
            else:
                return segmented + [current]
        elif current not in segments:
            queue += [[segmented, current[: len(current) - 1], current[-1] + rest]]
        else:
            queue += [[segmented + [current], rest, ""]]


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


def old_chinese(form):
    # take first variant only
    forms = []
    for f in form.split(" // "):
        if f.startswith("! "):
            f = f[2:]
        if " / " in f:
            f = f.split(" / ")[0]
        for r in "[]":
            f = f.replace(r, "")
        for seg in ["*N", "*m", "*k", "*t", "*s", "*C."]:
            f = f.replace(seg + "-", "")
            f = f.replace(seg + "ə-", "")
        f = f.replace("*", "")
        forms += [f]
    return " ".join(forms)


def parse_chinese_text(text):
    stop_symbols = "？，。："
    post_stop = "」】"
    pre_stop = "【「"
    out = []
    stop = False
    merge = False
    for char in text:
        if char in stop_symbols + post_stop:
            out[-1] += char
        elif char in pre_stop:
            out += [char]
            merge = True
        else:
            if merge:
                out[-1] += char
                merge = False
            else:
                out += [char]
    return out


def split_chinese_text(text):
    out = [""]
    stop_symbols = "？，。："
    non_stop_symbols = "【「」】"
    stop = False
    for char in text:
        if char in stop_symbols:
            out[-1] += char
            stop = True
        elif char in non_stop_symbols and stop:
            out[-1] += char
        elif char in non_stop_symbols:
            out[-1] += char
        else:
            if stop:
                out += [char]
                stop = False
            else:
                out[-1] += char
    return out

       



def parse_text(text, chars, args):

    stop_symbols = "？【」，。：】「"

    lines = defaultdict(
            lambda : {
                "Unit": "",
                "Translation": "",
                "Text": "",
                "Gloss": "",
                "Text_Line": [],
                "Gloss_Line": []
                })
    last_item = ""
    for i, row in enumerate(text.readlines()):
        if row[0] == "#":
            unit = row.split(" ")[2].strip()
            lines[unit]["Unit"] = unit
            last_item = ""
        if not row.strip():
            last_item = ""
            pass
        if row.startswith("Text: "):
            lines[unit]["Text"] = [] 
            last_item = "Text"
        if row.startswith("Gloss: "):
            lines[unit]["Gloss"] = []
            last_item = "Gloss"
        if row.startswith("Translation: "):
            lines[unit]["Translation"] = row[row.index(":") + 2 :].strip()
            last_item = ""

        if last_item and row.startswith("  "):
            lines[unit][last_item] += [row[2:].strip()]
            lines[unit][last_item + "_Line"] += [i+1]
    
    full_text = defaultdict(
            lambda : {
                "Unit": "",
                "Translation": "",
                "Text": "",
                "Full_Text": "",
                "Full_Gloss": "",
                "Gloss": "",
                "Phrase": "",
                "Phrase_Number": 0,
                "Number": 0
                })
            
    full_count = 1
    for key, line in sorted(lines.items(), key=lambda x: int(x[0])):
        if not len(lines["Text"]) == len(lines["Gloss"]):
            print(len(lines["Text"]), lines["Text_Lines"], new_texts)
            print(len(lines["Gloss"]), lines["Gloss_Lines"], new_glosses)
            input()
        elif len(lines["Text"]) == len(lines["Gloss"]):
            for i, (new_text, new_gloss) in enumerate(
                    zip(line["Text"], line["Gloss"])):             
                segmented = segment(new_text, chars)
                new_segmented = []
                merge = False
                for char in segmented:
                    if char in stop_symbols or not is_chinese(char):
                        if char in "【「":
                            new_segmented += [char]
                            merge = True
                        else:
                            try:
                                new_segmented[-1] += char
                            except IndexError:
                                new_segmented += [char]
                                merge = True
                    else:
                        if merge:
                            merge = False
                            new_segmented[-1] += char
                        else:
                            new_segmented += [char]
                if len(new_segmented) != len(new_gloss.split()):
                    args.log.info("Problem in {0} / {1}".format(
                        line["Unit"],
                        i+1))
                    print(new_segmented)
                    print(new_gloss)
                full_text[full_count]["Translation"] = line["Translation"]
                full_text[full_count]["Phrase"] = i + 1
                full_text[full_count]["Phrase_Number"] = i + 1
                full_text[full_count]["Gloss"] = new_gloss
                full_text[full_count]["Full_Text"] = line["Text"]
                full_text[full_count]["Full_Gloss"] = line["Gloss"]
                full_text[full_count]["Unit"] = line["Unit"]
                full_text[full_count]["Text"] = new_segmented
                full_text[full_count]["Number"] = full_count
                full_count += 1
    return full_text
            


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

        
        # get the word_idx
        new_word_idx = row["Word"] + "-" + old_chinese(row["OC"])
        if new_word_idx not in word2id:
            word2id[new_word_idx] = "word-{0}".format(word_count)
            word_count += 1
            word_idx = word2id[new_word_idx]
            
            # fill in basic entries
            entries[word_idx]["ID"] = word_idx
            entries[word_idx]["Headword"] = row["Word"] + " " + old_chinese(row["OC"])
            entries[word_idx]["Gloss"] = row["Gloss"]
            entries[word_idx]["Middle_Chinese"] = row["MC"]
            entries[word_idx]["Old_Chinese"] = row["OC"]
            entries[word_idx]["Character"] = row["Word"]
        else:
            word_idx = new_word_idx
        
        # fill word dictionary
        entries[word_idx]["Character_Variants"] += [row["Raw_Word"]]
        entries[word_idx]["Middle_Chinese_Readings"] += row["MC"].split(" // ")
        entries[word_idx]["Old_Chinese_Readings"] += row["OC"].split(" ")
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
            {"name": "Middle_Chinese_Readings", "datatype": "string", "separator": " / "},
            {"name": "Old_Chinese_Readings", "datatype": "string", "separator": " / "},
            {"name": "Glosses", "datatype": "string", "separator": " / "},
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
        
        data = self.raw_dir.read_csv("ad.tsv", delimiter="\t", dicts=True)
        entries, examples = parse_data(data, "ad")
        chars = set(
                [" I ", " II ", " III ", " IV ", " V ", " VI ", " VII ", 
                 " VIII ", " IX ", " X "]
                )
        for entry in entries.values():
            args.writer.objects["EntryTable"].append(entry)
            chars.add(entry["Character"])
        for example in examples.values():
            args.writer.objects["ExampleTable"].append(example)
        
        with open(self.raw_dir / "ad-text.md") as f:
            full_text = parse_text(f, chars, args)

        
        example_test = {}
        for example in examples.values():
            example_test[example["Number"]] = example

        errors = "# Text - Table - Mismatches\n\n"
        for key, example in full_text.items():
            if 40 < key < 60:
                errors += "## Unit {0}, phrase {1} in Text\n\n".format(
                        example["Unit"], key)
                header_len = max(
                        [
                            len(example["Text"]), 
                            len(example_test[example["Number"]]["Analyzed_Word"])])
                header = header_len * ["C"]
                errors += " | ".join(header) + "\n"
                errors += " | ".join([h.replace("C", "---") for h in header]) + "\n"
                ex1 = example["Text"] + header_len * [""]
                ex2 = example_test[example["Number"]]["Analyzed_Word"] + header_len * [""]
                errors += " | ".join(ex1[:header_len]) + "\n"
                errors += " | ".join(ex2[:header_len]) + "\n"
                errors += "\n"

        with open("errors.md", "w") as f:
            f.write(errors)
