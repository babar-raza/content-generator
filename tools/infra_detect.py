"""
Infrastructure Detection for Wave 2 Prep

Scans requirements.txt and imports to detect external infrastructure dependencies.
Generates docker-compose and .env.example based on detected services.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
from _env import get_repo_root


# Known infrastructure dependencies
INFRA_PATTERNS = {
    'chromadb': {
        'package': 'chromadb',
        'service': 'ChromaDB',
        'docker_image': 'chromadb/chroma:latest',
        'port': 8000,
        'env_vars': ['CHROMA_HOST', 'CHROMA_PORT']
    },
    'redis': {
        'package': 'redis',
        'service': 'Redis',
        'docker_image': 'redis:7-alpine',
        'port': 6379,
        'env_vars': ['REDIS_URL', 'REDIS_HOST', 'REDIS_PORT']
    },
    'postgres': {
        'package': 'psycopg2',
        'service': 'PostgreSQL',
        'docker_image': 'postgres:16-alpine',
        'port': 5432,
        'env_vars': ['POSTGRES_DSN', 'DATABASE_URL', 'POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    },
    'qdrant': {
        'package': 'qdrant-client',
        'service': 'Qdrant',
        'docker_image': 'qdrant/qdrant:latest',
        'port': 6333,
        'env_vars': ['QDRANT_URL', 'QDRANT_HOST', 'QDRANT_PORT']
    },
    'elasticsearch': {
        'package': 'elasticsearch',
        'service': 'Elasticsearch',
        'docker_image': 'elasticsearch:8.11.0',
        'port': 9200,
        'env_vars': ['ELASTICSEARCH_URL', 'ES_HOST', 'ES_PORT']
    },
    'rabbitmq': {
        'package': 'pika',
        'service': 'RabbitMQ',
        'docker_image': 'rabbitmq:3-management-alpine',
        'port': 5672,
        'env_vars': ['RABBITMQ_URL', 'RABBITMQ_HOST']
    },
    'kafka': {
        'package': 'kafka-python',
        'service': 'Kafka',
        'docker_image': 'confluentinc/cp-kafka:latest',
        'port': 9092,
        'env_vars': ['KAFKA_BOOTSTRAP_SERVERS', 'KAFKA_HOST']
    },
    'celery': {
        'package': 'celery',
        'service': 'Celery',
        'docker_image': None,  # Celery uses Redis/RabbitMQ
        'port': None,
        'env_vars': ['CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND']
    }
}

# LLM provider patterns
LLM_PROVIDERS = {
    'openai': {
        'package': 'openai',
        'provider': 'OpenAI',
        'env_vars': ['OPENAI_API_KEY', 'OPENAI_BASE_URL']
    },
    'google-generativeai': {
        'package': 'google-generativeai',
        'provider': 'Google Gemini',
        'env_vars': ['GEMINI_API_KEY', 'GOOGLE_AI_API_KEY']
    },
    'anthropic': {
        'package': 'anthropic',
        'provider': 'Anthropic Claude',
        'env_vars': ['ANTHROPIC_API_KEY']
    },
    'ollama': {
        'package': 'ollama',
        'provider': 'Ollama',
        'env_vars': ['OLLAMA_BASE_URL', 'OLLAMA_HOST']
    }
}


def scan_requirements() -> Set[str]:
    """Scan requirements.txt for installed packages."""
    repo_root = get_repo_root()
    req_file = repo_root / 'requirements.txt'

    packages = set()
    if req_file.exists():
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before ==, >=, etc.)
                    pkg_name = re.split(r'[=<>!]', line)[0].strip()
                    packages.add(pkg_name.lower())

    return packages


def scan_imports(directory: Path) -> Set[str]:
    """Scan Python files for import statements."""
    imports = set()

    for py_file in directory.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        # Extract module name
                        match = re.match(r'(?:from|import)\s+([a-zA-Z0-9_]+)', line)
                        if match:
                            imports.add(match.group(1).lower())
        except Exception:
            # Skip files that can't be read
            continue

    return imports


def detect_infrastructure() -> Dict:
    """Detect infrastructure dependencies."""
    repo_root = get_repo_root()
    src_dir = repo_root / 'src'

    # Scan requirements and imports
    packages = scan_requirements()
    imports = scan_imports(src_dir)

    detected_infra = {}
    detected_llms = {}

    # Check for infrastructure
    for key, config in INFRA_PATTERNS.items():
        if config['package'].lower() in packages or config['package'].lower() in imports:
            detected_infra[key] = config

    # Check for LLM providers
    for key, config in LLM_PROVIDERS.items():
        if config['package'].lower() in packages or config['package'].lower() in imports:
            detected_llms[key] = config

    return {
        'infrastructure': detected_infra,
        'llm_providers': detected_llms,
        'packages_scanned': len(packages),
        'imports_scanned': len(imports)
    }


def generate_docker_compose(detected: Dict) -> str:
    """Generate docker-compose.wave2.yml content."""
    infra = detected.get('infrastructure', {})

    if not infra:
        return None  # No infrastructure needed

    compose = {
        'version': '3.8',
        'services': {}
    }

    # Add detected services
    for key, config in infra.items():
        if config['docker_image'] is None:
            continue  # Skip services without docker image (like Celery)

        service_name = key.replace('-', '_')
        service_config = {
            'image': config['docker_image'],
            'ports': [f"{config['port']}:{config['port']}"],
            'restart': 'unless-stopped'
        }

        # Add service-specific configuration
        if key == 'chromadb':
            service_config['environment'] = {
                'ALLOW_RESET': 'TRUE',
                'ANONYMIZED_TELEMETRY': 'FALSE'
            }
            service_config['volumes'] = ['./chroma_data:/chroma/chroma']

        elif key == 'redis':
            service_config['volumes'] = ['./redis_data:/data']

        elif key == 'postgres':
            service_config['environment'] = {
                'POSTGRES_DB': 'ucop_dev',
                'POSTGRES_USER': 'ucop',
                'POSTGRES_PASSWORD': 'dev_password_change_me'
            }
            service_config['volumes'] = ['./postgres_data:/var/lib/postgresql/data']

        elif key == 'qdrant':
            service_config['volumes'] = ['./qdrant_data:/qdrant/storage']

        elif key == 'elasticsearch':
            service_config['environment'] = {
                'discovery.type': 'single-node',
                'ES_JAVA_OPTS': '-Xms512m -Xmx512m'
            }
            service_config['volumes'] = ['./es_data:/usr/share/elasticsearch/data']

        elif key == 'rabbitmq':
            service_config['ports'].append('15672:15672')  # Management UI
            service_config['volumes'] = ['./rabbitmq_data:/var/lib/rabbitmq']

        compose['services'][service_name] = service_config

    # Convert to YAML-like format
    import yaml
    return yaml.dump(compose, default_flow_style=False, sort_keys=False)


def generate_env_example(detected: Dict) -> str:
    """Generate .env.example content."""
    lines = [
        "# Wave 2 Preparation - Environment Variables",
        "# Copy this to .env and fill in actual values",
        "",
        "# Test Mode",
        "TEST_MODE=mock  # Options: mock, live",
        ""
    ]

    # LLM providers
    llms = detected.get('llm_providers', {})
    if llms:
        lines.append("# LLM Providers (for live testing)")
        for key, config in llms.items():
            lines.append(f"# {config['provider']}")
            for env_var in config['env_vars']:
                if 'KEY' in env_var:
                    lines.append(f"{env_var}=sk-...")
                elif 'URL' in env_var or 'HOST' in env_var:
                    lines.append(f"{env_var}=http://localhost:...")
                else:
                    lines.append(f"{env_var}=")
            lines.append("")

    # Infrastructure
    infra = detected.get('infrastructure', {})
    if infra:
        lines.append("# Infrastructure Services")
        for key, config in infra.items():
            lines.append(f"# {config['service']}")
            for env_var in config['env_vars']:
                if 'URL' in env_var:
                    lines.append(f"{env_var}=http://localhost:{config.get('port', 'PORT')}")
                elif 'HOST' in env_var:
                    lines.append(f"{env_var}=localhost")
                elif 'PORT' in env_var:
                    lines.append(f"{env_var}={config.get('port', 'PORT')}")
                elif 'PASSWORD' in env_var:
                    lines.append(f"{env_var}=dev_password_change_me")
                elif 'USER' in env_var:
                    lines.append(f"{env_var}=ucop")
                elif 'DB' in env_var and 'POSTGRES' in env_var:
                    lines.append(f"{env_var}=ucop_dev")
                else:
                    lines.append(f"{env_var}=")
            lines.append("")

    # Other common variables
    lines.extend([
        "# Logging",
        "LOG_LEVEL=INFO",
        "",
        "# Checkpoints",
        "CHECKPOINT_DIR=.checkpoints",
        ""
    ])

    return '\n'.join(lines)


def main():
    """Main entry point."""
    print("=== Infrastructure Detection (Wave 2 Prep) ===\n")

    repo_root = get_repo_root()

    # Find wave2_prep directory
    wave2_dirs = sorted((repo_root / 'reports' / 'wave2_prep').glob('*'), reverse=True)
    if wave2_dirs:
        output_dir = wave2_dirs[0] / '03_infra'
    else:
        output_dir = repo_root / 'reports' / 'infra_detection'

    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect infrastructure
    print("Scanning requirements.txt and imports...")
    detected = detect_infrastructure()

    print(f"Packages scanned: {detected['packages_scanned']}")
    print(f"Imports scanned: {detected['imports_scanned']}")
    print(f"Infrastructure detected: {len(detected['infrastructure'])}")
    print(f"LLM providers detected: {len(detected['llm_providers'])}")
    print()

    # Save detection results
    results = {
        'generated_at': datetime.now().isoformat(),
        'detected': detected
    }

    output_json = output_dir / 'infra_detect.json'
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[OK] Detection results saved to {output_json}")

    # Generate markdown report
    md_lines = [
        "# Infrastructure Detection Report",
        "",
        f"**Generated**: {datetime.now().isoformat()}",
        "",
        "## Summary",
        "",
        f"- **Packages Scanned**: {detected['packages_scanned']}",
        f"- **Imports Scanned**: {detected['imports_scanned']}",
        f"- **Infrastructure Services**: {len(detected['infrastructure'])}",
        f"- **LLM Providers**: {len(detected['llm_providers'])}",
        "",
        "## Infrastructure Services Detected",
        ""
    ]

    if detected['infrastructure']:
        for key, config in detected['infrastructure'].items():
            md_lines.append(f"### {config['service']}")
            md_lines.append(f"- **Package**: `{config['package']}`")
            if config['docker_image']:
                md_lines.append(f"- **Docker Image**: `{config['docker_image']}`")
                md_lines.append(f"- **Port**: {config['port']}")
            md_lines.append(f"- **Environment Variables**: {', '.join(config['env_vars'])}")
            md_lines.append("")
    else:
        md_lines.append("*No external infrastructure dependencies detected.*")
        md_lines.append("")

    md_lines.append("## LLM Providers Detected")
    md_lines.append("")

    if detected['llm_providers']:
        for key, config in detected['llm_providers'].items():
            md_lines.append(f"### {config['provider']}")
            md_lines.append(f"- **Package**: `{config['package']}`")
            md_lines.append(f"- **Environment Variables**: {', '.join(config['env_vars'])}")
            md_lines.append("")
    else:
        md_lines.append("*No LLM provider dependencies detected.*")
        md_lines.append("")

    output_md = output_dir / 'infra_detect.md'
    with open(output_md, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f"[OK] Markdown report saved to {output_md}")

    # Generate docker-compose
    try:
        import yaml
        compose_content = generate_docker_compose(detected)
        if compose_content:
            output_compose = output_dir / 'docker-compose.wave2.yml'
            with open(output_compose, 'w') as f:
                f.write(compose_content)
            print(f"[OK] docker-compose.wave2.yml saved to {output_compose}")
        else:
            print("[INFO] No infrastructure services with docker images detected - skipping docker-compose")
    except ImportError:
        print("[WARN] PyYAML not installed - skipping docker-compose generation")

    # Generate .env.example
    env_content = generate_env_example(detected)
    output_env = output_dir / '.env.example'
    with open(output_env, 'w') as f:
        f.write(env_content)

    print(f"[OK] .env.example saved to {output_env}")
    print("\nInfrastructure detection complete!")


if __name__ == '__main__':
    main()
