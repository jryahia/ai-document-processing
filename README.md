# AI Document Processing

**Document processing app: OCR for PDFs, scans and images, AI organization, semantic search and report generation.**

![TypeScript](https://img.shields.io/badge/TypeScript-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![React](https://img.shields.io/badge/React-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![Python](https://img.shields.io/badge/Python-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![OCR](https://img.shields.io/badge/OCR-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![OpenAI](https://img.shields.io/badge/OpenAI-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![Docker](https://img.shields.io/badge/Docker-161b22?style=for-the-badge&labelColor=161b22&color=161b22) ![Nginx](https://img.shields.io/badge/Nginx-161b22?style=for-the-badge&labelColor=161b22&color=161b22)

```mermaid
flowchart LR
    S0["PDF / scan / image upload"]
    S1["OCR text extraction"]
    S2["AI classification + organization"]
    S3["Semantic search index"]
    S4["Search + generated reports"]
    S0 --> S1 --> S2 --> S3 --> S4
```

## Problem it solves

Scanned documents are unsearchable until someone types them up. This app extracts text with OCR, organizes documents with AI and makes the whole library searchable by meaning.

An AI-powered document processing SaaS platform that extracts text from PDFs, scans, and images using OCR. Organizes content intelligently with AI, enables semantic search across your document library, and generates AI-powered reports.

## Features
- PDF/image OCR
- Semantic search
- Document organization
- Batch processing
- AI report generation

## Tech Stack
TypeScript, React, FastAPI, OCR, Vector DB