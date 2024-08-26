
#!usr/bin/env python3
# import scorer
import os
import xml.etree.ElementTree as ET

try:
    os.remove("robust_rank_file")
except FileNotFoundError:
    pass

try:
    os.remove("trec678_rank_file")
except FileNotFoundError:
    pass


robust_topics = ET.parse('trec678rb/topics/robust.xml').getroot()
robust_rank_file = open("robust_rank_file", "a")


trec678_topics = ET.parse('trec678rb/topics/trec678.xml').getroot()
trec678_rank_file = open("trec678_rank_file", "a")

field = "VECTOR"

import lucene
import numpy as np

from java.io import File

from org.apache.lucene.store import FSDirectory
from org.apache.lucene.search import IndexSearcher
from org.apache.lucene.analysis.standard import StandardAnalyzer
from org.apache.lucene.index import DirectoryReader
from org.apache.lucene.queryparser.classic import QueryParser, ParseException
from org.apache.lucene.search import BooleanQuery
from org.apache.lucene.search import BooleanClause
from org.apache.lucene.search.similarities import BooleanSimilarity
from org.apache.lucene.index import Term
from org.apache.lucene.search import TermQuery
from org.apache.lucene.util import BytesRef
from org.apache.lucene.analysis.en import EnglishAnalyzer
from java.io import StringReader
from org.apache.lucene.analysis.tokenattributes import CharTermAttribute
from org.apache.lucene.search.similarities import BM25Similarity




# Relative Intra-document TF (RITF)
# @param tf: TF(t, D) -> term frequency of t in document D
# @param avgtf: Avg.TF(D) -> average term frequency of document D
# @param c: free parameter (default is 1)
def ritf(tf, avgtf, c=1):
    return np.log2(1 + tf) / np.log2(c + avgtf)


# Length regularized TF (LRTF)
# @param tf: TF(t, D) -> term frequency of t in document D
# @param adl: ADL(C) -> average document length in collection C
# @param dl: len(D) -> length of document D
def lrtf(tf, adl, dl):
    return tf * np.log2(1 + (adl / dl))




lucene.initVM()

TERM_MAX_POSTING_LIST = 500000
QUERY_MAX_POSTING_LIST = 100000

indexPath = File("index-dir/").toPath()
analyzer = StandardAnalyzer()
directory = FSDirectory.open(indexPath)
reader = DirectoryReader.open(directory)
searcher = IndexSearcher(reader)
# using BooleanSimilarity is same as retrieving posting lists
searcher.setSimilarity(BooleanSimilarity())
storedFields = searcher.storedFields()
termVecReader = reader.termVectors()

# List to store all docno field values

# docno_list = []

# # Iterate through all documents in the index
# for doc_id in range(reader.maxDoc()):
#     if not reader.hasDeletions() or reader.isDeleted(doc_id) == False:
#         document = reader.document(doc_id)
#         search = IndexSearcher(reader)
#         docno_field = search.doc(doc_id).get("DOCNO")
#         if docno_field is not None:
#             docno_list.append(doc_id)



def iDF(docFreq, docCount):
    return np.log((1 + docCount) / (docFreq))


def avgFieldLength(collectionStats):
    return collectionStats.sumTotalTermFreq() / collectionStats.docCount()



def escape(query):
        """
        Escapes special characters in the query string to prevent parsing errors.
        """
        special_chars = ['/',',']
        for char in special_chars:
            if char == '-':
                query = query.replace(char,f'')
            else:
                query = query.replace(char,f' ')
        return query

def average_doc_len():
    # Variables to store total length and document count
    total_length = 0
    doc_count = 0

    # Iterate through all documents
    for i in range(reader.maxDoc()):
        if not reader.hasDeletions() or not reader.isDeleted(i):  # Check if the document is not deleted
            doc = reader.document(i)
            dlen = doc.get("DLEN")
            if dlen is not None:
                total_length += int(dlen)
                doc_count += 1
    if doc_count > 0:
        return total_length / doc_count
    return 0


avgdln = average_doc_len()
def calculate_avg_term_frequency(doc_id):
    terms = reader.getTermVector(doc_id, field)  # 'content' is the field name
    if terms is None:
        return 0.0
    
    total_term_freq = terms.getSumTotalTermFreq()
    num_terms = terms.size()

    if num_terms > 0:
        return total_term_freq / num_terms
    else:
        return 0.0
    
def get_total_term_frequency(term, index_reader):
    total_term_freq = 0
    for i in range(index_reader.leaves().size()):
        leaf_reader = index_reader.leaves().get(i).reader()
        term_vector = leaf_reader.terms(field)
        if term_vector is not None:
            terms_enum = term_vector.iterator()
            while terms_enum.next() is not None:
                if terms_enum.term().utf8ToString() == term:
                    total_term_freq += terms_enum.totalTermFreq()
                    break
    return total_term_freq
    

def analyze_query(query, analyzer):
    # Use StringReader to read the query string
    reader = StringReader(query)
    
    # TokenStream to get tokens from the analyzer
    token_stream = analyzer.tokenStream("CONTENT", reader)
    
    # CharTermAttribute to get term strings from tokens
    term_attr = token_stream.addAttribute(CharTermAttribute.class_)
    
    # Initialize the token stream
    token_stream.reset()
    
    # Iterate over tokens and print them
    terms = []
    while token_stream.incrementToken():
        term = term_attr.toString()
        terms.append(term)
    
    # Close the token stream
    token_stream.end()
    token_stream.close()
    
    return terms



class EXP_T_Scorer():
    def __init__(self, query, field):
        self.raw_query = escape(query)
        self.field = field
        self.query = self._parse_query()
        self.alpha = 2 / (1 + np.log2(1 + len(query)))
        self.collectionStats = searcher.collectionStatistics(field)
        self.avgdl = avgdln
        self.docCount = self.collectionStats.docCount()
        

    # Returns a parsed query which is all the terms separeted by space
    # and passed through the analyzer

    
    
    def _parse_query(self):
        # escaped_query = escapeQuerySyntax(self.raw_query)

        try:
            query = QueryParser("CONTENT", analyzer).parse(self.raw_query).toString("CONTENT")
        except ParseException as e:
            print(f"Failed to parse query: {self.raw_query}")
            print(f"ParseException: {e}")
        except lucene.JavaError as e:
            print("JavaError encountered:")
            print(e)
        except Exception as e:
            print("An unexpected error occurred:")
            print(e)
        
        return query

    def _query_interesection_list(self):
        """  boolqBuilder = BooleanQuery.Builder()
        for term in self.query.split():
            boolqBuilder.add(TermQuery(Term(self.field, term)), BooleanClause.Occur.MUST)
        boolq = boolqBuilder.build()"""
        # final_list = []
        # term_list = analyze_query(self.query, analyzer)
        # for term in term_list:
        #     boolq = QueryParser(self.field, analyzer).parse(term)
        #     hits = searcher.search(boolq, QUERY_MAX_POSTING_LIST).scoreDocs
        #     final_list.extend(hits)

        # unique_docs = set()
        # unique_hits = []
        # for hit in final_list:
        #     search = IndexSearcher(reader)
        #     doc_id = search.doc(hit.doc).get("DOCNO")
        #     if doc_id not in unique_docs:
        #         unique_docs.add(doc_id)
        #         unique_hits.append(hit)

        # return unique_hits

        # query_term_list = analyze_query(self.query, analyzer)
        # docno_list = []

        # # Iterate through all documents in the index
        # for doc_id in range(reader.maxDoc()):
        #     if not reader.hasDeletions() or reader.isDeleted(doc_id) == False:
        #         document = reader.document(doc_id)
        #         search = IndexSearcher(reader)
        #         docno_field = search.doc(doc_id).get("DOCNO")
        #         content_field = search.doc(doc_id).get("CONTENT")
        #         content_term_list = analyze_query(content_field, analyzer)
        #         for term in query_term_list:
        #             if term in content_term_list:
        #                 if docno_field is not None:
        #                     docno_list.append(doc_id)
    
        # unique_docs = set()
        # unique_hits = []
        # for hit in docno_list:
        #     if hit not in unique_docs:
        #         unique_docs.add(hit)
        #         unique_hits.append(hit)

        # return unique_hits

        # final_list = []
        # searcher.setSimilarity(BM25Similarity(1.8, 0.3))
        # term_list = analyze_query(self.query, analyzer)
        # for term in term_list:
        #     boolq = QueryParser(self.field, analyzer).parse(term)
        #     hits = searcher.search(boolq, QUERY_MAX_POSTING_LIST).scoreDocs
        #     final_list.extend(hits)
        # unique_docs = set()
        # unique_hits = []
        # for hit in final_list:
        #     doc_id = searcher.doc(hit.doc).get("DOCNO")
        #     if doc_id not in unique_docs:
        #         unique_docs.add(doc_id)
        #         unique_hits.append(hit)
            # final_hits = set()
            # boolqBuilder = BooleanQuery.Builder()
            # for term in self.query.split():
            #     boolqBuilder.add(TermQuery(Term(self.field, term)), BooleanClause.Occur.MUST)
            #     boolq = QueryParser(self.field, analyzer).parse(self.raw_query)
            #     hits = searcher.search(boolq, QUERY_MAX_POSTING_LIST).scoreDocs
            #     for h in hits:
            #         if h.doc not in final_hits:
            #             final_hits.add(h.doc)
        # final_res = []
        # unique_docs = set()
        
        # #hit_list = final_hits[:]
        # for hit in final_hits:
        #     if hit not in unique_docs:
        #         unique_docs.add(hit)
        #         final_res.append(hit)

        
            # return list(final_hits)
        query_term_list = analyze_query(self.query, analyzer)
        boolqBuilder = BooleanQuery.Builder()
        for term in query_term_list:
            boolqBuilder.add(TermQuery(Term(self.field, term)), BooleanClause.Occur.MUST)
        boolq = boolqBuilder.build()
        # boolq = QueryParser(self.field, analyzer).parse(self.raw_query)
        hits = searcher.search(boolq, QUERY_MAX_POSTING_LIST).scoreDocs
        return hits
        

        

    # 427,444
    def EXPTscore(self, docid):
        termVec = termVecReader.get(docid, self.field)
        termsEnum = termVec.iterator()
        dl = termVecReader.get(docid, "DLEN")
        if dl == None:
            dl = 1
        else:
            dl = int(dl)
            
        num_terms = termVec.size()
        avgtf = calculate_avg_term_frequency(docid)
        avgdl = self.avgdl
        score = 0
        i = 0
        sum_TDF = 0
        final_score = 0
        term_list = analyze_query(self.raw_query,analyzer)
        for term in term_list:
            if termsEnum.seekExact(BytesRef(term)):
                tf = termsEnum.totalTermFreq()
                #print(tf)
            else:
                continue
            term_ritf = ritf(tf, avgtf)
            term_lrtf = lrtf(tf, avgdl, dl)
            doc_freq = reader.docFreq(Term(field, term))
            idf = iDF(doc_freq, self.docCount)
            BRITF = term_ritf/(1+term_ritf) if tf > 0 else 0
            BLRTF = term_lrtf/(1+term_lrtf) if tf > 0 else 0
            TFF = (self.alpha)*BRITF + (1-self.alpha)*BLRTF
            total_term_freq = reader.totalTermFreq(Term(field, term))
            
            aveit = total_term_freq/doc_freq
            
            TDF = idf*(aveit/(1+aveit))
            score += (TFF*TDF)
            sum_TDF += TDF
            i += 1

        if sum_TDF == 0:
            return 0
        
        final_score = score/sum_TDF
        #print(final_score)
        
        return final_score
    

    def scoreDocs(self):
        hits = self._query_interesection_list()
        scoreDocs = []
        for hit in hits:
            docid = hit.doc
            score = self.EXPTscore(docid)
            scoreDoc = (docid, score)
            scoreDocs.append(scoreDoc)
        scoreDocs = sorted(scoreDocs, key=lambda scoreDoc: scoreDoc[1], reverse=True)
        if len(scoreDocs) > 1000:
            return scoreDocs[:1000]
        return scoreDocs


def docidTodocno(docid):
    return storedFields.document(docid).get("DOCNO")


for top in robust_topics:
    query_num = top[0].text  # this is query number
    title = top[1].text  # this will be our query
    expt_scorer = EXP_T_Scorer(title, field)
    print(query_num, title)
    rank = 1
    for scoredDoc in expt_scorer.scoreDocs():
        robust_rank_file.write(f"{query_num}\tQ0\t{docidTodocno(scoredDoc[0])}\t{rank}\t{scoredDoc[1]}\tcs2313\n")
        rank += 1

robust_rank_file.close()



print("TREC Rank ###########")

for top in trec678_topics:
    query_num = top[0].text  # this is query number
    title = top[1].text  # this will be our query
    expt_scorer = EXP_T_Scorer(title, field)
    print(query_num, title)
    rank = 1
    for scoredDoc in expt_scorer.scoreDocs():
        trec678_rank_file.write(f"{query_num}\tQ0\t{docidTodocno(scoredDoc[0])}\t{rank}\t{scoredDoc[1]}\tcs2313\n")
        rank += 1

trec678_rank_file.close()
