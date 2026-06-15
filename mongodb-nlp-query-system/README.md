# MongoDB NLP Query System

A powerful natural language interface for MongoDB that allows users to query databases using everyday language. The system automatically generates safe MongoDB queries, prevents destructive operations, and provides export capabilities.

## 🚀 Features

- **Natural Language Processing**: Convert English queries to MongoDB queries
- **Safety First**: Automatically blocks DELETE, UPDATE, and INSERT operations
- **Smart Caching**: Reuses similar queries for better performance
- **Export Capabilities**: Download results as CSV/Excel or email them
- **Beautiful UI**: Responsive Bootstrap 5 interface
- **REST API**: Complete API with OpenAPI documentation
- **Docker Ready**: Easy deployment with docker-compose

## 📋 Prerequisites

- Python 3.9+
- MongoDB 6.0+
- Redis (optional, for caching)
- Docker & Docker Compose (optional)

## 🛠️ Installation

### Option 1: Local Development

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/mongodb-nlp-query-system.git
cd mongodb-nlp-query-system