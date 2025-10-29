import csv
import json
import math
import pickle
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


class Indexer:

    def __init__(self, data_csv_path: str, index_dir: str = "data/index"):
        self.data_csv_path = Path(data_csv_path)
        self.index_dir = Path(index_dir)

        # Create index directory if it doesn't exist
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # File paths for persisted index data
        self.inverted_index_path = self.index_dir / "inverted_index.pkl"
        self.doc_metadata_path = self.index_dir / "doc_metadata.pkl"
        self.term_doc_freq_path = self.index_dir / "term_doc_freq.pkl"
        self.index_stats_path = self.index_dir / "index_stats.json"

        # Data structures for the index
        self.inverted_index: Dict[str, Dict[int, int]
                                  ] = defaultdict(lambda: defaultdict(int))
        # inverted_index structure: {term: {doc_id: term_frequency}}

        self.doc_metadata: Dict[int, Dict] = {}
        # doc_metadata structure: {doc_id: {url, name, description, country, etc.}}

        self.term_doc_freq: Dict[str, int] = defaultdict(int)
        # term_doc_freq structure: {term: number_of_documents_containing_term}

        self.total_docs = 0
        self.doc_lengths: Dict[int, int] = {}  # {doc_id: total_term_count}

        # Fields to index (can be configured)
        self.indexable_fields = ['name', 'full_name',
                                 'description', 'contry', 'type', 'status']

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into normalized terms.
        - Convert to lowercase
        - Remove special characters
        - Split on whitespace
        - Filter out very short tokens
        """
        if not text or not isinstance(text, str):
            return []

        # Convert to lowercase
        text = text.lower()

        # Replace punctuation and special chars with spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split on whitespace and filter
        tokens = [token.strip()
                  for token in text.split() if len(token.strip()) > 2]

        return tokens

    def _build_index_from_csv(self):
        """
        Read the CSV file and build the inverted index.
        """
        print(f"Building index from: {self.data_csv_path}")

        if not self.data_csv_path.exists():
            raise FileNotFoundError(
                f"Data file not found: {self.data_csv_path}")

        doc_id = 0

        with open(self.data_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Store document metadata
                self.doc_metadata[doc_id] = dict(row)

                # Track all terms in this document for length calculation
                doc_terms: Dict[str, int] = defaultdict(int)

                # Unique terms count
                terms_in_doc: Set[str] = set()

                # Process each indexable field
                for field in self.indexable_fields:
                    if field in row and row[field]:
                        tokens = self._tokenize(row[field])

                        for token in tokens:
                            # Update term frequency in document
                            doc_terms[token] += 1
                            terms_in_doc.add(token)

                # Update inverted index with term frequencies
                for term, freq in doc_terms.items():
                    self.inverted_index[term][doc_id] = freq

                # Update document frequency for each unique term in this doc
                for term in terms_in_doc:
                    self.term_doc_freq[term] += 1

                # Store document length (total number of terms)
                self.doc_lengths[doc_id] = sum(doc_terms.values())

                doc_id += 1

                if doc_id % 100 == 0:
                    print(f"  Indexed {doc_id} documents...")

        self.total_docs = doc_id
        print(f"Index building complete. Total documents: {self.total_docs}")
        print(f"Total unique terms: {len(self.inverted_index)}")

    def calculate_tf(self, term: str, doc_id: int) -> float:
        """
        Calculate Term Frequency (TF) for a term in a document.
        TF = (frequency of term in document) / (total terms in document)
        """
        if doc_id not in self.doc_lengths or self.doc_lengths[doc_id] == 0:
            return 0.0

        term_freq = self.inverted_index.get(term, {}).get(doc_id, 0)
        return term_freq / self.doc_lengths[doc_id]

    def calculate_idf_classic(self, term: str) -> float:
        """
        Calculate classic IDF (Inverse Document Frequency).
        IDF = log(N / df)
        where N = total documents, df = documents containing the term
        """
        df = self.term_doc_freq.get(term, 0)

        if df == 0:
            return 0.0

        return math.log(self.total_docs / df)

    def calculate_idf_smooth(self, term: str) -> float:
        """
        Calculate smooth IDF to prevent division by zero and reduce impact of very rare terms.
        Smooth IDF = log((N + 1) / (df + 1)) + 1
        where N = total documents, df = documents containing the term
        """
        df = self.term_doc_freq.get(term, 0)
        return math.log((self.total_docs + 1) / (df + 1)) + 1

    def calculate_tfidf(self, term: str, doc_id: int, idf_method: str = 'classic') -> float:
        """
        Calculate TF-IDF score for a term in a document.

        Args:
            term: The search term
            doc_id: Document identifier
            idf_method: 'classic' or 'smooth'

        Returns:
            TF-IDF score
        """
        tf = self.calculate_tf(term, doc_id)

        if idf_method == 'smooth':
            idf = self.calculate_idf_smooth(term)
        else:
            idf = self.calculate_idf_classic(term)

        return tf * idf

    def _save_index(self):
        """
        Persist the index data structures to disk.
        """
        print("Saving index to disk...")

        # Save inverted index
        with open(self.inverted_index_path, 'wb') as f:
            pickle.dump(dict(self.inverted_index), f)

        # Save document metadata
        with open(self.doc_metadata_path, 'wb') as f:
            pickle.dump(self.doc_metadata, f)

        # Save term document frequencies
        with open(self.term_doc_freq_path, 'wb') as f:
            pickle.dump(dict(self.term_doc_freq), f)

        # Save index statistics as JSON for human readability
        stats = {
            'total_docs': self.total_docs,
            'total_unique_terms': len(self.inverted_index),
            'doc_lengths': self.doc_lengths,
            'indexed_fields': self.indexable_fields
        }
        with open(self.index_stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)

        print(f"Index saved to: {self.index_dir}")

    def _load_index(self):
        """
        Load the index data structures from disk.
        """
        print("Loading existing index from disk...")

        # Load inverted index
        with open(self.inverted_index_path, 'rb') as f:
            self.inverted_index = defaultdict(
                lambda: defaultdict(int), pickle.load(f))

        # Load document metadata
        with open(self.doc_metadata_path, 'rb') as f:
            self.doc_metadata = pickle.load(f)

        # Load term document frequencies
        with open(self.term_doc_freq_path, 'rb') as f:
            self.term_doc_freq = defaultdict(int, pickle.load(f))

        # Load statistics
        with open(self.index_stats_path, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            self.total_docs = stats['total_docs']
            self.doc_lengths = {
                int(k): v for k, v in stats['doc_lengths'].items()}
            self.indexable_fields = stats.get(
                'indexed_fields', self.indexable_fields)

        print(f"Index loaded successfully.")
        print(f"  Total documents: {self.total_docs}")
        print(f"  Total unique terms: {len(self.inverted_index)}")

    def index_exists(self) -> bool:
        """
        Check if index files already exist.
        """
        return (self.inverted_index_path.exists() and
                self.doc_metadata_path.exists() and
                self.term_doc_freq_path.exists() and
                self.index_stats_path.exists())

    def run(self, force_rebuild: bool = False):

        if self.index_exists() and not force_rebuild:
            print("Index files found. Loading existing index...")
            self._load_index()
        else:
            if force_rebuild:
                print("Force rebuild requested. Building new index...")
            else:
                print("No existing index found. Building new index...")

            self._build_index_from_csv()
            self._save_index()

        print("Indexer ready.")


# --- Main execution block ---
if __name__ == "__main__":
    DATA_CSV = "data/extracted_data.csv"
    INDEX_DIR = "data/index"

    print("[i] Starting Indexer")

    indexer = Indexer(
        data_csv_path=DATA_CSV,
        index_dir=INDEX_DIR
    )

    # Run the indexing process
    # Set force_rebuild=True to rebuild even if index exists
    indexer.run(force_rebuild=False)

    print("\n--- Indexer finished. ---")
