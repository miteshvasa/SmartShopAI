from app.agents import _route_locally
from app.schemas import AgentName


def test_local_routing() -> None:
    assert _route_locally("what is the refund policy") == AgentName.faq_policy
    assert _route_locally("compare headphone prices") == AgentName.price_comparison
    assert _route_locally("summarize reviews for headphones") == AgentName.review_summarization
    assert _route_locally("recommend shoes") == AgentName.product_recommendation
