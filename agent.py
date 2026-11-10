import inspect
import json

from openai import OpenAI

# Step 1: import both tool functions, so the dictionary below can point at them.
from tools import TOOLS, calculate_stat, load_csv_summary

# Step 2: map each tool name to the function that runs it, one line per tool.
TOOL_FUNCTIONS = {
    "load_csv_summary": load_csv_summary,
    "calculate_stat": calculate_stat,
}

# Step 5: hard cap on tool rounds per user message, so a confused model can't loop forever.
MAX_TOOL_ROUNDS = 5

# Step 6: tell the model which tools exist, when to use them, and when not to.
SYSTEM_MESSAGE = (
    "You are a helpful assistant. The user's data is in grades.csv. "
    "You have two tools: load_csv_summary gives the columns, the row count and "
    "which columns are numeric; calculate_stat gives the mean, median, std, min "
    "or max of a numeric column. "
    "Use calculate_stat for any number about the data, and never calculate "
    "statistics yourself. "
    "Use the tools only for questions about the data. For general questions or "
    "simple math, answer directly in plain sentences, and never write a tool "
    "request as JSON text."
)

def get_llm_client():
    return OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )


def tool_error(message):
    """Print a short error line and return the JSON error the model will read."""
    print(f"[tool error] {message}")
    return json.dumps({"error": message})


def run_tool(name, raw_arguments, on_tool_call=None):
    """Run one tool by name from a raw JSON argument string. Never raises.

    Returns the JSON string that should be handed back as the tool result.
    `on_tool_call(name, raw_arguments)` is called too, so a UI can display it.
    """
    # Step 7: always show the call, even when the arguments will not parse.
    print(f"[tool call] {name}({raw_arguments})")

    # Step 7b: let an optional caller (the Streamlit app) know a tool ran.
    if on_tool_call is not None:
        on_tool_call(name, raw_arguments)

    # Step 4: look the function up, and report unknown names instead of crashing.
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return tool_error(f"Unknown tool: {name}. Available tools: {list(TOOL_FUNCTIONS)}")

    # Step 4: parse the arguments and run the tool; any failure becomes a tool result.
    try:
        arguments = json.loads(raw_arguments)
        result = function(**arguments)
    except json.JSONDecodeError as exc:
        return tool_error(f"Arguments were not valid JSON: {exc}")
    except TypeError:
        accepted = ", ".join(inspect.signature(function).parameters)
        return tool_error(
            f"{name} accepts these arguments: {accepted}. You sent: {arguments}"
        )
    except Exception as exc:
        return tool_error(f"{name} failed: {exc}")

    # Step 4: on success, serialize the returned dict as the tool's content.
    return json.dumps(result)


def run_tool_call(tool_call, on_tool_call=None):
    """Run one API tool call and return (tool_call_id, content) for the tool message."""
    content = run_tool(tool_call.function.name, tool_call.function.arguments, on_tool_call)
    return tool_call.id, content


def extract_tool_request(text):
    """Find a tool request written as plain text; return (name, parameters) or None."""
    # Step 1: take the text from the first "{" to the last "}".
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    # Step 2: it counts only if that slice is valid JSON with a name and parameters.
    try:
        payload = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str):
        return None

    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        parameters = payload.get("arguments")
    if not isinstance(parameters, dict):
        return None

    return payload["name"], parameters


def ask_model(client, messages, on_tool_call=None):
    """Call the model, run any tools it asks for, and return the final reply.

    Handles both real tool_calls and tool requests written as plain text.
    `on_tool_call(name, raw_arguments)` is passed through to run_tool.
    """
    for _ in range(MAX_TOOL_ROUNDS):
        # Step 3: send the conversation plus the tool descriptions.
        response = client.chat.completions.create(
            model="llama3.2:3b",
            messages=messages,
            tools=TOOLS,
            temperature=0.1,
        )
        message = response.choices[0].message

        # Step 4: no tool_calls means a plain answer, or a request written as text.
        if not message.tool_calls:
            text = message.content or ""

            # Step 5: if there is no JSON in the reply, this is the final answer.
            request = extract_tool_request(text)
            if request is None:
                return text

            name, parameters = request

            # Step 2: run it through the shared runner, so prints and errors match.
            result = run_tool(name, json.dumps(parameters), on_tool_call)

            if name in TOOL_FUNCTIONS:
                # Step 3: do not store the model's text, just feed back the result.
                content = (
                    f"Tool result for {name}: {result}. "
                    f"Now answer my question in plain sentences."
                )
            else:
                # Step 4: nothing ran, so say the tool is unknown and ask for text.
                content = (
                    f"The tool '{name}' does not exist. The only tools are: "
                    f"{', '.join(TOOL_FUNCTIONS)}. Answer my question in plain text."
                )
            messages.append({"role": "user", "content": content})
            continue

        # Step 4: store the model's tool request before replying to it.
        messages.append(message)

        # Step 4: answer every call, then loop so the model can use those results.
        for tool_call in message.tool_calls:
            tool_call_id, content = run_tool_call(tool_call, on_tool_call)
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
