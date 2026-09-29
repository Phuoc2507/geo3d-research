# -*- coding: utf-8 -*-
"""
expr.py — dịch từ api/_lib/kernel/analysis/expr.ts

Parser + evaluator biểu thức 1 dòng cho engine giải tích:
  số, biến, + - * / ^ (^ phải-kết-hợp), đơn nguyên (lỏng hơn ^), ngoặc,
  hàm dựng sẵn sin/cos/tan/sqrt/abs/exp/ln/log, hằng pi/e.
Grammar (đệ quy xuống):
  E := T (('+'|'-') T)*
  T := U (('*'|'/') U)*
  U := ('-'|'+') U | F
  F := B ('^' U)?
  B := num | const | var | func '(' E ')' | '(' E ')'
"""
from __future__ import annotations
import math
import re

FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "sqrt": math.sqrt, "abs": abs, "exp": math.exp,
    "ln": math.log, "log": math.log,     # ln = log = log tự nhiên (chuẩn giải tích VN)
}
CONSTS = {"pi": math.pi, "e": math.e}

_TOKEN = re.compile(r"\s*(?:([0-9.]+)|([A-Za-z_]\w*)|([+\-*/^()]))")


def _tokenize(s: str):
    toks, i = [], 0
    while i < len(s):
        m = _TOKEN.match(s, i)
        if not m or m.end() == i:
            raise ValueError(f"Ký tự lạ trong biểu thức tại: '{s[i:]}'")
        num, name, op = m.groups()
        if num is not None:
            toks.append(("num", num))
        elif name is not None:
            toks.append(("name", name))
        else:
            toks.append((op, op))       # '(' ')' hoặc toán tử
        i = m.end()
    return toks


def parse_expr(src: str):
    """Trả một hàm f(env=None) -> float. env là dict biến, ví dụ {'x': 2.0}."""
    toks = _tokenize(src)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def eat():
        nonlocal pos
        tk = toks[pos]
        pos += 1
        return tk

    def parse_E():
        left = parse_T()
        while peek() and peek()[0] in ("+", "-"):
            op = eat()[0]
            right = parse_T()
            l = left
            left = (lambda l, right, op: (lambda env: l(env) + right(env) if op == "+" else l(env) - right(env)))(l, right, op)
        return left

    def parse_T():
        left = parse_U()
        while peek() and peek()[0] in ("*", "/"):
            op = eat()[0]
            right = parse_U()
            l = left
            left = (lambda l, right, op: (lambda env: l(env) * right(env) if op == "*" else l(env) / right(env)))(l, right, op)
        return left

    def parse_U():
        tk = peek()
        if tk and tk[0] == "-":
            eat(); u = parse_U(); return lambda env: -u(env)
        if tk and tk[0] == "+":
            eat(); return parse_U()
        return parse_F()

    def parse_F():
        base = parse_B()
        if peek() and peek()[0] == "^":
            eat(); exp = parse_U()
            return lambda env: math.pow(base(env), exp(env))
        return base

    def parse_B():
        tk = peek()
        if tk is None:
            raise ValueError("Biểu thức cụt")
        if tk[0] == "num":
            eat(); val = float(tk[1]); return lambda env: val
        if tk[0] == "(":
            eat(); e = parse_E()
            if not peek() or peek()[0] != ")":
                raise ValueError("Thiếu )")
            eat(); return e
        if tk[0] == "name":
            eat()
            if peek() and peek()[0] == "(":       # lời gọi hàm
                fname = tk[1]
                eat(); arg = parse_E()
                if not peek() or peek()[0] != ")":
                    raise ValueError("Thiếu )")
                eat()
                def call(env, fname=fname, arg=arg):
                    fn = FUNCS.get(fname)
                    if fn is None:
                        raise ValueError(f"Hàm lạ: {fname}")
                    return fn(arg(env))
                return call
            if tk[1] in CONSTS:
                cv = CONSTS[tk[1]]
                return lambda env: cv
            name = tk[1]
            def var(env, name=name):
                if env is None or name not in env:
                    raise ValueError(f"Biến chưa gán: {name}")
                return env[name]
            return var
        raise ValueError(f"Token lạ: {tk[1]}")

    fn = parse_E()
    if pos != len(toks):
        raise ValueError("Biểu thức dư token")
    return lambda env=None: fn(env or {})


def eval_expr(src: str, env: dict | None = None) -> float:
    return parse_expr(src)(env or {})
