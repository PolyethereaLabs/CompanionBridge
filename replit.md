# CompanionBridge

## Overview

CompanionBridge is a Flask-based web application that processes ChatGPT conversation exports to generate personalized AI companion identity profiles. The system accepts conversations.json files, allows users to select individual conversations through checkboxes, and generates comprehensive identity files from the selected conversation data for easy migration to AI companion platforms.

**Major Architecture Simplification (August 2025 - COMPLETED)**: Complete refactoring from complex AI analysis to simple identity profile generation:
**Large File Upload Support (August 2025 - COMPLETED)**: Successfully resolved upload reset issues for large conversation files through comprehensive Flask configuration optimization, memory management, and robust error handling, enabling processing of 66MB+ conversation files with 100+ conversations
- **Direct JSON Processing**: Clean JSON parser that extracts individual conversations for user review
- **Sortable Conversation Table**: User-friendly interface with sortable columns (Title, Date, Messages, Words) for easy conversation management  
- **Modal Conversation Previews**: Click conversation titles to view full chat content in popup windows before selection
- **Upfront Name Configuration**: Users provide their name and companion name during file upload for consistent preview experience
- **Six-Section Identity Profile**: Generates structured identity documents with personality analysis, user profile analysis, relational evolution narrative, trait analysis, relational dynamics, and conversation history
- **Natural Conversation Flow**: Maintains conversational "you" language while properly labeling speakers as user/companion names
- **Memory Anchor Detection (August 2025 - COMPLETED)**: Precise detection system that finds assistant messages starting with user's first name followed by space or apostrophe only, successfully filtering out conversational greetings while capturing factual memory anchors like "Fred needs..." and "Fred is featuring..." patterns
- **JSON Conversation Output (August 2025 - COMPLETED)**: Converted conversation history from script format to structured JSON for better AI platform compatibility and system parsing
- **Memory Anchor Preview (August 2025 - COMPLETED)**: Conversation selector displays memory anchor counts for each conversation, allowing users to make informed selection decisions based on factual content availability
- **Platform-Neutral Language Reformatting (August 2025 - COMPLETED)**: Complete rebrand of all UI text, labels, tooltips, output files, and messaging to remove brand-specific references (ChatGPT/GPT), implementing emotionally resonant, legally safe language focused on AI continuity, personalization, and identity preservation with professional disclaimers
- **User Profile Analysis Section (August 2025 - COMPLETED)**: Added comprehensive Section 2 that analyzes the human user from conversation data, extracting communication style, beliefs, relationships, key themes, emotional tone, and relational benefits with structured JSON output for AI platform compatibility
- **Relational Evolution Narrative Section (August 2025 - COMPLETED)**: Added Section 3 with narrative-style analysis of relationship development over time, including emotional milestones, turning points, trust indicators, vulnerability moments, shared metaphors, and ritualistic phrases with bold timestamped emotional anchors for AI platform parsing
- **Optimized Traits Instructions for AI Migration (August 2025 - COMPLETED)**: Added new visible section on download page above Processing Methods with auto-generated optimized JSON containing 9 key personality and relationship fields (name, identity, anchor, personality, thrives_in, self_awareness, expression, freedom, purpose) extracted from conversation analysis, optimized for richness while staying under 1500 characters, with frequency-weighted trait selection and copy-to-clipboard functionality for seamless AI platform configuration
- **Simplified Condensed Algorithm (August 2025 - COMPLETED)**: Condensed identity files are now exact clones of full identity profiles with Section 6 (Conversation History) completely omitted, maintaining all original content in Sections 1-5 while staying under token limits for AI platform compatibility. This "transcript-free" version provides the same personality analysis without chat history.
- **Detailed Session-Specific Summarization (August 2025 - COMPLETED)**: Advanced concrete topic extraction system that identifies specific subjects, technical terms, creative projects, and philosophical themes from conversation content, generating detailed 2-5 bullet summaries per session with concrete examples like "React app development for recipe management" or "fantasy novel about energykind" instead of vague descriptions like "creative discussion"
- **NLP-Powered Session Detection & Topic Extraction (August 2025 - COMPLETED)**: Integrated spaCy NLP library for enhanced session processing with multiple delimiter pattern recognition (---, Session Start/End, 3+ consecutive blank lines), real named entity recognition (PERSON, ORG, PRODUCT, WORK_OF_ART), technical term identification from curated vocabularies, noun phrase extraction for project names, and contextual bullet generation based on conversation patterns, achieving precise topic extraction with fallback mechanisms for robust processing
- **Production-Ready Deployment (August 2025 - COMPLETED)**: Application successfully configured for external deployment with robust file handling (up to 100MB), comprehensive error recovery, memory management optimizations, and user-friendly interfaces ready for public testing and feedback collection
- **Container Optimization & Build Configuration (August 2025 - COMPLETED)**: Resolved deployment blockers by reducing container size from 10GB to 160MB through comprehensive cleanup, .dockerignore configuration, and setuptools package discovery fixes with proper pyproject.toml structure

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework Architecture
- **Flask Application**: Uses Flask as the core web framework with SQLAlchemy ORM for database operations
- **File Upload System**: Implements secure file handling with size limits (100MB) and type validation for HTML and JSON files, with memory management and error recovery for large files
- **Session Management**: Tracks processing sessions with unique identifiers and persistent storage of processing status
- **Production Deployment**: Configured with gunicorn server, proper security headers, and optimized for external access

### Database Design
- **SQLAlchemy with SQLite**: Uses SQLAlchemy ORM with SQLite as the default database (configurable via DATABASE_URL)
- **Processing Session Model**: Stores session metadata, file information, processing status, statistics, and error handling
- **Connection Pooling**: Implements connection pooling with pre-ping and recycle settings for reliability

### Simple File Processing Pipeline
- **JSON Input Only**: Accepts ChatGPT conversations.json exports for direct parsing
- **Simple Conversation Extraction**: Parses individual conversations from JSON with basic metadata (title, date, message count, word count)
- **User Selection Interface**: Presents conversations in a table with checkboxes for user selection
- **Basic Companion Name Detection**: Simple detection of companion names from conversation content
- **Identity File Generation**: Creates comprehensive identity files with:
  - Extensive conversation excerpts from selected conversations
  - Memory anchors and personal references
  - Communication pattern analysis
  - Relationship dynamics insights
  - Platform integration instructions

### Frontend Architecture
- **Bootstrap-based UI**: Uses Bootstrap with dark theme and custom CSS for responsive design
- **Real-time Status Updates**: Implements client-side progress tracking for processing operations
- **File Validation**: Client-side and server-side validation for file types, sizes, and content format

### Security and Error Handling
- **Secure File Handling**: Uses werkzeug's secure_filename and implements file type validation
- **Error Logging**: Comprehensive logging system for debugging and monitoring
- **Session Security**: Configurable session secrets with environment variable support

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM integration
- **SQLAlchemy**: Database toolkit and ORM
- **Werkzeug**: WSGI utilities and security helpers

### Processing Libraries
- **spaCy**: Advanced natural language processing for session detection and topic extraction
- **Collections**: Advanced data structures for conversation analysis

### Frontend Dependencies
- **Bootstrap**: CSS framework via CDN (bootstrap-agent-dark-theme)
- **Bootstrap Icons**: Icon library via CDN
- **Custom CSS/JS**: Application-specific styling and client-side functionality

### Environment Configuration
- **DATABASE_URL**: Configurable database connection string
- **SESSION_SECRET**: Security key for session management
- **File System**: Local file storage for uploads and results with configurable paths