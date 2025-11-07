"""Enhanced duplication detector with similarity scoring."""

from pathlib import Path
from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class EnhancedDuplicationDetector:
    """Detects duplicate/similar blog posts with detailed scoring."""
    
    def __init__(self, blog_index_path: Path = None):
        self.blog_index_path = blog_index_path or Path("./data/blog_index.json")
        self.blog_index = self._load_blog_index()
        self.vectorizer = None
        logger.info(f"EnhancedDuplicationDetector initialized with {len(self.blog_index)} posts")
    
    def _load_blog_index(self) -> List[Dict[str, Any]]:
        """Load existing blog posts index."""
        if not self.blog_index_path.exists():
            logger.warning(f"Blog index not found: {self.blog_index_path}")
            return []
        
        try:
            with open(self.blog_index_path) as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to load blog index: {e}")
            return []
    
    def check_duplication(self,
                         title: str,
                         outline: str = "",
                         threshold: float = 0.75) -> Dict[str, Any]:
        """Check for duplicates using TF-IDF + cosine similarity."""
        
        if not self.blog_index:
            return {
                "duplicates": [],
                "similar": [],
                "unique": True
            }
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Combine title and outline
            query_text = f"{title} {outline}"
            
            # Get all existing posts
            existing_texts = [
                f"{post.get('title', '')} {post.get('content', '')[:500]}"
                for post in self.blog_index
            ]
            
            # Vectorize
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            all_texts = existing_texts + [query_text]
            vectors = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity
            query_vector = vectors[-1]
            existing_vectors = vectors[:-1]
            similarities = cosine_similarity(query_vector, existing_vectors)[0]
            
            # Find duplicates (high similarity)
            duplicates = []
            similar = []
            
            for idx, sim in enumerate(similarities):
                post = self.blog_index[idx]
                
                if sim > threshold:
                    duplicates.append({
                        "slug": post.get('slug', 'unknown'),
                        "title": post.get('title', 'Unknown'),
                        "similarity_score": float(sim),
                        "url": post.get('url', '')
                    })
                elif sim > threshold * 0.7:  # Similar but not duplicate
                    similar.append({
                        "slug": post.get('slug', 'unknown'),
                        "title": post.get('title', 'Unknown'),
                        "similarity_score": float(sim),
                        "url": post.get('url', '')
                    })
            
            # Sort by similarity
            duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
            similar.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            result = {
                "duplicates": duplicates,
                "similar": similar[:5],  # Top 5 similar
                "unique": len(duplicates) == 0
            }
            
            logger.info(
                f"Duplication check: {len(duplicates)} duplicates, "
                f"{len(similar)} similar posts"
            )
            
            return result
            
        except ImportError:
            logger.warning("sklearn not available, using basic comparison")
            return self._basic_check(title, threshold)
        except Exception as e:
            logger.error(f"Duplication check failed: {e}")
            return {
                "duplicates": [],
                "similar": [],
                "unique": True,
                "error": str(e)
            }
    
    def _basic_check(self, title: str, threshold: float) -> Dict[str, Any]:
        """Basic duplication check without sklearn."""
        duplicates = []
        similar = []
        
        title_lower = title.lower()
        
        for post in self.blog_index:
            post_title = post.get('title', '').lower()
            
            # Simple word overlap
            title_words = set(title_lower.split())
            post_words = set(post_title.split())
            
            if not title_words or not post_words:
                continue
            
            overlap = len(title_words & post_words)
            union = len(title_words | post_words)
            
            similarity = overlap / union if union > 0 else 0
            
            if similarity > threshold:
                duplicates.append({
                    "slug": post.get('slug', 'unknown'),
                    "title": post.get('title', 'Unknown'),
                    "similarity_score": similarity,
                    "url": post.get('url', '')
                })
            elif similarity > threshold * 0.7:
                similar.append({
                    "slug": post.get('slug', 'unknown'),
                    "title": post.get('title', 'Unknown'),
                    "similarity_score": similarity,
                    "url": post.get('url', '')
                })
        
        return {
            "duplicates": duplicates,
            "similar": similar[:5],
            "unique": len(duplicates) == 0
        }
    
    def format_report(self, result: Dict[str, Any]) -> str:
        """Format duplication check result as markdown."""
        if result.get("unique"):
            return "✅ No duplicate content detected.\n"
        
        output = ["## Duplication Check Results\n"]
        
        if result.get("duplicates"):
            output.append("### 🚨 Potential Duplicates\n")
            for dup in result["duplicates"]:
                output.append(
                    f"- **{dup['title']}** "
                    f"(similarity: {dup['similarity_score']:.1%})\n"
                    f"  - Slug: `{dup['slug']}`"
                )
                if dup.get('url'):
                    output.append(f"  - URL: {dup['url']}")
                output.append("")
        
        if result.get("similar"):
            output.append("### 📊 Similar Content\n")
            for sim in result["similar"]:
                output.append(
                    f"- {sim['title']} "
                    f"(similarity: {sim['similarity_score']:.1%})"
                )
            output.append("")
        
        return "\n".join(output)
