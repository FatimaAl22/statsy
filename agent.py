import inspect
import json

from openai import OpenAI

from tools import TOOLS, load_csv_summary

# Step 2: map each tool name to the function that runs it. Adding a tool later
# means one new line here (plus its description in TOOLS over in tools.py).
TOOL_FUNCTIONS = {
    "load_csv_summary": load_csv_summary,
}

# Step 5: hard cap on tool rounds per user message, so a confused model can't loop forever.
MAX_TOOL_ROUNDS = 5

# Step 6: tell the model where the user's data lives and which tool reads it.
SYSTEM_MESSAGE = (
    "You are a helpful assistant. The user's data is in grades.csv. "
    "Use the load_csv_summary tool only when the user asks about that data: "
    "its columns, row count or numeric columns. "
    "For any other question, such as general knowledge, answer directly "
    "and do not call any tool."
)

def get_llm_client():
    return OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )


def tool_error(tool_call_id, message):
    """Print a short error line and build the JSON result the model will read."""
    print(f"[tool error] {message}")
    return tool_call_id, json.dumps({"error": message})


def run_tool_call(tool_call):
    """Run one tool call and return (tool_call_id, content) for the tool message."""
    # Step 4: read the function name and the raw JSON argument string.
    name = tool_call.function.name
    raw_arguments = tool_call.function.arguments

    # Step 7: always show the call, even when the arguments will not parse.
    print(f"[tool call] {name}({raw_arguments})")

    # Step 4: look the function up, and report unknown names instead of crashing.
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return tool_error(tool_call.id, f"Unknown tool: {name}. Available tools: {list(TOOL_FUNCTIONS)}")

    # Step 4: parse the arguments and run the tool; any failure becomes a tool result.
    try:
        arguments = json.loads(raw_arguments)
        result = function(**arguments)
    except json.JSONDecodeError as exc:
        return tool_error(tool_call.id, f"Arguments were not valid JSON: {exc}")
    except TypeError:
        accepted = ", ".join(inspect.signature(function).parameters)
        return tool_error(
            tool_call.id,
            f"{name} accepts these arguments: {accepted}. You sent: {arguments}",
        )
    except Exception as exc:
        return tool_error(tool_call.id, f"{name} failed: {exc}")

    # Step 4: on success, serialize the returned dict as the tool's content.
    return tool_call.id, json.dumps(result)


def ask_model(client, messages):
    """Call the model, run any tool calls it asks for, and return the final reply."""
    for _ in range(MAX_TOOL_ROUNDS):
        # Step 3: send the conversation plus the tool descriptions.
        response = client.chat.completions.create(
            model="llama3.2:3b",
            messages=messages,
            tools=TOOLS,
            temperature=0.1,
        )
        message = response.choices[0].message

        # Step 4: no tool_calls means the model answered on its own, so we are done.
        if not message.tool_calls:
            return message.content

        # Step 4: store the model's tool request before replying to it.
        messages.append(message)

        # Step 4: answer every call, then loop so the model can use those results.
        for tool_call in message.tool_calls:
            tool_call_id, content = run_tool_call(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": content,
                }
            )

    # Step 5: the loop hit the cap, so give the user a plain answer instead of hanging.
    return f"Sorry, I stopped after {MAX_TOOL_ROUNDS} tool rounds without a final answer."


def agent_loop(client):
    # Step 6: the system message now points at grades.csv.
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
    ]

    while True:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        messages.append({"role": "user", "content": user_input})
        reply = ask_model(client, messages)
        print(f"Assistant: {reply}")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    client = get_llm_client()
    agent_loop(client)
