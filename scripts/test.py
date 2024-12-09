from pycldf import Dataset
import json

ds = Dataset.from_metadata("../cldf/cldf-metadata.json")

words = ds.objects("EntryTable")
phrases = ds.objects("ExampleTable")

text = "<html>" 
text += "<style>"
text += """
table.gloss {
  border-bottom: 2px solid black;
  }
table.gloss td {
  padding: 5px;
}
div.slip {
  background-color: lightyellow;
  padding: 5px;
  margin-top: 5px;
  margin-right: 5px;
  display: table-cell;
  border: 2px solid black;
}
.fragment {
  width: 20px;
  display: table-cell;
}
table.entry {
  border: 2px solid crimson;
}
table.entry.td {
  border: 2px solid blue;
  text-wrap: pretty;
}
"""

text += "</style><body>"

WORDS = {}
for word in words:
    WORDS[word.cldf.id] = word.data

slip = ""
for phrase in phrases:
    slip_ = phrase.data["Slip_ID"].replace("ad", "slip")
    ptext = ""
    if slip != slip_:
        if slip:
            text += "</div>\n\n"
            text += '<div class="fragment"></div>'
            text += '<div class="slip" id="' + slip + '">check</div>\n\n'
        slip = slip_
        ptext += "<h2>Bamboo Slip {0}</h2>\n".format(slip)
        ptext += '<div class="slip">'
    ptext += '<table class="gloss">'
    ptext += "<tr><th>Text</th>"
    for i, word in enumerate(phrase.cldf.analyzedWord):
        ptext += "<td>" + '<span class="word" onmouseover="lookup(this)"' + 'data-word_id="' \
                + phrase.data["Word_IDS"][i] + '" data-phrase_id="' \
                + slip_ + \
                '">' + word + "</span></td>"
    ptext += "</tr>\n"
    ptext += "<tr><th>Gloss</th>"
    for i, word in enumerate(phrase.cldf.gloss):
        ptext += "<td><i>" + word + "</i></td>"
    ptext += "</tr>\n"
    ptext += "<tr><th>Middle Chinese</th>"
    for i, word in enumerate(phrase.data["Middle_Chinese_Reading"]):
        ptext += "<td><i>" + word + "</i></td>"
    ptext += "</tr>\n"
    ptext += "<tr><th>Old Chinese</th>"
    for i, word in enumerate(phrase.data["Old_Chinese_Reading"]):
        if word:
            ptext += "<td>" + word + "</td>"
        else:
            ptext += "<td>" + "?" + "</td>"
    ptext += "</tr>\n"
    ptext += "</table>\n\n"
    text += ptext + "\n"
text += "</body>"

text += "<script>let WORDS = " + json.dumps(WORDS, indent=2) + ';\n</script>'

text += """
<script>
function lookup(node) {
  let node_ = document.getElementById(node.dataset["phrase_id"]);
  let i; 
  let all_words = document.getElementsByClassName("word");
  for (i = 0; i < all_words.length; i += 1) {
    all_words[i].parentNode.style.backgroundColor = "lightyellow";
  }
  node.parentNode.style.backgroundColor = "lightgray";
  let text = "<table class='entry'>";
  let key, itm;
  for (key in WORDS[node.dataset["word_id"]]) {
    itm = WORDS[node.dataset["word_id"]][key];
    if (itm !== null) {
      text += "<tr><th>" + key + "</th><td>";
      console.log(key, itm);
      if (typeof itm == "object") {
        text += itm.join(" ");
      }
      else {
        text += itm;
      }
      text += "</td></tr>";
    }
  }
  node.style.display = "table-cell"
  text += "</table>";
  node_.innerHTML = text;
  
}

</script>"""
text += "</html>"
with open("example.html", "w") as f:
    f.write(text)

        
