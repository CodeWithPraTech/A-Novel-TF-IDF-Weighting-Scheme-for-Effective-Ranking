#!/usr/bin/env python3

""" -- INDEXING --

There are four types of files, starting with:
fb, fr, ft, la.
Each file contains lots of documents.

Each document is inside a <doc> tag which contains many
children tags which enclose different fields for each document.

We are indexing two fields from each document, namely: DOCNO, TEXT.
1. DOCNO is inside <docno> tag in all four types of files.
2. TEXT  is inside <text>  tag in all four types of files.

- We are storing DOCNO as StringField (as it is not tokenized).
- We are NOT storing TEXT but indexing it as TextField (as it is tokenized),
    and we are also storing the TermVectors for this field.

NOTE:
- <docno> tag is present in ALL documents, but some dont contain <text> tag.
- We ignore documents with no TEXT i.e. no <text> tag.
- We ignore information inside all other tags for all files.
"""


import os
from bs4 import BeautifulSoup
from collections import Counter

import lucene
from java.io import File
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.analysis.en import EnglishAnalyzer
from org.apache.lucene.index import IndexWriter, IndexWriterConfig
from org.apache.lucene.store import FSDirectory
import org.apache.lucene.document as document
from org.apache.lucene.analysis.tokenattributes import CharTermAttribute


lucene.initVM()

# Make sure index-dir directory is removed before re-indexing
indexPath = File("index-dir/").toPath()
indexDir = FSDirectory.open(indexPath)
analyzer = StandardAnalyzer()
writerConfig = IndexWriterConfig(analyzer)
writer = IndexWriter(indexDir, writerConfig)


# def compute_term_frequencies(text, analyzer):
#     term_freqs = Counter()
#     token_stream = analyzer.tokenStream("TEXT", text)
#     token_stream.reset()
#     while token_stream.incrementToken():
#         term = token_stream.getAttribute(CharTermAttribute.class_).toString()
#         term_freqs[term] += 1
#     token_stream.end()
#     token_stream.close()
#     return term_freqs

def compute_average_term_frequency(term_freqs):
    total_terms = sum(term_freqs.values())
    avg_term_freq = total_terms / len(term_freqs) if term_freqs else 0
    return avg_term_freq


# Make new IndexableFieldType that stores term vectors (we are doing this for TEXT field)
termvec_store_TextField = document.FieldType(document.TextField.TYPE_NOT_STORED)
termvec_store_TextField.setStoreTermVectors(True)


def indexDoc(docno, text):
    # Calculate term frequencies
    # terms = text.split()
    # term_freqs = Counter(terms)
    # total_terms = sum(term_freqs.values())
    # avg_term_freq = total_terms / len(term_freqs) if len(term_freqs) > 0 else 0

    # doc = document.Document()
    # doc.add(document.Field("DOCNO", docno, document.StringField.TYPE_STORED))
    # doc.add(document.Field("TEXT", text, termvec_store_TextField))
    # doc.add(document.IntPoint("DLEN", len(text)))
    # doc.add(document.FloatPoint("AvTF",avg_term_freq))

    # writer.addDocument(doc)
    analyzer = StandardAnalyzer()

    # Compute term frequencies using the analyzer
    # term_freqs = compute_term_frequencies(text, analyzer)
    # avg_term_freq = compute_average_term_frequency(term_freqs)

    # Create and add the document
    doc = document.Document()
    doc.add(document.Field("DOCNO", docno, document.StringField.TYPE_STORED))
    doc.add(document.Field("CONTENT", text, document.TextField.TYPE_STORED))
    doc.add(document.Field("VECTOR",  text, termvec_store_TextField))
    doc.add(document.StoredField("DLEN", len(text)))
    # doc.add(document.IntPoint("DLEN", len(text)))
    #doc.add(document.StoredField("AVTF", avg_term_freq))

    # Compute and add document length
    # doc_length = sum(term_freqs.values())
    # doc.add(document.StoredField("DLEN", doc_length))

    writer.addDocument(doc)


doc_count = 1
avg_document_len = 0
for filename in os.listdir("trec678rb/documents"):
    with open("trec678rb/documents/" + filename, "r", encoding="ISO-8859-1") as fp:
        soup = BeautifulSoup(fp, "html.parser")
        docs = soup.find_all("doc")
        # Loop through each DOC and process it
        for i, doc in enumerate(docs, 1):
            # Extract the DOCNO field
            docno_tag = doc.find("docno")
            docno = docno_tag.get_text(strip=True) if docno_tag else "No DOCNO"
            
            # Remove the DOCNO tag and its associated newline
            if docno_tag:
                docno_tag.decompose()
                # Remove the newline after the DOCNO tag
                if docno_tag.next_element and isinstance(docno_tag.next_element, str):
                    next_element = docno_tag.next_element
                    if '\n' in next_element:
                        doc.next_element.replace_with(next_element.replace('\n', '', 1))
            
            # Extract the remaining content without tags
            content = doc.get_text(separator="").strip()
            print(f"Indexing {doc_count} -- {docno} - ", end='')
            indexDoc(docno,content)
            print("Done!")
            doc_count += 1
            
            # Print the extracted DOCNO and the rest of the content
            # print(f"Document {i} DOCNO: {docno}\n")
            # print(f"Document {i} Content:\n{content}\n")
            # print("-" * 50)


                
# avg_document_len = avg_document_len/doc_count
# doc = document.Document()
# doc.add(document.StoredField("ADL",avg_document_len))
# doc.add(document.StoredField("TotalDocNo",doc_count))
# writer.addDocument(doc)

writer.close()


