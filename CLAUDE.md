# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent smart shopping system using Google's ADK (Agent Development Kit) framework. The system helps users compare products across stores and recommends optimal purchasing decisions.

## Architecture

### Agent Hierarchy

**Orchestrator Agent** (Main Coordinator)
- Routes user requests to appropriate subagents
- Manages multi-agent workflows
- Aggregates results from subagents
- Returns final recommendations to the chat interface

**Product Normalizer Agent**
- Finds all products available in the same store
- Normalizes product data across different store formats
- Handles product search and matching

**Optimizer Agent**
- Computes price differences between items across stores
- Calculates total costs and savings
- Performs comparison analytics

**Evaluator Agent**
- Recommends where to buy items based on optimizer results
- Considers factors like total price, availability, and convenience
- Provides final purchasing recommendations

### Communication Flow

1. User submits query via chat interface
2. Backend API receives request
3. Orchestrator agent analyzes request and routes to subagents
4. Product Normalizer finds products in stores
5. Optimizer calculates price differences
6. Evaluator recommends optimal purchase strategy
7. Orchestrator aggregates and returns results

## Technical Stack

- **Framework**: Google ADK for multi-agent orchestration
- **Frontend**: Streamlit (Python-native chat interface with built-in components)
- **Language**: Python (entire stack)

## Development Notes

### Multi-Agent Coordination

The orchestrator uses ADK's multi-agent capabilities to manage subagent interactions. Each subagent should be designed with:
- Clear input/output contracts
- Specific tools and functions for their domain
- Error handling for their specialized tasks

### Agent Communication Protocol

Subagents communicate through the orchestrator, not directly with each other. The typical flow is sequential:
Product Normalizer → Optimizer → Evaluator

However, the orchestrator should be flexible enough to parallelize or reorder steps when appropriate.

### Key Implementation Considerations

1. Product data normalization is critical - different stores may have different product identifiers, names, and formats
2. Price comparison must account for quantities, units, and packaging differences
3. The evaluator should consider multiple factors beyond just price (availability, store proximity, bulk discounts)
4. All agent interactions should be logged for debugging and monitoring
5. Implement fallback mechanisms when products aren't found or data is incomplete
