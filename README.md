# <i>Reflo</i>
### Reflowing revenue that almost got stuck.

A bounded, auditable agent that detects failed subscription payments, classifies the root cause, decides a recovery action within a fixed action set, gates it
against explicit guardrails, executes it against Razorpay test-mode APIs, and logs a complete audit trail.

Built for Razorpay's AI Buildathon — Track: AI Revenue Recovery.

See `docs/ARCHITECTURE.md` for the full SRS/SDD.

You can explore the live deployment of this project here:
👉 **[Live Link](https://reflo-recovery-agent.vercel.app/)**

> ⚠️ **Note on Deployment:** This project is hosted on a free instance on Render. If the application has been idle, it may take around **10 to 15 seconds** to spin up and load the initial page while the server wakes up. Thank you for your patience!

## Repo layout
- `backend/` — FastAPI service. Deploy target: **Render**.
- `frontend/` — Next.js dashboard (Recovery Queue, Case Detail, Batch Metrics, Guardrail Config). Deploy target: **Vercel**.
- `docs/` — architecture and design documentation.

## Local dev
```
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
## Architecture
<img width="1024" height="765" alt="image" src="https://github.com/user-attachments/assets/9d3cf84d-c467-4a08-b0e4-0571ff99f7c6" />

## Author

**Sanskar Gupta**  
AI/ML Engineering Student  
Building practical AI systems with Python, LangChain, FAISS, and LLMs.

GitHub: 

--- https://github.com/sanskarhere/Reflo.git

## License

MIT License


## 📦 Installation

```bash
git clone https://github.com/sanskarhere/Reflo.git
pip install -r requirements.txt



