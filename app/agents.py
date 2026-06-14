from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelAPIError
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.openai import OpenAIProvider
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repository import (
    get_product_reviews,
    policy_sources,
    product_sources,
    review_sources,
    run_safe_sql,
    search_policies,
    search_products,
)
from app.schemas import AgentName, AgentRoute, SpecialistAnswer

NO_INFORMATION = "I do not have the information."


@dataclass
class AgentDeps:
    session: AsyncSession
    conversation_context: str = ""
    customer_preferences: dict[str, Any] | None = None


def configured_model() -> OpenAIChatModel | TestModel:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIChatModel(
            settings.openai_model,
            provider=OpenAIProvider(api_key=settings.openai_api_key),
        )
    return TestModel()


coordinator_agent = Agent(
    configured_model(),
    deps_type=AgentDeps,
    output_type=AgentRoute,
    system_prompt=(
        "Route the customer query to exactly one specialist: product_recommendation, "
        "review_summarization, price_comparison, or faq_policy. Never request or expose PII."
    ),
)

product_agent = Agent(
    configured_model(),
    deps_type=AgentDeps,
    output_type=SpecialistAnswer,
    system_prompt=(
        "Recommend products using catalog data only. Respect budget, category, and feature needs. "
        "Do not infer protected traits or expose personal data. If catalog tools return no "
        f"relevant rows, say exactly: {NO_INFORMATION}"
    ),
)

review_agent = Agent(
    configured_model(),
    deps_type=AgentDeps,
    output_type=SpecialistAnswer,
    system_prompt=(
        "Summarize product reviews with sentiment, recurring pros, recurring cons, and confidence. "
        "Be concise and cite review records. If review tools return no relevant rows, say "
        f"exactly: {NO_INFORMATION}"
    ),
)

price_agent = Agent(
    configured_model(),
    deps_type=AgentDeps,
    output_type=SpecialistAnswer,
    system_prompt=(
        "Compare prices and features across brands using product catalog data. "
        "Highlight tradeoffs and avoid unsupported claims. If catalog tools return no relevant "
        f"rows, say exactly: {NO_INFORMATION}"
    ),
)

policy_agent = Agent(
    configured_model(),
    deps_type=AgentDeps,
    output_type=SpecialistAnswer,
    system_prompt=(
        "Answer FAQ, return, refund, shipping, warranty, and store policy "
        "questions using policy data. "
        "Escalate ambiguity instead of inventing policy. If policy tools return no relevant "
        f"rows, say exactly: {NO_INFORMATION}"
    ),
)


async def _catalog_tool(ctx: RunContext[AgentDeps], query: str) -> str:
    products = await search_products(ctx.deps.session, query)
    return "\n".join(
        f"{p.sku} | {p.brand} | {p.name} | {p.category} | ${p.price:.2f} | {p.features}"
        for p in products
    )


async def _reviews_tool(ctx: RunContext[AgentDeps], query: str) -> str:
    reviews = await get_product_reviews(ctx.deps.session, query)
    return "\n".join(
        f"{r.id} | {r.product_sku} | {r.rating}/5 | {r.title}: {r.body}" for r in reviews
    )


async def _policies_tool(ctx: RunContext[AgentDeps], query: str) -> str:
    policies = await search_policies(ctx.deps.session, query)
    return "\n".join(f"{p.id} | {p.topic} | {p.question} | {p.answer}" for p in policies)


async def _sql_tool(ctx: RunContext[AgentDeps], sql: str) -> str:
    rows = await run_safe_sql(ctx.deps.session, sql)
    return "\n".join(str(row) for row in rows)


for agent in (product_agent, review_agent, price_agent, policy_agent):
    agent.tool(_catalog_tool)
    agent.tool(_reviews_tool)
    agent.tool(_policies_tool)
    agent.tool(_sql_tool)


def _has_openai_key() -> bool:
    return bool(get_settings().openai_api_key)


def _route_locally(query: str) -> AgentName:
    lowered = query.lower()
    policy_terms = ("return", "refund", "policy", "shipping", "warranty", "exchange")
    if any(word in lowered for word in policy_terms):
        return AgentName.faq_policy
    if any(word in lowered for word in ("review", "sentiment", "pros", "cons", "rating")):
        return AgentName.review_summarization
    if any(word in lowered for word in ("compare", "price", "cheapest", "brand", "versus", "vs")):
        return AgentName.price_comparison
    return AgentName.product_recommendation


async def route_query(query: str, deps: AgentDeps) -> AgentRoute:
    if _has_openai_key():
        prompt = f"Context:\n{deps.conversation_context}\n\nCustomer query:\n{query}"
        try:
            result = await coordinator_agent.run(prompt, deps=deps)
            return result.output
        except ModelAPIError:
            return AgentRoute(agent=_route_locally(query), rationale="Local fallback route.")
    return AgentRoute(agent=_route_locally(query), rationale="Local keyword route.")


async def answer_with_agent(agent_name: AgentName, query: str, deps: AgentDeps) -> SpecialistAnswer:
    empty_answer = await _empty_if_no_evidence(agent_name, query, deps)
    if empty_answer:
        return empty_answer

    if _has_openai_key():
        prompt = (
            f"Conversation context, redacted and ephemeral:\n{deps.conversation_context}\n\n"
            f"Customer preferences:\n{deps.customer_preferences or {}}\n\nQuery:\n{query}"
        )
        agent = {
            AgentName.product_recommendation: product_agent,
            AgentName.review_summarization: review_agent,
            AgentName.price_comparison: price_agent,
            AgentName.faq_policy: policy_agent,
        }[agent_name]
        try:
            result = await agent.run(prompt, deps=deps)
            return result.output
        except ModelAPIError:
            return await _fallback_answer(agent_name, query, deps)
    return await _fallback_answer(agent_name, query, deps)


async def _empty_if_no_evidence(
    agent_name: AgentName, query: str, deps: AgentDeps
) -> SpecialistAnswer | None:
    if agent_name == AgentName.faq_policy:
        policies = await search_policies(deps.session, query)
        if not policies:
            return SpecialistAnswer(answer=NO_INFORMATION, sources=[])
        return None

    if agent_name == AgentName.review_summarization:
        reviews = await get_product_reviews(deps.session, query)
        if not reviews:
            return SpecialistAnswer(answer=NO_INFORMATION, sources=[])
        return None

    if agent_name in {AgentName.product_recommendation, AgentName.price_comparison}:
        products = await search_products(deps.session, query)
        if not products:
            return SpecialistAnswer(answer=NO_INFORMATION, sources=[])
    return None


async def _fallback_answer(agent_name: AgentName, query: str, deps: AgentDeps) -> SpecialistAnswer:
    if agent_name == AgentName.faq_policy:
        policies = await search_policies(deps.session, query)
        answer = " ".join(f"{p.topic} - {p.question}: {p.answer}" for p in policies[:3])
        return SpecialistAnswer(
            answer=answer or NO_INFORMATION,
            sources=policy_sources(policies),
        )

    if agent_name == AgentName.review_summarization:
        reviews = await get_product_reviews(deps.session, query)
        if not reviews:
            return SpecialistAnswer(answer=NO_INFORMATION, sources=[])
        avg = sum(review.rating for review in reviews) / len(reviews)
        pros = [review.title for review in reviews if review.rating >= 4][:3]
        cons = [review.title for review in reviews if review.rating <= 3][:3]
        answer = (
            f"Average sentiment is {avg:.1f}/5 across {len(reviews)} reviews. "
            f"Common positives: {', '.join(pros) or 'not enough positive themes'}. "
            f"Common concerns: {', '.join(cons) or 'few recurring concerns'}."
        )
        return SpecialistAnswer(answer=answer, sources=review_sources(reviews))

    products = await search_products(deps.session, query)
    if agent_name == AgentName.price_comparison:
        ordered = sorted(products, key=lambda product: product.price)
        answer = " | ".join(
            f"{p.brand} {p.name}: ${p.price:.2f}, {p.features}" for p in ordered[:5]
        )
        return SpecialistAnswer(
            answer=answer or NO_INFORMATION,
            sources=product_sources(ordered),
        )

    answer = " ".join(
        f"I recommend {p.brand} {p.name} (${p.price:.2f}) because it offers {p.features}."
        for p in products[:3]
    )
    return SpecialistAnswer(
        answer=answer or NO_INFORMATION,
        sources=product_sources(products),
    )
