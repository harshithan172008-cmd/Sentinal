import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable, args=["connectors/gmail_server.py"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("search_billing_emails", {"max_results": 2})
            print("OK:", res.content[0].text[:200])


def show(e, depth=0):
    if isinstance(e, BaseExceptionGroup):
        for sub in e.exceptions:
            show(sub, depth + 1)
    else:
        print("REAL ERROR:", type(e).__name__, e)


try:
    asyncio.run(main())
except BaseException as e:
    show(e)