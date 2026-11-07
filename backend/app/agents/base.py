from app.services.provider import provider


async def call(prompt, context, schema):
    return await provider.generate(prompt, context, schema)
