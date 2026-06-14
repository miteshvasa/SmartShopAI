import asyncio
import json
from pathlib import Path

import httpx

from app.agents import AgentDeps, answer_with_agent, route_query
from app.db import SessionLocal, init_db
from app.schemas import ChatRequest

DATASET = Path("evals/agent_eval_dataset.jsonl")
API_URL = "http://localhost:8000/chat"


async def run_case_local(case: dict) -> dict:
    async with SessionLocal() as session:
        deps = AgentDeps(session=session)
        route = await route_query(case["query"], deps)
        answer = await answer_with_agent(route.agent, case["query"], deps)
        return {"agent": route.agent.value, "answer": answer.answer}


async def run_case_api(client: httpx.AsyncClient, case: dict) -> dict:
    response = await client.post(API_URL, json=ChatRequest(query=case["query"]).model_dump())
    response.raise_for_status()
    return response.json()


def score(case: dict, result: dict) -> tuple[bool, list[str]]:
    failures = []
    if result["agent"] != case["expected_agent"]:
        failures.append(f"agent expected {case['expected_agent']} got {result['agent']}")
    answer = result["answer"].lower()
    for phrase in case["must_include"]:
        if phrase.lower() not in answer:
            failures.append(f"missing phrase: {phrase}")
    return not failures, failures


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]


async def main(cases: list[dict]) -> None:
    await init_db()
    passed = 0
    async with httpx.AsyncClient(timeout=20) as client:
        for case in cases:
            try:
                result = await run_case_api(client, case)
            except Exception:
                result = await run_case_local(case)
            ok, failures = score(case, result)
            passed += int(ok)
            status = "PASS" if ok else "FAIL"
            print(f"{status}: {case['query']}")
            for failure in failures:
                print(f"  - {failure}")
    print(f"\n{passed}/{len(cases)} passed")


if __name__ == "__main__":
    asyncio.run(main(load_cases()))
