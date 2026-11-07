from app.agents.base import call
from app.schemas import SRS


async def execute(context):
    return await call(
        "You are the Requirement Intelligence Agent. Produce a concise complete SRS from the requirement and existing project decisions. Include functional and non-functional requirements, business rules, user stories with testable acceptance criteria, edge cases, complexity, assumptions and unresolved questions. Distinguish stated requirements from assumptions. Do not invent performance measurements or pretend an unanswered question was answered.",
        context,
        SRS,
    )
