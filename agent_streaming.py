from langchain.agents import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.callbacks.streaming_stdout_final_only import (
    FinalStreamingStdOutCallbackHandler,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.callbacks import AsyncIteratorCallbackHandler
from langchain.chat_models import ChatOpenAI
import asyncio
import os
from pydantic import BaseModel
from queue import Queue
from typing import Any
import time
import threading

q = Queue()

os.environ["OPENAI_API_KEY"] = "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"

app = FastAPI()

iter_callback = AsyncIteratorCallbackHandler()
stream_callback = FinalStreamingStdOutCallbackHandler()


class Message(BaseModel):
    content: str


class AgentStreaming(FinalStreamingStdOutCallbackHandler):
    def __init__(self, queue: Queue, **kwargs):
        super().__init__(**kwargs)
        self.queue = queue

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run on new LLM token. Only available when streaming is enabled."""

        # Remember the last n tokens, where n = len(answer_prefix_tokens)
        self.append_to_last_tokens(token)

        # Check if the last n tokens match the answer_prefix_tokens list ...
        if self.check_if_answer_reached():
            self.answer_reached = True
            if self.stream_prefix:
                for t in self.last_tokens:
                    # sys.stdout.write(t)
                    self.queue.put(t)
                # sys.stdout.flush()
            return

        # ... if yes, then print tokens from now on
        if self.answer_reached:
            # sys.stdout.write(token)
            # sys.stdout.flush()
            self.queue.put(token)


llm = ChatOpenAI(streaming=True, callbacks=[AgentStreaming(q)], temperature=0)
tools = load_tools(["wikipedia", "llm-math"], llm=llm)
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=False
)


def send_gen(message: str, q: Queue):
    while True:
        token = q.get()
        if token == "<endtoken-spark>":
            break
        yield token


def run_agent(messsage: str, q: Queue):
    agent.run(messsage)
    q.put("<endtoken-spark>")


@app.post("/chat")
async def stream_chat(message: Message):
    t1 = threading.Thread(
        target=run_agent,
        args=(message.content, q),
    )
    t1.start()
    gen = send_gen(message=message.content, q=q)
    return StreamingResponse(gen, media_type="text/event-stream")
