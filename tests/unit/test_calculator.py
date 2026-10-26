from chatbot_agent.tools.calculator import calculate


def test_basic_arithmetic() -> None:
    assert calculate("2 + 2") == "4"
    assert calculate("(2+3)*4") == "20"
    assert calculate("-3 + 5") == "2"
    assert calculate("10 / 2") == "5"


def test_rejects_code_and_large_work() -> None:
    assert "unsupported" in calculate("__import__('os').system('ls')")
    assert calculate("2 ** 10") == "Exponentiation is not supported."
    assert "too long" in calculate("1+" * 80 + "1")
    assert calculate("1 / 0") == "Division by zero."
    assert "too large" in calculate(f"{10**12} * {10**12}")
