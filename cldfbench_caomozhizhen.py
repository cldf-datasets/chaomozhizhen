from collections import ChainMap
from itertools import chain
import pathlib
import re
import sys
from clldutils.misc import slug
from collections import defaultdict

from cldfbench import CLDFSpec, Dataset as BaseDataset

import PIL


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
    stop_symbols = "；？，。："
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
    stop_symbols = "；？，。："
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
    stop_symbols = "；？【」，。：】「"

    lines = defaultdict(
        lambda: {
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
        lambda: {
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
    lookup = {
            "XXXVII【慌者】悔之，": "XXXVII【慌 者】 悔 之，".split(),
            "「XX【為和如何？」": "「XX【為 和 如 何？」".split()
            }
    for key, line in sorted(lines.items(), key=lambda x: int(x[0])):
        if not len(lines["Text"]) == len(lines["Gloss"]):
            print(len(lines["Text"]), lines["Text_Lines"], )
            print(len(lines["Gloss"]), lines["Gloss_Lines"], new_glosses)
            input()
        elif len(lines["Text"]) == len(lines["Gloss"]):
            for i, (new_text, new_gloss) in enumerate(
                    zip(line["Text"], line["Gloss"])):  
                if new_text in lookup:
                    new_segmented = lookup[new_text]
                else:
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
                new_gloss = new_gloss.replace(" ?", "?")
                new_gloss = new_gloss.replace(" ：", ":")
                new_gloss = new_gloss.replace(" ？", "?")
                new_gloss = new_gloss.replace(" 。", ".")
                new_gloss = new_gloss.replace("。", ".")
                new_gloss = new_gloss.replace(" ，", ",")
                new_gloss = new_gloss.replace(" ；", ";")
                new_gloss = new_gloss.replace("[*", "*[")
                new_gloss = new_gloss.replace("† ", "")
                new_gloss = new_gloss.replace("[ *", "*[")
                new_gloss = new_gloss.replace("【 *", "*[")
                new_gloss = new_gloss.replace("*kʰˤeʔ / *kʰˤijʔ", "*kʰˤeʔ/kʰˤijʔ")
                new_gloss = re.sub(r"([^\s【])\*", r"\1 *", new_gloss) 
                new_gloss = re.sub(r"([^\s])【", r"\1 【", new_gloss) 
                if len(new_segmented) != len(new_gloss.split()):
                    args.log.info("Problem in {0} / {1}".format(
                        line["Unit"],
                        i+1))
                    print(new_segmented)
                    print(new_gloss)
                # split new_gloss by asterisk (!)

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


def parse_oc(info, text, chars):
    lookup = {
            "*C.qur ! // *[ts]əʔ // *tsəʔ": "*C.qur // *tsəʔ",
            "! *[ts]əʔ // *tsəʔ": "*tsəʔ",
            "*[d]eʔ // ! *kˤa(ʔ)-s // *kˤaʔ-s": "*[d]eʔ // *kˤa(ʔ)-s",
            "dajH bju // bju // pju": "dajH bju",
            "*lˤa[t]-s // ! *ba // *[b]a // *p(r)a": "*lˤa[t]-s // *ba",
            "*lˤa[t]-s // ! *ba // *[b]a // *p(r)a": "*lˤa[t]-s // *ba",
            "*C.qur // ! *[ts]əʔ // *tsəʔ": "*C.qur // *tsəʔ",
            "*tə // ! *N-kˤre[n] // *kˤre[n] // *kˤre[n]": "*tə // N-ˤre[n]",
            "*pʰi[t] // ! *ba // *[b]a // *p(r)a": "*pʰi[t] // *ba",
            "*C.qˤoŋ // ! *[ts]əʔ // *tsəʔ": "*C.qˤoŋ // *tsəʔ",
            }
    if text in lookup:
        text = lookup[text]
    if len(chars) > 1:
        if text.startswith("!"):
            text = [text.split(" // ")[0][2:]]
        elif " // " in text:
            text = text.split(" // ")
        elif " / " in text:
            text = text.split(" / ")
        elif " " in text:
            text = text.split(" ")
        else:
            text = [text]
        text = [old_chinese(t) for t in text]
    else:
        if " // " in text:
            text = text.split(" // ")[0]
        elif " / " in text:
            text = text.split(" / ")[0]
        elif " " in text:
            text = text.replace("!", "").strip().split(" ")[0]
        text = [old_chinese(text)]
        
    return "_".join(text)


def parse_data(data, text):
    examples = defaultdict(
        lambda: {
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
            "Cognacy": "",
            "Character_IDS": [],
            "Text_Unit": [],
            "IDS_in_Source": [],
        })
    entries = defaultdict(
        lambda: {
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
            "Example_IDS": []
        })

    slip_number, phrase_number, word_number = 0, 0, 0
    slip_idx, phrase_idx, word_idx = "", "", ""
    previous_slip, previous_phrase = "", ""
    word2id, word_count = {}, 1
    characters = {}
    for row in data:
        if previous_phrase != row["Phrase_ID"]:
            phrase_number += 1
            phrase_idx = row["Phrase_ID"]
            previous_phrase = row["Phrase_ID"]

            # fill in entries
            examples[phrase_idx]["ID"] = phrase_idx
            examples[phrase_idx]["Number"] = phrase_number

        # get the word_idx
        new_word_idx = row["Word"] + "-" + parse_oc(row["ID"], row["OC"], row["Word"])
        if new_word_idx not in word2id:
            word2id[new_word_idx] = "word-{0}".format(word_count)
            word_count += 1
            word_idx = word2id[new_word_idx]

            # fill in basic entries
            entries[word_idx]["ID"] = word_idx
            entries[word_idx]["Headword"] = row["Word"] + " " + parse_oc(
                    row["ID"], row["OC"], row["Word"])
            entries[word_idx]["Gloss"] = row["Gloss"]
            entries[word_idx]["Middle_Chinese"] = parse_oc(
                    row["ID"], row["MC"], row["Word"])
            entries[word_idx]["Old_Chinese"] = parse_oc(
                    row["ID"], row["OC"], row["Word"])
            entries[word_idx]["Character"] = row["Word"]
        else:
            word_idx = word2id[new_word_idx]

        # fill word dictionary
        entries[word_idx]["Character_Variants"] += [row["Raw_Word"]]
        entries[word_idx]["Middle_Chinese_Readings"] += [
                parse_oc(row["ID"], row["MC"], row["Word"])]
        entries[word_idx]["Old_Chinese_Readings"] += [
                parse_oc(row["ID"], row["MC"], row["Word"])]
        entries[word_idx]["Glosses"] += [row["Gloss"]]
        entries[word_idx]["Example_IDS"] += [phrase_idx]

        # fill text examples
        # check for double readings
        examples[phrase_idx]["Old_Chinese_Reading"] += [parse_oc(
            row["ID"], row["OC"], row["Word"])]
        examples[phrase_idx]["Middle_Chinese_Reading"] += [parse_oc(
            row["ID"], row["MC"], row["Word"])]
        examples[phrase_idx]["Primary_Text"] += [row["Raw_Word"]]
        examples[phrase_idx]["Analyzed_Word"] += [row["Word"]]
        examples[phrase_idx]["Gloss"] += [row["Gloss"].strip().replace(" ", ".")]
        examples[phrase_idx]["Word_IDS"] += [word_idx]
        examples[phrase_idx]["Text_Unit"] = row["Text_Unit"]
        examples[phrase_idx]["IDS_in_Source"] += [row["ID"]]
        
        adids = row["AD_IDS"].split()
        adims = row["AD_Images"].split()
        sbids = row["SB_IDS"].split()
        sbims = row["SB_Images"].split()
        charids = []
        if adids:
            for adid, adim, w in zip(adids, adims, row["Word"]):
                charid = "{0}/{1}".format(
                        adim, adid.replace("r", "/"))
                charids += [charid]
                characters[charid] = w
        elif sbids:
            for sbid, sbim, w in zip(sbids, sbims, row["Word"]):
                charid = "{0}/{1}".format(
                        sbim, sbid.replace("r", "/"))
                charids += [charid]
                characters[charid] = w
        else:
            charids += ["0"]
        examples[phrase_idx]["Character_IDS"] += [" ".join(charids)]

    # refine data
    for example in examples.values():
        example["Primary_Text"] = " ".join(example["Primary_Text"])
    for idx, entry in entries.items():
        if not entry["ID"]:
            print("!", idx, entry)
            input()
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

    return entries, examples, characters


def join_parts(texta, textb):
    i, j = 0, 0
    out = []
    while i < len(texta):
        char = texta[i]
        new_out = []
        for k, part in enumerate(char.split("_")):
            new_out += [textb[j + k]]
        out += [new_out]
        j += k
        j += 1
        i += 1
    return ["_".join(p) for p in out]


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
            "Middle_Chinese",
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
            {"name": 'Text_Unit', "datatype": "string"},
            'Text_ID',
            {"name": "Word_IDS", "datatype": "string", "separator": " "},
            {"name": "IDS_in_Source", "datatype": "integer", "separator": " "},
            {"name": "Middle_Chinese_Reading", "datatype": "string", "separator": " "},
            {"name": "Old_Chinese_Reading", "datatype": "string", "separator": " "},
            {"name": "Old_Chinese_Reading_2", "datatype": "string", "separator": " "},
            {"name": "Analyzed_Word_2", "datatype": "string", "separator": " "},
            {"name": "Character_IDS", "datatype": "string", "separator": " "},
            "Cognacy"
        )

        args.writer.cldf.add_table(
                "images.csv",
                "ID",
                "Path",
                {"name": "Height", "datatype": "integer"},
                {"name": "Width", "datatype": "integer"}
                )

        args.writer.cldf.add_table(
            "characters.csv", 
            "ID", 
            "Name",
            "Rectangle",
            "Image"
            )
        #args.writer.cldf.add_foreign_key("ExampleTable", "Character_IDS",
        #                                 "characters.csv", "ID")

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
                'Glottocode': ''
            }
        )
        

        data = self.raw_dir.read_csv("ad.tsv", delimiter="\t", dicts=True)
        entries, examples, characters = parse_data(data, "ad")

        files = [row[0] for row in self.raw_dir.read_csv("files.csv")]

        for f in files:
            args.log.info("Analyzing Image File {0}.jpg".format(f))
            with PIL.Image.open(self.raw_dir / "media" / "{0}.jpg".format(f)) as img:
                width, height = img.size
                args.writer.objects["images.csv"].append(
                        {
                            "ID": f,
                            "Path": f + ".jpg",
                            "Width": width,
                            "Height": height}
                        )

            dt = self.raw_dir.read_csv(f + ".csv", delimiter=",", dicts=True)
            for row in dt:
                if row["QUOTE_TRANSCRIPTION"].strip() != "full":
                    idx = f + "/" + row["QUOTE_TRANSCRIPTION"].replace(
                            "r", "/")
                    if idx not in characters:
                        args.log.info("missing idx '" + idx + "'")
                    else:
                        args.writer.objects["characters.csv"].append(
                                {
                                    "ID": idx,
                                    "Name": characters[idx],
                                    "Rectangle": row["ANCHOR"],
                                    "Image": f
                                    })

        chars = set(
            [" I ", " II ", " III ", " IV ", " V ", " VI ", " VII ", 
            " VIII ", " IX ", " X ", " XX ", " XXXVII【 "]
        )


        with open(self.raw_dir / "ad-text.md") as f:
            full_text = parse_text(f, chars, args)

        example_test = {}
        for example in examples.values():
            example_test[example["Number"]] = example


        for entry in entries.values():
            args.writer.objects["EntryTable"].append(entry)
            chars.add(entry["Character"])
        ecount = 0
        for example in examples.values():
            num = example["Number"]
            ocr = full_text[num]["Gloss"].split(" ")
            aw = full_text[num]["Text"]
            try:
                ocr = join_parts(example["Old_Chinese_Reading"], ocr)
            except IndexError:
                ecount += 1
                print(ecount)
                print(example["ID"])
                print(num)
                print(ocr)
                print(example["Old_Chinese_Reading"])
                print("---")
            example["Old_Chinese_Reading_2"] = ocr
            example["Analyzed_Word_2"] = aw
            args.writer.objects["ExampleTable"].append(example)

        errors = "# Text - Table - Mismatches\n\n"
        #for key, example in full_text.items():
        #    if 350 < key < 499:
        #        print("Processing key:", key)  # Print the key being processed
        #        errors += "## Unit {0}, phrase {1} in Text\n\n".format(
        #            example["Unit"], key)
        #        header_len = max(
        #            [
        #                len(example["Text"]),
        #                len(example_test[example["Number"]]["Analyzed_Word"])
        #            ])
        #        header = header_len * ["C"]
        #        errors += " | ".join(header) + "\n"
        #        errors += " | ".join([h.replace("C", "---") for h in header]) + "\n"
        #        ex1 = example["Text"] + header_len * [""]
        #        ex2 = example_test[example["Number"]]["Analyzed_Word"] + header_len * [""]
        #        errors += " | ".join(ex1[:header_len]) + "\n"
        #        errors += " | ".join(ex2[:header_len]) + "\n"
        #        errors += "\n"

        # Check file writing
        print("Before file writing")
        # ... (remaining code)
        # ... (previous code)

        with open("errors.md", "w") as f:
            f.write(errors)
        print("After file writing")


