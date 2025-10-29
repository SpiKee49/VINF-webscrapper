from collections import defaultdict
from typing import List, Dict

from indexer_module import Indexer


class Searcher:
    """
    Search engine that uses the inverted index to find and rank documents.
    Supports both classic and smooth IDF scoring methods.
    """

    def __init__(self, indexer: Indexer):
        """
        Initialize the searcher with an existing indexer.

        Args:
            indexer: An initialized Indexer instance with loaded index data
        """
        self.indexer = indexer

        if self.indexer.total_docs == 0:
            raise ValueError(
                "Indexer has no documents. Please build/load the index first.")

        print(
            f"Searcher initialized with {self.indexer.total_docs} documents.")

    def search(self, query: str, idf_method: str = 'classic', top_k: int = 10) -> List[Dict]:
        """
        Search for documents matching the query and return ranked results.

        Args:
            query: Search query string
            idf_method: 'classic' or 'smooth' IDF calculation method
            top_k: Number of top results to return

        Returns:
            List of dictionaries containing document metadata and scores
        """
        # Tokenize the query
        query_terms = self.indexer._tokenize(query)

        if not query_terms:
            print("No valid search terms found in query.")
            return []

        print(f"Searching for: {query_terms}")
        print(f"Using IDF method: {idf_method}")

        # Calculate scores for all documents
        doc_scores: Dict[int, float] = defaultdict(float)

        for term in query_terms:
            if term not in self.indexer.inverted_index:
                print(f"  Term '{term}' not found in index.")
                continue

            # Get all documents containing this term
            for doc_id in self.indexer.inverted_index[term].keys():
                # Calculate TF-IDF score for this term in this document
                tfidf_score = self.indexer.calculate_tfidf(
                    term, doc_id, idf_method)
                doc_scores[doc_id] += tfidf_score

        if not doc_scores:
            print("No documents found matching the query.")
            return []

        # Sort documents by score (descending)
        ranked_docs = sorted(doc_scores.items(),
                             key=lambda x: x[1], reverse=True)

        # Prepare results with metadata
        results = []
        for doc_id, score in ranked_docs[:top_k]:
            result = {
                'doc_id': doc_id,
                'score': score,
                'metadata': self.indexer.doc_metadata[doc_id]
            }
            results.append(result)

        print(
            f"Found {len(doc_scores)} matching documents. Returning top {len(results)}.")
        return results

    def compare_idf_methods(self, query: str, top_k: int = 10) -> Dict[str, List[Dict]]:
        """
        Compare results using both IDF methods side by side.

        Args:
            query: Search query string
            top_k: Number of top results to return for each method

        Returns:
            Dictionary with 'classic' and 'smooth' keys containing results
        """
        print(f"\n{'='*60}")
        print(f"Comparing IDF methods for query: '{query}'")
        print(f"{'='*60}\n")

        results = {
            'classic': self.search(query, idf_method='classic', top_k=top_k),
            'smooth': self.search(query, idf_method='smooth', top_k=top_k)
        }

        return results

    def search_with_filter(self, query: str, filters: Dict[str, str],
                           idf_method: str = 'classic', top_k: int = 10) -> List[Dict]:
        """
        Search with additional metadata filters.

        Args:
            query: Search query string
            filters: Dictionary of field:value pairs to filter by (e.g., {'contry': 'France'})
            idf_method: 'classic' or 'smooth' IDF calculation method
            top_k: Number of top results to return

        Returns:
            List of filtered and ranked results
        """
        # First, get all search results
        # Get more results for filtering
        all_results = self.search(query, idf_method, top_k=1000)

        # Apply filters
        filtered_results = []
        for result in all_results:
            metadata = result['metadata']

            # Check if all filter conditions are met
            matches_all = True
            for field, value in filters.items():
                if field not in metadata or value.lower() not in metadata[field].lower():
                    matches_all = False
                    break

            if matches_all:
                filtered_results.append(result)

            # Stop if we have enough results
            if len(filtered_results) >= top_k:
                break

        print(f"Applied filters: {filters}")
        print(f"Filtered results: {len(filtered_results)}")

        return filtered_results

    def get_term_statistics(self, term: str) -> Dict:
        """
        Get statistics about a specific term in the index.

        Args:
            term: The term to analyze

        Returns:
            Dictionary with term statistics
        """
        normalized_term = self.indexer._tokenize(term)
        if not normalized_term:
            return {'error': 'Invalid term'}

        term = normalized_term[0]

        if term not in self.indexer.inverted_index:
            return {
                'term': term,
                'found': False,
                'message': 'Term not found in index'
            }

        doc_freq = self.indexer.term_doc_freq[term]
        total_occurrences = sum(self.indexer.inverted_index[term].values())

        stats = {
            'term': term,
            'found': True,
            'document_frequency': doc_freq,
            'total_occurrences': total_occurrences,
            'idf_classic': self.indexer.calculate_idf_classic(term),
            'idf_smooth': self.indexer.calculate_idf_smooth(term),
            'percentage_of_docs': (doc_freq / self.indexer.total_docs) * 100
        }

        return stats

    def display_results(self, results: List[Dict], show_description: bool = True):
        """
        Display search results in a formatted way.

        Args:
            results: List of result dictionaries from search
            show_description: Whether to show full description
        """
        if not results:
            print("No results to display.")
            return

        print(f"\n{'='*80}")
        print(f"Displaying {len(results)} results:")
        print(f"{'='*80}\n")

        for i, result in enumerate(results, 1):
            metadata = result['metadata']
            score = result['score']

            print(f"{i}. {metadata.get('name', 'N/A')} (Score: {score:.4f})")
            print(f"   URL: {metadata.get('url', 'N/A')}")

            if metadata.get('contry'):
                print(f"   Country: {metadata.get('contry')}")

            if metadata.get('type'):
                print(f"   Type: {metadata.get('type')}")

            if show_description and metadata.get('description'):
                desc = metadata['description']
                # Truncate long descriptions
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"   Description: {desc}")

            print()


# --- Main execution block ---
if __name__ == "__main__":
    print("[i] Starting Searcher")

    # Initialize indexer and load the index
    indexer = Indexer(
        data_csv_path="data/extracted_data.csv",
        index_dir="data/index"
    )
    indexer.run(force_rebuild=False)

    # Create searcher
    searcher = Searcher(indexer)

    # Example searches
    print("\n" + "="*80)
    print("EXAMPLE SEARCHES")
    print("="*80)

    # Example 1: Basic search
    query = "historic temple"
    results = searcher.search(query, idf_method='classic', top_k=5)
    searcher.display_results(results)

    # Example 2: Compare IDF methods
    print("\n" + "="*80)
    print("COMPARING IDF METHODS")
    print("="*80)

    query = "ancient city"
    comparison = searcher.compare_idf_methods(query, top_k=3)

    print("\n--- Classic IDF Results ---")
    searcher.display_results(comparison['classic'], show_description=False)

    print("\n--- Smooth IDF Results ---")
    searcher.display_results(comparison['smooth'], show_description=False)

    # Example 3: Search with filters
    print("\n" + "="*80)
    print("SEARCH WITH FILTERS")
    print("="*80)

    query = "cultural"
    filters = {'type': 'Cultural'}
    filtered_results = searcher.search_with_filter(query, filters, top_k=5)
    searcher.display_results(filtered_results, show_description=False)

    # Example 4: Term statistics
    print("\n" + "="*80)
    print("TERM STATISTICS")
    print("="*80)

    term = "historic"
    stats = searcher.get_term_statistics(term)
    print(f"\nStatistics for term '{term}':")
    for key, value in stats.items():
        if key != 'term':
            print(f"  {key}: {value}")

    print("\n--- Searcher finished. ---")
