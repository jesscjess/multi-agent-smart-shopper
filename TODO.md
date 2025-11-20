# Multi-Agent System with Chat Interface - TODO

## Project Overview
Building a multi-agent system using Google's ADK framework with:
- 1 Main orchestrator agent
- 3 Specialized subagents
- Web-based chat interface
- Backend API integration

## Architecture Plan
**Orchestrator Agent**: Main coordinator for routing requests and managing subagent interactions
**Product Normalizer Agent**: Finds all products in the same store and normalizes product data
**Optimizer Agent**: Computes price differences between items across stores
**Evaluator Agent**: Recommends where to buy items based on optimization results
**Chat Interface**: Web-based frontend with real-time communication
**Backend API**: Handles chat requests and agent orchestration

## TODO List

### Phase 1: Setup & Architecture
- [x] Define the 3 subagent roles and capabilities
- [x] Create CLAUDE.md documentation for future development
- [ ] Set up project structure and ADK installation
- [ ] Design the orchestrator agent architecture
- [ ] Define data models for products, stores, and prices
- [ ] Design API contracts between agents

### Phase 2: Core Implementation
- [ ] Implement the main orchestrator agent
- [ ] Implement Product Normalizer Agent
  - [ ] Product search functionality
  - [ ] Store-specific data adapters
  - [ ] Product matching and normalization logic
- [ ] Implement Optimizer Agent
  - [ ] Price comparison algorithms
  - [ ] Cost calculation across stores
  - [ ] Savings analysis
- [ ] Implement Evaluator Agent
  - [ ] Recommendation engine
  - [ ] Multi-factor evaluation (price, availability, convenience)
  - [ ] Result ranking and formatting
- [ ] Set up inter-agent communication and coordination

### Phase 3: Interface & Integration
- [ ] Create the chat interface frontend using Streamlit
  - [ ] Install Streamlit and set up basic app structure
  - [ ] Implement chat UI with st.chat_message and st.chat_input
  - [ ] Connect frontend to orchestrator agent
  - [ ] Add session state management for conversation history
- [ ] Add logging and monitoring for agent interactions
- [ ] Implement error handling and fallback mechanisms
- [ ] Add loading states and progress indicators in UI

### Phase 4: Testing & Deployment
- [ ] Test individual agents independently
- [ ] Test full multi-agent workflow integration
- [ ] Set up deployment configuration (local/cloud)

## Key Technical Considerations
1. Use ADK's multi-agent orchestration capabilities
2. Implement proper error handling and fallback mechanisms
3. Design clear communication protocols between agents
4. Include monitoring and logging for debugging
5. Plan for both local development and scalable deployment

## Questions Answered
- ✓ What are the specific roles/capabilities for the 3 subagents?
  - Product Normalizer, Optimizer, and Evaluator (see Architecture Plan)
- ✓ What frontend framework preference for the chat interface?
  - Streamlit (Python-native, fast setup, built-in chat components)

## Open Questions
- What type of tasks/queries should the system handle? (e.g., "Find cheapest place to buy milk and eggs")
- Local development vs cloud deployment preference?
- Which stores/retailers should be supported initially?
- Will store data come from APIs, web scraping, or manual entry?
- Authentication and user management requirements?