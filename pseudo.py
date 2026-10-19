"""Transpilador simple: pseudocódigo en español -> Python / JavaScript / Kotlin.

Uso: python pseudo.py ejemplo.pseudo python|js|kotlin
"""
import re
import sys


# ---------- Parser: texto -> AST ----------
def parse_block(lines, i, stop):
    body = []
    while i < len(lines):
        line = lines[i]
        word = line.split()[0]
        if word in stop:
            return body, i
        i += 1
        if word == "funcion":
            m = re.match(r"funcion\s+(\w+)\((.*)\)", line)
            params = [p.strip() for p in m.group(2).split(",") if p.strip()]
            inner, i = parse_block(lines, i, {"fin"})
            body.append(("func", m.group(1), params, inner))
            i += 1
        elif word == "si":
            cond = line[2:].strip()
            then, i = parse_block(lines, i, {"sino", "fin"})
            other = []
            if lines[i].split()[0] == "sino":
                other, i = parse_block(lines, i + 1, {"fin"})
            body.append(("if", cond, then, other))
            i += 1
        elif word == "mientras":
            inner, i = parse_block(lines, i, {"fin"})
            body.append(("while", line[8:].strip(), inner))
            i += 1
        elif word == "mostrar":
            body.append(("show", line[7:].strip()))
        elif word == "devolver":
            body.append(("return", line[8:].strip()))
        elif "=" in line:
            name, expr = line.split("=", 1)
            body.append(("assign", name.strip(), expr.strip()))
        else:
            body.append(("expr", line))
    return body, i


def parse(source):
    lines = [l.strip() for l in source.splitlines() if l.strip() and not l.strip().startswith("#")]
    return parse_block(lines, 0, set())[0]


# ---------- Generadores: AST -> código ----------
def convert_expr(expr, lang):
    expr = re.sub(r"\by\b", "&&" if lang != "python" else "and", expr)
    expr = re.sub(r"\bo\b", "||" if lang != "python" else "or", expr)
    expr = re.sub(r"\bno\b", "!" if lang != "python" else "not", expr)
    return expr


def gen(nodes, lang, level=0, declared=None):
    declared = set() if declared is None else declared
    pad = "    " * level
    out = []
    brace = lang != "python"
    e = lambda x: convert_expr(x, lang)

    def block(header, inner, scope):
        out.append(f"{pad}{header}" + (" {" if brace else ":"))
        out.extend(gen(inner, lang, level + 1, scope))
        if brace:
            out.append(f"{pad}}}")

    for n in nodes:
        kind = n[0]
        if kind == "show":
            out.append(pad + {"python": f"print({e(n[1])})", "js": f"console.log({e(n[1])});",
                              "kotlin": f"println({e(n[1])})"}[lang])
        elif kind == "return":
            out.append(f"{pad}return {e(n[1])}" + (";" if lang == "js" else ""))
        elif kind == "assign":
            name, expr = n[1], e(n[2])
            if lang == "python" or name in declared:
                out.append(f"{pad}{name} = {expr}" + (";" if lang == "js" else ""))
            else:
                declared.add(name)
                out.append(f"{pad}{'let' if lang == 'js' else 'var'} {name} = {expr}" + (";" if lang == "js" else ""))
        elif kind == "expr":
            out.append(f"{pad}{e(n[1])}" + (";" if lang == "js" else ""))
        elif kind == "if":
            block(f"if {e(n[1])}" if lang == "python" else f"if ({e(n[1])})", n[2], declared)
            if n[3]:
                out.append(f"{pad}else:" if lang == "python" else f"{pad}else {{")
                out.extend(gen(n[3], lang, level + 1, declared))
                if brace:
                    out.append(f"{pad}}}")
        elif kind == "while":
            block(f"while {e(n[1])}" if lang == "python" else f"while ({e(n[1])})", n[2], declared)
        elif kind == "func":
            _, name, params, inner = n
            if lang == "python":
                header = f"def {name}({', '.join(params)})"
            elif lang == "js":
                header = f"function {name}({', '.join(params)})"
            else:
                header = f"fun {name}({', '.join(p + ': Any' for p in params)})"
            block(header, inner, set(params))
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("python", "js", "kotlin"):
        sys.exit("Uso: python pseudo.py archivo.pseudo python|js|kotlin")
    with open(sys.argv[1], encoding="utf-8") as f:
        print("\n".join(gen(parse(f.read()), sys.argv[2])))
