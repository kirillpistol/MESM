"""Build a deterministic AST index without importing/executing source modules."""
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(root):
    lines=['# MESM — L3: актуальный указатель кода','Сформирован scripts/build_code_index.py из текущих объявлений AST. Не заменяет математические пояснения. Номера строк относятся к данной версии файлов.']
    for base in ('src/mesm','dashboard','scripts'):
        for path in sorted((root/base).rglob('*.py')):
            tree=ast.parse(path.read_text(encoding='utf-8'))
            lines+=['\n## '+path.relative_to(root).as_posix()]
            doc=ast.get_docstring(tree)
            if doc:lines.append(doc.splitlines()[0].replace('|','/'))
            def visit(node,prefix=''):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                        name=prefix+child.name
                        explanation=ast.get_docstring(child)
                        text=explanation.splitlines()[0] if explanation else 'Описание: см. реализацию и основной справочник функций.'
                        lines.append(f'- `{name}` — строка {child.lineno}. {text}')
                        visit(child,name+'.')
                    else:visit(child,prefix)
            visit(tree)
    return '\n\n'.join(lines)+'\n'
if __name__=='__main__':
    target=ROOT/'docs/40_current_code_index.md';target.write_text(build(ROOT),encoding='utf-8');print(target)
