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

        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component(
            "EntryTable",
            "Character",
            "Middle Chinese",
            "Old_Chinese",
            {"name": "Gloss", "datatype": "string"},
            {"name": "Example_ID", "datatype": "string"},
            )

        args.writer.cldf.add_component(
            'ExampleTable',
            {"name": 'Number', "datatype": "integer"},
            'Slip_ID',
            {'name': 'Slip_Number', 'datatype': 'integer'},
            'Text_ID',
            {"name": "Word_IDS", "datatype": "string", "separator": " "},
            #{"name": "Word_Forms", "datatype": "string", "separator": r"\t"},
        )


        args.writer.cldf.add_table('texts.csv', 'ID', 'Title')

        args.writer.cldf.add_foreign_key(
                'ExampleTable', 'Text_ID', 'texts.csv', 'ID'
                )
        args.writer.cldf.add_foreign_key(
                "EntryTable", "Example_ID", "examples.csv", "ID")
        
        args.writer.objects['LanguageTable'].append(
                {
                    'ID': 'OldChinese', 
                    'Name': 'Old Chinese', 
                    'Glottocode': ''}
                )

        # add a form table
        args.writer.cldf.add_component(
            "FormTable",
            {"name": "Character", "datatype": "string"},
            {"name": "Entry_IDS", "datatype": "string", "separator": " "},
            {"name": "Middle_Chinese_Forms", "datatype": "string", "separator": " // "},
            {"name": "Old_Chinese_Forms", "datatype": "string", "separator": " // "},
            {"name": "Glosses", "datatype": "string", "separator": " // "},
            )
    
        words = defaultdict(
                lambda : {
                    "Glosses": [], 
                    "Phrase_IDS": [],
                    "Word_Numbers": [],
                    "Word_Forms": [],
                    "Middle_Chinese": [],
                    "Old_Chinese": [],
                    "Word_IDS": []
                    })
        word2id = {}
        data = self.raw_dir.read_csv("ad.tsv", dicts=True, delimiter="\t")
        phrase = ""
        word_count = 1
        phrase_count = 1

        phrases = defaultdict(lambda : {
            "Word_IDS": [],
            "Word_Forms": [],
            "Raw_Forms": [],
            "Gloss": []
            })
        for i, row in enumerate(data):

            idx = row["ID"]
            if phrase != row["Phrase_ID"]:
                word_number = 1
                phrase = row["Phrase_ID"]
                phrase_idx = "ad-" + str(phrase)
                phrases[phrase_idx]["Slip_ID"] = row["Slip_ID"]
                phrases[phrase_idx]["Phrase_Number"] = phrase_count
                phrase_count += 1
            if not row["Word"] in word2id:
                word_idx = word_count
                word2id[row["Word"]] = word_idx
                word_count += 1
                words[word_idx]["Character"] = row["Word"]
            else:
                word_idx = word2id[row["Word"]]
            
            # fill in data on phrases
            phrase_idx = "ad-" + str(phrase)
            phrases[phrase_idx]["Word_IDS"] += ["word-ad-" + str(idx)]
            phrases[phrase_idx]["Word_Forms"] += [row["Word"]]
            phrases[phrase_idx]["Gloss"] += [row["Gloss"].replace(" ", "_")]
            phrases[phrase_idx]["Raw_Forms"] += [row["Raw_Word"]]
            
            words[word_idx]["Glosses"] += [row["Gloss"]]
            words[word_idx]["Word_Forms"] += [row["Raw_Word"]]
            words[word_idx]["Middle_Chinese"] += row["MC"].split()
            words[word_idx]["Old_Chinese"] += [
                    x.strip("!") for x in row["OC"].split(" // ")]
            words[word_idx]["Word_Numbers"] += [word_number]
            words[word_idx]["Phrase_IDS"] += [phrase]
            words[word_idx]["Word_IDS"] += [idx]

            args.writer.objects["EntryTable"].append({
                "ID": "ad-"+str(i+1),
                "Language_ID": "OldChinese",
                "Headword": row["Word"],
                "Middle_Chinese": row["MC"],
                "Old_Chinese": row["OC"],
                "Gloss": row["Gloss"],
                "Character": row["Raw_Word"],
                "Example_ID": "ad-{0}".format(phrase)
                })
        for word, values in sorted(words.items()):
            args.writer.objects["FormTable"].append({
                "ID": "word-ad-{0}".format(word),
                "Language_ID": "OldChinese",
                "Form": values["Old_Chinese"][0],
                "Character": values["Character"],
                "Entry_IDS": values["Word_IDS"],
                "Middle_Chinese_Forms": values["Middle_Chinese"],
                "Old_Chinese_Forms": values["Old_Chinese"],
                })
        for phrase, values in sorted(
                phrases.items(), key=lambda x: int(x[1]["Phrase_Number"])):
            args.writer.objects["ExampleTable"].append({
                "ID": phrase,
                "Number": values["Phrase_Number"],
                "Language_ID": "OldChinese",
                "Slip_ID": values["Slip_ID"],
                "Slip_Number": values["Slip_ID"],
                "Text_ID": "ad",
                "Word_IDS": values["Word_IDS"],
                "Primary_Text": " ".join(values["Raw_Forms"]),
                "Analyzed_Word": values["Word_Forms"],
                "Gloss": values["Gloss"],
                })


        print(phrases)

            #    poems_ = f.read().split("\n\n\n\n")
            #    for poem in poems_:
            #        in_poem = False
            #        for row in poem.split("\n"):
            #            if row.startswith("?"):
            #                pass

            #            elif row.strip() and row[0].isdigit():
            #                name = row
            #                in_poem = True
            #                stanza = 1
            #                P[name] = {stanza: []}
            #            elif in_poem:
            #                if row.strip():
            #                    P[name][stanza] += [row.strip()]
            #                else:
            #                    stanza += 1
            #                    P[name][stanza] = []
        #args.log.info("parsed data")
        #
        #poems = {}
        #idx = 1
        #entries = defaultdict(list)
        #for i, name in enumerate(P):
        #    poem_id, poem_name = name.split(". ")
        #    args.writer.objects["poems.csv"].append({
        #        "ID": poem_id,
        #        "Title": poem_name,
        #        })
        #    args.log.info("Analyzing poem {0} / {1}".format(i+1, name))
        #    for stanza in P[name]:
        #        for i, row in enumerate(P[name][stanza]):
        #            for j, (
        #                    phrase, chars, rhyme_words, rhyme_word_idxs,
        #                    rhyme_idxs
        #                    ) in enumerate(parse_line(row)):
        #                for word in rhyme_words:
        #                    entries[word] += [idx]
        #                args.writer.objects["ExampleTable"].append({
        #                    "ID": idx,
        #                    "Primary_Text": phrase,
        #                    "Analyzed_Word": chars,
        #                    "Gloss": "",
        #                    "Poem_ID": poem_id,
        #                    "Stanza_Number": stanza,
        #                    "Line_Number": i+1,
        #                    "Phrase_Number": j+1,
        #                    "Language_ID": "OldChinese",
        #                    "Rhyme_Words": rhyme_words,
        #                    "Rhyme_Word_Indices": rhyme_word_idxs ,
        #                    "Rhyme_IDS": ["{0}-{1}".format(
        #                        poem_id, rid) for rid in rhyme_idxs]
        #                    })
        #                idx += 1
        #for i, (entry, occs) in enumerate(entries.items()):
        #    args.writer.objects["EntryTable"].append({
        #        "ID": i+1,
        #        "Language_ID": "OldChinese",
        #        "Headword": entry,
        #        "Example_IDS": occs
        #        })



        # output

        #args.writer.cldf.properties['dc:creator'] = "Johann-Mattis List" 

        #language = {
        #    'ID': "OldChinese",
        #    'Name': "Old Chinese",
        #    'Glottocode': "",
        #}
        #args.writer.objects['LanguageTable'] = [language]

        #args.writer.objects['EntryTable'] = entries
        #args.writer.objects['SenseTable'] = senses
        #args.writer.objects['ExampleTable'] = examples
        #args.writer.objects['media.csv'] = media
