"""Mock response data for service tests."""

from typing import Dict, Any

# Ollama mock responses
OLLAMA_GENERATE_RESPONSE = {
    "model": "llama2",
    "created_at": "2024-01-01T00:00:00Z",
    "response": "This is a generated response from Ollama.",
    "done": True
}

OLLAMA_TAGS_RESPONSE = {
    "models": [
        {
            "name": "llama2:latest",
            "modified_at": "2024-01-01T00:00:00Z",
            "size": 3825819519
        },
        {
            "name": "qwen2.5:latest",
            "modified_at": "2024-01-01T00:00:00Z",
            "size": 4661211296
        }
    ]
}

# Gemini mock responses
GEMINI_GENERATE_RESPONSE = {
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": "This is a generated response from Gemini."
                    }
                ],
                "role": "model"
            },
            "finishReason": "STOP",
            "index": 0
        }
    ],
    "usageMetadata": {
        "promptTokenCount": 10,
        "candidatesTokenCount": 20,
        "totalTokenCount": 30
    }
}

# OpenAI mock responses
OPENAI_CHAT_RESPONSE = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677652288,
    "model": "gpt-4o-mini",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "This is a generated response from OpenAI."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    }
}

# GitHub Gist mock responses
GIST_CREATE_RESPONSE = {
    "id": "abc123",
    "html_url": "https://gist.github.com/user/abc123",
    "description": "Test gist",
    "public": False,
    "files": {
        "test.py": {
            "filename": "test.py",
            "type": "application/x-python",
            "language": "Python",
            "raw_url": "https://gist.githubusercontent.com/user/abc123/raw/test.py",
            "size": 100
        }
    },
    "owner": {
        "login": "user",
        "id": 12345
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
}

# ChromaDB mock responses
CHROMA_QUERY_RESPONSE = {
    "ids": [["doc1", "doc2"]],
    "embeddings": None,
    "documents": [["Document 1 content", "Document 2 content"]],
    "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
    "distances": [[0.1, 0.3]]
}

# PyTrends mock responses
PYTRENDS_INTEREST_RESPONSE = {
    "python": [50, 55, 60, 65, 70],
    "javascript": [45, 48, 52, 55, 58],
    "isPartial": [False, False, False, False, True]
}

PYTRENDS_RELATED_QUERIES = {
    "python": {
        "top": [
            {"query": "python tutorial", "value": 100},
            {"query": "python download", "value": 85},
            {"query": "python programming", "value": 75}
        ],
        "rising": [
            {"query": "python 3.12", "value": 500},
            {"query": "python ai", "value": 300}
        ]
    }
}

# Embedding mock data
MOCK_EMBEDDINGS = [
    [0.1, 0.2, 0.3, 0.4, 0.5],
    [0.2, 0.3, 0.4, 0.5, 0.6],
    [0.3, 0.4, 0.5, 0.6, 0.7]
]

# Link checker mock responses
LINK_CHECK_SUCCESS = {
    "status_code": 200,
    "headers": {
        "content-type": "text/html",
        "server": "nginx"
    }
}

LINK_CHECK_NOT_FOUND = {
    "status_code": 404,
    "headers": {
        "content-type": "text/html"
    }
}

# Error responses
OLLAMA_ERROR_RESPONSE = {
    "error": "model not found"
}

GEMINI_ERROR_RESPONSE = {
    "error": {
        "code": 400,
        "message": "Invalid API key",
        "status": "INVALID_ARGUMENT"
    }
}

OPENAI_ERROR_RESPONSE = {
    "error": {
        "message": "Incorrect API key provided",
        "type": "invalid_request_error",
        "param": None,
        "code": "invalid_api_key"
    }
}


def get_mock_response(provider: str, endpoint: str, success: bool = True) -> Dict[str, Any]:
    """Get mock response for a provider and endpoint.
    
    Args:
        provider: Provider name (ollama, gemini, openai, gist, trends, chroma)
        endpoint: Endpoint name (generate, query, etc.)
        success: Whether to return success or error response
        
    Returns:
        Mock response dictionary
    """
    responses = {
        "ollama": {
            "generate": OLLAMA_GENERATE_RESPONSE if success else OLLAMA_ERROR_RESPONSE,
            "tags": OLLAMA_TAGS_RESPONSE,
        },
        "gemini": {
            "generate": GEMINI_GENERATE_RESPONSE if success else GEMINI_ERROR_RESPONSE,
        },
        "openai": {
            "chat": OPENAI_CHAT_RESPONSE if success else OPENAI_ERROR_RESPONSE,
        },
        "gist": {
            "create": GIST_CREATE_RESPONSE,
        },
        "chroma": {
            "query": CHROMA_QUERY_RESPONSE,
        },
        "trends": {
            "interest": PYTRENDS_INTEREST_RESPONSE,
            "related": PYTRENDS_RELATED_QUERIES,
        }
    }
    
    return responses.get(provider, {}).get(endpoint, {})
# DOCGEN:LLM-FIRST@v4