from app.agents.base import call
from app.schemas import Plan


async def execute(context):
    return await call(
        "You are the Engineering Orchestrator. Analyze the requested engineering workflow, decompose it into practical milestones and tasks with dependencies and acceptance conditions. Use the selected language/framework. For review-only requests plan review, security and documentation only. Prefer a bounded runnable vertical slice for large requirements. List constraints honestly. Agents are requirements, architecture, database, code, review, security, testing_documentation. Do not grant approvals.",
        context,
        Plan,
    )
