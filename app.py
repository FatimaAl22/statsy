import streamlit as st

# Step 1: reuse the agent module; no tool logic is copied here.
import agent

st.title("statsy")
st.caption(
    "Answers questions about grades.csv using two tools: "
    "load_csv_summary and calculate_stat."
)

# Step 2: build the client and message list once, kept across Streamlit reruns.
if "client" not in st.session_state:
    st.session_state.client = agent.get_llm_client()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": agent.SYSTEM_MESSAGE}]
if "chat" not in st.session_state:
    st.session_state.chat = []  # display-only copy: role, content, tool calls

# Step 3: sidebar reset button clears the conversation, keeping the system message.
with st.sidebar:
    if st.button("Clear chat"):
        st.session_state.messages = [{"role": "system", "content": agent.SYSTEM_MESSAGE}]
        st.session_state.chat = []
        st.rerun()

# Step 4: draw the history. "chat" holds only user and assistant entries, so the
# system message and any tool messages sent to the model never reach the screen.
for entry in st.session_state.chat:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
        if entry.get("tools"):
            st.caption("Tools used: " + "; ".join(entry["tools"]))

# Step 5: read the user's question from the chat box.
question = st.chat_input("Ask about grades.csv")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.chat.append({"role": "user", "content": question})

    # Step 6: ask the agent, collecting each tool call for display.
    calls = []
    with st.spinner("Thinking..."):
        reply = agent.ask_model(
            st.session_state.client,
            st.session_state.messages,
            on_tool_call=lambda name, args: calls.append(f"{name}({args})"),
        )

    # Step 7: remember the reply for the model and for the screen, then redraw.
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.chat.append(
        {"role": "assistant", "content": reply, "tools": calls}
    )
    st.rerun()
