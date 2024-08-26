# A Novel TF-IDF Weighting Scheme for Effective Ranking

## Overview

This project introduces a novel TF-IDF weighting scheme designed to improve the effectiveness of document ranking in information retrieval systems. The scheme has been implemented and tested on two standard datasets: **Robust** and **TREC678**. The results demonstrate that the proposed method enhances the retrieval quality, particularly in returning relevant documents early in the ranked list.

## Features

- **Custom TF-IDF Weighting**: A modified TF-IDF algorithm aimed at boosting the relevance of retrieved documents.
- **Evaluation on Standard Datasets**: Performance evaluated on Robust and TREC678 datasets, which are widely used benchmarks in the information retrieval community.
- **Performance Metrics**: Detailed evaluation using MAP (Mean Average Precision), R-Precision, bpref (Binary Preference), Reciprocal Rank, and Precision at various levels.

## Code Structure

The code is organized as follows:

- **data/**: Contains the datasets (Robust, TREC678) used for evaluation.
- **src/**: The main implementation of the TF-IDF weighting scheme.
  - `tfidf.py`: The core implementation of the novel TF-IDF weighting algorithm.
  - `evaluation.py`: Scripts for evaluating the performance on different datasets.
- **results/**: Stores the output results, including the performance metrics.
- **README.md**: Documentation and instructions for running the project (this file).

## Installation

### Prerequisites

- Python 3.8+
- Required Python libraries can be installed using:

