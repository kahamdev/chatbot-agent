from chatbot_agent.evals import run


def test_local_evaluation_cases() -> None:
    assert run() == 0
