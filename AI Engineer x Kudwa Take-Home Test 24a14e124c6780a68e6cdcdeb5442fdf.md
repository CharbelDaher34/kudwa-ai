# AI Engineer x Kudwa Take-Home Test

Build an intelligent financial data processing system that demonstrates your expertise in AI/ML integration, backend architecture, and API design. This challenge focuses on PRACTICAL PROBLEM-SOLVING and ARCHITECTURAL THINKING with strong emphasis on AI capabilities.

## 🧪 **PROJECT OVERVIEW**

You'll integrate diverse financial data sources into a unified backend system and enrich it with powerful AI capabilities. This directly reflects one of Kudwa's core technical challenges: integrating diverse financial data sources into a coherent and reliable single source of truth, enhanced with intelligent AI-powered insights.

## 🏅 THE CHALLENGE

Design and implement a system that can:

1. INTEGRATE financial data from both provided sources
2. PROCESS and validate financial data with intelligent error handling
3. EXPOSE clean APIs for data access and analysis
4. PROVIDE AI-powered insights and natural language interactions

## 🗒️ **CORE REQUIREMENTS**

1. **Backend Architecture (Simplified for AI Focus)**

- Framework: Your choice (FastAPI)
- Database: Simple setup (SQLite acceptable)
- Data Integration: Focus on parsing and basic transformation
- API Design: RESTful endpoints

1. **AI Integration (A is mandatory; B is optional)**

**A. Natural Language Querying**

- Enable users to query financial data naturally through API endpoints.
- Integrate backend logic with LLM to interpret queries, fetch relevant data, and present clear answers
- Generate concise, insightful narratives from the integrated data, with clear answers and supporting data
- Handle follow-up questions and context-aware conversations
- Question examples:
    - "What was the total profit in Q1?"
    - "Show me revenue trends for 2024"
    - "Which expense category had the highest increase this year?"
    - "Compare Q1 and Q2 performance"
- Output Examples:
    - "Revenue increased by 10% in Q2, primarily driven by strong sales growth"
    - "Operating expenses rose 15% due to increased payroll and office costs"
    - "Cash flow improved significantly with better collection rates"
    - "Seasonal patterns show December revenue peaks at 180% of monthly average"

*Optional: log reasoning traces, tool calls, etc.*

**B. AI Analytics (great to have but not mandatory, choose one)**

- Comparative analysis across time periods
- Anomaly detection in financial patterns
- Revenue/expense forecasting and trend analysis
- Financial health scoring and risk assessment

*Note: keep it simple. A full fledged tool like the above would take too much time.*

---

1. **Data Processing (Focused on AI Preparation)**
- Parse both JSON data formats into a workable structure
- Basic data validation and quality checks
- Handle missing/inconsistent data intelligently
- Prepare data for AI analysis and querying

1. **Technical Quality**
- Clean Architecture: Well-structured, maintainable code
- Documentation: 1-2 pages technical report summarizing design decisions
- Error Handling: Focus on AI component reliability

## 🖊️ ADDITIONAL DETAIL

**API ENDPOINTS DESIGN**

Design clean RESTful endpoints that support the required AI features. Focus on practical implementation over detailed specification.

## 📒 DELIVERABLES

1. **Working AI-Powered Backend System**
- Complete API with natural language query support
- Natural language financial insights/summaries generation
- Advanced analytics features (optional)

1. **Code Repository with README**
- Clean, well-organized codebase
- Clear `README.md` with:
    - Setup instructions
    - Database initialization steps
    - API usage (if relevant)
- **Makefile** for simplified setup and common tasks (optional)

1. **Technical Documentation**
- 1-2 pages technical report summarizing design decisions. Examples of possible sections:
    - Project overview and architecture
    - Technology stack and rationale (especially AI/LLM choices)
    - Setup and installation instructions
    - AI/ML approach explanation and model choices
    - Known issues and limitations

1. **Demo Friendly System**
- DEPLOYED APIs or easy local setup (you can also use [render.com](http://render.com) for free deployments)
- Working endpoints demonstrable via API calls

**DEPLOYMENT EXPECTATIONS**

We highly value:

- Deployed APIs accessible via URL with live documentation
- Clear instructions for local development setup

## 🏆 **SUCCESS TIPS**

- AI First: Focus your energy on making the AI features exceptional
- Start with One Source: Get QuickBooks data working perfectly, then add Rootfi
- Document AI Decisions: Especially your LLM integration and model choices
- Test AI Thoroughly: Include edge cases and error scenarios for AI components
- Be Deployment Ready: Shows production-ready thinking
- Focus on Value: Make your AI features as real-life as possible

## **Ready to showcase your senior AI engineering skills?**

We're excited to see your approach to building production-quality AI-powered backend systems. Remember: we're evaluating your AI INTEGRATION DEPTH, BACKEND ARCHITECTURE, and PROBLEM-SOLVING ABILITIES.

## ⌛ Timeline?

You have 5 days to complete this test. Focus on Quality over Quantity, and do not hesitate to ask us business or other questions!

## 💰 Budget?

We can make available a 10$ budget for API calls. Please reach out to access this.

## 💽 Data Required for Exercise

- You will be required to use the below dataset

[data_set_1.json](AI%20Engineer%20x%20Kudwa%20Take-Home%20Test%2024a14e124c6780a68e6cdcdeb5442fdf/data_set_1.json)

[data_set_2.json](AI%20Engineer%20x%20Kudwa%20Take-Home%20Test%2024a14e124c6780a68e6cdcdeb5442fdf/data_set_2.json)

# Good luck! 🚀🚀🚀

---

## 💰 BONUS FEATURES (Great-to-Have)

- Basic eval for direct data querying
- Docker containerization with docker-compose setup
- Performance monitoring and logging
- Additional LLM model comparisons or A/B testing