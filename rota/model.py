"""Model client with a hard per-item call budget.

Every request is counted *before* it is sent, so a failed request still
spends budget -- the grader's proxy counts requests, not successes.  The
OpenAI client's own retries are disabled for the same reason.
"""
import os
import re
import time

import httpx
from openai import OpenAI

SAMPLING = dict(temperature=1.0, top_p=0.95,
                extra_body={"reasoning": {"enabled": False}})


def _env():
    vals = {}
    here = os.path.dirname(os.path.abspath(__file__))
    for d in (os.getcwd(), os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        p = os.path.join(d, ".env")
        if os.path.exists(p):
            for line in open(p):
                m = re.match(r"\s*([A-Za-z_]+)\s*=\s*(.*?)\s*$", line)
                if m:
                    vals.setdefault(m.group(1), m.group(2).strip("'\""))
    for k in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "MODEL",
              "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        if os.environ.get(k):
            vals[k] = os.environ[k]
    return vals


class BudgetExceeded(Exception):
    pass


class Model:
    def __init__(self):
        e = _env()
        self.model = e.get("MODEL", "ibm-granite/granite-4.2-8b")
        self.client = OpenAI(
            base_url=e.get("OPENROUTER_BASE_URL") or e.get("OPENAI_BASE_URL"),
            api_key=e.get("OPENROUTER_API_KEY") or e.get("OPENAI_API_KEY"),
            max_retries=0, timeout=300)
        # Optional hook for the "does the model matter" check: perturb every
        # completion before the system sees it.
        self.corrupt = os.environ.get("ROTA_CORRUPT_MODEL") == "1"


class ItemSession:
    """All model calls for one item go through here."""

    def __init__(self, model, item_id, cap):
        self.m, self.id, self.cap, self.used = model, item_id, cap, 0
        self.log = []

    @property
    def left(self):
        return self.cap - self.used

    def ask(self, system, user, max_tokens=4096):
        if self.used >= self.cap:
            raise BudgetExceeded(self.id)
        self.used += 1
        t0 = time.time()
        for attempt in range(4):
            try:
                r = self.m.client.chat.completions.create(
                    model=self.m.model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    max_tokens=max_tokens,
                    extra_headers={"X-Item-Id": self.id},
                    **SAMPLING)
                out = r.choices[0].message.content or ""
                break
            except Exception as ex:
                # A TCP connection that never opened carried no request, so
                # no proxy can have counted it: retrying it cannot break the
                # budget, and not retrying could leave the item with no call
                # at all.  Anything else (timeout, HTTP error, a reset after
                # sending) may have been counted, so it is spent, not retried.
                if _never_sent(ex) and attempt < 3:
                    self.log.append({"retry": repr(ex)[:120]})
                    time.sleep(2 ** attempt)
                    continue
                self.log.append({"error": repr(ex)[:200], "s": time.time() - t0})
                return None
        if self.m.corrupt:
            out = _corrupt(out)
        self.log.append({"s": round(time.time() - t0, 2), "out": out})
        return out


def _never_sent(ex):
    """True only for a failure to open the connection (refused, DNS)."""
    seen = set()
    while ex is not None and id(ex) not in seen:
        seen.add(id(ex))
        if isinstance(ex, (httpx.ConnectError, ConnectionRefusedError)):
            return True
        ex = ex.__cause__ or ex.__context__
    return False


def _corrupt(text):
    """Model-dependence check only: hand each statement the translation the
    model wrote for the NEXT statement (the echoed copy stays put, so
    realignment cannot undo it)."""
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if "=>" in l or re.match(r"\s*\d+:", l)]
    def split(l):
        if "=>" in l:
            a, b = l.rsplit("=>", 1)
            return a + "=>", b
        a, b = l.split(":", 1)
        return a + ":", b
    parts = [split(lines[i]) for i in idx]
    rot = [p[1] for p in parts[1:] + parts[:1]]
    for i, (head, _), new in zip(idx, parts, rot):
        lines[i] = head + new
    return "\n".join(lines)
